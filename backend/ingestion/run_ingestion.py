import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

from backend.harmonization.matcher import harmonize_modis_viirs
from backend.ingestion.firms_client import fetch_area_fires, fetch_data_availability
from backend.processing.normalize import normalize_firms_df

load_dotenv()

DEFAULT_BBOX = os.getenv("DEFAULT_BBOX", "75,25,85,32")
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
PROCESSED_DIR = DATA_DIR / "processed"

# Representative Northern India fire windows across seasons & years:
# - Post-monsoon crop residue burning (Oct-Nov)
# - Pre-monsoon rabi harvest & Himalayan foothill forest fires (Apr-May)
# - Recent NRT window (Nov 2026)
HISTORICAL_WINDOWS = [
    ("2024-10-20", "2024-11-15"),  # 2024 post-monsoon stubble peak
    ("2025-04-15", "2025-05-10"),  # 2025 pre-monsoon fire season
    ("2025-10-20", "2025-11-15"),  # 2025 post-monsoon stubble peak
    ("2026-04-15", "2026-05-10"),  # 2026 pre-monsoon fire season
    ("2026-11-01", "2026-11-14"),  # 2026 recent NRT window
]


def _iter_5day_chunks(start_str: str, end_str: str):
    """Yields (chunk_end_date_str, day_range) stepping backward in <=5-day chunks."""
    start_dt = datetime.strptime(start_str, "%Y-%m-%d").date()
    end_dt = datetime.strptime(end_str, "%Y-%m-%d").date()
    cursor = end_dt
    while cursor >= start_dt:
        span = min(5, (cursor - start_dt).days + 1)
        yield cursor.strftime("%Y-%m-%d"), span
        cursor -= timedelta(days=span)


def _select_sources_for_date(end_date_str: str, avail_map: dict[str, tuple[str, str]]) -> tuple[str, str]:
    """
    Enforces SP > NRT priority using live NASA FIRMS availability dates.
    """
    modis_sp_max = avail_map.get("MODIS_SP", ("", ""))[1]
    viirs_sp_max = avail_map.get("VIIRS_NOAA20_SP", ("", ""))[1]

    modis_src = "MODIS_SP" if modis_sp_max and end_date_str <= modis_sp_max else "MODIS_NRT"
    viirs_src = "VIIRS_NOAA20_SP" if viirs_sp_max and end_date_str <= viirs_sp_max else "VIIRS_NOAA20_NRT"
    return modis_src, viirs_src


