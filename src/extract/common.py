"""Shared helpers for the extract scripts: CLI args, HTTP, JSON logging, file writing."""

import argparse
import json
import logging
from datetime import date
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

RAW_DIR = Path("data/raw")
TIMEOUT_SECONDS = 120


def get_json(url: str, params: dict) -> Any:
    """GET a URL and return the JSON body.

    Retries up to 5 times with growing waits on 429 (rate limit) and 5xx errors,
    then raises requests.HTTPError if the request still fails.
    """
    retry = Retry(
        total=5,
        backoff_factor=5,
        status_forcelist=[429, 500, 502, 503, 504],
        raise_on_status=False,
    )
    with requests.Session() as session:
        session.mount("https://", HTTPAdapter(max_retries=retry))
        response = session.get(url, params=params, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()


class JsonFormatter(logging.Formatter):
    """Format each log record as one JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "time": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        entry.update(getattr(record, "extra_fields", {}))
        return json.dumps(entry)


def get_logger(name: str) -> logging.Logger:
    """Return a logger that prints JSON lines to the console."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse --start and --end dates (YYYY-MM-DD, both inclusive)."""
    parser = argparse.ArgumentParser(description="Extract data for a date range.")
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    args = parser.parse_args(argv)
    if args.start > args.end:
        parser.error("--start must be on or before --end")
    return args


def split_by_day(records: list[dict], date_field: str) -> dict[str, list[dict]]:
    """Group records by the YYYY-MM-DD prefix of a timestamp field."""
    days: dict[str, list[dict]] = {}
    for record in records:
        day = record[date_field][:10]
        days.setdefault(day, []).append(record)
    return days


def write_json(records: list[dict], source: str, dt: str, base_dir: Path = RAW_DIR) -> Path:
    """Write records as JSON Lines to <base_dir>/<source>/dt=<dt>/<source>.json.

    The file name is fixed, so rerunning for the same day overwrites it (idempotent).
    """
    path = base_dir / source / f"dt={dt}" / f"{source}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")
    return path
