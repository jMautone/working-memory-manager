from datetime import timedelta

from conftest import START, checkpoints, load, path_of, write_initiative

from wcm import checkpoint


def non_blank(text):
    return [line for line in text.splitlines() if line.strip()]


def after(lines, heading):
    return lines[lines.index(heading) + 1]


# --- NOW block -------------------------------------------------------------------


def test_now_written_on_creation(run, kb):
    run(
        "new",
        "Payment retries",
        "--why",
        "Provider may return the same transaction ID after a timeout",
    )
    lines = non_blank(path_of(kb, "INIT-0001").read_text(encoding="utf-8").split("\n---\n", 1)[1])
    assert lines == [
        "# Payment retries",
        "## NOW",
        "**Focus:** Payment retries",
        "**Stopped at:**",
        "**Why it matters:** Provider may return the same transaction ID after a timeout",
        "**Important:**",
        "**Next:**",
    ]


def test_focus_defaults_to_the_title(run, kb):
    run("new", "Payment retries")
    assert load(kb, "INIT-0001").now["Focus"] == "Payment retries"


def test_two_pauses_leave_one_now(run, kb):
    run("new", "Payment retries")
    run("pause", "-n", "Finish backoff")
    run("resume", "1")
    run("pause", "-n", "Verify duplicates")
    text = path_of(kb, "INIT-0001").read_text(encoding="utf-8")
    assert text.count("## NOW") == 1
    assert "**Next:** Verify duplicates" in text
    assert "Finish backoff" not in text


# --- pause flow with prompts ------------------------------------------------------


def test_three_enters_is_a_valid_pause(run, kb):
    run("new", "Payment retries", "--next", "Finish backoff")
    before = load(kb, "INIT-0001").now
    result = run("pause", answers=["", "", ""])
    assert result.code == 0
    assert result.out.index("INIT-0001 Payment retries") < result.out.index("Next action")
    assert "[Finish backoff]" in result.out
    assert load(kb, "INIT-0001").now == before
    assert len(checkpoints(kb, "INIT-0001")) == 1
    assert result.out.rstrip().endswith("Safe to switch context.")


def test_prompts_come_in_order(run, kb):
    run("new", "Payment retries", "--next", "n")
    out = run("pause", answers=["", "", ""]).out
    assert out.index("Next action") < out.index("Stopped at") < out.index("Important")
    assert "Focus" not in out
    assert "Why it matters" not in out


def test_typed_text_replaces(run, kb):
    run("new", "Payment retries", "--next", "Finish backoff")
    run("pause", answers=["Verify duplicate handling", "", ""])
    init = load(kb, "INIT-0001")
    assert init.now["Next"] == "Verify duplicate handling"
    assert init.now["Stopped at"] == ""


def test_dash_clears_a_field(run, kb):
    run("new", "Payment retries", "--next", "n")
    run("pause", "-n", "n", "-i", "Idempotency first")
    run("resume", "1")
    run("pause", answers=["", "", "-"])
    assert load(kb, "INIT-0001").now["Important"] == ""


def test_next_cannot_be_cleared(run, kb):
    run("new", "Payment retries", "--next", "n")
    result = run("pause", answers=["-"])
    assert result.code == 1
    assert "next action is required" in result.err
    assert load(kb, "INIT-0001").status == "active"
    assert checkpoints(kb, "INIT-0001") == []


# --- pause flow without prompts ---------------------------------------------------


def test_urgent_pause_with_a_flag(run, kb):
    run("new", "Payment retries")
    run("pause", "-n", "x", "-s", "Halfway", "-i", "Careful")
    run("resume", "1")
    result = run("pause", "-n", "Finish backoff", answers=[])
    assert result.code == 0
    assert "[" not in result.out
    init = load(kb, "INIT-0001")
    assert init.now["Next"] == "Finish backoff"
    assert init.now["Stopped at"] == "Halfway"
    assert init.now["Important"] == "Careful"
    assert len(checkpoints(kb, "INIT-0001")) == 2


def test_piped_stdin_with_a_prior_next(run, kb):
    run("new", "Payment retries", "--next", "Finish backoff")
    before = load(kb, "INIT-0001").now
    result = run("pause", tty=False)
    assert result.code == 0
    assert "Next action" not in result.out
    assert load(kb, "INIT-0001").now == before


def test_piped_stdin_without_a_next(run, kb):
    run("new", "Payment retries")
    result = run("pause", tty=False)
    assert result.code == 1
    assert "next action is required" in result.err
    assert "-n" in result.err
    assert load(kb, "INIT-0001").status == "active"


# --- checkpoints ------------------------------------------------------------------


