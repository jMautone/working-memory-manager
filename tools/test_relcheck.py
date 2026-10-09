import io
import os
import subprocess
from pathlib import Path

import pytest

import relcheck
from relcheck import (
    Branch,
    ConventionError,
    Facts,
    Kind,
    Minor,
    Title,
    Version,
    alpha_notes,
    archived_as,
    changelog_section,
    check_pr,
    next_alpha,
    next_check,
    open_minor,
    parse_branch,
    parse_title,
    published_versions,
    stamp_pyproject,
)


def versions(*ss: str) -> list[Version]:
    return [Version.parse(s) for s in ss]


# --- Versions ---------------------------------------------------------------


@pytest.mark.parametrize(
    "s, want",
    [
        ("v0.1.0", Version(0, 1, 0)),
        ("v0.1.0-alpha.1", Version(0, 1, 0, 1)),
        ("v1.0.0", Version(1, 0, 0)),
        ("v10.20.3", Version(10, 20, 3)),
        ("v0.2.0-alpha.12", Version(0, 2, 0, 12)),
    ],
)
def test_parse_version(s, want):
    assert Version.parse(s) == want
    assert str(want) == s


@pytest.mark.parametrize(
    "s",
    ["", "0.1.0", "v0.1", "v01.1.0", "v0.1.0-alpha.0", "v0.1.0-beta.1", "v0.1.0-alpha", "v0.1.0 "],
)
def test_parse_version_errors(s):
    with pytest.raises(ConventionError):
        Version.parse(s)


def test_order():
    ordered = versions(
        "v0.1.0-alpha.1", "v0.1.0-alpha.2", "v0.1.0-alpha.10", "v0.1.0",
        "v0.2.0-alpha.1", "v0.3.0", "v1.0.0-alpha.1", "v1.0.0",
    )  # fmt: skip
    assert sorted(reversed(ordered), key=Version.key) == ordered


def test_pep440():
    assert Version.parse("v0.1.0-alpha.2").pep440 == "0.1.0a2"
    assert Version.parse("v1.0.0").pep440 == "1.0.0"


@pytest.mark.parametrize(
    "published, want",
    [
        ([], Minor(0, 1)),
        (["v0.1.0-alpha.1"], Minor(0, 1)),
        (["v0.1.0-alpha.1", "v0.1.0"], Minor(0, 2)),
        (["v0.1.0", "v0.1.0-alpha.1"], Minor(0, 2)),  # input order does not matter
        (["v0.3.0-alpha.3", "v0.3.0"], Minor(1, 0)),  # F4 ships 1.0
    ],
)
def test_open_minor(published, want):
    assert open_minor(versions(*published)) == want


@pytest.mark.parametrize("published", [["v1.0.0"], ["v0.5.0"]])
def test_open_minor_errors(published):
    with pytest.raises(ConventionError):
        open_minor(versions(*published))


@pytest.mark.parametrize(
    "published, want",
    [
        ([], "v0.1.0-alpha.1"),
        (["v0.1.0-alpha.1", "v0.1.0-alpha.2"], "v0.1.0-alpha.3"),
        (["v0.1.0-alpha.1", "v0.1.0"], "v0.2.0-alpha.1"),
    ],
)
def test_next_alpha(published, want):
    assert str(next_alpha(versions(*published))) == want


