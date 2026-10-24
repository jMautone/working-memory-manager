"""The initiative file: parse, render and invariants. No filesystem, no clock.

An initiative file is YAML frontmatter, a `# <title>` heading, a `## NOW` block
of five `**<Label>:** <value>` lines, and a free tail. Rendering regenerates
the known frontmatter keys, the title and the NOW block, and keeps everything
else the person wrote.
"""

import os.path
import re
from dataclasses import dataclass, field
from datetime import date, datetime, time

from wcm import frontmatter
from wcm.frontmatter import MalformedError

STATES = ("active", "paused", "waiting", "done")
PRIORITIES = ("critical", "high", "normal", "low")
TYPES = ("feature", "bug", "incident", "research", "refactor", "other")
NOW_LABELS = ("Focus", "Stopped at", "Why it matters", "Important", "Next")
NOW_LIMIT = 15

# Keys every initiative file carries, with the value written when one is missing.
KNOWN_KEYS = {
    "id": None,
    "title": "",
    "type": "other",
    "status": None,
    "priority": "normal",
    "created": None,
    "updated": None,
    "last_resumed": None,
    "last_paused": None,
    "waiting_on": None,
    "tags": [],
    "workspaces": [],
    "links": [],
}

_HEADING = re.compile(r"#{1,6}(\s|$)")
_FIELD = re.compile(r"\*\*(" + "|".join(re.escape(label) for label in NOW_LABELS) + r"):\*\*(.*)")
_NOW_HEADING = re.compile(r"##\s+NOW\s*")
_TITLE = re.compile(r"#\s+(.*)")


@dataclass
class Initiative:
    meta: dict
    now: dict = field(default_factory=lambda: dict.fromkeys(NOW_LABELS, ""))
    now_extra: list = field(default_factory=list)
    intro: str = ""
    tail: str = ""
    now_lines: int = 0

    @property
    def id(self) -> str:
        return self.meta["id"]

    @property
    def title(self) -> str:
        value = self.meta.get("title")
        return "" if value is None else one_line(str(value))

    @property
    def status(self) -> str:
        return self.meta["status"]

    @property
    def priority(self) -> str:
        value = self.meta.get("priority")
        return value if value in PRIORITIES else "normal"

    @property
    def waiting_on(self) -> dict:
        value = self.meta.get("waiting_on")
        return value if isinstance(value, dict) else {}

    def time(self, key: str) -> datetime | None:
        return parse_time(self.meta.get(key))

    @property
    def primary_path(self) -> str | None:
        """The path of the primary workspace, with `~` expanded, as recorded."""
        workspaces = self.meta.get("workspaces")
        if not isinstance(workspaces, list):
            return None
        for entry in workspaces:
            if isinstance(entry, dict) and entry.get("primary") is True and entry.get("path"):
                return os.path.expanduser(str(entry["path"]))
        return None

    def set_time(self, key: str, value: datetime | None) -> None:
        self.meta[key] = format_time(value) if value is not None else None


def format_time(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def parse_time(value) -> datetime | None:
    """Accept what a person may write by hand: a string, a YAML timestamp or a date."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.astimezone()
    if isinstance(value, date):
        return datetime.combine(value, time()).astimezone()
    try:
        parsed = datetime.fromisoformat(str(value).strip())
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.astimezone()


def one_line(text: str | None) -> str:
    """NOW values and titles are single lines."""
    return " ".join((text or "").split())


def new_meta(
    initiative_id: str,
    title: str,
    *,
    type_: str,
    status: str,
    priority: str,
    created: datetime,
    tags: list[str],
    workspace: str | None,
) -> dict:
    stamp = format_time(created)
    return {
        "id": initiative_id,
        "title": title,
        "type": type_,
        "status": status,
        "priority": priority,
        "created": stamp,
        "updated": stamp,
        "last_resumed": stamp if status == "active" else None,
        "last_paused": stamp if status == "paused" else None,
        "waiting_on": None,
        "tags": tags,
        "workspaces": [{"path": workspace, "primary": True}] if workspace else [],
        "links": [],
    }


def parse(text: str) -> Initiative:
    """Parse an initiative file, or raise MalformedError saying why."""
    front, body_text = frontmatter.split(text)
    meta = frontmatter.load(front)
    if not isinstance(meta.get("id"), str) or not meta["id"].strip():
        raise MalformedError("the frontmatter has no id")
    if "status" not in meta or meta["status"] is None:
        raise MalformedError("the frontmatter has no status")
    if meta["status"] not in STATES:
        raise MalformedError(f"status {meta['status']!r} is not one of {', '.join(STATES)}")

    body = body_text.split("\n")
    now_at = next((j for j in range(len(body)) if _NOW_HEADING.fullmatch(body[j])), None)
    # Everything before NOW (or before the first other heading, when there is no
    # NOW) is the intro; the first `# ` line in it is the title heading.
    if now_at is None:
        intro_end = next(
            (
                j
                for j in range(len(body))
                if _HEADING.match(body[j]) and not _TITLE.fullmatch(body[j])
            ),
            len(body),
        )
    else:
        intro_end = now_at
    intro = body[:intro_end]
    title_at = next((j for j, line in enumerate(intro) if _TITLE.fullmatch(line)), None)
    if title_at is not None:
        if not one_line(str(meta.get("title") or "")):
            meta["title"] = one_line(_TITLE.fullmatch(intro[title_at]).group(1))
        del intro[title_at]

    init = Initiative(meta=meta, intro=_strip_blank_edges(intro))
    if now_at is None:
        init.tail = _strip_blank_edges(body[intro_end:])
        return init

    seen = set()
    blank_before = False
    j = now_at + 1
    while j < len(body) and not _HEADING.match(body[j]):
        line = body[j].rstrip()
        if not line.strip():
            blank_before = True
            j += 1
            continue
        init.now_lines += 1
        m = _FIELD.fullmatch(line)
        if m and m.group(1) not in seen:
            seen.add(m.group(1))
            init.now[m.group(1)] = one_line(m.group(2))
        else:
            # Keep one blank line between extra lines, so their Markdown stays intact.
            if blank_before and init.now_extra:
                init.now_extra.append("")
            init.now_extra.append(line)
        blank_before = False
        j += 1
    init.tail = _strip_blank_edges(body[j:])
    return init


def render(init: Initiative) -> str:
    """Render the file. Known keys keep their place; unknown keys pass through."""
    meta = dict(init.meta)
    for key, default in KNOWN_KEYS.items():
        if key not in meta:
            meta[key] = list(default) if isinstance(default, list) else default
    front = frontmatter.dump(meta)
    out = ["---", front.rstrip("\n"), "---", "", f"# {init.title}", ""]
    if init.intro:
        out += [init.intro, ""]
    out += ["## NOW", ""]
    for label in NOW_LABELS:
        value = one_line(init.now.get(label, ""))
        out += [f"**{label}:** {value}" if value else f"**{label}:**", ""]
    if init.now_extra:
        out += [*init.now_extra, ""]
    if init.tail:
        out += [init.tail, ""]
    return "\n".join(out)


def _strip_blank_edges(lines: list[str]) -> str:
    start, end = 0, len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return "\n".join(lines[start:end])


def invariant_problems(init: Initiative) -> list[str]:
    """What this initiative violates on its own (the single-active rule is store-wide)."""
    problems = []
    if init.status in ("paused", "waiting") and not init.now.get("Next"):
        problems.append(f"{init.id} is {init.status} without a next action")
    if init.status == "waiting" and not one_line(str(init.waiting_on.get("what") or "")):
        problems.append(f"{init.id} is waiting without saying on what")
    return problems