def test_checkpoint_written_on_pause(run, kb, fake_clock):
    run("new", "Payment retries")
    run("pause", "-n", "x", "-s", "backoff incomplete")
    run("resume", "1")
    fake_clock.advance(minutes=1)
    run("pause", "-n", "Finish backoff")
    latest = checkpoints(kb, "INIT-0001")[-1]
    lines = non_blank(latest.read_text(encoding="utf-8"))
    assert lines[0].startswith("# Checkpoint 2026-09-16T09:01:00")
    assert lines[1] == "Author: human"
    assert lines[2] == "Trigger: pause"
    assert after(lines, "## Incomplete work") == "backoff incomplete"
    assert after(lines, "## Next action") == "Finish backoff"
    assert after(lines, "## Focus") == "Payment retries"
    for heading in (
        "## Completed since previous checkpoint",
        "## Discoveries",
        "## Open questions",
    ):
        assert heading in lines


def test_checkpoint_name_is_local_time(run, kb):
    run("new", "Payment retries")
    run("pause", "-n", "x")
    assert [p.name for p in checkpoints(kb, "INIT-0001")] == ["2026-09-16T090000.md"]


def test_two_checkpoints_in_the_same_second(run, kb):
    run("new", "Payment retries")
    run("pause", "-n", "x")
    run("resume", "1")
    run("pause", "-n", "y")
    assert [p.name for p in checkpoints(kb, "INIT-0001")] == [
        "2026-09-16T090000-2.md",
        "2026-09-16T090000.md",
    ]


def test_file_name_suffixes():
    assert checkpoint.file_name(START, set()) == "2026-09-16T090000.md"
    taken = {"2026-09-16T090000.md", "2026-09-16T090000-2.md"}
    assert checkpoint.file_name(START, taken) == "2026-09-16T090000-3.md"
    assert checkpoint.time_of("2026-09-16T090000-3.md", START.tzinfo) == START
    assert checkpoint.time_of("notes.md", START.tzinfo) is None


def test_earlier_checkpoint_untouched(run, kb, fake_clock):
    run("new", "Payment retries")
    run("pause", "-n", "x")
    first = checkpoints(kb, "INIT-0001")[0]
    content = first.read_bytes()
    fake_clock.advance(minutes=1)
    run("resume", "1")
    run("pause", "-n", "y")
    assert first.read_bytes() == content
    assert len(checkpoints(kb, "INIT-0001")) == 2


# --- resume brief -----------------------------------------------------------------


def test_brief_after_two_days(run, kb, fake_clock, tmp_path):
    wt = tmp_path / "wt"
    wt.mkdir()
    run(
        "new",
        "Payment retries",
        "--focus",
        "Retry policy",
        "--why",
        "Duplicate IDs",
        "--path",
        wt,
    )
    run("pause", "-n", "Finish backoff", "-s", "Backoff incomplete", "-i", "Idempotency")
    fake_clock.advance(days=2, hours=2)
    result = run("resume", "INIT-0001")
    out = result.out
    assert "INIT-0001" in out and "Payment retries" in out
    assert "paused 2d ago" in out
    for value in (
        "Retry policy",
        "Backoff incomplete",
        "Duplicate IDs",
        "Idempotency",
        "Finish backoff",
    ):
        assert value in out
    assert "Path:" in out
    assert out.index("Retry policy") < out.index("Backoff incomplete") < out.index("Finish backoff")
    assert "Checkpoint" not in out


def test_empty_fields_are_skipped(run, kb):
    write_initiative(kb, "INIT-0009", next_="Go")
    out = run("resume", "INIT-0009").out
    assert "Stopped at" not in out
    assert "Important" not in out
    assert "Next:" in out


def test_long_now_warns(run, kb):
    extra = "".join(f"line {n}\n" for n in range(15))
    write_initiative(kb, "INIT-0007", body_extra=extra)
    out = run("now").out
    assert "INIT-0007 has a NOW block of 20 lines" in out
    assert "history" in out


def test_a_now_of_fifteen_lines_does_not_warn(run, kb):
    extra = "".join(f"line {n}\n" for n in range(10))
    write_initiative(kb, "INIT-0007", body_extra=extra)
    assert "NOW block" not in run("now").out


def test_brief_waiting_line(run, kb, fake_clock):
    since = (START - timedelta(days=3)).isoformat()
    write_initiative(
        kb,
        "INIT-0003",
        status="waiting",
        waiting_on=f"{{what: approval, owner: Ana, since: '{since}'}}",
    )
    out = run("resume", "3").out
    assert "waiting for 3d on: approval (owner: Ana)" in out
