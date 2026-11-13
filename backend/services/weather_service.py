import httpx
import logging
from typing import Dict, Any, Optional
from config import config

logger = logging.getLogger(__name__)

async def get_weather(city: str) -> Dict[str, Any]:
    """
    Fetches weather data from OpenWeatherMap.
    """
    if not config.OPENWEATHERMAP_API_KEY:
        logger.warning("OpenWeatherMap API key is missing. Returning mock data.")
        return {
            "temperature": 25.0,
            "humidity": 50,
            "rainfall": 0.0,
            "condition": "Mocked"
        }

    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={config.OPENWEATHERMAP_API_KEY}&units=metric"
    
    async with httpx.AsyncClient(timeout=config.WEATHER_API_TIMEOUT) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            
            return {
                "temperature": data.get("main", {}).get("temp"),
                "humidity": data.get("main", {}).get("humidity"),
                "rainfall": data.get("rain", {}).get("1h", 0.0),
                "condition": data.get("weather", [{}])[0].get("main")
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"Weather API error for {city}: {e.response.status_code}")
            raise Exception(f"Weather service returned error: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Network error while fetching weather for {city}: {str(e)}")
            raise Exception("Weather service is currently unreachable.")

async def get_air_quality(city: str) -> Dict[str, Any]:
    """
    Fetches air quality from OpenAQ v3 API.
    Falls back to reasonable defaults if unavailable.
    """
    # OpenAQ v3 endpoint - search by city name
    url = f"https://api.openaq.org/v3/locations?city={city}&limit=1&country=PK"
    
    async with httpx.AsyncClient(timeout=config.WEATHER_API_TIMEOUT) as client:
        try:
            response = await client.get(url, headers={"Accept": "application/json"})
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
            if not results:
                return {"aqi": 75, "pollution": "Data unavailable"}
            
            location_id = results[0]["id"]
            
            # Get latest measurements for this location
            meas_url = f"https://api.openaq.org/v3/locations/{location_id}/latest"
            meas_r = await client.get(meas_url, headers={"Accept": "application/json"})
            meas_r.raise_for_status()
            meas_data = meas_r.json()
            
            measurements = meas_data.get("results", [])
            pm25 = next(
                (m["value"] for m in measurements if m.get("parameter", {}).get("name") == "pm25"),
                20.0
            )
            # Rough US AQI from PM2.5
            aqi = int(min(pm25 * 4, 500))
            
            return {
                "aqi": aqi,
                "pollution": {m.get("parameter", {}).get("name", "unknown"): m.get("value") for m in measurements}
            }
        except Exception as e:
            logger.error(f"OpenAQ v3 error for {city}: {e}")
            return {"aqi": 75, "pollution": "Data unavailable"}
