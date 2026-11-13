from fastapi import APIRouter, HTTPException
from services.weather_service import get_weather, get_air_quality

router = APIRouter(prefix="/api/weather", tags=["weather"])

@router.get("/{city}")
async def fetch_city_weather_report(city: str):
    """
    Returns a combined weather and air quality report for a given city.
    """
    try:
        weather_data = await get_weather(city)
        aq_data = await get_air_quality(city)
        
        return {
            "city": city,
            "weather": weather_data,
            "air_quality": aq_data
        }
    except Exception as e:
        # We catch the exception and return a 503 if the services are down
        # or 404 if the city is not found (though our service currently raises generic Exception)
        raise HTTPException(status_code=503, detail=str(e))
