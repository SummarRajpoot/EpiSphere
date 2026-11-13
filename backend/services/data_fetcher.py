import json
import logging
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from models import Region
from routes.regions import calculate_risk, generate_recommendations

logger = logging.getLogger("uvicorn.error")

DISEASE_SH_URL = "https://disease.sh/v3/covid-19/countries/Pakistan"
OPENWEATHER_WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
OPENWEATHER_AQI_URL = "https://api.openweathermap.org/data/2.5/air_pollution"

FALLBACK_NATIONAL = {
    "active": 15000,
    "cases": 0,
    "recovered": 0,
    "todayCases": 0,
}
FALLBACK_WEATHER = {"temp": 32.0, "humidity": 60, "rainfall": 1.0, "aqi": 80}

CITIES: List[Dict[str, Any]] = [
    {"name": "Karachi", "share": 0.264, "lat": 24.86, "lon": 67.01, "pop_density": 26000},
    {"name": "Lahore", "share": 0.215, "lat": 31.55, "lon": 74.34, "pop_density": 8700},
    {"name": "Islamabad", "share": 0.018, "lat": 33.69, "lon": 73.06, "pop_density": 1800},
    {"name": "Peshawar", "share": 0.036, "lat": 34.01, "lon": 71.58, "pop_density": 5000},
    {"name": "Quetta", "share": 0.016, "lat": 30.19, "lon": 67.00, "pop_density": 2000},
    {"name": "Multan", "share": 0.031, "lat": 30.20, "lon": 71.47, "pop_density": 4500},
]


def _build_history(current: int) -> List[int]:
    """Build a 7-day ascending history ending at the current case count."""
    if current <= 0:
        return [0] * 7
    start = current * 0.5
    step = (current - start) / 6
    hist = [int(start + step * i) for i in range(6)]
    hist.append(int(current))
    return hist


def _format_trend(new_value: int, old_value: int) -> str:
    if old_value <= 0:
        return "+0%"
    change = ((new_value - old_value) / old_value) * 100
    sign = "+" if change >= 0 else ""
    return f"{sign}{change:.1f}%"


def infer_disease(temp: float, humidity: float, rainfall: float, aqi: float) -> str:
    if humidity > 60 and rainfall > 2:
        return "Dengue"
    if temp > 38:
        return "Heatstroke"
    if aqi > 150:
        return "Asthma / Respiratory Issues"
    if temp < 15 and humidity > 50:
        return "Influenza"
    return "Typhoid"


def _aqi_from_openweather(payload: Dict[str, Any]) -> int:
    """Convert OpenWeather air-pollution payload into an approximate AQI number."""
    entries = payload.get("list") or []
    if not entries:
        return FALLBACK_WEATHER["aqi"]
    components = entries[0].get("components") or {}
    pm25 = components.get("pm2_5")
    if pm25 is not None:
        return int(float(pm25) * 2)
    raw_aqi = (entries[0].get("main") or {}).get("aqi")
    if raw_aqi is None:
        return FALLBACK_WEATHER["aqi"]
    # OpenWeather AQI is 1-5; scale it so downstream thresholds still work.
    return int(raw_aqi) * 50


