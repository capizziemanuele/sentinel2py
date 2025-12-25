# sentinel2py/downloader/manager.py
import os
from typing import List, Union
from .search import SentinelSearch
from .selector import SentinelSelector
from .fetch import BandFetcher
from .stacker import BandStacker

class Sentinel2Manager:
    """
    High-level manager for searching, selecting, downloading, and stacking Sentinel-2 tiles.
    """

    def __init__(self, out_dir: str = "./data"):
        self.out_dir = out_dir
        os.makedirs(out_dir, exist_ok=True)
        self.searcher = SentinelSearch()
        self.selector = SentinelSelector()
        self.fetcher = BandFetcher()
        self.stacker = BandStacker()

    def find_items(self, bbox: List[float], start_date: str, end_date: str, max_cloud_cover: int = 20, limit: int = 50):
        """Search for tiles matching criteria."""
        return self.searcher.search(bbox, start_date, end_date, max_cloud_cover, limit)

    def select_best(self, items, method: str = "least_cloudy", index: int = 0):
        """Select best tile using specified method."""
        if method == "least_cloudy":
            item = self.selector.least_cloudy(items)
            cloud = item.properties.get("eo:cloud_cover", "unknown")
            print(f"[SELECT] Least cloudy tile: {item.id}, Cloud: {cloud}%")
            return item
        elif method == "index":
            item = self.selector.by_index(items, index)
            print(f"[SELECT] Tile by index {index}: {item.id}")
            return item
        else:
            raise ValueError("Invalid selection method")

    def download_bands(self, item, bands: List[str], stack_strategy: Union[str, float] = "same") -> List[str]:
        """
        Download specified bands and optionally stack them.
        stack_strategy: "same", "highest", or numeric resolution
        """
        tile_id = item.properties.get("sentinel:tile_id", item.id)
        tile_dir = os.path.join(self.out_dir, tile_id)
        os.makedirs(tile_dir, exist_ok=True)

        print(f"[DOWNLOAD] Downloading {len(bands)} bands for tile {tile_id}")
        band_paths_dict = self.fetcher.download_list(item, bands, tile_dir)
        band_paths = list(band_paths_dict.values())

        if stack_strategy:
            stack_path = os.path.join(tile_dir, f"{'_'.join(bands)}_stack.tif")
            print(f"[STACK] Using strategy: {stack_strategy}")
            if stack_strategy == "same":
                return [self.stacker.stack_same_resolution(band_paths, stack_path)]
            elif stack_strategy == "highest":
                return [self.stacker.stack_to_highest_resolution(band_paths, stack_path)]
            elif isinstance(stack_strategy, (int, float)):
                return [self.stacker.stack_to_resolution(band_paths, stack_path, stack_strategy)]
        return band_paths
