"""DuckDB-backed access to the multi-year FIRMS archive Parquet store."""
from __future__ import annotations

from datetime import date
from functools import lru_cache
from pathlib import Path

import duckdb
import pandas as pd

HOTSPOTS_GLOB = "data/processed/archive/hotspots/*.parquet"
MONTHLY_H3 = Path("data/processed/archive/monthly_h3.parquet")
H3_CELLS = Path("data/processed/archive/h3_cells.parquet")
MANIFEST = Path("data/processed/archive/manifest.csv")

SENSOR_LABELS = {
    "MODIS_ARCHIVE": "MODIS",
    "VIIRS_SNPP_ARCHIVE": "VIIRS S-NPP",
    "VIIRS_NOAA20_ARCHIVE": "VIIRS NOAA-20",
    "VIIRS_NOAA21_ARCHIVE": "VIIRS NOAA-21",
}


class ArchiveNotReady(RuntimeError):
    pass


def _connect() -> duckdb.DuckDBPyConnection:
    if not Path("data/processed/archive/hotspots").exists():
        raise ArchiveNotReady("Archive Parquet not built yet. Run backend.ingestion.archive_ingest.")
    con = duckdb.connect()
    con.execute("SET threads = 4")
    con.execute("SET memory_limit = '3GB'")
    return con


