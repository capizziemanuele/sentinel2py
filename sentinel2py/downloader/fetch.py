import os
import time
import requests
from typing import List, Dict
from tqdm import tqdm
import planetary_computer
from .config import BAND_PRESETS, BAND_RESOLUTIONS

class BandFetcher:
    """Download Sentinel-2 bands from Planetary Computer."""

    def __init__(self, retries: int = 3, timeout: int = 20):
        self.retries = retries
        self.timeout = timeout

    def _build_band_filename(self, band: str, item) -> str:
        date_str = item.properties.get("datetime", "unknown").split("T")[0].replace("-", "")
        res = BAND_RESOLUTIONS.get(band, 10)
        return f"{band}_{date_str}_{res}m.tif"

    def download_one(self, item, band: str, dest_dir: str, overwrite=False, verbose=True) -> str:
        os.makedirs(dest_dir, exist_ok=True)
        asset = item.assets.get(band)
        if asset is None:
            raise ValueError(f"Band '{band}' not found in item {item.id}")
        signed = planetary_computer.sign(asset)
        filename = self._build_band_filename(band, item)
        local_path = os.path.join(dest_dir, filename)
        if os.path.exists(local_path) and not overwrite:
            if verbose:
                tqdm.write(f"[SKIP] {filename} already exists")
            return local_path

        for attempt in range(1, self.retries + 1):
            try:
                with requests.get(signed.href, stream=True, timeout=self.timeout) as r:
                    r.raise_for_status()
                    total_size = int(r.headers.get("content-length", 0))
                    with open(local_path, "wb") as f, tqdm(total=total_size, unit="B", unit_scale=True, desc=f"Downloading {band}", leave=True) as bar:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                bar.update(len(chunk))
                if verbose:
                    tqdm.write(f"[SUCCESS] Downloaded {local_path}")
                return local_path
            except requests.RequestException as e:
                tqdm.write(f"[RETRY {attempt}] Failed downloading {filename}: {e}")
                time.sleep(2)
        raise RuntimeError(f"[ERROR] Failed to download {filename} after {self.retries} attempts")

    def download_list(self, item, bands: List[str], dest_dir: str, overwrite=False, verbose=True) -> Dict[str, Dict]:
        downloaded_paths = {}
        for band in bands:
            path = self.download_one(item, band, dest_dir, overwrite, verbose)
            res = BAND_RESOLUTIONS.get(band)
            downloaded_paths[band] = {"path": path, "resolution": res}
        return downloaded_paths
