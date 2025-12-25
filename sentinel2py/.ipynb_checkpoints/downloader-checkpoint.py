import os
import requests

AWS_BASE = "https://roda.sentinel-hub.com/sentinel-s2-l2a"

def download_band(tile_id: str, band: str, out_dir: str = "./data"):
    """
    Download a single Sentinel-2 band (.jp2) from AWS open data.
    
    Example band: B04, B08, B02
    """
    os.makedirs(out_dir, exist_ok=True)
    url = f"{AWS_BASE}/{tile_id}/GRANULE/*/IMG_DATA/{band}.jp2"
    out_path = os.path.join(out_dir, f"{tile_id}_{band}.jp2")

    print(f"Downloading {band}...")
    response = requests.get(url, stream=True)

    if response.status_code != 200:
        raise RuntimeError(f"Failed to download: {url}")

    with open(out_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    return out_path
