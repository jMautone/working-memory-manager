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

import yaml

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
_BOOL_TAG = "tag:yaml.org,2002:bool"
_NULL_TAG = "tag:yaml.org,2002:null"
_TIMESTAMP_TAG = "tag:yaml.org,2002:timestamp"


class _Loader(yaml.SafeLoader):
    """Read every plain scalar as text, except null and true/false.

    YAML 1.1 would turn a hand-written `9:30` into 570, `0123` into 83, `1.10`
    into 1.1 and `yes` into True, and rewrite them that way. Keeping them as
    text preserves what the person wrote; the tool only needs strings, lists,
    null and booleans.
    """


_Loader.yaml_implicit_resolvers = {
    first: [(tag, rx) for tag, rx in resolvers if tag == _NULL_TAG]
    for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
_Loader.add_implicit_resolver(
    _BOOL_TAG, re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"), list("tTfF")
)


class _Dumper(yaml.SafeDumper):
    """Write ISO timestamps plain, as people write them and Obsidian reads them."""


def _represent_str(dumper: yaml.SafeDumper, value: str):
    if dumper.resolve(yaml.ScalarNode, value, (True, False)) == _TIMESTAMP_TAG:
        return dumper.represent_scalar(_TIMESTAMP_TAG, value)
    return dumper.represent_str(value)


def _represent_datetime(dumper: yaml.SafeDumper, value: datetime):
    return dumper.represent_scalar(_TIMESTAMP_TAG, value.isoformat())


_Dumper.add_representer(str, _represent_str)
_Dumper.add_representer(datetime, _represent_datetime)


class MalformedError(ValueError):
    pass


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
    text = text.removeprefix("﻿").replace("\r\n", "\n")
    lines = text.split("\n")
    if not lines or lines[0].rstrip() != "---":
        raise MalformedError("the file does not start with a --- frontmatter line")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].rstrip() == "---")
    except StopIteration:
        raise MalformedError("the frontmatter has no closing --- line") from None
    try:
        meta = yaml.load("\n".join(lines[1:end]), Loader=_Loader)
    except Exception as e:  # PyYAML raises more than YAMLError on bad values
        raise MalformedError(f"the frontmatter is not valid YAML ({_first_line(e)})") from None
    if not isinstance(meta, dict):
        raise MalformedError("the frontmatter is not a mapping")
    if not isinstance(meta.get("id"), str) or not meta["id"].strip():
        raise MalformedError("the frontmatter has no id")
    if "status" not in meta or meta["status"] is None:
        raise MalformedError("the frontmatter has no status")
    if meta["status"] not in STATES:
        raise MalformedError(f"status {meta['status']!r} is not one of {', '.join(STATES)}")

    body = lines[end + 1 :]
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
    front = yaml.dump(
        meta,
        Dumper=_Dumper,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=float("inf"),
    )
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


def _first_line(error: Exception) -> str:
    text = str(error).strip()
    return text.splitlines()[0] if text else type(error).__name__


def invariant_problems(init: Initiative) -> list[str]:
    """What this initiative violates on its own (the single-active rule is store-wide)."""
    problems = []
    if init.status in ("paused", "waiting") and not init.now.get("Next"):
        problems.append(f"{init.id} is {init.status} without a next action")
    if init.status == "waiting" and not one_line(str(init.waiting_on.get("what") or "")):
        problems.append(f"{init.id} is waiting without saying on what")
    return problems
