"""Trains a calibrated Isolation Forest on archive monthly H3 aggregates.

Unlike backend/ml/train.py (single-window day-level), this model learns normal
burning behaviour per H3 cell-month across 2003-2026 and scores every
(h3_index, year, month) record for the anomaly calendar/map layers.

Outputs:
- models/isolation_forest_archive_v1.joblib
- data/processed/archive/monthly_scores.parquet (score, severity per cell-month)
"""
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler

MONTHLY = Path("data/processed/archive/monthly_h3.parquet")
BASELINES = Path("data/processed/archive/baselines_h3_month.parquet")
Scores_PATH = Path("data/processed/archive/monthly_scores.parquet")
MODEL_PATH = Path("models/isolation_forest_archive_v1.joblib")

FEATURES = [
    "log_total",
    "viirs_share",
    "frp_mean_mw",
    "log_frp_sum",
    "log_baseline_mean",
    "count_z",
    "log_baseline_p95",
    "satellite_count",
]


def build_features() -> pd.DataFrame:
    monthly = pd.read_parquet(MONTHLY)
    base = pd.read_parquet(
        BASELINES,
        columns=[
            "h3_index",
            "month",
            "baseline_count_mean",
            "baseline_count_std",
            "baseline_count_p95",
            "baseline_count_median",
        ],
    )
    df = monthly.merge(base, on=["h3_index", "month"], how="left")

    df["log_total"] = np.log1p(df["total_detections"])
    df["viirs_share"] = df["viirs_count"] / df["total_detections"].clip(lower=1)
    df["log_frp_sum"] = np.log1p(df["frp_sum_mw"].clip(lower=0))
    df["log_baseline_mean"] = np.log1p(df["baseline_count_mean"].fillna(0).clip(lower=0))
    df["log_baseline_p95"] = np.log1p(df["baseline_count_p95"].fillna(0).clip(lower=0))
    std = df["baseline_count_std"].replace(0, np.nan)
    df["count_z"] = ((df["total_detections"] - df["baseline_count_mean"]) / std).clip(-10, 15)
    df["count_z"] = df["count_z"].fillna(0)
    df["frp_mean_mw"] = df["frp_mean_mw"].fillna(0)
    df["satellite_count"] = df["satellite_count"].fillna(0)
    return df


def severity(score: pd.Series, z: pd.Series) -> pd.Series:
    conditions = [
        (score >= 0.90) & (z >= 1.5),
        score >= 0.90,
        score >= 0.65,
    ]
    return pd.Series(
        np.select(conditions, ["extreme", "anomalous", "elevated"], default="normal"),
        index=score.index,
    )


def main() -> None:
    print("[1/4] Building features from monthly_h3 + baselines...")
    df = build_features()
    X = df[FEATURES].to_numpy(dtype=np.float32)
    print(f"      rows={len(df):,} features={len(FEATURES)}")

    print("[2/4] Scaling + fitting IsolationForest (300 trees, contamination=0.05)...")
    scaler = RobustScaler()
    Xs = scaler.fit_transform(X)
    model = IsolationForest(
        n_estimators=150,
        contamination=0.05,
        max_samples=4096,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(Xs)

    print("[3/4] Scoring + calibrating...")
    raw = -model.decision_function(Xs)
    q50, q95, q99 = np.quantile(raw, [0.5, 0.95, 0.99])
    lo, hi = np.quantile(raw, [0.001, 0.999])
    score = np.clip((raw - lo) / max(hi - lo, 1e-9), 0, 1)

    df["anomaly_raw"] = raw
    df["anomaly_score"] = score
    df["severity"] = severity(pd.Series(score, index=df.index), df["count_z"]).values
    df["is_anomaly"] = raw >= q95

    print(f"      score quantiles p50={q50:.4f} p95={q95:.4f} p99={q99:.4f}")
    print("      severity:", df["severity"].value_counts().to_dict())

    print("[4/4] Saving scores + model artifact...")
    out_cols = [
        "h3_index",
        "year",
        "month",
        "total_detections",
        "modis_count",
        "viirs_count",
        "frp_sum_mw",
        "frp_max_mw",
        "baseline_count_mean",
        "baseline_count_median",
        "count_z",
        "anomaly_score",
        "severity",
        "is_anomaly",
    ]
    df[out_cols].to_parquet(Scores_PATH, compression="zstd", index=False)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": model,
            "scaler": scaler,
            "features": FEATURES,
            "calibration": {"q50": float(q50), "q95": float(q95), "q99": float(q99),
                            "raw_min": float(lo), "raw_max": float(hi)},
            "trained_rows": int(len(df)),
            "trained_years": [int(df["year"].min()), int(df["year"].max())],
        },
        MODEL_PATH,
    )
    print(f"      model -> {MODEL_PATH} ({MODEL_PATH.stat().st_size / 1e6:.1f} MB)")
    print(f"      scores -> {Scores_PATH} ({Scores_PATH.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
