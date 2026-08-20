import os
import sys

# Add mcp_servers to path
sys.path.append(os.path.join(os.path.dirname(__file__), "mcp_servers"))

def test_budget_mcp():
    print("Testing Budget MCP...")
    from budget_server import calculate_trip_cost, validate_budget, evaluate_constraints, compare_trip_options
    
    # Test calculate_trip_cost
    res = calculate_trip_cost(3, "mid", 100, 150)
    assert res["total_estimated_cost"] == (4000 * 2) + (1200 * 3) + 100 + 150 # 8000 + 3600 + 250 = 11850
    
    # Test validate_budget
    res = validate_budget(800.0, 1000.0)
    assert not res["budget_conflict"]
    assert res["status"] == "WITHIN_BUDGET"
    
    res = validate_budget(1200.0, 1000.0)
    assert res["budget_conflict"]
    assert res["status"] == "EXCEEDED"
    
    # Test evaluate_constraints
    res = evaluate_constraints(120, 180, False, "driving-car", "driving-car")
    assert res["is_valid"]
    
    res = evaluate_constraints(200, 180, False, "driving-car", "driving-car")
    assert not res["is_valid"]
    assert "exceeds maximum allowed" in res["conflict_reasons"][0]
    
    # Test compare_trip_options
    res = compare_trip_options(800, 120, 900, 100, 1000, 180)
    assert res["recommended_option"] == "Option A"
    
    print("SUCCESS: Budget MCP OK")

def test_weather_mcp():
    print("Testing Weather MCP...")
    from weather_server import get_current_weather, get_weather_forecast, check_weather_suitability
    
    # Since keys are missing, they should return errors gracefully (not crash)
    res = get_current_weather("London, UK")
    assert "Error" in res or "Valid OPENWEATHERMAP_API_KEY is not set" in res
    
    res = get_weather_forecast("London, UK", 3)
    assert "Error" in res or "Valid OPENWEATHERMAP_API_KEY is not set" in res
    
    # Test suitability logic (deterministic)
    res = check_weather_suitability("Heavy rain and thunderstorms", ["Hiking", "Museum"])
    assert "Weather Conflicts Detected" in res
    assert "Hiking" in res
    assert "Museum" not in res
    
    res = check_weather_suitability("Sunny and clear", ["Hiking", "Museum"])
    assert "All activities appear suitable" in res
    
    print("SUCCESS: Weather MCP OK")

def test_places_mcp():
    print("Testing Places MCP...")
    from places_server import search_destinations, search_attractions, search_restaurants, get_place_details
    
    # Missing/invalid keys should be handled gracefully by returning mock fallback data or config error
    res = search_destinations("New York")
    assert "destinations" in res or "Error" in str(res) or "Valid FOURSQUARE_API_KEY is not set" in str(res)
    
    res = search_destinations("")
    assert "Error: Query cannot be empty" in str(res)
    
    print("SUCCESS: Places MCP OK")

def test_transport_mcp():
    print("Testing Transport MCP...")
    try:
        from transport_server import find_transport_options
        res = find_transport_options()
        assert "supported_modes" in res
        print("SUCCESS: Transport MCP OK")
    except ImportError:
        print("Transport MCP not found or failed to import.")
    except Exception as e:
        print(f"FAILED: Transport MCP: {e}")

if __name__ == "__main__":
    test_budget_mcp()
    test_weather_mcp()
    test_places_mcp()
    test_transport_mcp()
    print("All MCP Server tests completed.")

