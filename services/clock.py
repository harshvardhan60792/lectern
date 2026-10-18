"""One place for "today", so tests can pin the date."""
from datetime import date

_fixed: date | None = None


def today() -> date:
    return _fixed or date.today()


def set_today(value: date | None) -> None:
    global _fixed
    _fixed = value
