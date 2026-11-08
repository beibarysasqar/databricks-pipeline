# Databricks notebook source
# MAGIC %md
# MAGIC # 01 Bronze: load raw JSON files into Delta tables
# MAGIC Reads the JSON Lines files from the Unity Catalog Volume and appends them, unchanged,
# MAGIC to `bronze_311` and `bronze_weather`. Two columns are added for traceability:
# MAGIC `_ingested_at` (when this run happened) and `_source_file` (which file the row came from).
# MAGIC Bronze is an append-only history; duplicates are removed later in silver.

# COMMAND ----------

from pyspark.sql import functions as F

dbutils.widgets.text("catalog", "main")
dbutils.widgets.text("schema", "nyc_pipeline")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")

spark.sql(f"USE CATALOG {catalog}")
spark.sql(f"USE SCHEMA {schema}")
raw_path = f"/Volumes/{catalog}/{schema}/raw"

# COMMAND ----------


def load_bronze(source: str, table: str, comment: str) -> None:
    """Read all raw files of one source and append them to a bronze table."""
    df = (
        spark.read.json(f"{raw_path}/{source}/")
        .withColumn("_ingested_at", F.current_timestamp())
        .withColumn("_source_file", F.col("_metadata.file_path"))
    )
    df.write.mode("append").option("mergeSchema", "true").saveAsTable(table)
    spark.sql(f"COMMENT ON TABLE {table} IS '{comment}'")
    print(f"{table}: appended {df.count()} rows")


# COMMAND ----------

load_bronze("nyc_311", "bronze_311", "Raw NYC 311 service requests, one row per loaded record.")
load_bronze("weather", "bronze_weather", "Raw hourly NYC weather from Open-Meteo.")
