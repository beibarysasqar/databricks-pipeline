"""Extract NYC 311 service requests from the Socrata API for a date range.

Usage: python -m src.extract.extract_311 --start 2026-10-01 --end 2026-10-04
"""

from datetime import date, timedelta

from src.extract.common import get_json, get_logger, parse_args, split_by_day, write_json

URL = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
# Only the columns silver uses. Asking for all ~40 columns makes each page ~40x slower.
FIELDS = [
    "unique_key",
    "created_date",
    "closed_date",
    "agency",
    "complaint_type",
    "descriptor",
    "borough",
    "incident_zip",
    "status",
    "latitude",
    "longitude",
]
PAGE_SIZE = 10_000
MAX_RECORDS = 50_000
SOURCE = "nyc_311"

logger = get_logger(__name__)


def build_where(start: date, end: date) -> str:
    """Build the Socrata filter: created_date from start up to (not incl.) the day after end."""
    next_day = end + timedelta(days=1)
    return f"created_date >= '{start}T00:00:00' AND created_date < '{next_day}T00:00:00'"


def fetch_page(where: str, offset: int) -> list[dict]:
    """Fetch one page of records, ordered by unique_key so paging is stable."""
    params = {
        "$select": ",".join(FIELDS),
        "$where": where,
        "$order": "unique_key",
        "$limit": PAGE_SIZE,
        "$offset": offset,
    }
    return get_json(URL, params)


def fetch(start: date, end: date) -> list[dict]:
    """Fetch all pages until a short page or MAX_RECORDS is reached.

    Hitting MAX_RECORDS means the last day is probably cut off, so we log a warning.
    """
    where = build_where(start, end)
    records: list[dict] = []
    while len(records) < MAX_RECORDS:
        page = fetch_page(where, offset=len(records))
        records.extend(page)
        logger.info("page fetched", extra={"extra_fields": {"rows": len(page)}})
        if len(page) < PAGE_SIZE:
            break
    if len(records) >= MAX_RECORDS:
        logger.warning(
            "MAX_RECORDS reached, last day may be incomplete; use a shorter date range",
            extra={"extra_fields": {"max_records": MAX_RECORDS}},
        )
    return records[:MAX_RECORDS]


def main(argv: list[str] | None = None) -> None:
    """Fetch records and write one JSON file per day."""
    args = parse_args(argv)
    records = fetch(args.start, args.end)
    for dt, day_records in split_by_day(records, "created_date").items():
        path = write_json(day_records, SOURCE, dt)
        logger.info(
            "file written", extra={"extra_fields": {"path": str(path), "rows": len(day_records)}}
        )


if __name__ == "__main__":
    main()
