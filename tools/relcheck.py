"""relcheck enforces the branch, PR title and version conventions of
docs/decisions/0001-versionado-y-releases.md. The pr-conventions workflow runs
it on every pull request to main, and release.yml runs it on every push to
main.

The decisions live in pure functions (versions, titles, branches, check_pr,
changelog_section, alpha_notes, stamp_pyproject). Only the command handlers at
the bottom read git and the filesystem.

Standard library only: it runs before the project is installed.

usage:
  python tools/relcheck.py pr --branch <head-ref> --title <title> [--base <ref>] [--root <dir>]
  python tools/relcheck.py merge [--rev <rev>] [--root <dir>]
  python tools/relcheck.py notes --version <version> [--rev <rev>] [--root <dir>]
  python tools/relcheck.py stamp --version <version> [--root <dir>]
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import NamedTuple, TextIO

# --- Versions ---------------------------------------------------------------


class ConventionError(Exception):
    """A convention is violated, or git failed: exit code 1."""


class Minor(NamedTuple):
    """A MAJOR.MINOR line. Each phase ships as one minor."""

    major: int
    minor: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}"


# PHASES maps F1..F4 of persistent-working-memory-plan.md §14 to their minor,
# in order. F4 ships 1.0.0. Keep it in sync with the table in
# docs/decisions/0001-versionado-y-releases.md.
PHASES = [Minor(0, 1), Minor(0, 2), Minor(0, 3), Minor(1, 0)]

_VERSION_RE = re.compile(
    r"^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-alpha\.([1-9][0-9]*))?$"
)


@dataclass(frozen=True)
class Version:
    """A release version: vMAJOR.MINOR.PATCH, optionally -alpha.N."""

    major: int
    minor: int
    patch: int
    alpha: int = 0  # 0 for a final release

    @classmethod
    def parse(cls, s: str) -> Version:
        """Parse "v0.1.0" or "v0.1.0-alpha.2"."""
        m = _VERSION_RE.fullmatch(s)
        if m is None:
            raise ConventionError(f"{s!r} is not a version: want vX.Y.Z or vX.Y.Z-alpha.N")
        return cls(int(m[1]), int(m[2]), int(m[3]), int(m[4] or 0))

    def __str__(self) -> str:
        s = f"v{self.major}.{self.minor}.{self.patch}"
        return s + f"-alpha.{self.alpha}" if self.alpha else s

    @property
    def is_alpha(self) -> bool:
        return self.alpha > 0

    @property
    def minor_of(self) -> Minor:
        return Minor(self.major, self.minor)

    @property
    def pep440(self) -> str:
        """The same version as Python packaging spells it: 0.1.0a2."""
        s = f"{self.major}.{self.minor}.{self.patch}"
        return s + f"a{self.alpha}" if self.alpha else s

    def key(self) -> tuple[int, int, int, int, int]:
        """SemVer order: v0.1.0-alpha.2 < v0.1.0 < v0.2.0-alpha.1."""
        # A pre-release sorts before its final.
        return (self.major, self.minor, self.patch, 0 if self.alpha else 1, self.alpha)


def open_minor(published: list[Version]) -> Minor:
    """The minor that merges to main publish into: the minor of the latest
    published alpha, or the phase after the latest final."""
    if not published:
        return PHASES[0]
    latest = max(published, key=Version.key)
    if latest.is_alpha:
        return latest.minor_of
    if latest.minor_of not in PHASES:
        raise ConventionError(f"latest version {latest} is not a phase minor (ADR 0001)")
    i = PHASES.index(latest.minor_of)
    if i + 1 == len(PHASES):
        raise ConventionError(
            f"{latest} closed the last phase in the table; extend PHASES and ADR 0001"
        )
    return PHASES[i + 1]


def _last_alpha(published: list[Version], m: Minor) -> int:
    return max((p.alpha for p in published if p.minor_of == m), default=0)


def next_alpha(published: list[Version]) -> Version:
    """The alpha the next change or fix publishes."""
    m = open_minor(published)
    return Version(m.major, m.minor, 0, _last_alpha(published, m) + 1)


def next_check(v: Version, published: list[Version]) -> None:
    """Raise unless v may be published next, given every version main
    already published."""
    if v.patch != 0:
        raise ConventionError(f"{v}: patch releases come from a vX.Y.x branch, not from main")
    m = open_minor(published)
    last = _last_alpha(published, m)
    following = Version(m.major, m.minor, 0, last + 1)
    if v in published:
        # Another PR published it first: say what to use instead.
        if v.is_alpha:
            raise ConventionError(f"{v} is already published; the next alpha is {following}")
        raise ConventionError(f"{v} is already published; the open minor is now {m}")
    if v.minor_of != m:
        raise ConventionError(f"{v} targets {v.minor_of}, but the open minor is {m}")
    if v.is_alpha:
        if v.alpha != last + 1:
            raise ConventionError(f"{v}: the next alpha of {m} is {following}")
    elif last == 0:
        raise ConventionError(f"{v}: a final needs at least one alpha of {m} published first")


# --- Titles -----------------------------------------------------------------

TITLE_TYPES = ("feat", "fix", "docs", "chore", "ci", "refactor", "test", "perf")
MAX_TITLE_LEN = 72  # the title without its version suffix

_TITLE_RE = re.compile(r"^([a-z]+)\(([^()]*)\)(!?): (.*)$")
_SUFFIX_RE = re.compile(r" \[([^\[\]]*)\]$")
_PR_NUMBER_RE = re.compile(r" \(#[0-9]+\)$")
_KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class Title:
    """A PR title: <type>(<scope>)[!]: <summary> [<version>]."""

    type: str
    scope: str
    summary: str
    breaking: bool = False
    version: Version | None = None  # None when the title has no suffix


def parse_title(s: str) -> Title:
    """Parse a PR title and check its format. A trailing " [...]" is always
    read as the version suffix, so a malformed version is an error and never
    silently becomes part of the summary."""
    version = None
    head = s
    if m := _SUFFIX_RE.search(s):
        try:
            version = Version.parse(m[1])
        except ConventionError as e:
            raise ConventionError(f"version suffix [{m[1]}]: {e}") from None
        head = s[: m.start()]
    if len(head) > MAX_TITLE_LEN:
        raise ConventionError(
            f"title is {len(head)} characters without the version suffix; "
            f"the limit is {MAX_TITLE_LEN}"
        )
    m = _TITLE_RE.fullmatch(head)
    if m is None:
        raise ConventionError(
            f"title {s!r} does not match <type>(<scope>)[!]: <summary> [<version>]"
        )
    type_, scope, bang, summary = m[1], m[2], m[3], m[4]
    if type_ not in TITLE_TYPES:
        raise ConventionError(f"type {type_!r} is not one of {', '.join(TITLE_TYPES)}")
    if not _KEBAB_RE.fullmatch(scope):
        raise ConventionError(f"scope {scope!r} must be non-empty kebab-case")
    if summary == "":
        raise ConventionError("summary is empty")
    if summary.strip() != summary:
        raise ConventionError(f"summary {summary!r} has leading or trailing spaces")
    if summary[0].isupper():
        raise ConventionError(f"summary {summary!r} must start in lowercase")
    if summary.endswith("."):
        raise ConventionError(f"summary {summary!r} must not end with a period")
    return Title(type_, scope, summary, bang == "!", version)


def subject_version(subject: str) -> Version | None:
    """The version a squash subject on main published,
    "<title> [vX.Y.Z] (#N)", or None when it has no suffix."""
    m = _SUFFIX_RE.search(_PR_NUMBER_RE.sub("", subject))
    if m is None:
        return None
    try:
        return Version.parse(m[1])
    except ConventionError as e:
        raise ConventionError(f"subject {subject!r}: {e}") from None


def published_versions(subjects: list[str]) -> list[Version]:
    """The versions the given subjects of main published."""
    return [v for s in subjects if (v := subject_version(s)) is not None]


# --- Branches ---------------------------------------------------------------


class Kind(Enum):
    CHANGE = "change"  # vX.Y/<change>: publishes an alpha
    FIX = "fix"  # fix/<slug>: publishes an alpha
    RELEASE = "release"  # release/vX.Y.0: publishes a final
    PLAIN = "plain"  # chore|docs|ci|refactor|test/<slug>: publishes nothing
    DEPENDABOT = "dependabot"  # dependabot/**: publishes nothing


@dataclass(frozen=True)
class Branch:
    kind: Kind
    prefix: str = ""  # PLAIN: chore, docs, ci, refactor or test
    minor: Minor | None = None  # CHANGE: the minor of the change's phase
    change: str = ""  # CHANGE: the OpenSpec change name
    release: Version | None = None  # RELEASE: the final it publishes

    @property
    def publishes(self) -> bool:
        return self.kind in (Kind.CHANGE, Kind.FIX, Kind.RELEASE)


_CHANGE_BRANCH_RE = re.compile(r"^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)/([a-z0-9]+(?:-[a-z0-9]+)*)$")
_SLUG_BRANCH_RE = re.compile(r"^(fix|chore|docs|ci|refactor|test)/([a-z0-9]+(?:-[a-z0-9]+)*)$")
_RELEASE_BRANCH_RE = re.compile(r"^release/(.*)$")
_ARCHIVED_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}-(.+)$")


def parse_branch(s: str) -> Branch:
    """Classify a head branch name."""
    if m := _CHANGE_BRANCH_RE.fullmatch(s):
        return Branch(Kind.CHANGE, minor=Minor(int(m[1]), int(m[2])), change=m[3])
    if m := _SLUG_BRANCH_RE.fullmatch(s):
        if m[1] == "fix":
            return Branch(Kind.FIX)
        return Branch(Kind.PLAIN, prefix=m[1])
    if m := _RELEASE_BRANCH_RE.fullmatch(s):
        try:
            v = Version.parse(m[1])
        except ConventionError:
            v = None
        if v is None or v.is_alpha or v.patch != 0:
            raise ConventionError(f"branch {s!r}: a release branch is release/vX.Y.0")
        return Branch(Kind.RELEASE, release=v)
    if s.startswith("dependabot/"):
        return Branch(Kind.DEPENDABOT)
    raise ConventionError(
        f"branch {s!r} matches no allowed pattern: vX.Y/<change>, fix/<slug>, "
        "release/vX.Y.0, chore|docs|ci|refactor|test/<slug> (see CONTRIBUTING.md)"
    )


def archived_as(directory: str, change: str) -> bool:
    """Whether directory, a name under openspec/changes/archive, is the
    archive of change. OpenSpec names archives YYYY-MM-DD-<change>, so
    "2026-09-30-shell-integration" archives "shell-integration" and not
    "integration"."""
    m = _ARCHIVED_RE.fullmatch(directory)
    return m is not None and m[1] == change


# --- The pull request check -------------------------------------------------


@dataclass(frozen=True)
class Facts:
    """What check_pr needs from the repository besides branch and title."""

    published: tuple[Version, ...] = ()  # versions already published on main
    change_exists: bool = False  # CHANGE: openspec/changes/<change>/, archived or not
    changelog_section: bool = False  # RELEASE: a non-empty "## [X.Y.0]" section


def check_pr(b: Branch, t: Title, f: Facts) -> tuple[Version | None, list[str]]:
    """Validate a pull request against ADR 0001. Return the version the merge
    publishes (None if none) and every violation found."""
    errs: list[str] = []
    published = list(f.published)

    if b.kind is Kind.CHANGE:
        if t.scope != b.change:
            errs.append(f"scope {t.scope!r} must be the change name {b.change!r}")
        if not f.change_exists:
            errs.append(f"openspec/changes/{b.change}/ does not exist, archived or not")
    elif b.kind is Kind.FIX:
        if t.type != "fix":
            errs.append(f"a fix/ branch needs type fix, not {t.type!r}")
    elif b.kind is Kind.RELEASE:
        if t.type != "chore" or t.scope != "release":
            errs.append(f"a release/ branch needs chore(release), not {t.type}({t.scope})")
        if not f.changelog_section:
            errs.append(
                f'CHANGELOG.md has no "## [{str(b.release)[1:]}]" section with release notes'
            )
    elif b.kind is Kind.PLAIN:
        if t.type != b.prefix:
            errs.append(f"a {b.prefix}/ branch needs type {b.prefix}, not {t.type!r}")

    v = t.version
    if not b.publishes and v is not None:
        errs.append(f"this branch does not publish; remove the version suffix [{v}]")
    elif b.publishes and v is None:
        errs.append(f'this branch publishes; end the title with " [{_suggestion(b, published)}]"')
    elif b.publishes and v is not None:
        if b.kind is Kind.CHANGE and (not v.is_alpha or v.minor_of != b.minor):
            errs.append(f"a v{b.minor}/ branch publishes an alpha of {b.minor}, not {v}")
        elif b.kind is Kind.FIX and not v.is_alpha:
            errs.append(f"a fix/ branch publishes an alpha, not {v}")
        elif b.kind is Kind.RELEASE and v != b.release:
            errs.append(f"release/{b.release} publishes {b.release}, not {v}")
        try:
            next_check(v, published)
        except ConventionError as e:
            errs.append(str(e))

    if errs:
        return None, errs
    return v, []


def _suggestion(b: Branch, published: list[Version]) -> str:
    """The version a publishing branch should put in its title."""
    if b.kind is Kind.RELEASE:
        return str(b.release)
    try:
        return str(next_alpha(published))
    except ConventionError:
        return "vX.Y.0-alpha.N"


# --- Release notes ----------------------------------------------------------


def changelog_section(content: str, v: Version) -> str | None:
    """The body of the "## [X.Y.Z]" section of a Keep a Changelog file,
    without its heading and without a trailing "---" separator. None when the
    section does not exist or is empty: a final needs release notes."""
    heading = f"## [{str(v)[1:]}]"
    lines = content.replace("\r\n", "\n").split("\n")
    start = None
    end = len(lines)
    for i, line in enumerate(lines):
        if start is None:
            if line == heading or line.startswith(heading + " "):
                start = i + 1
            continue
        if line.startswith("## "):
            end = i
            break
    if start is None:
        return None
    body = "\n".join(lines[start:end]).strip()
    body = body.removesuffix("---").strip()
    return body or None


_NOTE_GROUPS = (
    ("Features", re.compile(r"^feat(\([^)]*\))?!?:")),
    ("Fixes", re.compile(r"^fix(\([^)]*\))?!?:")),
)


def alpha_notes(subjects: list[str]) -> str:
    """The release notes of an alpha: the titles merged since the previous
    published version, grouped into Features, Fixes and Other, oldest first.
    subjects are newest first and start at the alpha's own commit."""
    merged: list[str] = []
    for i, s in enumerate(subjects):
        if i > 0 and subject_version(s) is not None:
            break
        if s:
            merged.append(s)
    merged.reverse()

    groups: dict[str, list[str]] = {"Features": [], "Fixes": [], "Other": []}
    for s in merged:
        name = next((n for n, r in _NOTE_GROUPS if r.match(s)), "Other")
        groups[name].append(s)
    parts = [
        f"### {name}\n\n" + "\n".join(f"- {s}" for s in items)
        for name, items in groups.items()
        if items
    ]
    return "\n\n".join(parts)