@pytest.mark.parametrize(
    "v, published, want_err",
    [
        ("v0.1.0-alpha.1", [], None),
        ("v0.1.0-alpha.2", ["v0.1.0-alpha.1"], None),
        ("v0.1.0", ["v0.1.0-alpha.1"], None),
        ("v0.2.0-alpha.1", ["v0.1.0-alpha.1", "v0.1.0"], None),
        ("v1.0.0-alpha.1", ["v0.3.0-alpha.1", "v0.3.0"], None),
        # Two PRs raced for the same alpha: the second one must fail.
        (
            "v0.1.0-alpha.1",
            ["v0.1.0-alpha.1"],
            "already published; the next alpha is v0.1.0-alpha.2",
        ),
        ("v0.1.0", ["v0.1.0-alpha.1", "v0.1.0"], "already published; the open minor is now 0.2"),
        ("v0.1.0-alpha.3", ["v0.1.0-alpha.1"], "next alpha of 0.1 is v0.1.0-alpha.2"),
        ("v0.2.0-alpha.1", ["v0.1.0-alpha.1"], "open minor is 0.1"),
        ("v0.1.0-alpha.2", ["v0.1.0-alpha.1", "v0.1.0"], "open minor is 0.2"),
        ("v0.1.0", [], "at least one alpha"),
        ("v0.1.1", ["v0.1.0-alpha.1", "v0.1.0"], "vX.Y.x branch"),
        ("v0.4.0-alpha.1", ["v0.3.0-alpha.1", "v0.3.0"], "open minor is 1.0"),
    ],
)
def test_next_check(v, published, want_err):
    if want_err is None:
        next_check(Version.parse(v), versions(*published))
    else:
        with pytest.raises(ConventionError, match=want_err):
            next_check(Version.parse(v), versions(*published))


# --- Titles -----------------------------------------------------------------


def test_parse_title():
    t = parse_title(
        "feat(add-working-memory-layer)!: add wcm pause, resume and now [v0.1.0-alpha.1]"
    )
    assert t == Title(
        "feat",
        "add-working-memory-layer",
        "add wcm pause, resume and now",
        True,
        Version(0, 1, 0, 1),
    )
    t = parse_title("chore(ci): bump actions/checkout from 4 to 7")
    assert t.version is None and not t.breaking
    # The 72-character limit does not count the version suffix.
    parse_title("docs(x): " + "a" * 63 + " [v0.1.0-alpha.1]")


@pytest.mark.parametrize(
    "s, want",
    [
        ("add wcm now", "does not match"),
        ("feat: add wcm now", "does not match"),
        ("feat(): add wcm now", "kebab-case"),
        ("feat(Now): add wcm now", "kebab-case"),
        ("feature(now): add wcm now", "is not one of"),
        ("feat(now): Add wcm now", "lowercase"),
        ("feat(now): add wcm now.", "period"),
        ("feat(now):  add wcm now", "leading or trailing spaces"),
        ("feat(now): add wcm now [0.1.0]", r"version suffix \[0.1.0\]"),
        ("feat(now): add wcm now [v0.1]", r"version suffix \[v0.1\]"),
        ("feat(now): add wcm now [wip]", r"version suffix \[wip\]"),
        ("docs(x): " + "a" * 64, "the limit is 72"),
    ],
)
def test_parse_title_errors(s, want):
    with pytest.raises(ConventionError, match=want):
        parse_title(s)


def test_published_versions():
    subjects = [
        "feat(inbox): add wcm capture [v0.1.0-alpha.2] (#6)",
        "chore(ci): bump actions/checkout from 4 to 7 (#5)",
        "feat(add-working-memory-layer): add wcm now [v0.1.0-alpha.1] (#3)",
        "docs: agregar el plan del Working Memory Layer (WCM)",
        "",
    ]
    assert published_versions(subjects) == versions("v0.1.0-alpha.2", "v0.1.0-alpha.1")
    # A malformed suffix on main must be an error, not be skipped.
    with pytest.raises(ConventionError):
        published_versions(["feat(x): y [v0.1] (#9)"])


# --- Branches ---------------------------------------------------------------


@pytest.mark.parametrize(
    "s, want",
    [
        (
            "v0.1/add-working-memory-layer",
            Branch(Kind.CHANGE, minor=Minor(0, 1), change="add-working-memory-layer"),
        ),
        ("v1.0/attention", Branch(Kind.CHANGE, minor=Minor(1, 0), change="attention")),
        ("fix/now-sort-order", Branch(Kind.FIX)),
        ("release/v0.1.0", Branch(Kind.RELEASE, release=Version(0, 1, 0))),
        ("chore/dependabot-config", Branch(Kind.PLAIN, prefix="chore")),
        ("ci/release-conventions", Branch(Kind.PLAIN, prefix="ci")),
        ("docs/contributing", Branch(Kind.PLAIN, prefix="docs")),
        ("refactor/render", Branch(Kind.PLAIN, prefix="refactor")),
        ("test/e2e-windows", Branch(Kind.PLAIN, prefix="test")),
        ("dependabot/github_actions/actions/checkout-7", Branch(Kind.DEPENDABOT)),
    ],
)
def test_parse_branch(s, want):
    assert parse_branch(s) == want


