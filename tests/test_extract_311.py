"""Tests for the NYC 311 extractor (no real network calls)."""

from datetime import date

import pytest
import requests

from src.extract import extract_311
from src.extract.extract_311 import URL, build_where, fetch


def test_build_where_covers_full_end_day() -> None:
    where = build_where(date(2026, 10, 1), date(2026, 10, 6))
    assert "created_date >= '2026-10-01T00:00:00'" in where
    assert "created_date < '2026-10-07T00:00:00'" in where


def test_fetch_pages_until_short_page(requests_mock, monkeypatch) -> None:
    monkeypatch.setattr(extract_311, "PAGE_SIZE", 2)
    requests_mock.get(
        URL,
        [
            {"json": [{"unique_key": "1"}, {"unique_key": "2"}]},
            {"json": [{"unique_key": "3"}]},
        ],
    )
    records = fetch(date(2026, 10, 1), date(2026, 10, 1))
    assert [r["unique_key"] for r in records] == ["1", "2", "3"]
    assert requests_mock.call_count == 2
    assert requests_mock.request_history[1].qs["$offset"] == ["2"]


def test_fetch_stops_at_max_records(requests_mock, monkeypatch) -> None:
    monkeypatch.setattr(extract_311, "PAGE_SIZE", 2)
    monkeypatch.setattr(extract_311, "MAX_RECORDS", 3)
    requests_mock.get(URL, json=[{"unique_key": "x"}, {"unique_key": "y"}])
    records = fetch(date(2026, 10, 1), date(2026, 10, 1))
    assert len(records) == 3


def test_fetch_raises_on_http_error(requests_mock) -> None:
    requests_mock.get(URL, status_code=500)
    with pytest.raises(requests.HTTPError):
        fetch(date(2026, 10, 1), date(2026, 10, 1))
