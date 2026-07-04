"""Timezone edge-case tests for app.shared.datetime helpers."""

import datetime as _dt
from zoneinfo import ZoneInfo

from app.shared.datetime import app_date, app_datetime, app_now, day_start

# ── helpers ──────────────────────────────────────────────────
SGT = ZoneInfo("Asia/Singapore")  # UTC+8
NYC = ZoneInfo("America/New_York")  # UTC-5 / -4 DST
UTC = ZoneInfo("UTC")


# ── app_now ──────────────────────────────────────────────────
def test_app_now_has_tz_and_is_roughly_now(monkeypatch):
    monkeypatch.setattr("app.shared.datetime.get_app_timezone", lambda: SGT)
    now = app_now()
    assert now.tzinfo is not None
    assert now.tzinfo.key == "Asia/Singapore"
    assert abs((now - _dt.datetime.now(SGT)).total_seconds()) < 5.0


# ── app_datetime ─────────────────────────────────────────────
def test_app_datetime_none_returns_now(monkeypatch):
    monkeypatch.setattr("app.shared.datetime.get_app_timezone", lambda: SGT)
    result = app_datetime(None)
    assert result.tzinfo is not None
    assert abs((result - _dt.datetime.now(SGT)).total_seconds()) < 5.0


def test_app_datetime_naive_gets_localised(monkeypatch):
    monkeypatch.setattr("app.shared.datetime.get_app_timezone", lambda: SGT)
    naive = _dt.datetime(2026, 1, 1, 12, 0, 0)
    result = app_datetime(naive)
    assert result.tzinfo.key == "Asia/Singapore"
    assert result.hour == 12
    assert result == _dt.datetime(2026, 1, 1, 12, 0, 0, tzinfo=SGT)


def test_app_datetime_aware_gets_converted(monkeypatch):
    monkeypatch.setattr("app.shared.datetime.get_app_timezone", lambda: SGT)
    utc_dt = _dt.datetime(2026, 1, 1, 4, 0, 0, tzinfo=UTC)
    result = app_datetime(utc_dt)
    assert result.tzinfo.key == "Asia/Singapore"
    assert result.hour == 12  # UTC 4am → SGT noon


# ── app_date ─────────────────────────────────────────────────
def test_app_date_naive_uses_calendar_date(monkeypatch):
    monkeypatch.setattr("app.shared.datetime.get_app_timezone", lambda: SGT)
    naive = _dt.datetime(2026, 1, 15, 23, 59, 59)
    assert app_date(naive) == _dt.date(2026, 1, 15)


def test_app_date_aware_midnight_utc_is_same_day_in_sgt(monkeypatch):
    monkeypatch.setattr("app.shared.datetime.get_app_timezone", lambda: SGT)
    # Midnight UTC = 8am SGT — same day
    dt_utc = _dt.datetime(2026, 3, 15, 0, 0, 0, tzinfo=UTC)
    assert app_date(dt_utc) == _dt.date(2026, 3, 15)


def test_app_date_aware_rolls_day_at_boundary(monkeypatch):
    monkeypatch.setattr("app.shared.datetime.get_app_timezone", lambda: SGT)
    # 15:59 UTC = 23:59 SGT — still same day
    dt_before = _dt.datetime(2026, 3, 15, 15, 59, 0, tzinfo=UTC)
    assert app_date(dt_before) == _dt.date(2026, 3, 15)

    # 16:00 UTC = midnight SGT next day
    dt_after = _dt.datetime(2026, 3, 15, 16, 0, 0, tzinfo=UTC)
    assert app_date(dt_after) == _dt.date(2026, 3, 16)


# ── day_start ────────────────────────────────────────────────
def test_day_start_produces_midnight_in_app_tz(monkeypatch):
    monkeypatch.setattr("app.shared.datetime.get_app_timezone", lambda: SGT)
    start = day_start(_dt.date(2026, 6, 15))
    assert start == _dt.datetime(2026, 6, 15, 0, 0, 0, tzinfo=SGT)
    assert start.tzinfo.key == "Asia/Singapore"


def test_day_start_wraps_to_utc_correctly(monkeypatch):
    monkeypatch.setattr("app.shared.datetime.get_app_timezone", lambda: SGT)
    start = day_start(_dt.date(2026, 1, 1))
    # SGT midnight = UTC 4pm previous day
    assert start.astimezone(UTC) == _dt.datetime(2025, 12, 31, 16, 0, 0, tzinfo=UTC)


# ── DST edge cases (New York → Eastern) ──────────────────────
def test_app_date_across_dst_spring_forward(monkeypatch):
    monkeypatch.setattr("app.shared.datetime.get_app_timezone", lambda: NYC)
    # EST is UTC-5, EDT is UTC-4
    # 2026-03-08 is US spring-forward day
    est = _dt.datetime(2026, 3, 8, 0, 30, 0, tzinfo=_dt.timezone(_dt.timedelta(hours=-5)))
    assert app_date(est) == _dt.date(2026, 3, 8)


def test_app_date_across_dst_fall_back(monkeypatch):
    monkeypatch.setattr("app.shared.datetime.get_app_timezone", lambda: NYC)
    # 2026-11-01 is US fall-back day
    edt = _dt.datetime(2026, 11, 1, 1, 30, 0, tzinfo=_dt.timezone(_dt.timedelta(hours=-4)))
    assert app_date(edt) == _dt.date(2026, 11, 1)


def test_day_start_across_dst(monkeypatch):
    monkeypatch.setattr("app.shared.datetime.get_app_timezone", lambda: NYC)
    start = day_start(_dt.date(2026, 7, 4))
    assert start.tzinfo.key == "America/New_York"
    # EDT is UTC-4, so midnight EDT = 04:00 UTC
    assert start.astimezone(UTC).hour == 4


# ── Idempotency / invariants ─────────────────────────────────
def test_app_date_day_start_roundtrip(monkeypatch):
    monkeypatch.setattr("app.shared.datetime.get_app_timezone", lambda: SGT)
    d = _dt.date(2026, 5, 1)
    assert app_date(day_start(d)) == d


def test_app_datetime_idempotent_for_localized(monkeypatch):
    monkeypatch.setattr("app.shared.datetime.get_app_timezone", lambda: SGT)
    dt = _dt.datetime(2026, 5, 1, 14, 0, 0, tzinfo=SGT)
    result = app_datetime(dt)
    assert result == dt
    assert app_datetime(result) == dt
