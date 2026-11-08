# Setup: Databricks, upload and Workflow

All names below (`main`, `nyc_pipeline`) are defaults. Use your own if they differ.
Never commit your workspace URL, tokens or account IDs.

## 1. Create the catalog, schema and Volume

Run this once in the Databricks SQL editor:

```sql
CREATE CATALOG IF NOT EXISTS main;
CREATE SCHEMA IF NOT EXISTS main.nyc_pipeline;
CREATE VOLUME IF NOT EXISTS main.nyc_pipeline.raw;
```

The Volume `raw` is a folder inside Unity Catalog where the JSON files will live:
`/Volumes/main/nyc_pipeline/raw/<source>/dt=YYYY-MM-DD/<source>.json`.

## 2. Install and log in to the Databricks CLI

```bash
brew tap databricks/tap && brew install databricks
databricks auth login --host <your-workspace-url>
```

The login saves a profile in `~/.databrickscfg` (outside the repo). If you use a
profile other than `DEFAULT`, set `DATABRICKS_CONFIG_PROFILE=<name>`.

## 3. Extract and upload

```bash
export DBX_CATALOG=main
export DBX_SCHEMA=nyc_pipeline
bash scripts/extract_and_upload.sh 2026-10-25 2026-10-30
```

The script runs both extractors locally, then copies `data/raw` into the Volume with
`databricks fs cp --overwrite`. Rerunning for the same dates replaces the same files.
Pick an end date at least a week ago: Open-Meteo's archive lags by about 5 days.

## 4. Import the notebooks

In the workspace: **Workspace → Import**, and import the three files from `databricks/`
(or add the GitHub repo as a **Git folder**). Run them once by hand in order:
`01_bronze` → `02_silver` → `03_gold`.

## 5. Create the Workflow (job)

1. Go to **Jobs & Pipelines → Create → Job**. Name it `nyc_311_weather_pipeline`.
2. Add three **Notebook** tasks:
   - `bronze` → `01_bronze`
   - `silver` → `02_silver`, depends on `bronze`
   - `gold` → `03_gold`, depends on `silver`
3. Use **Serverless** compute (or a small cluster).
4. Under **Job parameters** add `catalog = main` and `schema = nyc_pipeline`.
   Every task receives them as notebook widgets.
5. Under **Job notifications** add your e-mail for **Failure**.
6. Click **Run now** and check all three tasks turn green.

A schedule is optional: the raw files are uploaded from a laptop, so running the job
right after `extract_and_upload.sh` is enough.

## 6. Check the results

```sql
-- Silver must have no duplicate keys (expect 0 rows)
SELECT unique_key, COUNT(*) FROM main.nyc_pipeline.silver_311
GROUP BY unique_key HAVING COUNT(*) > 1;

-- Gold: one row per day and complaint type
SELECT * FROM main.nyc_pipeline.gold_daily_complaints_weather
ORDER BY complaint_date, complaint_count DESC;
```

Run the job a second time: silver row counts must stay the same.
