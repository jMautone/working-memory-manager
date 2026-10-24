"""Checkpoint files: naming and content. Pure: the caller passes the time."""

import re
from datetime import datetime

from wcm.model import format_time, one_line

TRIGGERS = ("pause", "switch", "done")
_NAME = re.compile(r"(\d{4}-\d{2}-\d{2}T\d{6})(?:-\d+)?\.md")
_NAME_FORMAT = "%Y-%m-%dT%H%M%S"


def file_name(when: datetime, existing: set[str]) -> str:
    """`YYYY-MM-DDTHHMMSS.md` in local time, with `-2`, `-3` on collision."""
    base = when.strftime(_NAME_FORMAT)
    name, n = f"{base}.md", 2
    while name in existing:
        name, n = f"{base}-{n}.md", n + 1
    return name


def time_of(name: str, tz) -> datetime | None:
    """The time encoded in a checkpoint file name, read in the time zone `tz`."""
    m = _NAME.fullmatch(name)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), _NAME_FORMAT).replace(tzinfo=tz)
    except ValueError:  # a name with an impossible date, made by hand
        return None


def is_checkpoint(name: str) -> bool:
    return _NAME.fullmatch(name) is not None


def render(when: datetime, trigger: str, now: dict) -> str:
    sections = (
        ("Focus", now.get("Focus")),
        ("Completed since previous checkpoint", ""),
        ("Incomplete work", now.get("Stopped at")),
        ("Discoveries", now.get("Important")),
        ("Open questions", ""),
        ("Next action", now.get("Next")),
    )
    out = [f"# Checkpoint {format_time(when)}", "", "Author: human", f"Trigger: {trigger}", ""]
    for heading, value in sections:
        out += [f"## {heading}", ""]
        if one_line(value):
            out += [one_line(value), ""]
    return "\n".join(out)
