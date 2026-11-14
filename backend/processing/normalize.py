import pandas as pd
import h3


def _normalize_confidence(row: pd.Series, sensor_family: str) -> str:
    """
    Maps MODIS numeric confidence (0-100) and VIIRS categorical confidence (l, n, h)
    into a unified tier: 'low', 'nominal', or 'high'.
    """
    val = str(row["confidence"]).strip().lower()

    if sensor_family == "MODIS":
        try:
            score = float(val)
            if score < 30:
                return "low"
            elif score < 80:
                return "nominal"
            else:
                return "high"
        except ValueError:
            return "unknown"

    elif sensor_family == "VIIRS":
        mapping = {"l": "low", "n": "nominal", "h": "high"}
        return mapping.get(val, "unknown")

    return "unknown"


def normalize_firms_df(df: pd.DataFrame, source_id: str, h3_resolution: int = 5) -> pd.DataFrame:
    """
    Standardizes a raw NASA FIRMS DataFrame (MODIS or VIIRS) while preserving original values.
    """
    if df.empty:
        return pd.DataFrame()

    out = df.copy()

    # 1. Identify sensor family, processing level, and native pixel resolution
    source_upper = source_id.upper()
    sensor_family = "MODIS" if "MODIS" in source_upper else "VIIRS"
    processing_level = "SP" if source_upper.endswith("_SP") else "NRT"
    spatial_res_m = 1000 if sensor_family == "MODIS" else 375

    out["source_id"] = source_id
    out["sensor_family"] = sensor_family
    out["processing_level"] = processing_level
    out["spatial_res_m"] = spatial_res_m

    # 2. Zero-pad acq_time (e.g., 705 -> '0705') and build UTC datetime
    time_str = out["acq_time"].astype(str).str.strip().str.zfill(4)
    datetime_str = out["acq_date"].astype(str).str.strip() + " " + time_str
    out["acq_datetime"] = pd.to_datetime(datetime_str, format="%Y-%m-%d %H%M", utc=True)
    out["utc_date"] = out["acq_datetime"].dt.strftime("%Y-%m-%d")

    # 3. Preserve raw confidence & add harmonized confidence tier
    out["raw_confidence"] = out["confidence"].astype(str)
    out["confidence_tier"] = out.apply(_normalize_confidence, axis=1, sensor_family=sensor_family)

    # 4. Ensure numeric types for scientific measurements
    out["latitude"] = pd.to_numeric(out["latitude"], errors="coerce")
    out["longitude"] = pd.to_numeric(out["longitude"], errors="coerce")
    out["frp"] = pd.to_numeric(out["frp"], errors="coerce")

    # 5. Assign global H3 hexagonal grid index (Resolution 5 ≈ 252 km² per cell)
    out["h3_index"] = [
        h3.latlng_to_cell(lat, lon, h3_resolution)
        for lat, lon in zip(out["latitude"], out["longitude"])
    ]

    # Select and order clean columns (preserving key raw attributes)
    keep_cols = [
        "source_id",
        "sensor_family",
        "processing_level",
        "spatial_res_m",
        "latitude",
        "longitude",
        "h3_index",
        "acq_datetime",
        "utc_date",
        "frp",
        "raw_confidence",
        "confidence_tier",
        "satellite",
        "instrument",
        "daynight",
        "scan",
        "track",
    ]
    # Keep only columns present in the raw CSV
    final_cols = [c for c in keep_cols if c in out.columns]
    return out[final_cols].reset_index(drop=True)