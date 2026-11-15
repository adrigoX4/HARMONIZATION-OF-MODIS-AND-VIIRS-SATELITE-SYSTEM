"""DuckDB-backed access to the multi-year FIRMS archive Parquet store."""
from __future__ import annotations

import os
import threading
from datetime import date
from functools import lru_cache
from pathlib import Path

import duckdb
import pandas as pd

ARCHIVE_DIR = Path("data/processed/archive")
HOTSPOTS_GLOB = "data/processed/archive/hotspots/*.parquet"
MONTHLY_H3 = Path("data/processed/archive/monthly_h3.parquet")
H3_CELLS = Path("data/processed/archive/h3_cells.parquet")
MONTHLY_SCORES = Path("data/processed/archive/monthly_scores.parquet")
MANIFEST = Path("data/processed/archive/manifest.csv")

# Remote mode: no local archive (e.g. a 512 MB Render container). DuckDB then reads
# the Parquet files straight from the Hugging Face Dataset over hf:// (httpfs),
# with a small memory budget. Local development keeps the on-disk paths.
HF_ARCHIVE_DATASET = os.getenv("HF_ARCHIVE_DATASET", "asrath0skye/modis-viirs-fire-archive").strip()
HF_BASE = f"hf://datasets/{HF_ARCHIVE_DATASET}"
# Path of the hotspot files inside the dataset. The dataset mirrors the local
# layout (flat hotspots/*.parquet, one source per file, no year in the file
# name); set e.g. "hotspots/year=*/**/*.parquet" if
# it is ever re-uploaded with year partitions.
HF_HOTSPOTS_PATTERN = os.getenv("HF_HOTSPOTS_PATTERN", "hotspots/*.parquet").strip().lstrip("/")
REMOTE = not (ARCHIVE_DIR.is_dir() and any(ARCHIVE_DIR.glob("*.parquet")))

SENSOR_LABELS = {
    "MODIS_ARCHIVE": "MODIS",
    "VIIRS_SNPP_ARCHIVE": "VIIRS S-NPP",
    "VIIRS_NOAA20_ARCHIVE": "VIIRS NOAA-20",
    "VIIRS_NOAA21_ARCHIVE": "VIIRS NOAA-21",
}


class ArchiveNotReady(RuntimeError):
    pass


# One DuckDB connection for the whole process, used by one query at a time.
# Concurrent requests (FastAPI runs sync routes in a thread pool) queue on the
# lock instead of each opening a connection with its own memory budget.
_LOCK = threading.Lock()
_CON: duckdb.DuckDBPyConnection | None = None
_VIEWS: set[str] = set()


def _sql_str(value: str) -> str:
    return value.replace("'", "''")


def _connection() -> duckdb.DuckDBPyConnection:
    global _CON
    if _CON is not None:
        return _CON
    if not REMOTE and not (ARCHIVE_DIR / "hotspots").exists():
        raise ArchiveNotReady("Archive Parquet not built yet. Run backend.ingestion.archive_ingest.")
    con = duckdb.connect()
    try:
        if REMOTE:
            temp_dir = os.getenv("DUCKDB_TEMP_DIR", "/tmp/duckdb_temp")
            os.makedirs(temp_dir, exist_ok=True)
            con.execute(f"SET memory_limit = '{_sql_str(os.getenv('DUCKDB_MEMORY_LIMIT', '220MB'))}'")
            con.execute("SET threads = 1")
            con.execute(f"SET temp_directory = '{_sql_str(temp_dir)}'")
            con.execute("INSTALL httpfs")
            con.execute("LOAD httpfs")
            token = os.getenv("HF_TOKEN", "").strip()
            if token:  # only needed if the dataset is private
                con.execute(f"CREATE OR REPLACE SECRET hf_token (TYPE huggingface, TOKEN '{_sql_str(token)}')")
        else:
            con.execute("SET threads = 4")
            con.execute("SET memory_limit = '3GB'")
        con.execute("SET enable_progress_bar = false")  # server logs, not a terminal
    except Exception as exc:
        con.close()
        raise ArchiveNotReady(f"DuckDB setup failed: {exc}") from exc
    _CON = con
    return con


def _hotspots_glob() -> str:
    return f"{HF_BASE}/{HF_HOTSPOTS_PATTERN}" if REMOTE else HOTSPOTS_GLOB


