import os
import sys
import requests
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    from fastmcp import FastMCP
from typing import Any

# Ensure the project root is in the path so `services` can be found
# when this script is launched as a subprocess by the MCP client
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.places import fetch_destinations, fetch_attractions, fetch_restaurants, fetch_hotels, fetch_place_details

mcp = FastMCP("Places MCP Server")

@mcp.tool()
def search_destinations(query: str, limit: int = 5) -> Any:
    """
    Search for general destinations, neighborhoods, or cities.
    
    Args:
        query: Name of the destination (e.g., "Brooklyn", "Downtown Seattle")
        limit: Max number of results (default 5, max 10)
    """
    if not query.strip():
        return "Error: Query cannot be empty."
    if not (1 <= limit <= 10):
        return "Error: Limit must be between 1 and 10."
        
    try:
        results = fetch_destinations(query, limit)
        if not results:
            return f"No destinations found for '{query}'."
        return {"destinations": results}
        
    except ValueError as ve:
        return f"Configuration Error: {str(ve)}"
    except requests.exceptions.RequestException as e:
        return f"API Error: Failed to search destinations: {str(e)}"
    except Exception as e:
        return f"Unexpected Error: {str(e)}"


@mcp.tool()
def search_attractions(location: str, query: str = "", limit: int = 5) -> Any:
    """
    Search for tourist attractions, landmarks, and activities in a specific location.
    
    Args:
        location: The city or area (e.g., "New York, NY")
        query: Optional specific term (e.g., "Museum", "Park")
        limit: Max number of results (default 5)
    """
    if not location.strip():
        return "Error: Location cannot be empty."
        
    try:
        results = fetch_attractions(location, query, limit)
        if not results:
            return f"No attractions found in '{location}' matching '{query}'."
        return {"attractions": results}
        
    except ValueError as ve:
        return f"Configuration Error: {str(ve)}"
    except requests.exceptions.RequestException as e:
        return f"API Error: Failed to search attractions: {str(e)}"


@mcp.tool()
def search_hotels(location: str, query: str = "", limit: int = 5) -> Any:
    """
    Search for hotels, resorts, or accommodations in a specific location.
    
    Args:
        location: The city or area (e.g., "Ahmedabad, Gujarat" or "Udaipur")
        query: Optional hotel type or name (e.g., "Resort", "Boutique")
        limit: Max number of results (default 5)
    """
    if not location.strip():
        return "Error: Location cannot be empty."
        
    try:
        results = fetch_hotels(location, query, limit)
        if not results:
            return f"No hotels found in '{location}' matching '{query}'."
        return {"hotels": results}
        
    except ValueError as ve:
        return f"Configuration Error: {str(ve)}"
    except requests.exceptions.RequestException as e:
        return f"API Error: Failed to search hotels: {str(e)}"


@mcp.tool()
def search_restaurants(location: str, query: str = "", limit: int = 5) -> Any:
    """
    Search for restaurants, cafes, or bars in a specific location.
    
    Args:
        location: The city or area (e.g., "New York, NY")
        query: Optional specific food type (e.g., "Italian", "Coffee")
        limit: Max number of results (default 5)
    """
    if not location.strip():
        return "Error: Location cannot be empty."
        
    try:
        results = fetch_restaurants(location, query, limit)
        if not results:
            return f"No restaurants found in '{location}' matching '{query}'."
        return {"restaurants": results}
        
    except ValueError as ve:
        return f"Configuration Error: {str(ve)}"
    except requests.exceptions.RequestException as e:
        return f"API Error: Failed to search restaurants: {str(e)}"


@mcp.tool()
def get_place_details(place_id: str) -> Any:
    """
    Get detailed information about a specific place using its ID.
    
    Args:
        place_id: The unique ID of the place (from search tools)
    """
    if not place_id.strip():
        return "Error: place_id cannot be empty."
        
    try:
        details = fetch_place_details(place_id)
        return {"place_details": details}
        
    except ValueError as ve:
        return f"Configuration Error: {str(ve)}"
    except requests.exceptions.RequestException as e:
        return f"API Error: Failed to fetch place details: {str(e)}"


if __name__ == "__main__":
    mcp.run()
