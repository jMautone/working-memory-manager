"""The `wcm` command line: argument parsing, one handler per command, exit codes.

Exit codes: 0 success, 1 domain error (unknown ID, malformed file, a refused
transition, nothing to act on), 2 usage error. Errors go to stderr.

Each handler reads through the store, decides, and only then writes: a
refused command leaves every file as it was.
"""

import argparse
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime

from wcm import clock, editor, ids, model, note, prompt, render, shell
from wcm.store import Entry, NotFound, Store

OK, DOMAIN_ERROR, USAGE_ERROR = 0, 1, 2


class DomainError(Exception):
    pass


class UsageError(Exception):
    pass


@dataclass
class Ctx:
    store: Store
    now: datetime
    out: object
    err: object

    def say(self, text: str = "") -> None:
        print(text, file=self.out)

    def warn(self, text: str) -> None:
        print(f"!  {text}", file=self.out)


# --- parsing -----------------------------------------------------------------


def _id_arg(text: str) -> str:
    try:
        return ids.parse(text)
    except ids.InvalidId as e:
        raise argparse.ArgumentTypeError(str(e)) from None


def _add_pause_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("-n", "--next", dest="next_", metavar="TEXT", help="next action")
    p.add_argument(
        "-s", "--stopped-at", dest="stopped_at", metavar="TEXT", help="where you stopped"
    )
    p.add_argument("-i", "--important", metavar="TEXT", help="something not to forget")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wcm",
        description="Working memory layer: let go of an initiative, see what needs "
        "attention, and pick it up again in under 30 seconds.",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    p = sub.add_parser("new", help="create an initiative and switch to it")
    p.add_argument("title", nargs="+", help="title of the initiative")
    p.add_argument("--type", choices=model.TYPES, default="other")
    p.add_argument("--priority", choices=model.PRIORITIES, default="normal")
    p.add_argument("--path", metavar="DIR", help="directory where the work happens")
    p.add_argument("--tags", metavar="A,B", default="", help="comma-separated tags")
    p.add_argument("--focus", metavar="TEXT", help="what this is about (default: the title)")
    p.add_argument("--why", metavar="TEXT", help="why it matters")
    p.add_argument("--next", dest="next_", metavar="TEXT", help="next action of the new initiative")
    p.add_argument(
        "--pause-next",
        metavar="TEXT",
        help="next action of the initiative being paused, so the switch needs no prompt",
    )
    p.add_argument(
        "--paused", action="store_true", help="create it paused, without switching (needs --next)"
    )
    p.set_defaults(handler=cmd_new)

    p = sub.add_parser("now", help="show what needs attention")
    p.set_defaults(handler=cmd_now)

    p = sub.add_parser("pause", help="let go of an initiative (default: the active one)")
    p.add_argument("id", nargs="?", type=_id_arg, metavar="ID")
    _add_pause_flags(p)
    p.set_defaults(handler=cmd_pause)

    p = sub.add_parser("resume", help="switch to an initiative (no ID: show the active one again)")
    p.add_argument("id", nargs="?", type=_id_arg, metavar="ID")
    p.set_defaults(handler=cmd_resume)

    p = sub.add_parser("done", help="close an initiative (default: the active one)")
    p.add_argument("id", nargs="?", type=_id_arg, metavar="ID")
    p.set_defaults(handler=cmd_done)

    p = sub.add_parser(
        "note",
        help="save a note, linked to the active initiative (edit <ID>: open one)",
        description="Save a note in seconds; the text is its title. With no text, ask for "
        "it. `wcm note edit <ID>` opens an existing note in the editor (VISUAL, then EDITOR).",
    )
    p.add_argument("text", nargs="*", help="the note, saved as its title")
    p.add_argument("-t", "--tag", action="append", metavar="TAG", help="add a tag (repeat, or a,b)")
    p.add_argument(
        "-e", "--edit", action="store_true", help="open the note in the editor after saving it"
    )
    p.add_argument("--free", action="store_true", help="do not link it to the active initiative")
    p.set_defaults(handler=cmd_note)

    p = sub.add_parser("notes", help="find notes, newest first")
    p.add_argument("terms", nargs="*", metavar="term", help="text each note must contain")
    p.add_argument(
        "-t",
        "--tag",
        action="append",
        metavar="TAG",
        help="only notes with this tag (repeat, or a,b)",
    )
    p.add_argument(
        "-i",
        "--initiative",
        type=_id_arg,
        metavar="ID",
        help="only notes linked to this initiative",
    )
    p.set_defaults(handler=cmd_notes)
    return parser


