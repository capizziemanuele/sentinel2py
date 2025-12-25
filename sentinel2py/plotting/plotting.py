import os
import rasterio
import numpy as np
import matplotlib.pyplot as plt

class SentinelPlotter:
    """Plot RGB and NDVI images from Sentinel-2."""

    @staticmethod
    def plot_rgb_with_info(rgb_path: str, item=None, bands=(1, 2, 3), preset="RGB", stretch=True, method_func=None, **kwargs):
        with rasterio.open(rgb_path) as src:
            img = src.read(bands)
            img = np.transpose(img, (1, 2, 0))
            res_x, res_y = src.res
            resolution = int((res_x + res_y)/2)

        # Apply custom visualization method if given
        if method_func:
            img = method_func(img, **kwargs)
        elif stretch:
            p2, p98 = np.percentile(img, (2, 98))
            img = np.clip((img - p2) / (p98 - p2), 0, 1)

        if item:
            tile_id = item.properties.get("sentinel:tile_id", item.id)
            date = str(item.properties.get("datetime", "unknown")).split("T")[0]
            cloud = item.properties.get("eo:cloud_cover", "unknown")
            title = f"{preset} - Tile {tile_id} | Date: {date} | Cloud: {cloud}% | Res: {resolution}m"
        else:
            title = f"{preset} - {os.path.basename(rgb_path)} | Res: {resolution}m"

        plt.figure(figsize=(8, 8))
        plt.imshow(img)
        plt.axis("off")
        plt.title(title, fontsize=12)
        plt.show()

    @staticmethod
    def compute_ndvi(red_path: str, nir_path: str):
        with rasterio.open(red_path) as r:
            red = r.read(1).astype(float)
        with rasterio.open(nir_path) as r:
            nir = r.read(1).astype(float)
        return (nir - red) / (nir + red + 1e-6)

    @staticmethod
    def plot_ndvi(ndvi_array: np.ndarray, title="NDVI", cmap="RdYlGn"):
        plt.figure(figsize=(8, 8))
        plt.imshow(ndvi_array, cmap=cmap, vmin=-1, vmax=1)
        plt.colorbar(label="NDVI")
        plt.title(title)
        plt.axis("off")
        plt.show()
