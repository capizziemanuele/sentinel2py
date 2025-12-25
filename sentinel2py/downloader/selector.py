from typing import List

class SentinelSelector:
    """Select Sentinel-2 items based on different criteria."""

    @staticmethod
    def by_index(items: List, index: int):
        if index < 0 or index >= len(items):
            raise IndexError(f"Index {index} out of bounds")
        return items[index]

    @staticmethod
    def least_cloudy(items: List):
        return min(items, key=lambda x: x.properties.get("eo:cloud_cover", 100))

    @staticmethod
    def by_date(items: List, date: str):
        return [i for i in items if i.properties.get("datetime", "").startswith(date)]

    @staticmethod
    def print_metadata(items: List):
        for i, item in enumerate(items):
            tile = item.properties.get("sentinel:tile_id", item.id)
            date = item.properties.get("datetime", "unknown")
            cloud = item.properties.get("eo:cloud_cover", "unknown")
            print(f"[{i}] Tile: {tile} | Date: {date} | Cloud cover: {cloud}%")
