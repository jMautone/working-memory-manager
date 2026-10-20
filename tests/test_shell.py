import pytest
from conftest import write_initiative


@pytest.fixture
def cd_file(tmp_path, monkeypatch):
    path = tmp_path / "cd.txt"
    path.write_text("", encoding="utf-8")
    monkeypatch.setenv("WCM_CD_FILE", str(path))
    return path


@pytest.fixture
def workdir(tmp_path):
    path = tmp_path / "wt" / "payment-retries"
    path.mkdir(parents=True)
    return path


def workspace(path) -> str:
    return f"[{{path: '{path}', primary: true}}]"


def test_resume_with_an_existing_path(run, kb, cd_file, workdir):
    write_initiative(kb, "INIT-0007", workspaces=workspace(workdir))
    assert run("resume", "INIT-0007").code == 0
    assert cd_file.read_bytes() == (str(workdir) + "\n").encode("utf-8")


def test_resume_the_active_one_again(run, kb, cd_file, workdir):
    write_initiative(kb, "INIT-0007", status="active", workspaces=workspace(workdir))
    assert run("resume").code == 0
    assert cd_file.read_text(encoding="utf-8") == str(workdir) + "\n"


def test_new_requests_the_change(run, cd_file, workdir):
    assert run("new", "Payment retries", "--path", workdir).code == 0
    assert cd_file.read_text(encoding="utf-8") == str(workdir) + "\n"


def test_new_paused_does_not_request_it(run, cd_file, workdir):
    run("new", "Later", "--paused", "--next", "x", "--path", workdir)
    assert cd_file.read_text(encoding="utf-8") == ""


def test_resume_with_a_missing_path(run, kb, cd_file, tmp_path):
    gone = tmp_path / "gone"
    write_initiative(kb, "INIT-0007", workspaces=workspace(gone))
    result = run("resume", "INIT-0007")
    assert result.code == 0
    assert cd_file.read_text(encoding="utf-8") == ""
    assert "Path:" in result.out
    assert "does not exist" in result.out


def test_commands_without_a_path(run, kb, cd_file):
    run("new", "Payment retries")
    run("pause", "-n", "x")
    run("now")
    run("resume", "1")
    assert cd_file.read_text(encoding="utf-8") == ""


def test_direct_invocation_without_the_wrapper(run, kb, workdir, monkeypatch):
    monkeypatch.delenv("WCM_CD_FILE", raising=False)
    write_initiative(kb, "INIT-0007", workspaces=workspace(workdir))
    result = run("resume", "INIT-0007")
    assert result.code == 0
    assert "Path:" in result.out
    assert str(workdir) in result.out


def test_written_without_bom(run, kb, cd_file, tmp_path):
    accented = tmp_path / "trabajo-ñandú"
    accented.mkdir()
    write_initiative(kb, "INIT-0007", workspaces=workspace(accented))
    run("resume", "7")
    raw = cd_file.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert raw.decode("utf-8") == str(accented) + "\n"
