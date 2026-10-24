import sys
from datetime import timedelta
from pathlib import Path

import pytest
from conftest import note_path, path_of, write_initiative, write_note

from wcm import editor, note

FAKE_EDITOR = Path(__file__).with_name("fake_editor.py")


def read(kb, note_id) -> note.Note:
    return note.parse(note_path(kb, note_id).read_text(encoding="utf-8"), note_id)


def files_in_notes(kb) -> list[str]:
    base = kb / "notes"
    return sorted(p.name for p in base.iterdir()) if base.is_dir() else []


@pytest.fixture
def fake_editor(monkeypatch):
    """`EDITOR` runs tests/fake_editor.py; `edit` and `exit` steer what it does."""
    monkeypatch.delenv("VISUAL", raising=False)
    monkeypatch.setenv("EDITOR", f'"{sys.executable}" "{FAKE_EDITOR}"')
    monkeypatch.delenv("WCM_TEST_EDIT", raising=False)
    monkeypatch.delenv("WCM_TEST_EXIT", raising=False)

    def configure(edit: str | None = None, exit: int | None = None):
        if edit is not None:
            monkeypatch.setenv("WCM_TEST_EDIT", edit)
        if exit is not None:
            monkeypatch.setenv("WCM_TEST_EXIT", str(exit))

    return configure


@pytest.fixture
def no_editor(monkeypatch):
    """Fail the test if an editor would open."""

    def fail(path):
        raise AssertionError(f"an editor opened {path}")

    monkeypatch.setattr(editor, "open", fail)


# --- save ------------------------------------------------------------------------


def test_save_without_opening_anything(run, kb, no_editor):
    result = run("note", "el", "gateway", "corta", "a", "los", "30s")
    assert (result.code, result.out) == (0, "NOTE-0001 saved.\n")
    assert read(kb, "NOTE-0001").title == "el gateway corta a los 30s"


def test_file_written_on_save(run, kb):
    write_note(kb, "NOTE-0011")
    result = run("note", "the gateway cuts at 30s, not 60", "-t", "infra")
    assert result.out == "NOTE-0012 saved.\n"
    assert note_path(kb, "NOTE-0012").read_bytes() == (
        b"---\n"
        b"id: NOTE-0012\n"
        b"title: the gateway cuts at 30s, not 60\n"
        b"tags:\n"
        b"- infra\n"
        b"initiative: null\n"
        b"capture: null\n"
        b"created: 2026-09-16T09:00:00-03:00\n"
        b"updated: 2026-09-16T09:00:00-03:00\n"
        b"---\n"
        b"\n"
        b"# the gateway cuts at 30s, not 60\n"
    )


def test_options_after_the_text(run, kb):
    write_initiative(kb, "INIT-0007", status="active")
    assert run("note", "retry budget is 3", "-t", "payments", "--free").code == 0
    n = read(kb, "NOTE-0001")
    assert (n.title, n.tags, n.initiative) == ("retry budget is 3", ["payments"], None)


def test_options_before_the_text(run, kb):
    assert run("note", "-t", "payments", "retry", "budget").code == 0
    assert read(kb, "NOTE-0001").title == "retry budget"


def test_text_is_collapsed_to_one_line(run, kb):
    run("note", "first line\nsecond   line")
    assert read(kb, "NOTE-0001").title == "first line second line"


def test_blank_text_refused(run, kb):
    result = run("note", "   ")
    assert result.code == 2
    assert "a text is required" in result.err
    assert files_in_notes(kb) == []


def test_repeated_and_comma_separated_tags(run, kb):
    run("note", "x", "-t", "infra", "-t", "db, Infra", "-t", "#gateway")
    assert read(kb, "NOTE-0001").tags == ["infra", "db", "gateway"]


def test_help_lists_the_options(run):
    result = run("note", "--help")
    assert result.code == 0
    for option in ("-t TAG", "--tag", "-e", "--edit", "--free", "edit <ID>"):
        assert option in result.out


def test_notes_under_a_hub_that_does_not_exist(run, hub):
    assert not hub.exists()
    assert run("note", "first").code == 0
    assert (hub / "kbs" / "work" / "notes" / "NOTE-0001.md").is_file()


