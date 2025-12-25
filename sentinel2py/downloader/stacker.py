# sentinel2py/downloader/stacker.py
import os
import logging
from typing import List, Optional
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling

log = logging.getLogger(__name__)

class BandStacker:
    """
    Stack multiple Sentinel-2 bands into one GeoTIFF.
    Supports:
    - same resolution stacking
    - resampling to highest resolution
    - resampling to user-defined resolution
    """

    @staticmethod
    def _stack_arrays(band_paths: List[str], out_path: str, target_res: Optional[float] = None):
        with rasterio.open(band_paths[0]) as ref:
            meta = ref.meta.copy()
            ref_crs = ref.crs
            if target_res:
                scale = ref.res[0] / target_res
                height, width = int(ref.height * scale), int(ref.width * scale)
                transform = rasterio.Affine(
                    target_res, ref.transform.b, ref.transform.c,
                    ref.transform.d, -target_res, ref.transform.f
                )
                print(f"[STACK] Resampling bands to {target_res}m resolution")
            else:
                height, width = ref.height, ref.width
                transform = ref.transform
                print(f"[STACK] Keeping original resolution: {ref.res[0]}m")

        stack = np.zeros((len(band_paths), height, width), dtype=meta["dtype"])

        for i, path in enumerate(band_paths):
            with rasterio.open(path) as src:
                arr = np.zeros((height, width), dtype=meta["dtype"])
                reproject(
                    source=rasterio.band(src, 1),
                    destination=arr,
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=ref_crs,
                    resampling=Resampling.bilinear
                )
                stack[i] = arr
                print(f"[STACK] Band added: {os.path.basename(path)}")

        meta.update(count=len(band_paths), height=height, width=width, transform=transform)

        with rasterio.open(out_path, "w", **meta) as dst:
            for i in range(len(band_paths)):
                dst.write(stack[i], i + 1)

        print(f"[STACK] Stacked file created: {out_path}")
        return out_path

    def stack_same_resolution(self, band_paths: List[str], out_path: str):
        """Stack bands keeping original resolutions."""
        return self._stack_arrays(band_paths, out_path)

    def stack_to_highest_resolution(self, band_paths: List[str], out_path: str):
        """Resample all bands to the highest (smallest pixel size) resolution."""
        resolutions = [rasterio.open(p).res[0] for p in band_paths]
        target_res = min(resolutions)
        return self._stack_arrays(band_paths, out_path, target_res)

    def stack_to_resolution(self, band_paths: List[str], out_path: str, resolution: float):
        """Resample all bands to a user-defined resolution."""
        return self._stack_arrays(band_paths, out_path, resolution)
