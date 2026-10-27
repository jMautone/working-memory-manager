import pytest
from conftest import note_path, write_note

from wcm import note, store


@pytest.fixture
def st(hub) -> store.Store:
    return store.Store()


def test_first_id_without_a_notes_directory(st, kb):
    assert not (kb / "notes").exists()
    assert st.next_note_id() == "NOTE-0001"


def test_gap_is_not_reused(st, kb):
    write_note(kb, "NOTE-0003")
    write_note(kb, "NOTE-0007")
    assert st.next_note_id() == "NOTE-0008"


def test_malformed_note_still_counts(st, kb):
    write_note(kb, "NOTE-0009", text="no frontmatter at all\n")
    assert st.next_note_id() == "NOTE-0010"


def test_other_files_in_notes_are_ignored(st, kb):
    write_note(kb, "NOTE-0012", title="gateway")
    notes = kb / "notes"
    (notes / "Gateway timeouts.md").write_text("# Gateway\n", encoding="utf-8")
    (notes / "NOTE-12-draft.md").write_text("draft\n", encoding="utf-8")
    (notes / "archive").mkdir()
    (notes / "archive" / "NOTE-0050.md").write_text("old\n", encoding="utf-8")
    (notes / "NOTE-0099.md").mkdir()
    entries, problems = st.scan_notes()
    assert [e.note.id for e in entries] == ["NOTE-0012"]
    assert problems == []
    assert st.next_note_id() == "NOTE-0013"


def test_scan_reports_malformed_notes(st, kb):
    write_note(kb, "NOTE-0005", text='---\nid: NOTE-0005\ntitle: "unbalanced\n---\n')
    write_note(kb, "NOTE-0006", title="x").write_text(
        "---\nid: NOTE-0016\ntitle: x\n---\n", encoding="utf-8"
    )
    write_note(kb, "NOTE-0007", title="fine")
    entries, problems = st.scan_notes()
    assert [e.note.id for e in entries] == ["NOTE-0007"]
    assert [(st.relative(p.path), p.reason.split(" (")[0]) for p in problems] == [
        ("notes/NOTE-0005.md", "the frontmatter is not valid YAML"),
        ("notes/NOTE-0006.md", "its id is 'NOTE-0016' but its name says NOTE-0006"),
    ]


def test_scan_reports_undecodable_files(st, kb):
    note_path(kb, "NOTE-0001").parent.mkdir(parents=True)
    note_path(kb, "NOTE-0001").write_bytes(b"---\nid: \xff\n---\n")
    entries, problems = st.scan_notes()
    assert entries == []
    assert "cannot be read" in problems[0].reason


def test_prefilter_skips_parsing(st, kb, monkeypatch):
    write_note(kb, "NOTE-0001", title="gateway")
    write_note(kb, "NOTE-0002", title="retries")
    parsed = []
    real = note.parse
    monkeypatch.setattr(note, "parse", lambda text, i: parsed.append(i) or real(text, i))
    entries, _ = st.scan_notes(note.prefilter(["GATEWAY"], [], None))
    assert [e.note.id for e in entries] == ["NOTE-0001"]
    assert parsed == ["NOTE-0001"]


def test_find_note_path(st, kb):
    path = write_note(kb, "NOTE-0005", text="broken\n")
    assert st.find_note_path("NOTE-0005") == path
    with pytest.raises(store.NotFound, match="NOTE-0099 was not found"):
        st.find_note_path("NOTE-0099")


def test_create_note_under_a_hub_that_does_not_exist(st, hub):
    assert not hub.exists()
    path = st.create_note("NOTE-0001", "---\nid: NOTE-0001\n---\n")
    assert path == hub / "kbs" / "work" / "notes" / "NOTE-0001.md"
    assert path.read_bytes() == b"---\nid: NOTE-0001\n---\n"
    assert sorted(p.name for p in path.parent.iterdir()) == ["NOTE-0001.md"]


def test_create_note_never_overwrites(st, kb):
    path = write_note(kb, "NOTE-0001", title="mine")
    before = path.read_bytes()
    with pytest.raises(FileExistsError, match="notes/NOTE-0001.md already exists"):
        st.create_note("NOTE-0001", "other\n")
    assert path.read_bytes() == before
    assert sorted(p.name for p in path.parent.iterdir()) == ["NOTE-0001.md"]


def test_replace_note_writes_it_whole(st, kb):
    path = write_note(kb, "NOTE-0001", title="mine")
    st.replace_note(path, "﻿---\r\nid: NOTE-0001\r\n---\r\n")
    assert path.read_bytes() == "﻿---\r\nid: NOTE-0001\r\n---\r\n".encode()
    assert sorted(p.name for p in path.parent.iterdir()) == ["NOTE-0001.md"]