def test_new_note_creates_nothing_else(run, kb):
    write_note(kb, "NOTE-0011")
    run("note", "retry budget is 3")
    assert files_in_notes(kb) == ["NOTE-0011.md", "NOTE-0012.md"]
    assert sorted(p.name for p in kb.iterdir()) == ["notes"]


def test_gap_and_malformed_notes_count(run, kb):
    write_note(kb, "NOTE-0003")
    broken = write_note(kb, "NOTE-0009", text="---\nid: [\n---\n")
    before = broken.read_bytes()
    assert run("note", "next").out == "NOTE-0010 saved.\n"
    assert broken.read_bytes() == before


def test_other_files_in_notes_do_not_count(run, kb):
    write_note(kb, "NOTE-0012")
    (kb / "notes" / "NOTE-12-draft.md").write_text("draft\n", encoding="utf-8")
    (kb / "notes" / "archive").mkdir()
    (kb / "notes" / "archive" / "NOTE-0050.md").write_text("old\n", encoding="utf-8")
    assert run("note", "next").out == "NOTE-0013 saved.\n"


def test_a_note_that_starts_with_the_word_edit(run, kb, no_editor):
    result = run("note", "edit the config before deploying")
    assert result.out == "NOTE-0001 saved.\n"
    assert read(kb, "NOTE-0001").title == "edit the config before deploying"


# --- link to the active initiative ----------------------------------------------


def test_linked_to_the_active_initiative(run, kb):
    init = write_initiative(kb, "INIT-0007", status="active", title="Payment retries")
    before = init.read_bytes()
    write_note(kb, "NOTE-0011")
    result = run("note", "the gateway cuts at 30s, not 60")
    assert result.out == "NOTE-0012 saved, linked to INIT-0007 Payment retries.\n"
    assert init.read_bytes() == before
    assert read(kb, "NOTE-0012").initiative == "INIT-0007"


def test_linked_note_frontmatter(run, kb):
    write_initiative(kb, "INIT-0007", status="active")
    run("note", "retry budget is 3")
    assert 'initiative: "[[INIT-0007]]"\n' in note_path(kb, "NOTE-0001").read_text("utf-8")


def test_free_note(run, kb):
    write_initiative(kb, "INIT-0007", status="active")
    write_note(kb, "NOTE-0012")
    result = run("note", "Thinking in Systems: stocks and flows", "--free")
    assert result.out == "NOTE-0013 saved.\n"
    assert "initiative: null\n" in note_path(kb, "NOTE-0013").read_text("utf-8")


def test_no_active_initiative_is_a_free_note(run, kb):
    write_initiative(kb, "INIT-0007", status="paused")
    assert run("note", "x").out == "NOTE-0001 saved.\n"
    assert read(kb, "NOTE-0001").initiative is None


def test_two_active_initiatives_on_disk(run, kb):
    a = write_initiative(kb, "INIT-0003", status="active")
    b = write_initiative(kb, "INIT-0004", status="active")
    before = a.read_bytes(), b.read_bytes()
    result = run("note", "x")
    assert result.code == 0
    lines = result.out.splitlines()
    assert lines[0] == "NOTE-0001 saved."
    assert lines[1].startswith("!")
    assert "INIT-0003" in lines[1] and "INIT-0004" in lines[1] and "not linked" in lines[1]
    assert read(kb, "NOTE-0001").initiative is None
    assert (a.read_bytes(), b.read_bytes()) == before


# --- prompt ----------------------------------------------------------------------


def test_text_typed_at_the_prompt(run, kb):
    result = run("note", "-t", "infra", answers=["gateway: #retries; at the edge"])
    assert result.code == 0
    assert "Note\n> " in result.out
    n = read(kb, "NOTE-0001")
    assert (n.title, n.tags) == ("gateway: #retries; at the edge", ["infra"])


def test_empty_answer_saves_nothing(run, kb):
    result = run("note", answers=["  "])
    assert result.code == 1
    assert "nothing was saved" in result.err
    assert files_in_notes(kb) == []


def test_no_text_and_no_terminal(run, kb, monkeypatch):
    def fail(*_):
        raise AssertionError("stdin was read")

    monkeypatch.setattr("sys.stdin.readline", fail, raising=False)
    result = run("note", tty=False)
    assert result.code == 2
    assert "a text is required" in result.err
    assert files_in_notes(kb) == []


# --- edit ------------------------------------------------------------------------


