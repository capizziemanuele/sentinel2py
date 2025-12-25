# sentinel2py/downloader/config.py

BAND_PRESETS = {
    "RGB": ["B04", "B03", "B02"],
    "VISUAL": ["visual"],
    "NIR": ["B08"],
    "NDVI": ["B08", "B04"],
    "NDWI": ["B03", "B08"],
    "SWIR": ["B11", "B12"],
    "RE_ALL": ["B05", "B06", "B07", "B8A"],
    "ALL_10M": ["B02", "B03", "B04", "B08"],
    "ALL_20M": ["B05", "B06", "B07", "B8A", "B11", "B12"],
    "ALL_60M": ["B01", "B09", "B10"],
    "ALL_BANDS": ["B01","B02","B03","B04","B05","B06","B07","B08","B8A","B09","B10","B11","B12","SCL"]
}

BAND_RESOLUTIONS = {
    "B01": 60, "B02": 10, "B03": 10, "B04": 10,
    "B05": 20, "B06": 20, "B07": 20, "B08": 10,
    "B8A": 20, "B09": 60, "B10": 60, "B11": 20,
    "B12": 20, "SCL": 60
}