def _configure_streams() -> None:
    """Write what the reader's console can decode.

    On Windows, Python encodes redirected output in the ANSI code page, while
    PowerShell decodes it with the console's code page: use the latter, so a
    title with accents survives `wcm now | Select-String`.
    """
    console_cp = 0
    if sys.platform == "win32":
        try:
            import ctypes

            console_cp = ctypes.windll.kernel32.GetConsoleOutputCP()
        except AttributeError, OSError:
            console_cp = 0
    for stream, real in ((sys.stdout, sys.__stdout__), (sys.stderr, sys.__stderr__)):
        try:
            # Only the process's own streams: a test harness's capture is left alone.
            if console_cp and stream is real and not stream.isatty():
                stream.reconfigure(encoding=f"cp{console_cp}", errors="replace")
            else:
                stream.reconfigure(errors="replace")
        except AttributeError, ValueError, LookupError, OSError:
            pass


def _ellipsis(stream) -> str:
    try:
        render.ELLIPSIS.encode(stream.encoding or "utf-8")
    except UnicodeEncodeError, LookupError, AttributeError:
        return "..."
    return render.ELLIPSIS


def main(argv: list[str] | None = None) -> int:
    _configure_streams()
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return USAGE_ERROR if e.code not in (0, None) else OK
    if args.command is None:
        parser.print_usage(sys.stderr)
        print("wcm: error: a command is required", file=sys.stderr)
        return USAGE_ERROR
    ctx = Ctx(store=Store(), now=clock.now(), out=sys.stdout, err=sys.stderr)
    try:
        return args.handler(args, ctx)
    except UsageError as e:
        print(f"wcm {args.command}: error: {e}", file=sys.stderr)
        return USAGE_ERROR
    except (DomainError, NotFound, model.MalformedError, OSError) as e:
        print(f"wcm: error: {e}", file=sys.stderr)
        return DOMAIN_ERROR
    except KeyboardInterrupt, EOFError:
        print("\nwcm: interrupted; nothing was changed", file=sys.stderr)
        return DOMAIN_ERROR


# --- shared flows --------------------------------------------------------------


def _actives(ctx: Ctx) -> list[Entry]:
    entries, _ = ctx.store.scan()
    return [e for e in entries if e.location == "initiatives" and e.initiative.status == "active"]


def _refuse_many_active(ctx: Ctx, actives: list[Entry]) -> None:
    if len(actives) > 1:
        files = ", ".join(ctx.store.relative(e.path) for e in actives)
        raise DomainError(
            f"more than one initiative is active ({files}); fix the files by hand first"
        )


def _resolve(ctx: Ctx, initiative_id: str | None) -> Entry:
    """The named initiative, or the active one when no ID is given. Never a guess."""
    if initiative_id:
        return ctx.store.find(initiative_id)
    actives = _actives(ctx)
    if not actives:
        raise DomainError("no initiative is active; see wcm now")
    _refuse_many_active(ctx, actives)
    return actives[0]


