"""Domain-specific inventory manager classes."""
from pathlib import Path
from core.base_manager import BaseAcousticManager

SCHEMA = [
    "id",
    "common_name",
    "scientific_name",
    "primary_habitat",
    "mean_centroid_hz",
    "rms_energy_mean",
    "zero_crossing_rate_mean",
    "min_frequency_hz",
    "max_frequency_hz",
    "avg_duration_sec",
    "conservation_status",
    "recorded_location",
]
DATA_DIR = Path(__file__).resolve().parents[1] / "data"

class AvianManager(BaseAcousticManager):
    def __init__(self): super().__init__(DATA_DIR / "avian_bioacoustics.csv", SCHEMA)

class MammalianManager(BaseAcousticManager):
    def __init__(self): super().__init__(DATA_DIR / "mammalian_bioacoustics.csv", SCHEMA)

class MarineAmphibianManager(BaseAcousticManager):
    def __init__(self): super().__init__(DATA_DIR / "marine_amphibian_bioacoustics.csv", SCHEMA)
