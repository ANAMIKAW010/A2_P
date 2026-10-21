"""Deterministic audio measurements, snapshots, and reference matching."""
from __future__ import annotations

from typing import Any

import librosa
import numpy as np
import pandas as pd


FEATURE_COLUMNS = (
    "spectral_centroid_mean",
    "rms_energy_mean",
    "zero_crossing_rate_mean",
    "duration_sec",
)

REFERENCE_FEATURE_COLUMNS = {
    "spectral_centroid_mean": "mean_centroid_hz",
    "rms_energy_mean": "rms_energy_mean",
    "zero_crossing_rate_mean": "zero_crossing_rate_mean",
    "duration_sec": "avg_duration_sec",
}


def load_audio(file_path_or_buffer: Any) -> tuple[np.ndarray, int]:
    """Decode mono audio at the fixed analysis sample rate."""
    audio, sample_rate = librosa.load(file_path_or_buffer, sr=22050, mono=True)
    if audio.size == 0:
        raise ValueError("The audio file contains no readable samples.")
    return audio.astype(float, copy=False), int(sample_rate)


def extract_features_from_signal(audio: np.ndarray, sample_rate: int) -> dict[str, float]:
    """Compute the four non-ML measurements used by the matching rule."""
    if audio.size == 0:
        raise ValueError("The audio signal contains no readable samples.")
    centroid = librosa.feature.spectral_centroid(y=audio, sr=sample_rate)[0]
    rms = librosa.feature.rms(y=audio)[0]
    zcr = librosa.feature.zero_crossing_rate(y=audio)[0]
    return {
        "spectral_centroid_mean": float(np.mean(centroid)),
        "rms_energy_mean": float(np.mean(rms)),
        "zero_crossing_rate_mean": float(np.mean(zcr)),
        "duration_sec": float(len(audio) / sample_rate),
    }


def extract_audio_features(file_path_or_buffer: Any) -> dict[str, float]:
    """Load an audio input at 22,050 Hz and return its acoustic measurements."""
    audio, sample_rate = load_audio(file_path_or_buffer)
    return extract_features_from_signal(audio, sample_rate)


def build_visual_snapshot(
    audio: np.ndarray,
    sample_rate: int,
    max_waveform_points: int = 600,
    max_frequency_bins: int = 48,
    max_time_bins: int = 72,
) -> dict[str, Any]:
    """Create a compact, JSON-safe waveform and spectrogram for run history."""
    sample_indices = np.linspace(0, len(audio) - 1, min(max_waveform_points, len(audio)), dtype=int)
    stft = np.abs(librosa.stft(audio))
    reference = float(np.max(stft)) if stft.size else 1.0
    spectrogram = librosa.amplitude_to_db(stft, ref=max(reference, 1e-12))
    freq_indices = np.linspace(0, spectrogram.shape[0] - 1, min(max_frequency_bins, spectrogram.shape[0]), dtype=int)
    time_indices = np.linspace(0, spectrogram.shape[1] - 1, min(max_time_bins, spectrogram.shape[1]), dtype=int)
    reduced = spectrogram[np.ix_(freq_indices, time_indices)]
    return {
        "waveform": {
            "time_sec": (sample_indices / sample_rate).astype(float).tolist(),
            "amplitude": audio[sample_indices].astype(float).tolist(),
        },
        "spectrogram": {
            "time_sec": librosa.frames_to_time(time_indices, sr=sample_rate).astype(float).tolist(),
            "frequency_hz": librosa.fft_frequencies(sr=sample_rate)[freq_indices].astype(float).tolist(),
            "db": reduced.astype(float).tolist(),
        },
    }


def match_species_rule_based(
    extracted_features: dict[str, float], reference_df: pd.DataFrame
) -> dict[str, Any]:
    """Find the nearest baseline using MinMax-scaled Euclidean distance.

    The baseline columns come directly from the inventory CSVs. This is a fixed,
    reproducible rule and does not train a model or infer a classifier.
    """
    if reference_df.empty:
        return {"match": None, "confidence": 0.0, "distance": None, "ranked": []}
    missing = [column for column in REFERENCE_FEATURE_COLUMNS.values() if column not in reference_df.columns]
    if missing:
        raise ValueError("Reference data is missing acoustic baseline columns: " + ", ".join(missing))

    target = np.array([extracted_features.get(column, np.nan) for column in FEATURE_COLUMNS], dtype=float)
    if not np.isfinite(target).all():
        raise ValueError("Extracted features must contain finite numeric values.")

    refs = reference_df.copy()
    source_columns = list(REFERENCE_FEATURE_COLUMNS.values())
    numeric_baselines = refs.loc[:, source_columns].apply(pd.to_numeric, errors="coerce")
    valid_rows = numeric_baselines.notna().all(axis=1)
    refs = refs.loc[valid_rows].reset_index(drop=True)
    matrix = numeric_baselines.loc[valid_rows].to_numpy(dtype=float)
    if matrix.size == 0:
        return {"match": None, "confidence": 0.0, "distance": None, "ranked": []}

    minima = matrix.min(axis=0)
    ranges = matrix.max(axis=0) - minima
    zero_range = ranges == 0
    if zero_range.any():
        ranges[zero_range] = np.maximum(np.abs(minima[zero_range]), 1.0)
    normalized_references = (matrix - minima) / ranges
    normalized_target = (target - minima) / ranges
    distances = np.linalg.norm(normalized_references - normalized_target, axis=1)
    order = np.argsort(distances)

    ranked: list[dict[str, Any]] = []
    for index in order:
        row = refs.iloc[int(index)].to_dict()
        distance = float(distances[index])
        row["distance"] = distance
        row["confidence"] = float(100 * np.exp(-distance))
        ranked.append(row)
    best = ranked[0]
    return {
        "match": best,
        "confidence": best["confidence"],
        "distance": best["distance"],
        "ranked": ranked,
    }
