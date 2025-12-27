# sentinel2py/downloader/stacker.py

"""
BandStacker – clean stacking utilities for Sentinel-2 bands.

Features:
- Stack multiple TIFF bands into a single raster
- Auto-resample to highest resolution or custom resolution
- Includes a beautiful tqdm progress bar
"""

import os
import rasterio
from rasterio.enums import Resampling
from tqdm.auto import tqdm


class BandStacker:
    """Stacks multiple raster bands into a single multi-band GeoTIFF."""

    # ===========================
    # Utility
    # ===========================
    def _get_base_meta(self, band_paths):
        """Return metadata from the first band."""
        with rasterio.open(band_paths[0]) as src:
            return src.meta.copy(), src.height, src.width, src.res

    # ===========================
    # CORE STACKER
    # ===========================
    def _stack_write(self, out_file, meta, band_paths, read_fn):
        """Write stacked output using a readable callback."""
        os.makedirs(os.path.dirname(out_file), exist_ok=True)

        with rasterio.open(out_file, "w", **meta) as dst:
            for i, band in enumerate(
                tqdm(range(len(band_paths)), desc="📦 Writing stack", unit="band")
            ):
                data = read_fn(i, band_paths[i])
                dst.write(data, i + 1)

        return out_file

    # ===========================
    # MODES
    # ===========================
    def stack_same_resolution(self, band_paths, out_file):
        """Stack assuming all bands have same pixel resolution."""
        meta, _, _, _ = self._get_base_meta(band_paths)
        meta.update(count=len(band_paths))

        # Reader callback
        def reader(i, path):
            with rasterio.open(path) as src:
                return src.read(1)

        return self._stack_write(out_file, meta, band_paths, reader)

    def stack_to_highest_resolution(self, band_paths, out_file):
        """Resample all bands to highest resolution (minimum pixel size)."""
        # choose smallest resolution band
        band_res_info = []
        for p in band_paths:
            with rasterio.open(p) as src:
                band_res_info.append((p, src.res[0]))
        base_band = sorted(band_res_info, key=lambda x: x[1])[0][0]

        with rasterio.open(base_band) as base:
            base_meta = base.meta.copy()
            meta = base_meta.copy()
            meta.update(count=len(band_paths))
            dst_height, dst_width = base.height, base.width

        def reader(i, path):
            with rasterio.open(path) as src:
                data = src.read(
                    out_shape=(1, dst_height, dst_width),
                    resampling=Resampling.bilinear,
                )
                return data[0]

        return self._stack_write(out_file, meta, band_paths, reader)

    def stack_to_resolution(self, band_paths, out_file, resolution):
        """Resample all bands to a custom target resolution (e.g. 10, 20)."""
        # find first band at that resolution
        base_path = None
        for p in band_paths:
            with rasterio.open(p) as src:
                if abs(src.res[0] - float(resolution)) < 1e-6:
                    base_path = p
                    break

        if base_path is None:
            base_path = band_paths[0]

        with rasterio.open(base_path) as base:
            base_meta = base.meta.copy()
            res_scale = base.res[0] / float(resolution)
            meta = base_meta.copy()
            meta.update(
                count=len(band_paths),
                height=int(base.height * res_scale),
                width=int(base.width * res_scale),
                transform=base.transform * base.transform.scale(
                    base.res[0] / resolution, base.res[1] / resolution
                ),
            )
            dst_height, dst_width = meta["height"], meta["width"]

        def reader(i, path):
            with rasterio.open(path) as src:
                data = src.read(
                    out_shape=(1, dst_height, dst_width),
                    resampling=Resampling.bilinear,
                )
                return data[0]

        return self._stack_write(out_file, meta, band_paths, reader)
