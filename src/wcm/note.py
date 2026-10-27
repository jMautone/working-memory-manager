"""The note file: parse, render, match and touch. No filesystem, no clock.

A note is YAML frontmatter and a Markdown body that starts with `# <title>`.
Once written, a note belongs to the person: the only change WCM ever makes to
it is the value of `updated` after an edit.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from wcm import frontmatter, ids
from wcm.frontmatter import MalformedError
from wcm.model import format_time, one_line, parse_time

_TITLE = re.compile(r"#\s+(.*)")
_LINK = re.compile(r"\[\[\s*(init-\d+)\s*(?:\|[^\]]*)?\]\]|(init-\d+)", re.IGNORECASE)
_UPDATED = re.compile(r"updated:")


@dataclass
class Note:
    id: str
    title: str
    tags: list[str]
    initiative: str | None
    created: datetime | None
    body: str


def link_of(value) -> str | None:
    """The initiative ID a note links to: `[[INIT-0007]]`, `[[INIT-0007|alias]]` or `INIT-0007`."""
    if not isinstance(value, str):
        return None
    m = _LINK.fullmatch(value.strip())
    if not m:
        return None
    text = (m.group(1) or m.group(2)).upper()
    number = int(text.removeprefix("INIT-"))
    # Only the canonical spelling links, as Obsidian resolves it by file name.
    return text if number > 0 and ids.format_id(number) == text else None


def _tags(value) -> list[str]:
    if value is None:
        return []
    values = value if isinstance(value, list) else [value]
    return [t for t in (one_line(str(v)) for v in values if v is not None) if t]


def parse(text: str, file_id: str) -> Note:
    """Parse the note stored as `<file_id>.md`, or raise MalformedError saying why."""
    front, body = frontmatter.split(text)
    meta = frontmatter.load(front)
    note_id = meta.get("id")
    if note_id is None or not one_line(str(note_id)):
        raise MalformedError("the frontmatter has no id")
    note_id = one_line(str(note_id))
    if note_id != file_id:
        raise MalformedError(f"its id is {note_id!r} but its name says {file_id}")
    title = one_line(str(meta.get("title") or ""))
    if not title:
        heading = next((m for line in body.split("\n") if (m := _TITLE.fullmatch(line))), None)
        title = one_line(heading.group(1)) if heading else ""
    if not title:
        raise MalformedError("the note has no title (a title key or a # heading)")
    return Note(
        id=note_id,
        title=title,
        tags=_tags(meta.get("tags")),
        initiative=link_of(meta.get("initiative")),
        created=parse_time(meta.get("created")),
        body=body,
    )


def render_new(
    note_id: str, title: str, tags: list[str], initiative: str | None, created: datetime
) -> str:
    stamp = format_time(created)
    front = frontmatter.dump(
        {
            "id": note_id,
            "title": title,
            "tags": list(tags),
            "initiative": f"[[{initiative}]]" if initiative else None,
            "capture": None,
            "created": stamp,
            "updated": stamp,
        }
    )
    return f"---\n{front}---\n\n# {title}\n"


def _bare_tag(tag: str) -> str:
    return tag.strip().removeprefix("#").strip()


def normalize_tags(values: list[str] | None) -> list[str]:
    """Split on commas, trim, drop one leading `#`, drop empty and repeated tags."""
    out, seen = [], set()
    for value in values or []:
        for part in value.split(","):
            tag = _bare_tag(part)
            if tag and tag.casefold() not in seen:
                seen.add(tag.casefold())
                out.append(tag)
    return out


def matches(note: Note, terms: list[str], tags: list[str], initiative: str | None) -> bool:
    """Every term in the title, a tag or the body; every tag; the linked initiative."""
    fields = [note.title.casefold(), *(t.casefold() for t in note.tags), note.body.casefold()]
    for term in terms:
        needle = term.casefold()
        if not any(needle in f for f in fields):
            return False
    have = {_bare_tag(t).casefold() for t in note.tags}
    if any(_bare_tag(t).casefold() not in have for t in tags):
        return False
    return initiative is None or note.initiative == initiative


def prefilter(
    terms: list[str], tags: list[str], initiative: str | None
) -> Callable[[str], bool] | None:
    """A test on the casefolded raw file that only rejects notes `matches` would reject.

    The title and the tags are in the frontmatter and the body is the rest of
    the file, so whatever can match appears in the raw text.
    """
    needles = [t.casefold() for t in terms]
    needles += [_bare_tag(t).casefold() for t in tags]
    if initiative:
        needles.append(initiative.casefold())
    if not needles:
        return None
    return lambda raw: all(n in raw for n in needles)


def touch_updated(text: str, when: datetime) -> str:
    """Set `updated` in the frontmatter, leaving every other byte as it is.

    Works on lines, never through YAML, so comments, flow lists, a byte-order
    mark and `\\r\\n` line endings survive. Without an `updated:` line, one is
    added before the closing `---`.
    """
    lines = text.split("\n")
    if lines[0].removeprefix(frontmatter.BOM).rstrip() != "---":
        raise MalformedError("the file does not start with a --- frontmatter line")
    end = next((i for i in range(1, len(lines)) if lines[i].rstrip() == "---"), None)
    if end is None:
        raise MalformedError("the frontmatter has no closing --- line")
    stamp = format_time(when)
    for i in range(1, end):
        if _UPDATED.match(lines[i]):
            cr = "\r" if lines[i].endswith("\r") else ""
            lines[i] = f"updated: {stamp}{cr}"
            break
    else:
        cr = "\r" if lines[0].endswith("\r") else ""
        lines.insert(end, f"updated: {stamp}{cr}")
    return "\n".join(lines)
