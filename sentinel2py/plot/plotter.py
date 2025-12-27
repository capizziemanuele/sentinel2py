# sentinel2py/plot/plotter.py
import numpy as np
import rasterio
import matplotlib.pyplot as plt
from skimage import exposure

class SentinelPlotter:
    """
    Sentinel-2 plotting utilities for RGB, NDVI, NDWI.
    
    Features:
    - Percentile-based stretch for RGB
    - Optional histogram equalization and gamma correction
    - Custom 1-based band indices
    - Downsampling for large images
    - NDVI/NDWI values can remain [-1,1] or normalized to [0,1]
    """
    
    def __init__(self):
        pass

    # -----------------------------
    # Internal helpers
    # -----------------------------
    def _read_stack(self, path, band_indices=None, downsample=None):
        """Read selected bands from a stacked GeoTIFF (1-based indices)."""
        with rasterio.open(path) as src:
            if band_indices is None:
                band_indices = list(range(1, src.count + 1))
            if downsample:
                out_shape = (len(band_indices), src.height // downsample, src.width // downsample)
                arr = src.read(band_indices, out_shape=out_shape)
            else:
                arr = src.read(band_indices)
        arr = np.transpose(arr, (1, 2, 0))  # C,H,W -> H,W,C
        return arr.astype(np.float32)

    def _stretch(self, arr, gamma=1.0, percent_clip=(2, 98)):
        """Percentile stretch per band with optional gamma correction."""
        out = np.zeros_like(arr)
        for i in range(arr.shape[2]):
            low, high = np.percentile(arr[:, :, i], percent_clip)
            out[:, :, i] = (arr[:, :, i] - low) / (high - low + 1e-8)
        out = np.clip(out, 0, 1)
        if gamma != 1.0:
            out = out ** (1 / gamma)
        return out

    def _equalize(self, arr):
        """Histogram equalization per band."""
        out = np.zeros_like(arr)
        for i in range(arr.shape[2]):
            out[:, :, i] = exposure.equalize_hist(arr[:, :, i])
        return out

    # -----------------------------
    # RGB plotting
    # -----------------------------
    def plot_rgb(self, path, bands=(1,2,3), downsample=None,
                 stretch=True, percent_clip=(2,98), gamma=1.0, equalize=False):
        """
        Plot RGB composite with optional stretch, gamma, equalization.

        Parameters:
        - path: stacked GeoTIFF path
        - bands: 1-based indices tuple (R,G,B)
        - downsample: factor to downsample
        - stretch: percentile stretch
        - percent_clip: low/high percentile for stretch
        - gamma: gamma correction
        - equalize: histogram equalization
        """
        if len(bands) != 3:
            raise ValueError("bands must be a tuple of three indices (R,G,B)")
        
        arr = self._read_stack(path, band_indices=list(bands), downsample=downsample)
        
        if stretch:
            arr = self._stretch(arr, gamma=gamma, percent_clip=percent_clip)
        if equalize:
            arr = self._equalize(arr)
        
        plt.figure(figsize=(8,8))
        plt.imshow(arr)
        plt.title("RGB Composite")
        plt.axis("off")
        plt.show()

    # -----------------------------
    # NDVI plotting
    # -----------------------------
    def plot_ndvi(self, path, bands=(4,3), downsample=None, stretch=False, 
              percent_clip=(2,98), gamma=1.0, equalize=False, normalize=False, cmap="RdYlGn"):
        if len(bands) != 2:
            raise ValueError("bands must be a tuple (NIR, RED)")

        arr = self._read_stack(path, band_indices=list(bands), downsample=downsample)
        nir = arr[:, :, 0]
        red = arr[:, :, 1]
        ndvi = (nir - red) / (nir + red + 1e-8)

        # Keep [-1,1] unless normalize=True
        if normalize:
            ndvi = (ndvi + 1) / 2

        # Optional: contrast stretch within current NDVI range
        if stretch:
            # Stretch between low/high percentiles
            low, high = np.percentile(ndvi, percent_clip)
            ndvi = (ndvi - low) / (high - low + 1e-8)
            if not normalize:
                # Scale back to [-1,1] range
                ndvi = ndvi * 2 - 1
            ndvi = np.clip(ndvi, -1, 1) if not normalize else np.clip(ndvi, 0, 1)
        
        # Optional histogram equalization only on normalized data
        if equalize:
            if not normalize:
                print("Equalization not recommended for [-1,1] NDVI. Skipping.")
            else:
                ndvi = exposure.equalize_hist(ndvi)

        plt.figure(figsize=(8,8))
        plt.imshow(ndvi, cmap=cmap, vmin=-1 if not normalize else 0, vmax=1)
        plt.colorbar(label="NDVI")
        plt.title("NDVI")
        plt.axis("off")
        plt.show()

    # -----------------------------
    # NDWI plotting
    # -----------------------------
    def plot_ndwi(self, path, bands=(2,4), downsample=None, stretch=False, 
                  percent_clip=(2,98), gamma=1.0, equalize=False, normalize=False, cmap="Blues"):
        """
        Compute & plot NDWI = (GREEN - NIR)/(GREEN + NIR)
        
        Parameters:
        - bands: tuple of 1-based indices (GREEN, NIR)
        - normalize: scale to [0,1] if True
        """
        if len(bands) != 2:
            raise ValueError("bands must be a tuple (GREEN, NIR)")
        
        arr = self._read_stack(path, band_indices=list(bands), downsample=downsample)
        green = arr[:, :, 0]
        nir = arr[:, :, 1]
        ndwi = (green - nir) / (green + nir + 1e-8)
        
        if normalize:
            ndwi = (ndwi + 1)/2
        if stretch:
            ndwi = self._stretch(ndwi[:, :, np.newaxis], gamma=gamma, percent_clip=percent_clip)[:,:,0]
        if equalize:
            ndwi = exposure.equalize_hist((ndwi + 1)/2 if not normalize else ndwi)
            if not normalize:
                ndwi = ndwi * 2 - 1
        
        plt.figure(figsize=(8,8))
        plt.imshow(ndwi, cmap=cmap, vmin=-1 if not normalize else 0, vmax=1)
        plt.colorbar(label="NDWI")
        plt.title("NDWI")
        plt.axis("off")
        plt.show()
