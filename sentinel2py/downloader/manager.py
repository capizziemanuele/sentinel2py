# sentinel2py/downloader/manager.py
import os
from typing import Optional, List
import planetary_computer
from pystac_client import Client

from sentinel2py.downloader.config import BAND_PRESETS
from sentinel2py.downloader.fetch import BandFetcher
from sentinel2py.downloader.stacker import BandStacker
from sentinel2py.downloader.selector import SentinelSelector

class Sentinel2Manager:
    """Manage search, download, stacking, and selection of Sentinel-2 tiles using presets."""

    def __init__(self, out_dir="./data"):
        self.out_dir = out_dir
        self.fetcher = BandFetcher()
        self.stacker = BandStacker()
        self.selector = SentinelSelector()
        self.catalog_url = "https://planetarycomputer.microsoft.com/api/stac/v1"

    # -----------------------------
    # Search
    # -----------------------------
    def find_items(self, bbox, start, end, max_cloud=20, limit=10):
        catalog = Client.open(self.catalog_url)
        search = catalog.search(
            collections=["sentinel-2-l2a"],
            bbox=bbox,
            datetime=f"{start}/{end}",
            query={"eo:cloud_cover": {"lt": max_cloud}},
            limit=limit,
        )
        items = list(search.get_items())
        return [planetary_computer.sign(item) for item in items]

    # -----------------------------
    # Selection
    # -----------------------------
    def select_best(self, items: List, method: str = "least_cloudy", **kwargs):
        """
        Select the best tile based on a given method.

        Parameters
        ----------
        items : list
            List of STAC items.
        method : str
            Selection method. Options: 'least_cloudy', 'by_index', 'by_date'.
        kwargs : dict
            Extra arguments required by some methods (e.g., index or date).

        Returns
        -------
        item
            Selected STAC item.
        """
        if not items:
            raise ValueError("No items provided for selection.")

        if method == "least_cloudy":
            return self.selector.least_cloudy(items)
        elif method == "by_index":
            index = kwargs.get("index")
            if index is None:
                raise ValueError("Please provide 'index' for by_index method.")
            return self.selector.by_index(items, index)
        elif method == "by_date":
            date = kwargs.get("date")
            if date is None:
                raise ValueError("Please provide 'date' (YYYY-MM-DD) for by_date method.")
            matched = self.selector.by_date(items, date)
            if not matched:
                raise ValueError(f"No items found for date {date}")
            return matched[0]  # return first match
        else:
            raise ValueError(f"Unknown selection method: {method}")

    # -----------------------------
    # Download & stack
    # -----------------------------
    def download_bands(
        self,
        item,
        preset: str = "RGB",
        stack: bool = True,
        overwrite: bool = False,
        target_res: Optional[float] = None,
        verbose: bool = True
    ):
        """
        Download bands using a preset and optionally stack them.

        Parameters
        ----------
        item : pystac.Item
            STAC item to download.
        preset : str
            Preset from config.py (e.g., "RGB", "NIR").
        stack : bool
            Whether to stack the bands after downloading.
        overwrite : bool
            Overwrite existing files.
        target_res : float, optional
            If provided, resample bands to this resolution when stacking.
        verbose : bool
            Print progress messages.

        Returns
        -------
        downloaded : dict
            {band: {"path": path, "resolution": res}}
        stacked : dict or None
            {resolution: stacked_file} if stacked, else None
        """
        if preset not in BAND_PRESETS:
            raise ValueError(f"Preset '{preset}' not found. Available: {list(BAND_PRESETS.keys())}")

        bands = BAND_PRESETS[preset]
        tile_id = item.properties.get("sentinel:tile_id", item.id)
        tile_dir = os.path.join(self.out_dir, tile_id)
        os.makedirs(tile_dir, exist_ok=True)

        # Download bands
        downloaded = self.fetcher.download_list(item, bands, tile_dir, overwrite, verbose)

        if not stack:
            if verbose:
                print("[INFO] Stacking skipped")
            return downloaded, None

        # Decide stacking resolution
        if target_res:
            stack_func = lambda paths, out_file: self.stacker.stack_to_resolution(paths, out_file, target_res)
            res_label = target_res
            if verbose:
                print(f"[INFO] Stacking bands resampled to {target_res}m")
        else:
            stack_func = self.stacker.stack_same_resolution
            res_label = min([downloaded[b]["resolution"] for b in bands])
            if verbose:
                print(f"[INFO] Stacking bands at their original resolution ({res_label}m)")

        # Build output stacked filename with resolution in the name
        date_str = str(item.properties.get("datetime", "unknown")).split("T")[0].replace("-", "")
        band_token = "_".join(bands)
        stacked_file = os.path.join(tile_dir, f"{band_token}_{date_str}_{res_label}m_stack.tif")

        # Check if file exists
        if os.path.exists(stacked_file) and not overwrite:
            if verbose:
                print(f"[SKIP] Stacked file already exists: {stacked_file}")
            return downloaded, {res_label: stacked_file}

        # Perform stacking
        band_paths = [downloaded[b]["path"] for b in bands]
        stacked_path = stack_func(band_paths, stacked_file)

        return downloaded, {res_label: stacked_path}