# --- Stamping ---------------------------------------------------------------

_TABLE_RE = re.compile(r"^\s*\[")
_PROJECT_TABLE_RE = re.compile(r"^\s*\[project\]\s*(#.*)?$")
_VERSION_LINE_RE = re.compile(r'^(\s*version\s*=\s*)"[^"]*"(.*)$')


def stamp_pyproject(content: str, v: Version) -> str:
    """Rewrite the static version of [project] in pyproject.toml to v, in
    PEP 440 form. The release injects the version this way, so the source
    keeps a placeholder and the title stays the single source of truth."""
    lines = content.split("\n")
    in_project = False
    for i, line in enumerate(lines):
        if _TABLE_RE.match(line):
            in_project = bool(_PROJECT_TABLE_RE.match(line))
            continue
        if in_project and (m := _VERSION_LINE_RE.match(line)):
            lines[i] = f'{m[1]}"{v.pep440}"{m[2]}'
            stamped = "\n".join(lines)
            try:
                project = tomllib.loads(stamped).get("project", {})
            except tomllib.TOMLDecodeError as e:
                raise ConventionError(f"pyproject.toml: {e}") from None
            if project.get("version") != v.pep440:
                break
            return stamped
    raise ConventionError(
        'pyproject.toml needs a static version = "..." in [project] for the '
        "release to stamp (see CONTRIBUTING.md, Releases)"
    )


