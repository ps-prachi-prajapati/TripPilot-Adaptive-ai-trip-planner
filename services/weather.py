import os
import requests

OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")

def get_coordinates(location: str) -> tuple[float, float]:
    """Helper function to get coordinates for a location string."""
    if not OPENWEATHERMAP_API_KEY or OPENWEATHERMAP_API_KEY == "your_openweathermap_api_key":
        raise ValueError("Valid OPENWEATHERMAP_API_KEY is not set in environment.")
        
    geocode_url = "http://api.openweathermap.org/geo/1.0/direct"
    params = {
        'q': location,
        'limit': 1,
        'appid': OPENWEATHERMAP_API_KEY
    }
    
    response = requests.get(geocode_url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    if not data:
        raise ValueError(f"Location '{location}' not found.")
        
    return data[0]['lat'], data[0]['lon']

def fetch_current_weather(lat: float, lon: float) -> dict:
    weather_url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        'lat': lat,
        'lon': lon,
        'units': 'metric',
        'appid': OPENWEATHERMAP_API_KEY
    }
    
    res = requests.get(weather_url, params=params, timeout=10)
    res.raise_for_status()
    return res.json()

def fetch_weather_forecast(lat: float, lon: float) -> dict:
    forecast_url = "http://api.openweathermap.org/data/2.5/forecast"
    params = {
        'lat': lat,
        'lon': lon,
        'units': 'metric',
        'appid': OPENWEATHERMAP_API_KEY
    }
    
    res = requests.get(forecast_url, params=params, timeout=10)
    res.raise_for_status()
    return res.json()
