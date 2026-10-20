from datetime import datetime

import pytest
from conftest import START

from wcm import model


def make(**now) -> model.Initiative:
    init = model.Initiative(
        meta=model.new_meta(
            "INIT-0007",
            "Payment retries",
            type_="feature",
            status="paused",
            priority="high",
            created=START,
            tags=["payments"],
            workspace="/wt/payment-retries",
        )
    )
    init.now.update(now)
    return init


def test_round_trip_keeps_everything():
    init = make(Focus="Retry policy", Next="Finish backoff", Important="Idempotency first")
    text = model.render(init)
    again = model.parse(text)
    assert again.meta == init.meta
    assert again.now == init.now
    assert model.render(again) == text


def test_render_layout():
    text = model.render(make(Next="Finish backoff"))
    body = text.split("\n---\n", 1)[1]
    lines = [line for line in body.splitlines() if line.strip()]
    assert lines[0] == "# Payment retries"
    assert lines[1] == "## NOW"
    assert lines[2:7] == [
        "**Focus:**",
        "**Stopped at:**",
        "**Why it matters:**",
        "**Important:**",
        "**Next:** Finish backoff",
    ]


def test_empty_fields_render_with_no_text():
    text = model.render(make())
    assert "**Stopped at:**\n" in text
    assert "**Stopped at:** " not in text


def test_labels_in_any_order_are_read_and_rendered_canonically():
    text = """---
id: INIT-0007
status: paused
title: X
---

# X

## NOW

**Next:** Second
**Focus:** First
"""
    init = model.parse(text)
    assert init.now["Next"] == "Second"
    assert init.now["Focus"] == "First"
    rendered = model.render(init)
    assert rendered.index("**Focus:** First") < rendered.index("**Next:** Second")


def test_extra_line_inside_now_is_kept_and_counted():
    text = model.render(make(Next="Finish backoff")).replace(
        "**Next:** Finish backoff", "**Next:** Finish backoff\nA stray line someone wrote"
    )
    init = model.parse(text)
    assert init.now["Next"] == "Finish backoff"
    assert init.now_extra == ["A stray line someone wrote"]
    assert init.now_lines == 6
    assert "A stray line someone wrote" in model.render(init)


def test_now_values_are_single_lines():
    init = make(Next="line one\nline two")
    assert "**Next:** line one line two" in model.render(init)


def test_body_after_now_and_before_it_is_preserved():
    text = (
        model.render(make(Next="n")).replace("## NOW", "Some intro the person wrote.\n\n## NOW")
        + "\n## Notes\n\nFirst paragraph.\n\nSecond paragraph.\n"
    )
    init = model.parse(text)
    assert init.intro == "Some intro the person wrote."
    assert init.tail == "## Notes\n\nFirst paragraph.\n\nSecond paragraph."
    rendered = model.render(init)
    assert rendered.index("Some intro") < rendered.index("## NOW") < rendered.index("## Notes")


def test_unknown_frontmatter_keys_pass_through():
    text = model.render(make(Next="n")).replace("links: []\n", "links: []\nowner: ana\n")
    init = model.parse(text)
    assert "owner: ana" in model.render(init)


def test_primary_path():
    assert make().primary_path == "/wt/payment-retries"
    init = make()
    init.meta["workspaces"] = [{"path": "/a", "primary": False}]
    assert init.primary_path is None


def test_hand_written_timestamps_are_understood():
    text = """---
id: INIT-0002
status: paused
title: X
last_paused: 2026-09-16T10:00:00-03:00
---
"""
    init = model.parse(text)
    assert init.time("last_paused") == datetime.fromisoformat("2026-09-16T10:00:00-03:00")


@pytest.mark.parametrize(
    "text, reason",
    [
        ("no frontmatter\n", "does not start"),
        ("---\nid: INIT-0001\nstatus: paused\n", "no closing"),
        ("---\nid: 'INIT-0001\nstatus: paused\n---\n", "not valid YAML"),
        ("---\n- a list\n---\n", "not a mapping"),
        ("---\nstatus: paused\n---\n", "no id"),
        ("---\nid: INIT-0001\n---\n", "no status"),
        ("---\nid: INIT-0001\nstatus: archived\n---\n", "archived"),
    ],
)
def test_malformed(text, reason):
    with pytest.raises(model.MalformedError, match=reason):
        model.parse(text)


def test_invariants():
    paused = make()
    assert model.invariant_problems(paused) == ["INIT-0007 is paused without a next action"]
    paused.now["Next"] = "n"
    assert model.invariant_problems(paused) == []
    paused.meta["status"] = "waiting"
    paused.meta["waiting_on"] = {"what": "", "owner": "me"}
    assert model.invariant_problems(paused) == ["INIT-0007 is waiting without saying on what"]
    paused.meta["status"] = "active"
    paused.now["Next"] = ""
    assert model.invariant_problems(paused) == []


def test_body_without_now_is_stable():
    text = "---\nid: INIT-0001\nstatus: paused\ntitle: T\n---\n\n# T\n\nPara one.\n\nPara two.\n"
    once = model.render(model.parse(text))
    twice = model.render(model.parse(once))
    assert once == twice
    assert "Para one.\n\nPara two." in once
    assert once.index("Para one.") < once.index("## NOW")


def test_blank_lines_between_extra_now_lines_are_kept():
    text = model.render(make(Next="n")).replace(
        "**Next:** n", "**Next:** n\n- a bullet\n\nA loose paragraph\n\n\n\nAnother"
    )
    init = model.parse(text)
    assert init.now_extra == ["- a bullet", "", "A loose paragraph", "", "Another"]
    assert init.now_lines == 8
    assert model.render(model.parse(model.render(init))) == model.render(init)


def test_render_fills_missing_known_keys():
    init = model.parse("---\nid: INIT-0001\nstatus: paused\nowner: ana\n---\n")
    meta = model.parse(model.render(init)).meta
    assert meta["owner"] == "ana"
    assert (meta["type"], meta["priority"], meta["tags"], meta["workspaces"]) == (
        "other",
        "normal",
        [],
        [],
    )
