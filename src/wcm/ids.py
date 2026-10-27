"""IDs: initiatives `INIT-0007` (also `init-7` or `7`), notes `NOTE-0012` (also `note-12` or `12`)."""

import re

_PREFIXED = re.compile(r"init-(\d+)", re.IGNORECASE)
_NOTE_PREFIXED = re.compile(r"note-(\d+)", re.IGNORECASE)
_BARE = re.compile(r"\d+")
DIR_NAME = re.compile(r"INIT-(\d+)")
NOTE_FILE = re.compile(r"NOTE-(\d+)\.md")


class InvalidId(ValueError):
    pass


def format_id(number: int) -> str:
    return f"INIT-{number:04d}"


def format_note(number: int) -> str:
    return f"NOTE-{number:04d}"


def _number(text: str, prefixed: re.Pattern) -> int | None:
    t = text.strip()
    m = prefixed.fullmatch(t) or _BARE.fullmatch(t)
    if not m:
        return None
    return int(m.group(1) if m.re is prefixed else m.group(0))


def parse(text: str) -> str:
    """Return the canonical ID for any accepted form, or raise InvalidId."""
    number = _number(text, _PREFIXED)
    if number is None:
        raise InvalidId(f"not an initiative ID: {text!r} (use INIT-0007, init-7 or 7)")
    if number < 1:
        raise InvalidId(f"not an initiative ID: {text!r} (IDs start at 1)")
    return format_id(number)


def parse_note(text: str) -> str:
    """Return the canonical note ID for any accepted form, or raise InvalidId."""
    number = _number(text, _NOTE_PREFIXED)
    if number is None:
        raise InvalidId(f"not a note ID: {text!r} (use NOTE-0012, note-12 or 12)")
    if number < 1:
        raise InvalidId(f"not a note ID: {text!r} (IDs start at 1)")
    return format_note(number)


def number(initiative_id: str) -> int:
    m = DIR_NAME.fullmatch(initiative_id)
    if not m:
        raise InvalidId(f"not a canonical initiative ID: {initiative_id!r}")
    return int(m.group(1))
