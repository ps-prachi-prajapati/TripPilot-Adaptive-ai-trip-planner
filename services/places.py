import os
import requests
from dotenv import load_dotenv

load_dotenv()

FOURSQUARE_API_KEY = os.getenv("FOURSQUARE_API_KEY")

def _get_foursquare_headers():
    if not FOURSQUARE_API_KEY or FOURSQUARE_API_KEY == "your_foursquare_api_key":
        raise ValueError("Valid FOURSQUARE_API_KEY is not set in environment.")
    return {
        "accept": "application/json",
        "Authorization": FOURSQUARE_API_KEY
    }

def _parse_foursquare_place(place: dict) -> dict:
    """Helper to parse raw Foursquare JSON into agent-friendly format."""
    location = place.get("location", {})
    categories = place.get("categories", [])
    category_name = categories[0]["name"] if categories else "General"
    
    return {
        "id": place.get("fsq_id", ""),
        "name": place.get("name", "Unknown"),
        "category": category_name,
        "address": location.get("formatted_address", "No address available"),
        "distance": place.get("distance", 0),  # in meters
        "rating": place.get("rating", "N/A"),
        "lat": place.get("geocodes", {}).get("main", {}).get("latitude"),
        "lon": place.get("geocodes", {}).get("main", {}).get("longitude")
    }

def fetch_destinations(query: str, limit: int) -> list[dict]:
    headers = _get_foursquare_headers()
    url = "https://api.foursquare.com/v3/places/search"
    params = {
        "query": query,
        "types": "neighborhood,city,locality",
        "limit": limit
    }
    
    response = requests.get(url, params=params, headers=headers, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    results = data.get("results", [])
    return [_parse_foursquare_place(r) for r in results]

def fetch_attractions(location: str, query: str, limit: int) -> list[dict]:
    headers = _get_foursquare_headers()
    url = "https://api.foursquare.com/v3/places/search"
    params = {
        "near": location,
        "query": query,
        "categories": "16000",  # Landmarks and Outdoors category in Foursquare
        "limit": limit,
        "sort": "RATING"
    }
    
    response = requests.get(url, params=params, headers=headers, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    results = data.get("results", [])
    return [_parse_foursquare_place(r) for r in results]

def fetch_restaurants(location: str, query: str, limit: int) -> list[dict]:
    headers = _get_foursquare_headers()
    url = "https://api.foursquare.com/v3/places/search"
    params = {
        "near": location,
        "query": query,
        "categories": "13000",  # Dining and Drinking category in Foursquare
        "limit": limit,
        "sort": "RATING"
    }
    
    response = requests.get(url, params=params, headers=headers, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    results = data.get("results", [])
    return [_parse_foursquare_place(r) for r in results]

def fetch_hotels(location: str, query: str, limit: int) -> list[dict]:
    headers = _get_foursquare_headers()
    url = "https://api.foursquare.com/v3/places/search"
    params = {
        "near": location,
        "query": query or "hotel",
        "categories": "19014",  # Hotel and Lodging category in Foursquare
        "limit": limit,
        "sort": "RATING"
    }
    
    response = requests.get(url, params=params, headers=headers, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    results = data.get("results", [])
    return [_parse_foursquare_place(r) for r in results]

def fetch_place_details(place_id: str) -> dict:
    headers = _get_foursquare_headers()
    url = f"https://api.foursquare.com/v3/places/{place_id}"
    params = {
        "fields": "fsq_id,name,description,tel,website,rating,hours,location,categories"
    }
    
    response = requests.get(url, params=params, headers=headers, timeout=10)
    response.raise_for_status()
    place = response.json()
    
    categories = place.get("categories", [])
    category_name = categories[0]["name"] if categories else "General"
    
    return {
        "id": place.get("fsq_id", ""),
        "name": place.get("name", "Unknown"),
        "category": category_name,
        "description": place.get("description", "No description available"),
        "address": place.get("location", {}).get("formatted_address", "No address"),
        "rating": place.get("rating", "N/A"),
        "website": place.get("website", "No website"),
        "phone": place.get("tel", "No phone number")
    }
