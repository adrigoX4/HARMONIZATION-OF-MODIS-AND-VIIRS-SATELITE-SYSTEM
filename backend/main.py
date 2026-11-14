from pathlib import Path
from typing import Optional
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.calendar.aggregator import build_burning_calendar
from backend.ml.features import build_cell_day_features

app = FastAPI(
    title="NASA MODIS–VIIRS Fire Harmonization API",
    version="1.0.0",
    description="Harmonized satellite fire detections, Dual-Layer Burning Calendar, and Anomaly Intelligence.",
)

# Allow local frontend dev server (React/Vite) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HARMONIZED_CSV = Path("data/processed/harmonized_sample.csv")
PAIRS_CSV = Path("data/processed/matched_pairs_sample.csv")


def _load_harmonized() -> pd.DataFrame:
    if not HARMONIZED_CSV.exists():
        raise HTTPException(
            status_code=404,
            detail="Processed data not found. Run 'python -m tests.test_harmonization' first.",
        )
    return pd.read_csv(HARMONIZED_CSV)


def _load_pairs() -> pd.DataFrame:
    if not PAIRS_CSV.exists():
        return pd.DataFrame()
    return pd.read_csv(PAIRS_CSV)


@app.get("/")
def root():
    return {"status": "online", "service": "MODIS-VIIRS Harmonization Backend", "docs": "/docs"}


@app.get("/api/v1/dashboard")
def get_dashboard_summary():
    df = _load_harmonized()
    pairs = _load_pairs()

    modis_df = df[df["sensor_family"] == "MODIS"]
    viirs_df = df[df["sensor_family"] == "VIIRS"]

    return {
        "total_observations": int(len(df)),
        "modis_count": int(len(modis_df)),
        "viirs_count": int(len(viirs_df)),
        "paired_clusters": int(len(pairs)),
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
):
    df = _load_harmonized()

    if sensor:
        df = df[df["sensor_family"].str.upper() == sensor.upper()]
    if match_status:
        df = df[df["match_status"].str.lower() == match_status.lower()]
    if date:
        df = df[df["utc_date"] == date]

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
def get_harmonization_matches(limit: int = Query(50, ge=1, le=500)):
    pairs = _load_pairs()
    if pairs.empty:
        return {"count": 0, "matches": []}

    records = pairs.head(limit).to_dict(orient="records")
    return {"count": len(records), "matches": records}


@app.get("/api/v1/calendar")
def get_burning_calendar(
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
):
    df = _load_harmonized()
    s_date = start_date or str(df["utc_date"].min())
    e_date = end_date or str(df["utc_date"].max())

    days = build_burning_calendar(harmonized_df=df, start_date=s_date, end_date=e_date)
    return {
        "start_date": s_date,
        "end_date": e_date,
        "days": days,
    }


@app.get("/api/v1/ml/features-preview")
def get_ml_features_preview(limit: int = Query(20, ge=1, le=200)):
    df = _load_harmonized()
    features_df = build_cell_day_features(df)
    return {
        "count": len(features_df),
        "columns": list(features_df.columns),
        "sample": features_df.head(limit).to_dict(orient="records"),
    }