def _view_source(name: str) -> str:
    if REMOTE:
        return {
            "hotspots": f"read_parquet('{_hotspots_glob()}', hive_partitioning = false)",
            "monthly": f"read_parquet('{HF_BASE}/monthly_h3.parquet')",
            "cells": f"read_parquet('{HF_BASE}/h3_cells.parquet')",
            "scores": f"read_parquet('{HF_BASE}/monthly_scores.parquet')",
        }[name]
    if name == "hotspots":
        return f"read_parquet('{HOTSPOTS_GLOB}')"
    path, missing = {
        "monthly": (MONTHLY_H3, "monthly_h3.parquet missing. Run backend.ingestion.build_aggregates."),
        "cells": (H3_CELLS, "h3_cells.parquet missing. Run backend.ingestion.build_aggregates."),
        "scores": (MONTHLY_SCORES, "monthly_scores.parquet not found. Run backend.ml.train_archive."),
    }[name]
    if not path.exists():
        raise ArchiveNotReady(missing)
    return f"read_parquet('{path.as_posix()}')"


def query(views: tuple[str, ...], sql: str, fetch: str = "all"):
    """Runs `sql` on the shared connection after making sure `views` exist.
    fetch: 'all' (list of tuples), 'one' (single tuple) or 'df' (DataFrame)."""
    with _LOCK:
        con = _connection()
        try:
            for name in views:
                if name not in _VIEWS:
                    con.execute(f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM {_view_source(name)}")
                    _VIEWS.add(name)
            cur = con.execute(sql)
            if fetch == "one":
                return cur.fetchone()
            if fetch == "df":
                return cur.df()
            return cur.fetchall()
        except (duckdb.BinderException, duckdb.ParserException, duckdb.CatalogException):
            raise  # query bugs stay 400s
        except duckdb.IOException as exc:  # missing file / network
            raise ArchiveNotReady(f"Archive unavailable: {exc}") from exc
        except duckdb.Error as exc:
            if REMOTE:  # e.g. DNS / connection errors surface as a plain duckdb.Error
                raise ArchiveNotReady(f"Archive unavailable: {exc}") from exc
            raise


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
def _hotspot_file_index() -> tuple[tuple[str, date | None, date | None], ...]:
    """(file, min acq_date, max acq_date) per hotspot file, from Parquet footer
    statistics only. Built once per process."""
    rows = query(
        (),
        f"""
        SELECT file_name,
               MIN(stats_min_value)::DATE AS dmin,
               MAX(stats_max_value)::DATE AS dmax
        FROM parquet_metadata('{_hotspots_glob()}')
        WHERE path_in_schema = 'acq_date'
        GROUP BY 1 ORDER BY 1
        """,
    )
    if not rows:
        raise ArchiveNotReady("No hotspot Parquet files found in the archive.")
    return tuple(rows)


def _hotspots_between(start: str, end: str) -> str:
    """FROM-clause source covering only the hotspot files whose date range
    overlaps [start, end], so a one-day or one-year query opens a handful of
    the 80 files instead of all of them (most important over hf://).
    File names carry no year, so the ranges come from footer statistics.
    Call it before query(): it takes the connection lock itself."""
    s, e = date.fromisoformat(start), date.fromisoformat(end)
    files = [
        f for f, dmin, dmax in _hotspot_file_index()
        if dmin is None or dmax is None or (dmin <= e and dmax >= s)
    ]
    if not files:
        return "(SELECT * FROM hotspots WHERE false)"
    return "read_parquet([" + ", ".join(f"'{_sql_str(f)}'" for f in files) + "])"


def _coverage_from_footers() -> dict:
    """Same shape as the full scan, read from Parquet footer statistics only
    (row counts and per-row-group min/max), so remote mode doesn't pull the
    whole hotspot archive over the network. Each hotspot file holds a single
    source_id; distinct cells come from h3_cells.parquet."""
    groups = query(
        (),
        f"""
        SELECT file_name, row_group_id,
               MAX(CASE WHEN path_in_schema = 'source_id' THEN stats_min_value END) AS source_id,
               MAX(CASE WHEN path_in_schema = 'acq_date' THEN stats_min_value END)::DATE AS dmin,
               MAX(CASE WHEN path_in_schema = 'acq_date' THEN stats_max_value END)::DATE AS dmax,
               MAX(row_group_num_rows) AS n
        FROM parquet_metadata('{_hotspots_glob()}')
        WHERE path_in_schema IN ('source_id', 'acq_date')
        GROUP BY 1, 2
        """,
    )
    cells = query(("cells",), "SELECT COUNT(DISTINCT h3_index) FROM cells", "one")
    per_sensor: dict[str, list] = {}
    years: set[int] = set()
    for _f, _rg, sid, dmin, dmax, n in groups:
        agg = per_sensor.setdefault(sid, [dmin, dmax, 0])
        agg[0], agg[1], agg[2] = min(agg[0], dmin), max(agg[1], dmax), agg[2] + int(n)
        years.update(range(dmin.year, dmax.year + 1))
    if not per_sensor:
        raise ArchiveNotReady("No hotspot Parquet files found in the archive.")
    return {
        "date_min": str(min(v[0] for v in per_sensor.values())),
        "date_max": str(max(v[1] for v in per_sensor.values())),
        "total_detections": sum(v[2] for v in per_sensor.values()),
        "distinct_h3_cells": int(cells[0]),
        "years": sorted(years),
        "sensors": [
            {
                "source_id": sid,
                "label": SENSOR_LABELS.get(sid, sid),
                "date_min": str(dmin),
                "date_max": str(dmax),
                "detections": cnt,
            }
            for sid, (dmin, dmax, cnt) in sorted(per_sensor.items())
        ],
    }


@lru_cache(maxsize=1)
def coverage() -> dict:
    if REMOTE:
        return _coverage_from_footers()
    row = query(
        ("hotspots",),
        "SELECT MIN(acq_date), MAX(acq_date), COUNT(*), COUNT(DISTINCT h3_index) FROM hotspots",
        "one",
    )
    sensors = query(
        ("hotspots",),
        "SELECT source_id, MIN(acq_date), MAX(acq_date), COUNT(*) FROM hotspots GROUP BY 1 ORDER BY 1",
    )
    years = query(("hotspots",), "SELECT DISTINCT year(acq_date) FROM hotspots ORDER BY 1")
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
    source = _hotspots_between(start, end)
    row = query(
        ("hotspots",),
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
        FROM {source} WHERE {_where(bbox, start, end)}
        """,
        "one",
    )
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
    source = _hotspots_between(start, end)
    rows = query(
        ("hotspots",),
        f"""
        SELECT
            {bucket} AS period,
            COUNT(*) AS total,
            SUM(CASE WHEN sensor_family = 'MODIS' THEN 1 ELSE 0 END) AS modis,
            SUM(CASE WHEN sensor_family = 'VIIRS' THEN 1 ELSE 0 END) AS viirs,
            MAX(frp) AS max_frp_mw,
            SUM(frp) AS total_frp_mw
        FROM {source} WHERE {_where(bbox, start, end)}
        GROUP BY 1 ORDER BY 1
        """
    )
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
    rows = query(
        ("monthly", "cells"),
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
    )
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
    rows = query(
        ("monthly", "cells"),
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
    )
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
    w, s, e, n = bbox
    rows = query(
        ("hotspots",),
        f"""
        SELECT year(acq_date) AS year, source_id, COUNT(*) AS detections
        FROM hotspots
        WHERE latitude BETWEEN {s} AND {n} AND longitude BETWEEN {w} AND {e}
        GROUP BY 1, 2 ORDER BY 1, 2
        """
    )
    return [
        {"year": int(r[0]), "source_id": r[1], "label": SENSOR_LABELS.get(r[1], r[1]), "detections": int(r[2])}
        for r in rows
    ]


def hotspots_df(bbox_str: str, start: str, end: str, limit: int | None, sensor: str | None = None) -> pd.DataFrame:
    """Raw detections in bbox/date range. `limit=None` returns every row."""
    bbox = parse_bbox(bbox_str)
    start, end = parse_date(start, "start"), parse_date(end, "end")
    sensor_filter = f" AND sensor_family = '{sensor.upper()}'" if sensor else ""
    limit_sql = f"LIMIT {int(limit)}" if limit is not None else ""
    source = _hotspots_between(start, end)
    return query(
        ("hotspots",),
        f"""
        SELECT latitude, longitude, h3_index, acq_datetime, acq_date, acq_time,
               frp, raw_confidence, confidence_tier, satellite, instrument,
               daynight, sensor_family, processing_level, spatial_res_m, brightness
        FROM {source}
        WHERE {_where(bbox, start, end)}{sensor_filter}
        ORDER BY acq_datetime
        {limit_sql}
        """,
        "df",
    )
