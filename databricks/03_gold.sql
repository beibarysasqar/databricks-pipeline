-- Databricks notebook source
-- MAGIC %md
-- MAGIC # 03 Gold: daily complaints with weather
-- MAGIC One row per day and complaint type, with that day's weather next to it.
-- MAGIC The table is rebuilt from silver on every run (`CREATE OR REPLACE`), so reruns are safe.

-- COMMAND ----------

CREATE WIDGET TEXT catalog DEFAULT 'main';
CREATE WIDGET TEXT schema DEFAULT 'nyc_pipeline';

-- COMMAND ----------

USE CATALOG IDENTIFIER(:catalog);
USE SCHEMA IDENTIFIER(:schema);

-- COMMAND ----------

CREATE OR REPLACE TABLE gold_daily_complaints_weather (
  complaint_date         COMMENT 'Calendar day (local NYC time)',
  complaint_type         COMMENT 'Main complaint category',
  complaint_count        COMMENT 'Number of 311 requests of this type on this day',
  avg_temperature_c      COMMENT 'Average hourly temperature that day, degrees Celsius',
  total_precipitation_mm COMMENT 'Total precipitation that day, millimetres',
  max_wind_speed_kmh     COMMENT 'Highest hourly wind speed that day, km/h'
)
COMMENT 'Daily NYC 311 complaint counts by type, joined with daily weather'
AS
WITH daily_complaints AS (
  SELECT
    CAST(created_date AS DATE) AS complaint_date,
    complaint_type,
    COUNT(*)                   AS complaint_count
  FROM silver_311
  GROUP BY 1, 2
),
daily_weather AS (
  SELECT
    CAST(weather_hour AS DATE)        AS weather_date,
    ROUND(AVG(temperature_c), 1)      AS avg_temperature_c,
    ROUND(SUM(precipitation_mm), 1)   AS total_precipitation_mm,
    MAX(wind_speed_kmh)               AS max_wind_speed_kmh
  FROM silver_weather
  GROUP BY 1
)
SELECT
  c.complaint_date,
  c.complaint_type,
  c.complaint_count,
  w.avg_temperature_c,
  w.total_precipitation_mm,
  w.max_wind_speed_kmh
FROM daily_complaints AS c
LEFT JOIN daily_weather AS w
  ON c.complaint_date = w.weather_date;

-- COMMAND ----------

SELECT * FROM gold_daily_complaints_weather ORDER BY complaint_date, complaint_count DESC LIMIT 20;
