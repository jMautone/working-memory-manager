import pytest

from wcm import frontmatter


def test_link_is_double_quoted_and_read_back():
    text = frontmatter.dump({"initiative": "[[INIT-0007]]"})
    assert text == 'initiative: "[[INIT-0007]]"\n'
    assert frontmatter.load(text) == {"initiative": "[[INIT-0007]]"}


def test_link_with_an_alias_in_a_list():
    text = frontmatter.dump({"links": ["[[INIT-0007|payment retries]]"]})
    assert '- "[[INIT-0007|payment retries]]"' in text
    assert frontmatter.load(text) == {"links": ["[[INIT-0007|payment retries]]"]}


def test_timestamps_stay_plain():
    text = frontmatter.dump({"created": "2026-09-16T09:00:00-03:00"})
    assert text == "created: 2026-09-16T09:00:00-03:00\n"
    assert frontmatter.load(text) == {"created": "2026-09-16T09:00:00-03:00"}


def test_split_reads_bom_and_crlf():
    front, body = frontmatter.split("﻿---\r\nid: X\r\n---\r\n\r\n# X\r\n")
    assert front == "id: X"
    assert body == "\n# X\n"


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("# X\n", "does not start with a --- frontmatter line"),
        ("---\nid: X\n", "no closing --- line"),
    ],
)
def test_split_refuses(text, reason):
    with pytest.raises(frontmatter.MalformedError, match=reason):
        frontmatter.split(text)


@pytest.mark.parametrize(
    ("front", "reason"),
    [('title: "unbalanced', "not valid YAML"), ("- a\n- b", "not a mapping"), ("", "mapping")],
)
def test_load_refuses(front, reason):
    with pytest.raises(frontmatter.MalformedError, match=reason):
        frontmatter.load(front)
