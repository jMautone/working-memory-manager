import pytest
from conftest import checkpoints, load, path_of, write_initiative


def triggers(kb, initiative_id, location="initiatives"):
    return [
        line.removeprefix("Trigger: ")
        for p in checkpoints(kb, initiative_id, location)
        for line in p.read_text(encoding="utf-8").splitlines()
        if line.startswith("Trigger: ")
    ]


# --- exit codes ------------------------------------------------------------------


@pytest.mark.parametrize("command", ["new", "now", "pause", "resume", "done"])
def test_help_for_each_command(run, command):
    result = run(command, "--help")
    assert result.code == 0
    assert "usage: wcm" in result.out


def test_top_level_help_lists_the_five_commands(run):
    result = run("--help")
    for command in ("new", "now", "pause", "resume", "done"):
        assert command in result.out


def test_unknown_command(run):
    result = run("frobnicate")
    assert result.code == 2
    assert "usage" in result.err


def test_no_command_is_a_usage_error(run):
    assert run().code == 2


def test_four_states_only(run, kb):
    write_initiative(kb, "INIT-0002", status="archived")
    result = run("now")
    assert "archived" in result.out
    assert "PAUSED" not in result.out


# --- new -------------------------------------------------------------------------


def test_first_initiative_becomes_active(run, kb):
    write_initiative(kb, "INIT-0006")
    result = run("new", "Payment retries")
    assert result.code == 0
    assert "INIT-0007 active" in result.out
    init = load(kb, "INIT-0007")
    assert init.status == "active"
    assert init.meta["last_resumed"] == "2026-09-16T09:00:00-03:00"


def test_creating_while_another_is_active_switches(run, kb):
    write_initiative(kb, "INIT-0006")
    run("new", "Payment retries")
    result = run(
        "new",
        "Login incident",
        "--type",
        "incident",
        "--priority",
        "critical",
        "--next",
        "Reproduce the lockout race",
        "--pause-next",
        "Finish PaymentRetryPolicy",
        answers=[],
    )
    assert result.code == 0
    old, new = load(kb, "INIT-0007"), load(kb, "INIT-0008")
    assert old.status == "paused"
    assert old.now["Next"] == "Finish PaymentRetryPolicy"
    assert new.status == "active"
    assert new.now["Next"] == "Reproduce the lockout race"
    assert triggers(kb, "INIT-0007") == ["switch"]
    assert "[" not in result.out  # no prompt was shown


def test_creating_while_another_is_active_prompts_without_pause_next(run, kb):
    run("new", "A", "--next", "a next")
    result = run("new", "B", answers=["", "", ""])
    assert result.code == 0
    assert "Next action" in result.out
    assert load(kb, "INIT-0001").status == "paused"


def test_paused_creation_needs_a_next_action(run, kb):
    result = run("new", "Later thing", "--paused")
    assert result.code == 1
    assert "next action" in result.err
    assert not kb.exists() or not any(kb.rglob("*.md"))


def test_paused_creation_leaves_the_active_one(run, kb):
    run("new", "A")
    result = run("new", "B", "--paused", "--next", "b")
    assert result.code == 0
    assert "INIT-0002 paused" in result.out
    assert load(kb, "INIT-0001").status == "active"
    b = load(kb, "INIT-0002")
    assert b.status == "paused"
    assert b.meta["last_paused"] == "2026-09-16T09:00:00-03:00"


def test_new_refused_when_the_outgoing_pause_is_refused(run, kb):
    run("new", "A")
    result = run("new", "B", tty=False)
    assert result.code == 1
    assert "-n" in result.err
    assert load(kb, "INIT-0001").status == "active"
    assert not path_of(kb, "INIT-0002").exists()


def test_path_that_does_not_exist(run, kb, tmp_path):
    missing = tmp_path / "nope"
    result = run("new", "Spike", "--path", missing)
    assert result.code == 0
    assert load(kb, "INIT-0001").primary_path == str(missing)
    assert "does not exist" in result.out


def test_tags_focus_and_why(run, kb):
    run("new", "X", "--tags", "a, b,,c", "--focus", "The focus", "--why", "Because")
    init = load(kb, "INIT-0001")
    assert init.meta["tags"] == ["a", "b", "c"]
    assert init.now["Focus"] == "The focus"
    assert init.now["Why it matters"] == "Because"


