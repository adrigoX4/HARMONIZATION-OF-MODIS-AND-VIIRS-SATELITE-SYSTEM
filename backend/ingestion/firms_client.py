import os
from pathlib import Path
from datetime import datetime, timezone
import requests
import pandas as pd
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

FIRMS_MAP_KEY = os.getenv("FIRMS_MAP_KEY")
BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api"
RAW_DATA_DIR = Path("data/raw")


def check_key() -> str:
    if not FIRMS_MAP_KEY or FIRMS_MAP_KEY == "your_nasa_firms_map_key_here":
        raise ValueError(
            "FIRMS_MAP_KEY is missing or still set to placeholder in .env!"
        )
    return FIRMS_MAP_KEY


def fetch_data_availability(sensor: str = "ALL") -> pd.DataFrame:
    """
    Fetches official date availability (min_date, max_date) for SP and NRT products.
    """
    key = check_key()
    url = f"{BASE_URL}/data_availability/csv/{key}/{sensor}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    from io import StringIO
    return pd.read_csv(StringIO(response.text))


def fetch_area_fires(
    source: str,
    bbox: str,
    day_range: int = 2,
    date: str | None = None,
    save_raw: bool = True,
) -> pd.DataFrame:
    """
    Fetches active-fire CSV hotspots from NASA FIRMS Area API.
    - source: e.g. 'MODIS_NRT', 'VIIRS_SNPP_NRT', 'VIIRS_NOAA20_NRT', 'VIIRS_NOAA21_NRT'
    - bbox: 'west,south,east,north' (e.g. '75,25,85,32' for Northern India) or 'world'
    - day_range: 1 to 5 days
    - date: optional 'YYYY-MM-DD'
    """
    key = check_key()
    if not (1 <= day_range <= 5):
        raise ValueError("day_range must be between 1 and 5.")

    if date:
        url = f"{BASE_URL}/area/csv/{key}/{source}/{bbox}/{day_range}/{date}"
    else:
        url = f"{BASE_URL}/area/csv/{key}/{source}/{bbox}/{day_range}"

    response = requests.get(url, timeout=60)
    response.raise_for_status()

    # Handle invalid key or plain-text API messages
    if response.text.strip().startswith("Invalid"):
        raise RuntimeError(f"NASA FIRMS API Error: {response.text.strip()}")

    if save_raw:
        RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_bbox = bbox.replace(",", "_").replace("-", "m")
        filename = RAW_DATA_DIR / f"{source}_{safe_bbox}_{day_range}d_{timestamp}.csv"
        filename.write_text(response.text, encoding="utf-8")
        print(f"Saved raw CSV -> {filename}")

    from io import StringIO
    return pd.read_csv(StringIO(response.text))