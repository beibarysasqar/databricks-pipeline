"""Tests for the shared extract helpers."""

import json
from datetime import date

import pytest

from src.extract.common import parse_args, split_by_day, write_json


def test_parse_args_reads_dates() -> None:
    args = parse_args(["--start", "2026-10-01", "--end", "2026-10-06"])
    assert args.start == date(2026, 10, 1)
    assert args.end == date(2026, 10, 6)


def test_parse_args_rejects_start_after_end() -> None:
    with pytest.raises(SystemExit):
        parse_args(["--start", "2026-10-06", "--end", "2026-10-01"])


def test_split_by_day_groups_on_date_prefix() -> None:
    records = [
        {"t": "2026-10-01T09:00:00"},
        {"t": "2026-10-01T23:00:00"},
        {"t": "2026-10-02T00:00:00"},
    ]
    days = split_by_day(records, "t")
    assert sorted(days) == ["2026-10-01", "2026-10-02"]
    assert len(days["2026-10-01"]) == 2


def test_write_json_creates_partition_path_as_json_lines(tmp_path) -> None:
    path = write_json([{"a": 1}, {"a": 2}], "src", "2026-10-01", base_dir=tmp_path)
    assert path == tmp_path / "src" / "dt=2026-10-01" / "src.json"
    lines = path.read_text().splitlines()
    assert [json.loads(line) for line in lines] == [{"a": 1}, {"a": 2}]


def test_write_json_rerun_overwrites_file(tmp_path) -> None:
    write_json([{"a": 1}, {"a": 2}], "src", "2026-10-01", base_dir=tmp_path)
    path = write_json([{"a": 3}], "src", "2026-10-01", base_dir=tmp_path)
    assert path.read_text().splitlines() == ['{"a": 3}']
