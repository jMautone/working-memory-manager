import pytest

from wcm import editor


@pytest.fixture
def env(monkeypatch):
    monkeypatch.delenv("VISUAL", raising=False)
    monkeypatch.delenv("EDITOR", raising=False)
    return monkeypatch


def test_visual_wins_over_editor(env):
    env.setenv("VISUAL", "nvim")
    env.setenv("EDITOR", "nano")
    assert editor.command() == "nvim"


def test_blank_visual_falls_back_to_editor(env):
    env.setenv("VISUAL", "  ")
    env.setenv("EDITOR", "code --wait")
    assert editor.command() == "code --wait"


@pytest.mark.parametrize(("platform", "default"), [("win32", "notepad"), ("darwin", "vi")])
def test_default_per_os(env, platform, default):
    env.setattr(editor.sys, "platform", platform)
    assert editor.command() == default


@pytest.mark.parametrize("platform", ["win32", "linux"])
def test_split_program_and_arguments(monkeypatch, platform):
    monkeypatch.setattr(editor.sys, "platform", platform)
    assert editor.split("code --wait") == ["code", "--wait"]


def test_split_windows_quoted_path(monkeypatch):
    monkeypatch.setattr(editor.sys, "platform", "win32")
    cmd = r'"C:\Program Files\Notepad++\notepad++.exe" -multiInst'
    assert editor.split(cmd) == [r"C:\Program Files\Notepad++\notepad++.exe", "-multiInst"]


def test_split_posix_quoted_path(monkeypatch):
    monkeypatch.setattr(editor.sys, "platform", "linux")
    cmd = '"/Applications/My Editor/bin/edit" -u NONE'
    assert editor.split(cmd) == ["/Applications/My Editor/bin/edit", "-u", "NONE"]


def test_missing_program_is_an_editor_error(env, tmp_path):
    env.setenv("EDITOR", "wcm-no-such-editor --wait")
    with pytest.raises(editor.EditorError, match="wcm-no-such-editor.*VISUAL or EDITOR"):
        editor.open(tmp_path / "NOTE-0001.md")


def test_unbalanced_quotes_are_an_editor_error(env, tmp_path):
    env.setattr(editor.sys, "platform", "linux")
    env.setenv("EDITOR", '"vi')
    with pytest.raises(editor.EditorError, match="cannot read the editor command"):
        editor.open(tmp_path / "NOTE-0001.md")