def _pause_fields(
    ctx: Ctx, entry: Entry, flags: dict[str, str | None], hint: str
) -> dict[str, str]:
    """Decide the new NOW values for an initiative being let go. Writes nothing.

    `hint` tells the person how to give the next action without a prompt, in
    the terms of the command that is running.
    """
    init = entry.initiative
    values = dict(init.now)
    given = {label: value for label, value in flags.items() if value is not None}
    if given:
        for label, value in given.items():
            values[label] = model.one_line(value)
    elif prompt.stdin_is_tty():
        ctx.say(f"{init.id} {init.title}")
        ctx.say()
        for prompt_label, label in (
            ("Next action", "Next"),
            ("Stopped at", "Stopped at"),
            ("Important", "Important"),
        ):
            answer = prompt.ask(prompt_label, values[label], ctx.out)
            if answer is None and label == "Next":
                raise DomainError(f"a next action is required to pause {init.id}")
            values[label] = model.one_line(answer or "")
        ctx.say()
    if not values["Next"]:
        suffix = "" if not given and prompt.stdin_is_tty() else f" ({hint})"
        raise DomainError(f"a next action is required to pause {init.id}{suffix}")
    return values


def _apply_pause(ctx: Ctx, entry: Entry, values: dict[str, str], trigger: str) -> None:
    init = entry.initiative
    init.now.update(values)
    init.meta["status"] = "paused"
    init.set_time("last_paused", ctx.now)
    init.meta["waiting_on"] = None
    ctx.store.write_checkpoint(entry, ctx.now, trigger)
    ctx.store.save(entry, ctx.now)
    ctx.say("Checkpoint saved.")
    ctx.say("Safe to switch context.")


def _path_problem(path: str | None) -> str | None:
    """Why a recorded workspace path cannot be used, independent of the current directory."""
    if not path:
        return None
    if not os.path.isabs(path):
        return f"workspace path is not absolute: {path}"
    if not os.path.isdir(path):
        return f"workspace path does not exist: {path}"
    return None


def _go_to(ctx: Ctx, init: model.Initiative) -> None:
    problem = _path_problem(init.primary_path)
    if problem:
        ctx.warn(f"{init.id} {problem}")
    else:
        shell.request_cd(init.primary_path)


# --- commands ------------------------------------------------------------------


def cmd_new(args, ctx: Ctx) -> int:
    title = model.one_line(" ".join(args.title))
    if not title:
        raise UsageError("a title is required")
    next_ = model.one_line(args.next_)
    if args.paused and not next_:
        raise DomainError('a paused initiative needs a next action: add --next "<text>"')
    path = os.path.abspath(os.path.expanduser(args.path)) if args.path else None
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    current = None
    if not args.paused:
        actives = _actives(ctx)
        _refuse_many_active(ctx, actives)
        if actives:
            current = actives[0]
            values = _pause_fields(
                ctx, current, {"Next": args.pause_next}, 'use --pause-next "<next action>"'
            )

    status = "paused" if args.paused else "active"
    initiative_id = ctx.store.next_id()
    init = model.Initiative(
        meta=model.new_meta(
            initiative_id,
            title,
            type_=args.type,
            status=status,
            priority=args.priority,
            created=ctx.now,
            tags=tags,
            workspace=path,
        )
    )
    init.now["Focus"] = model.one_line(args.focus) or title
    init.now["Why it matters"] = model.one_line(args.why)
    init.now["Next"] = next_

    if current is not None:
        _apply_pause(ctx, current, values, "switch")
        ctx.say()
    ctx.store.create(init)
    ctx.say(f"{initiative_id} {status}: {title}")
    problem = _path_problem(path)
    if problem:
        ctx.warn(f"{initiative_id} {problem}")
    elif status == "active":
        _go_to(ctx, init)
    return OK


def cmd_now(args, ctx: Ctx) -> int:
    entries, problems = ctx.store.scan()
    in_flight = [
        e for e in entries if e.location == "initiatives" and e.initiative.status != "done"
    ]
    tz = ctx.now.tzinfo
    latest = {
        e.initiative.id: ctx.store.latest_checkpoint(e, tz)
        for e in in_flight
        if e.initiative.status == "active"
    }
    path_problems = {
        e.initiative.id: problem
        for e in in_flight
        if (problem := _path_problem(e.initiative.primary_path))
    }
    width = shutil.get_terminal_size(fallback=(100, 24)).columns
    ctx.out.write(
        render.working_set(
            [e.initiative for e in in_flight],
            now=ctx.now,
            width=width,
            latest_checkpoint=latest,
            path_problems=path_problems,
            problems=[(ctx.store.relative(p.path), p.reason) for p in problems],
            ellipsis=_ellipsis(ctx.out),
        )
    )
    return OK