@pytest.mark.parametrize(
    "s",
    [
        "main",
        "v1/working-memory",  # no minor
        "v0.1.x",  # maintenance line, never a PR head to main
        "v0.1/Working_Memory",  # not kebab-case
        "v0.1/working-memory/",  # trailing slash
        "feat/inbox",  # features go through vX.Y/<change>
        "fix/",  # empty slug
        "release/v0.1.0-alpha.1",  # a release branch publishes a final
        "release/v0.1.1",  # patches come from vX.Y.x
        "release/0.1.0",
        "claude/some-session",
    ],
)
def test_parse_branch_errors(s):
    with pytest.raises(ConventionError):
        parse_branch(s)


def test_parse_branch_points_to_contributing():
    with pytest.raises(ConventionError, match="CONTRIBUTING.md"):
        parse_branch("feature/x")


@pytest.mark.parametrize(
    "directory, change, want",
    [
        ("2026-09-30-add-working-memory-layer", "add-working-memory-layer", True),
        ("2026-09-30-inbox-capture", "capture", False),
        ("2026-09-30-inbox-capture", "inbox", False),
        ("add-working-memory-layer", "add-working-memory-layer", False),
        ("2026-9-30-add-working-memory-layer", "add-working-memory-layer", False),
    ],
)
def test_archived_as(directory, change, want):
    assert archived_as(directory, change) is want


# --- The pull request check -------------------------------------------------

ALPHA1 = tuple(versions("v0.1.0-alpha.1"))


def check(branch: str, title: str, facts: Facts):
    return check_pr(parse_branch(branch), parse_title(title), facts)


@pytest.mark.parametrize(
    "branch, title, facts, publishes",
    [
        ("v0.1/add-working-memory-layer", "feat(add-working-memory-layer): add wcm now [v0.1.0-alpha.1]",
         Facts(change_exists=True), "v0.1.0-alpha.1"),
        ("fix/now-sort-order", "fix(now): sort by priority first [v0.1.0-alpha.2]",
         Facts(published=ALPHA1), "v0.1.0-alpha.2"),
        ("release/v0.1.0", "chore(release): close F1 [v0.1.0]",
         Facts(published=ALPHA1, changelog_section=True), "v0.1.0"),
        ("ci/release-conventions", "ci(release): add branch, title and release conventions",
         Facts(), None),
        ("dependabot/pip/pyyaml-6.1", "chore(deps): bump pyyaml from 6.0 to 6.1",
         Facts(published=ALPHA1), None),
    ],
)  # fmt: skip
def test_check_pr_valid(branch, title, facts, publishes):
    v, errs = check(branch, title, facts)
    assert errs == []
    assert (str(v) if v else None) == publishes


