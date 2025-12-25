# sentinel2py/downloader/selector.py
from typing import List

class SentinelSelector:
    """
    Select Sentinel-2 items based on different criteria.
    """

    @staticmethod
    def by_index(items: List, index: int):
        """Select an item by its index in the list."""
        if index < 0 or index >= len(items):
            raise IndexError(f"Index {index} out of bounds")
        return items[index]

    @staticmethod
    def least_cloudy(items: List):
        """Select the item with the lowest cloud cover."""
        return min(items, key=lambda x: x.properties.get("eo:cloud_cover", 100))

    @staticmethod
    def by_date(items: List, date: str):
        """Return items matching exact date string (YYYY-MM-DD)."""
        return [i for i in items if i.properties.get("datetime", "").startswith(date)]
