"""Backfills the archive's trailing gap (Aug-Nov 2026) via the live FIRMS API.

The FIRMS archive lags ~3 months, so the newest weeks are only available as
NRT/SP API pulls. This fetches world 5-day chunks for every sensor, normalizes
them with the same schema as archive_ingest.py, and writes per-source Parquet
files. Safe to re-run: existing chunk files are skipped.
"""
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from backend.ingestion.archive_ingest import OUT_SCHEMA, normalize_chunk, log
from backend.ingestion.firms_client import fetch_area_fires, fetch_data_availability

OUT_DIR = Path("data/processed/archive/hotspots")
RAW_DIR = Path("data/raw/backfill")

SENSOR_FORMATS = {
    "MODIS": {"family": "MODIS", "res": 1000},
    "VIIRS_SNPP": {"family": "VIIRS", "res": 375},
    "VIIRS_NOAA20": {"family": "VIIRS", "res": 375},
    "VIIRS_NOAA21": {"family": "VIIRS", "res": 375},
}

# First day NOT covered by the downloaded archive, per sensor.
START_DATES = {
    "MODIS": "2026-09-01",
    "VIIRS_SNPP": "2026-08-01",
    "VIIRS_NOAA20": "2026-08-01",
    "VIIRS_NOAA21": "2026-08-01",
}
END_DATE = "2026-11-15"


def _sp_max_dates() -> dict[str, str]:
    df = fetch_data_availability("ALL")
    out = {}
    for _, row in df.iterrows():
        key = str(row.get("data_id", "")).upper()
        if key.endswith("_SP"):
            out[key] = str(row.get("max_date", ""))
    return out


def _iter_chunks(start: str, end: str):
    cursor = date.fromisoformat(end)
    stop = date.fromisoformat(start)
    while cursor >= stop:
        chunk_start = max(stop, cursor - timedelta(days=4))
        yield chunk_start.isoformat(), cursor.isoformat()
        cursor = chunk_start - timedelta(days=1)


def backfill_sensor(sensor: str, sp_max: dict[str, str]) -> None:
    meta = SENSOR_FORMATS[sensor]
    _ = sp_max  # availability consulted per chunk below
    for start, end in _iter_chunks(START_DATES[sensor], END_DATE):
        sp_key = f"{sensor}_SP"
        nrt_key = f"{sensor}_NRT"
        source = sp_key if sp_max.get(sp_key, "") >= end else nrt_key
        out_path = OUT_DIR / f"{source}_backfill_{start}_{end}.parquet"
        if out_path.exists():
            log(f"SKIP backfill {source} {start}..{end}")
            continue

        df = fetch_area_fires(
            source=source, bbox="world", day_range=5, date=end, save_raw=False
        )
        if df is None or df.empty or "latitude" not in df.columns:
            log(f"EMPTY backfill {source} {start}..{end}")
            continue

        df = df[pd.to_datetime(df["acq_date"]).between(start, end)]
        if df.empty:
            log(f"EMPTY after range filter {source} {start}..{end}")
            continue

        df = normalize_chunk(df, meta["family"])
        df["source_id"] = source
        df["sensor_family"] = meta["family"]
        df["processing_level"] = "SP" if source.endswith("_SP") else "NRT"
        df["spatial_res_m"] = meta["res"]

        table = pa.Table.from_pandas(df[OUT_SCHEMA.names], schema=OUT_SCHEMA, preserve_index=False)
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        pq.write_table(table, out_path, compression="zstd")
        log(f"BACKFILL {source} {start}..{end}: {len(df):,} rows -> {out_path.name}")
        time.sleep(1.2)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    sp_max = {}
    try:
        sp_max = _sp_max_dates()
        log(f"SP availability: {sp_max}")
    except Exception as exc:  # availability endpoint is advisory; NRT fallback still works
        log(f"WARN could not read availability: {exc}")

    for sensor in SENSOR_FORMATS:
        log(f"=== Backfilling {sensor} from {START_DATES[sensor]} to {END_DATE} ===")
        backfill_sensor(sensor, sp_max)
    log("=== Backfill finished ===")


if __name__ == "__main__":
    main()
