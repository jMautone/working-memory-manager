"""YAML frontmatter shared by initiatives and notes: cut it out, read it, write it.

No filesystem, no clock. A frontmatter block is a `---` first line, YAML, and
a closing `---` line; the rest of the file is the body.
"""

import re
from datetime import datetime

import yaml

_BOOL_TAG = "tag:yaml.org,2002:bool"
_NULL_TAG = "tag:yaml.org,2002:null"
_STR_TAG = "tag:yaml.org,2002:str"
_TIMESTAMP_TAG = "tag:yaml.org,2002:timestamp"
BOM = "﻿"


class MalformedError(ValueError):
    pass


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
    """Write ISO timestamps plain and `[[links]]` double-quoted, as Obsidian does."""


def _represent_str(dumper: yaml.SafeDumper, value: str):
    if value.startswith("[["):
        return dumper.represent_scalar(_STR_TAG, value, style='"')
    if dumper.resolve(yaml.ScalarNode, value, (True, False)) == _TIMESTAMP_TAG:
        return dumper.represent_scalar(_TIMESTAMP_TAG, value)
    return dumper.represent_str(value)


def _represent_datetime(dumper: yaml.SafeDumper, value: datetime):
    return dumper.represent_scalar(_TIMESTAMP_TAG, value.isoformat())


_Dumper.add_representer(str, _represent_str)
_Dumper.add_representer(datetime, _represent_datetime)


def split(text: str) -> tuple[str, str]:
    """Return the frontmatter YAML and the body, or raise MalformedError.

    A byte-order mark is dropped and `\\r\\n` read as `\\n`, so files saved
    by Notepad read like any other.
    """
    lines = text.removeprefix(BOM).replace("\r\n", "\n").split("\n")
    if lines[0].rstrip() != "---":
        raise MalformedError("the file does not start with a --- frontmatter line")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].rstrip() == "---")
    except StopIteration:
        raise MalformedError("the frontmatter has no closing --- line") from None
    return "\n".join(lines[1:end]), "\n".join(lines[end + 1 :])


def load(front: str) -> dict:
    """Read the frontmatter YAML as a mapping, or raise MalformedError."""
    try:
        meta = yaml.load(front, Loader=_Loader)
    except Exception as e:  # PyYAML raises more than YAMLError on bad values
        raise MalformedError(f"the frontmatter is not valid YAML ({_first_line(e)})") from None
    if not isinstance(meta, dict):
        raise MalformedError("the frontmatter is not a mapping")
    return meta


def dump(meta: dict) -> str:
    """The YAML of a frontmatter block, keys in the given order, ending in `\\n`."""
    return yaml.dump(
        meta,
        Dumper=_Dumper,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=float("inf"),
    )


def _first_line(error: Exception) -> str:
    text = str(error).strip()
    return text.splitlines()[0] if text else type(error).__name__
