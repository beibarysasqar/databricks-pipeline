# NYC 311 + Weather Data Pipeline

A small ELT pipeline that answers one question: **do New Yorkers complain about different
things depending on the weather?** It combines NYC 311 service requests with hourly
weather and builds one daily table in Databricks.

## How the data flows

```
NYC 311 API ─┐
             ├─> Python extract (laptop) ─> data/raw/*.json ─> Unity Catalog Volume
Open-Meteo ──┘
   ─> bronze (raw) ─> silver (clean, no duplicates) ─> gold (daily complaints + weather)
```

1. **Extract (local Python).** Two scripts call free public APIs (no keys) for a date
   range and save one JSON Lines file per source per day under `data/raw/<source>/dt=<day>/`.
2. **Upload.** `scripts/extract_and_upload.sh` copies those files to a Unity Catalog Volume
   with the Databricks CLI.
3. **Bronze.** `01_bronze.py` loads the files into Delta tables as they are, plus the load
   time and source file name.
4. **Silver.** `02_silver.py` fixes data types, keeps the newest copy of each record and
   `MERGE`s it into the silver tables, so reruns never create duplicates.
5. **Gold.** `03_gold.sql` counts complaints per day and type and adds that day's
   temperature, rain and wind.
6. **Orchestration.** A Databricks Workflow runs bronze → silver → gold and e-mails on failure.
7. **CI.** GitHub Actions runs ruff and pytest on every push.

## Repo layout

| Path | What it is |
|---|---|
| `src/extract/common.py` | Shared helpers: date args, JSON logs, writing files |
| `src/extract/extract_311.py` | Pages through the NYC 311 Socrata API |
| `src/extract/extract_weather.py` | Gets hourly weather from Open-Meteo |
| `scripts/extract_and_upload.sh` | Runs both extracts and uploads to Databricks |
| `databricks/` | Bronze, silver and gold notebooks |
| `tests/` | Unit tests (no real network calls) |
| `docs/setup.md` | Databricks setup, upload and Workflow steps |

## Run it

```bash
pip install -r requirements-dev.txt
pytest -q
ruff check . && ruff format --check .

python -m src.extract.extract_311 --start 2026-10-26 --end 2026-10-30
python -m src.extract.extract_weather --start 2026-10-26 --end 2026-10-30
```

For the Databricks part, follow [docs/setup.md](docs/setup.md).

## Why about 5 days of data?

- NYC gets roughly 9K 311 requests a day, so 5 days is about 45K rows: big enough to be
  realistic, small enough to extract in a minute and run on Databricks Free Edition.
- The extractor stops at 50K rows as a safety cap and logs a warning if it hits it,
  because then the last day would be incomplete. 5 days stays safely under the cap.
- Weather is hourly, so the same 5 days is about 120 rows. That is enough to compare
  rainy days with dry ones.
- The end date should be at least a week ago, because the Open-Meteo archive lags by
  about 5 days and recent 311 records are still being filled in.
- The range is just `--start` / `--end`, so it is easy to load more days later.

## Rerunning is safe (idempotent)

- Extract writes a fixed file name per day, so a rerun overwrites the same file.
- Silver keeps one row per key (`unique_key` for 311, the hour for weather) using `MERGE`.
- Gold is rebuilt from silver with `CREATE OR REPLACE`.
