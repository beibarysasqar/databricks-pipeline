# Databricks notebook source
# MAGIC %md
# MAGIC # 02 Silver: clean, deduplicate and MERGE
# MAGIC For each source:
# MAGIC 1. Create the silver table once, with a comment on the table and every column.
# MAGIC 2. Build a clean batch from bronze: cast types, drop rows without a key, and keep only
# MAGIC    the latest version of each key (highest `_ingested_at`).
# MAGIC 3. `MERGE` the batch into silver on the key: update existing rows, insert new ones.
# MAGIC
# MAGIC Rerunning this notebook never creates duplicates. Both sources use local NYC time.

# COMMAND ----------

dbutils.widgets.text("catalog", "main")
dbutils.widgets.text("schema", "nyc_pipeline")
spark.sql(f"USE CATALOG {dbutils.widgets.get('catalog')}")
spark.sql(f"USE SCHEMA {dbutils.widgets.get('schema')}")

# COMMAND ----------

# MAGIC %md ## NYC 311 service requests (key: `unique_key`)

# COMMAND ----------

spark.sql("""
CREATE TABLE IF NOT EXISTS silver_311 (
  unique_key     BIGINT    COMMENT 'Unique id of the service request',
  created_date   TIMESTAMP COMMENT 'When the request was created (local NYC time)',
  closed_date    TIMESTAMP COMMENT 'When the request was closed, null if still open',
  agency         STRING    COMMENT 'City agency handling the request, e.g. NYPD',
  complaint_type STRING    COMMENT 'Main complaint category, e.g. Noise - Residential',
  descriptor     STRING    COMMENT 'More detail about the complaint',
  borough        STRING    COMMENT 'NYC borough of the incident',
  incident_zip   STRING    COMMENT 'ZIP code of the incident',
  status         STRING    COMMENT 'Request status, e.g. Open or Closed',
  latitude       DOUBLE    COMMENT 'Incident latitude',
  longitude      DOUBLE    COMMENT 'Incident longitude',
  _ingested_at   TIMESTAMP COMMENT 'When the row was loaded into bronze'
)
COMMENT 'Cleaned NYC 311 service requests, one row per unique_key'
""")

# COMMAND ----------

spark.sql("""
CREATE OR REPLACE TEMP VIEW updates_311 AS
SELECT
  CAST(unique_key AS BIGINT)      AS unique_key,
  CAST(created_date AS TIMESTAMP) AS created_date,
  CAST(closed_date AS TIMESTAMP)  AS closed_date,
  agency,
  TRIM(complaint_type)            AS complaint_type,
  descriptor,
  UPPER(borough)                  AS borough,
  incident_zip,
  status,
  CAST(latitude AS DOUBLE)        AS latitude,
  CAST(longitude AS DOUBLE)       AS longitude,
  _ingested_at
FROM bronze_311
WHERE unique_key IS NOT NULL AND created_date IS NOT NULL
QUALIFY ROW_NUMBER() OVER (PARTITION BY unique_key ORDER BY _ingested_at DESC) = 1
""")

spark.sql("""
MERGE INTO silver_311 AS t
USING updates_311 AS s
ON t.unique_key = s.unique_key
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
""").show()

# COMMAND ----------

# MAGIC %md ## Hourly weather (key: `weather_hour`)

# COMMAND ----------

spark.sql("""
CREATE TABLE IF NOT EXISTS silver_weather (
  weather_hour   TIMESTAMP COMMENT 'Start of the hour (local NYC time)',
  temperature_c  DOUBLE    COMMENT 'Air temperature at 2 m, degrees Celsius',
  precipitation_mm DOUBLE  COMMENT 'Total precipitation in the hour, millimetres',
  wind_speed_kmh DOUBLE    COMMENT 'Wind speed at 10 m, km/h',
  _ingested_at   TIMESTAMP COMMENT 'When the row was loaded into bronze'
)
COMMENT 'Cleaned hourly NYC weather, one row per hour'
""")

# COMMAND ----------

spark.sql("""
CREATE OR REPLACE TEMP VIEW updates_weather AS
SELECT
  CAST(time AS TIMESTAMP)          AS weather_hour,
  CAST(temperature_2m AS DOUBLE)   AS temperature_c,
  CAST(precipitation AS DOUBLE)    AS precipitation_mm,
  CAST(wind_speed_10m AS DOUBLE)   AS wind_speed_kmh,
  _ingested_at
FROM bronze_weather
WHERE time IS NOT NULL
QUALIFY ROW_NUMBER() OVER (PARTITION BY time ORDER BY _ingested_at DESC) = 1
""")

spark.sql("""
MERGE INTO silver_weather AS t
USING updates_weather AS s
ON t.weather_hour = s.weather_hour
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
""").show()
