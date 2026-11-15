"""Builds app-facing aggregates from the archive hotspot Parquet files.

Outputs (data/processed/archive/):
- monthly_h3.parquet  : (h3_index, year, month) detection counts and FRP stats
- baselines_h3_month.parquet : per (h3_index, month) multi-year statistics used
  for anomaly vs historical-median comparisons

Run after backend/ingestion/archive_ingest.py (and optional archive_backfill.py).
"""
from pathlib import Path

import duckdb

HOTSPOTS_GLOB = "data/processed/archive/hotspots/*.parquet"
OUT_DIR = Path("data/processed/archive")

MONTHLY_SQL = f"""
COPY (
    SELECT
        h3_index,
        CAST(year(acq_date) AS SMALLINT)  AS year,
        CAST(month(acq_date) AS TINYINT)  AS month,
        COUNT(*)                          AS total_detections,
        SUM(CASE WHEN sensor_family = 'MODIS' THEN 1 ELSE 0 END) AS modis_count,
        SUM(CASE WHEN sensor_family = 'VIIRS' THEN 1 ELSE 0 END) AS viirs_count,
        SUM(frp)                          AS frp_sum_mw,
        AVG(frp)                          AS frp_mean_mw,
        MAX(frp)                          AS frp_max_mw,
        COUNT(DISTINCT satellite)         AS satellite_count
    FROM read_parquet('{HOTSPOTS_GLOB}')
    GROUP BY 1, 2, 3
) TO '{OUT_DIR / 'monthly_h3.parquet'}' (FORMAT PARQUET, COMPRESSION ZSTD)
"""

BASELINE_SQL = f"""
COPY (
    WITH monthly AS (
        SELECT * FROM read_parquet('{OUT_DIR / 'monthly_h3.parquet'}')
    )
    SELECT
        h3_index,
        month,
        COUNT(*)                          AS active_years,
        AVG(total_detections)             AS baseline_count_mean,
        STDDEV_SAMP(total_detections)     AS baseline_count_std,
        AVG(frp_sum_mw)                   AS baseline_frp_sum_mean,
        STDDEV_SAMP(frp_sum_mw)           AS baseline_frp_sum_std,
        MEDIAN(total_detections)          AS baseline_count_median,
        QUANTILE_CONT(total_detections, 0.95) AS baseline_count_p95,
        MAX(total_detections)             AS baseline_count_max
    FROM monthly
    GROUP BY 1, 2
) TO '{OUT_DIR / 'baselines_h3_month.parquet'}' (FORMAT PARQUET, COMPRESSION ZSTD)
"""


CELLS_SQL = f"""
COPY (
    SELECT h3_index,
           AVG(latitude)  AS latitude,
           AVG(longitude) AS longitude,
           MIN(acq_date)  AS first_seen,
           MAX(acq_date)  AS last_seen
    FROM read_parquet('{HOTSPOTS_GLOB}')
    GROUP BY 1
) TO '{OUT_DIR / 'h3_cells.parquet'}' (FORMAT PARQUET, COMPRESSION ZSTD)
"""


def main() -> None:
    con = duckdb.connect()
    print("Building h3 cell centroids...")
    con.execute(CELLS_SQL)
    print("Building monthly_h3 aggregate...")
    con.execute(MONTHLY_SQL)
    print(con.execute(f"SELECT COUNT(*) FROM read_parquet('{OUT_DIR / 'monthly_h3.parquet'}')").fetchone())
    print("Building per-cell monthly baselines...")
    con.execute(BASELINE_SQL)
    print(con.execute(f"SELECT COUNT(*) FROM read_parquet('{OUT_DIR / 'baselines_h3_month.parquet'}')").fetchone())
    print("Done.")


if __name__ == "__main__":
    main()
