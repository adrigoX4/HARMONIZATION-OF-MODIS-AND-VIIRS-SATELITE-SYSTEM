import numpy as np
import pandas as pd


def _haversine_km(lat1: float, lon1: float, lat2_arr: np.ndarray, lon2_arr: np.ndarray) -> np.ndarray:
    """
    Computes great-circle distance in kilometers between one point and an array of points.
    """
    r = 6371.0  # Earth radius in km
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2_arr)
    dphi = np.radians(lat2_arr - lat1)
    dlambda = np.radians(lon2_arr - lon1)

    a = np.sin(dphi / 2.0) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2.0) ** 2
    return 2.0 * r * np.arcsin(np.sqrt(a))


def _to_epoch_seconds(dt_series: pd.Series) -> np.ndarray:
    """
    Converts timezone-aware UTC pandas timestamps into plain float64 Unix epoch seconds.
    """
    return pd.to_datetime(dt_series, utc=True).astype("int64").to_numpy() / 1e9


def harmonize_modis_viirs(
    modis_df: pd.DataFrame,
    viirs_df: pd.DataFrame,
    match_dist_km: float = 1.5,
    possible_dist_km: float = 3.0,
    match_hours: float = 4.0,
    possible_hours: float = 12.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Associates normalized MODIS (1km) and VIIRS (375m) fire detections across space and time.
    Returns:
      1. combined_observations: All MODIS & VIIRS rows labeled with match_status and metrics
      2. match_pairs: Table of paired MODIS-VIIRS observations for side-by-side comparison
    """
    modis = modis_df.copy()
    viirs = viirs_df.copy()

    modis["match_status"] = "MODIS-only"
    modis["match_id"] = None
    modis["nearest_dist_km"] = np.nan
    modis["time_diff_min"] = np.nan

    viirs["match_status"] = "VIIRS-only"
    viirs["match_id"] = None
    viirs["nearest_dist_km"] = np.nan
    viirs["time_diff_min"] = np.nan

    if modis.empty or viirs.empty:
        combined = pd.concat([modis, viirs], ignore_index=True)
        return combined, pd.DataFrame()

    v_lats = viirs["latitude"].to_numpy()
    v_lons = viirs["longitude"].to_numpy()
    v_secs = _to_epoch_seconds(viirs["acq_datetime"])
    m_secs = _to_epoch_seconds(modis["acq_datetime"])

    match_records = []
    match_counter = 1

    for pos, (m_idx, m_row) in enumerate(modis.iterrows()):
        # 1. Compute spatial distances to all VIIRS points
        dists_km = _haversine_km(m_row["latitude"], m_row["longitude"], v_lats, v_lons)

        # Quick bounding filter for candidate VIIRS points within possible_dist_km
        candidate_indices = np.where(dists_km <= possible_dist_km)[0]
        if len(candidate_indices) == 0:
            continue

        # 2. Compute time differences in minutes and hours using plain epoch seconds
        time_diffs_min = np.abs(v_secs[candidate_indices] - m_secs[pos]) / 60.0
        time_diffs_hr = time_diffs_min / 60.0

        valid_mask = time_diffs_hr <= possible_hours
        if not np.any(valid_mask):
            continue

        valid_cands = candidate_indices[valid_mask]
        valid_dists = dists_km[valid_cands]
        valid_mins = time_diffs_min[valid_mask]

        # Pick closest spatial counterpart among temporally valid candidates
        best_local = int(np.argmin(valid_dists))
        best_v_idx = int(valid_cands[best_local])
        best_dist = float(valid_dists[best_local])
        best_min = float(valid_mins[best_local])

        if best_dist <= match_dist_km and (best_min / 60.0) <= match_hours:
            status = "Matched"
        else:
            status = "Possible Match"

        pair_id = f"PAIR_{match_counter:05d}"
        match_counter += 1

        # Update MODIS row
        modis.at[m_idx, "match_status"] = status
        modis.at[m_idx, "match_id"] = pair_id
        modis.at[m_idx, "nearest_dist_km"] = round(best_dist, 3)
        modis.at[m_idx, "time_diff_min"] = round(best_min, 1)

        # Update all VIIRS pixels falling inside this MODIS 1km footprint window
        for c_idx, c_dist, c_min in zip(valid_cands, valid_dists, valid_mins):
            v_status = "Matched" if (c_dist <= match_dist_km and (c_min / 60.0) <= match_hours) else "Possible Match"
            if viirs.at[c_idx, "match_status"] != "Matched":
                viirs.at[c_idx, "match_status"] = v_status
                viirs.at[c_idx, "match_id"] = pair_id
                viirs.at[c_idx, "nearest_dist_km"] = round(float(c_dist), 3)
                viirs.at[c_idx, "time_diff_min"] = round(float(c_min), 1)

        v_best = viirs.loc[best_v_idx]
        match_records.append({
            "match_id": pair_id,
            "match_status": status,
            "h3_index": m_row["h3_index"],
            "utc_date": m_row["utc_date"],
            "modis_lat": m_row["latitude"],
            "modis_lon": m_row["longitude"],
            "viirs_lat": v_best["latitude"],
            "viirs_lon": v_best["longitude"],
            "distance_km": round(best_dist, 3),
            "time_diff_min": round(best_min, 1),
            "modis_frp": m_row["frp"],
            "viirs_frp": v_best["frp"],
            "viirs_pixels_in_footprint": int(len(valid_cands)),
        })

    combined = pd.concat([modis, viirs], ignore_index=True)
    pairs_df = pd.DataFrame(match_records)
    return combined, pairs_df