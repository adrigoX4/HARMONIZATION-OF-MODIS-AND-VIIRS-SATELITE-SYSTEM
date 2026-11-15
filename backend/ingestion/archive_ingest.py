"""Converts raw FIRMS yearly archive CSVs (World, standard processing) into Parquet.

Each input CSV becomes one Parquet file under data/processed/archive/hotspots/.
Output schema matches the app's harmonized conventions (sensor_family,
confidence_tier, h3_index, acq_datetime, utc_date) so downstream modules can
consume it. Safe to re-run: existing outputs are skipped.
"""
import re
import time
from pathlib import Path

import h3
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

RAW_DIR = Path("data/raw/archive")
OUT_DIR = Path("data/processed/archive/hotspots")
LOG_PATH = Path("data/processed/archive/ingest.log")
MANIFEST_PATH = Path("data/processed/archive/manifest.csv")

CHUNK_ROWS = 1_000_000
H3_RESOLUTION = 5

SENSORS = {
    "M-C61": {"sensor_family": "MODIS", "source_id": "MODIS_ARCHIVE", "spatial_res_m": 1000},
    "SV-C2": {"sensor_family": "VIIRS", "source_id": "VIIRS_SNPP_ARCHIVE", "spatial_res_m": 375},
    "J1V-C2": {"sensor_family": "VIIRS", "source_id": "VIIRS_NOAA20_ARCHIVE", "spatial_res_m": 375},
    "J2V-C2": {"sensor_family": "VIIRS", "source_id": "VIIRS_NOAA21_ARCHIVE", "spatial_res_m": 375},
}

FILE_RE = re.compile(r"fire_archive_(M-C61|SV-C2|J1V-C2|J2V-C2)_(\d+)\.csv$")

OUT_SCHEMA = pa.schema(
    [
        ("source_id", pa.string()),
        ("sensor_family", pa.string()),
        ("processing_level", pa.string()),
        ("spatial_res_m", pa.int16()),
        ("latitude", pa.float32()),
        ("longitude", pa.float32()),
        ("h3_index", pa.string()),
        ("acq_datetime", pa.timestamp("us")),
        ("acq_date", pa.date32()),
        ("acq_time", pa.int16()),
        ("frp", pa.float32()),
        ("raw_confidence", pa.string()),
        ("confidence_tier", pa.string()),
        ("satellite", pa.string()),
        ("instrument", pa.string()),
        ("daynight", pa.string()),
        ("scan", pa.float32()),
        ("track", pa.float32()),
        ("brightness", pa.float32()),
        ("bright_t31", pa.float32()),
        ("fire_type", pa.int8()),
    ]
)

VIIRS_TIER = {"l": "low", "n": "nominal", "h": "high"}


def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def normalize_chunk(df: pd.DataFrame, sensor_family: str) -> pd.DataFrame:
    df.columns = [c.strip().lower() for c in df.columns]
    for col in ("satellite", "instrument", "daynight"):
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce").astype("float32")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce").astype("float32")
    df["frp"] = pd.to_numeric(df["frp"], errors="coerce").astype("float32")
    for col in ("scan", "track", "brightness", "bright_t31"):
        df[col] = pd.to_numeric(df.get(col), errors="coerce").astype("float32")

    time_str = df["acq_time"].astype(str).str.strip().str.zfill(4)
    dt = pd.to_datetime(
        df["acq_date"].astype(str).str.strip() + " " + time_str,
        format="%Y-%m-%d %H%M",
        errors="coerce",
    )
    df["acq_datetime"] = dt
    df["acq_date"] = dt.dt.date
    df["acq_time"] = pd.to_numeric(time_str, errors="coerce").fillna(0).astype("int16")

    raw_conf = df["confidence"].astype(str).str.strip()
    df["raw_confidence"] = raw_conf
    if sensor_family == "MODIS":
        score = pd.to_numeric(raw_conf, errors="coerce")
        df["confidence_tier"] = np.select(
            [score < 30, score < 80], ["low", "nominal"], default="high"
        )
        df["fire_type"] = np.nan
    else:
        df["confidence_tier"] = raw_conf.str.lower().map(VIIRS_TIER).fillna("unknown")
        df["fire_type"] = pd.to_numeric(df.get("type"), errors="coerce")

    df = df.dropna(subset=["latitude", "longitude", "acq_datetime"])
    df = df[(df["latitude"].between(-90, 90)) & (df["longitude"].between(-180, 180))]

    df["h3_index"] = [
        h3.latlng_to_cell(lat, lon, H3_RESOLUTION)
        for lat, lon in zip(df["latitude"].values, df["longitude"].values)
    ]

    df["fire_type"] = df["fire_type"].fillna(0).astype("int8")
    df["acq_datetime"] = pd.to_datetime(df["acq_datetime"]).dt.tz_localize(None).astype("datetime64[us]")
    return df


