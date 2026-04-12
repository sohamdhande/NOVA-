"""
NOVA Weather Tool — Phase B
Fetches real-time weather data via Open-Meteo (free, no API key).
Geocodes arbitrary locations via Nominatim.
"""

import httpx
from llm import _chat


# ── Default coordinates (Pune, India) ─────────────────────────
_DEFAULT_LAT = 18.5204
_DEFAULT_LNG = 73.8567
_DEFAULT_LOCATION = "Pune, India"

# ── WMO Weather Code → human-readable condition ──────────────
_WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    56: "Light freezing drizzle", 57: "Dense freezing drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    66: "Light freezing rain", 67: "Heavy freezing rain",
    71: "Slight snowfall", 73: "Moderate snowfall", 75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
}


async def _geocode(location: str) -> tuple[float, float, str]:
    """Resolve a location name into (lat, lng, display_name) via Nominatim."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": location, "format": "json", "limit": 1},
            headers={"User-Agent": "NOVA-Weather/1.0"},
        )
        resp.raise_for_status()
        data = resp.json()
        if not data:
            raise ValueError(f"Could not geocode location: {location}")
        entry = data[0]
        return float(entry["lat"]), float(entry["lon"]), entry.get("display_name", location)


async def get_weather(location: str = _DEFAULT_LOCATION) -> dict:
    """
    Fetch current weather for *location*.

    Returns dict with keys:
        temp, feels_like, condition, humidity, wind, location
    """
    # Resolve coordinates
    if location.lower().strip() in ("pune", "pune, india", "pune india"):
        lat, lng, display = _DEFAULT_LAT, _DEFAULT_LNG, "Pune, India"
    else:
        lat, lng, display = await _geocode(location)

    # Call Open-Meteo
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lng,
                "current": "temperature_2m,apparent_temperature,weathercode,windspeed_10m,relativehumidity_2m",
                "timezone": "Asia/Kolkata",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    current = data.get("current", {})
    weather_code = current.get("weathercode", 0)

    return {
        "temp": current.get("temperature_2m"),
        "feels_like": current.get("apparent_temperature"),
        "condition": _WMO_CODES.get(weather_code, f"Code {weather_code}"),
        "humidity": current.get("relativehumidity_2m"),
        "wind": current.get("windspeed_10m"),
        "location": display,
    }


async def weather_summary(location: str = _DEFAULT_LOCATION) -> str:
    """
    Return a concise, LLM-crafted weather briefing for *location*.
    """
    try:
        data = await get_weather(location)
    except Exception as e:
        return f"⚠ Unable to fetch weather for {location}: {e}"

    user_prompt = (
        f"Location: {data['location']}\n"
        f"Temperature: {data['temp']}°C (feels like {data['feels_like']}°C)\n"
        f"Condition: {data['condition']}\n"
        f"Humidity: {data['humidity']}%\n"
        f"Wind: {data['wind']} km/h"
    )

    from core.personality import get_system_prefix
    system_prompt = get_system_prefix() + "\n\n" + (
        "Give a concise weather briefing in 2-3 lines. "
        "Include temperature, condition, and one practical tip "
        "(e.g. carry umbrella, stay hydrated). No fluff."
    )

    try:
        return _chat(system=system_prompt, user=user_prompt).strip()
    except Exception:
        # Deterministic fallback
        tip = ""
        code_val = data.get("condition", "").lower()
        if "rain" in code_val or "drizzle" in code_val or "shower" in code_val:
            tip = "Carry an umbrella."
        elif data["temp"] and data["temp"] > 35:
            tip = "Stay hydrated."
        elif data["temp"] and data["temp"] < 10:
            tip = "Dress warmly."
        else:
            tip = "Enjoy your day."

        return (
            f"🌤 {data['location']}: {data['temp']}°C, {data['condition']}. "
            f"Humidity {data['humidity']}%, wind {data['wind']} km/h. {tip}"
        )