@pytest.mark.parametrize(
    "branch, title, facts, want",
    [
        ("v0.1/add-working-memory-layer", "feat(now): add wcm now [v0.1.0-alpha.1]",
         Facts(change_exists=True), "must be the change name 'add-working-memory-layer'"),
        ("v0.1/add-working-memory-layer", "feat(add-working-memory-layer): add wcm now [v0.1.0-alpha.1]",
         Facts(), "does not exist, archived or not"),
        ("v0.1/add-working-memory-layer", "feat(add-working-memory-layer): add wcm now",
         Facts(change_exists=True), 'end the title with " [v0.1.0-alpha.1]"'),
        ("v0.1/inbox", "feat(inbox): add wcm capture [v0.1.0-alpha.2]",
         Facts(change_exists=True), "next alpha of 0.1 is v0.1.0-alpha.1"),
        ("v0.2/workspaces", "feat(workspaces): add wcm workspace [v0.2.0-alpha.1]",
         Facts(change_exists=True, published=ALPHA1), "open minor is 0.1"),
        ("v0.1/add-working-memory-layer", "feat(add-working-memory-layer): add wcm now [v0.2.0-alpha.1]",
         Facts(change_exists=True), "publishes an alpha of 0.1"),
        ("v0.1/add-working-memory-layer", "feat(add-working-memory-layer): add wcm now [v0.1.0]",
         Facts(change_exists=True, published=ALPHA1), "publishes an alpha of 0.1"),
        # Two PRs took the same alpha; the second must update its title.
        ("v0.1/inbox", "feat(inbox): add wcm capture [v0.1.0-alpha.1]",
         Facts(change_exists=True, published=ALPHA1), "already published"),
        ("fix/now-sort-order", "feat(now): sort [v0.1.0-alpha.2]",
         Facts(published=ALPHA1), "needs type fix"),
        ("fix/now-sort-order", "fix(now): sort [v0.1.0]",
         Facts(published=ALPHA1), "publishes an alpha, not v0.1.0"),
        ("release/v0.1.0", "chore(release): close F1 [v0.1.0]",
         Facts(published=ALPHA1), 'no "## [0.1.0]" section'),
        ("release/v0.1.0", "chore(release): close F1 [v0.1.0]",
         Facts(changelog_section=True), "at least one alpha"),
        ("release/v0.1.0", "feat(release): close F1 [v0.1.0]",
         Facts(published=ALPHA1, changelog_section=True), "needs chore(release)"),
        ("ci/release-conventions", "ci(release): add conventions [v0.1.0-alpha.1]",
         Facts(), "does not publish; remove the version suffix"),
        ("ci/release-conventions", "docs(release): add conventions",
         Facts(), "needs type ci"),
        ("dependabot/github_actions/actions/checkout-7", "chore(ci): bump checkout [v0.1.0-alpha.2]",
         Facts(published=ALPHA1), "does not publish"),
    ],
)  # fmt: skip
def test_check_pr_invalid(branch, title, facts, want):
    v, errs = check(branch, title, facts)
    assert v is None
    assert want in "\n".join(errs)


def test_check_pr_reports_every_violation():
    _, errs = check("v0.1/add-working-memory-layer", "docs(now): add wcm now", Facts())
    assert len(errs) == 3  # wrong scope, missing change, missing version


# --- Release notes ----------------------------------------------------------

SAMPLE_CHANGELOG = """# Changelog

## [Unreleased]

### Added

- Something new.

## [0.1.0] — 2026-10-15

### Added

- `wcm now`.

### Fixed

- A bug.

---

## [0.1.01] — not a real version
"""


def test_changelog_section():
    want = "### Added\n\n- `wcm now`.\n\n### Fixed\n\n- A bug."
    assert changelog_section(SAMPLE_CHANGELOG, Version(0, 1, 0)) == want
    # CRLF checkouts read the same.
    assert changelog_section(SAMPLE_CHANGELOG.replace("\n", "\r\n"), Version(0, 1, 0)) == want
    for v in (Version(0, 2, 0), Version(0, 1, 0, 1), Version(0, 9, 0)):
        assert changelog_section(SAMPLE_CHANGELOG, v) is None


@pytest.mark.parametrize(
    "content",
    [
        "# Changelog\n\n## [0.1.0] — 2026-10-15\n\n## [Unreleased]\n\n- Something.\n",
        "# Changelog\n\n## [0.1.0] — 2026-10-15\n\n---\n\n## [0.0.1]\n",
        "# Changelog\n\n## [0.1.0]",
    ],
)
def test_changelog_section_rejects_empty_sections(content):
    # A final published with this file would get blank release notes.
    assert changelog_section(content, Version(0, 1, 0)) is None


def test_changelog_section_ignores_look_alike_headings():
    look_alikes = (
        "# Changelog\n\n## [0.1.01] — not 0.1.0\n\n- wrong.\n\n## [0.1.0-alpha.1]\n\n- wrong too.\n"
    )
    assert changelog_section(look_alikes, Version(0, 1, 0)) is None
    # A look-alike before the real section must not shadow it.
    both = look_alikes + "\n## [0.1.0] — 2026-10-15\n\n- right.\n"
    assert changelog_section(both, Version(0, 1, 0)) == "- right."


