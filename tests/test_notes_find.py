import os
from datetime import timedelta

import pytest
from conftest import START, note_path, path_of, write_initiative, write_note

from wcm import note, render


def listed(out: str) -> list[str]:
    return [line.split()[0] for line in out.splitlines() if line.startswith("  NOTE-")]


def ago(**delta) -> str:
    return (START - timedelta(**delta)).isoformat()


# --- render.note_list --------------------------------------------------------------


def make(note_id="NOTE-0012", title="the gateway cuts at 30s, not 60", **fields) -> note.Note:
    values = {"tags": [], "initiative": None, "created": START, "body": f"\n# {title}\n"}
    values.update(fields)
    return note.Note(id=note_id, title=title, **values)


def lines_of(notes, width=100, problems=()):
    out = render.note_list(notes, now=START, width=width, problems=list(problems), filtered=False)
    return out.splitlines()


def test_linked_note_line():
    n = make(created=START - timedelta(hours=2), initiative="INIT-0007")
    (line,) = lines_of([n])
    assert line.split() == ["NOTE-0012", *n.title.split(), "2h", "0m", "INIT-0007"]


def test_free_note_line():
    n = make("NOTE-0004", "Edge", created=START - timedelta(weeks=3))
    (line,) = lines_of([n])
    assert line.split() == ["NOTE-0004", "Edge", "3w"]


def test_missing_created_is_a_question_mark():
    (line,) = lines_of([make(created=None)])
    assert line.endswith("  ?")


@pytest.mark.parametrize("initiative", [None, "INIT-0007"])
def test_long_title_is_shortened(initiative):
    n = make(title="x" * 300, created=START - timedelta(days=2), initiative=initiative)
    (line,) = lines_of([n], width=80)
    assert render.display_width(line) <= 80
    assert "x…" in line
    assert line.endswith("2d  INIT-0007" if initiative else "2d")


def test_order_newest_first_then_highest_id_then_no_created():
    notes = [
        make("NOTE-0001", "a", created=START - timedelta(days=1)),
        make("NOTE-0002", "b", created=None),
        make("NOTE-0003", "c", created=START),
        make("NOTE-0004", "d", created=START),
        make("NOTE-0005", "e", created=None),
    ]
    order = [line.split()[0] for line in lines_of(notes)]
    assert order == ["NOTE-0004", "NOTE-0003", "NOTE-0001", "NOTE-0005", "NOTE-0002"]


def test_problems_follow_the_list():
    lines = lines_of([make()], problems=[("notes/NOTE-0005.md", "the frontmatter has no id")])
    assert lines[-1] == "!  Could not read notes/NOTE-0005.md: the frontmatter has no id"


# --- wcm notes ---------------------------------------------------------------------


@pytest.fixture
def three(kb):
    write_note(kb, "NOTE-0012", title="the gateway cuts at 30s, not 60", created=ago(hours=1))
    write_note(kb, "NOTE-0004", title="Edge", body="\nThe Gateway is slow.\n", created=ago(days=3))
    write_note(kb, "NOTE-0009", title="Retries", tags="[payments]", created=ago(days=1))


def test_search_by_a_word(run, three):
    result = run("notes", "gateway")
    assert result.code == 0
    assert listed(result.out) == ["NOTE-0012", "NOTE-0004"]


def test_several_terms_must_all_match(run, kb, three):
    write_note(kb, "NOTE-0013", title="timeout and gateway", created=ago(days=5))
    assert listed(run("notes", "gateway", "timeout").out) == ["NOTE-0013"]


def test_term_with_spaces_is_one_substring(run, kb):
    write_note(kb, "NOTE-0001", title="gateway timeout")
    write_note(kb, "NOTE-0002", title="timeout of the gateway")
    assert listed(run("notes", "gateway timeout").out) == ["NOTE-0001"]


def test_match_in_a_tag(run, kb, three):
    write_note(kb, "NOTE-0003", title="Setup", tags="[infra]")
    assert listed(run("notes", "INFRA").out) == ["NOTE-0003"]


def test_accents_are_significant(run, kb):
    write_note(kb, "NOTE-0001", title="Release", body="\nla versión 2\n")
    assert listed(run("notes", "version").out) == []
    assert listed(run("notes", "VERSIÓN").out) == ["NOTE-0001"]


def test_filter_by_tag_and_initiative(run, kb):
    write_initiative(kb, "INIT-0007")
    write_note(kb, "NOTE-0012", tags="[infra]", initiative='"[[INIT-0007]]"')
    write_note(kb, "NOTE-0013", tags="[infra]")
    write_note(kb, "NOTE-0014", tags="[db]", initiative='"[[INIT-0007]]"')
    assert listed(run("notes", "-t", "infra", "-i", "7").out) == ["NOTE-0012"]


