# sentinel2py/downloader/manager.py
import os
from typing import Optional, List, Dict
import planetary_computer
from pystac_client import Client
from tqdm import tqdm

from sentinel2py.downloader.config import BAND_PRESETS, BAND_RESOLUTIONS
from sentinel2py.downloader.fetch import BandFetcher
from sentinel2py.downloader.stacker import BandStacker
from sentinel2py.downloader.selector import SentinelSelector

class Sentinel2Manager:
    """Manage search, download, stacking, and selection of Sentinel-2 tiles."""

    def __init__(self, out_dir="./data"):
        self.out_dir = out_dir
        self.fetcher = BandFetcher()
        self.stacker = BandStacker()
        self.selector = SentinelSelector()
        self.catalog_url = "https://planetarycomputer.microsoft.com/api/stac/v1"

    # -----------------------------
    # Search
    # -----------------------------
    def find_items(self, bbox, start, end, max_cloud=20, limit=10) -> List:
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
            return matched[0]
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
        """Download bands and optionally stack them."""
        if preset not in BAND_PRESETS:
            raise ValueError(f"Preset '{preset}' not found. Available: {list(BAND_PRESETS.keys())}")

        bands = BAND_PRESETS[preset]
        tile_id = item.properties.get("sentinel:tile_id", item.id)
        tile_dir = os.path.join(self.out_dir, tile_id)
        os.makedirs(tile_dir, exist_ok=True)

        downloaded_paths = {}

        if verbose:
            print(f"[INFO] Downloading {len(bands)} Sentinel-2 bands...")

        # Download bands with progress
        for band in tqdm(bands, desc="Overall Bands", unit="band", leave=True, dynamic_ncols=True):
            path = self.fetcher.download_one(item, band, tile_dir, overwrite, verbose)
            res = BAND_RESOLUTIONS.get(band, 10)
            downloaded_paths[band] = {"path": path, "resolution": res}

        if not stack:
            if verbose:
                print("[INFO] Stacking skipped")
            return downloaded_paths, None

        # Decide stacking resolution
        if target_res == "highest":
            stack_func = self.stacker.stack_to_highest_resolution
            if verbose:
                print(f"[INFO] Stacking bands to highest resolution among bands")
        elif isinstance(target_res, (int, float)):
            stack_func = lambda paths, out_file: self.stacker.stack_to_resolution(paths, out_file, target_res)
            if verbose:
                print(f"[INFO] Stacking bands to custom resolution: {target_res}m")
        else:
            stack_func = self.stacker.stack_same_resolution
            if verbose:
                print(f"[INFO] Stacking bands at native resolution")

        date_str = str(item.properties.get("datetime", "unknown")).split("T")[0].replace("-", "")
        band_token = "_".join(bands)
        if target_res == "highest":
            res_label = min([downloaded_paths[b]["resolution"] for b in bands])
        elif isinstance(target_res, (int, float)):
            res_label = target_res
        else:
            res_label = min([downloaded_paths[b]["resolution"] for b in bands])

        stacked_file = os.path.join(tile_dir, f"{band_token}_{date_str}_{res_label}m_stack.tif")
        if os.path.exists(stacked_file) and not overwrite:
            if verbose:
                print(f"[SKIP] Stacked file already exists: {stacked_file}")
            return downloaded_paths, {res_label: stacked_file}

        band_paths = [downloaded_paths[b]["path"] for b in bands]
        stacked_path = stack_func(band_paths, stacked_file)

        return downloaded_paths, {res_label: stacked_path}

    # -----------------------------
    # Multiple tiles downloader
    # -----------------------------
    def download_multiple_tiles(
        self,
        tiles: list,
        preset: str = "RGB",
        stack: bool = True,
        target_res: float | str | None = None,
        overwrite: bool = False
    ):
        all_downloaded = {}
        all_stacked = {}

        for i, tile in enumerate(tiles):
            tile_id = tile.properties.get("sentinel:tile_id", tile.id)
            cloud_cover = tile.properties.get("eo:cloud_cover", "N/A")
            print(f"\n[{i+1}/{len(tiles)}] Downloading tile {tile_id} | cloud: {cloud_cover}%")

            downloaded, stacked = self.download_bands(
                tile,
                preset=preset,
                stack=stack,
                overwrite=overwrite,
                target_res=target_res,
                verbose=True
            )

            all_downloaded[tile_id] = downloaded
            all_stacked[tile_id] = stacked

        return all_downloaded, all_stacked

    # -----------------------------
    # Get least cloudy N tiles
    # -----------------------------
    def get_least_cloudy_tiles(self, bbox, start_date, end_date, max_cloud=20, limit=50, n_tiles=3):
        items = self.find_items(bbox, start_date, end_date, max_cloud=max_cloud, limit=limit)
        if not items:
            raise ValueError("No Sentinel-2 tiles found.")
        sorted_items = sorted(items, key=lambda i: i.properties.get("eo:cloud_cover", 100))
        return sorted_items[:n_tiles]

    # -----------------------------
    # Pretty print STAC items
    # -----------------------------
    def print_tiles(self, tiles: list):
        """
        Nicely print a list of STAC items (tiles).

        Parameters
        ----------
        tiles : list
            List of STAC items
        """
        if not tiles:
            print("[INFO] No tiles to display.")
            return

        print(f"\n{'Index':<5} | {'Tile ID':<15} | {'Date':<12} | {'Cloud %':<8}")
        print("-" * 50)
        for i, tile in enumerate(tiles):
            tile_id = tile.properties.get("sentinel:tile_id", tile.id)
            date = tile.properties.get("datetime", "unknown").split("T")[0]
            cloud = tile.properties.get("eo:cloud_cover", "N/A")
            print(f"{i:<5} | {tile_id:<15} | {date:<12} | {cloud:<8}")
        print("-" * 50)