def process_file(csv_path: Path, meta: dict) -> dict:
    out_path = OUT_DIR / f"{meta['source_id']}_{csv_path.stem.split('_')[-1]}.parquet"
    if out_path.exists():
        log(f"SKIP (exists): {out_path.name}")
        return {"file": csv_path.name, "rows": pq.ParquetFile(out_path).metadata.num_rows, "skipped": True}

    writer = pq.ParquetWriter(out_path, OUT_SCHEMA, compression="zstd", compression_level=3)
    total = 0
    date_min, date_max = None, None
    started = time.time()
    try:
        reader = pd.read_csv(csv_path, chunksize=CHUNK_ROWS, low_memory=False)
        for i, chunk in enumerate(reader):
            df = normalize_chunk(chunk, meta["sensor_family"])
            df["source_id"] = meta["source_id"]
            df["sensor_family"] = meta["sensor_family"]
            df["processing_level"] = "SP"
            df["spatial_res_m"] = meta["spatial_res_m"]

            table = pa.Table.from_pandas(df[OUT_SCHEMA.names], schema=OUT_SCHEMA, preserve_index=False)
            writer.write_table(table, row_group_size=500_000)
            total += len(df)

            chunk_min = df["acq_date"].min()
            chunk_max = df["acq_date"].max()
            date_min = chunk_min if date_min is None else min(date_min, chunk_min)
            date_max = chunk_max if date_max is None else max(date_max, chunk_max)
            log(
                f"  {csv_path.name} chunk {i + 1}: {len(df):,} rows "
                f"({total:,} total, {total / max(time.time() - started, 1e-6):,.0f} rows/s)"
            )
    finally:
        writer.close()

    if total == 0:
        out_path.unlink(missing_ok=True)
        log(f"EMPTY: {csv_path.name} produced no rows")
        return {"file": csv_path.name, "rows": 0, "skipped": False}

    log(f"DONE {csv_path.name} -> {out_path.name}: {total:,} rows, {date_min}..{date_max}")
    return {
        "file": csv_path.name,
        "source_id": meta["source_id"],
        "sensor_family": meta["sensor_family"],
        "rows": total,
        "date_min": str(date_min),
        "date_max": str(date_max),
        "parquet": str(out_path),
        "skipped": False,
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_files = sorted(p for p in RAW_DIR.glob("fire_archive_*.csv") if FILE_RE.search(p.name))
    if not csv_files:
        raise SystemExit(f"No archive CSVs found in {RAW_DIR}")

    log(f"=== Archive ingestion start: {len(csv_files)} CSVs ===")
    records = []
    for csv_path in csv_files:
        m = FILE_RE.search(csv_path.name)
        meta = SENSORS[m.group(1)]
        log(f"Processing {csv_path.name} ({meta['source_id']})")
        records.append(process_file(csv_path, meta))

    manifest = pd.DataFrame(records)
    manifest.to_csv(MANIFEST_PATH, index=False)
    log(f"=== Finished. Total rows: {int(manifest['rows'].sum()):,}. Manifest: {MANIFEST_PATH} ===")


if __name__ == "__main__":
    main()
