import os
import sys
import requests
from fastmcp import FastMCP
from dotenv import load_dotenv
from typing import List

# Load environment variables
load_dotenv()

# Ensure the project root is in the path so `services` can be found
# when this script is launched as a subprocess by the MCP client
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Initialize FastMCP Server
mcp = FastMCP("Weather MCP Server")

from services.weather import get_coordinates, fetch_current_weather, fetch_weather_forecast


@mcp.tool()
def get_current_weather(location: str) -> str:
    """
    Get the current weather conditions for a given location.
    
    Args:
        location: City name (e.g. "New York, NY" or "London, UK")
    """
    if not location.strip():
        return "Error: Location string cannot be empty."
        
    try:
        lat, lon = get_coordinates(location)
        
        data = fetch_current_weather(lat, lon)
        
        condition = data['weather'][0]['main']
        desc = data['weather'][0]['description']
        temp = data['main']['temp']
        feels_like = data['main']['feels_like']
        humidity = data['main']['humidity']
        
        return (f"Current weather in {location}: {condition} ({desc}). "
                f"Temperature: {temp}°C (Feels like {feels_like}°C). "
                f"Humidity: {humidity}%.")
                
    except ValueError as ve:
        return f"Error: {str(ve)}"
    except requests.exceptions.RequestException as e:
        return f"Error fetching current weather: {str(e)}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"


@mcp.tool()
def get_weather_forecast(location: str, days: int = 3) -> str:
    """
    Get the weather forecast for a given location for the specified number of days (max 5).
    
    Args:
        location: City name (e.g. "New York, NY")
        days: Number of days to forecast (1 to 5, default 3)
    """
    if not location.strip():
        return "Error: Location string cannot be empty."
    if not (1 <= days <= 5):
        return "Error: Days must be between 1 and 5."
        
    try:
        lat, lon = get_coordinates(location)
        
        data = fetch_weather_forecast(lat, lon)
        
        # Simplify the 3-hour data into daily summaries
        daily_summaries = {}
        for item in data.get('list', []):
            date = item['dt_txt'].split(' ')[0]
            if date not in daily_summaries:
                daily_summaries[date] = {
                    "temp_c": item['main']['temp'],
                    "condition": item['weather'][0]['main'],
                    "description": item['weather'][0]['description'],
                    "precip_chance": item.get('pop', 0) * 100
                }
                if len(daily_summaries) >= days:
                    break
                    
        result = [f"Forecast for {location} (Next {days} days):"]
        for date, info in daily_summaries.items():
            result.append(f"- {date}: {info['condition']} ({info['description']}), Temp: {info['temp_c']}°C, Precip Chance: {info['precip_chance']}%")
            
        return "\n".join(result)
        
    except ValueError as ve:
        return f"Error: {str(ve)}"
    except requests.exceptions.RequestException as e:
        return f"Error fetching forecast: {str(e)}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"


@mcp.tool()
def check_weather_suitability(forecast_text: str, activities: List[str]) -> str:
    """
    Evaluates whether planned activities are suitable for the given weather forecast.
    
    Args:
        forecast_text: The weather conditions (e.g., "Heavy Rain", "Sunny, 25°C")
        activities: A list of planned activities (e.g., ["Hiking", "Museum Visit"])
    """
    if not forecast_text.strip():
        return "Error: Forecast text cannot be empty."
    if not activities:
        return "Error: Activities list cannot be empty."
        
    forecast_lower = forecast_text.lower()
    
    bad_weather_keywords = ['rain', 'storm', 'snow', 'thunder', 'hurricane', 'drizzle', 'showers']
    is_bad_weather = any(kw in forecast_lower for kw in bad_weather_keywords)
    
    outdoor_keywords = ['hike', 'hiking', 'beach', 'park', 'walking', 'outdoor', 'bike', 'biking', 'camping', 'tour']
    
    conflicts = []
    
    if is_bad_weather:
        for activity in activities:
            act_lower = activity.lower()
            if any(kw in act_lower for kw in outdoor_keywords):
                conflicts.append(f"Activity '{activity}' is not recommended due to weather conditions: {forecast_text}.")
                
    if conflicts:
        return "Weather Conflicts Detected:\n- " + "\n- ".join(conflicts)
    else:
        return "All activities appear suitable for the forecasted weather."

if __name__ == "__main__":
    mcp.run()
