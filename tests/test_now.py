import os
from datetime import timedelta

import pytest
from conftest import START, write_initiative

from wcm import render


def ts(delta: timedelta) -> str:
    return (START - delta).isoformat()


# --- ages and truncation -----------------------------------------------------------


@pytest.mark.parametrize(
    "delta, text",
    [
        (timedelta(seconds=30), "0m"),
        (timedelta(minutes=23), "23m"),
        (timedelta(minutes=59, seconds=59), "59m"),
        (timedelta(minutes=60), "1h 0m"),
        (timedelta(hours=1, minutes=23), "1h 23m"),
        (timedelta(hours=23, minutes=59), "23h 59m"),
        (timedelta(hours=24), "1d"),
        (timedelta(hours=50), "2d"),
        (timedelta(days=13, hours=23), "13d"),
        (timedelta(days=14), "2w"),
        (timedelta(days=21), "3w"),
        (timedelta(minutes=-5), "0m"),
        (None, "?"),
    ],
)
def test_age_buckets(delta, text):
    assert render.age(delta) == text


def test_truncate():
    long = "x" * 300
    cut = render.truncate(long, 80)
    assert len(cut) == 80
    assert cut.endswith("…")
    assert render.truncate("short", 80) == "short"


# --- sections ---------------------------------------------------------------------


def test_typical_working_set(run, kb):
    write_initiative(
        kb,
        "INIT-0008",
        status="active",
        title="Login incident",
        last_resumed=ts(timedelta(hours=1)),
    )
    write_initiative(kb, "INIT-0007", title="Payment retries", last_paused=ts(timedelta(days=2)))
    write_initiative(kb, "INIT-0005", title="Security analysis", last_paused=ts(timedelta(hours=5)))
    out = run("now").out
    assert out.index("ACTIVE") < out.index("INIT-0008") < out.index("PAUSED")
    assert out.index("PAUSED") < out.index("INIT-0005") < out.index("INIT-0007")
    assert "Next: Do the thing" in out


def test_empty_store(run):
    result = run("now")
    assert result.code == 0
    assert result.out.strip().count("\n") == 0
    assert "wcm new" in result.out


def test_nothing_active(run, kb):
    write_initiative(kb, "INIT-0005")
    write_initiative(kb, "INIT-0007")
    out = run("now").out
    assert "ACTIVE" not in out
    assert "PAUSED" in out and "INIT-0005" in out and "INIT-0007" in out


def test_done_initiatives_are_not_listed(run, kb):
    write_initiative(kb, "INIT-0002", status="done", location="done")
    out = run("now").out
    assert "INIT-0002" not in out
    assert "wcm new" in out


def test_two_lines_per_initiative(run, kb):
    write_initiative(kb, "INIT-0007", title="Payment retries", next_="Finish backoff")
    lines = run("now").out.splitlines()
    i = next(n for n, line in enumerate(lines) if "INIT-0007" in line)
    assert "Payment retries" in lines[i]
    assert lines[i + 1].strip() == "Next: Finish backoff"


def test_priority_shown_only_when_notable(run, kb):
    write_initiative(
        kb, "INIT-0008", status="active", priority="critical", last_resumed=ts(timedelta(minutes=5))
    )
    write_initiative(kb, "INIT-0007")
    lines = run("now").out.splitlines()
    line8 = next(line for line in lines if "INIT-0008" in line)
    line7 = next(line for line in lines if "INIT-0007" in line)
    assert "critical" in line8
    assert not any(p in line7 for p in ("critical", "high", "normal", "low"))


def test_long_next_action_is_truncated(run, kb, monkeypatch):
    monkeypatch.setenv("COLUMNS", "80")
    write_initiative(kb, "INIT-0007", next_="y" * 300)
    line = next(line for line in run("now").out.splitlines() if "Next:" in line)
    assert len(line) <= 80
    assert line.endswith("…")


def test_paused_two_days_ago(run, kb):
    write_initiative(kb, "INIT-0007", last_paused=ts(timedelta(hours=50)))
    line = next(line for line in run("now").out.splitlines() if "INIT-0007" in line)
    assert line.rstrip().endswith("2d")


def test_missing_timestamp(run, kb):
    write_initiative(kb, "INIT-0007", last_paused="null")
    line = next(line for line in run("now").out.splitlines() if "INIT-0007" in line)
    assert line.rstrip().endswith("?")