def test_repeated_tags_must_all_match(run, kb):
    write_note(kb, "NOTE-0001", tags="[infra, db]")
    write_note(kb, "NOTE-0002", tags="[infra]")
    assert listed(run("notes", "-t", "#Infra", "-t", "DB").out) == ["NOTE-0001"]
    assert listed(run("notes", "-t", "infra,db").out) == ["NOTE-0001"]


def test_initiative_filter_finds_closed_initiatives(run, kb):
    write_initiative(kb, "INIT-0007", status="done", location="done")
    write_note(kb, "NOTE-0001", initiative='"[[INIT-0007]]"')
    assert listed(run("notes", "-i", "INIT-0007").out) == ["NOTE-0001"]


def test_unknown_initiative_filter(run, kb, three):
    result = run("notes", "-i", "99")
    assert result.code == 1
    assert "INIT-0099 was not found" in result.err


def test_invalid_initiative_filter(run, three):
    assert run("notes", "-i", "abc").code == 2


def test_nothing_matches(run, three):
    result = run("notes", "kubernetes")
    assert (result.code, result.out) == (0, "No notes match.\n")


def test_no_notes_yet(run):
    result = run("notes")
    assert result.code == 0
    assert len(result.out.splitlines()) == 1
    assert "wcm note" in result.out


def test_list_all_without_terms(run, three):
    result = run("notes")
    assert listed(result.out) == ["NOTE-0012", "NOTE-0009", "NOTE-0004"]
    assert len(result.out.splitlines()) == 3


def test_same_output_from_any_directory(run, three, tmp_path, monkeypatch):
    first = run("notes").out
    monkeypatch.chdir(tmp_path)
    assert run("notes").out == first


def test_link_with_an_alias(run, kb):
    write_initiative(kb, "INIT-0007")
    write_note(kb, "NOTE-0001", initiative='"[[INIT-0007|payment retries]]"')
    out = run("notes", "-i", "7").out
    assert listed(out) == ["NOTE-0001"]
    assert out.rstrip().endswith("INIT-0007")


def test_unrecognized_value_is_free(run, kb):
    write_initiative(kb, "INIT-0007")
    write_note(kb, "NOTE-0001", initiative="payment retries")
    out = run("notes").out
    assert listed(out) == ["NOTE-0001"]
    assert "INIT-0007" not in out
    assert listed(run("notes", "-i", "7").out) == []


def test_minimal_hand_written_note(run, kb):
    write_note(
        kb,
        "NOTE-0020",
        text="---\nid: NOTE-0020\n---\n\n# Idempotency keys\n\nOne key per request.\n",
    )
    (line,) = run("notes", "idempotency").out.splitlines()
    assert line == "  NOTE-0020  Idempotency keys  ?"


def test_broken_note_during_a_search(run, kb):
    broken = write_note(kb, "NOTE-0005", text='---\nid: NOTE-0005\ntitle: "gateway notes\n---\n')
    before = broken.read_bytes()
    write_note(kb, "NOTE-0012", title="the gateway cuts at 30s")
    result = run("notes", "gateway")
    assert result.code == 0
    assert listed(result.out) == ["NOTE-0012"]
    warnings = [line for line in result.out.splitlines() if line.startswith("!")]
    assert len(warnings) == 1 and "notes/NOTE-0005.md" in warnings[0]
    assert broken.read_bytes() == before


def test_broken_note_that_cannot_match(run, kb):
    write_note(kb, "NOTE-0005", text='---\nid: NOTE-0005\ntitle: "unbalanced\n---\n')
    write_note(kb, "NOTE-0012", title="the gateway cuts at 30s")
    assert run("notes", "kubernetes").out == "No notes match.\n"
    assert "notes/NOTE-0005.md" in run("notes").out


def test_name_and_id_disagree(run, kb):
    write_note(kb, "NOTE-0006", text="---\nid: NOTE-0016\ntitle: x\n---\n")
    out = run("notes").out
    assert listed(out) == []
    (warning,) = out.splitlines()
    assert warning.startswith("!") and "notes/NOTE-0006.md" in warning
    assert "NOTE-0016" not in listed(out)


def test_other_files_are_not_listed(run, kb):
    write_note(kb, "NOTE-0012", title="gateway")
    (kb / "notes" / "Gateway timeouts.md").write_text("# gateway\n", encoding="utf-8")
    (kb / "notes" / "NOTE-12-draft.md").write_text("gateway\n", encoding="utf-8")
    (kb / "notes" / "archive").mkdir()
    (kb / "notes" / "archive" / "NOTE-0050.md").write_text("gateway\n", encoding="utf-8")
    out = run("notes").out
    assert out.splitlines() == [line for line in out.splitlines() if line.startswith("  NOTE-")]
    assert listed(out) == ["NOTE-0012"]


