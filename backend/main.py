from functools import lru_cache
from pathlib import Path
from typing import Optional
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.calendar.aggregator import build_burning_calendar
from backend.ml.features import build_cell_day_features
from backend.ml.predictor import score_cell_day_anomalies
from backend.api.archive_routes import router as archive_router

app = FastAPI(
    title="NASA MODIS–VIIRS Fire Harmonization API",
    version="1.0.0",
    description="Global multi-sensor MODIS + VIIRS satellite fire harmonization, Burning Calendar, and Calibrated Isolation Forest Anomaly Intelligence.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(archive_router)

HISTORY_CSV = Path("data/processed/harmonized_history.csv")
SAMPLE_HARMONIZED_CSV = Path("data/processed/harmonized_sample.csv")
SAMPLE_PAIRS_CSV = Path("data/processed/matched_pairs_sample.csv")


@lru_cache(maxsize=1)
def _load_full_dataset() -> pd.DataFrame:
    csv_path = HISTORY_CSV if HISTORY_CSV.exists() else SAMPLE_HARMONIZED_CSV
    if not csv_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Processed data not found. Run 'python -m backend.ingestion.run_ingestion' first.",
        )
    return pd.read_csv(csv_path, low_memory=False)


def _get_active_window_df() -> pd.DataFrame:
    """Returns the latest global active window (Nov 2026) for responsive dashboard & map rendering."""
    df = _load_full_dataset()
    if HISTORY_CSV.exists() and not df.empty:
        recent = df[df["utc_date"] >= "2026-11-05"]
        if not recent.empty:
            return recent
    return df


def _build_pairs_from_df(df: pd.DataFrame) -> pd.DataFrame:
    """Constructs cross-sensor MODIS-VIIRS paired cluster records directly from harmonized detections."""
    if SAMPLE_PAIRS_CSV.exists() and not HISTORY_CSV.exists():
        return pd.read_csv(SAMPLE_PAIRS_CSV)

    matched = df[df["match_status"].isin(["Matched", "Possible Match"]) & df["match_id"].notna()].copy()
    if matched.empty:
        return pd.DataFrame()

    modis = matched[matched["sensor_family"] == "MODIS"].drop_duplicates(subset=["match_id"])
    viirs = matched[matched["sensor_family"] == "VIIRS"].drop_duplicates(subset=["match_id"])
    merged = pd.merge(
        modis,
        viirs,
        on="match_id",
        suffixes=("_modis", "_viirs"),
        how="inner",
    )
    if merged.empty:
        return pd.DataFrame()

    pairs = pd.DataFrame({
        "match_id": merged["match_id"],
        "match_status": merged["match_status_modis"],
        "utc_date": merged["utc_date_modis"],
        "h3_index": merged["h3_index_modis"],
        "modis_source_id": merged["source_id_modis"],
        "viirs_source_id": merged["source_id_viirs"],
        "modis_frp": merged["frp_modis"],
        "viirs_frp": merged["frp_viirs"],
        "distance_km": merged["nearest_dist_km_modis"].fillna(0.0).round(3),
        "time_diff_min": merged["time_diff_min_modis"].fillna(0.0).round(1),
    })
    return pairs.sort_values(["utc_date", "viirs_frp"], ascending=[False, False]).reset_index(drop=True)


