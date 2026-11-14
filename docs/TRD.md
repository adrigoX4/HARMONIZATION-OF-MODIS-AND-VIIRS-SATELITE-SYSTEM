# Technical Requirements Document (TRD)
**Project:** MODIS–VIIRS Satellite Fire Harmonization & Anomaly Intelligence Platform  
**Version:** 1.0 (Verified against NASA FIRMS API v4.2.8)

---

## 1. System Architecture Overview
`NASA FIRMS API (CSV)` $\rightarrow$ `Python Ingestion (backend/ingestion)` $\rightarrow$ `Normalization & Deduplication (backend/processing)` $\rightarrow$ `MODIS-VIIRS Spatio-Temporal Matcher (backend/harmonization)` $\rightarrow$ `PostgreSQL + PostGIS (backend/database)` $\rightarrow$ `Isolation Forest Inference (backend/ml)` $\rightarrow$ `FastAPI REST/GeoJSON (backend/api)` $\rightarrow$ `React + Vite + Leaflet + NASA GIBS (frontend)`

---

## 2. Verified NASA Data Contracts
Based on live `data_availability` queries:
* **MODIS Active Fire (1 km):** `MODIS_SP` (`2000-11-01` to `max_sp_date`), `MODIS_NRT` (post-SP to present).
* **VIIRS Active Fire (375 m I-band):**
  * `VIIRS_NOAA20_SP` (`2018-04-01` to `max_sp_date`) + `VIIRS_NOAA20_NRT`
  * `VIIRS_NOAA21_SP` (`2023-03-01` to `max_sp_date`) + `VIIRS_NOAA21_NRT`
  * `VIIRS_SNPP_SP` (`2012-01-20` to `2026-07-31`) + `VIIRS_SNPP_NRT` (through `2026-11-02`)
* **Burned Area:** `BA_MODIS` (`2000-11-01` to `2026-08-01`) and `BA_VIIRS` (`2012-03-01` to `2026-08-01`).
* **Imagery Visualization:** NASA GIBS WMTS tiles (EPSG:3857 / EPSG:4326) rendered via Leaflet.

---

## 3. Data Normalization Rules (`backend/processing/normalize.py`)
1. **Timestamp Standardization:** Zero-pad `acq_time` to 4 digits (`705` $\rightarrow$ `'0705'`), combine with `acq_date`, and parse as timezone-aware UTC `acq_datetime`.
2. **Spatial Indexing:** Preserve raw `latitude` and `longitude` (WGS84 `EPSG:4326`) and compute **H3 Resolution 5** (`h3_index`, ~252 $\text{km}^2$ cell area) for global aggregation and ML grid-day grouping.
3. **Confidence Harmonization:** Preserve `raw_confidence` and compute `confidence_tier`:
   * **MODIS (0–100):** `< 30` $\rightarrow$ `low`, `30–79` $\rightarrow$ `nominal`, `>= 80` $\rightarrow$ `high`.
   * **VIIRS (`l`, `n`, `h`):** `l` $\rightarrow$ `low`, `n` $\rightarrow$ `nominal`, `h` $\rightarrow$ `high`.
4. **Source Hierarchy (`SP` > `NRT`):** Query `data_availability` before ingestion; never ingest `NRT` rows for dates covered by `SP`.

---

## 4. MODIS–VIIRS Harmonization Logic (`backend/harmonization/matcher.py`)
* **Candidate Pairing:** Compare MODIS (~1 km pixel) and VIIRS (375 m pixel) observations on the same UTC date (or $\pm 12$ hours across midnight).
* **Spatial & Temporal Thresholds:**
  * **Matched:** Spatial distance $\le 1.5\text{ km}$ AND time difference $\le 4\text{ hours}$.
  * **Possible Match:** Spatial distance $\le 3.0\text{ km}$ AND time difference $\le 12\text{ hours}$.
  * **MODIS-only / VIIRS-only:** No counterpart within thresholds.
* **Scientific Metadata Preserved:** Store `distance_km`, `time_diff_minutes`, `frp_ratio`, and sensor resolution tags (`1000m` vs `375m`).

---

## 5. Isolation Forest ML Contract (`backend/ml/`)
* **Granularity:** One row = `(h3_index, utc_date)` trained strictly on cleaned `SP` historical data.
* **Required Input Features (`model_schema_v1.json`):**
  1. `modis_count` (int)
  2. `viirs_count` (int)
  3. `matched_group_count` (int)
  4. `viirs_to_modis_ratio` (float)
  5. `mean_frp` (float)
  6. `max_frp` (float)
  7. `frp_std` (float)
  8. `high_conf_ratio` (float)
  9. `burned_area_sq_km` (float)
  10. `day_of_year_sin` (float)
  11. `day_of_year_cos` (float)
  12. `historical_frp_zscore` (float)
* **Artifact Format:** `models/isolation_forest_v1.joblib` containing `{"model": IsolationForest, "features": list[str], "version": "1.0", "contamination": 0.015}`.

---

## 6. Backend REST API Endpoints (`FastAPI /api/v1`)
* `GET /api/v1/dashboard` — Global counts, latest sensor availability, anomaly summary.
* `GET /api/v1/fires/geojson?bbox=...&date=...&sensor=...` — GeoJSON `FeatureCollection` for Leaflet map.
* `GET /api/v1/harmonization/matches?date=...` — Matched vs. sensor-only breakdown & FRP comparison.
* `GET /api/v1/calendar?year=2026&month=11&h3=...` — Daily active-fire metrics, burned-area estimates, and missing-data flags.
* `GET /api/v1/calendar/{date}` — Full daily report (MODIS, VIIRS, matches, burned area, anomaly drivers).
* `GET /api/v1/anomalies?date=...` — Isolation Forest outlier cells (`is_anomaly == -1`), scores, and explanations.
* `GET /api/v1/datasets` — Live `data_availability` and `missing_data` audit log.