def test_notes_writes_nothing(run, kb, three):
    write_note(kb, "NOTE-0005", text="broken\n")
    write_initiative(kb, "INIT-0007", status="active")
    files = [p for p in kb.rglob("*") if p.is_file()]
    stamps = {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in files}
    run("notes")
    run("notes", "gateway", "-t", "x", "-i", "7")
    assert {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in files} == stamps
    assert sorted(p for p in kb.rglob("*") if p.is_file()) == sorted(files)


# --- the brief ---------------------------------------------------------------------


def test_brief_with_linked_notes(run, kb, tmp_path):
    work = tmp_path / "wt"
    work.mkdir()
    write_initiative(
        kb, "INIT-0007", last_paused=ago(days=2), workspaces=f"[{{path: '{work}', primary: true}}]"
    )
    link = '"[[INIT-0007]]"'
    write_note(kb, "NOTE-0010", title="older", initiative=link, created=ago(days=2))
    write_note(
        kb,
        "NOTE-0012",
        title="the gateway cuts at 30s, not 60",
        initiative=link,
        created=ago(hours=1),
    )
    write_note(kb, "NOTE-0011", title="older too", initiative=link, created=ago(days=1))
    lines = run("resume", "INIT-0007").out.splitlines()
    notes_at = next(i for i, line in enumerate(lines) if "Notes:" in line)
    path_at = next(i for i, line in enumerate(lines) if "Path:" in line)
    next_at = next(i for i, line in enumerate(lines) if "Next:" in line)
    assert lines[notes_at] == "  Notes:          3 (latest: the gateway cuts at 30s, not 60)"
    assert next_at < notes_at < path_at


def test_no_linked_notes(run, kb):
    write_initiative(kb, "INIT-0009")
    write_note(kb, "NOTE-0001", initiative='"[[INIT-0007]]"')
    assert "Notes:" not in run("resume", "9").out


def test_notes_shown_when_resuming_the_active_one_again(run, kb):
    write_initiative(kb, "INIT-0007", status="active", last_resumed=ago(hours=1))
    write_note(kb, "NOTE-0001", title="retry budget is 3", initiative='"[[init-0007]]"')
    files = [p for p in kb.rglob("*") if p.is_file()]
    stamps = {p: p.stat().st_mtime_ns for p in files}
    result = run("resume")
    assert result.code == 0
    assert "  Notes:          1 (latest: retry budget is 3)" in result.out.splitlines()
    assert {p: p.stat().st_mtime_ns for p in files} == stamps
    assert sorted(p for p in kb.rglob("*") if p.is_file()) == sorted(files)


def test_free_and_malformed_notes_are_not_counted(run, kb):
    write_initiative(kb, "INIT-0007")
    write_note(kb, "NOTE-0001", title="the valid one", initiative='"[[INIT-0007]]"')
    write_note(kb, "NOTE-0002", title="free, mentions INIT-0007 in its title")
    write_note(kb, "NOTE-0003", text='---\nid: NOTE-0003\ninitiative: "[[INIT-0007]]\n---\n')
    out = run("resume", "INIT-0007").out
    assert "  Notes:          1 (latest: the valid one)" in out.splitlines()


def test_closing_an_initiative_leaves_its_notes_in_place(run, kb):
    write_initiative(kb, "INIT-0007", status="active")
    run("note", "retry budget is 3")
    before = note_path(kb, "NOTE-0001").read_bytes()
    assert run("done", "INIT-0007").code == 0
    assert path_of(kb, "INIT-0007", "done").is_file()
    assert note_path(kb, "NOTE-0001").read_bytes() == before
    assert b'initiative: "[[INIT-0007]]"' in before
    assert listed(run("notes", "-i", "7").out) == ["NOTE-0001"]


def test_notes_from_the_cli_round_trip(run, kb, fake_clock):
    write_initiative(kb, "INIT-0007", status="active", title="Payment retries")
    run("note", "the gateway cuts at 30s, not 60", "-t", "infra")
    fake_clock.advance(hours=2)
    run("note", "Thinking in Systems", "--free")
    out = run("notes").out.splitlines()
    assert out[0].split()[0] == "NOTE-0002"
    assert out[1].split()[0] == "NOTE-0001" and out[1].endswith("2h 0m  INIT-0007")
    assert os.listdir(kb / "notes") and listed(run("notes", "-t", "INFRA").out) == ["NOTE-0001"]
