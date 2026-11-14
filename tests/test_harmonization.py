from pathlib import Path
import pandas as pd
from backend.processing.normalize import normalize_firms_df
from backend.harmonization.matcher import harmonize_modis_viirs


def main():
    raw_dir = Path("data/raw")
    modis_files = sorted(raw_dir.glob("MODIS_NRT_*.csv"))
    viirs_files = sorted(raw_dir.glob("VIIRS_NOAA20_NRT_*.csv"))

    if not modis_files or not viirs_files:
        raise FileNotFoundError("Raw MODIS or VIIRS CSV not found in data/raw/. Run test_firms_api first.")

    print(f"Loading MODIS file: {modis_files[-1].name}")
    print(f"Loading VIIRS file: {viirs_files[-1].name}")

    raw_modis = pd.read_csv(modis_files[-1])
    raw_viirs = pd.read_csv(viirs_files[-1])

    norm_modis = normalize_firms_df(raw_modis, source_id="MODIS_NRT")
    norm_viirs = normalize_firms_df(raw_viirs, source_id="VIIRS_NOAA20_NRT")

    combined_df, pairs_df = harmonize_modis_viirs(norm_modis, norm_viirs)

    print("\n--- HARMONIZATION SUMMARY ---")
    print(combined_df.groupby(["sensor_family", "match_status"]).size())

    print(f"\nTotal Paired Fire Clusters Found: {len(pairs_df)}")
    if not pairs_df.empty:
        print("\nSample Matched Pairs (MODIS 1km vs VIIRS 375m):")
        print(
            pairs_df[
                ["match_id", "match_status", "distance_km", "time_diff_min", "modis_frp", "viirs_frp", "viirs_pixels_in_footprint"]
            ].head(5).to_string(index=False)
        )

    # Save processed sample to data/processed/
    Path("data/processed").mkdir(parents=True, exist_ok=True)
    combined_df.to_csv("data/processed/harmonized_sample.csv", index=False)
    pairs_df.to_csv("data/processed/matched_pairs_sample.csv", index=False)
    print("\nSaved harmonized outputs to data/processed/!")


if __name__ == "__main__":
    main()