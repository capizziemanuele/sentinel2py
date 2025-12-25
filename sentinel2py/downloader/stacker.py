import os
from typing import List, Optional
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling

class BandStacker:
    """Stack Sentinel-2 bands with flexible resampling."""

    @staticmethod
    def _stack_arrays(band_paths: List[str], out_path: str, target_res: Optional[float] = None):
        if not band_paths:
            raise ValueError("No band paths provided for stacking.")

        with rasterio.open(band_paths[0]) as ref:
            meta = ref.meta.copy()
            ref_crs = ref.crs
            if target_res:
                scale = ref.res[0] / target_res
                height, width = int(ref.height * scale), int(ref.width * scale)
                transform = rasterio.Affine(target_res, ref.transform.b, ref.transform.c, ref.transform.d, -target_res, ref.transform.f)
                print(f"[STACK] Resampling bands to {target_res}m resolution")
            else:
                height, width = ref.height, ref.width
                transform = ref.transform
                print(f"[STACK] Keeping original resolution: {ref.res[0]}m")

        stack = np.zeros((len(band_paths), height, width), dtype=meta["dtype"])

        for i, path in enumerate(band_paths):
            with rasterio.open(path) as src:
                arr = np.zeros((height, width), dtype=meta["dtype"])
                reproject(source=rasterio.band(src, 1), destination=arr, src_transform=src.transform, src_crs=src.crs, dst_transform=transform, dst_crs=ref_crs, resampling=Resampling.bilinear)
                stack[i] = arr
                print(f"[STACK] Band added: {os.path.basename(path)}")

        meta.update(count=len(band_paths), height=height, width=width, transform=transform)
        with rasterio.open(out_path, "w", **meta) as dst:
            for i in range(len(band_paths)):
                dst.write(stack[i], i + 1)

        print(f"[STACK] Stacked file created: {out_path}")
        return out_path

    def stack_same_resolution(self, band_paths: List[str], out_path: str):
        print(f"[INFO] Stacking {len(band_paths)} bands at their original resolutions...")
        return self._stack_arrays(band_paths, out_path)

    def stack_to_highest_resolution(self, band_paths: List[str], out_path: str):
        resolutions = [rasterio.open(p).res[0] for p in band_paths]
        target_res = min(resolutions)
        print(f"[INFO] Stacking {len(band_paths)} bands to highest resolution ({target_res}m)...")
        return self._stack_arrays(band_paths, out_path, target_res)

    def stack_to_resolution(self, band_paths: List[str], out_path: str, resolution: float):
        print(f"[INFO] Stacking {len(band_paths)} bands to user-defined resolution ({resolution}m)...")
        return self._stack_arrays(band_paths, out_path, resolution)
