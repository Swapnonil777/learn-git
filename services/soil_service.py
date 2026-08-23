"""
Soil properties via ISRIC SoilGrids v2.0 REST API — free, no key required.
Docs: https://rest.isric.org/soilgrids/v2.0/docs
Returns properties at the 0-5cm depth layer, which is what matters most
for surface fungal/bacterial disease pressure.

Note: SoilGrids is a global model (250m resolution), not ground-truthed
soil sensor data — good enough for a prototype, but call this out to users.
Swap-in path: national soil survey APIs, or real IoT soil sensors once
farmers have them (the whole point of this system is to work without them).
"""
import httpx

SOILGRIDS_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"


async def get_soil_snapshot(lat: float, lon: float) -> dict:
    params = {
        "lon": lon,
        "lat": lat,
        "property": ["phh2o", "soc", "nitrogen"],
        "depth": "0-5cm",
        "value": "mean",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(SOILGRIDS_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, httpx.TimeoutException):
        return {"ph": None, "organic_carbon_g_kg": None, "nitrogen_g_kg": None}

    result = {"ph": None, "organic_carbon_g_kg": None, "nitrogen_g_kg": None}
    try:
        layers = data["properties"]["layers"]
        for layer in layers:
            name = layer["name"]
            depths = layer.get("depths", [])
            if not depths:
                continue
            mean_val = depths[0]["values"].get("mean")
            if mean_val is None:
                continue
            # SoilGrids returns scaled integer values; d_factor un-scales them.
            d_factor = layer.get("unit_measure", {}).get("d_factor", 1)
            actual = mean_val / d_factor
            if name == "phh2o":
                result["ph"] = round(actual, 2)
            elif name == "soc":
                result["organic_carbon_g_kg"] = round(actual, 2)
            elif name == "nitrogen":
                result["nitrogen_g_kg"] = round(actual, 2)
    except (KeyError, IndexError, TypeError, ZeroDivisionError):
        pass

    return result