# --- Commands: the only part that touches git and the filesystem -----------


def _git(root: str, *args: str) -> str:
    try:
        r = subprocess.run(
            ["git", "-C", root, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError as e:
        raise ConventionError(f"git {' '.join(args)}: {e}") from None
    if r.returncode != 0:
        raise ConventionError(
            f"git {' '.join(args)}: exit status {r.returncode}: {r.stderr.strip()}"
        )
    return r.stdout


def _git_subjects(root: str, rev: str) -> list[str]:
    return _git(root, "log", "--format=%s", rev).rstrip("\n").split("\n")


def _read_changelog(root: str) -> str:
    """CHANGELOG.md, or "" when the file does not exist."""
    path = Path(root, "CHANGELOG.md")
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _change_exists(root: str, change: str) -> bool:
    """Whether openspec/changes/<change>/ or its archive exists."""
    changes = Path(root, "openspec", "changes")
    if change != "archive" and (changes / change).is_dir():
        return True
    archive = changes / "archive"
    if not archive.is_dir():
        return False
    return any(e.is_dir() and archived_as(e.name, change) for e in archive.iterdir())


def _no_notes(v: Version) -> ConventionError:
    return ConventionError(f'CHANGELOG.md has no "## [{str(v)[1:]}]" section with release notes')


def cmd_pr(a: argparse.Namespace, out: TextIO) -> None:
    errs: list[str] = []
    b = t = None
    try:
        b = parse_branch(a.branch)
    except ConventionError as e:
        errs.append(str(e))
    try:
        t = parse_title(a.title)
    except ConventionError as e:
        errs.append(str(e))
    if b is None or t is None:
        raise ConventionError("\n".join(errs))

    published = published_versions(_git_subjects(a.root, a.base))
    change_exists = b.kind is Kind.CHANGE and _change_exists(a.root, b.change)
    has_section = b.kind is Kind.RELEASE and (
        changelog_section(_read_changelog(a.root), b.release) is not None
    )
    v, errs = check_pr(b, t, Facts(tuple(published), change_exists, has_section))
    if errs:
        raise ConventionError("\n".join(errs))
    print(f"ok: publishes {v or 'nothing'}", file=out)


def cmd_merge(a: argparse.Namespace, out: TextIO) -> None:
    subject = _git(a.root, "log", "-1", "--format=%s", a.rev).strip()
    v = subject_version(subject)
    if v is None:
        return  # no suffix: the commit publishes nothing
    # Everything main published before this commit. On a re-run after a
    # partial failure the commit itself is excluded, so the check still passes.
    next_check(v, published_versions(_git_subjects(a.root, a.rev + "^")))
    if not v.is_alpha and changelog_section(_read_changelog(a.root), v) is None:
        raise _no_notes(v)
    # A tag already on this commit means an earlier run got this far.
    try:
        tagged = _git(a.root, "rev-parse", "-q", "--verify", f"refs/tags/{v}^{{commit}}")
    except ConventionError:
        tagged = None
    if tagged is not None:
        commit = _git(a.root, "rev-parse", a.rev + "^{commit}")
        if tagged.strip() != commit.strip():
            raise ConventionError(f"tag {v} already exists on another commit")
    print(v, file=out)


def cmd_notes(a: argparse.Namespace, out: TextIO) -> None:
    v = Version.parse(a.version)
    if not v.is_alpha:
        body = changelog_section(_read_changelog(a.root), v)
        if body is None:
            raise _no_notes(v)
        print(body, file=out)
        return
    # An alpha's notes come from the merged titles, never from CHANGELOG.md.
    subjects = _git_subjects(a.root, a.rev)
    if subject_version(subjects[0]) != v:
        raise ConventionError(f"{a.rev} is not the commit that publishes {v}")
    print(alpha_notes(subjects), file=out)


def cmd_stamp(a: argparse.Namespace, out: TextIO) -> None:
    v = Version.parse(a.version)
    path = Path(a.root, "pyproject.toml")
    if not path.exists():
        raise ConventionError(f"{path} does not exist")
    content = path.read_text(encoding="utf-8")
    path.write_text(stamp_pyproject(content, v), encoding="utf-8", newline="")
    print(v.pep440, file=out)


class _Parser(argparse.ArgumentParser):
    """An ArgumentParser that writes its errors to a given stream."""

    def __init__(self, *args, stderr: TextIO, **kwargs):
        super().__init__(*args, **kwargs)
        self._stderr = stderr

    def _print_message(self, message: str, file: TextIO | None = None) -> None:
        if message:
            self._stderr.write(message)


def _parser(stderr: TextIO) -> argparse.ArgumentParser:
    p = _Parser(prog="relcheck", stderr=stderr, add_help=False)
    sub = p.add_subparsers(dest="command", required=True, parser_class=_Parser, metavar="<command>")

    def command(name: str, handler, help: str) -> argparse.ArgumentParser:
        c = sub.add_parser(name, help=help, stderr=stderr, add_help=False)
        c.set_defaults(handler=handler)
        c.add_argument("--root", default=".", help="repository root")
        return c

    c = command("pr", cmd_pr, "Check a pull request. Prints the version its merge publishes.")
    c.add_argument("--branch", required=True, help="head branch of the pull request")
    c.add_argument("--title", required=True, help="title of the pull request")
    c.add_argument(
        "--base",
        default="origin/main",
        help="ref whose history holds the published versions",
    )

    c = command(
        "merge",
        cmd_merge,
        "Read the version a squash commit on main publishes and re-check it. "
        "Prints the version, or nothing when the commit publishes nothing.",
    )
    c.add_argument("--rev", default="HEAD", help="the squash commit pushed to main")

    c = command(
        "notes",
        cmd_notes,
        "Print the release notes: the CHANGELOG.md section of a final, "
        "or the titles merged since the previous version for an alpha.",
    )
    c.add_argument("--version", required=True, help="the version being published")
    c.add_argument("--rev", default="HEAD", help="the commit that publishes it (alpha)")

    c = command(
        "stamp",
        cmd_stamp,
        "Write the version into pyproject.toml, in PEP 440 form, before building.",
    )
    c.add_argument("--version", required=True, help="the version being published")
    return p


def main(argv: list[str], stdout: TextIO = sys.stdout, stderr: TextIO = sys.stderr) -> int:
    """Run a command and return the exit code: 0 ok, 1 a convention is
    violated or git failed, 2 usage error."""
    parser = _parser(stderr)
    try:
        a = parser.parse_args(argv)
    except SystemExit as e:
        if e.code != 0:
            return 2
        return 0
    try:
        a.handler(a, stdout)
    except ConventionError as e:
        for line in str(e).split("\n"):
            print(f"relcheck: {line}", file=stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
