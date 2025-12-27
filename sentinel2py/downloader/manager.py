# sentinel2py/downloader/manager.py

import os
from typing import List
from pystac_client import Client
import planetary_computer
from tqdm.auto import tqdm

from .config import BAND_PRESETS, BAND_RESOLUTIONS
from .fetch import BandFetcher
from .stacker import BandStacker
from .selector import SentinelSelector


class Sentinel2Manager:
    """High-level manager: search → select → download → stack Sentinel-2 tiles."""

    def __init__(self, out_dir: str = "./data"):
        self.out_dir = out_dir
        self.fetcher = BandFetcher()
        self.stacker = BandStacker()
        self.selector = SentinelSelector()
        self.catalog_url = "https://planetarycomputer.microsoft.com/api/stac/v1"

    # -------------------------------------------------------
    # SEARCH
    # -------------------------------------------------------
    def find_items(self, bbox, start, end, max_cloud=20, limit=10) -> List:
        """Query STAC for Sentinel-2 tiles."""
        catalog = Client.open(self.catalog_url)
        search = catalog.search(
            collections=["sentinel-2-l2a"],
            bbox=bbox,
            datetime=f"{start}/{end}",
            query={"eo:cloud_cover": {"lt": max_cloud}},
            limit=limit,
        )
        return [planetary_computer.sign(item) for item in search.get_items()]

    # -------------------------------------------------------
    # TILE SELECTION
    # -------------------------------------------------------
    def select_best(self, items: List, method="least_cloudy", **kwargs):
        """Choose a tile using selection logic."""
        if not items:
            raise ValueError("No items provided for selection.")

        if method == "least_cloudy":
            return self.selector.least_cloudy(items)

        if method == "by_index":
            index = kwargs.get("index")
            if index is None:
                raise ValueError("Please provide index=")
            return self.selector.by_index(items, index)

        if method == "by_date":
            date = kwargs.get("date")
            if date is None:
                raise ValueError("Provide date='YYYY-MM-DD'")
            m = self.selector.by_date(items, date)
            if not m:
                raise ValueError(f"No tiles found for date {date}")
            return m[0]

        raise ValueError(f"Unknown method: {method}")

    # -------------------------------------------------------
    # GET TOP-N LEAST CLOUDY TILES
    # -------------------------------------------------------
    def get_least_cloudy_tiles(self, bbox, start, end, max_cloud=20, limit=50, n_tiles=3):
        items = self.find_items(bbox, start, end, max_cloud=max_cloud, limit=limit)
        if not items:
            raise ValueError("No Sentinel-2 tiles found.")

        sorted_tiles = sorted(items, key=lambda i: i.properties.get("eo:cloud_cover", 100))
        return sorted_tiles[:n_tiles]

    # -------------------------------------------------------
    # DOWNLOAD SINGLE TILE (bands + optional stack)
    # -------------------------------------------------------
    def download_bands(
        self,
        item,
        preset="RGB",
        stack=True,
        overwrite=False,
        target_res=None,
        verbose=True
    ):
        """
        Download all bands in a preset into:
        ./data/<full_tile_id>/...
        and optionally create a single stack file.
        """

        if preset not in BAND_PRESETS:
            raise ValueError(f"Preset '{preset}' not found. Available: {list(BAND_PRESETS.keys())}")

        bands = BAND_PRESETS[preset]

        # Folder name = full STAC item id
        tile_full_id = item.id                             # ex. S2A_MSIL2A_20230628T102601_R108_T31TGM_20241003T161149
        tile_short = item.id.split("_")[-2]                # ex. T31TGM
        tile_dir = os.path.join(self.out_dir, tile_full_id)
        os.makedirs(tile_dir, exist_ok=True)

        if verbose:
            print(f"[INFO] Downloading {len(bands)} bands → {tile_dir}")

        downloaded_paths = {}
        for band in tqdm(bands, desc="Downloading Bands", unit="band", dynamic_ncols=True):
            path = self.fetcher.download_one(item, band, tile_dir, overwrite, verbose=False)
            res = BAND_RESOLUTIONS.get(band, 10)
            downloaded_paths[band] = {"path": path, "resolution": res}

        if not stack:
            return downloaded_paths, None

        # Determine resolution label for stacked output
        if target_res == "highest":
            res_label = min([v["resolution"] for v in downloaded_paths.values()])
            stack_func = self.stacker.stack_to_highest_resolution
        elif isinstance(target_res, (int, float)):
            res_label = target_res
            stack_func = lambda paths, outfile: self.stacker.stack_to_resolution(paths, outfile, target_res)
        else:
            # default: same resolution stack
            res_label = min([v["resolution"] for v in downloaded_paths.values()])
            stack_func = self.stacker.stack_same_resolution

        # Build final stack filename
        # Example: B02_B03_B04_20230628_T31TGM_10m_stack.tif
        date_str = str(item.properties.get("datetime", "unknown")).split("T")[0].replace("-", "")
        band_token = "_".join(bands)
        out_stack = os.path.join(tile_dir, f"{band_token}_{date_str}_{tile_short}_{res_label}m_stack.tif")

        # Skip if already exists
        if os.path.exists(out_stack) and not overwrite:
            if verbose:
                print(f"[SKIP] Already exists → {out_stack}")
            return downloaded_paths, {res_label: out_stack}

        band_list = [downloaded_paths[b]["path"] for b in bands]
        stacked_path = stack_func(band_list, out_stack)

        return downloaded_paths, {res_label: stacked_path}

    # -------------------------------------------------------
    # DOWNLOAD MULTIPLE TILES
    # -------------------------------------------------------
    def download_multiple_tiles(
        self,
        tiles,
        preset="RGB",
        stack=True,
        target_res=None,
        overwrite=False
    ):
        all_downloaded = {}
        all_stacked = {}

        for i, tile in enumerate(tiles):
            full_id = tile.id
            short_id = tile.id.split("_")[-2]
            clouds = tile.properties.get("eo:cloud_cover", "N/A")

            print(f"\n[{i+1}/{len(tiles)}] Tile {short_id}  (cloud={clouds}%)")

            downloaded, stacked = self.download_bands(
                tile,
                preset=preset,
                stack=stack,
                overwrite=overwrite,
                target_res=target_res,
                verbose=True
            )

            all_downloaded[full_id] = downloaded
            all_stacked[full_id] = stacked

        return all_downloaded, all_stacked
