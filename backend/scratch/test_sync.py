import requests

def find_one():
    url = "https://overpass.kumi.systems/api/interpreter"
    query = '[out:json];nwr["amenity"="hospital"](24.8,67.0,24.9,67.1);out center 1;'
    try:
        r = requests.post(url, data={"data": query}, timeout=30)
        print(f"Status: {r.status_code}")
        print(r.json())
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    find_one()
