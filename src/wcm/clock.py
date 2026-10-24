"""The current time, in local time with its UTC offset. Tests replace `now`."""

from datetime import datetime


def now() -> datetime:
    return datetime.now().astimezone()
