import os
import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTESERVICE_API_KEY = os.getenv("OPENROUTESERVICE_API_KEY")

def _get_ors_headers():
    if not OPENROUTESERVICE_API_KEY or OPENROUTESERVICE_API_KEY == "your_openrouteservice_api_key":
        raise ValueError("Valid OPENROUTESERVICE_API_KEY is not set in environment.")
    return {
        'Authorization': OPENROUTESERVICE_API_KEY,
        'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8'
    }

def fetch_travel_time(start_lat: float, start_lon: float, end_lat: float, end_lon: float, mode: str) -> dict:
    headers = _get_ors_headers()
    url = f"https://api.openrouteservice.org/v2/directions/{mode}"
    
    # OpenRouteService expects coordinates as [longitude, latitude]
    params = {
        'start': f"{start_lon},{start_lat}",
        'end': f"{end_lon},{end_lat}"
    }
    
    response = requests.get(url, params=params, headers=headers, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    if 'features' in data and len(data['features']) > 0:
        summary = data['features'][0]['properties']['summary']
        distance_km = summary['distance'] / 1000.0
        duration_mins = summary['duration'] / 60.0
        
        return {
            "distance_km": distance_km,
            "duration_mins": duration_mins
        }
    else:
        raise ValueError("No route found between these coordinates.")
