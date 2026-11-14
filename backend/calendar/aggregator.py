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

    calendar_days = []

    for day in all_dates:
        if day in missing_set:
            calendar_days.append({
                "date": day,
                "data_state": "missing_data",
                "active_fire": None,
                "burned_area": {
                    "estimated_sq_km": round(float(ba_lookup.get(day, 0.0)), 2),
                    "source_product": "MCD64A1 / BA_MODIS (Monthly Derived)",
                    "is_live_daily": False,
                },
                "note": "Satellite observation unavailable for this date; not zero fire activity.",
            })
            continue

        day_rows = harmonized_df[harmonized_df["utc_date"] == day] if not harmonized_df.empty else pd.DataFrame()

        if day_rows.empty:
            calendar_days.append({
                "date": day,
                "data_state": "confirmed_zero",
                "active_fire": {
                    "modis_detections": 0,
                    "viirs_detections": 0,
                    "matched_groups": 0,
                    "mean_frp_mw": 0.0,
                    "max_frp_mw": 0.0,
                },
                "burned_area": {
                    "estimated_sq_km": round(float(ba_lookup.get(day, 0.0)), 2),
                    "source_product": "MCD64A1 / BA_MODIS (Monthly Derived)",
                    "is_live_daily": False,
                },
                "note": "Valid satellite passes recorded with zero thermal anomalies detected.",
            })
            continue

        modis_cnt = int((day_rows["sensor_family"] == "MODIS").sum())
        viirs_cnt = int((day_rows["sensor_family"] == "VIIRS").sum())
        matched_cnt = int(day_rows["match_id"].dropna().nunique())

        calendar_days.append({
            "date": day,
            "data_state": "active_fire",
            "active_fire": {
                "modis_detections": modis_cnt,
                "viirs_detections": viirs_cnt,
                "matched_groups": matched_cnt,
                "mean_frp_mw": round(float(day_rows["frp"].mean()), 2),
                "max_frp_mw": round(float(day_rows["frp"].max()), 2),
            },
            "burned_area": {
                "estimated_sq_km": round(float(ba_lookup.get(day, 0.0)), 2),
                "source_product": "MCD64A1 / BA_MODIS (Monthly Derived)",
                "is_live_daily": False,
            },
            "note": "Active-fire counts represent satellite hotspot detections, not unique wildfire incidents.",
        })

    return calendar_days