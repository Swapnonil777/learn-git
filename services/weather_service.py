"""
Weather via Open-Meteo (https://open-meteo.com) — free, no API key.
Gives current conditions + a 7-day forecast, which we use both to snapshot
"today" and to estimate whether humidity is trending up (favors fungal
spread) or down.

Swap-in path for production: a paid provider (Tomorrow.io, OpenWeather)
for higher resolution / hyperlocal data, or a national met department API.
"""
import httpx

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


async def get_weather_snapshot(lat: float, lon: float) -> dict:
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,precipitation",
        "daily": "relative_humidity_2m_mean,precipitation_sum",
        "forecast_days": 7,
        "timezone": "auto",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(OPEN_METEO_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, httpx.TimeoutException):
        # Network/API failure shouldn't crash a diagnosis — degrade gracefully.
        return {
            "temperature_c": None,
            "humidity_pct": None,
            "rainfall_mm_7d": None,
            "forecast_humidity_trend": None,
        }

    current = data.get("current", {})
    daily = data.get("daily", {})

    humidity_series = daily.get("relative_humidity_2m_mean", [])
    rainfall_series = daily.get("precipitation_sum", [])

    trend = "stable"
    if len(humidity_series) >= 4:
        first_half_avg = sum(humidity_series[:3]) / 3
        second_half_avg = sum(humidity_series[-3:]) / 3
        if second_half_avg - first_half_avg > 5:
            trend = "rising"
        elif first_half_avg - second_half_avg > 5:
            trend = "falling"

    return {
        "temperature_c": current.get("temperature_2m"),
        "humidity_pct": current.get("relative_humidity_2m"),
        "rainfall_mm_7d": round(sum(rainfall_series), 1) if rainfall_series else None,
        "forecast_humidity_trend": trend,
    }