def test_priority_before_recency(run, kb):
    write_initiative(kb, "INIT-0005", priority="high", last_paused=ts(timedelta(days=5)))
    write_initiative(kb, "INIT-0007", last_paused=ts(timedelta(hours=1)))
    out = run("now").out
    assert out.index("INIT-0005") < out.index("INIT-0007")


# --- stale active -----------------------------------------------------------------


def test_active_for_six_hours(run, kb, fake_clock):
    run("new", "Login incident")
    fake_clock.advance(hours=6)
    out = run("now").out
    warning = next(line for line in out.splitlines() if line.startswith("!"))
    assert "INIT-0001" in warning and "6h" in warning and "wcm pause" in warning


def test_four_hours_is_not_stale(run, kb, fake_clock):
    run("new", "Login incident")
    fake_clock.advance(hours=4)
    assert "!" not in run("now").out


def test_recently_resumed_after_a_long_pause(run, kb, fake_clock):
    run("new", "Payment retries")
    run("pause", "-n", "x")
    fake_clock.advance(days=3)
    run("resume", "1")
    fake_clock.advance(minutes=30)
    assert "without a checkpoint" not in run("now").out


def test_a_recent_checkpoint_counts(run, kb, fake_clock):
    write_initiative(kb, "INIT-0008", status="active", last_resumed=ts(timedelta(hours=10)))
    cp = (
        kb
        / "initiatives"
        / "INIT-0008"
        / "checkpoints"
        / (START - timedelta(hours=1)).strftime("%Y-%m-%dT%H%M%S.md")
    )
    cp.write_text("# Checkpoint\n", encoding="utf-8")
    assert "without a checkpoint" not in run("now").out


# --- warnings -----------------------------------------------------------------------


def test_missing_path_warned(run, kb, tmp_path):
    gone = tmp_path / "gone"
    write_initiative(kb, "INIT-0007", workspaces=f"[{{path: '{gone}', primary: true}}]")
    result = run("now")
    assert result.code == 0
    warning = next(line for line in result.out.splitlines() if line.startswith("!"))
    assert "INIT-0007" in warning and str(gone) in warning


def test_two_active_warned(run, kb):
    write_initiative(kb, "INIT-0003", status="active", last_resumed=ts(timedelta(minutes=5)))
    write_initiative(kb, "INIT-0004", status="active", last_resumed=ts(timedelta(minutes=5)))
    out = run("now").out
    active = out[out.index("ACTIVE") :]
    assert "INIT-0003" in active and "INIT-0004" in active
    assert "More than one initiative is active" in out


def test_waiting_initiative_is_not_hidden(run, kb):
    write_initiative(
        kb, "INIT-0003", status="waiting", waiting_on="{what: architecture approval, owner: Ana}"
    )
    out = run("now").out
    warning = next(line for line in out.splitlines() if "INIT-0003" in line)
    assert warning.startswith("!")
    assert "architecture approval" in warning
    assert "wcm new" not in out


def test_waiting_without_what_warned(run, kb):
    write_initiative(kb, "INIT-0003", status="waiting", waiting_on="{what: '', owner: me}")
    assert "INIT-0003 is waiting without saying on what" in run("now").out


def test_now_changes_no_file(run, kb, tmp_path):
    write_initiative(kb, "INIT-0003", status="active", last_resumed=ts(timedelta(hours=9)))
    write_initiative(
        kb, "INIT-0007", next_="", workspaces=f"[{{path: '{tmp_path / 'gone'}', primary: true}}]"
    )
    write_initiative(kb, "INIT-0005", title="'broken")
    before = {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in kb.rglob("*") if p.is_file()}
    listing = sorted(kb.rglob("*"))
    result = run("now")
    assert result.code == 0
    assert result.out.count("!") >= 4
    assert {
        p: (p.stat().st_mtime_ns, p.read_bytes()) for p in kb.rglob("*") if p.is_file()
    } == before
    assert sorted(kb.rglob("*")) == listing


def test_run_from_two_directories(run, kb, tmp_path, monkeypatch):
    write_initiative(kb, "INIT-0007")
    monkeypatch.chdir(tmp_path.anchor or os.sep)
    first = run("now").out
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.chdir(repo)
    assert run("now").out == first
