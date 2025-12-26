# sentinel2py/downloader/selector.py

from typing import List, Optional, Any
from datetime import datetime
from tqdm import tqdm


class SelectionError(Exception):
    """Custom exception for invalid Sentinel item selections."""
    pass


class SentinelSelector:
    """
    Utility class for selecting Sentinel-2 STAC items based on:
        - index
        - cloud cover
        - date / date range
        - sorting

    All methods return either a single item or a filtered list.
    """

    # -------------------------
    # INTERNAL VALIDATORS
    # -------------------------
    @staticmethod
    def _ensure_items(items: List[Any]) -> None:
        if not items:
            raise SelectionError("No Sentinel-2 items available for selection.")

    @staticmethod
    def _get_date_str(item) -> str:
        """Extract YYYY-MM-DD date from item."""
        dt = item.properties.get("datetime", None)
        if not dt:
            return "unknown"
        return dt.split("T")[0]

    @staticmethod
    def _get_cloud(item) -> float:
        return float(item.properties.get("eo:cloud_cover", 100.0))

    # -------------------------
    # PUBLIC SELECTION METHODS
    # -------------------------
    @staticmethod
    def by_index(items: List[Any], index: int):
        """Return item at given index, raise if invalid."""
        SentinelSelector._ensure_items(items)
        try:
            return items[index]
        except IndexError:
            raise SelectionError(f"Index '{index}' is out of bounds (items={len(items)})")

    @staticmethod
    def least_cloudy(items: List[Any]):
        """Return item with lowest cloud cover."""
        SentinelSelector._ensure_items(items)
        return min(items, key=SentinelSelector._get_cloud)

    @staticmethod
    def by_date(items: List[Any], date: str) -> List[Any]:
        """
        Filter items matching YYYY-MM-DD.
        Returns list (can be empty).
        """
        SentinelSelector._ensure_items(items)
        return [i for i in items if SentinelSelector._get_date_str(i) == date]

    @staticmethod
    def by_date_range(items: List[Any], start: str, end: str) -> List[Any]:
        """
        Return items inside date interval inclusive.
        Expects format YYYY-MM-DD.
        """
        SentinelSelector._ensure_items(items)
        s = datetime.fromisoformat(start)
        e = datetime.fromisoformat(end)

        return [
            i for i in items
            if (d := datetime.fromisoformat(SentinelSelector._get_date_str(i))) >= s and d <= e
        ]

    @staticmethod
    def sort_by_cloud(items: List[Any], ascending: bool = True) -> List[Any]:
        """Return list sorted by cloud %."""
        SentinelSelector._ensure_items(items)
        return sorted(items, key=SentinelSelector._get_cloud, reverse=not ascending)

    @staticmethod
    def sort_by_date(items: List[Any], ascending: bool = True) -> List[Any]:
        """Sort by datetime field."""
        SentinelSelector._ensure_items(items)
        return sorted(items, key=lambda x: SentinelSelector._get_date_str(x), reverse=not ascending)

    # -------------------------
    # METADATA OUTPUT
    # -------------------------
    @staticmethod
    def metadata(items: List[Any]) -> List[dict]:
        """
        Return standardized metadata list instead of printing raw text.
        Enables logging, tests, or table formatting.
        """
        SentinelSelector._ensure_items(items)
        return [
            {
                "index": i,
                "tile": item.properties.get("sentinel:tile_id", item.id),
                "date": SentinelSelector._get_date_str(item),
                "cloud_cover": SentinelSelector._get_cloud(item)
            }
            for i, item in enumerate(items)
        ]

    @staticmethod
    def print_metadata(items: List[Any]) -> None:
        """Pretty print metadata in human-readable format."""
        data = SentinelSelector.metadata(items)

        tqdm.write("\n🛰️ Sentinel-2 Item Summary\n---------------------------")
        for d in data:
            tqdm.write(
                f"[{d['index']}] Tile: {d['tile']} | Date: {d['date']} | Cloud: {d['cloud_cover']}%"
            )
        tqdm.write("---------------------------\n")
