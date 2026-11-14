import numpy as np
import pandas as pd


FEATURE_COLUMNS = [
    "modis_count",
    "viirs_count",
    "matched_group_count",
    "viirs_to_modis_ratio",
    "mean_frp",
    "max_frp",
    "frp_std",
    "high_conf_ratio",
    "burned_area_sq_km",
    "day_of_year_sin",
    "day_of_year_cos",
    "historical_frp_zscore",
]


def build_cell_day_features(
    harmonized_df: pd.DataFrame,
    burned_area_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Aggregates harmonized fire observations into one row per (h3_index, utc_date).
    Produces the exact 12 features required by Isolation Forest (model_schema_v1).
    """
    if harmonized_df.empty:
        return pd.DataFrame(columns=["h3_index", "utc_date"] + FEATURE_COLUMNS)

    df = harmonized_df.copy()
    df["is_modis"] = (df["sensor_family"] == "MODIS").astype(int)
    df["is_viirs"] = (df["sensor_family"] == "VIIRS").astype(int)
    df["is_high_conf"] = (df["confidence_tier"] == "high").astype(int)

    grouped = (
        df.groupby(["h3_index", "utc_date"], as_index=False)
        .agg(
            modis_count=("is_modis", "sum"),
            viirs_count=("is_viirs", "sum"),
            matched_group_count=("match_id", lambda s: s.dropna().nunique()),
            mean_frp=("frp", "mean"),
            max_frp=("frp", "max"),
            frp_std=("frp", "std"),
            high_conf_ratio=("is_high_conf", "mean"),
        )
    )

    # Fill std NaN when a cell has only 1 detection on that day
    grouped["frp_std"] = grouped["frp_std"].fillna(0.0)
    grouped["viirs_to_modis_ratio"] = grouped["viirs_count"] / (grouped["modis_count"] + 1.0)

    # Merge monthly burned-area estimate if available (kept strictly separate from active fire counts)
    if burned_area_df is not None and not burned_area_df.empty:
        grouped = grouped.merge(
            burned_area_df[["h3_index", "utc_date", "burned_area_sq_km"]],
            on=["h3_index", "utc_date"],
            how="left",
        )
        grouped["burned_area_sq_km"] = grouped["burned_area_sq_km"].fillna(0.0)
    else:
        grouped["burned_area_sq_km"] = 0.0

    # Cyclical seasonal encoding (Day of Year -> sin/cos)
    dt = pd.to_datetime(grouped["utc_date"])
    day_of_year = dt.dt.dayofyear
    grouped["day_of_year_sin"] = np.sin(2.0 * np.pi * day_of_year / 365.25)
    grouped["day_of_year_cos"] = np.cos(2.0 * np.pi * day_of_year / 365.25)

    # Cell-level historical FRP z-score (deviation from that cell's baseline)
    cell_stats = grouped.groupby("h3_index")["mean_frp"].transform
    cell_mean = cell_stats("mean")
    cell_std = cell_stats("std").replace(0.0, np.nan)
    grouped["historical_frp_zscore"] = ((grouped["mean_frp"] - cell_mean) / cell_std).fillna(0.0)

    return grouped[["h3_index", "utc_date"] + FEATURE_COLUMNS]