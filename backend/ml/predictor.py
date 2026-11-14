import os
from functools import lru_cache
from pathlib import Path

import h3
import joblib
import numpy as np
import pandas as pd
from dotenv import load_dotenv

from backend.ml.features import FEATURE_COLUMNS, build_cell_day_features
from backend.ml.train import apply_baseline_calibration

load_dotenv()

DEFAULT_MODEL_PATH = Path(os.getenv("MODEL_PATH", "models/isolation_forest_v1.joblib"))


@lru_cache(maxsize=2)
def load_model_artifact(model_path: str = str(DEFAULT_MODEL_PATH)) -> dict:
    path = Path(model_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Trained Isolation Forest model not found at '{path}'. "
            "Run 'python -m backend.ml.train' first."
        )
    return joblib.load(path)


def _explain_row(row: pd.Series) -> list[str]:
    reasons = []
    if row["historical_frp_zscore"] >= 2.5:
        reasons.append(f"Mean FRP +{row['historical_frp_zscore']:.1f}σ above H3 cell baseline ({row['mean_frp']:.1f} MW)")
    elif row["max_frp"] >= 100.0:
        reasons.append(f"High peak radiative power ({row['max_frp']:.1f} MW)")

    total_det = row["modis_count"] + row["viirs_count"]
    if total_det >= 15:
        reasons.append(f"Dense cluster surge ({int(total_det)} detections: {int(row['viirs_count'])} VIIRS, {int(row['modis_count'])} MODIS)")

    if row["viirs_count"] >= 5 and row["modis_count"] == 0:
        reasons.append("VIIRS-only sub-pixel thermal cluster missed by 1km MODIS")

    if row["high_conf_ratio"] >= 0.75 and total_det >= 3:
        reasons.append(f"High satellite confidence ({int(round(row['high_conf_ratio'] * 100))}% high-tier)")

    if not reasons:
        reasons.append("Multivariate seasonal/intensity deviation from regional norm")
    return reasons


def score_cell_day_anomalies(
    harmonized_df: pd.DataFrame,
    burned_area_df: pd.DataFrame | None = None,
    model_path: str | Path = DEFAULT_MODEL_PATH,
    only_anomalies: bool = False,
) -> pd.DataFrame:
    """
    Scores harmonized MODIS+VIIRS observations at (h3_index, utc_date) granularity
    using the calibrated Isolation Forest model and multi-season H3 baselines.
    """
    if harmonized_df.empty:
        return pd.DataFrame()

    artifact = load_model_artifact(str(model_path))
    feature_cols = artifact.get("feature_columns", FEATURE_COLUMNS)
    scaler = artifact["scaler"]
    model = artifact["model"]
    cal = artifact["calibration"]

    baselines_records = artifact.get("h3_baselines", [])
    baselines_df = pd.DataFrame(baselines_records) if baselines_records else pd.DataFrame()

    raw_features = build_cell_day_features(harmonized_df, burned_area_df=burned_area_df)
    calibrated = apply_baseline_calibration(
        raw_features,
        baselines_df=baselines_df,
        global_frp_mean=cal["global_frp_mean"],
        global_frp_std=cal["global_frp_std"],
    )

    X = calibrated[feature_cols].fillna(0.0).to_numpy(dtype=np.float64)
    X_scaled = scaler.transform(X)

    raw_scores = -model.decision_function(X_scaled)
    preds = model.predict(X_scaled)

    # Normalize raw decision score to intuitive [0, 1] risk index anchored at training p50..p99
    denom = max(cal["score_p99"] - cal["score_p50"], 1e-6)
    norm_score = np.clip((raw_scores - cal["score_p50"]) / denom, 0.0, 1.0)

    out = calibrated.copy()
    out["anomaly_score"] = np.round(norm_score, 4)
    out["raw_decision_score"] = np.round(raw_scores, 4)
    out["is_anomaly"] = (preds == -1)

    def _tier(row) -> str:
        if row["anomaly_score"] >= 0.90 and row["is_anomaly"]:
            return "extreme"
        if row["is_anomaly"]:
            return "anomalous"
        if row["anomaly_score"] >= 0.65:
            return "elevated"
        return "normal"

    out["severity"] = out.apply(_tier, axis=1)
    out["drivers"] = out.apply(_explain_row, axis=1)

    # Attach H3 cell center coordinates for map overlays
    centers = [h3.cell_to_latlng(idx) for idx in out["h3_index"]]
    out["center_lat"] = [round(c[0], 5) for c in centers]
    out["center_lon"] = [round(c[1], 5) for c in centers]

    out = out.sort_values(["anomaly_score", "mean_frp"], ascending=[False, False]).reset_index(drop=True)
    if only_anomalies:
        out = out[out["is_anomaly"]].reset_index(drop=True)
    return out
