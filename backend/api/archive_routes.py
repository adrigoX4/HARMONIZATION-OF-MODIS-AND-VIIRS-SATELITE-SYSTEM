"""Archive-backed and Live Real-Time endpoints: global/regional + date-driven queries."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import lru_cache
import math
import os

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query, Response

from backend.archive import store
from backend.api.response_cache import bundle_cache, response_cache
from backend.ingestion.firms_client import fetch_area_fires

router = APIRouter(prefix="/api/v1/archive", tags=["archive"])

PRESETS = [
    {"id": "world", "label": "Global Planetary", "bbox": "-180,-90,180,90"},
    {"id": "india", "label": "South Asia / India", "bbox": "68,6,98,37"},
    {"id": "uttarakhand", "label": "Uttarakhand & Himalaya", "bbox": "75,25,85,32"},
    {"id": "amazon", "label": "Amazon Basin", "bbox": "-75,-20,-45,5"},
    {"id": "california", "label": "California & West US", "bbox": "-125,32,-114,43"},
    {"id": "africa", "label": "Sub-Saharan Africa", "bbox": "-20,-35,52,38"},
    {"id": "australia", "label": "Australia", "bbox": "112,-45,155,-9"},
    {"id": "indonesia", "label": "Southeast Asia / Indonesia", "bbox": "95,-11,141,6"},
    {"id": "europe", "label": "Europe & Mediterranean", "bbox": "-25,34,45,72"},
]

def _fail(exc: Exception) -> HTTPException:
    if isinstance(exc, store.ArchiveNotReady):
        return HTTPException(status_code=503, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


def _harmonize_pairs(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Links MODIS (1 km) and VIIRS (375 m) hotspots within <= 1.5 km and <= 4 hours."""
    if df.empty:
        return df, pd.DataFrame()

    df = df.copy().reset_index(drop=True)
    # Vectorised (was a per-row iterrows loop); same "MOD-2026-10-31-17" format.
    df["source_id"] = (
        df["sensor_family"].astype(str).str[:3]
        + "-"
        + df["acq_date"].astype(str).str[:10]
        + "-"
        + df.index.astype(str)
    )
    df["match_status"] = np.where(df["sensor_family"] == "MODIS", "MODIS-only", "VIIRS-only")
    df["match_id"] = None
    df["nearest_dist_km"] = np.nan
    df["time_diff_min"] = np.nan

    modis = df[df["sensor_family"] == "MODIS"].copy()
    viirs = df[df["sensor_family"] == "VIIRS"].copy()
    if modis.empty or viirs.empty:
        return df, pd.DataFrame()

    # Everything below works on plain NumPy arrays (no iterrows / .iloc / df.at
    # inside the loop) so a complete global day (90k+ rows) harmonizes in a few
    # seconds. The matching rules and their arithmetic are unchanged.
    m_ns = pd.to_datetime(modis["acq_datetime"], errors="coerce").to_numpy("datetime64[ns]")
    v_ns = pd.to_datetime(viirs["acq_datetime"], errors="coerce").to_numpy("datetime64[ns]")
    m_nat = np.isnat(m_ns)
    v_nat = np.isnat(v_ns)
    m_ns = m_ns.astype("int64")
    v_ns = v_ns.astype("int64")

    m_lat_deg_arr = modis["latitude"].to_numpy()
    m_lon_deg_arr = modis["longitude"].to_numpy()
    m_lat = np.radians(m_lat_deg_arr)
    m_lon = np.radians(m_lon_deg_arr)
    v_lat = np.radians(viirs["latitude"].to_numpy())
    v_lon = np.radians(viirs["longitude"].to_numpy())
    m_rows = modis.index.to_numpy()          # positions in df (RangeIndex)
    v_rows = viirs.index.to_numpy()
    m_date = modis["acq_date"].astype(str).str[:10].to_numpy()
    m_h3 = modis["h3_index"].to_numpy()
    m_frp = modis["frp"].to_numpy()
    v_frp = viirs["frp"].to_numpy()
    source_ids = df["source_id"].to_numpy()

    status_col = df["match_status"].to_numpy(dtype=object).copy()
    match_id_col = np.full(len(df), None, dtype=object)
    dist_col = np.full(len(df), np.nan)
    tdiff_col = np.full(len(df), np.nan)

    # Candidate search: VIIRS positions sorted by latitude so each MODIS point only
    # scans a narrow latitude window (binary search) instead of every VIIRS row.
    # The exact +-0.025 deg box test is unchanged, and candidates are put back in
    # original order, so results are identical to the old full scan.
    v_lat_deg = viirs["latitude"].to_numpy()
    v_lon_deg = viirs["longitude"].to_numpy()
    lat_order = np.argsort(v_lat_deg, kind="stable")
    lat_sorted = v_lat_deg[lat_order]
    window = 0.025 + 1e-9

    pairs = []
    pair_counter = 1
    for m_pos in range(len(modis)):
        m_lat_deg = m_lat_deg_arr[m_pos]
        lo = np.searchsorted(lat_sorted, m_lat_deg - window, side="left")
        hi = np.searchsorted(lat_sorted, m_lat_deg + window, side="right")
        if lo >= hi:
            continue
        window_idx = lat_order[lo:hi]
        exact = (np.abs(v_lat_deg[window_idx] - m_lat_deg) <= 0.025) & (
            np.abs(v_lon_deg[window_idx] - m_lon_deg_arr[m_pos]) <= 0.025
        )
        if not np.any(exact):
            continue

        cand_indices = np.sort(window_idx[exact])
        dlat = v_lat[cand_indices] - m_lat[m_pos]
        dlon = v_lon[cand_indices] - m_lon[m_pos]
        a = np.sin(dlat / 2.0) ** 2 + math.cos(m_lat[m_pos]) * np.cos(v_lat[cand_indices]) * np.sin(dlon / 2.0) ** 2
        dist_km = 2.0 * 6371.0 * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))

        t_diff = np.abs((v_ns[cand_indices] - m_ns[m_pos]) / 1e9) / 60.0
        t_diff[v_nat[cand_indices] | m_nat[m_pos]] = np.nan
        t_diff = np.nan_to_num(t_diff, nan=60.0)

        valid = (dist_km <= 2.5) & (t_diff <= 240.0)
        if not np.any(valid):
            continue

        best_local = int(np.argmin(dist_km + (t_diff / 240.0)))
        if not valid[best_local]:
            valid_pos = np.where(valid)[0]
            best_local = int(valid_pos[np.argmin(dist_km[valid_pos])])

        v_pos = int(cand_indices[best_local])
        m_idx = m_rows[m_pos]
        v_idx = v_rows[v_pos]
        d_val = float(dist_km[best_local])
        t_val = float(t_diff[best_local])
        status = "Matched" if (d_val <= 1.5 and t_val <= 180.0) else "Possible Match"
        mid = f"PAIR-{m_date[m_pos]}-{pair_counter:04d}"
        pair_counter += 1

        status_col[m_idx] = status
        match_id_col[m_idx] = mid
        dist_col[m_idx] = round(d_val, 3)
        tdiff_col[m_idx] = round(t_val, 1)

        if match_id_col[v_idx] is None:
            status_col[v_idx] = status
            match_id_col[v_idx] = mid
            dist_col[v_idx] = round(d_val, 3)
            tdiff_col[v_idx] = round(t_val, 1)

        pairs.append({
            "match_id": mid,
            "match_status": status,
            "utc_date": m_date[m_pos],
            "h3_index": m_h3[m_pos],
            "latitude": float(m_lat_deg),
            "longitude": float(m_lon_deg_arr[m_pos]),
            "modis_source_id": source_ids[m_idx],
            "viirs_source_id": source_ids[v_idx],
            "modis_frp": float(m_frp[m_pos]),
            "viirs_frp": float(v_frp[v_pos]),
            "distance_km": round(d_val, 3),
            "time_diff_min": round(t_val, 1),
        })

    df["match_status"] = status_col
    df["match_id"] = match_id_col
    df["nearest_dist_km"] = dist_col
    df["time_diff_min"] = tdiff_col

    pairs_df = pd.DataFrame(pairs)
    if not pairs_df.empty:
        pairs_df = pairs_df.sort_values(["distance_km", "viirs_frp"], ascending=[True, False]).reset_index(drop=True)
    return df, pairs_df


