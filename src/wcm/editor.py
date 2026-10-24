"""The editor a note opens in: `VISUAL`, then `EDITOR`, then the OS default.

The only effect besides the store: it runs the editor attached to the same
console and waits for it to exit.

                Windows                          macOS and Linux
    default     notepad                          vi
    split       shlex, non-POSIX, then drop the  shlex, POSIX
                double quotes around each token
                (backslashes in C:\\... stay)
    lookup      shutil.which honors PATHEXT, so  shutil.which on PATH
                `code` resolves to code.cmd
"""

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

HINT = 'set VISUAL or EDITOR to an editor that waits until you close it, such as "code --wait"'


class EditorError(Exception):
    pass


def command() -> str:
    for name in ("VISUAL", "EDITOR"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return "notepad" if sys.platform == "win32" else "vi"


def split(cmd: str) -> list[str]:
    """The program and its arguments; double quotes group a path with spaces."""
    if sys.platform == "win32":
        tokens = shlex.split(cmd, posix=False)
        return [t[1:-1] if len(t) >= 2 and t[0] == t[-1] == '"' else t for t in tokens]
    return shlex.split(cmd)


def open(path: Path) -> int:
    """Run the editor on `path`, wait for it, and return its exit code."""
    cmd = command()
    try:
        parts = split(cmd)
    except ValueError as e:
        raise EditorError(f"cannot read the editor command {cmd!r} ({e}); {HINT}") from None
    if not parts:
        raise EditorError(f"the editor command {cmd!r} is empty; {HINT}")
    program = shutil.which(parts[0]) or parts[0]
    try:
        return subprocess.run([program, *parts[1:], os.path.abspath(path)]).returncode
    except OSError as e:
        raise EditorError(f"cannot start the editor {cmd!r} ({e.strerror or e}); {HINT}") from None
