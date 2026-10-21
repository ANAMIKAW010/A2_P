import streamlit as st
from core.inventory_managers import MammalianManager
from core.ui import render_inventory
st.set_page_config(page_title="Mammalian acoustics | BioEcho", page_icon="🐋", layout="wide")
render_inventory(MammalianManager(), "Mammalian Acoustics", "Browse and maintain terrestrial and marine mammal call references.")