def _df_to_geojson(df: pd.DataFrame, limit: int = 4500) -> dict:
    """Map points only. `limit` thins what is DRAWN; stats never come from here.
    `total_available` tells the UI how many points exist so it can say
    "Showing 4,500 of 52,840 detections"."""
    if df.empty:
        return {"type": "FeatureCollection", "count": 0, "total_available": 0, "truncated": False,
                "category_counts": {}, "features": []}
    total_available = int(len(df))
    # Per-category totals for the map legend, taken before any thinning.
    category_counts = {str(k): int(v) for k, v in df["match_status"].value_counts().items()}

    # Thin the map points only. Cross-sensor pairs are over-represented (up to half
    # the budget) so they stay visible, and the rest is a random spatial sample of
    # single-sensor fires. On a full global day there are more paired points than
    # the whole budget, so "pairs first" alone would hide every VIIRS-only fire.
    if len(df) > limit:
        is_paired = df["match_status"].isin(["Matched", "Possible Match"])
        paired, unpaired = df[is_paired], df[~is_paired]
        paired_n = min(len(paired), limit // 2)
        unpaired_n = min(len(unpaired), limit - paired_n)
        paired_n = min(len(paired), limit - unpaired_n)  # hand back any unused budget
        df = pd.concat(
            [
                paired.sample(n=paired_n, random_state=42) if paired_n else paired.iloc[0:0],
                unpaired.sample(n=unpaired_n, random_state=42) if unpaired_n else unpaired.iloc[0:0],
            ],
            ignore_index=True,
        )

    features = []
    for _, row in df.iterrows():
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(row["longitude"]), float(row["latitude"])],
            },
            "properties": {
                "source_id": str(row.get("source_id", "")),
                "sensor_family": str(row.get("sensor_family", "")),
                "instrument": str(row.get("instrument", row.get("sensor_family", ""))),
                "spatial_res_m": int(row.get("spatial_res_m", 375 if row.get("sensor_family") == "VIIRS" else 1000)),
                "utc_date": str(row.get("acq_date", ""))[:10],
                "acq_datetime": str(row.get("acq_datetime", "")),
                "frp": float(row.get("frp", 0.0)),
                "confidence_tier": str(row.get("confidence_tier", "nominal")),
                "raw_confidence": str(row.get("raw_confidence", "")),
                "h3_index": str(row.get("h3_index", "")),
                "match_status": str(row.get("match_status", "VIIRS-only")),
                "match_id": None if pd.isna(row.get("match_id")) else str(row.get("match_id")),
                "nearest_dist_km": None if pd.isna(row.get("nearest_dist_km")) else float(row.get("nearest_dist_km")),
                "time_diff_min": None if pd.isna(row.get("time_diff_min")) else float(row.get("time_diff_min")),
            },
        })
    return {
        "type": "FeatureCollection",
        "count": len(features),
        "total_available": total_available,
        "truncated": len(features) < total_available,
        "category_counts": category_counts,
        "features": features,
    }


