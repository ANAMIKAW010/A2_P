import librosa
import numpy as np
import pandas as pd
from pathlib import Path
from core.feature_extractor import extract_audio_features

# Map subfolders to their specific output CSV files
PROCESS_MAP = {
    "avian": Path("data/avian_bioacoustics.csv"),
    "mammalian": Path("data/mammalian_bioacoustics.csv"),
    "marine": Path("data/marine_amphibian_bioacoustics.csv")
}

AUDIO_ROOT = Path("raw_audio")


def extract_frequency_bounds(audio: np.ndarray, sr: int) -> tuple[float, float]:
    """Calculate the estimated 5th and 95th percentile frequency boundaries."""
    # Compute roll-off: low cutoff (energy starts) and high cutoff (energy drops off)
    rolloff_low = librosa.feature.spectral_rolloff(y=audio, sr=sr, roll_percent=0.05)[0]
    rolloff_high = librosa.feature.spectral_rolloff(y=audio, sr=sr, roll_percent=0.95)[0]

    min_freq = float(np.mean(rolloff_low))
    max_freq = float(np.mean(rolloff_high))

    # Fallback sanity checks to respect schema bounds
    min_freq = max(50.0, min_freq)
    max_freq = max(min_freq + 100.0, max_freq)

    return round(min_freq, 2), round(max_freq, 2)


def run_batch():
    if not AUDIO_ROOT.exists():
        print(f"Root folder '{AUDIO_ROOT}' not found. Please create it.")
        return

    for category, output_csv in PROCESS_MAP.items():
        category_dir = AUDIO_ROOT / category

        if not category_dir.exists():
            print(f"Skipping {category}: Folder '{category_dir}' does not exist.")
            continue

        records = []
        print(f"\n--- Processing {category.upper()} ---")

        for idx, filepath in enumerate(category_dir.glob("*.*")):
            if filepath.suffix.lower() not in ['.wav', '.mp3', '.flac', '.m4a', '.ogg']:
                continue

            print(f"Extracting: {filepath.name}...")

            try:
                features = extract_audio_features(filepath)
                y, sr = librosa.load(filepath, sr=22050, mono=True)
                min_hz, max_hz = extract_frequency_bounds(y, sr)

                record = {
                    "id": f"{category[:3].upper()}_AUTO_{idx:03d}",
                    "common_name": filepath.stem.replace("_", " ").title(),
                    "scientific_name": "TBD",
                    "primary_habitat": "TBD",
                    "mean_centroid_hz": round(features["spectral_centroid_mean"], 2),
                    "rms_energy_mean": round(features["rms_energy_mean"], 6),
                    "zero_crossing_rate_mean": round(features["zero_crossing_rate_mean"], 4),
                    "min_frequency_hz": min_hz,
                    "max_frequency_hz": max_hz,
                    "avg_duration_sec": round(features["duration_sec"], 2),
                    "conservation_status": "Least Concern",
                    "recorded_location": "Field Sample"
                }
                records.append(record)
            except Exception as e:
                print(f"Error on {filepath.name}: {e}")

        # Save directly to the app's data folder
        if records:
            df = pd.DataFrame(records)
            output_csv.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(output_csv, index=False)
            print(f"Saved {len(records)} {category} records to {output_csv.name}")
        else:
            print(f"No valid audio found in {category_dir}.")


if __name__ == "__main__":
    run_batch()