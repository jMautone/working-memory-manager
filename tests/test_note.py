from datetime import timedelta

import pytest
from conftest import START

from wcm import note
from wcm.frontmatter import MalformedError

LATER = START + timedelta(days=1, hours=2)


def make(**fields) -> note.Note:
    values = {
        "id": "NOTE-0012",
        "title": "the gateway cuts at 30s, not 60",
        "tags": ["infra"],
        "initiative": None,
        "created": START,
        "body": "\n# the gateway cuts at 30s, not 60\n",
    }
    values.update(fields)
    return note.Note(**values)


# --- parse and render_new ------------------------------------------------------


def test_render_new_layout():
    text = note.render_new("NOTE-0012", "the gateway cuts at 30s, not 60", [], "INIT-0007", START)
    assert text == (
        "---\n"
        "id: NOTE-0012\n"
        "title: the gateway cuts at 30s, not 60\n"
        "tags: []\n"
        'initiative: "[[INIT-0007]]"\n'
        "capture: null\n"
        "created: 2026-09-16T09:00:00-03:00\n"
        "updated: 2026-09-16T09:00:00-03:00\n"
        "---\n"
        "\n"
        "# the gateway cuts at 30s, not 60\n"
    )


@pytest.mark.parametrize(
    ("title", "tags", "initiative"),
    [
        ("the gateway cuts at 30s, not 60", ["infra", "db"], None),
        ("gateway: #retries; at the edge", [], "INIT-0007"),
        ("[[wiki]] 'quoted' \"double\" yes null 0123", ["#x", "ñandú"], "INIT-12345"),
    ],
)
def test_parse_reads_what_render_new_writes(title, tags, initiative):
    parsed = note.parse(note.render_new("NOTE-0012", title, tags, initiative, START), "NOTE-0012")
    assert (parsed.id, parsed.title, parsed.tags) == ("NOTE-0012", title, tags)
    assert (parsed.initiative, parsed.created) == (initiative, START)
    assert parsed.body == f"\n# {title}\n"


def test_minimal_hand_written_note():
    text = "---\nid: NOTE-0020\n---\n\n# Idempotency keys\n\nUse a key per request.\n"
    parsed = note.parse(text, "NOTE-0020")
    assert parsed.title == "Idempotency keys"
    assert (parsed.tags, parsed.initiative, parsed.created) == ([], None, None)
    assert "Use a key per request." in parsed.body


def test_title_key_wins_over_the_heading():
    text = "---\nid: NOTE-0020\ntitle: From the key\n---\n\n# From the heading\n"
    assert note.parse(text, "NOTE-0020").title == "From the key"


def test_empty_title_key_falls_back_to_the_heading():
    text = "---\nid: NOTE-0020\ntitle: ''\n---\n\nintro\n\n# From the heading\n"
    assert note.parse(text, "NOTE-0020").title == "From the heading"


def test_single_tag_as_text():
    text = "---\nid: NOTE-0020\ntitle: X\ntags: infra\n---\n"
    assert note.parse(text, "NOTE-0020").tags == ["infra"]


def test_unknown_keys_are_ignored():
    text = "---\nid: NOTE-0020\ntitle: X\naliases: [a]\nsource: somewhere\n---\n"
    assert note.parse(text, "NOTE-0020").title == "X"


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("# Just a heading\n", "does not start with a --- frontmatter line"),
        ('---\nid: NOTE-0005\ntitle: "unbalanced\n---\n', "not valid YAML"),
        ("---\n- a\n---\n", "not a mapping"),
        ("---\ntitle: X\n---\n", "has no id"),
        (
            "---\nid: NOTE-0016\ntitle: X\n---\n",
            "its id is 'NOTE-0016' but its name says NOTE-0005",
        ),
        ("---\nid: NOTE-0005\n---\n\nno heading here\n", "has no title"),
    ],
)
def test_malformed_reasons(text, reason):
    with pytest.raises(MalformedError, match=reason):
        note.parse(text, "NOTE-0005")


# --- link_of and normalize_tags ------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("[[INIT-0007]]", "INIT-0007"),
        ("[[init-0007|alias]]", "INIT-0007"),
        ("[[INIT-0007|payment retries]]", "INIT-0007"),
        ("INIT-0007", "INIT-0007"),
        (" init-0007 ", "INIT-0007"),
        ("payment retries", None),
        ("[[INIT-7]]", None),
        ("[[INIT-0000]]", None),
        ("[[NOTE-0007]]", None),
        (None, None),
        (7, None),
    ],
)
def test_link_of(value, expected):
    assert note.link_of(value) == expected


def test_normalize_tags():
    assert note.normalize_tags(["infra", "db, Infra", "#gateway"]) == ["infra", "db", "gateway"]


def test_normalize_tags_drops_empty_ones():
    assert note.normalize_tags([" , ", "#", "  a  "]) == ["a"]
    assert note.normalize_tags(None) == []


# --- matches and prefilter -------------------------------------------------------


def raw_of(n: note.Note) -> str:
    """The file text of a note, as the prefilter sees it."""
    text = note.render_new(n.id, n.title, n.tags, n.initiative, START)
    return (text + n.body).casefold()