def cmd_pause(args, ctx: Ctx) -> int:
    entry = _resolve(ctx, args.id)
    if entry.initiative.status == "done":
        raise DomainError(f"{entry.initiative.id} is done; there is nothing to pause")
    values = _pause_fields(
        ctx,
        entry,
        {"Next": args.next_, "Stopped at": args.stopped_at, "Important": args.important},
        'use -n "<next action>"',
    )
    _apply_pause(ctx, entry, values, "pause")
    return OK


def cmd_resume(args, ctx: Ctx) -> int:
    actives = _actives(ctx)
    _refuse_many_active(ctx, actives)
    current = actives[0] if actives else None

    if args.id is None and current is None:
        entries, _ = ctx.store.scan()
        waiting = [
            e.initiative
            for e in entries
            if e.location == "initiatives" and e.initiative.status in ("paused", "waiting")
        ]
        print("wcm: error: no initiative is active", file=ctx.err)
        ctx.out.write(render.candidates(waiting))
        return DOMAIN_ERROR

    target = current if args.id is None else ctx.store.find(args.id)
    init = target.initiative
    if init.status == "done" or target.location == "done":
        raise DomainError(
            f"{init.id} is done. To reopen it, move done/{init.id} back to initiatives/ "
            "in the knowledge base and set its status to paused"
        )

    if current is not None and current.initiative.id == init.id:
        # Back in a new terminal: show it again and go there, without writing.
        ctx.out.write(
            render.brief(
                init,
                now=ctx.now,
                status_before="active",
                since_before=init.time("last_resumed"),
                waiting_on={},
                notes=_linked_notes(ctx, init.id),
            )
        )
        _go_to(ctx, init)
        return OK

    status_before = init.status
    if status_before == "waiting":
        since_before = model.parse_time(init.waiting_on.get("since"))
    else:
        since_before = init.time("last_paused")
    waiting_on = dict(init.waiting_on)

    if current is not None:
        values = _pause_fields(
            ctx,
            current,
            {},
            f'run wcm pause -n "<next action>" first, then wcm resume {init.id}',
        )
        _apply_pause(ctx, current, values, "switch")
        ctx.say()

    init.meta["status"] = "active"
    init.set_time("last_resumed", ctx.now)
    init.meta["waiting_on"] = None
    ctx.store.save(target, ctx.now)
    ctx.out.write(
        render.brief(
            init,
            now=ctx.now,
            status_before=status_before,
            since_before=since_before,
            waiting_on=waiting_on,
            notes=_linked_notes(ctx, init.id),
        )
    )
    _go_to(ctx, init)
    return OK


def cmd_done(args, ctx: Ctx) -> int:
    entry = _resolve(ctx, args.id)
    init = entry.initiative
    if init.status == "done" or entry.location == "done":
        raise DomainError(f"{init.id} is already done")
    target = ctx.store.done_directory(init.id)
    if target.exists():
        raise DomainError(f"{ctx.store.relative(target)} already exists; nothing was changed")
    # Move first: a refused move leaves everything as it was. Then record the
    # closing in the moved directory.
    moved = ctx.store.move_to_done(entry)
    init.meta["status"] = "done"
    init.set_time("closed", ctx.now)
    ctx.store.write_checkpoint(moved, ctx.now, "done")
    ctx.store.save(moved, ctx.now)
    ctx.say(f"{init.id} done: {init.title}")
    return OK


def _linked_notes(ctx: Ctx, initiative_id: str) -> tuple[int, str] | None:
    """How many valid notes link to the initiative, and the title of the latest."""
    entries, _ = ctx.store.scan_notes(note.prefilter([], [], initiative_id))
    linked = [e.note for e in entries if e.note.initiative == initiative_id]
    if not linked:
        return None
    return len(linked), render.notes_in_order(linked)[0].title


