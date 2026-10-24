"""Fixtures: a temporary store, an injectable clock, and a runner for the CLI."""

import builtins
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from wcm import cli, clock, model, prompt

TZ = timezone(timedelta(hours=-3))
START = datetime(2026, 9, 16, 9, 0, 0, tzinfo=TZ)


class FakeClock:
    def __init__(self):
        self.t = START

    def __call__(self) -> datetime:
        return self.t

    def advance(self, **delta) -> None:
        self.t += timedelta(**delta)


@dataclass
class Result:
    code: int
    out: str
    err: str


@pytest.fixture
def fake_clock(monkeypatch) -> FakeClock:
    c = FakeClock()
    monkeypatch.setattr(clock, "now", c)
    return c


@pytest.fixture
def hub(tmp_path, monkeypatch) -> Path:
    h = tmp_path / "hub"
    monkeypatch.setenv("WCM_HOME", str(h))
    monkeypatch.delenv("WCM_CD_FILE", raising=False)
    monkeypatch.setenv("COLUMNS", "100")
    monkeypatch.setenv("LINES", "40")
    return h


@pytest.fixture
def kb(hub) -> Path:
    return hub / "kbs" / "work"


@pytest.fixture
def run(hub, fake_clock, monkeypatch, capsys):
    """Run `wcm <argv>`. `answers` feeds the prompts and implies a terminal."""

    def _run(*argv, answers=None, tty=None) -> Result:
        interactive = (answers is not None) if tty is None else tty
        monkeypatch.setattr(prompt, "stdin_is_tty", lambda: interactive)
        feed = iter(answers or [])

        def fake_input(text=""):
            print(text, end="")
            try:
                return next(feed)
            except StopIteration:
                raise AssertionError("unexpected prompt") from None

        monkeypatch.setattr(builtins, "input", fake_input)
        code = cli.main([str(a) for a in argv])
        out, err = capsys.readouterr()
        return Result(code, out, err)

    return _run


def path_of(kb: Path, initiative_id: str, location: str = "initiatives") -> Path:
    return kb / location / initiative_id / f"{initiative_id}.md"


def load(kb: Path, initiative_id: str, location: str = "initiatives") -> model.Initiative:
    return model.parse(path_of(kb, initiative_id, location).read_text(encoding="utf-8"))


def checkpoints(kb: Path, initiative_id: str, location: str = "initiatives") -> list[Path]:
    base = kb / location / initiative_id / "checkpoints"
    return sorted(base.iterdir()) if base.is_dir() else []


def write_initiative(
    kb: Path,
    initiative_id: str,
    *,
    status: str = "paused",
    title: str = "Hand written",
    next_: str = "Do the thing",
    priority: str = "normal",
    extra_meta: str = "",
    last_paused: str = "null",
    last_resumed: str = "null",
    waiting_on: str = "null",
    workspaces: str = "[]",
    body_extra: str = "",
    location: str = "initiatives",
) -> Path:
    """Write an initiative file the way a person would."""
    path = path_of(kb, initiative_id, location)
    (path.parent / "checkpoints").mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
id: {initiative_id}
title: {title}
type: other
status: {status}
priority: {priority}
created: 2026-09-01T09:00:00-03:00
updated: 2026-09-01T09:00:00-03:00
last_resumed: {last_resumed}
last_paused: {last_paused}
waiting_on: {waiting_on}
tags: []
workspaces: {workspaces}
links: []
{extra_meta}---

# {title}

## NOW

**Focus:** {title}

**Stopped at:**

**Why it matters:**

**Important:**

**Next:** {next_}
{body_extra}""",
        encoding="utf-8",
    )
    return path


def note_path(kb: Path, note_id: str) -> Path:
    return kb / "notes" / f"{note_id}.md"


def write_note(
    kb: Path,
    note_id: str,
    *,
    title: str = "Hand written",
    tags: str = "[]",
    initiative: str = "null",
    created: str = "2026-09-01T09:00:00-03:00",
    body: str = "",
    text: str | None = None,
) -> Path:
    """Write a note file the way a person (or Obsidian) would."""
    path = note_path(kb, note_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    if text is None:
        text = f"""---
id: {note_id}
title: {title}
tags: {tags}
initiative: {initiative}
created: {created}
---

# {title}
{body}"""
    path.write_text(text, encoding="utf-8")
    return path