@router.get("/presets")
def get_presets():
    return {"presets": PRESETS}


@router.get("/meta")
@response_cache.cached
def get_meta():
    try:
        return store.coverage()
    except Exception as exc:
        raise _fail(exc)


@router.get("/summary")
@response_cache.cached
def get_summary(
    bbox: str = Query("-180,-90,180,90"),
    start: str = Query("2003-01-01"),
    end: str = Query("2026-12-31"),
):
    try:
        return store.summary(bbox, start, end)
    except Exception as exc:
        raise _fail(exc)


@router.get("/series")
@response_cache.cached
def get_series(
    bbox: str = Query("-180,-90,180,90"),
    start: str = Query("2003-01-01"),
    end: str = Query("2026-12-31"),
    granularity: str = Query("month"),
):
    try:
        return {"series": store.series(bbox, start, end, granularity)}
    except Exception as exc:
        raise _fail(exc)


@router.get("/calendar")
@response_cache.cached
def get_calendar(
    bbox: str = Query("-180,-90,180,90"),
    year_from: int = Query(2003, ge=2003, le=2026),
    year_to: int = Query(2026, ge=2003, le=2026),
):
    try:
        return {"cells": store.calendar_matrix(bbox, year_from, year_to)}
    except Exception as exc:
        raise _fail(exc)


