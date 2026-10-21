import streamlit as st
import librosa
import numpy as np
import plotly.graph_objects as go
from pathlib import Path
from core.history_manager import HistoryManager

st.set_page_config(page_title="Run History", page_icon="📜", layout="wide")

st.title("📜 Acoustic Diagnostics History")
st.markdown("Review your past audio identifications, complete with waveforms and species data.")

history_mgr = HistoryManager()
history = history_mgr.get_history()

if not history:
    st.info("No run history found. Go to the main app to analyze some audio!")
else:
    run_options = {f"{run['timestamp']} - {run['top_match']} ({run.get('filename', 'Unknown')})": run for run in
                   history}
    selected_run_label = st.selectbox("Select a past analysis:", list(run_options.keys()))

    selected_run = run_options[selected_run_label]
    animal_data = selected_run.get("animal_data", {})
    audio_path = selected_run.get("audio_path")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader(f"Identified: {selected_run.get('top_match')}")
        if animal_data.get("image_url"):
            st.image(animal_data["image_url"], use_container_width=True)

        st.markdown(f"**Summary:** {animal_data.get('summary', 'No summary available.')}")
        st.markdown(f"**Habitat:** {animal_data.get('habitat', 'N/A')}")
        st.markdown(f"**Diet:** {animal_data.get('diet', 'N/A')}")
        st.markdown(f"**Behavior:** {animal_data.get('behavior', 'N/A')}")

    with col2:
        st.subheader("Acoustic Fingerprint")
        if audio_path and Path(audio_path).exists():
            st.audio(audio_path)
            try:
                audio, sr = librosa.load(audio_path, sr=22050, mono=True)
                times = np.arange(len(audio)) / sr

                wave_fig = go.Figure(
                    go.Scattergl(x=times, y=audio, mode="lines", line={"color": "#37775a", "width": 1}))
                wave_fig.update_layout(title="Waveform", xaxis_title="Time (s)", yaxis_title="Amplitude", height=280,
                                       margin={"t": 45, "b": 35})
                st.plotly_chart(wave_fig, use_container_width=True)

                spec = librosa.amplitude_to_db(np.abs(librosa.stft(audio)), ref=np.max)
                spec_fig = go.Figure(go.Heatmap(z=spec, x=librosa.frames_to_time(np.arange(spec.shape[1]), sr=sr),
                                                y=librosa.fft_frequencies(sr=sr), colorscale="Viridis"))
                spec_fig.update_layout(title="Spectrogram", xaxis_title="Time (s)", yaxis_title="Frequency (Hz)",
                                       height=360, margin={"t": 45, "b": 35})
                st.plotly_chart(spec_fig, use_container_width=True)

            except Exception as e:
                st.error(f"Could not load audio visualizations: {e}")
        else:
            st.warning("Audio file not found on disk. It may have been moved or deleted.")