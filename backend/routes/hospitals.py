import time
from typing import List, Optional, Dict, Any
import httpx
from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/hospitals", tags=["hospitals"])

# Bounding boxes for major Pakistani cities (min_lat, min_lon, max_lat, max_lon)
CITY_BBOXES = {
    "Karachi": (24.74, 66.85, 25.10, 67.30),
    "Lahore": (31.37, 74.16, 31.70, 74.50),
    "Islamabad": (33.60, 72.95, 33.80, 73.20),
    "Peshawar": (33.95, 71.45, 34.07, 71.65),
    "Quetta": (30.15, 66.90, 30.25, 67.10),
    "Multan": (30.15, 71.40, 30.25, 71.55),
}

# Simple in-memory cache: {city_key: (timestamp, data)}
_cache: Dict[str, tuple] = {}
# Cache cleared manually as requested
CACHE_TTL = 3600  # 1 hour in seconds

DISEASES = ["Dengue", "Cholera", "Typhoid", "Malaria", "COVID-19", "Hepatitis", "Tuberculosis"]

async def fetch_osm_hospitals(city: Optional[str] = None) -> List[Dict[str, Any]]:
    cache_key = city or "all_pakistan"
    now = time.time()
    
    if cache_key in _cache:
        ts, data = _cache[cache_key]
        if now - ts < CACHE_TTL:
            return data

    if city and city in CITY_BBOXES:
        bbox = CITY_BBOXES[city]
        bbox_str = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"
        limit = ""
    else:
        # All Pakistan bbox with limit
        bbox_str = "23.5,60.5,37.5,77.5"
        limit = "[maxsize:1073741824];" # Increase max size for larger area if needed

    overpass_urls = [
        "https://overpass-api.de/api/interpreter",
        "https://lz4.overpass-api.de/api/interpreter",
        "https://z.overpass-api.de/api/interpreter"
    ]
    
    query = f"""
    [out:json][timeout:30];
    (
      node["amenity"="hospital"]({bbox_str});
      way["amenity"="hospital"]({bbox_str});
      relation["amenity"="hospital"]({bbox_str});
      node["healthcare"="hospital"]({bbox_str});
      way["healthcare"="hospital"]({bbox_str});
      relation["healthcare"="hospital"]({bbox_str});
    );
    out center body 50;
    """
    
    async with httpx.AsyncClient() as client:
        for url in overpass_urls:
            try:
                response = await client.post(url, data={"data": query}, timeout=30.0)
                response.raise_for_status()
                osm_data = response.json()
                elements = osm_data.get("elements", [])
                
                hospitals = []
                for el in elements[:50] if not city else elements:
                    tags = el.get("tags", {})
                    h_id = el.get("id")
                    
                    # Get coordinates from center if it's a way/relation, else use lat/lon
                    lat = el.get("lat") or el.get("center", {}).get("lat")
                    lng = el.get("lon") or el.get("center", {}).get("lon")
                    
                    if not lat or not lng:
                        continue
                    
                    h_type = "Government" if tags.get("operator:type") == "public" else "Private"
                    
                    hospitals.append({
                        "id": h_id,
                        "name": tags.get("name:en") or tags.get("name") or "Unknown Hospital",
                        "city": city or tags.get("addr:city") or "Unknown",
                        "lat": lat,
                        "lng": lng,
                        "address": tags.get("addr:street") or tags.get("addr:full") or "",
                        "phone": tags.get("phone") or tags.get("contact:phone") or "",
                        "type": h_type,
                        "emergency": tags.get("emergency") == "yes",
                        "beds": int(tags.get("capacity:persons", 0) or tags.get("capacity", 0)) or None,
                        "rating": None,   # OSM does not have ratings — show "N/A" in frontend
                        "diseases": [],   # Will be filtered by disease query param if provided
                    })
                
                _cache[cache_key] = (now, hospitals)
                return hospitals
            except Exception as e:
                print(f"OSM Fetch Error from {url}: {e}")
                # Continue to next URL if current one fails
                continue
        
        # If all URLs fail, return previous cache or empty list
        return _cache.get(cache_key, (0, []))[1]


@router.get("/")
async def get_hospitals(
    city: Optional[str] = Query(None, description="Filter by city name"),
    disease: Optional[str] = Query(None, description="Filter/annotate by disease name"),
):
    """
    Fetches real hospitals from OpenStreetMap Overpass API.
    """
    hospitals = await fetch_osm_hospitals(city)

    if disease:
        annotated = []
        for h in hospitals:
            hospital = dict(h)
            hospital["can_treat"] = True
            annotated.append(hospital)
        return annotated

    return hospitals

@router.get("/cities")
def get_cities():
    """Returns a sorted list of all cities supported for real-time OSM lookup."""
    return sorted(list(CITY_BBOXES.keys()))

@router.get("/diseases")
def get_diseases():
    """Returns a sorted list of diseases for the filter."""
    return sorted(DISEASES)
