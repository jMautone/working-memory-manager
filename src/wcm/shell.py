"""The directory-change request protocol (`WCM_CD_FILE`).

A child process cannot change its parent shell's directory. The shell wrapper
(`shell/wcm.psm1`) names a file in `WCM_CD_FILE`; the CLI writes the directory
there and the wrapper moves to it once the CLI exits.
"""

import os
from pathlib import Path


def request_cd(path: str | None) -> bool:
    """Ask the shell to move to `path`. Return False when the directory is missing."""
    if not path:
        return True
    if not Path(path).is_dir():
        return False
    target = os.environ.get("WCM_CD_FILE", "").strip()
    if target:
        with open(target, "w", encoding="utf-8", newline="\n") as f:
            f.write(path + "\n")
    return True