@router.get("/comparison")
def get_comparison(
    bbox: str = Query("-180,-90,180,90"),
    year: int = Query(2025, ge=2003, le=2026),
):
    try:
        rows = store.year_vs_history(bbox, year)
        return {"year": year, "months": rows}
    except Exception as exc:
        raise _fail(exc)


@router.get("/sensor-era")
def get_sensor_era(bbox: str = Query("-180,-90,180,90")):
    try:
        return {"years": store.yearly_by_sensor(bbox)}
    except Exception as exc:
        raise _fail(exc)


# Keyed on (bbox, date): a different date or region is always a fresh query.
# Holds full days (up to ~100k rows each), so the cache is kept small, and
# smaller still in remote (low-RAM) mode. ARCHIVE_DAY_CACHE overrides it.
@lru_cache(maxsize=int(os.getenv("ARCHIVE_DAY_CACHE", "2" if store.REMOTE else "12")))
def _cached_archive_harmonized(bbox: str, target_date: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    # No row cap: every detection for the day feeds the stats and the pairing.
    # (This used to be limit=25000 with ORDER BY acq_datetime, which silently kept
    # only the first 25,000 detections of the UTC day.)
    df = store.hotspots_df(bbox, target_date, target_date, limit=None, sensor=None)
    return _harmonize_pairs(df)


@router.get("/day-bundle")
@bundle_cache.cached
def get_archive_day_bundle(
    bbox: str = Query("-180,-90,180,90"),
    date: str | None = Query(None, description="YYYY-MM-DD; defaults to latest archive date"),
    sensor: str | None = Query(None),
    match_status: str | None = Query(None),
    limit: int = Query(4500, ge=100, le=12000),
):
    """Returns harmonized GeoJSON, KPI summary, and cross-sensor matched pairs for ANY date & region."""
    try:
        cov = store.coverage()
        target_date = date or cov["date_max"]
        harmonized_df, pairs_df = _cached_archive_harmonized(bbox, target_date)
    except Exception as exc:
        raise _fail(exc)

    filtered_df = harmonized_df
    if sensor:
        filtered_df = filtered_df[filtered_df["sensor_family"].str.upper() == sensor.upper()]
    if match_status:
        filtered_df = filtered_df[filtered_df["match_status"].str.lower() == match_status.lower()]

    breakdown = harmonized_df["match_status"].value_counts().to_dict() if not harmonized_df.empty else {}
    summary_payload = {
        "bbox": bbox,
        "date": target_date,
        "total_observations": int(len(harmonized_df)),
        "modis_count": int((harmonized_df["sensor_family"] == "MODIS").sum()) if not harmonized_df.empty else 0,
        "viirs_count": int((harmonized_df["sensor_family"] == "VIIRS").sum()) if not harmonized_df.empty else 0,
        "paired_clusters": int(len(pairs_df)),
        "match_breakdown": breakdown,
        "mean_frp_mw": round(float(harmonized_df["frp"].mean()), 2) if not harmonized_df.empty else 0.0,
        "max_frp_mw": round(float(harmonized_df["frp"].max()), 2) if not harmonized_df.empty else 0.0,
        "date_range": {"start": cov["date_min"], "end": target_date},
    }

    return {
        "date": target_date,
        "archive_coverage": {"min": cov["date_min"], "max": cov["date_max"]},
        "summary": summary_payload,
        "geojson": _df_to_geojson(filtered_df, limit=limit),
        "matches": pairs_df.head(150).to_dict(orient="records") if not pairs_df.empty else [],
    }


@router.get("/live-bundle")
def get_live_firms_bundle(
    bbox: str = Query("-180,-90,180,90"),
    sensor: str | None = Query(None),
    match_status: str | None = Query(None),
    limit: int = Query(4500, ge=100, le=12000),
):
    """Fetches true real-time 24h NASA FIRMS NRT detections for the requested bbox."""
    firms_bbox = "world" if bbox.strip() == "-180,-90,180,90" else bbox.strip()
    sources = [
        ("MODIS_NRT", "MODIS", 1000),
        ("VIIRS_SNPP_NRT", "VIIRS", 375),
        ("VIIRS_NOAA20_NRT", "VIIRS", 375),
    ]
    frames = []
    for src, fam, res_m in sources:
        try:
            raw = fetch_area_fires(source=src, bbox=firms_bbox, day_range=1, save_raw=False)
            if raw is not None and not raw.empty and "latitude" in raw.columns:
                raw = raw.copy()
                raw["sensor_family"] = fam
                raw["instrument"] = src
                raw["spatial_res_m"] = res_m
                raw["acq_time_str"] = raw["acq_time"].astype(str).str.zfill(4)
                raw["acq_datetime"] = (
                    raw["acq_date"].astype(str)
                    + " "
                    + raw["acq_time_str"].str[:2]
                    + ":"
                    + raw["acq_time_str"].str[2:]
                )
                raw["raw_confidence"] = raw.get("confidence", "n")
                raw["confidence_tier"] = raw["raw_confidence"].astype(str)
                raw["h3_index"] = ""
                frames.append(raw)
        except Exception:
            continue

    if not frames:
        # Graceful fallback to latest archive day if FIRMS NRT is temporarily unreachable
        return get_archive_day_bundle(bbox=bbox, date=None, sensor=sensor, match_status=match_status, limit=limit)

    combined = pd.concat(frames, ignore_index=True)
    harmonized_df, pairs_df = _harmonize_pairs(combined)

    filtered_df = harmonized_df
    if sensor:
        filtered_df = filtered_df[filtered_df["sensor_family"].str.upper() == sensor.upper()]
    if match_status:
        filtered_df = filtered_df[filtered_df["match_status"].str.lower() == match_status.lower()]

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    breakdown = harmonized_df["match_status"].value_counts().to_dict()
    return {
        "mode": "LIVE_NRT",
        "date": today_str,
        "summary": {
            "bbox": bbox,
            "date": today_str,
            "total_observations": int(len(harmonized_df)),
            "modis_count": int((harmonized_df["sensor_family"] == "MODIS").sum()),
            "viirs_count": int((harmonized_df["sensor_family"] == "VIIRS").sum()),
            "paired_clusters": int(len(pairs_df)),
            "match_breakdown": breakdown,
            "mean_frp_mw": round(float(harmonized_df["frp"].mean()), 2) if not harmonized_df.empty else 0.0,
            "max_frp_mw": round(float(harmonized_df["frp"].max()), 2) if not harmonized_df.empty else 0.0,
            "date_range": {"start": today_str, "end": today_str},
        },
        "geojson": _df_to_geojson(filtered_df, limit=limit),
        "matches": pairs_df.head(150).to_dict(orient="records") if not pairs_df.empty else [],
    }


def _query_anomalies(w: float, s: float, e: float, n: float, year: int, limit: int) -> pd.DataFrame:
    return store.query(
        ("scores", "cells"),
        f"""
        SELECT
            s.h3_index,
            s.year,
            s.month,
            c.latitude,
            c.longitude,
            s.total_detections,
            s.modis_count,
            s.viirs_count,
            s.frp_sum_mw,
            s.frp_max_mw,
            -- monthly_scores.parquet stores only the count z-score (count_z)
            CAST(NULL AS DOUBLE) AS frp_zscore,
            s.count_z AS count_zscore,
            s.anomaly_score,
            s.is_anomaly,
            s.severity
        FROM scores s
        JOIN cells c
          ON s.h3_index = c.h3_index
        WHERE s.year = {int(year)}
          AND c.latitude BETWEEN {s} AND {n}
          AND c.longitude BETWEEN {w} AND {e}
        ORDER BY s.anomaly_score DESC
        LIMIT {int(limit)}
        """,
        "df",
    )


@router.get("/anomalies")
@response_cache.cached
def get_archive_anomalies(
    bbox: str = Query("-180,-90,180,90"),
    year: int = Query(2025, ge=2003, le=2026),
    limit: int = Query(80, ge=1, le=300),
):
    """Returns calibrated 20-year Isolation Forest H3 anomalies for the chosen region & year."""
    try:
        w, s, e, n = store.parse_bbox(bbox)
        rows = _query_anomalies(w, s, e, n, year, limit)
    except Exception as exc:
        raise _fail(exc)

    items = []
    for _, r in rows.iterrows():
        drivers = []
        if abs(float(r.get("frp_zscore", 0) or 0)) >= 2.0:
            drivers.append(f"FRP {float(r['frp_zscore']):+.1f}σ vs 20-yr cell norm")
        if abs(float(r.get("count_zscore", 0) or 0)) >= 2.0:
            drivers.append(f"Detections {float(r['count_zscore']):+.1f}σ surge")
        if int(r.get("viirs_count", 0)) > 0 and int(r.get("modis_count", 0)) == 0:
            drivers.append("VIIRS sub-pixel cluster")
        if not drivers:
            drivers.append(f"Peak FRP {float(r.get('frp_max_mw', 0)):.1f} MW")

        items.append({
            "h3_index": r["h3_index"],
            "utc_date": f"{int(r['year'])}-{int(r['month']):02d}",
            "latitude": round(float(r["latitude"]), 3),
            "longitude": round(float(r["longitude"]), 3),
            "modis_count": int(r["modis_count"]),
            "viirs_count": int(r["viirs_count"]),
            "total_detections": int(r["total_detections"]),
            "max_frp": round(float(r["frp_max_mw"] or 0), 1),
            "frp_sum_mw": round(float(r["frp_sum_mw"] or 0), 1),
            "anomaly_score": round(float(r["anomaly_score"] or 0), 3),
            "is_anomaly": bool(r["is_anomaly"]),
            "severity": str(r["severity"]),
            "baseline_label": str(r["severity"]).capitalize() + " Anomaly" if r["is_anomaly"] else "Within 20-Yr Baseline",
            "drivers": drivers,
        })

    return {"source": "isolation_forest_archive_v1 (2003-2026)", "year": year, "bbox": bbox, "items": items}


@router.get("/hotspots")
def get_archive_hotspots(
    bbox: str = Query("-180,-90,180,90"),
    start: str = Query("2026-01-01"),
    end: str = Query("2026-12-31"),
    sensor: str | None = Query(None),
    limit: int = Query(200, ge=1, le=2000),
):
    """Returns structured JSON records for the Data Explorer table."""
    try:
        df = store.hotspots_df(bbox, start, end, limit=limit, sensor=sensor or None)
    except Exception as exc:
        raise _fail(exc)

    records = []
    for idx, r in df.iterrows():
        records.append({
            "id": f"{r['sensor_family'][:3]}-{str(r['acq_date'])[:10]}-{idx}",
            "sensor_family": str(r["sensor_family"]),
            "instrument": str(r["instrument"]),
            "acq_datetime": str(r["acq_datetime"]),
            "latitude": round(float(r["latitude"]), 4),
            "longitude": round(float(r["longitude"]), 4),
            "frp": round(float(r["frp"]), 2),
            "confidence_tier": str(r["confidence_tier"]),
            "daynight": str(r["daynight"]),
            "spatial_res_m": int(r["spatial_res_m"]),
            "h3_index": str(r["h3_index"]),
        })
    return {"count": len(records), "records": records}


@router.get("/hotspots.csv")
def download_hotspots_csv(
    bbox: str = Query("-180,-90,180,90"),
    start: str = Query("2003-01-01"),
    end: str = Query("2026-12-31"),
    limit: int = Query(200_000, ge=1, le=1_000_000),
    sensor: str | None = Query(None),
):
    try:
        df = store.hotspots_df(bbox, start, end, limit, sensor)
    except Exception as exc:
        raise _fail(exc)

    truncated = len(df) >= limit
    csv_text = df.to_csv(index=False)
    headers = {
        "Content-Disposition": f'attachment; filename="firms_hotspots_{start}_{end}.csv"',
        "X-Row-Count": str(len(df)),
        "X-Truncated": "true" if truncated else "false",
    }
    return Response(content=csv_text, media_type="text/csv", headers=headers)