GATEWAY_TITLE = make()
GATEWAY_BODY = make(
    id="NOTE-0004", title="Edge", tags=[], body="\n# Edge\n\nThe Gateway is slow.\n"
)
NEITHER = make(id="NOTE-0009", title="Retries", tags=["payments"], body="\n# Retries\n")
TAGGED = make(id="NOTE-0003", title="Setup", tags=["infra"], body="\n# Setup\n")
ACCENT = make(id="NOTE-0002", title="Notes", tags=[], body="\n# Notes\n\nla versión 2\n")
SPACED = make(
    id="NOTE-0010", title="x", tags=[], body="\n# x\n\na gateway timeout here\n", initiative=None
)
LINKED = make(id="NOTE-0011", tags=["Infra"], initiative="INIT-0007")
ALL = [GATEWAY_TITLE, GATEWAY_BODY, NEITHER, TAGGED, ACCENT, SPACED, LINKED]

CASES = [
    (["gateway"], [], None, {"NOTE-0012", "NOTE-0004", "NOTE-0010", "NOTE-0011"}),
    (["gateway", "60"], [], None, {"NOTE-0012", "NOTE-0011"}),
    (["INFRA"], [], None, {"NOTE-0012", "NOTE-0003", "NOTE-0011"}),
    (["version"], [], None, set()),
    (["versión"], [], None, {"NOTE-0002"}),
    (["gateway timeout"], [], None, {"NOTE-0010"}),
    (["timeout gateway"], [], None, set()),
    ([], ["#INFRA"], None, {"NOTE-0012", "NOTE-0003", "NOTE-0011"}),
    ([], ["infra"], "INIT-0007", {"NOTE-0011"}),
    ([], [], None, {n.id for n in ALL}),
]


@pytest.mark.parametrize(("terms", "tags", "initiative", "expected"), CASES)
def test_matches(terms, tags, initiative, expected):
    assert {n.id for n in ALL if note.matches(n, terms, tags, initiative)} == expected


@pytest.mark.parametrize(("terms", "tags", "initiative", "expected"), CASES)
def test_prefilter_never_drops_a_match(terms, tags, initiative, expected):
    keep = note.prefilter(terms, tags, initiative)
    for n in ALL:
        if note.matches(n, terms, tags, initiative):
            assert keep is None or keep(raw_of(n))


def test_prefilter_drops_what_cannot_match():
    keep = note.prefilter(["kubernetes"], [], None)
    assert not any(keep(raw_of(n)) for n in ALL)
    assert note.prefilter([], [], None) is None


def test_terms_match_different_fields():
    n = make(title="gateway", tags=["infra"], body="\n# gateway\n\ntimeout\n")
    assert note.matches(n, ["gateway", "infra", "timeout"], [], None)


# --- touch_updated ---------------------------------------------------------------


def only_updated_changed(before: str, after: str) -> bool:
    b = [line for line in before.split("\n") if not line.startswith("updated:")]
    a = [line for line in after.split("\n") if not line.startswith("updated:")]
    return a == b


def test_touch_replaces_the_value():
    before = note.render_new("NOTE-0012", "x", ["infra"], None, START)
    after = note.touch_updated(before, LATER)
    assert "updated: 2026-09-17T11:00:00-03:00\n" in after
    assert "created: 2026-09-16T09:00:00-03:00\n" in after
    assert only_updated_changed(before, after)


def test_touch_adds_a_missing_updated_before_the_closing_line():
    before = "---\nid: NOTE-0020\ntitle: X\n---\n\n# X\n"
    after = note.touch_updated(before, LATER)
    assert after == "---\nid: NOTE-0020\ntitle: X\nupdated: 2026-09-17T11:00:00-03:00\n---\n\n# X\n"


def test_touch_keeps_crlf_and_bom():
    before = "﻿---\r\nid: NOTE-0020\r\nupdated: old\r\ntitle: X\r\n---\r\n\r\n# X\r\n"
    after = note.touch_updated(before, LATER)
    assert after == before.replace("updated: old", "updated: 2026-09-17T11:00:00-03:00")


def test_touch_adds_with_crlf():
    before = "---\r\nid: NOTE-0020\r\n---\r\n# X\r\n"
    after = note.touch_updated(before, LATER)
    assert after == "---\r\nid: NOTE-0020\r\nupdated: 2026-09-17T11:00:00-03:00\r\n---\r\n# X\r\n"


def test_touch_keeps_comments_and_flow_lists():
    before = (
        "---\n"
        "id: NOTE-0012  # the file name\n"
        "title: x\n"
        "tags: [infra, db]\n"
        "# a comment the person wrote\n"
        "summary: |\n"
        "  updated: inside a block is not the key\n"
        "updated: 2026-09-16T09:00:00-03:00\n"
        "---\n"
        "\n"
        "updated: in the body stays\n"
    )
    after = note.touch_updated(before, LATER)
    assert after == before.replace(
        "updated: 2026-09-16T09:00:00-03:00", "updated: 2026-09-17T11:00:00-03:00"
    )
    assert note.parse(after, "NOTE-0012").tags == ["infra", "db"]
