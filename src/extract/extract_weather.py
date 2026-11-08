"""Extract hourly historical weather for New York City from Open-Meteo.

Usage: python -m src.extract.extract_weather --start 2026-10-01 --end 2026-10-05
"""

from datetime import date

import requests

from src.extract.common import get_logger, parse_args, split_by_day, write_json

URL = "https://archive-api.open-meteo.com/v1/archive"
NYC_LATITUDE = 40.7128
NYC_LONGITUDE = -74.0060
HOURLY_FIELDS = ["temperature_2m", "precipitation", "wind_speed_10m"]
SOURCE = "weather"

logger = get_logger(__name__)


def to_rows(hourly: dict) -> list[dict]:
    """Turn Open-Meteo's column lists into one dict per hour."""
    rows = []
    for i, time in enumerate(hourly["time"]):
        row = {"time": time}
        for field in HOURLY_FIELDS:
            row[field] = hourly[field][i]
        rows.append(row)
    return rows


def fetch(start: date, end: date) -> list[dict]:
    """Fetch hourly weather for the date range (both days inclusive)."""
    params = {
        "latitude": NYC_LATITUDE,
        "longitude": NYC_LONGITUDE,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "hourly": ",".join(HOURLY_FIELDS),
        "timezone": "America/New_York",
    }
    response = requests.get(URL, params=params, timeout=60)
    response.raise_for_status()
    return to_rows(response.json()["hourly"])


def main(argv: list[str] | None = None) -> None:
    """Fetch weather and write one JSON file per day."""
    args = parse_args(argv)
    records = fetch(args.start, args.end)
    for dt, day_records in split_by_day(records, "time").items():
        path = write_json(day_records, SOURCE, dt)
        logger.info(
            "file written", extra={"extra_fields": {"path": str(path), "rows": len(day_records)}}
        )


if __name__ == "__main__":
    main()
