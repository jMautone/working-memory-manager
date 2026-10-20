import os

import pytest
from conftest import load, path_of, write_initiative

from wcm import store


def test_default_hub(run, monkeypatch, tmp_path):
    home = tmp_path / "home"
    monkeypatch.delenv("WCM_HOME")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    assert run("new", "Payment retries").code == 0
    assert (home / ".wcm" / "kbs" / "work" / "initiatives" / "INIT-0001").is_dir()


def test_hub_override(run, hub, tmp_path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    assert run("new", "Payment retries").code == 0
    assert path_of(hub / "kbs" / "work", "INIT-0001").is_file()
    assert not (home / ".wcm").exists()


def test_nothing_is_written_under_the_current_directory(run, tmp_path, monkeypatch):
    cwd = tmp_path / "repo"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    run("new", "Payment retries")
    run("pause", "-n", "Finish backoff")
    run("now")
    run("resume", "1", tty=False)
    run("done")
    assert list(cwd.iterdir()) == []


def test_now_on_an_empty_hub_creates_nothing(run, hub):
    assert run("now").code == 0
    assert not hub.exists()


def test_new_initiative_layout(run, kb):
    write_initiative(kb, "INIT-0006")
    run("new", "Payment retries", "--paused", "--next", "x")
    assert path_of(kb, "INIT-0007").is_file()
    assert (kb / "initiatives" / "INIT-0007" / "checkpoints").is_dir()
    assert list((kb / "initiatives" / "INIT-0007" / "checkpoints").iterdir()) == []


def test_frontmatter_written_on_creation(run, kb, tmp_path):
    workdir = tmp_path / "wt"
    workdir.mkdir()
    result = run(
        "new", "Payment", "retries", "--type", "feature", "--priority", "high", "--path", workdir
    )
    assert result.code == 0
    init = load(kb, "INIT-0001")
    meta = init.meta
    assert meta["id"] == "INIT-0001"
    assert meta["title"] == "Payment retries"
    assert (meta["type"], meta["status"], meta["priority"]) == ("feature", "active", "high")
    assert meta["workspaces"] == [{"path": os.path.abspath(workdir), "primary": True}]
    assert meta["last_paused"] is None
    assert meta["waiting_on"] is None
    assert meta["created"] == "2026-09-16T09:00:00-03:00"
    for key in ("updated", "last_resumed", "tags", "links"):
        assert key in meta


def test_relative_path_is_made_absolute(run, kb, tmp_path, monkeypatch):
    (tmp_path / "wt").mkdir()
    monkeypatch.chdir(tmp_path)
    run("new", "X", "--path", "wt")
    assert load(kb, "INIT-0001").primary_path == os.path.join(os.getcwd(), "wt")


def test_creation_without_a_path(run, kb):
    run("new", "Research CRDTs")
    assert load(kb, "INIT-0001").meta["workspaces"] == []


def test_body_starts_with_the_title(run, kb):
    run("new", "Payment retries")
    text = path_of(kb, "INIT-0001").read_text(encoding="utf-8")
    body = [line for line in text.split("\n---\n", 1)[1].splitlines() if line.strip()]
    assert body[0] == "# Payment retries"
    assert body[1] == "## NOW"


def test_files_are_utf8_without_bom_and_lf(run, kb):
    run("new", "Café ñandú")
    raw = path_of(kb, "INIT-0001").read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert b"\r\n" not in raw
    assert "Café ñandú".encode() in raw


def test_updated_tracks_writes(run, kb, fake_clock):
    run("new", "Payment retries")
    created = load(kb, "INIT-0001").meta["created"]
    fake_clock.advance(hours=1)
    run("pause", "-n", "Finish backoff")
    meta = load(kb, "INIT-0001").meta
    assert meta["updated"] == "2026-09-16T10:00:00-03:00"
    assert meta["created"] == created


def test_now_does_not_touch_updated(run, kb, fake_clock):
    run("new", "Payment retries")
    before = path_of(kb, "INIT-0001").read_bytes()
    fake_clock.advance(hours=1)
    run("now")
    assert path_of(kb, "INIT-0001").read_bytes() == before


def test_other_initiatives_are_not_touched(run, kb, fake_clock):
    run("new", "A", "--paused", "--next", "a")
    before = path_of(kb, "INIT-0001").read_bytes()
    fake_clock.advance(hours=1)
    run("new", "B")
    run("pause", "-n", "b")
    assert path_of(kb, "INIT-0001").read_bytes() == before


def test_hand_edits_survive_a_rewrite(run, kb):
    run("new", "Payment retries")
    path = path_of(kb, "INIT-0001")
    text = path.read_text(encoding="utf-8")
    text = text.replace("links: []\n", "links: []\nowner: ana\n")
    text += "\n## Notes\n\nFirst paragraph.\n\nSecond paragraph.\n\nThird paragraph.\n"
    path.write_text(text, encoding="utf-8")
    assert run("pause", "-n", "Finish backoff").code == 0
    rewritten = path.read_text(encoding="utf-8")
    assert "owner: ana" in rewritten
    notes = "## Notes\n\nFirst paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    assert notes in rewritten
    assert rewritten.index("**Next:** Finish backoff") < rewritten.index("## Notes")


def test_no_temporary_file_remains(run, kb):
    run("new", "Payment retries")
    run("pause", "-n", "x")
    leftovers = [p for p in kb.rglob("*") if p.name.endswith(".tmp")]
    assert leftovers == []


def test_interrupted_rewrite_keeps_the_previous_file(run, kb, monkeypatch):
    run("new", "Payment retries")
    path = path_of(kb, "INIT-0001")
    before = path.read_bytes()

    def boom(src, dst):
        raise OSError("killed")

    monkeypatch.setattr(os, "replace", boom)
    result = run("pause", "-n", "x")
    assert result.code == 1
    assert path.read_bytes() == before
    assert not path.with_name(path.name + ".tmp").exists()


@pytest.mark.parametrize("form", ["7", "init-7", "INIT-0007", "Init-0007"])
def test_short_ids_are_accepted(run, kb, form):
    write_initiative(kb, "INIT-0007", next_="Go on")
    result = run("resume", form)
    assert result.code == 0
    assert load(kb, "INIT-0007").status == "active"


def test_empty_store_gets_init_0001(run, kb):
    run("new", "First")
    assert path_of(kb, "INIT-0001").is_file()


def test_highest_id_lives_in_done(run, kb):
    write_initiative(kb, "INIT-0003")
    write_initiative(kb, "INIT-0009", status="done", location="done")
    run("new", "Next", "--paused", "--next", "x")
    assert path_of(kb, "INIT-0010").is_file()


def test_gap_is_not_reused(run, kb):
    for n in (1, 2, 3, 5, 6):
        write_initiative(kb, f"INIT-{n:04d}")
    run("new", "Next", "--paused", "--next", "x")
    assert path_of(kb, "INIT-0007").is_file()
    assert not path_of(kb, "INIT-0004").exists()


def test_hand_written_initiative_is_listed(run, kb):
    write_initiative(kb, "INIT-0002", title="Notes", next_="Read them")
    result = run("now")
    assert "PAUSED" in result.out
    assert "INIT-0002" in result.out


def test_obsidian_and_unknown_files_are_ignored(run, kb):
    obsidian = kb / ".obsidian"
    obsidian.mkdir(parents=True)
    (obsidian / "app.json").write_text("{}", encoding="utf-8")
    (kb / "initiatives").mkdir()
    readme = kb / "initiatives" / "README.md"
    readme.write_text("my notes", encoding="utf-8")
    (kb / "initiatives" / "INIT-9999.md").write_text("not a directory", encoding="utf-8")
    result = run("now")
    assert result.code == 0
    assert "!" not in result.out
    run("new", "Next")
    assert path_of(kb, "INIT-0001").is_file()
    assert (obsidian / "app.json").read_text(encoding="utf-8") == "{}"
    assert readme.read_text(encoding="utf-8") == "my notes"


def test_broken_frontmatter_during_now(run, kb):
    write_initiative(kb, "INIT-0004", title="Fine", next_="ok")
    path = write_initiative(kb, "INIT-0005", title="'unbalanced")
    before = path.read_bytes()
    result = run("now")
    assert result.code == 0
    assert "INIT-0004" in result.out
    assert "initiatives/INIT-0005/INIT-0005.md" in result.out
    assert path.read_bytes() == before


def test_name_and_id_disagree(run, kb):
    path = write_initiative(kb, "INIT-0007")
    path.write_text(
        path.read_text(encoding="utf-8").replace("id: INIT-0007", "id: INIT-0008"), encoding="utf-8"
    )
    result = run("now")
    assert "INIT-0007/INIT-0007.md" in result.out
    assert "INIT-0008" in result.out  # named in the warning only
    assert "PAUSED" not in result.out


def test_targeting_a_broken_initiative(run, kb):
    write_initiative(kb, "INIT-0004", status="active", next_="ok")
    path = write_initiative(kb, "INIT-0005", title="'unbalanced")
    before = {p: p.read_bytes() for p in kb.rglob("*.md")}
    result = run("resume", "INIT-0005", tty=False)
    assert result.code == 1
    assert "INIT-0005/INIT-0005.md" in result.err
    assert {p: p.read_bytes() for p in kb.rglob("*.md")} == before
    assert path.exists()


def test_missing_file_in_an_initiative_directory_is_reported(run, kb):
    (kb / "initiatives" / "INIT-0003").mkdir(parents=True)
    result = run("now")
    assert "INIT-0003/INIT-0003.md" in result.out


def test_store_relative_paths_use_forward_slashes(tmp_path):
    s = store.Store(tmp_path)
    assert s.relative(s.kb / "initiatives" / "INIT-0001" / "INIT-0001.md") == (
        "initiatives/INIT-0001/INIT-0001.md"
    )


# --- what a person writes by hand survives -----------------------------------------


def test_hand_written_values_keep_their_meaning(run, kb):
    path = write_initiative(
        kb,
        "INIT-0002",
        extra_meta="standup: 9:30\nversion: 1.10\nticket: 0123\nreviewed: yes\nflag: true\n",
    )
    assert run("pause", "2", "-n", "again").code == 0
    meta = load(kb, "INIT-0002").meta
    assert meta["standup"] == "9:30"
    assert meta["version"] == "1.10"
    assert meta["ticket"] == "0123"
    assert meta["reviewed"] == "yes"
    assert meta["flag"] is True
    text = path.read_text(encoding="utf-8")
    assert "\ncreated: 2026-09-01T09:00:00-03:00\n" in text  # byte for byte


def test_timestamps_are_written_plain(run, kb):
    run("new", "Payment retries")
    text = path_of(kb, "INIT-0001").read_text(encoding="utf-8")
    assert "\ncreated: 2026-09-16T09:00:00-03:00\n" in text


def test_impossible_timestamp_does_not_break_commands(run, kb):
    write_initiative(kb, "INIT-0002", last_paused="2026-09-31T10:00:00-03:00")
    result = run("now")
    assert result.code == 0
    line = next(line for line in result.out.splitlines() if "INIT-0002" in line)
    assert line.rstrip().endswith("?")
    assert run("new", "X", "--pause-next", "y").code == 0


def test_bad_explicit_tag_is_reported_not_raised(run, kb):
    write_initiative(kb, "INIT-0002", extra_meta="weird: !!int x\n")
    result = run("now")
    assert result.code == 0
    assert "INIT-0002/INIT-0002.md" in result.out
    assert "Traceback" not in result.err


def test_long_title_is_not_folded(run, kb):
    title = "Investigate why the payment provider returns duplicated transaction identifiers ---"
    assert run("new", title).code == 0
    assert load(kb, "INIT-0001").title == title
    assert "INIT-0001" in run("now").out


def test_missing_title_comes_from_the_heading(run, kb):
    path = path_of(kb, "INIT-0002")
    (path.parent / "checkpoints").mkdir(parents=True)
    path.write_text(
        "---\nid: INIT-0002\nstatus: paused\n---\n\n# Hand written thing\n\n"
        "## NOW\n\n**Next:** do it\n",
        encoding="utf-8",
    )
    assert "Hand written thing" in run("now").out
    assert run("pause", "2", "-n", "x").code == 0
    text = path.read_text(encoding="utf-8")
    assert "\n# Hand written thing\n" in text
    meta = load(kb, "INIT-0002").meta
    for key in ("title", "type", "priority", "tags", "workspaces", "links", "last_resumed"):
        assert key in meta


def test_multi_line_title_does_not_grow_the_file(run, kb):
    path = write_initiative(kb, "INIT-0002")
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace("title: Hand written\n", "title: |\n  Beta\n  second line\n", 1),
        encoding="utf-8",
    )
    run("pause", "2", "-n", "a")
    first = path.read_text(encoding="utf-8")
    run("pause", "2", "-n", "a")
    assert path.read_text(encoding="utf-8").count("second line") == first.count("second line")
    assert "\n# Beta second line\n" in first


def test_banner_above_the_title_is_kept_once(run, kb):
    path = write_initiative(kb, "INIT-0004", title="Renamed title")
    text = path.read_text(encoding="utf-8").replace(
        "# Renamed title", "> [!info] banner\n\n# Old title"
    )
    path.write_text(text, encoding="utf-8")
    run("pause", "4", "-n", "go")
    run("pause", "4", "-n", "go again")
    rewritten = path.read_text(encoding="utf-8")
    assert rewritten.count("\n# ") == 1
    assert "> [!info] banner" in rewritten


def test_bad_checkpoint_name_does_not_break_now(run, kb):
    run("new", "A")
    (kb / "initiatives" / "INIT-0001" / "checkpoints" / "2026-09-31T090000.md").write_text(
        "x", encoding="utf-8"
    )
    result = run("now")
    assert result.code == 0
    assert "INIT-0001" in result.out
