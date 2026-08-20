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

from services.transport import fetch_travel_time

mcp = FastMCP("Transport MCP Server")

@mcp.tool()
def find_transport_options() -> Any:
    """
    Returns the transportation modes currently supported by the routing API.
    Agent should use these exact string modes when calculating travel time.
    """
    return {
        "supported_modes": [
            {"id": "driving-car", "name": "Driving (Car)", "type": "private"},
            {"id": "cycling-regular", "name": "Cycling", "type": "active"},
            {"id": "foot-walking", "name": "Walking", "type": "active"}
        ],
        "note": "Public transit routing is not currently supported by the OpenRouteService provider."
    }

@mcp.tool()
def calculate_travel_time(start_lat: float, start_lon: float, end_lat: float, end_lon: float, mode: str = "driving-car") -> Any:
    """
    Calculate real travel time and distance between two coordinates.
    
    Args:
        start_lat: Starting latitude
        start_lon: Starting longitude
        end_lat: Destination latitude
        end_lon: Destination longitude
        mode: Must be one of: 'driving-car', 'cycling-regular', 'foot-walking'
    """
    valid_modes = ["driving-car", "cycling-regular", "foot-walking"]
    if mode not in valid_modes:
        return f"Error: Invalid mode. Must be one of {valid_modes}"
        
    try:
        data = fetch_travel_time(start_lat, start_lon, end_lat, end_lon, mode)
        
        return {
            "status": "success",
            "mode": mode,
            "distance_km": round(data["distance_km"], 2),
            "duration_mins": round(data["duration_mins"], 2)
        }
            
    except ValueError as ve:
        return {"status": "error", "message": f"Configuration Error: {str(ve)}"}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"API Error: Failed to calculate route: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected Error: {str(e)}"}

@mcp.tool()
def calculate_transport_cost(distance_km: float, mode: str) -> Any:
    """
    Calculates the estimated monetary cost for a trip based on distance and mode.
    Since live transit/rideshare pricing APIs are generally paid/private, 
    this uses standardized global heuristics applied to the real route distance.
    
    Args:
        distance_km: The distance in kilometers (from calculate_travel_time).
        mode: The transport mode.
    """
    if distance_km < 0:
        return {"status": "error", "message": "Distance cannot be negative."}
        
    cost = 0.0
    cost_breakdown = ""
    
    if "car" in mode:
        # Standard India average estimation: ₹15 per km + ₹100 base fare
        cost = (distance_km * 15.0) + 100.0
        cost_breakdown = "Base fare ₹100.00 + ₹15.00/km"
    elif "foot" in mode or "cycling" in mode:
        cost = 0.0
        cost_breakdown = "Free"
    else:
        # Generic fallback
        cost = 200.0
        cost_breakdown = "Flat rate assumption"
        
    return {
        "status": "success",
        "estimated_cost_inr": round(cost, 2),
        "calculation_basis": cost_breakdown,
        "mode": mode,
        "distance_km": distance_km
    }

if __name__ == "__main__":
    mcp.run()