async def fetch_pakistan_covid(client: httpx.AsyncClient) -> Dict[str, Any]:
    try:
        response = await client.get(DISEASE_SH_URL, timeout=config.WEATHER_API_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return {
            "active": int(data.get("active") or FALLBACK_NATIONAL["active"]),
            "cases": int(data.get("cases") or 0),
            "recovered": int(data.get("recovered") or 0),
            "todayCases": int(data.get("todayCases") or 0),
        }
    except Exception as exc:
        logger.error("disease.sh fetch failed: %s", exc)
        return dict(FALLBACK_NATIONAL)


async def fetch_city_weather(
    client: httpx.AsyncClient,
    city: Dict[str, Any],
    api_key: Optional[str],
) -> Dict[str, float]:
    if not api_key:
        logger.warning("OPENWEATHERMAP_API_KEY missing; using fallback weather for %s", city["name"])
        return dict(FALLBACK_WEATHER)

    weather = dict(FALLBACK_WEATHER)
    try:
        weather_resp = await client.get(
            OPENWEATHER_WEATHER_URL,
            params={"q": f"{city['name']},PK", "appid": api_key, "units": "metric"},
            timeout=config.WEATHER_API_TIMEOUT,
        )
        weather_resp.raise_for_status()
        payload = weather_resp.json()
        weather["temp"] = float(payload.get("main", {}).get("temp", FALLBACK_WEATHER["temp"]))
        weather["humidity"] = float(payload.get("main", {}).get("humidity", FALLBACK_WEATHER["humidity"]))
        weather["rainfall"] = float(payload.get("rain", {}).get("1h", 0.0) or 0.0)
    except Exception as exc:
        logger.error("Weather fetch failed for %s: %s", city["name"], exc)

    try:
        aqi_resp = await client.get(
            OPENWEATHER_AQI_URL,
            params={"lat": city["lat"], "lon": city["lon"], "appid": api_key},
            timeout=config.WEATHER_API_TIMEOUT,
        )
        aqi_resp.raise_for_status()
        weather["aqi"] = float(_aqi_from_openweather(aqi_resp.json()))
    except Exception as exc:
        logger.error("AQI fetch failed for %s: %s", city["name"], exc)

    return weather


async def fetch_and_update_all(db: AsyncSession) -> Dict[str, Any]:
    """
    Fetch live national COVID + city weather data and upsert Region rows.
    """
    logger.info("[data_fetcher] Starting live data refresh …")
    api_key = config.OPENWEATHERMAP_API_KEY
    updated = []

    async with httpx.AsyncClient() as client:
        national = await fetch_pakistan_covid(client)
        national_active = national.get("active") or FALLBACK_NATIONAL["active"]

        for city in CITIES:
            try:
                weather = await fetch_city_weather(client, city, api_key)
                active_cases = int(national_active * city["share"])
                patients = active_cases * 3
                disease = infer_disease(
                    weather["temp"],
                    weather["humidity"],
                    weather["rainfall"],
                    weather["aqi"],
                )

                result = await db.execute(select(Region).where(Region.city.ilike(city["name"])))
                region = result.scalars().first()

                pop_density = float(city["pop_density"])
                hosp_capacity = region.hospital_capacity if region else None
                vax_rate = region.vaccination_rate if region else None
                risk = calculate_risk(patients, disease, pop_density, hosp_capacity, vax_rate)
                recs = generate_recommendations(risk, disease, hosp_capacity, vax_rate)

                if region:
                    old_cases = region.active_cases or 0
                    old_patients = region.patients or 0
                    region.active_trend = _format_trend(active_cases, old_cases)
                    region.patients_trend = _format_trend(patients, old_patients)
                    region.last_week_cases = old_cases

                    history = json.loads(region.history) if region.history else [0] * 7
                    if not isinstance(history, list):
                        history = [0] * 7
                    while len(history) < 7:
                        history.insert(0, 0)
                    history = history[-7:]
                    history.pop(0)
                    history.append(active_cases)
                    region.history = json.dumps(history)

                    region.active_cases = active_cases
                    region.patients = patients
                    region.risk = risk
                    region.disease = disease
                    region.population_density = pop_density
                    region.recommendations = json.dumps(recs)
                else:
                    history = _build_history(active_cases)
                    region = Region(
                        city=city["name"],
                        risk=risk,
                        active_cases=active_cases,
                        active_trend="+0%",
                        patients=patients,
                        patients_trend="+0%",
                        history=json.dumps(history),
                        disease=disease,
                        population_density=pop_density,
                        hospital_capacity=hosp_capacity,
                        vaccination_rate=vax_rate,
                        recommendations=json.dumps(recs),
                        last_week_cases=active_cases,
                    )
                    db.add(region)

                updated.append(
                    {
                        "city": city["name"],
                        "active_cases": active_cases,
                        "patients": patients,
                        "disease": disease,
                        "risk": risk,
                    }
                )
            except Exception as exc:
                logger.error("Failed to update %s: %s", city["name"], exc)

        await db.commit()

    logger.info("[data_fetcher] Refresh complete. national_active=%s", national_active)
    return {"national": national, "regions": updated}
