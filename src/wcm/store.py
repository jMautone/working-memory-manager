"""The store on disk: the hub, the `work` knowledge base and its initiatives.

Every effect on the store lives here. Layout under the hub (`WCM_HOME`, or
`~/.wcm`):

    kbs/work/initiatives/<ID>/<ID>.md
    kbs/work/initiatives/<ID>/checkpoints/<timestamp>.md
    kbs/work/done/<ID>/...

Anything else in the knowledge base (`.obsidian/`, notes a person keeps next
to the initiatives) is never read or written.
"""

import os
import shutil
from dataclasses import dataclass
from datetime import datetime, tzinfo
from pathlib import Path

from wcm import checkpoint, ids, model

LOCATIONS = ("initiatives", "done")


class NotFound(LookupError):
    pass


@dataclass
class Problem:
    """A file the store could not use, with the reason."""

    path: Path
    reason: str


@dataclass
class Entry:
    """An initiative and where it lives."""

    initiative: model.Initiative
    path: Path
    location: str

    @property
    def directory(self) -> Path:
        return self.path.parent


def hub() -> Path:
    override = os.environ.get("WCM_HOME", "").strip()
    return Path(override).expanduser() if override else Path.home() / ".wcm"


class Store:
    def __init__(self, root: Path | None = None):
        self.root = root if root is not None else hub()
        self.kb = self.root / "kbs" / "work"

    def relative(self, path: Path) -> str:
        """A path inside the knowledge base, for messages, with forward slashes."""
        try:
            return path.relative_to(self.kb).as_posix()
        except ValueError:
            return str(path)

    # --- reading -----------------------------------------------------------

    def _candidates(self):
        for location in LOCATIONS:
            base = self.kb / location
            if not base.is_dir():
                continue
            for d in sorted(base.iterdir()):
                if d.is_dir() and ids.DIR_NAME.fullmatch(d.name):
                    yield location, d

    def _load(self, location: str, directory: Path) -> Entry:
        path = directory / f"{directory.name}.md"
        if not path.is_file():
            raise model.MalformedError(f"missing {directory.name}.md")
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            raise model.MalformedError(f"cannot be read ({e})") from None
        init = model.parse(text)
        if init.id != directory.name:
            raise model.MalformedError(f"its id is {init.id!r} but its name says {directory.name}")
        return Entry(init, path, location)

    def scan(self) -> tuple[list[Entry], list[Problem]]:
        entries, problems = [], []
        for location, directory in self._candidates():
            try:
                entries.append(self._load(location, directory))
            except model.MalformedError as e:
                problems.append(Problem(directory / f"{directory.name}.md", str(e)))
        return entries, problems

    def find(self, initiative_id: str) -> Entry:
        """Raise NotFound, or MalformedError naming the file."""
        for location in LOCATIONS:
            directory = self.kb / location / initiative_id
            if directory.is_dir():
                try:
                    return self._load(location, directory)
                except model.MalformedError as e:
                    rel = self.relative(directory / f"{initiative_id}.md")
                    raise model.MalformedError(f"{rel}: {e}") from None
        raise NotFound(f"{initiative_id} was not found")

    def next_id(self) -> str:
        highest = 0
        for location in LOCATIONS:
            base = self.kb / location
            if base.is_dir():
                for d in base.iterdir():
                    m = ids.DIR_NAME.fullmatch(d.name)
                    if m and d.is_dir():
                        highest = max(highest, int(m.group(1)))
        return ids.format_id(highest + 1)

    def latest_checkpoint(self, entry: Entry, tz: tzinfo) -> datetime | None:
        names = self._checkpoint_names(entry.directory)
        times = [t for t in (checkpoint.time_of(n, tz) for n in names) if t]
        return max(times, default=None)

    def checkpoint_count(self, entry: Entry) -> int:
        return len(self._checkpoint_names(entry.directory))

    @staticmethod
    def _checkpoint_names(directory: Path) -> set[str]:
        base = directory / "checkpoints"
        if not base.is_dir():
            return set()
        return {p.name for p in base.iterdir() if checkpoint.is_checkpoint(p.name)}

    # --- writing -----------------------------------------------------------

    def create(self, init: model.Initiative) -> Entry:
        directory = self.kb / "initiatives" / init.id
        (directory / "checkpoints").mkdir(parents=True, exist_ok=False)
        entry = Entry(init, directory / f"{init.id}.md", "initiatives")
        _write_atomic(entry.path, model.render(init))
        return entry

    def save(self, entry: Entry, when: datetime) -> None:
        entry.initiative.set_time("updated", when)
        _write_atomic(entry.path, model.render(entry.initiative))

    def write_checkpoint(self, entry: Entry, when: datetime, trigger: str) -> Path:
        base = entry.directory / "checkpoints"
        base.mkdir(parents=True, exist_ok=True)
        existing = {p.name for p in base.iterdir()}
        while True:
            path = base / checkpoint.file_name(when, existing)
            try:
                # Exclusive create: an existing checkpoint is never overwritten.
                with path.open("x", encoding="utf-8", newline="\n") as f:
                    f.write(checkpoint.render(when, trigger, entry.initiative.now))
                return path
            except FileExistsError:
                existing.add(path.name)

    def move_to_done(self, entry: Entry) -> Entry:
        target = self.kb / "done" / entry.directory.name
        if target.exists():
            raise FileExistsError(f"{self.relative(target)} already exists")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(entry.directory), str(target))
        return Entry(entry.initiative, target / entry.path.name, "done")


def _write_atomic(path: Path, text: str) -> None:
    """Write the whole file or nothing: temp file in the same directory, then replace."""
    tmp = path.with_name(path.name + ".tmp")
    try:
        with tmp.open("w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()
