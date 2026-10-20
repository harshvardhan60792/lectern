"""Two small things every service needs."""
from datetime import date


class ValidationError(ValueError):
    """Input the user can fix. The message is shown to them as-is."""


# One place for "today", so tests can pin the date.
_fixed: date | None = None


def today() -> date:
    return _fixed or date.today()


def set_today(value: date | None) -> None:
    global _fixed
    _fixed = value
