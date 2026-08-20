import os
import requests
import re
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Pre-baked coordinates catalog for top cities when API is in demo/fallback mode
KNOWN_COORDINATES = {
    "ahmedabad": {"lat": 23.0225, "lon": 72.5714, "full_address": "Ahmedabad, Gujarat, India", "place_id": "ChIJS-X6rJmEXjkR888Y0-k3ygg"},
    "vadodara": {"lat": 22.3072, "lon": 73.1812, "full_address": "Vadodara, Gujarat, India", "place_id": "ChIJbU6663XvXzkR2t2Y_64q1gg"},
    "mumbai": {"lat": 19.0760, "lon": 72.8777, "full_address": "Mumbai, Maharashtra, India", "place_id": "ChIJwe1EZjDG5zsRaYxkjY_2hIA"},
    "delhi": {"lat": 28.6139, "lon": 77.2090, "full_address": "New Delhi, Delhi, India", "place_id": "ChIJLbZ-NFv9DDkRKiwoLength"},
    "jaipur": {"lat": 26.9124, "lon": 75.7873, "full_address": "Jaipur, Rajasthan, India", "place_id": "ChIJx2hCE6C3bTkR_1y7Length"},
    "udaipur": {"lat": 24.5854, "lon": 73.7125, "full_address": "Udaipur, Rajasthan, India", "place_id": "ChIJc123UdaiprR_Length"},
    "surat": {"lat": 21.1702, "lon": 72.8311, "full_address": "Surat, Gujarat, India", "place_id": "ChIJy123Surat_Length"},
    "pune": {"lat": 18.5204, "lon": 73.8567, "full_address": "Pune, Maharashtra, India", "place_id": "ChIJy123Pune_Length"},
    "bangalore": {"lat": 12.9716, "lon": 77.5946, "full_address": "Bangalore, Karnataka, India", "place_id": "ChIJbU6663XvXzkR2t2Y_BLR"},
    "goa": {"lat": 15.2993, "lon": 74.1240, "full_address": "Goa, India", "place_id": "ChIJy123Goa_Length"},
    "london": {"lat": 51.5074, "lon": -0.1278, "full_address": "London, UK", "place_id": "ChIJdd4hrwug2EcRmSrV3Vo6llI"},
    "new york": {"lat": 40.7128, "lon": -74.0060, "full_address": "New York, NY, USA", "place_id": "ChIJOwgLwNFFwhQRhAKaSuperKey"},
    "paris": {"lat": 48.8566, "lon": 2.3522, "full_address": "Paris, France", "place_id": "ChIJD7fiBh9u5kcRYJSMaMOCCwQ"},
    "tokyo": {"lat": 35.6762, "lon": 139.6503, "full_address": "Tokyo, Japan", "place_id": "ChIJ51tW3qv3GGAR3cV2ypMCDvo"}
}

def clean_place_name(place_str: str) -> str:
    """Strips leading emoji icons and replaces ampersands with commas for better geocoding."""
    if not place_str:
        return ""
    cleaned = re.sub(r'^[^\w\s]+', '', place_str).strip()
    # Replace ampersands with commas for better autocomplete geocoding
    cleaned = cleaned.replace(" & ", ", ").replace("&", ",")
    return cleaned if cleaned else place_str

LOCATION_CACHE = {}

