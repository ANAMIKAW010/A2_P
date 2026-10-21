# BioEcho

BioEcho is a local Streamlit web app for managing bioacoustic reference inventories and exploring uploaded recordings. It uses deterministic acoustic measurements and nearest-reference distance; it does not train or run machine-learning models.

## Requirements

- Python 3.10 or newer
- `pip`
- Optional: FFmpeg for decoding MP3 and some non-WAV formats. WAV is the most dependable input format.

## Install and run

Open a terminal in this project folder.

### Windows PowerShell

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run Home.py
```

If PowerShell blocks activation, use Command Prompt instead:

```bat
py -3.10 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run Home.py
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run Home.py
```

Streamlit prints a local URL (usually `http://localhost:8501`) and opens it in your browser. Stop the server with `Ctrl+C`. To listen on your local network, use `streamlit run app.py --server.address 0.0.0.0`; only do this on a trusted network.

## Use guide

### Analyze a recording

1. Open the BioEcho landing page and upload a WAV, MP3, FLAC, OGG, or M4A recording.
2. Listen with the audio control. Inspect the waveform and spectrogram.
3. Select **Analyze recording**. BioEcho extracts mean spectral centroid, RMS energy, zero-crossing rate, and duration, then compares the recording to all three local inventories.
4. Review the closest reference, ranked alternatives, and relative score. The score is an exponential transform of the nearest normalized Euclidean distance, not a calibrated probability.
5. Read the optional species note panels. They fetch Wikipedia page content over the internet; unavailable pages or network access produce fallback text.
6. Open **Recent analysis history** to review the last 20 runs saved locally in `data/run_history.json`.

### Manage reference inventories

Use the Streamlit navigation menu or the inventory cards to open Avian Acoustics, Mammalian Acoustics, or Marine & Amphibian Acoustics. Each page has five tabs:

- **View & Filter**: search all fields, filter by habitat, choose a sort field, and inspect matching rows.
- **Add Entry**: enter an ID and species details. ID, common name, and scientific name are required; IDs are unique within that inventory.
- **Edit / Delete**: select an ID, edit its fields, or check **Yes, delete** before the delete button becomes active.
- **Visualizations**: inspect frequency ranges and conservation-status counts. Charts use the active search and habitat filters.
- **Audit & Export**: download a timestamped text report (with row count and active filters) or filtered CSV.

Changes are written immediately to the relevant CSV under `data/`. The write uses a temporary file and atomic replace. Keep backups of these CSV files if they contain valuable edits.

## Data and matching notes

- The included CSV files provide six illustrative starting references per inventory. They are not a validated field reference library; replace or augment them with appropriately sourced measurements for real research.
- The inventory schema stores centroid and duration baselines but does not provide reference RMS/ZCR columns. To keep the required CSV format, the matcher uses fixed RMS and centroid-derived ZCR proxies for those dimensions. Therefore treat the displayed ranking as exploratory, and use well-curated reference data and validation before drawing scientific conclusions.
- The `min_frequency_hz` and `max_frequency_hz` columns support inventory visualizations; the current matcher uses mean centroid and average duration alongside the proxy dimensions.
- History stays in the local JSON file. It is not encrypted and should not be used for sensitive recordings on a shared computer.
- Wikipedia enrichment requires an internet connection. Inventory editing, charts, and local audio feature extraction do not require external services once dependencies are installed.

## Project layout

```text
Home.py                         Streamlit landing page and audio analysis
pages/                         Three inventory CRUD pages
core/base_manager.py           CSV CRUD, schema checks, atomic writes
core/inventory_managers.py     Domain-specific manager classes
core/feature_extractor.py      Librosa feature extraction and matching
core/history_manager.py        Local last-20-run JSON history
core/scraper.py                Best-effort Wikipedia enrichment
core/ui.py                     Shared inventory page UI
data/*.csv                     Local reference inventories
data/run_history.json          Created on first saved analysis
requirements.txt
```
