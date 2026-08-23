"""
Reverse geocoding via OpenStreetMap Nominatim — free, no key, but rate
limited (~1 req/sec) and asks for a descriptive User-Agent. Fine for a
prototype; swap for Google Geocoding API or a self-hosted Nominatim
instance if you need volume.

We deliberately round coordinates before returning them for storage —
district-level aggregation doesn't need (and shouldn't keep) exact
farm-level GPS precision.
"""
import httpx

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"

HEADERS = {"User-Agent": "crop-disease-early-warning-prototype/0.1"}


async def reverse_geocode(lat: float, lon: float) -> dict:
    params = {"lat": lat, "lon": lon, "format": "jsonv2", "zoom": 8}
    try:
        async with httpx.AsyncClient(timeout=10.0, headers=HEADERS) as client:
            resp = await client.get(NOMINATIM_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, httpx.TimeoutException):
        return {"district": "Unknown", "state": None}

    addr = data.get("address", {})
    district = (
        addr.get("state_district")
        or addr.get("county")
        or addr.get("city")
        or addr.get("town")
        or "Unknown"
    )
    state = addr.get("state")
    return {"district": district, "state": state}


def round_coords(lat: float, lon: float, precision: int = 2) -> tuple:
    """Round to ~1.1km precision at precision=2 — enough for a district
    heatmap, not enough to pin an individual farm."""
    return round(lat, precision), round(lon, precision)
