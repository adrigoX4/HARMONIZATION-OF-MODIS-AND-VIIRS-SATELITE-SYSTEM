from backend.ingestion.firms_client import fetch_data_availability, fetch_area_fires


def main():
    print("1. Checking NASA FIRMS Data Availability...")
    avail_df = fetch_data_availability("ALL")
    print(avail_df.to_string(index=False))
    print("-" * 60)

    # Small bounding box test (Northern India: west=75, south=25, east=85, north=32)
    test_bbox = "75,25,85,32"

    print("\n2. Fetching 2-day MODIS_NRT sample...")
    modis_df = fetch_area_fires(source="MODIS_NRT", bbox=test_bbox, day_range=2)
    print(f"MODIS rows fetched: {len(modis_df)}")
    if not modis_df.empty:
        print(modis_df[["latitude", "longitude", "acq_date", "acq_time", "frp", "confidence"]].head(3))

    print("\n3. Fetching 2-day VIIRS_NOAA20_NRT sample...")
    viirs_df = fetch_area_fires(source="VIIRS_NOAA20_NRT", bbox=test_bbox, day_range=2)
    print(f"VIIRS NOAA-20 rows fetched: {len(viirs_df)}")
    if not viirs_df.empty:
        print(viirs_df[["latitude", "longitude", "acq_date", "acq_time", "frp", "confidence"]].head(3))


if __name__ == "__main__":
    main()