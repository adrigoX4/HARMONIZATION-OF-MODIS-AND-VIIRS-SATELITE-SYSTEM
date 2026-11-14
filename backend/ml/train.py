import os
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler

from backend.ml.features import FEATURE_COLUMNS, build_cell_day_features

load_dotenv()

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
HISTORY_CSV = DATA_DIR / "processed" / "harmonized_history.csv"
BASELINES_CSV = DATA_DIR / "processed" / "h3_baselines_v1.csv"
MODEL_PATH = Path(os.getenv("MODEL_PATH", "models/isolation_forest_v1.joblib"))
DEFAULT_BBOX = os.getenv("DEFAULT_BBOX", "75,25,85,32")


def apply_baseline_calibration(
    features_df: pd.DataFrame,
    baselines_df: pd.DataFrame,
    global_frp_mean: float,
    global_frp_std: float,
) -> pd.DataFrame:
    """
    Calibrates `historical_frp_zscore` using multi-season H3 resolution-5 cell baselines
    rather than single-batch sample statistics.
    """
    if features_df.empty:
        return features_df.copy()

    df = features_df.copy()
    if baselines_df is not None and not baselines_df.empty:
        lookup = baselines_df[["h3_index", "active_days", "baseline_mean_frp", "baseline_std_frp"]]
        df = df.merge(lookup, on="h3_index", how="left")
    else:
        df["active_days"] = 0
        df["baseline_mean_frp"] = np.nan
        df["baseline_std_frp"] = np.nan

    # Use cell-specific baseline when cell has >= 3 historical active days; otherwise fall back to regional baseline
    reliable_cell = df["active_days"].fillna(0) >= 3
    ref_mean = np.where(reliable_cell, df["baseline_mean_frp"], global_frp_mean)
    raw_std = np.where(reliable_cell, df["baseline_std_frp"], global_frp_std)
    safe_std = np.where((np.isnan(raw_std)) | (raw_std <= 1e-3), max(global_frp_std, 1.0), raw_std)

    df["historical_frp_zscore"] = ((df["mean_frp"] - ref_mean) / safe_std).clip(-10.0, 15.0)
    return df.drop(columns=["active_days", "baseline_mean_frp", "baseline_std_frp"], errors="ignore")


def train_isolation_forest(
    history_csv: Path = HISTORY_CSV,
    baselines_csv: Path = BASELINES_CSV,
    model_path: Path = MODEL_PATH,
    contamination: float = 0.05,
    random_state: int = 42,
) -> dict:
    if not history_csv.exists():
        raise FileNotFoundError(f"Missing historical dataset: {history_csv}. Run 'python -m backend.ingestion.run_ingestion' first.")

    print(f"[1/4] Loading historical harmonized records from {history_csv}...")
    history_df = pd.read_csv(history_csv)
    baselines_df = pd.read_csv(baselines_csv) if baselines_csv.exists() else pd.DataFrame()

    print("[2/4] Engineering (h3_index, utc_date) cell-day feature matrix...")
    raw_features = build_cell_day_features(history_df)
    global_frp_mean = float(raw_features["mean_frp"].mean())
    global_frp_std = float(raw_features["mean_frp"].std())

    features_df = apply_baseline_calibration(
        raw_features,
        baselines_df=baselines_df,
        global_frp_mean=global_frp_mean,
        global_frp_std=global_frp_std,
    )

    X = features_df[FEATURE_COLUMNS].fillna(0.0).to_numpy(dtype=np.float64)
    print(f"      Training matrix shape: {X.shape[0]:,} cell-days x {X.shape[1]} features")

    print(f"[3/4] Fitting RobustScaler + IsolationForest (contamination={contamination})...")
    scaler = RobustScaler()
    X_scaled = scaler.fit_transform(X)

    iso_forest = IsolationForest(
        n_estimators=300,
        max_samples="auto",
        contamination=contamination,
        max_features=1.0,
        random_state=random_state,
        n_jobs=-1,
    )
    iso_forest.fit(X_scaled)

    # Compute calibration quantiles on training scores so predictor outputs interpretable [0, 1] risk scores
    raw_scores = -iso_forest.decision_function(X_scaled)  # higher = more anomalous
    preds = iso_forest.predict(X_scaled)  # -1 = anomaly, 1 = normal
    score_p50 = float(np.percentile(raw_scores, 50))
    score_p95 = float(np.percentile(raw_scores, 95))
    score_p99 = float(np.percentile(raw_scores, 99))

    features_df["anomaly_flag"] = (preds == -1)
    features_df["raw_anomaly_score"] = raw_scores

    normal_slice = features_df[~features_df["anomaly_flag"]]
    anom_slice = features_df[features_df["anomaly_flag"]]

    print("      --- Calibration & Separation Diagnostics ---")
    print(f"      Flagged anomalous cell-days : {len(anom_slice):,} / {len(features_df):,} ({100 * len(anom_slice) / len(features_df):.2f}%)")
    print(f"      Normal mean FRP             : {normal_slice['mean_frp'].mean():.2f} MW | Anomalous mean FRP: {anom_slice['mean_frp'].mean():.2f} MW")
    print(f"      Normal mean VIIRS count     : {normal_slice['viirs_count'].mean():.2f} | Anomalous mean VIIRS count: {anom_slice['viirs_count'].mean():.2f}")
    print(f"      Score quantiles             : p50={score_p50:.4f}, p95={score_p95:.4f}, p99={score_p99:.4f}")

    # Store compact per-H3 baseline lookup inside artifact so predictor is 100% self-contained
    baseline_records = (
        baselines_df.to_dict(orient="records")
        if not baselines_df.empty
        else []
    )

    artifact = {
        "schema_version": "model_schema_v1",
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "bbox": DEFAULT_BBOX,
        "h3_resolution": 5,
        "feature_columns": FEATURE_COLUMNS,
        "scaler": scaler,
        "model": iso_forest,
        "calibration": {
            "contamination": contamination,
            "global_frp_mean": global_frp_mean,
            "global_frp_std": global_frp_std,
            "score_p50": score_p50,
            "score_p95": score_p95,
            "score_p99": score_p99,
            "training_rows": int(len(features_df)),
            "training_hexagons": int(features_df["h3_index"].nunique()),
        },
        "h3_baselines": baseline_records,
    }

    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, model_path, compress=3)
    size_kb = model_path.stat().st_size / 1024.0
    print(f"[4/4] Saved calibrated model bundle -> {model_path} ({size_kb:.1f} KB)")
    return artifact


if __name__ == "__main__":
    train_isolation_forest()