def test_empty_title_is_refused(run):
    assert run("new", "  ").code == 1


# --- at most one active ----------------------------------------------------------


def test_two_active_on_disk_refuse_activation(run, kb):
    a = write_initiative(kb, "INIT-0003", status="active")
    b = write_initiative(kb, "INIT-0004", status="active")
    c = write_initiative(kb, "INIT-0007")
    before = {p: p.read_bytes() for p in (a, b, c)}
    result = run("resume", "INIT-0007", answers=["", "", ""])
    assert result.code == 1
    assert "INIT-0003/INIT-0003.md" in result.err
    assert "INIT-0004/INIT-0004.md" in result.err
    assert {p: p.read_bytes() for p in (a, b, c)} == before
    assert run("new", "Another").code == 1


# --- resume ----------------------------------------------------------------------


def test_resume_with_another_active(run, kb, fake_clock):
    write_initiative(kb, "INIT-0007", last_paused="2026-09-14T09:00:00-03:00")
    write_initiative(kb, "INIT-0008", status="active", next_="Keep going")
    result = run("resume", "INIT-0007", answers=["", "", ""])
    assert result.code == 0
    assert load(kb, "INIT-0008").status == "paused"
    assert triggers(kb, "INIT-0008") == ["switch"]
    target = load(kb, "INIT-0007")
    assert target.status == "active"
    assert target.meta["last_resumed"] == "2026-09-16T09:00:00-03:00"


def test_resume_without_a_terminal_keeps_the_outgoing_values(run, kb):
    write_initiative(kb, "INIT-0007")
    write_initiative(kb, "INIT-0008", status="active", next_="Keep going")
    result = run("resume", "7", tty=False)
    assert result.code == 0
    assert load(kb, "INIT-0008").now["Next"] == "Keep going"


def test_resume_a_waiting_initiative(run, kb):
    write_initiative(
        kb,
        "INIT-0003",
        status="waiting",
        waiting_on="{what: architecture approval, owner: Ana, since: '2026-09-10T09:00:00-03:00'}",
    )
    result = run("resume", "INIT-0003")
    assert result.code == 0
    init = load(kb, "INIT-0003")
    assert init.status == "active"
    assert init.meta["waiting_on"] is None
    assert "architecture approval" in result.out


def test_resume_a_done_initiative(run, kb):
    write_initiative(kb, "INIT-0002", status="done", location="done")
    result = run("resume", "INIT-0002")
    assert result.code == 1
    assert "move done/INIT-0002 back" in result.err


def test_resume_an_unknown_id(run, kb):
    result = run("resume", "INIT-0099")
    assert result.code == 1
    assert "INIT-0099 was not found" in result.err


def test_back_in_a_new_terminal(run, kb, fake_clock):
    run("new", "Payment retries", "--next", "Finish backoff")
    before = path_of(kb, "INIT-0001").read_bytes()
    fake_clock.advance(hours=1, minutes=5)
    result = run("resume")
    assert result.code == 0
    assert "INIT-0001 Payment retries" in result.out
    assert "active for 1h 5m" in result.out
    assert "Finish backoff" in result.out
    assert path_of(kb, "INIT-0001").read_bytes() == before
    assert checkpoints(kb, "INIT-0001") == []


def test_resume_the_active_one_by_id(run, kb):
    run("new", "Payment retries", "--next", "Finish backoff")
    before = path_of(kb, "INIT-0001").read_bytes()
    by_id = run("resume", "INIT-0001")
    without = run("resume")
    assert by_id.code == without.code == 0
    assert by_id.out == without.out
    assert path_of(kb, "INIT-0001").read_bytes() == before


def test_nothing_active_and_no_id(run, kb):
    write_initiative(kb, "INIT-0005", title="Security analysis")
    write_initiative(kb, "INIT-0007", title="Payment retries")
    result = run("resume")
    assert result.code == 1
    assert "INIT-0005" in result.out
    assert "INIT-0007" in result.out


# --- pause -----------------------------------------------------------------------