def test_alpha_notes():
    subjects = [  # newest first, as git log prints them
        "fix(now): sort by priority first [v0.1.0-alpha.2] (#8)",
        "docs(readme): explain the profile line (#7)",
        "feat(inbox)!: change the capture line format (#6)",
        "",
        "feat(add-working-memory-layer): add wcm now [v0.1.0-alpha.1] (#3)",
        "chore(ci): something older (#2)",
    ]
    assert alpha_notes(subjects) == (
        "### Features\n\n- feat(inbox)!: change the capture line format (#6)\n\n"
        "### Fixes\n\n- fix(now): sort by priority first [v0.1.0-alpha.2] (#8)\n\n"
        "### Other\n\n- docs(readme): explain the profile line (#7)"
    )


# --- Stamping ---------------------------------------------------------------

PYPROJECT = """[build-system]
requires = ["setuptools"]
version = "not this one"

[project]
name = "wcm"
version = "0.0.0.dev0"  # stamped by the release
requires-python = ">=3.14"

[tool.x]
version = "nor this one"
"""


def test_stamp_pyproject():
    got = stamp_pyproject(PYPROJECT, Version(0, 1, 0, 2))
    assert got == PYPROJECT.replace('"0.0.0.dev0"', '"0.1.0a2"')


@pytest.mark.parametrize(
    "content",
    [
        '[project]\nname = "wcm"\ndynamic = ["version"]\n',
        '[tool.x]\nversion = "1"\n',
        "",
    ],
)
def test_stamp_pyproject_needs_a_static_version(content):
    with pytest.raises(ConventionError, match="static version"):
        stamp_pyproject(content, Version(0, 1, 0, 1))


# --- Commands, against real git repositories --------------------------------

GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "relcheck",
    "GIT_AUTHOR_EMAIL": "relcheck@example.com",
    "GIT_COMMITTER_NAME": "relcheck",
    "GIT_COMMITTER_EMAIL": "relcheck@example.com",
}


def git(d: Path, *args: str) -> None:
    """Run git in d for a test, ignoring the user's signing config."""
    subprocess.run(
        ["git", "-C", str(d), "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false", *args],
        env=GIT_ENV,
        check=True,
        capture_output=True,
    )


def commit(d: Path, subject: str) -> None:
    git(d, "commit", "-q", "--no-verify", "--allow-empty", "-m", subject)


@pytest.fixture
def new_repo(tmp_path):
    """A real git repository whose main branch has one empty commit per
    subject, oldest first."""

    def make(*subjects: str) -> Path:
        git(tmp_path, "init", "-q", "-b", "main")
        for s in ("initial commit", *subjects):
            commit(tmp_path, s)
        return tmp_path

    return make


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def run(*args: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    code = relcheck.main(list(args), out, err)
    return code, out.getvalue(), err.getvalue()


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["publish"],
        ["merge", "-h"],
        ["merge", "--bogus"],
        ["merge", "HEAD~3"],  # a positional rev must not silently check HEAD
        ["pr", "--title", "ci(x): y"],
        ["pr", "--branch", "ci/x"],
        ["notes"],
        ["stamp"],
    ],
)
def test_usage(args):
    code, _, stderr = run(*args)
    assert code == 2
    assert "usage:" in stderr


def test_pr(new_repo):
    d = new_repo("chore(ci): add dependabot config (#2)")
    write(d / "openspec/changes/archive/2026-09-30-add-working-memory-layer/proposal.md", "x")

    code, stdout, stderr = run(
        "pr", "--root", str(d), "--base", "main",
        "--branch", "v0.1/add-working-memory-layer",
        "--title", "feat(add-working-memory-layer): add wcm pause, resume and now [v0.1.0-alpha.1]",
    )  # fmt: skip
    assert (code, stdout, stderr) == (0, "ok: publishes v0.1.0-alpha.1\n", "")

    code, stdout, _ = run(
        "pr", "--root", str(d), "--base", "main",
        "--branch", "ci/release-conventions",
        "--title", "ci(release): add branch, title and release conventions",
    )  # fmt: skip
    assert (code, stdout) == (0, "ok: publishes nothing\n")


