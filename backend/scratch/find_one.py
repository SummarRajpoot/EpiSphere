import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import httpx

async def find_one():
    url = "https://overpass.kumi.systems/api/interpreter"
    query = '[out:json];nwr["amenity"="hospital"](24.8,67.0,24.9,67.1);out center 1;'
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(url, data={"data": query}, timeout=30)
            print(r.json())
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(find_one())
