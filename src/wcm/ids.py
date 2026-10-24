"""Initiative IDs: `INIT-0007`, also accepted as `init-7` or `7`."""

import re

_PREFIXED = re.compile(r"init-(\d+)", re.IGNORECASE)
_BARE = re.compile(r"\d+")
DIR_NAME = re.compile(r"INIT-(\d+)")


class InvalidId(ValueError):
    pass


def format_id(number: int) -> str:
    return f"INIT-{number:04d}"


def parse(text: str) -> str:
    """Return the canonical ID for any accepted form, or raise InvalidId."""
    t = text.strip()
    m = _PREFIXED.fullmatch(t) or _BARE.fullmatch(t)
    if not m:
        raise InvalidId(f"not an initiative ID: {text!r} (use INIT-0007, init-7 or 7)")
    number = int(m.group(1) if m.re is _PREFIXED else m.group(0))
    if number < 1:
        raise InvalidId(f"not an initiative ID: {text!r} (IDs start at 1)")
    return format_id(number)


def number(initiative_id: str) -> int:
    m = DIR_NAME.fullmatch(initiative_id)
    if not m:
        raise InvalidId(f"not a canonical initiative ID: {initiative_id!r}")
    return int(m.group(1))