def test_write_the_body_later(run, kb, fake_editor, fake_clock):
    run("note", "retry budget")
    fake_clock.advance(days=1)
    fake_editor(edit="\nA paragraph about the budget.\n")
    result = run("note", "edit", "1")
    assert (result.code, result.out) == (0, "NOTE-0001 updated.\n")
    text = note_path(kb, "NOTE-0001").read_text("utf-8")
    assert text.endswith("# retry budget\n\nA paragraph about the budget.\n")


@pytest.mark.parametrize("form", ["12", "note-12", "NOTE-0012", "Note-0012"])
def test_short_forms_accepted(run, kb, fake_editor, form):
    write_note(kb, "NOTE-0012", title="x")
    fake_editor(edit="more\n")
    result = run("note", "edit", form)
    assert (result.code, result.out) == (0, "NOTE-0012 updated.\n")


def test_write_the_body_now(run, kb, fake_editor):
    write_note(kb, "NOTE-0013")
    fake_editor(edit="\nThe body.\n")
    result = run("note", "-e", "retry budget")
    assert (result.code, result.out) == (0, "NOTE-0014 saved.\nNOTE-0014 updated.\n")
    assert note_path(kb, "NOTE-0014").read_text("utf-8").endswith("\nThe body.\n")


def test_editor_closed_without_changes(run, kb, fake_editor):
    path = write_note(kb, "NOTE-0012")
    before = path.read_bytes()
    result = run("note", "edit", "12")
    assert (result.code, result.out) == (0, "NOTE-0012 unchanged.\n")
    assert path.read_bytes() == before


def test_fix_a_malformed_note(run, kb, fake_editor, monkeypatch):
    path = write_note(kb, "NOTE-0005", text='---\nid: NOTE-0005\ntitle: "unbalanced\n---\n')
    opened = []
    real = editor.open
    monkeypatch.setattr(editor, "open", lambda p: opened.append(p) or real(p))
    result = run("note", "edit", "5")
    assert (result.code, result.out) == (0, "NOTE-0005 unchanged.\n")
    assert opened == [path]


def test_unknown_note(run, kb, no_editor):
    result = run("note", "edit", "99")
    assert result.code == 1
    assert "NOTE-0099 was not found" in result.err


def test_edit_without_an_id(run, kb, no_editor):
    result = run("note", "edit")
    assert result.code == 2
    assert "a note ID is required" in result.err
    assert files_in_notes(kb) == []


@pytest.mark.parametrize(
    "argv",
    [
        ("edit", "12", "-t", "x"),
        ("edit", "12", "-e"),
        ("edit", "12", "--free"),
        ("edit", "12", "13"),
        ("edit", "the", "config"),
    ],
)
def test_edit_takes_only_one_id(run, kb, no_editor, argv):
    write_note(kb, "NOTE-0012")
    result = run("note", *argv)
    assert result.code == 2
    assert files_in_notes(kb) == ["NOTE-0012.md"]


def test_invalid_note_id(run, kb, no_editor):
    result = run("note", "edit", "twelve")
    assert result.code == 2
    assert "not a note ID" in result.err
    assert 'wcm note "edit ..."' in result.err


# --- editor selection --------------------------------------------------------------


def test_editor_cannot_start(run, kb, monkeypatch):
    monkeypatch.delenv("VISUAL", raising=False)
    monkeypatch.setenv("EDITOR", "wcm-no-such-editor --wait")
    result = run("note", "-e", "x")
    assert result.code == 1
    assert result.out == "NOTE-0001 saved.\n"
    assert "wcm-no-such-editor" in result.err
    assert "VISUAL or EDITOR" in result.err
    assert note_path(kb, "NOTE-0001").is_file()


def test_editor_fails(run, kb, fake_editor, fake_clock):
    path = write_note(kb, "NOTE-0012", text="---\nid: NOTE-0012\ntitle: x\n---\n")
    fake_clock.advance(hours=1)
    fake_editor(edit="half a thought\n", exit=3)
    result = run("note", "edit", "12")
    assert result.code == 1
    assert "code 3" in result.err
    assert path.read_text("utf-8") == "---\nid: NOTE-0012\ntitle: x\n---\nhalf a thought\n"


