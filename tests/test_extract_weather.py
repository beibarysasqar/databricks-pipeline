"""Tests for the Open-Meteo weather extractor (no real network calls)."""

from datetime import date

from src.extract.extract_weather import URL, fetch, to_rows

HOURLY = {
    "time": ["2026-10-01T00:00", "2026-10-01T01:00"],
    "temperature_2m": [15.2, 14.8],
    "precipitation": [0.0, 0.3],
    "wind_speed_10m": [10.1, 12.4],
}


def test_to_rows_turns_columns_into_rows() -> None:
    rows = to_rows(HOURLY)
    assert rows[1] == {
        "time": "2026-10-01T01:00",
        "temperature_2m": 14.8,
        "precipitation": 0.3,
        "wind_speed_10m": 12.4,
    }


def test_fetch_sends_dates_and_returns_rows(requests_mock) -> None:
    requests_mock.get(URL, json={"hourly": HOURLY})
    rows = fetch(date(2026, 10, 1), date(2026, 10, 6))
    query = requests_mock.last_request.qs
    assert query["start_date"] == ["2026-10-01"]
    assert query["end_date"] == ["2026-10-06"]
    assert len(rows) == 2
