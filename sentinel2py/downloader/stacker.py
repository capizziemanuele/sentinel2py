# sentinel2py/downloader/stacker.py

import os
from typing import List, Optional
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from tqdm.auto import tqdm

class BandStacker:
    """Stack Sentinel-2 bands with flexible resampling and proper QGIS-friendly output."""

    @staticmethod
    def _stack_arrays(band_paths: List[str], out_path: str, target_res: Optional[float] = None):
        if not band_paths:
            raise ValueError("No band paths provided for stacking.")

        # Open reference band
        with rasterio.open(band_paths[0]) as ref:
            meta = ref.meta.copy()
            ref_crs = ref.crs
            ref_dtype = ref.meta["dtype"]

            if target_res:
                # Compute new width/height based on target resolution
                scale_x = ref.res[0] / target_res
                scale_y = ref.res[1] / target_res
                width = int(ref.width * scale_x)
                height = int(ref.height * scale_y)

                # Build new transform
                transform = rasterio.Affine(
                    target_res, ref.transform.b, ref.transform.c,
                    ref.transform.d, -target_res, ref.transform.f
                )
                print(f"[STACK] Resampling bands to {target_res}m resolution")
            else:
                width = ref.width
                height = ref.height
                transform = ref.transform
                target_res = ref.res[0]
                print(f"[STACK] Keeping original resolution: {target_res}m")

        # Initialize empty stack array
        stack = np.zeros((len(band_paths), height, width), dtype=ref_dtype)

        # Reproject each band into the stack with progress bar
        for i, path in enumerate(tqdm(band_paths, desc="Stacking bands", unit="band")):
            with rasterio.open(path) as src:
                reproject(
                    source=rasterio.band(src, 1),
                    destination=stack[i],
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=ref_crs,
                    resampling=Resampling.bilinear
                )

        # Update metadata for the stacked file
        meta.update(
            count=len(band_paths),
            height=height,
            width=width,
            transform=transform,
            dtype=ref_dtype
        )

        # Write stacked raster
        with rasterio.open(out_path, "w", **meta) as dst:
            for i in range(len(band_paths)):
                dst.write(stack[i], i + 1)

        print(f"[STACK] Stacked file created: {out_path}")
        return out_path

    # -----------------------------
    # Public stacking methods
    # -----------------------------
    def stack_same_resolution(self, band_paths: List[str], out_path: str):
        """Stack bands at their native resolution."""
        print(f"[INFO] Stacking {len(band_paths)} bands at original resolution...")
        return self._stack_arrays(band_paths, out_path)

    def stack_to_highest_resolution(self, band_paths: List[str], out_path: str):
        """Stack bands to the highest (smallest) resolution among the bands."""
        resolutions = [rasterio.open(p).res[0] for p in band_paths]
        target_res = min(resolutions)
        print(f"[INFO] Stacking {len(band_paths)} bands to highest resolution ({target_res}m)...")
        return self._stack_arrays(band_paths, out_path, target_res)

    def stack_to_resolution(self, band_paths: List[str], out_path: str, resolution: float):
        """Stack bands to a user-defined resolution."""
        print(f"[INFO] Stacking {len(band_paths)} bands to target resolution ({resolution}m)...")
        return self._stack_arrays(band_paths, out_path, resolution)
