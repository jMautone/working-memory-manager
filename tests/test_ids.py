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
