# FireWatch API: small Docker host (Render free tier, 512 MB RAM) or HF Space.
# The Parquet archive is NOT baked into the image and NOT downloaded: with no
# local data/processed/archive, DuckDB reads it over hf:// from the Hugging Face
# Dataset named by HF_ARCHIVE_DATASET (default asrath0skye/modis-viirs-fire-archive).
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/tmp/hf_cache \
    DUCKDB_TEMP_DIR=/tmp/duckdb_temp

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt
# Pre-install DuckDB's httpfs extension so startup doesn't have to fetch it.
RUN python -c "import duckdb; duckdb.connect().execute('INSTALL httpfs')"

COPY backend/ ./backend/
COPY models/ ./models/

# Writable scratch dirs (some hosts run the container as a non-root user).
# data/processed/archive is deliberately NOT created: its absence is what
# switches the API to reading the archive remotely over hf://.
RUN mkdir -p /tmp/duckdb_temp /tmp/hf_cache \
    && chmod -R 777 /tmp/duckdb_temp /tmp/hf_cache

EXPOSE 7860

CMD sh -c "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-7860}"
