# sentinel2py/downloader/search.py
from pystac_client import Client
from typing import List
import logging

log = logging.getLogger(__name__)
ENDPOINT = "https://planetarycomputer.microsoft.com/api/stac/v1"

class SentinelSearch:
    """
    Search Sentinel-2 L2A imagery on Microsoft Planetary Computer via STAC API.
    """

    def __init__(self, endpoint: str = ENDPOINT):
        self.client = Client.open(endpoint)

    def search(
        self, bbox: List[float], start_date: str, end_date: str, max_cloud_cover: int = 20, limit: int = 50
    ) -> List:
        """
        Search Sentinel-2 L2A items by bounding box, date range, cloud cover, and limit.
        """
        log.info(f"[SEARCH] bbox={bbox}, dates={start_date} -> {end_date}, max_cloud={max_cloud_cover}%")
        search = self.client.search(
            collections=["sentinel-2-l2a"],
            bbox=bbox,
            datetime=f"{start_date}/{end_date}",
            query={"eo:cloud_cover": {"lt": max_cloud_cover}},
            limit=limit
        )
        items = list(search.items())
        log.info(f"[SEARCH] Found {len(items)} items")
        return items

    @staticmethod
    def describe_items(items: List) -> None:
        """
        Print basic metadata for user inspection.
        """
        for i, item in enumerate(items):
            tile = item.properties.get("sentinel:tile_id", item.id)
            date = item.properties.get("datetime", "unknown")
            cloud = item.properties.get("eo:cloud_cover", "unknown")
            print(f"[{i}] Tile: {tile} | Date: {date} | Cloud cover: {cloud}%")