@app.get("/")
def root():
    df = _load_full_dataset()
    return {
        "status": "online",
        "coverage": "global",
        "service": "MODIS-VIIRS Harmonization Backend",
        "dataset": "harmonized_history.csv (Real Global NASA FIRMS)" if HISTORY_CSV.exists() else "sample",
        "total_rows": int(len(df)),
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/v1/dashboard")
def get_dashboard_summary():
    df = _get_active_window_df()
    full_df = _load_full_dataset()

    modis_df = df[df["sensor_family"] == "MODIS"]
    viirs_df = df[df["sensor_family"] == "VIIRS"]

    return {
        "total_observations": int(len(df)),
        "total_historical_archive": int(len(full_df)),
        "modis_count": int(len(modis_df)),
        "viirs_count": int(len(viirs_df)),
        "paired_clusters": int(df["match_id"].dropna().nunique()),
        "match_breakdown": df["match_status"].value_counts().to_dict(),
        "mean_frp_mw": round(float(df["frp"].mean()), 2) if not df.empty else 0.0,
        "max_frp_mw": round(float(df["frp"].max()), 2) if not df.empty else 0.0,
        "date_range": {
            "start": str(df["utc_date"].min()) if not df.empty else None,
            "end": str(df["utc_date"].max()) if not df.empty else None,
        },
    }


@app.get("/api/v1/fires/geojson")
def get_fires_geojson(
    sensor: Optional[str] = Query(None, description="Filter by MODIS or VIIRS"),
    match_status: Optional[str] = Query(None, description="Filter by Matched, Possible Match, MODIS-only, VIIRS-only"),
    date: Optional[str] = Query(None, description="Filter by YYYY-MM-DD"),
    limit: int = Query(5000, ge=100, le=15000, description="Max global points returned for smooth map rendering"),
):
    df = _load_full_dataset() if date else _get_active_window_df()

    if sensor:
        df = df[df["sensor_family"].str.upper() == sensor.upper()]
    if match_status:
        df = df[df["match_status"].str.lower() == match_status.lower()]
    if date:
        df = df[df["utc_date"] == date]

    # Sample proportionally across all continents/latitude-longitude bands if capping points for browser map FPS
    if len(df) > limit:
        df = df.sample(n=limit, random_state=42)

    features = []
    for _, row in df.iterrows():
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(row["longitude"]), float(row["latitude"])],
            },
            "properties": {
                "source_id": row["source_id"],
                "sensor_family": row["sensor_family"],
                "spatial_res_m": int(row["spatial_res_m"]),
                "utc_date": row["utc_date"],
                "acq_datetime": str(row["acq_datetime"]),
                "frp": float(row["frp"]),
                "confidence_tier": row["confidence_tier"],
                "raw_confidence": str(row["raw_confidence"]),
                "h3_index": row["h3_index"],
                "match_status": row["match_status"],
                "match_id": None if pd.isna(row["match_id"]) else row["match_id"],
                "nearest_dist_km": None if pd.isna(row["nearest_dist_km"]) else float(row["nearest_dist_km"]),
                "time_diff_min": None if pd.isna(row["time_diff_min"]) else float(row["time_diff_min"]),
            },
        })

    return {
        "type": "FeatureCollection",
        "count": len(features),
        "features": features,
    }


@app.get("/api/v1/harmonization/matches")
def get_harmonization_matches(limit: int = Query(100, ge=1, le=500)):
    df = _get_active_window_df()
    pairs = _build_pairs_from_df(df)
    if pairs.empty:
        return {"count": 0, "matches": []}

    records = pairs.head(limit).to_dict(orient="records")
    return {"count": len(records), "matches": records}


@app.get("/api/v1/calendar")
def get_burning_calendar(
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
):
    df = _load_full_dataset() if (start_date or end_date) else _get_active_window_df()
    s_date = start_date or str(df["utc_date"].min())
    e_date = end_date or str(df["utc_date"].max())

    days = build_burning_calendar(harmonized_df=df, start_date=s_date, end_date=e_date)
    return {
        "start_date": s_date,
        "end_date": e_date,
        "days": days,
    }


@app.get("/api/v1/anomalies")
def get_calibrated_anomalies(
    limit: int = Query(100, ge=1, le=500),
    only_anomalies: bool = Query(False, description="Return only rows flagged by Isolation Forest"),
):
    df = _get_active_window_df()
    try:
        scored_df = score_cell_day_anomalies(df, only_anomalies=only_anomalies)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    if scored_df.empty:
        return {"count": 0, "anomaly_count": 0, "anomalies": []}

    tier_labels = {
        "extreme": "Extreme Anomaly (≥ 99th pct)",
        "anomalous": "Unusual vs. H3 Seasonal Baseline",
        "elevated": "Elevated Thermal Activity",
        "normal": "Within H3 Seasonal Baseline",
    }
    scored_df["baseline_label"] = scored_df["severity"].map(tier_labels).fillna("Within H3 Seasonal Baseline")

    records = scored_df.head(limit).to_dict(orient="records")
    return {
        "count": len(records),
        "total_cells": int(len(scored_df)),
        "anomaly_count": int(scored_df["is_anomaly"].sum()),
        "anomalies": records,
    }


@app.get("/api/v1/ml/features-preview")
def get_ml_features_preview(limit: int = Query(20, ge=1, le=200)):
    df = _get_active_window_df()
    features_df = build_cell_day_features(df)
    return {
        "count": len(features_df),
        "columns": list(features_df.columns),
        "sample": features_df.head(limit).to_dict(orient="records"),
    }