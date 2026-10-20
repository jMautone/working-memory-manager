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

from wcm import clock, ids, model, prompt, render, shell
from wcm.store import Entry, NotFound, Store

OK, DOMAIN_ERROR, USAGE_ERROR = 0, 1, 2


class DomainError(Exception):
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
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except AttributeError, ValueError:
            pass
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


def _pause_fields(ctx: Ctx, entry: Entry, flags: dict[str, str | None]) -> dict[str, str]:
    """Decide the new NOW values for an initiative being let go. Writes nothing."""
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
        hint = "" if not given and prompt.stdin_is_tty() else ' (use -n "<next action>")'
        raise DomainError(f"a next action is required to pause {init.id}{hint}")
    return values


def _apply_pause(ctx: Ctx, entry: Entry, values: dict[str, str], trigger: str) -> None:
    init = entry.initiative
    init.now.update(values)
    init.meta["status"] = "paused"
    init.set_time("last_paused", ctx.now)
    init.meta["waiting_on"] = None
    ctx.store.write_checkpoint(entry, ctx.now, trigger)
    ctx.store.save(entry, ctx.now)


def _go_to(ctx: Ctx, init: model.Initiative) -> None:
    if not shell.request_cd(init.primary_path):
        ctx.warn(f"{init.id} workspace path does not exist: {init.primary_path}")


# --- commands ------------------------------------------------------------------


def cmd_new(args, ctx: Ctx) -> int:
    title = " ".join(" ".join(args.title).split())
    if not title:
        raise DomainError("a title is required")
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
            flags = {"Next": args.pause_next}
            values = _pause_fields(ctx, current, flags)

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
        ctx.say(f"{current.initiative.id} paused.")
    ctx.store.create(init)
    ctx.say(f"{initiative_id} {status}: {title}")
    if path and not os.path.isdir(path):
        ctx.warn(f"{initiative_id} workspace path does not exist: {path}")
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
    missing = {
        e.initiative.id: e.initiative.primary_path
        for e in in_flight
        if e.initiative.primary_path and not os.path.isdir(e.initiative.primary_path)
    }
    width = shutil.get_terminal_size(fallback=(100, 24)).columns
    ctx.out.write(
        render.working_set(
            [e.initiative for e in in_flight],
            now=ctx.now,
            width=width,
            latest_checkpoint=latest,
            missing_paths=missing,
            problems=[(ctx.store.relative(p.path), p.reason) for p in problems],
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
    )
    _apply_pause(ctx, entry, values, "pause")
    ctx.say("Checkpoint saved.")
    ctx.say("Safe to switch context.")
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
        values = _pause_fields(ctx, current, {})
        _apply_pause(ctx, current, values, "switch")
        ctx.say(f"{current.initiative.id} paused.")
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
        )
    )
    _go_to(ctx, init)
    return OK


def cmd_done(args, ctx: Ctx) -> int:
    entry = _resolve(ctx, args.id)
    init = entry.initiative
    if init.status == "done" or entry.location == "done":
        raise DomainError(f"{init.id} is already done")
    init.meta["status"] = "done"
    init.set_time("closed", ctx.now)
    ctx.store.write_checkpoint(entry, ctx.now, "done")
    ctx.store.save(entry, ctx.now)
    ctx.store.move_to_done(entry)
    ctx.say(f"{init.id} done: {init.title}")
    return OK
