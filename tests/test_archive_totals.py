"""Regression test: archive day totals must not be capped at 25,000.

The /api/v1/archive/day-bundle endpoint used to load at most 25,000 rows
(ORDER BY acq_datetime LIMIT 25000), so every busy day reported exactly 25,000
detections. These checks compare the endpoint's KPIs with an independent
DuckDB COUNT(*) over the same bbox and date.

Run either way (from the repo root, archive Parquet must be built):
    python -m tests.test_archive_totals
    python -m pytest tests/test_archive_totals.py
"""
from __future__ import annotations

from backend.api.archive_routes import get_archive_day_bundle
from backend.archive import store

GLOBAL = "-180,-90,180,90"
# Both days have far more than 25,000 global detections in the archive.
BUSY_DAYS = ["2022-01-15", "2026-10-31"]
OLD_CAP = 25_000


def _check_day(date: str) -> dict:
    truth = store.summary(GLOBAL, date, date)
    bundle = get_archive_day_bundle(bbox=GLOBAL, date=date, sensor=None, match_status=None, limit=4500)
    s = bundle["summary"]

    assert truth["total_detections"] > OLD_CAP, f"{date}: pick a busier test day ({truth['total_detections']})"

    # KPIs come from the full day, matching DuckDB exactly
    assert s["total_observations"] == truth["total_detections"], (date, s["total_observations"], truth)
    assert s["modis_count"] == truth["modis_count"]
    assert s["viirs_count"] == truth["viirs_count"]
    assert s["modis_count"] + s["viirs_count"] == s["total_observations"]
    assert sum(s["match_breakdown"].values()) == s["total_observations"]
    assert abs(s["max_frp_mw"] - truth["max_frp_mw"]) < 0.01
    assert abs(s["mean_frp_mw"] - truth["mean_frp_mw"]) < 0.01

    # The map may be thinned, but it must say how many points exist
    geo = bundle["geojson"]
    assert geo["total_available"] == truth["total_detections"]
    assert len(geo["features"]) <= 4500
    assert geo["truncated"] is (len(geo["features"]) < geo["total_available"])
    return s


def test_busy_days_report_true_totals():
    totals = {d: _check_day(d)["total_observations"] for d in BUSY_DAYS}
    # A changed date must never reuse another date's cached result
    assert len(set(totals.values())) == len(BUSY_DAYS), totals


if __name__ == "__main__":
    for d in BUSY_DAYS:
        s = _check_day(d)
        print(
            f"{d}: total {s['total_observations']:,}  MODIS {s['modis_count']:,}  VIIRS {s['viirs_count']:,}  "
            f"pairs {s['paired_clusters']:,}  peak {s['max_frp_mw']} MW  mean {s['mean_frp_mw']} MW"
        )
    test_busy_days_report_true_totals()
    print("OK: totals match DuckDB and exceed the old 25,000 cap")
