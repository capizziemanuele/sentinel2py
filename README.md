# Sentinel2Py

`Sentinel2Py` is a Python package for **downloading, stacking, and visualizing Sentinel-2 satellite imagery**. It integrates STAC search via [Microsoft Planetary Computer](https://planetarycomputer.microsoft.com/) and provides utilities to generate **RGB composites and spectral indices** such as NDVI and NDWI.

---

## Features

- Search for Sentinel-2 L2A tiles by bounding box, date range, and cloud cover
- Download bands using **presets** (RGB, RGBNIR, NDVI, NDWI, etc.)
- Stack bands into single GeoTIFFs at native or specified resolution
- Plot **RGB**, **NDVI**, and **NDWI** with percentile stretching, gamma correction, histogram equalization, and optional normalization
- Download multiple tiles in one call

---

## Installation

```bash
git clone <your-repo-url>
cd sentinel2py
pip install -r requirements.txt
```

---


### Initialize Manager and Plotter

```python
from sentinel2py.downloader.manager import Sentinel2Manager
from sentinel2py.plot.plotter import SentinelPlotter

manager = Sentinel2Manager(out_dir="./data")
plotter = SentinelPlotter()
```


---

### **Download & Stack Bands**

```python
downloaded, stacked = manager.download_bands(tile, preset="RGBNIR", stack=True)
stack_path = list(stacked.values())[0]  # Get stacked file path
```

---

### **Plot RGB and Indices**

```python
# RGB True Color
plotter.plot_rgb(
    stack_path,
    bands=(3,2,1),  # B04,B03,B02
    downsample=4,
    stretch=True,
    gamma=1,
    equalize=False)

# NDVI
plotter.plot_ndvi(
    stack_path,
    bands=(4,3),    # NIR, RED
    downsample=4,
    stretch=True,
    normalize=False,
    cmap="RdYlGn")

# NDWI
plotter.plot_ndwi(
    stack_path,
    bands=(2,4),    # GREEN, NIR
    downsample=4,
    stretch=False,
    normalize=False,
    cmap="Blues",
    equalize=True)
```
---

### Download Multiple Tiles

```python
all_downloaded, all_stacked = manager.download_multiple_tiles(
    tiles,
    preset="RGBNIR",
    stack=True,
    target_res="highest",
    overwrite=False)
```
---

### **Optional: Cloud Cover Table**

```python
import pandas as pd

df = pd.DataFrame([{
    "Tile": t.id.split("_")[-2],
    "Date": t.properties.get("datetime").split("T")[0],
    "Cloud (%)": t.properties.get("eo:cloud_cover", "N/A")
} for t in tiles])

print(df)
```


---

### **Notes & License**

---

## Notes

- NDVI and NDWI values can remain in the natural range `[-1,1]` or be normalized to `[0,1]`
- `BAND_PRESETS` are customizable; you can define new combinations of bands
- Downsampling (`downsample`) is useful for plotting large tiles without using too much memory

---

## License

MIT License – free to use and modify

