# FireWatch API: Hugging Face Docker Space (port 7860).
# The Parquet archive is NOT baked into the image; on startup the API downloads
# it from the Hugging Face Dataset named by HF_ARCHIVE_DATASET
# (default adrigoX4/modis-viirs-fire-archive) into /app/data/processed/archive.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/tmp/hf_cache

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY backend/ ./backend/
COPY models/ ./models/

# Spaces run the container as a non-root user, so data + cache dirs must be writable.
RUN mkdir -p /app/data/processed/archive /tmp/hf_cache \
    && chmod -R 777 /app/data /tmp/hf_cache

EXPOSE 7860

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
