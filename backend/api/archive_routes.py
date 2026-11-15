"""Archive-backed endpoints: region + date-range queries over 2003-2026 FIRMS data."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Response

from backend.archive import store

router = APIRouter(prefix="/api/v1/archive", tags=["archive"])

PRESETS = [
    {"id": "world", "label": "Global", "bbox": "-180,-90,180,90"},
    {"id": "africa", "label": "Africa", "bbox": "-20,-35,52,38"},
    {"id": "asia", "label": "Asia", "bbox": "25,-11,180,78"},
    {"id": "europe", "label": "Europe", "bbox": "-25,34,45,72"},
    {"id": "north_america", "label": "North America", "bbox": "-170,7,-50,75"},
    {"id": "south_america", "label": "South America", "bbox": "-82,-56,-34,13"},
    {"id": "oceania", "label": "Oceania", "bbox": "110,-48,180,0"},
    {"id": "india", "label": "India", "bbox": "68,6,98,37"},
    {"id": "amazon", "label": "Amazon Basin", "bbox": "-75,-20,-45,5"},
    {"id": "australia", "label": "Australia", "bbox": "112,-45,155,-9"},
    {"id": "california", "label": "California", "bbox": "-125,32,-114,43"},
    {"id": "indonesia", "label": "Indonesia", "bbox": "95,-11,141,6"},
]


def _fail(exc: Exception) -> HTTPException:
    if isinstance(exc, store.ArchiveNotReady):
        return HTTPException(status_code=503, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


@router.get("/presets")
def get_presets():
    return {"presets": PRESETS}


@router.get("/meta")
def get_meta():
    try:
        return store.coverage()
    except Exception as exc:
        raise _fail(exc)


@router.get("/summary")
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
