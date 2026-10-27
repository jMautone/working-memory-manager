import pytest

from wcm import ids


@pytest.mark.parametrize("text", ["INIT-0007", "init-0007", "Init-7", "init-7", "7", " 7 "])
def test_accepted_forms(text):
    assert ids.parse(text) == "INIT-0007"


def test_large_numbers_keep_their_digits():
    assert ids.parse("12345") == "INIT-12345"


@pytest.mark.parametrize(
    "text", ["", "INIT", "INIT-", "foo", "INIT-7a", "-7", "0", "init-0", "NOTE-7"]
)
def test_rejected_forms(text):
    with pytest.raises(ids.InvalidId):
        ids.parse(text)


def test_invalid_id_is_a_usage_error(run):
    result = run("resume", "nope")
    assert result.code == 2
    assert "not an initiative ID" in result.err


@pytest.mark.parametrize(
    "text", ["NOTE-0012", "note-0012", "Note-12", "note-12", "12", "0012", " 12 "]
)
def test_note_accepted_forms(text):
    assert ids.parse_note(text) == "NOTE-0012"


@pytest.mark.parametrize(
    "text", ["", "twelve", "0", "note-0", "NOTE-", "NOTE-12a", "INIT-0012", "init-12"]
)
def test_note_rejected_forms(text):
    with pytest.raises(ids.InvalidId):
        ids.parse_note(text)


def test_note_file_names():
    assert ids.NOTE_FILE.fullmatch("NOTE-0012.md")
    assert ids.NOTE_FILE.fullmatch("NOTE-12345.md")
    for name in ("NOTE-12-draft.md", "Gateway timeouts.md", "NOTE-0012.md.tmp", "note-0012.md"):
        assert not ids.NOTE_FILE.fullmatch(name)
