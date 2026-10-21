"""Atomic local persistence for the most recent audio-analysis runs."""
from __future__ import annotations
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

class HistoryManager:
    def __init__(self, filepath: str | Path | None = None, max_entries: int = 20):
        self.filepath = Path(filepath) if filepath else Path(__file__).resolve().parents[1] / "data" / "run_history.json"
        self.audio_dir = self.filepath.parent / "history_audio"
        self.max_entries = max_entries
        self.last_error = ""

    def save_run(self, run_data: dict[str, Any], audio_bytes: bytes = None, animal_data: dict = None) -> bool:
        temp_path = None
        try:
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            self.audio_dir.mkdir(parents=True, exist_ok=True)

            entry = dict(run_data)
            timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
            entry.setdefault("timestamp", timestamp)

            if audio_bytes:
                audio_path = self.audio_dir / f"run_{timestamp.replace(':', '-')}.wav"
                with open(audio_path, "wb") as f:
                    f.write(audio_bytes)
                entry["audio_path"] = str(audio_path)

            if animal_data:
                entry["animal_data"] = animal_data

            history = self.get_history()
            history.insert(0, entry) # Add to the top of the list
            history = history[:self.max_entries]

            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".tmp", dir=self.filepath.parent, delete=False) as tmp:
                temp_path = tmp.name
                json.dump(history, tmp, ensure_ascii=False, indent=2)
                tmp.flush()
                os.fsync(tmp.fileno())
            os.replace(temp_path, self.filepath)
        except (OSError, ValueError, TypeError) as exc:
            self.last_error = str(exc)
            return False
        else:
            self.last_error = ""
            return True
        finally:
            if temp_path and os.path.exists(temp_path):
                try: os.unlink(temp_path)
                except OSError: pass

    def get_history(self) -> list[dict[str, Any]]:
        try:
            with self.filepath.open("r", encoding="utf-8") as stream:
                value = json.load(stream)
        except FileNotFoundError:
            return []
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            self.last_error = str(exc)
            return []
        else:
            self.last_error = ""
            return value[:self.max_entries] if isinstance(value, list) else []
        finally:
            pass