import asyncio
import httpx

async def test_osm():
    overpass_url = "https://overpass-api.de/api/interpreter"
    # Islamabad bbox
    bbox_str = "33.60,72.95,33.80,73.20"
    query = f"""
    [out:json][timeout:25];
    node["amenity"="hospital"]({bbox_str});
    out body;
    """
    
    async with httpx.AsyncClient() as client:
        try:
            print(f"Querying Overpass for Islamabad: {bbox_str}")
            response = await client.post(overpass_url, data={"data": query}, timeout=30)
            print(f"Status: {response.status_code}")
            data = response.json()
            elements = data.get("elements", [])
            print(f"Found {len(elements)} elements")
            for el in elements[:5]:
                tags = el.get("tags", {})
                print(f"- {tags.get('name', 'Unknown')}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_osm())