def cmd_note(args, ctx: Ctx) -> int:
    if args.text and args.text[0] == "edit":
        return _edit_note(args, ctx)
    if args.text:
        title = model.one_line(" ".join(args.text))
        if not title:
            raise UsageError('a text is required: wcm note "<text>"')
    elif prompt.stdin_is_tty():
        title = model.one_line(prompt.line("Note", ctx.out))
        if not title:
            raise DomainError("the note is empty; nothing was saved")
    else:
        # Never from a pipe: Windows PowerShell 5.1 turns accents into `?` there.
        raise UsageError('a text is required: wcm note "<text>", or run it in a terminal')
    tags = note.normalize_tags(args.tag)

    linked, actives = None, []
    if not args.free:
        actives = [e.initiative for e in _actives(ctx)]
        if len(actives) == 1:
            linked = actives[0]

    note_id = ctx.store.next_note_id()
    text = note.render_new(note_id, title, tags, linked.id if linked else None, ctx.now)
    path = ctx.store.create_note(note_id, text)
    if linked:
        ctx.say(f"{note_id} saved, linked to {linked.id} {linked.title}.")
    else:
        ctx.say(f"{note_id} saved.")
    if len(actives) > 1:
        names = ", ".join(i.id for i in actives)
        ctx.warn(f"More than one initiative is active ({names}); the note was not linked")
    if args.edit:
        return _open_in_editor(ctx, note_id, path)
    return OK


def _edit_note(args, ctx: Ctx) -> int:
    rest = args.text[1:]
    if args.tag or args.edit or args.free:
        raise UsageError("edit takes only a note ID: wcm note edit <ID>")
    if not rest:
        raise UsageError("a note ID is required: wcm note edit <ID>")
    quote = 'to save a note that starts with "edit", quote the whole text: wcm note "edit ..."'
    if len(rest) > 1:
        raise UsageError(f"edit takes one note ID; {quote}")
    try:
        note_id = ids.parse_note(rest[0])
    except ids.InvalidId as e:
        raise UsageError(f"{e}; {quote}") from None
    return _open_in_editor(ctx, note_id, ctx.store.find_note_path(note_id))


def _open_in_editor(ctx: Ctx, note_id: str, path) -> int:
    """Open the note, wait, and record `updated` only when it changed and still reads."""
    rel = ctx.store.relative(path)
    before = path.read_bytes()
    ctx.out.flush()
    try:
        code = editor.open(path)
    except editor.EditorError as e:
        raise DomainError(str(e)) from None
    if code != 0:
        raise DomainError(f"the editor exited with code {code}; {rel} is left as it is on disk")
    after = path.read_bytes()
    if after == before:
        ctx.say(f"{note_id} unchanged.")
        return OK
    try:
        text = after.decode("utf-8")
        note.parse(text, note_id)
    except UnicodeDecodeError:
        raise model.MalformedError(f"{rel} is not UTF-8 text; it was left as saved") from None
    except model.MalformedError as e:
        raise model.MalformedError(f"{rel}: {e}; it was left as saved") from None
    ctx.store.replace_note(path, note.touch_updated(text, clock.now()))
    ctx.say(f"{note_id} updated.")
    return OK


def cmd_notes(args, ctx: Ctx) -> int:
    tags = note.normalize_tags(args.tag)
    if args.initiative and not ctx.store.exists(args.initiative):
        raise NotFound(f"{args.initiative} was not found")
    entries, problems = ctx.store.scan_notes(note.prefilter(args.terms, tags, args.initiative))
    found = [e.note for e in entries if note.matches(e.note, args.terms, tags, args.initiative)]
    width = shutil.get_terminal_size(fallback=(100, 24)).columns
    ctx.out.write(
        render.note_list(
            found,
            now=ctx.now,
            width=width,
            problems=[(ctx.store.relative(p.path), p.reason) for p in problems],
            filtered=bool(args.terms or tags or args.initiative),
            ellipsis=_ellipsis(ctx.out),
        )
    )
    return OK