def compute_h3_baselines(harmonized_df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes calibrated multi-year baseline statistics per H3 resolution-5 cell
    (both overall cell baseline and month-specific seasonal baseline).
    """
    if harmonized_df.empty:
        return pd.DataFrame()

    df = harmonized_df.copy()
    df["month"] = pd.to_datetime(df["utc_date"]).dt.month
    df["is_modis"] = (df["sensor_family"] == "MODIS").astype(int)
    df["is_viirs"] = (df["sensor_family"] == "VIIRS").astype(int)

    cell_day = (
        df.groupby(["h3_index", "utc_date", "month"], as_index=False)
        .agg(
            modis_count=("is_modis", "sum"),
            viirs_count=("is_viirs", "sum"),
            total_detections=("frp", "count"),
            mean_frp=("frp", "mean"),
            max_frp=("frp", "max"),
        )
    )

    baselines = (
        cell_day.groupby("h3_index", as_index=False)
        .agg(
            active_days=("utc_date", "nunique"),
            baseline_mean_frp=("mean_frp", "mean"),
            baseline_std_frp=("mean_frp", "std"),
            baseline_p95_frp=("max_frp", lambda s: float(np.percentile(s, 95))),
            baseline_mean_detections=("total_detections", "mean"),
            baseline_std_detections=("total_detections", "std"),
            baseline_viirs_share=("viirs_count", lambda s: float(s.sum() / max(1, cell_day.loc[s.index, "total_detections"].sum()))),
        )
    )
    baselines["baseline_std_frp"] = baselines["baseline_std_frp"].fillna(0.0)
    baselines["baseline_std_detections"] = baselines["baseline_std_detections"].fillna(0.0)
    return baselines


def run_historical_ingestion(bbox: str = DEFAULT_BBOX, windows: list[tuple[str, str]] = HISTORICAL_WINDOWS):
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[1/4] Checking NASA FIRMS data availability for AOI bbox={bbox}...")
    avail_df = fetch_data_availability("ALL")
    avail_map = {
        row["data_id"]: (str(row["min_date"]), str(row["max_date"]))
        for _, row in avail_df.iterrows()
    }

    all_harmonized = []
    all_pairs = []

    print(f"[2/4] Ingesting {len(windows)} historical windows in 5-day chunks (SP > NRT priority)...")
    for win_start, win_end in windows:
        modis_chunks = []
        viirs_chunks = []
        for chunk_end, span in _iter_5day_chunks(win_start, win_end):
            modis_src, viirs_src = _select_sources_for_date(chunk_end, avail_map)
            print(f"  -> Window {win_start}..{win_end} | chunk end={chunk_end} ({span}d) [{modis_src}, {viirs_src}]")

            raw_m = fetch_area_fires(source=modis_src, bbox=bbox, day_range=span, date=chunk_end, save_raw=True)
            time.sleep(0.5)
            raw_v = fetch_area_fires(source=viirs_src, bbox=bbox, day_range=span, date=chunk_end, save_raw=True)
            time.sleep(0.5)

            if not raw_m.empty:
                modis_chunks.append(normalize_firms_df(raw_m, source_id=modis_src, h3_resolution=5))
            if not raw_v.empty:
                viirs_chunks.append(normalize_firms_df(raw_v, source_id=viirs_src, h3_resolution=5))

        modis_win = pd.concat(modis_chunks, ignore_index=True) if modis_chunks else pd.DataFrame()
        viirs_win = pd.concat(viirs_chunks, ignore_index=True) if viirs_chunks else pd.DataFrame()

        # Enforce SP > NRT deduplication if overlapping dates exist
        for sensor_df in (modis_win, viirs_win):
            if not sensor_df.empty and "processing_level" in sensor_df.columns:
                sp_dates = set(sensor_df.loc[sensor_df["processing_level"] == "SP", "utc_date"])
                if sp_dates:
                    sensor_df.drop(
                        sensor_df[(sensor_df["processing_level"] == "NRT") & (sensor_df["utc_date"].isin(sp_dates))].index,
                        inplace=True,
                    )

        if modis_win.empty and viirs_win.empty:
            print(f"  !! No detections returned for {win_start}..{win_end}")
            continue

        combined_df, pairs_df = harmonize_modis_viirs(modis_win, viirs_win)
        all_harmonized.append(combined_df)
        if not pairs_df.empty:
            all_pairs.append(pairs_df)
        print(f"     Harmonized {len(combined_df):,} detections ({len(pairs_df):,} paired clusters)")

    if not all_harmonized:
        raise RuntimeError("Historical ingestion produced 0 records. Check FIRMS_MAP_KEY or network connectivity.")

    history_df = pd.concat(all_harmonized, ignore_index=True)
    history_pairs_df = pd.concat(all_pairs, ignore_index=True) if all_pairs else pd.DataFrame()

    history_path = PROCESSED_DIR / "harmonized_history.csv"
    history_df.to_csv(history_path, index=False)
    print(f"[3/4] Saved full historical harmonized dataset -> {history_path} ({len(history_df):,} rows)")

    baselines_df = compute_h3_baselines(history_df)
    baselines_path = PROCESSED_DIR / "h3_baselines_v1.csv"
    baselines_df.to_csv(baselines_path, index=False)
    print(f"[4/4] Saved H3 resolution-5 cell baselines -> {baselines_path} ({len(baselines_df):,} hexagons)")

    # Populate default sample files if missing so FastAPI endpoints work out-of-the-box
    sample_csv = PROCESSED_DIR / "harmonized_sample.csv"
    pairs_csv = PROCESSED_DIR / "matched_pairs_sample.csv"
    if not sample_csv.exists():
        recent_slice = all_harmonized[-1]
        recent_slice.to_csv(sample_csv, index=False)
        if all_pairs:
            all_pairs[-1].to_csv(pairs_csv, index=False)
        print(f"      Initialized {sample_csv} with latest window ({len(recent_slice):,} rows)")


if __name__ == "__main__":
    run_historical_ingestion()
