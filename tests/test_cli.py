import subprocess
import sys

from wcm import cli


class Stream:
    def __init__(self, encoding):
        self.encoding = encoding


def test_ellipsis_falls_back_when_the_output_cannot_encode_it():
    assert cli._ellipsis(Stream("utf-8")) == "…"
    assert cli._ellipsis(Stream("cp437")) == "..."
    assert cli._ellipsis(Stream(None)) == "…"


def test_module_entry_point_lists_the_commands(hub):
    result = subprocess.run(
        [sys.executable, "-m", "wcm", "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0
    for command in ("new", "now", "pause", "resume", "done"):
        assert command in result.stdout


def test_module_entry_point_exit_code_for_a_domain_error(hub):
    result = subprocess.run(
        [sys.executable, "-m", "wcm", "resume", "99"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 1
    assert "INIT-0099 was not found" in result.stderr