def test_pr_reads_published_versions_from_base(new_repo):
    # The PR branch forked before the alpha landed on main, so only --base
    # knows about it.
    d = new_repo()
    git(d, "branch", "v0.1/inbox")
    commit(d, "feat(add-working-memory-layer): add wcm now [v0.1.0-alpha.1] (#3)")
    git(d, "switch", "-q", "v0.1/inbox")
    write(d / "openspec/changes/inbox/proposal.md", "x")

    code, _, stderr = run(
        "pr", "--root", str(d), "--base", "main",
        "--branch", "v0.1/inbox", "--title", "feat(inbox): add wcm capture [v0.1.0-alpha.1]",
    )  # fmt: skip
    assert code == 1
    assert (
        "relcheck: v0.1.0-alpha.1 is already published; the next alpha is v0.1.0-alpha.2" in stderr
    )


def test_pr_reports_branch_and_title_together(new_repo):
    d = new_repo()
    code, _, stderr = run(
        "pr", "--root", str(d), "--base", "main", "--branch", "feature/x", "--title", "Add stuff"
    )
    assert code == 1
    assert stderr.count("relcheck: ") == 2


def test_pr_release(new_repo):
    d = new_repo("feat(add-working-memory-layer): add wcm now [v0.1.0-alpha.1] (#3)")
    args = [
        "pr",
        "--root",
        str(d),
        "--base",
        "main",
        "--branch",
        "release/v0.1.0",
        "--title",
        "chore(release): close F1 [v0.1.0]",
    ]

    code, _, stderr = run(*args)
    assert code == 1 and 'no "## [0.1.0]" section' in stderr

    write(d / "CHANGELOG.md", "# Changelog\n\n## [0.1.0] — 2026-10-15\n\n- `wcm now`.\n")
    assert run(*args) == (0, "ok: publishes v0.1.0\n", "")


def test_pr_release_rejects_empty_changelog_section(new_repo):
    d = new_repo("feat(add-working-memory-layer): add wcm now [v0.1.0-alpha.1] (#3)")
    # [0.1.0] added above [Unreleased] instead of renaming it: no notes.
    write(
        d / "CHANGELOG.md",
        "# Changelog\n\n## [0.1.0] — 2026-10-15\n\n## [Unreleased]\n\n- `wcm now`.\n",
    )
    code, _, stderr = run(
        "pr",
        "--root",
        str(d),
        "--base",
        "main",
        "--branch",
        "release/v0.1.0",
        "--title",
        "chore(release): close F1 [v0.1.0]",
    )
    assert code == 1 and 'no "## [0.1.0]" section' in stderr


@pytest.mark.parametrize(
    "subjects, code, stdout, stderr",
    [
        (["chore(ci): bump actions/checkout from 4 to 7 (#5)"], 0, "", ""),
        (["feat(add-working-memory-layer): add wcm now [v0.1.0-alpha.1] (#3)"], 0, "v0.1.0-alpha.1\n", ""),
        ([
            "feat(add-working-memory-layer): add wcm now [v0.1.0-alpha.1] (#3)",
            "chore(ci): bump actions/checkout from 4 to 7 (#5)",
            "feat(inbox): add wcm capture [v0.1.0-alpha.2] (#6)",
        ], 0, "v0.1.0-alpha.2\n", ""),
        ([
            "feat(add-working-memory-layer): add wcm now [v0.1.0-alpha.1] (#3)",
            "feat(inbox): add wcm capture [v0.1.0-alpha.1] (#6)",
        ], 1, "", "already published"),
        ([
            "feat(add-working-memory-layer): add wcm now [v0.1.0-alpha.1] (#3)",
            "chore(release): close F1 [v0.1.0] (#9)",
        ], 1, "", 'no "## [0.1.0]" section'),
    ],
    ids=["nothing", "first alpha", "second alpha", "duplicate", "final without changelog"],
)  # fmt: skip
def test_merge(new_repo, subjects, code, stdout, stderr):
    d = new_repo(*subjects)
    got_code, got_stdout, got_stderr = run("merge", "--root", str(d))
    assert (got_code, got_stdout) == (code, stdout)
    assert stderr in got_stderr