def test_editor_receives_the_absolute_path(run, kb, monkeypatch):
    calls = []
    monkeypatch.setenv("EDITOR", "myeditor --wait")
    monkeypatch.delenv("VISUAL", raising=False)
    monkeypatch.setattr(editor.shutil, "which", lambda name: f"/bin/{name}")
    monkeypatch.setattr(
        editor.subprocess,
        "run",
        lambda argv: calls.append(argv) or type("R", (), {"returncode": 0}),
    )
    write_note(kb, "NOTE-0012")
    assert run("note", "edit", "12").code == 0
    assert calls == [["/bin/myeditor", "--wait", str(note_path(kb, "NOTE-0012").absolute())]]


# --- updated follows edits ---------------------------------------------------------


@pytest.fixture
def editor_writes(monkeypatch):
    """An editor that rewrites the file with `change(text)` and exits with 0."""

    def install(change):
        def fake_open(path):
            text = path.read_bytes().decode("utf-8")
            path.write_bytes(change(text).encode("utf-8"))
            return 0

        monkeypatch.setattr(editor, "open", fake_open)

    return install


def test_edit_refreshes_updated(run, kb, fake_editor, fake_clock):
    run("note", "retry budget")
    fake_clock.advance(days=1)
    before = note_path(kb, "NOTE-0001").read_text("utf-8")
    fake_editor(edit="\nOne more line.\n")
    run("note", "edit", "1")
    after = note_path(kb, "NOTE-0001").read_text("utf-8")
    assert "created: 2026-09-16T09:00:00-03:00\n" in after
    assert "updated: 2026-09-17T09:00:00-03:00\n" in after
    expected = before.replace(
        "updated: 2026-09-16T09:00:00-03:00", "updated: 2026-09-17T09:00:00-03:00"
    )
    assert after == expected + "\nOne more line.\n"


def test_hand_formatting_preserved(run, kb, editor_writes, fake_clock):
    run("note", "x", "-t", "infra")
    fake_clock.advance(minutes=5)
    editor_writes(
        lambda text: text.replace("tags:\n- infra\n", "tags: [infra, db]  # flow\n# mine\n")
    )
    assert run("note", "edit", "1").out == "NOTE-0001 updated.\n"
    text = note_path(kb, "NOTE-0001").read_text("utf-8")
    assert "tags: [infra, db]  # flow\n# mine\n" in text
    assert "updated: 2026-09-16T09:05:00-03:00\n" in text


def test_hand_written_crlf_note_keeps_its_bytes(run, kb, editor_writes, fake_clock):
    path = write_note(kb, "NOTE-0020", text="﻿---\r\nid: NOTE-0020\r\n---\r\n# Keys\r\n")
    fake_clock.advance(minutes=5)
    editor_writes(lambda text: text + "more\r\n")
    assert run("note", "edit", "20").code == 0
    assert (
        path.read_bytes()
        == (
            "﻿---\r\nid: NOTE-0020\r\nupdated: 2026-09-16T09:05:00-03:00\r\n---\r\n"
            "# Keys\r\nmore\r\n"
        ).encode()
    )


def test_edit_breaks_the_note(run, kb, editor_writes):
    run("note", "x")
    editor_writes(lambda text: text.replace("id: NOTE-0001\n", ""))
    edited = note_path(kb, "NOTE-0001").read_text("utf-8").replace("id: NOTE-0001\n", "")
    result = run("note", "edit", "1")
    assert result.code == 1
    assert "notes/NOTE-0001.md" in result.err
    assert "has no id" in result.err
    assert note_path(kb, "NOTE-0001").read_text("utf-8") == edited


def test_nothing_is_written_in_the_initiative(run, kb, fake_editor):
    init = write_initiative(kb, "INIT-0007", status="active")
    before = init.read_bytes()
    fake_editor(edit="x\n")
    run("note", "-e", "y")
    assert init.read_bytes() == before
    assert path_of(kb, "INIT-0007") == init


def test_no_tmp_left_behind(run, kb, fake_editor):
    fake_editor(edit="x\n")
    run("note", "-e", "y")
    run("note", "z")
    assert files_in_notes(kb) == ["NOTE-0001.md", "NOTE-0002.md"]


def test_created_is_kept_across_days(run, kb, fake_editor, fake_clock):
    run("note", "y")
    fake_clock.advance(days=3)
    fake_editor(edit="x\n")
    run("note", "edit", "1")
    n = read(kb, "NOTE-0001")
    assert n.created == fake_clock.t - timedelta(days=3)
