"""Schema-aware CSV persistence and CRUD operations for BioEcho inventories."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

import numpy as np

import pandas as pd


class BaseAcousticManager:
    """Owns a schema-constrained CSV inventory with atomic writes."""

    def __init__(self, filepath: str | Path, schema_columns: list[str]):
        self.filepath = Path(filepath)
        self.schema_columns = list(schema_columns)
        self._data = pd.DataFrame(columns=self.schema_columns)
        self.last_error = ""
        self.load_csv()

    @property
    def data(self) -> pd.DataFrame:
        return self._data.copy(deep=True)

    def load_csv(self) -> bool:
        try:
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            loaded = pd.read_csv(self.filepath, dtype={"id": "string"})
            missing = set(self.schema_columns) - set(loaded.columns)
            if missing:
                raise ValueError(
                    "CSV is missing required columns: " + ", ".join(sorted(missing))
                )
            self._data = loaded.loc[:, self.schema_columns].fillna("")
        except FileNotFoundError:
            self._data = pd.DataFrame(columns=self.schema_columns)
            self.last_error = f"Inventory file not found: {self.filepath.name}"
            return False
        except pd.errors.EmptyDataError:
            self._data = pd.DataFrame(columns=self.schema_columns)
            self.last_error = f"Inventory file is empty: {self.filepath.name}"
            return False
        except (OSError, ValueError, pd.errors.ParserError) as exc:
            self.last_error = str(exc)
            return False
        else:
            self.last_error = ""
            return True
        finally:
            # The state is always left as a DataFrame, even if parsing failed.
            if not isinstance(self._data, pd.DataFrame):
                self._data = pd.DataFrame(columns=self.schema_columns)

    def save_csv(self) -> bool:
        temp_path: str | None = None
        try:
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", newline="", suffix=".tmp",
                prefix=f".{self.filepath.stem}_", dir=self.filepath.parent, delete=False
            ) as temporary:
                temp_path = temporary.name
                self._data.loc[:, self.schema_columns].to_csv(temporary, index=False)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temp_path, self.filepath)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self.last_error = str(exc)
            return False
        else:
            self.last_error = ""
            return True
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

    def _normalise_and_validate(
        self, record: Mapping[str, Any], *, require_id: bool = True
    ) -> tuple[bool, str, dict[str, Any]]:
        """Return a clean record after checking inventory invariants."""
        normalized = {column: record.get(column, "") for column in self.schema_columns}
        normalized["id"] = str(normalized["id"]).strip()
        for field in ("common_name", "scientific_name", "primary_habitat", "conservation_status"):
            normalized[field] = str(normalized[field]).strip()
        if require_id and not normalized["id"]:
            return False, "ID is required.", normalized
        if not normalized["common_name"] or not normalized["scientific_name"]:
            return False, "Common name and scientific name are required.", normalized

        numeric_fields = (
            "mean_centroid_hz",
            "rms_energy_mean",
            "zero_crossing_rate_mean",
            "min_frequency_hz",
            "max_frequency_hz",
            "avg_duration_sec",
        )
        for field in numeric_fields:
            try:
                value = float(normalized[field])
            except (TypeError, ValueError):
                return False, f"{field.replace('_', ' ')} must be a number.", normalized
            if not np.isfinite(value) or value < 0:
                return False, f"{field.replace('_', ' ')} must be a non-negative finite number.", normalized
            normalized[field] = value
        if normalized["avg_duration_sec"] <= 0:
            return False, "Average duration must be greater than zero.", normalized
        if normalized["min_frequency_hz"] > normalized["max_frequency_hz"]:
            return False, "Minimum frequency cannot exceed maximum frequency.", normalized
        if normalized["zero_crossing_rate_mean"] > 1:
            return False, "Zero-crossing rate must be between 0 and 1.", normalized
        return True, "", normalized

    def create_record(self, record: dict[str, Any]) -> tuple[bool, str]:
        valid, message, normalized = self._normalise_and_validate(record)
        if not valid:
            return False, message
        record_id = normalized["id"]
        if self._data["id"].astype(str).str.casefold().eq(record_id.casefold()).any():
            return False, f"ID '{record_id}' already exists."
        original = self._data.copy(deep=True)
        self._data = pd.concat([self._data, pd.DataFrame([normalized])], ignore_index=True)
        if not self.save_csv():
            self._data = original
            return False, f"Could not save record: {self.last_error}"
        return True, "Record added."

    def read_records(self, search: str = "", habitat: str = "", sort_by: str = "common_name", ascending: bool = True) -> pd.DataFrame:
        result = self.data
        if search.strip():
            mask = result.astype(str).apply(
                lambda col: col.str.contains(search.strip(), case=False, na=False, regex=False)
            ).any(axis=1)
            result = result.loc[mask]
        if habitat and habitat != "All habitats":
            result = result.loc[result["primary_habitat"].astype(str).eq(habitat)]
        if sort_by in result.columns:
            result = result.sort_values(sort_by, ascending=ascending, kind="stable")
        return result.reset_index(drop=True)

    def update_record(self, record_id: str, updates: dict[str, Any]) -> tuple[bool, str]:
        mask = self._data["id"].astype(str).eq(str(record_id))
        if not mask.any():
            return False, "Record not found."
        original = self._data.copy(deep=True)
        candidate = original.loc[mask].iloc[0].to_dict()
        candidate.update({key: value for key, value in updates.items() if key in self.schema_columns and key != "id"})
        valid, message, normalized = self._normalise_and_validate(candidate)
        if not valid:
            return False, message
        for key, value in normalized.items():
            if key != "id":
                self._data.loc[mask, key] = value
        if not self.save_csv():
            self._data = original
            return False, f"Could not save update: {self.last_error}"
        return True, "Record updated."

    def delete_record(self, record_id: str) -> tuple[bool, str]:
        mask = self._data["id"].astype(str).eq(str(record_id))
        if not mask.any():
            return False, "Record not found."
        original = self._data
        self._data = self._data.loc[~mask].reset_index(drop=True)
        if not self.save_csv():
            self._data = original
            return False, f"Could not save deletion: {self.last_error}"
        return True, "Record deleted."

    def get_summary_stats(self) -> dict[str, Any]:
        data = self._data
        durations = pd.to_numeric(data.get("avg_duration_sec", pd.Series(dtype=float)), errors="coerce")
        centroids = pd.to_numeric(data.get("mean_centroid_hz", pd.Series(dtype=float)), errors="coerce")
        return {
            "records": int(len(data)),
            "habitats": int(data["primary_habitat"].nunique()) if len(data) else 0,
            "conservation_categories": int(data["conservation_status"].nunique()) if len(data) else 0,
            "mean_duration_sec": float(durations.mean()) if durations.notna().any() else 0.0,
            "mean_centroid_hz": float(centroids.mean()) if centroids.notna().any() else 0.0,
        }
