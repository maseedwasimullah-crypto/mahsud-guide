"""Time utilities for Pakistan Standard Time (Asia/Karachi)."""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


_PST = ZoneInfo("Asia/Karachi")


def pakistan_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(_PST)


def pakistan_today() -> str:
    return pakistan_now().date().isoformat()


def format_pakistan(dt: datetime | None = None) -> str:
    if dt is None:
        dt = pakistan_now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_PST)
    else:
        dt = dt.astimezone(_PST)
    return dt.isoformat()


def now_iso_pakistan() -> str:
    return format_pakistan(pakistan_now())
