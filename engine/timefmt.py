"""Report filename stamps: timezone resolution and caller-supplied stamps.

Sweepy writes a ``YYYY-MM-DD-HHMMSS`` stamp into every report filename. A profile
chooses the clock with ``export.timezone``: ``local`` follows the machine, ``UTC``
pins Coordinated Universal Time, an IANA name such as ``America/New_York`` follows
that zone, and a ``-05:00``-style offset works without a timezone database.
"""

from __future__ import annotations

import datetime
import re
from typing import Optional

STAMP_FORMAT = "%Y-%m-%d-%H%M%S"
DEFAULT_TIMEZONE = "local"

_STAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{6}$")
_OFFSET_PATTERN = re.compile(r"^(?:UTC|GMT)?([+-])(\d{1,2}):?(\d{2})$", re.IGNORECASE)
_LOCAL_NAMES = frozenset({"", "local", "system", "machine"})
_UTC_NAMES = frozenset({"utc", "z", "gmt", "universal"})

_UNKNOWN_ZONE_HELP = (
    "Use 'local', 'UTC', an IANA name such as 'America/New_York', "
    "or an offset such as '-05:00'."
)


def resolve_timezone(name: Optional[str] = None) -> datetime.tzinfo:
    """Turn a profile's timezone setting into a ``tzinfo``.

    Raises ``ValueError`` for a value the machine cannot resolve, so a typo in a
    profile never silently moves every stamp.
    """
    text = str(name or "").strip()
    lowered = text.lower()

    if lowered in _LOCAL_NAMES:
        return datetime.datetime.now().astimezone().tzinfo or datetime.timezone.utc
    if lowered in _UTC_NAMES:
        return datetime.timezone.utc

    offset = _OFFSET_PATTERN.match(text)
    if offset:
        sign = -1 if offset.group(1) == "-" else 1
        hours, minutes = int(offset.group(2)), int(offset.group(3))
        if hours > 23 or minutes > 59:
            raise ValueError(f"Invalid UTC offset {name!r}. {_UNKNOWN_ZONE_HELP}")
        return datetime.timezone(sign * datetime.timedelta(hours=hours, minutes=minutes))

    try:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    except ImportError as exc:  # Python 3.8 and older have no zoneinfo
        raise ValueError(
            f"Timezone {name!r} needs Python 3.9 or newer. {_UNKNOWN_ZONE_HELP}"
        ) from exc
    try:
        return ZoneInfo(text)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(
            f"Unknown timezone {name!r}. {_UNKNOWN_ZONE_HELP} "
            "On Windows, install the 'tzdata' package for IANA names."
        ) from exc


def now(timezone_name: Optional[str] = None) -> datetime.datetime:
    """The current time in a profile's timezone."""
    return datetime.datetime.now(resolve_timezone(timezone_name))


def stamp(timezone_name: Optional[str] = None) -> str:
    """The current ``YYYY-MM-DD-HHMMSS`` stamp in a profile's timezone."""
    return now(timezone_name).strftime(STAMP_FORMAT)


def normalize_stamp(value: Optional[str]) -> Optional[str]:
    """Normalize a caller-supplied stamp to ``YYYY-MM-DD-HHMMSS``.

    Accepts the stamp form itself and ISO 8601, because an assistant usually has
    the user's clock as an ISO string. An aware value keeps its own wall clock:
    the caller already read it in the timezone they meant.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if _STAMP_PATTERN.match(text):
        return text
    try:
        moment = datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(
            f"Invalid timestamp {text!r}. Pass YYYY-MM-DD-HHMMSS, such as 2026-10-27-235510, "
            "or an ISO 8601 time such as 2026-10-27T23:55:10."
        ) from exc
    return moment.strftime(STAMP_FORMAT)
