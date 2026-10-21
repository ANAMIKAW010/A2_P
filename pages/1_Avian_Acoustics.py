import streamlit as st
from core.inventory_managers import AvianManager
from core.ui import render_inventory
st.set_page_config(page_title="Avian acoustics | BioEcho", page_icon="🐦", layout="wide")
render_inventory(AvianManager(), "Avian Acoustics", "Browse and maintain bird call reference records.")