def get_location_autocomplete(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Fetches place predictions using OpenStreetMap Nominatim geocoding API restricted to India.
    Returns list of dicts: [{"description": str, "place_id": str, "place_name": str, "latitude": float, "longitude": float}]
    """
    if not query or len(query.strip()) < 2:
        return []

    clean_q = clean_place_name(query).strip()

    # Query OpenStreetMap Nominatim geocoding API restricted to India
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": clean_q, "format": "json", "addressdetails": 1, "limit": limit, "countrycodes": "in"}
        headers = {"User-Agent": "AdaptiveTripPlanner/1.0 (L2 Project)"}
        resp = requests.get(url, params=params, headers=headers, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                results = []
                for item in data:
                    disp = item.get("display_name", clean_q)
                    osm_id = f"osm_{item.get('osm_id', abs(hash(disp)))}"
                    addr = item.get("address", {})
                    name = next((addr[k] for k in ["amenity", "building", "historic", "shop", "tourism", "road", "suburb", "city"] if k in addr), disp.split(",")[0])
                    lat = float(item.get("lat", 23.0225))
                    lon = float(item.get("lon", 72.5714))
                    
                    res_dict = {
                        "description": disp,
                        "place_id": osm_id,
                        "place_name": name,
                        "latitude": lat,
                        "longitude": lon
                    }
                    results.append(res_dict)
                    LOCATION_CACHE[disp] = res_dict
                return results
    except Exception:
        pass

    # Fallback matched from known coordinates
    results = []
    key_lower = clean_q.lower()
    for city, coord in KNOWN_COORDINATES.items():
        if city in key_lower:
            res_dict = {
                "description": coord["full_address"],
                "place_id": coord["place_id"],
                "place_name": city.capitalize(),
                "latitude": coord["lat"],
                "longitude": coord["lon"]
            }
            results.append(res_dict)
            LOCATION_CACHE[coord["full_address"]] = res_dict

    if results:
        return results[:limit]

    # Default fallback
    fallback_desc = f"{clean_q}, India"
    res_dict = {
        "description": fallback_desc,
        "place_id": f"place_{abs(hash(clean_q))}",
        "place_name": clean_q,
        "latitude": 23.0225,
        "longitude": 72.5714
    }
    LOCATION_CACHE[fallback_desc] = res_dict
    return [res_dict]

def get_location_details(place_id: str, default_name: str = "Location") -> Dict[str, Any]:
    """
    Fetches full place details using cache, catalog, or Nominatim lookup.
    Returns: {"place_name": str, "full_address": str, "latitude": float, "longitude": float, "place_id": str}
    """
    clean_name = clean_place_name(default_name)

    # 1. Check cache first
    if default_name in LOCATION_CACHE:
        cache_item = LOCATION_CACHE[default_name]
        return {
            "place_name": cache_item["place_name"],
            "full_address": cache_item["description"],
            "latitude": cache_item["latitude"],
            "longitude": cache_item["longitude"],
            "place_id": cache_item["place_id"]
        }
    if clean_name in LOCATION_CACHE:
        cache_item = LOCATION_CACHE[clean_name]
        return {
            "place_name": cache_item["place_name"],
            "full_address": cache_item["description"],
            "latitude": cache_item["latitude"],
            "longitude": cache_item["longitude"],
            "place_id": cache_item["place_id"]
        }

    # 2. Check catalog
    key_lower = clean_name.lower().split(",")[0].strip()
    if key_lower in KNOWN_COORDINATES:
        cat = KNOWN_COORDINATES[key_lower]
        return {
            "place_name": clean_name,
            "full_address": cat["full_address"],
            "latitude": cat["lat"],
            "longitude": cat["lon"],
            "place_id": place_id or cat["place_id"]
        }

    # 3. Nominatim lookup
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": clean_name, "format": "json", "limit": 1}
        headers = {"User-Agent": "AdaptiveTripPlanner/1.0"}
        resp = requests.get(url, params=params, headers=headers, timeout=3)
        if resp.status_code == 200 and resp.json():
            item = resp.json()[0]
            return {
                "place_name": clean_name,
                "full_address": item.get("display_name", clean_name),
                "latitude": float(item.get("lat", 23.0225)),
                "longitude": float(item.get("lon", 72.5714)),
                "place_id": place_id or f"osm_{item.get('osm_id', 1000)}"
            }
    except Exception:
        pass

    # Default fallback
    return {
        "place_name": clean_name,
        "full_address": f"{clean_name}, India",
        "latitude": 23.0225,
        "longitude": 72.5714,
        "place_id": place_id or f"place_{abs(hash(clean_name))}"
    }

