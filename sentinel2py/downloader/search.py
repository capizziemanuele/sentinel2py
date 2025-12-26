# sentinel2py/downloader/search.py

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import planetary_computer
from pystac_client import Client
from requests.exceptions import RequestException
from tqdm import tqdm
import time

log = logging.getLogger(__name__)
ENDPOINT = "https://planetarycomputer.microsoft.com/api/stac/v1"


class SearchError(Exception):
    """Custom exception for search failures."""
    pass


class SentinelSearch:
    """
    Search Sentinel-2 L2A imagery using Planetary Computer STAC API.
    Supports filtering, retries, metadata return, and signed-item output.
    """

    def __init__(self, endpoint: str = ENDPOINT, retries: int = 3, timeout: int = 5):
        self.endpoint = endpoint
        self.retries = retries
        self.timeout = timeout
        self.client = self._connect()

    # -------------------------
    # INTERNAL CONNECTION
    # -------------------------
    def _connect(self) -> Client:
        for attempt in range(1, self.retries + 1):
            try:
                return Client.open(self.endpoint)
            except RequestException:
                log.warning(f"[SEARCH] Failed connecting to STAC endpoint. Retry {attempt}/{self.retries}")
                time.sleep(self.timeout)
        raise SearchError(f"Could not connect to STAC endpoint {self.endpoint}")

    # -------------------------
    # MAIN SEARCH METHOD
    # -------------------------
    def search(
        self,
        bbox: List[float],
        start_date: str,
        end_date: str,
        max_cloud_cover: float = 20.0,
        limit: int = 50,
        sign: bool = True,
        filter_10m_only: bool = False,
    ) -> List:
        """
        Run search query and return list of items.

        Parameters
        ----------
        bbox : [west, south, east, north]
        start_date : YYYY-MM-DD
        end_date : YYYY-MM-DD
        sign : bool
            Automatically sign items for authenticated download
        filter_10m_only : bool
            Remove items without required 10m-resolution bands
        """
        log.info(
            f"[SEARCH] bbox={bbox}, date={start_date}->{end_date}, cloud<{max_cloud_cover}, limit={limit}"
        )

        search = self.client.search(
            collections=["sentinel-2-l2a"],
            bbox=bbox,
            datetime=f"{start_date}/{end_date}",
            query={"eo:cloud_cover": {"lt": max_cloud_cover}},
            limit=limit
        )

        try:
            items = list(search.items())
        except Exception as e:
            raise SearchError(f"Failed querying STAC: {e}")

        if filter_10m_only:
            items = [i for i in items if {"B02", "B03", "B04", "B08"}.issubset(i.assets.keys())]

        log.info(f"[SEARCH] Found {len(items)} items")

        # Optional signing
        if sign:
            return [planetary_computer.sign(i) for i in items]
        return items

    # -------------------------
    # UTILITIES
    # -------------------------
    @staticmethod
    def metadata(items: List) -> List[Dict[str, Any]]:
        """Return structured metadata instead of printing."""
        return [
            {
                "index": i,
                "tile": it.properties.get("sentinel:tile_id", it.id),
                "date": it.properties.get("datetime", "").split("T")[0],
                "cloud": it.properties.get("eo:cloud_cover", None),
            }
            for i, it in enumerate(items)
        ]

    @staticmethod
    def print_metadata(items: List) -> None:
        """Pretty print list metadata."""
        tqdm.write("\n🛰️ Sentinel-2 Results:\n-----------------------------------")
        for m in SentinelSearch.metadata(items):
            tqdm.write(
                f"[{m['index']}] Tile={m['tile']} | "
                f"Date={m['date']} | Cloud={m['cloud']}%"
            )
        tqdm.write("-----------------------------------\n")

    # -------------------------
    # HIGH-LEVEL "GET BEST" API
    # -------------------------
    def search_best(
        self,
        bbox: List[float],
        start_date: str,
        end_date: str,
        max_cloud_cover: float = 20.0,
        limit: int = 30
    ):
        """
        Single-shot: search → sort least-cloudy → return best tile
        """
        items = self.search(bbox, start_date, end_date, max_cloud_cover, limit)
        if not items:
            raise SearchError("No items returned in search.")
        best = min(items, key=lambda x: x.properties.get("eo:cloud_cover", 100))
        log.info(f"[SEARCH] Best item '{best.id}', cloud={best.properties.get('eo:cloud_cover')}%")
        return best
