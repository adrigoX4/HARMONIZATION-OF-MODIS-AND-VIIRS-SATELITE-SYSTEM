import pandas as pd


def build_burning_calendar(
    harmonized_df: pd.DataFrame,
    start_date: str,
    end_date: str,
    missing_dates: list[str] | None = None,
    burned_area_daily: pd.DataFrame | None = None,
) -> list[dict]:
    """
    Generates daily Burning Calendar records between start_date and end_date.
    Strictly separates active-fire detections from monthly burned-area estimates
    and distinguishes confirmed zero activity from missing satellite data.

    Each record exposes flat keys (date, total_count, modis_count, viirs_count,
    matched_count, total_frp_mw, active_h3_cells) consumed by the frontend
    Burning Calendar grid, Day Detail drawer, and Recharts components.
    """
    missing_set = set(missing_dates or [])
    all_dates = pd.date_range(start=start_date, end=end_date, freq="D").strftime("%Y-%m-%d")

    ba_lookup = {}
    if burned_area_daily is not None and not burned_area_daily.empty:
        ba_lookup = (
            burned_area_daily.groupby("utc_date")["burned_area_sq_km"]
            .sum()
            .to_dict()
        )

    df = harmonized_df.copy()
    if not df.empty:
        df["utc_date"] = pd.to_datetime(df["utc_date"]).dt.strftime("%Y-%m-%d")

    calendar_days = []

    for day in all_dates:
        burned_area = {
            "estimated_sq_km": round(float(ba_lookup.get(day, 0.0)), 2),
            "source_product": "MCD64A1 / BA_MODIS (Monthly Derived)",
            "is_live_daily": False,
        }

        if day in missing_set:
            calendar_days.append({
                "date": day,
                "utc_date": day,
                "data_state": "missing_data",
                "total_count": 0,
                "total_detections": 0,
                "modis_count": 0,
                "viirs_count": 0,
                "matched_count": 0,
                "total_frp_mw": 0.0,
                "active_h3_cells": 0,
                "active_fire": None,
                "burned_area": burned_area,
                "note": "Satellite observation unavailable for this date; not zero fire activity.",
            })
            continue

        day_rows = df[df["utc_date"] == day] if not df.empty else pd.DataFrame()

        if day_rows.empty:
            calendar_days.append({
                "date": day,
                "utc_date": day,
                "data_state": "confirmed_zero",
                "total_count": 0,
                "total_detections": 0,
                "modis_count": 0,
                "viirs_count": 0,
                "matched_count": 0,
                "total_frp_mw": 0.0,
                "active_h3_cells": 0,
                "active_fire": {
                    "modis_detections": 0,
                    "viirs_detections": 0,
                    "matched_groups": 0,
                    "mean_frp_mw": 0.0,
                    "max_frp_mw": 0.0,
                },
                "burned_area": burned_area,
                "note": "Valid satellite passes recorded with zero thermal anomalies detected.",
            })
            continue

        modis_cnt = int((day_rows["sensor_family"] == "MODIS").sum())
        viirs_cnt = int((day_rows["sensor_family"] == "VIIRS").sum())
        matched_cnt = int(day_rows["match_id"].dropna().nunique())
        total_frp_mw = round(float(day_rows["frp"].sum()), 2)
        active_h3_cells = int(day_rows["h3_index"].nunique())

        calendar_days.append({
            "date": day,
            "utc_date": day,
            "data_state": "active_fire",
            "total_count": int(len(day_rows)),
            "total_detections": int(len(day_rows)),
            "modis_count": modis_cnt,
            "viirs_count": viirs_cnt,
            "matched_count": matched_cnt,
            "total_frp_mw": total_frp_mw,
            "active_h3_cells": active_h3_cells,
            "active_fire": {
                "modis_detections": modis_cnt,
                "viirs_detections": viirs_cnt,
                "matched_groups": matched_cnt,
                "mean_frp_mw": round(float(day_rows["frp"].mean()), 2),
                "max_frp_mw": round(float(day_rows["frp"].max()), 2),
            },
            "burned_area": burned_area,
            "note": "Active-fire counts represent satellite hotspot detections, not unique wildfire incidents.",
        })

    return calendar_days
