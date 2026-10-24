"""A stand-in editor for tests, run as `python fake_editor.py <path>`.

Appends `WCM_TEST_EDIT` to the file when it is set, then exits with
`WCM_TEST_EXIT` (default 0). Without either, it touches nothing.
"""

import os
import sys

path = sys.argv[-1]
edit = os.environ.get("WCM_TEST_EDIT")
if edit:
    with open(path, "a", encoding="utf-8", newline="") as f:
        f.write(edit)
sys.exit(int(os.environ.get("WCM_TEST_EXIT", "0")))
