#!/usr/bin/env bash
# Run both extractors for a date range, then upload data/raw to a Unity Catalog Volume.
#
# Usage:  bash scripts/extract_and_upload.sh 2026-10-01 2026-10-06
# Needs:  DBX_CATALOG and DBX_SCHEMA env vars, and a configured Databricks CLI profile
#         (set DATABRICKS_CONFIG_PROFILE to pick a non-default profile).
set -euo pipefail

START="${1:?usage: $0 START_DATE END_DATE}"
END="${2:?usage: $0 START_DATE END_DATE}"
: "${DBX_CATALOG:?set DBX_CATALOG}"
: "${DBX_SCHEMA:?set DBX_SCHEMA}"

python -m src.extract.extract_311 --start "$START" --end "$END"
python -m src.extract.extract_weather --start "$START" --end "$END"

databricks fs cp -r --overwrite data/raw "dbfs:/Volumes/${DBX_CATALOG}/${DBX_SCHEMA}/raw"
echo "Upload finished."