def _hotspots(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(f"CREATE OR REPLACE VIEW hotspots AS SELECT * FROM read_parquet('{HOTSPOTS_GLOB}')")


def _monthly(con: duckdb.DuckDBPyConnection) -> None:
    if not MONTHLY_H3.exists():
        raise ArchiveNotReady("monthly_h3.parquet missing. Run backend.ingestion.build_aggregates.")
    con.execute(f"CREATE OR REPLACE VIEW monthly AS SELECT * FROM read_parquet('{MONTHLY_H3}')")


def _cells(con: duckdb.DuckDBPyConnection) -> None:
    if not H3_CELLS.exists():
        raise ArchiveNotReady("h3_cells.parquet missing. Run backend.ingestion.build_aggregates.")
    con.execute(f"CREATE OR REPLACE VIEW cells AS SELECT * FROM read_parquet('{H3_CELLS}')")


def _region_cells_sql(bbox: tuple[float, float, float, float]) -> str:
    w, s, e, n = bbox
    return (
        "SELECT h3_index FROM cells "
        f"WHERE latitude BETWEEN {s} AND {n} AND longitude BETWEEN {w} AND {e}"
    )


def parse_bbox(bbox: str) -> tuple[float, float, float, float]:
    try:
        w, s, e, n = (float(v) for v in bbox.split(","))
    except ValueError as exc:
        raise ValueError("bbox must be 'west,south,east,north'") from exc
    if not (-180 <= w < e <= 180 and -90 <= s < n <= 90):
        raise ValueError("bbox out of range or inverted")
    return w, s, e, n


def parse_date(value: str, field: str) -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise ValueError(f"{field} must be YYYY-MM-DD") from exc


def _where(bbox: tuple[float, float, float, float], start: str, end: str) -> str:
    w, s, e, n = bbox
    return (
        f"acq_date BETWEEN DATE '{start}' AND DATE '{end}' "
        f"AND latitude BETWEEN {s} AND {n} AND longitude BETWEEN {w} AND {e}"
    )


@lru_cache(maxsize=1)
def coverage() -> dict:
    con = _connect()
    _hotspots(con)
    row = con.execute(
        "SELECT MIN(acq_date), MAX(acq_date), COUNT(*), COUNT(DISTINCT h3_index) FROM hotspots"
    ).fetchone()
    sensors = con.execute(
        "SELECT source_id, MIN(acq_date), MAX(acq_date), COUNT(*) FROM hotspots GROUP BY 1 ORDER BY 1"
    ).fetchall()
    years = con.execute(
        "SELECT DISTINCT year(acq_date) FROM hotspots ORDER BY 1"
    ).fetchall()
    return {
        "date_min": str(row[0]),
        "date_max": str(row[1]),
        "total_detections": int(row[2]),
        "distinct_h3_cells": int(row[3]),
        "years": [int(y[0]) for y in years],
        "sensors": [
            {
                "source_id": sid,
                "label": SENSOR_LABELS.get(sid, sid),
                "date_min": str(dmin),
                "date_max": str(dmax),
                "detections": int(cnt),
            }
            for sid, dmin, dmax, cnt in sensors
        ],
    }


@lru_cache(maxsize=512)
def summary(bbox_str: str, start: str, end: str) -> dict:
    bbox = parse_bbox(bbox_str)
    start, end = parse_date(start, "start"), parse_date(end, "end")
    con = _connect()
    _hotspots(con)
    row = con.execute(
        f"""
        SELECT
            COUNT(*) AS total_detections,
            SUM(CASE WHEN sensor_family = 'MODIS' THEN 1 ELSE 0 END) AS modis_count,
            SUM(CASE WHEN sensor_family = 'VIIRS' THEN 1 ELSE 0 END) AS viirs_count,
            COUNT(DISTINCT acq_date) AS active_days,
            COUNT(DISTINCT h3_index) AS active_h3_cells,
            MAX(frp) AS max_frp_mw,
            AVG(frp) AS mean_frp_mw,
            SUM(frp) AS total_frp_mw
        FROM hotspots WHERE {_where(bbox, start, end)}
        """
    ).fetchone()
    return {
        "bbox": bbox_str,
        "start": start,
        "end": end,
        "total_detections": int(row[0] or 0),
        "modis_count": int(row[1] or 0),
        "viirs_count": int(row[2] or 0),
        "active_days": int(row[3] or 0),
        "active_h3_cells": int(row[4] or 0),
        "max_frp_mw": round(float(row[5] or 0), 2),
        "mean_frp_mw": round(float(row[6] or 0), 2),
        "total_frp_mw": round(float(row[7] or 0), 2),
    }


@lru_cache(maxsize=512)
def series(bbox_str: str, start: str, end: str, granularity: str = "day") -> list[dict]:
    bbox = parse_bbox(bbox_str)
    start, end = parse_date(start, "start"), parse_date(end, "end")
    if granularity not in ("day", "month"):
        raise ValueError("granularity must be 'day' or 'month'")
    bucket = "acq_date" if granularity == "day" else "date_trunc('month', acq_date)"
    con = _connect()
    _hotspots(con)
    rows = con.execute(
        f"""
        SELECT
            {bucket} AS period,
            COUNT(*) AS total,
            SUM(CASE WHEN sensor_family = 'MODIS' THEN 1 ELSE 0 END) AS modis,
            SUM(CASE WHEN sensor_family = 'VIIRS' THEN 1 ELSE 0 END) AS viirs,
            MAX(frp) AS max_frp_mw,
            SUM(frp) AS total_frp_mw
        FROM hotspots WHERE {_where(bbox, start, end)}
        GROUP BY 1 ORDER BY 1
        """
    ).fetchall()
    return [
        {
            "period": str(r[0])[:10] if granularity == "day" else str(r[0])[:7],
            "total": int(r[1]),
            "modis": int(r[2]),
            "viirs": int(r[3]),
            "max_frp_mw": round(float(r[4] or 0), 2),
            "total_frp_mw": round(float(r[5] or 0), 2),
        }
        for r in rows
    ]


@lru_cache(maxsize=128)
def calendar_matrix(bbox_str: str, year_from: int, year_to: int) -> list[dict]:
    bbox = parse_bbox(bbox_str)
    con = _connect()
    _monthly(con)
    _cells(con)
    rows = con.execute(
        f"""
        SELECT year, month,
               SUM(total_detections) AS total,
               SUM(modis_count) AS modis,
               SUM(viirs_count) AS viirs,
               SUM(frp_sum_mw) AS frp_sum_mw
        FROM monthly
        WHERE year BETWEEN {int(year_from)} AND {int(year_to)}
          AND h3_index IN ({_region_cells_sql(bbox)})
        GROUP BY 1, 2 ORDER BY 1, 2
        """
    ).fetchall()
    return [
        {
            "year": int(r[0]),
            "month": int(r[1]),
            "total": int(r[2]),
            "modis": int(r[3]),
            "viirs": int(r[4]),
            "frp_sum_mw": round(float(r[5] or 0), 2),
        }
        for r in rows
    ]


@lru_cache(maxsize=128)
def year_vs_history(bbox_str: str, year: int) -> list[dict]:
    """For each month of `year`, compares the regional total against the median
    of all other years in the archive (same month, same region)."""
    bbox = parse_bbox(bbox_str)
    con = _connect()
    _monthly(con)
    _cells(con)
    rows = con.execute(
        f"""
        WITH region AS (
            SELECT year, month, SUM(total_detections) AS total
            FROM monthly
            WHERE h3_index IN ({_region_cells_sql(bbox)})
            GROUP BY 1, 2
        ),
        baseline AS (
            SELECT month,
                   MEDIAN(total) AS median_total,
                   QUANTILE_CONT(total, 0.25) AS p25,
                   QUANTILE_CONT(total, 0.75) AS p75,
                   MAX(total) AS max_total
            FROM region WHERE year <> {int(year)}
            GROUP BY 1
        )
        SELECT r.month, r.total, b.median_total, b.p25, b.p75, b.max_total,
               CASE WHEN b.median_total > 0
                    THEN ROUND(100.0 * (r.total - b.median_total) / b.median_total, 1)
                    ELSE NULL END AS pct_vs_median
        FROM region r JOIN baseline b USING (month)
        WHERE r.year = {int(year)}
        ORDER BY r.month
        """
    ).fetchall()
    return [
        {
            "month": int(r[0]),
            "total": int(r[1] or 0),
            "median_other_years": float(r[2] or 0),
            "p25": float(r[3] or 0),
            "p75": float(r[4] or 0),
            "max_other_years": int(r[5] or 0),
            "pct_vs_median": float(r[6]) if r[6] is not None else None,
        }
        for r in rows
    ]


@lru_cache(maxsize=64)
def yearly_by_sensor(bbox_str: str) -> list[dict]:
    bbox = parse_bbox(bbox_str)
    con = _connect()
    _hotspots(con)
    w, s, e, n = bbox
    rows = con.execute(
        f"""
        SELECT year(acq_date) AS year, source_id, COUNT(*) AS detections
        FROM hotspots
        WHERE latitude BETWEEN {s} AND {n} AND longitude BETWEEN {w} AND {e}
        GROUP BY 1, 2 ORDER BY 1, 2
        """
    ).fetchall()
    return [
        {"year": int(r[0]), "source_id": r[1], "label": SENSOR_LABELS.get(r[1], r[1]), "detections": int(r[2])}
        for r in rows
    ]


def hotspots_df(bbox_str: str, start: str, end: str, limit: int | None, sensor: str | None = None) -> pd.DataFrame:
    """Raw detections in bbox/date range. `limit=None` returns every row."""
    bbox = parse_bbox(bbox_str)
    start, end = parse_date(start, "start"), parse_date(end, "end")
    con = _connect()
    _hotspots(con)
    sensor_filter = f" AND sensor_family = '{sensor.upper()}'" if sensor else ""
    limit_sql = f"LIMIT {int(limit)}" if limit is not None else ""
    return con.execute(
        f"""
        SELECT latitude, longitude, h3_index, acq_datetime, acq_date, acq_time,
               frp, raw_confidence, confidence_tier, satellite, instrument,
               daynight, sensor_family, processing_level, spatial_res_m, brightness
        FROM hotspots
        WHERE {_where(bbox, start, end)}{sensor_filter}
        ORDER BY acq_datetime
        {limit_sql}
        """
    ).df()
