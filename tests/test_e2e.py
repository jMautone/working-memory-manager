"""The Phase 1 exit sequence (plan §14), run end to end through the CLI."""

from conftest import checkpoints, load


def triggers(kb, initiative_id, location="initiatives"):
    out = []
    for p in checkpoints(kb, initiative_id, location):
        out += [
            line.removeprefix("Trigger: ")
            for line in p.read_text(encoding="utf-8").splitlines()
            if line.startswith("Trigger: ")
        ]
    return sorted(out)


def states(kb):
    found = {}
    for location in ("initiatives", "done"):
        base = kb / location
        if base.is_dir():
            for d in base.iterdir():
                found[d.name] = load(kb, d.name, location)
    return found


def check_invariants(kb):
    found = states(kb)
    assert sum(1 for i in found.values() if i.status == "active") <= 1
    for init in found.values():
        if init.status == "paused":
            assert init.now["Next"], f"{init.id} is paused without a next action"


def test_phase_one_exit_sequence(run, kb, fake_clock):
    steps = [
        (("new", "Payment retries", "--type", "feature", "--next", "Write the policy"), None),
        (("pause", "-n", "Finish backoff"), None),
        (("new", "Security analysis", "--type", "research", "--next", "Map the flows"), None),
        (("pause", "-n", "Validate token refresh"), None),
        (
            (
                "new",
                "Login incident",
                "--type",
                "incident",
                "--priority",
                "critical",
                "--next",
                "Reproduce",
            ),
            None,
        ),
        (("done",), None),
        (("resume", "1"), None),
        (("pause",), ["Verify duplicates", "", ""]),
        (("resume", "2"), None),
    ]
    for argv, answers in steps:
        fake_clock.advance(minutes=20)
        result = run(*argv, answers=answers, tty=answers is not None)
        assert result.code == 0, (argv, result.err)
        check_invariants(kb)

    a, b = load(kb, "INIT-0001"), load(kb, "INIT-0002")
    c = load(kb, "INIT-0003", "done")
    assert (a.status, b.status, c.status) == ("paused", "active", "done")
    assert a.now["Next"] == "Verify duplicates"
    assert b.now["Next"] == "Validate token refresh"
    assert triggers(kb, "INIT-0001") == ["pause", "pause"]
    assert triggers(kb, "INIT-0002") == ["pause"]
    assert triggers(kb, "INIT-0003", "done") == ["done"]
    assert not (kb / "initiatives" / "INIT-0003").exists()

    out = run("now").out
    assert (
        out.index("ACTIVE") < out.index("INIT-0002") < out.index("PAUSED") < out.index("INIT-0001")
    )
    assert "INIT-0003" not in out
