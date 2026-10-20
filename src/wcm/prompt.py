"""The interactive part of the pause flow. Tests replace `stdin_is_tty` and `input`."""

import sys

CLEAR = "-"


def stdin_is_tty() -> bool:
    try:
        return sys.stdin is not None and sys.stdin.isatty()
    except AttributeError, ValueError:
        return False


def ask(label: str, previous: str, out) -> str | None:
    """Show `label [previous]` and read one line.

    Return the previous value on Enter, None when the person types `-` to
    clear the field, and the typed text otherwise.
    """
    print(f"{label:<13}[{previous}]", file=out)
    answer = input("> ").strip()
    if not answer:
        return previous
    if answer == CLEAR:
        return None
    return answer