def test_pause_the_active_initiative(run, kb, fake_clock):
    run("new", "Payment retries")
    fake_clock.advance(minutes=30)
    result = run("pause", "-n", "Finish PaymentRetryPolicy")
    assert result.code == 0
    init = load(kb, "INIT-0001")
    assert init.status == "paused"
    assert init.meta["last_paused"] == "2026-09-16T09:30:00-03:00"
    assert result.out.rstrip().endswith("Safe to switch context.")
    assert "Checkpoint saved." in result.out
    assert run("pause", tty=False).code == 1  # no initiative is active any more


def test_nothing_to_pause(run):
    result = run("pause")
    assert result.code == 1
    assert "no initiative is active" in result.err


def test_pause_refuses_without_a_next_action(run, kb):
    run("new", "Payment retries")
    result = run("pause", answers=["", "", ""])
    assert result.code == 1
    assert "next action is required" in result.err
    assert load(kb, "INIT-0001").status == "active"
    assert checkpoints(kb, "INIT-0001") == []


def test_pause_an_already_paused_initiative(run, kb):
    write_initiative(kb, "INIT-0007", next_="Old")
    result = run("pause", "7", "-n", "New")
    assert result.code == 0
    assert load(kb, "INIT-0007").now["Next"] == "New"
    assert triggers(kb, "INIT-0007") == ["pause"]


def test_pause_clears_waiting_on(run, kb):
    write_initiative(kb, "INIT-0003", status="waiting", waiting_on="{what: approval, owner: me}")
    assert run("pause", "3", "-n", "x").code == 0
    init = load(kb, "INIT-0003")
    assert init.status == "paused"
    assert init.meta["waiting_on"] is None


def test_pause_a_done_initiative_is_refused(run, kb):
    write_initiative(kb, "INIT-0002", status="done", location="done")
    assert run("pause", "2", "-n", "x").code == 1


# --- done ------------------------------------------------------------------------


def test_close_the_active_initiative(run, kb):
    run("new", "Login incident")
    result = run("done")
    assert result.code == 0
    init = load(kb, "INIT-0001", "done")
    assert init.status == "done"
    assert init.meta["closed"] == "2026-09-16T09:00:00-03:00"
    assert triggers(kb, "INIT-0001", "done") == ["done"]
    assert not (kb / "initiatives" / "INIT-0001").exists()
    assert "ACTIVE" not in run("now").out


def test_close_a_paused_initiative(run, kb):
    write_initiative(kb, "INIT-0005")
    run("new", "Active one")
    assert run("done", "INIT-0005").code == 0
    assert load(kb, "INIT-0005", "done").status == "done"
    assert load(kb, "INIT-0006").status == "active"


def test_close_a_waiting_initiative(run, kb):
    write_initiative(
        kb, "INIT-0003", status="waiting", waiting_on="{what: architecture approval, owner: Ana}"
    )
    assert run("done", "INIT-0003").code == 0
    init = load(kb, "INIT-0003", "done")
    assert init.status == "done"
    assert init.meta["waiting_on"]["what"] == "architecture approval"


def test_moved_directory_keeps_its_checkpoints(run, kb):
    run("new", "A")
    run("pause", "-n", "a")
    run("resume", "1")
    run("done")
    assert len(checkpoints(kb, "INIT-0001", "done")) == 2


def test_close_an_already_done_initiative(run, kb):
    write_initiative(kb, "INIT-0002", status="done", location="done")
    result = run("done", "2")
    assert result.code == 1
    assert "already done" in result.err


def test_done_does_not_need_a_next_action(run, kb):
    run("new", "A")
    assert run("done").code == 0


# --- invariants and target resolution ---------------------------------------------


def test_hand_edited_paused_initiative_without_next(run, kb):
    write_initiative(kb, "INIT-0007", next_="")
    result = run("now")
    assert "PAUSED" in result.out
    assert "INIT-0007 is paused without a next action" in result.out


@pytest.mark.parametrize("command", [["done"], ["pause", "-n", "x"]])
def test_no_active_for_commands_with_an_optional_id(run, kb, command):
    write_initiative(kb, "INIT-0007")
    before = load(kb, "INIT-0007").meta
    result = run(*command)
    assert result.code == 1
    assert "no initiative is active" in result.err
    assert "wcm now" in result.err
    assert load(kb, "INIT-0007").meta == before
