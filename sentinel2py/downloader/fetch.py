# sentinel2py/downloader/fetch.py

import os
import time
import requests
from typing import List, Dict, Any
import planetary_computer
from .config import BAND_PRESETS, BAND_RESOLUTIONS
from tqdm.auto import tqdm


class DownloadError(Exception):
    """Raised when a band cannot be downloaded after retries."""
    pass


class BandFetcher:
    """Download Sentinel-2 bands from Planetary Computer, notebook-friendly."""

    def __init__(self, retries: int = 3, timeout: int = 20, chunk_size: int = 8192):
        self.retries = retries
        self.timeout = timeout
        self.chunk_size = chunk_size

    # -------------------------
    # Filename builder
    # -------------------------
    def _build_band_filename(self, band: str, item) -> str:
        date_str = item.properties.get("datetime", "unknown").split("T")[0].replace("-", "")
        res = BAND_RESOLUTIONS.get(band, 10)
        return f"{band}_{date_str}_{res}m.tif"

    # -------------------------
    # Download a single band
    # -------------------------
    def download_one(
        self,
        item,
        band: str,
        dest_dir: str,
        overwrite: bool = False,
        verbose: bool = True
    ) -> str:

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

        # Retry loop
        for attempt in range(1, self.retries + 1):
            try:
                with requests.get(signed.href, stream=True, timeout=self.timeout) as r:
                    r.raise_for_status()
                    total_size = int(r.headers.get("content-length", 0))

                    with open(local_path, "wb") as f, tqdm(
                        total=total_size,
                        unit="B",
                        unit_scale=True,
                        desc=f"📥 {band}",
                        leave=False,
                        dynamic_ncols=True
                    ) as bar:
                        for chunk in r.iter_content(chunk_size=self.chunk_size):
                            if chunk:
                                f.write(chunk)
                                bar.update(len(chunk))

                if verbose:
                    tqdm.write(f"[SUCCESS] Downloaded {filename}")
                return local_path

            except requests.RequestException as e:
                tqdm.write(f"[RETRY {attempt}] Failed downloading {filename}: {e}")
                time.sleep(2)

        raise DownloadError(f"Failed to download {filename} after {self.retries} attempts")

    # -------------------------
    # Download multiple bands
    # -------------------------
    def download_list(
        self,
        item,
        bands: List[str],
        dest_dir: str,
        overwrite: bool = False,
        verbose: bool = True
    ) -> Dict[str, Dict[str, Any]]:

        downloaded_paths: Dict[str, Dict[str, Any]] = {}

        if verbose:
            tqdm.write(f"[INFO] Downloading {len(bands)} Sentinel-2 bands...")

        for band in tqdm(bands, desc="Bands", unit="band", leave=True, dynamic_ncols=True):
            path = self.download_one(item, band, dest_dir, overwrite, verbose)
            res = BAND_RESOLUTIONS.get(band)
            downloaded_paths[band] = {"path": path, "resolution": res}

        return downloaded_paths
