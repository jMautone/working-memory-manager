"""What the person reads: `wcm now`, the resume brief, `wcm notes`, ages and warnings.

Pure: every function takes the time, the terminal width and the facts it
needs as arguments, and returns text.
"""

import unicodedata
from datetime import datetime, timedelta

from wcm.model import NOW_LABELS, NOW_LIMIT, PRIORITIES, Initiative, invariant_problems
from wcm.note import Note

STALE_AFTER = timedelta(hours=4)
ELLIPSIS = "…"
_INDENT = " " * 13  # under the title: two spaces, the ID, two spaces


def age(delta: timedelta | None) -> str:
    if delta is None:
        return "?"
    minutes = max(0, int(delta.total_seconds() // 60))
    if minutes < 60:
        return f"{minutes}m"
    hours, rest = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h {rest}m"
    days = hours // 24
    if days < 14:
        return f"{days}d"
    return f"{days // 7}w"


def since(when: datetime | None, now: datetime) -> str:
    return age(now - when if when else None)


def _char_width(c: str) -> int:
    if unicodedata.combining(c):
        return 0
    return 2 if unicodedata.east_asian_width(c) in ("W", "F") else 1


def display_width(text: str) -> int:
    """Terminal columns: wide East Asian characters and most emoji take two."""
    return sum(_char_width(c) for c in text)


def truncate(text: str, width: int, ellipsis: str = ELLIPSIS) -> str:
    """Cut `text` to at most `width` terminal columns, ending with `ellipsis`."""
    if width < 1:
        return ""
    if display_width(text) <= width:
        return text
    room = width - display_width(ellipsis)
    out, used = [], 0
    for c in text:
        w = _char_width(c)
        if used + w > room:
            break
        out.append(c)
        used += w
    return "".join(out) + ellipsis if room >= 0 else ellipsis[:width]


def pad(text: str, width: int) -> str:
    return text + " " * max(0, width - display_width(text))


def _priority_key(init: Initiative) -> int:
    return PRIORITIES.index(init.priority)


def _recent_first(when: datetime | None) -> float:
    return -when.timestamp() if when else float("inf")


def working_set(
    initiatives: list[Initiative],
    *,
    now: datetime,
    width: int,
    latest_checkpoint: dict[str, datetime | None],
    path_problems: dict[str, str],
    problems: list[tuple[str, str]],
    ellipsis: str = ELLIPSIS,
) -> str:
    """The `wcm now` screen. `initiatives` holds the ones not done."""
    active = sorted(
        (i for i in initiatives if i.status == "active"),
        key=lambda i: _recent_first(i.time("last_resumed")),
    )
    paused = sorted(
        (i for i in initiatives if i.status == "paused"),
        key=lambda i: (_priority_key(i), _recent_first(i.time("last_paused"))),
    )
    waiting = [i for i in initiatives if i.status == "waiting"]
    listed = active + paused
    title_width = max((display_width(i.title) for i in listed), default=0)
    title_width = max(10, min(title_width, width - 13 - 2 - 8 - 2 - 7))

    def entry(init: Initiative, when: datetime | None) -> list[str]:
        priority = init.priority if init.priority != "normal" else ""
        head = (
            f"  {init.id:<9}  {pad(truncate(init.title, title_width, ellipsis), title_width)}  "
            f"{priority:<8}  {since(when, now)}"
        )
        return [
            truncate(head.rstrip(), width, ellipsis),
            truncate(f"{_INDENT}Next: {init.now['Next']}".rstrip(), width, ellipsis),
        ]

    lines: list[str] = []
    if active:
        lines.append("ACTIVE")
        for init in active:
            lines += entry(init, init.time("last_resumed"))
        lines.append("")
    if paused:
        lines.append("PAUSED")
        for init in paused:
            lines += entry(init, init.time("last_paused"))
        lines.append("")
    if not active and not paused and not waiting:
        lines += ['Nothing in flight. Start with: wcm new "<title>"', ""]

    warnings = _warnings(
        active,
        paused,
        waiting,
        now=now,
        latest_checkpoint=latest_checkpoint,
        path_problems=path_problems,
        problems=problems,
    )
    # Warnings wrap rather than lose the path or the reason they name.
    lines += [f"!  {w}" for w in warnings]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines) + "\n"


def _warnings(active, paused, waiting, *, now, latest_checkpoint, path_problems, problems):
    out = []
    if len(active) > 1:
        out.append("More than one initiative is active: " + ", ".join(i.id for i in active))
    for init in active:
        reference = max(
            (t for t in (init.time("last_resumed"), latest_checkpoint.get(init.id)) if t),
            default=None,
        )
        if reference is not None and now - reference > STALE_AFTER:
            out.append(
                f"{init.id} has been active for {age(now - reference)} without a checkpoint;"
                " consider wcm pause"
            )
    for init in waiting:
        what = str(init.waiting_on.get("what") or "").strip()
        if what:
            owner = init.waiting_on.get("owner") or "me"
            out.append(f"{init.id} {init.title} is waiting on: {what} (owner: {owner})")
    for init in active + paused + waiting:
        out += invariant_problems(init)
        if init.now_lines > NOW_LIMIT:
            out.append(
                f"{init.id} has a NOW block of {init.now_lines} lines (limit {NOW_LIMIT}):"
                " NOW is being used as a history"
            )
        if init.id in path_problems:
            out.append(f"{init.id} {path_problems[init.id]}")
    for path, reason in problems:
        out.append(f"Could not read {path}: {reason}")
    return out


def brief(
    init: Initiative,
    *,
    now: datetime,
    status_before: str,
    since_before: datetime | None,
    waiting_on: dict,
    notes: tuple[int, str] | None = None,
) -> str:
    """What `wcm resume` prints: where it stopped and what comes next, no history."""
    lines = [f"{init.id} {init.title}"]
    if status_before == "waiting":
        what = waiting_on.get("what") or "?"
        owner = waiting_on.get("owner") or "me"
        lines.append(f"waiting for {since(since_before, now)} on: {what} (owner: {owner})")
    elif status_before == "active":
        lines.append(f"active for {since(since_before, now)}")
    else:
        lines.append(f"paused {since(since_before, now)} ago")
    lines.append("")
    for label in NOW_LABELS:
        value = init.now.get(label, "")
        if value:
            lines.append(f"  {label + ':':<16}{value}")
    path = init.primary_path
    if notes or path:
        lines.append("")
    if notes:
        count, latest = notes
        lines.append(f"  {'Notes:':<16}{count} (latest: {latest})")
    if path:
        lines.append(f"  {'Path:':<16}{path}")
    return "\n".join(lines) + "\n"


def candidates(initiatives: list[Initiative]) -> str:
    """The list `wcm resume` shows when nothing is active and no ID was given."""
    if not initiatives:
        return 'Nothing is in flight. Start with: wcm new "<title>"\n'
    lines = ["Resume one of these with: wcm resume <ID>", ""]
    for init in initiatives:
        lines.append(f"  {init.id:<9}  {init.status:<7}  {init.title}")
    return "\n".join(lines) + "\n"


def notes_in_order(notes: list[Note]) -> list[Note]:
    """Most recently created first; same or no `created` by ID, highest first; no `created` last."""
    return sorted(
        notes,
        key=lambda n: (n.created is None, _recent_first(n.created), -int(n.id.split("-")[1])),
    )


def note_list(
    notes: list[Note],
    *,
    now: datetime,
    width: int,
    problems: list[tuple[str, str]],
    filtered: bool,
    ellipsis: str = ELLIPSIS,
) -> str:
    """The `wcm notes` screen: one line per note, then the files it could not read."""
    ordered = notes_in_order(notes)
    ages = {n.id: since(n.created, now) for n in ordered}
    id_width = max((len(n.id) for n in ordered), default=0)
    age_width = max((len(a) for a in ages.values()), default=0)
    link_width = max((len(n.initiative) + 2 for n in ordered if n.initiative), default=0)
    title_width = max((display_width(n.title) for n in ordered), default=0)
    room = width - (2 + id_width + 2 + 2 + age_width + link_width)
    title_width = max(10, min(title_width, room))

    lines = []
    for n in ordered:
        title = pad(truncate(n.title, title_width, ellipsis), title_width)
        link = f"  {n.initiative}" if n.initiative else ""
        lines.append(f"  {n.id:<{id_width}}  {title}  {ages[n.id]:<{age_width}}{link}".rstrip())
    if not ordered:
        if filtered:
            lines.append("No notes match.")
        elif not problems:
            lines.append('No notes yet. Save one with: wcm note "<text>"')
    if ordered and problems:
        lines.append("")
    lines += [f"!  Could not read {path}: {reason}" for path, reason in problems]
    return "\n".join(lines) + "\n"
