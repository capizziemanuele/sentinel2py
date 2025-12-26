# app.py
import streamlit as st
import os
import numpy as np
import rasterio
import matplotlib.pyplot as plt
from sentinel2py.downloader.manager import Sentinel2Manager
from sentinel2py.downloader.config import BAND_PRESETS

# -----------------------------
# 1️⃣ App configuration
# -----------------------------
st.set_page_config(page_title="Sentinel-2 Downloader", layout="wide")

st.title("🌍 Sentinel-2 Downloader & Viewer")

OUT_DIR = "./sentinel_data"
manager = Sentinel2Manager(out_dir=OUT_DIR)

# -----------------------------
# 2️⃣ Input parameters
# -----------------------------
st.sidebar.header("Search Parameters")

bbox_input = st.sidebar.text_input(
    "Bounding Box (min_lon,min_lat,max_lon,max_lat)",
    "8.5,45.9,8.6,46.0"
)
bbox = [float(x.strip()) for x in bbox_input.split(",")]

start_date = st.sidebar.date_input("Start Date")
end_date = st.sidebar.date_input("End Date")

n_tiles = st.sidebar.slider("Number of least cloudy tiles", 1, 5, 3)
preset = st.sidebar.selectbox("Band preset", list(BAND_PRESETS.keys()))
stack_bands = st.sidebar.checkbox("Stack bands", value=True)
target_res = st.sidebar.text_input("Target resolution (m, empty = native)", "")

if target_res.strip():
    try:
        target_res = float(target_res)
    except ValueError:
        st.error("Invalid target resolution, must be a number.")
        target_res = None
else:
    target_res = None

overwrite = st.sidebar.checkbox("Overwrite existing files", value=False)

# -----------------------------
# 3️⃣ Search and download
# -----------------------------
if st.button("Search & Download Tiles"):

    with st.spinner("Searching for least cloudy tiles..."):
        try:
            tiles = manager.get_least_cloudy_tiles(
                bbox,
                start_date.isoformat(),
                end_date.isoformat(),
                n_tiles=n_tiles
            )
        except ValueError as e:
            st.error(str(e))
            st.stop()

    st.success(f"Found {len(tiles)} tiles!")
    manager.print_tiles(tiles)

    all_downloaded, all_stacked = {}, {}
    for i, tile in enumerate(tiles):
        st.write(f"### Tile {i+1}: {tile.properties.get('sentinel:tile_id', tile.id)}")
        downloaded, stacked = manager.download_multiple_tiles(
            [tile],
            preset=preset,
            stack=stack_bands,
            target_res=target_res,
            overwrite=overwrite
        )
        all_downloaded.update(downloaded)
        all_stacked.update(stacked)

        # Visualize RGB if stacked
        if stacked and preset == "RGB":
            tile_id = list(stacked.keys())[0]
            stacked_file = list(stacked[tile_id].values())[0]

            with rasterio.open(stacked_file) as src:
                rgb = src.read([1, 2, 3]).transpose(1, 2, 0)
                rgb = rgb.astype(float) / rgb.max()

            st.image(rgb, caption=f"Stacked RGB - {tile_id}", use_column_width=True)
