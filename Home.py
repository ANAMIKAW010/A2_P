"""BioEcho: Acoustic Biomonitoring & Bioacoustic Inventory System."""
from __future__ import annotations
import io
from pathlib import Path
import librosa
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from core.feature_extractor import extract_audio_features, match_species_rule_based
from core.history_manager import HistoryManager
from core.inventory_managers import AvianManager, MammalianManager, MarineAmphibianManager
from core.scraper import fetch_species_enrichment

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="BioEcho", page_icon="🌿", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
.stApp {background:#f6f7f4;color:#202820} .block-container{padding-top:2rem;max-width:1200px}
[data-testid="stMetric"]{background:#fff;border:1px solid #e3e8df;padding:16px;border-radius:14px}
.hero{background:linear-gradient(120deg,#e6efe4,#f7f4e9);padding:28px 32px;border-radius:18px;border:1px solid #dce5d9;margin-bottom:18px}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero"><h1>🌿 BioEcho</h1><p>Acoustic biomonitoring and bioacoustic inventory system</p><p>Explore reference inventories, inspect a recording, and compare its acoustic profile with documented baselines.</p></div>', unsafe_allow_html=True)
st.info("Identification is a transparent nearest-reference comparison, not a trained classifier. Results depend on the quality and coverage of the local reference CSVs.")

st.header("Audio Analysis Lab")
uploaded = st.file_uploader("Choose an audio recording", type=["wav", "mp3", "flac", "ogg", "m4a"], help="WAV is recommended. MP3 and other formats may require a compatible FFmpeg installation.")
if uploaded:
    st.audio(uploaded)
    try:
        audio, sr = librosa.load(io.BytesIO(uploaded.getvalue()), sr=22050, mono=True)
        if audio.size == 0: raise ValueError("No audio samples were decoded.")
        times = np.arange(len(audio)) / sr
        wave = go.Figure(go.Scattergl(x=times, y=audio, mode="lines", line={"color":"#37775a", "width":1}))
        wave.update_layout(title="Waveform", xaxis_title="Time (s)", yaxis_title="Amplitude", height=280, margin={"t":45,"b":35})
        st.plotly_chart(wave, use_container_width=True)
        spec = librosa.amplitude_to_db(np.abs(librosa.stft(audio)), ref=np.max)
        spec_fig = go.Figure(go.Heatmap(z=spec, x=librosa.frames_to_time(np.arange(spec.shape[1]), sr=sr), y=librosa.fft_frequencies(sr=sr), colorscale="Viridis", colorbar={"title":"dB"}))
        spec_fig.update_layout(title="Spectrogram", xaxis_title="Time (s)", yaxis_title="Frequency (Hz)", height=360, margin={"t":45,"b":35})
        st.plotly_chart(spec_fig, use_container_width=True)

        if st.button("Analyze recording", type="primary"):
            features = extract_audio_features(io.BytesIO(uploaded.getvalue()))
            managers = [AvianManager(), MammalianManager(), MarineAmphibianManager()]
            inventories = pd.concat([m.data.assign(domain=label) for m, label in zip(managers, ["Avian", "Mammalian", "Marine & amphibian"])], ignore_index=True)
            match = match_species_rule_based(features, inventories)

            if not match["match"]:
                st.warning("No reference records are available. Add species to an inventory first.")
            else:
                best = match["match"]
                with st.spinner("Retrieving species information..."):
                    info = fetch_species_enrichment(best.get("common_name", ""))

                st.session_state["bioecho_last_analysis"] = {
                    "filename": uploaded.name,
                    "features": features,
                    "match": match,
                    "domain": best.get("domain", ""),
                    "info": info
                }

                HistoryManager().save_run(
                    run_data={
                        "filename": uploaded.name,
                        "top_match": best.get("common_name", "Unknown"),
                        "scientific_name": best.get("scientific_name", ""),
                        "domain": best.get("domain", ""),
                        "confidence": round(match["confidence"], 2),
                        "features": features
                    },
                    audio_bytes=uploaded.getvalue(),
                    animal_data=info
                )

        analysis = st.session_state.get("bioecho_last_analysis")
        if analysis and analysis["filename"] == uploaded.name:
            best = analysis["match"]["match"]
            info = analysis["info"]
            left, right = st.columns([1, 2])
            with left:
                st.subheader("Closest reference")
                st.metric("Candidate", best["common_name"])
                st.caption(f"{best['scientific_name']} · {analysis['domain']}")
                st.metric("Relative score", f"{analysis['match']['confidence']:.1f}%")
                st.caption("A distance-derived similarity within this inventory; not a probability of correct identification.")
                st.json(analysis["features"])
            with right:
                st.subheader("Species notes")
                if info["image_url"]: st.image(info["image_url"], caption=best["common_name"], use_container_width=True)
                st.write(info["summary"])
                c1, c2, c3 = st.columns(3)
                c1.markdown("**Habitat**\n\n" + info["habitat"])
                c2.markdown("**Diet**\n\n" + info["diet"])
                c3.markdown("**Behavior**\n\n" + info["behavior"])
                if info["source_url"]: st.caption(f"Source: {info['source_url']}")
            st.subheader("Nearest reference candidates")
            st.dataframe(pd.DataFrame(analysis["match"]["ranked"]).drop(columns=["distance"], errors="ignore").head(5), use_container_width=True, hide_index=True)
    except Exception as exc:
        st.error(f"Could not decode or analyze this audio: {exc}")
else:
    st.caption("Upload an audio file to view its waveform and spectrogram, then run the acoustic comparison.")

st.divider()
st.header("Reference inventories")
nav = st.columns(3)
for col, name, page, manager in zip(nav, ["Avian Acoustics", "Mammalian Acoustics", "Marine & Amphibian"], ["1_Avian_Acoustics.py", "2_Mammalian_Acoustics.py", "3_Marine_Amphibians.py"], [AvianManager(), MammalianManager(), MarineAmphibianManager()]):
    with col:
        st.markdown(f"### {name}")
        st.write(f"{len(manager.data)} reference records")
        st.page_link(f"pages/{page}", label="Open inventory →")