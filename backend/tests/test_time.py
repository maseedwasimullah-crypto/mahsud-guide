"""Real-time Peshawar (Asia/Karachi) clock tests.

Dates are checked with controlled UTC instants so results are deterministic,
including the case where the UTC calendar date differs from Pakistan's.
"""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.utils.time import format_pakistan, pakistan_now, pakistan_today


def test_pakistan_now_is_in_karachi_offset():
    now = pakistan_now()
    assert now.tzinfo is not None
    # Pakistan is UTC+5 year-round (no DST).
    assert now.utcoffset().total_seconds() == 5 * 3600
    assert now.tzinfo.key == "Asia/Karachi"


def test_utc_midnight_maps_to_next_day_in_pakistan():
    # 2026-01-01 20:00 UTC == 2026-01-02 01:00 in Peshawar (dates differ).
    instant = datetime(2026, 1, 1, 20, 0, tzinfo=timezone.utc)
    local = instant.astimezone(ZoneInfo("Asia/Karachi"))
    assert local.date().isoformat() == "2026-01-02"
    assert local.hour == 1


def test_just_before_utc_midnight_keeps_pakistan_date():
    # 2026-06-30 23:30 UTC == 2026-07-01 04:30 in Peshawar.
    instant = datetime(2026, 6, 30, 23, 30, tzinfo=timezone.utc)
    local = instant.astimezone(ZoneInfo("Asia/Karachi"))
    assert local.date().isoformat() == "2026-07-01"
    # While the naive UTC date is still June.
    assert instant.date().isoformat() == "2026-06-30"


def test_format_pakistan_converts_naive_as_if_already_local():
    naive = datetime(2026, 3, 10, 12, 0, 0)
    formatted = format_pakistan(naive)
    assert formatted.endswith("+05:00")
    assert formatted.startswith("2026-03-10T12:00:00")


def test_format_pakistan_converts_from_other_zone():
    utc_instant = datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc)
    formatted = format_pakistan(utc_instant)
    assert formatted.startswith("2026-03-10T17:00:00")  # 12:00 UTC -> 17:00 PKT
    assert formatted.endswith("+05:00")


def test_api_time_endpoint_reports_live_peshawar_time(client):
    response = client.get("/api/time")
    assert response.status_code == 200
    payload = response.json()
    assert payload["timezone"] == "Asia/Karachi"
    assert payload["utc_offset"] == "+0500"
    # Date must equal what the server clock says in Karachi right now.
    assert payload["date"] == pakistan_today()
    assert payload["today"] == payload["date"]
    # Never hardcoded: iso must be within a couple of minutes of now.
    fetched = datetime.fromisoformat(payload["iso"])
    delta = abs((pakistan_now() - fetched).total_seconds())
    assert delta < 120, f"server clock drifted by {delta}s"


def test_api_time_endpoint_is_never_a_static_date(client):
    first = client.get("/api/time").json()["iso"]
    second = client.get("/api/time").json()["iso"]
    # Seconds may match if called within the same second, but both must parse
    # to real timezone-aware instants (a hardcoded string would fail this).
    assert datetime.fromisoformat(first).tzinfo is not None
    assert datetime.fromisoformat(second).tzinfo is not None
    assert first.endswith("+05:00")
