"""The store on disk: the hub, the `work` knowledge base and its initiatives.

Every effect on the store lives here. Layout under the hub (`WCM_HOME`, or
`~/.wcm`):

    kbs/work/initiatives/<ID>/<ID>.md
    kbs/work/initiatives/<ID>/checkpoints/<timestamp>.md
    kbs/work/done/<ID>/...
    kbs/work/notes/<NOTE-ID>.md

Anything else in the knowledge base (`.obsidian/`, other files a person keeps
next to the initiatives or the notes) is never read or written.
"""

import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, tzinfo
from pathlib import Path

from wcm import checkpoint, ids, model, note

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


@dataclass
class NoteEntry:
    """A note and its file."""

    note: note.Note
    path: Path


def hub() -> Path:
    override = os.environ.get("WCM_HOME", "").strip()
    return Path(override).expanduser() if override else Path.home() / ".wcm"


class Store:
    def __init__(self, root: Path | None = None):
        self.root = root if root is not None else hub()
        self.kb = self.root / "kbs" / "work"
        self.notes = self.kb / "notes"

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

    def exists(self, initiative_id: str) -> bool:
        """Whether the initiative has a directory, in flight or done, readable or not."""
        return any((self.kb / location / initiative_id).is_dir() for location in LOCATIONS)

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

    # --- notes ---------------------------------------------------------------

    def _note_files(self):
        """Files directly in notes/ named `NOTE-<digits>.md`; anything else is not a note."""
        if not self.notes.is_dir():
            return
        for p in sorted(self.notes.iterdir()):
            if ids.NOTE_FILE.fullmatch(p.name) and p.is_file():
                yield p

    def next_note_id(self) -> str:
        """One more than the highest note file name, read from names only."""
        numbers = (int(ids.NOTE_FILE.fullmatch(p.name).group(1)) for p in self._note_files())
        return ids.format_note(max(numbers, default=0) + 1)

    def note_path(self, note_id: str) -> Path:
        return self.notes / f"{note_id}.md"

    def find_note_path(self, note_id: str) -> Path:
        """The file of a note, without reading it: a malformed note can still be opened."""
        path = self.note_path(note_id)
        if not path.is_file():
            raise NotFound(f"{note_id} was not found")
        return path

    def scan_notes(
        self, prefilter: Callable[[str], bool] | None = None
    ) -> tuple[list[NoteEntry], list[Problem]]:
        """The notes, parsed. With `prefilter`, only files whose casefolded text passes it."""
        entries, problems = [], []
        for path in self._note_files():
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as e:
                problems.append(Problem(path, f"cannot be read ({e})"))
                continue
            if prefilter is not None and not prefilter(text.casefold()):
                continue
            try:
                entries.append(NoteEntry(note.parse(text, path.name.removesuffix(".md")), path))
            except model.MalformedError as e:
                problems.append(Problem(path, str(e)))
        return entries, problems

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

    def create_note(self, note_id: str, text: str) -> Path:
        """Write a new note in full, never over an existing file."""
        path = self.note_path(note_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        try:
            with tmp.open("w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            if path.exists():
                raise FileExistsError(f"{self.relative(path)} already exists; nothing was saved")
            os.replace(tmp, path)
        finally:
            if tmp.exists():
                tmp.unlink()
        return path

    def replace_note(self, path: Path, text: str) -> None:
        _write_atomic(path, text)

    def done_directory(self, initiative_id: str) -> Path:
        return self.kb / "done" / initiative_id

    def move_to_done(self, entry: Entry) -> Entry:
        """Move the whole directory in one rename, or leave it where it was.

        A plain rename, never a copy: on Windows a directory another program is
        using cannot be renamed, and a copy-then-delete fallback would leave
        half of it in each place.
        """
        target = self.done_directory(entry.directory.name)
        if target.exists():
            raise FileExistsError(f"{self.relative(target)} already exists")
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.rename(entry.directory, target)
        except OSError as e:
            raise OSError(
                f"cannot move {self.relative(entry.directory)} to done/ ({e.strerror or e}); "
                "is a shell or another program using it? Nothing was changed"
            ) from None
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
