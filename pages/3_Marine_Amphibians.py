import streamlit as st
from core.inventory_managers import MarineAmphibianManager
from core.ui import render_inventory
st.set_page_config(page_title="Marine & amphibian | BioEcho", page_icon="🐸", layout="wide")
render_inventory(MarineAmphibianManager(), "Marine & Amphibian Acoustics", "Browse and maintain marine and amphibian bioacoustic references.")