def test_merge_final_with_changelog(new_repo):
    d = new_repo(
        "feat(add-working-memory-layer): add wcm now [v0.1.0-alpha.1] (#3)",
        "chore(release): close F1 [v0.1.0] (#9)",
    )
    write(
        d / "CHANGELOG.md",
        "# Changelog\n\n## [Unreleased]\n\n## [0.1.0] — 2026-10-15\n\n- `wcm now`.\n",
    )
    assert run("merge", "--root", str(d)) == (0, "v0.1.0\n", "")


def test_merge_is_idempotent_after_tagging(new_repo):
    d = new_repo("feat(add-working-memory-layer): add wcm now [v0.1.0-alpha.1] (#3)")
    git(d, "tag", "-a", "v0.1.0-alpha.1", "-m", "v0.1.0-alpha.1")
    # Re-running release.yml after a failed publish must not fail on the tag
    # the first run already pushed.
    assert run("merge", "--root", str(d)) == (0, "v0.1.0-alpha.1\n", "")


def test_merge_rejects_tag_on_another_commit(new_repo):
    d = new_repo(
        "chore(ci): something (#4)",
        "feat(add-working-memory-layer): add wcm now [v0.1.0-alpha.1] (#3)",
    )
    git(d, "tag", "v0.1.0-alpha.1", "HEAD~1")
    code, _, stderr = run("merge", "--root", str(d))
    assert code == 1 and "already exists on another commit" in stderr


def test_notes_final(tmp_path):
    write(
        tmp_path / "CHANGELOG.md",
        "# Changelog\n\n## [Unreleased]\n\n## [0.1.0] — 2026-10-15\n\n### Added\n\n- `wcm now`.\n\n---\n\n## [0.0.1]\n",
    )
    assert run("notes", "--root", str(tmp_path), "--version", "v0.1.0") == (
        0,
        "### Added\n\n- `wcm now`.\n",
        "",
    )
    assert run("notes", "--root", str(tmp_path), "--version", "v0.2.0")[0] == 1


def test_notes_alpha_comes_from_titles(new_repo):
    # Even a matching CHANGELOG section must not become a second source.
    d = new_repo(
        "chore(ci): older (#2)", "feat(add-working-memory-layer): add wcm now [v0.1.0-alpha.1] (#3)"
    )
    write(d / "CHANGELOG.md", "# Changelog\n\n## [0.1.0-alpha.1]\n\n- not this.\n")
    code, stdout, _ = run("notes", "--root", str(d), "--version", "v0.1.0-alpha.1")
    assert code == 0
    assert stdout == (
        "### Features\n\n- feat(add-working-memory-layer): add wcm now [v0.1.0-alpha.1] (#3)\n\n"
        "### Other\n\n- initial commit\n- chore(ci): older (#2)\n"
    )


def test_notes_alpha_checks_the_commit(new_repo):
    d = new_repo("feat(add-working-memory-layer): add wcm now [v0.1.0-alpha.1] (#3)")
    code, _, stderr = run("notes", "--root", str(d), "--version", "v0.1.0-alpha.2")
    assert code == 1 and "is not the commit that publishes v0.1.0-alpha.2" in stderr


def test_stamp(tmp_path):
    write(tmp_path / "pyproject.toml", PYPROJECT)
    assert run("stamp", "--root", str(tmp_path), "--version", "v0.1.0-alpha.3") == (
        0,
        "0.1.0a3\n",
        "",
    )
    assert (
        '\nversion = "0.1.0a3"  # stamped by the release\n'
        in (tmp_path / "pyproject.toml").read_text()
    )


def test_stamp_without_pyproject(tmp_path):
    code, _, stderr = run("stamp", "--root", str(tmp_path), "--version", "v0.1.0-alpha.1")
    assert code == 1 and "pyproject.toml does not exist" in stderr
