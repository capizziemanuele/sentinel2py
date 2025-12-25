# sentinel2py/downloader/fetch.py
import os
import time
import logging
from typing import List, Dict
import requests
import planetary_computer
from tqdm import tqdm

log = logging.getLogger(__name__)

class BandFetcher:
    """
    Download Sentinel-2 bands from Microsoft Planetary Computer.

    Features:
    - Sequential download of bands
    - Skips files that already exist
    - Shows progress bar using tqdm
    - Retry mechanism for failed downloads
    """

    def __init__(self, retries: int = 3, timeout: int = 20):
        """
        Initialize the BandFetcher.

        Parameters
        ----------
        retries : int
            Number of retry attempts if a download fails.
        timeout : int
            Timeout in seconds for HTTP requests.
        """
        self.retries = retries
        self.timeout = timeout

    def download_one(self, item, band: str, dest_dir: str) -> str:
        """
        Download a single band of a Sentinel-2 item.

        Parameters
        ----------
        item : pystac.Item
            STAC item representing a Sentinel-2 tile.
        band : str
            Band name to download (e.g., "B02", "B03").
        dest_dir : str
            Directory where the file will be saved.

        Returns
        -------
        str
            Path to the downloaded file.

        Notes
        -----
        - Skips download if file already exists.
        - Shows a tqdm progress bar.
        - Retries download if network fails.
        """
        os.makedirs(dest_dir, exist_ok=True)
        asset = item.assets.get(band)
        if asset is None:
            raise ValueError(f"Band '{band}' not found in item {item.id}")

        signed = planetary_computer.sign(asset)
        local_path = os.path.join(dest_dir, f"{band}.tif")

        if os.path.exists(local_path):
            tqdm.write(f"[SKIP] {local_path} already exists")
            return local_path

        for attempt in range(1, self.retries + 1):
            try:
                with requests.get(signed.href, stream=True, timeout=self.timeout) as r:
                    r.raise_for_status()
                    total_size = int(r.headers.get("content-length", 0))
                    chunk_size = 8192

                    # Use tqdm to show progress bar
                    with open(local_path, "wb") as f, tqdm(
                        total=total_size,
                        unit="B",
                        unit_scale=True,
                        desc=f"Downloading {band}",
                        leave=True,
                        miniters=1
                    ) as bar:
                        for chunk in r.iter_content(chunk_size=chunk_size):
                            if chunk:
                                f.write(chunk)
                                bar.update(len(chunk))

                tqdm.write(f"[SUCCESS] Downloaded {local_path}")
                return local_path

            except requests.RequestException as e:
                tqdm.write(f"[RETRY {attempt}] Failed downloading {band}: {e}")
                if attempt < self.retries:
                    tqdm.write("[INFO] Retrying in 2 seconds...")
                    time.sleep(2)
                else:
                    raise RuntimeError(f"[ERROR] Failed to download {band} after {self.retries} attempts")

    def download_list(self, item, bands: List[str], dest_dir: str) -> Dict[str, str]:
        """
        Download multiple bands sequentially.

        Parameters
        ----------
        item : pystac.Item
            STAC item representing a Sentinel-2 tile.
        bands : List[str]
            List of band names to download.
        dest_dir : str
            Directory where the bands will be saved.

        Returns
        -------
        Dict[str, str]
            Dictionary mapping band name to local file path.
        """
        downloaded_paths = {}
        print(f"[INFO] Starting download of {len(bands)} bands for tile {item.id}")

        for band in bands:
            tqdm.write(f"[INFO] Processing band: {band}")
            path = self.download_one(item, band, dest_dir)
            downloaded_paths[band] = path

        print(f"[INFO] Completed download of {len(bands)} bands for tile {item.id}")
        return downloaded_paths
