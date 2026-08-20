"""
Budget/Trip Evaluation MCP Server — FastMCP
Provides deterministic calculation logic for costs and rigid constraint evaluation,
preventing the LLM from making arithmetic mistakes.
"""

from typing import List, Dict, Any
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    from fastmcp import FastMCP

mcp = FastMCP("Budget Evaluation MCP Server")

# ── Cost Estimation Data (INR) ────────────────────────────────────────────────
ACCOMMODATION_TIERS = {
    "budget":   {"avg": 1500,  "label": "Budget Hostel/Motel"},
    "mid":      {"avg": 4000, "label": "3-Star Hotel"},
    "comfort":  {"avg": 8000, "label": "4-Star Hotel"},
    "luxury":   {"avg": 15000, "label": "5-Star Resort"},
}

MEAL_TIERS = {
    "budget":   {"avg": 500,  "label": "Fast food / Groceries"},
    "mid":      {"avg": 1200,  "label": "Casual restaurants"},
    "comfort":  {"avg": 2500, "label": "Good restaurants"},
    "luxury":   {"avg": 5000, "label": "Fine dining"},
}

@mcp.tool()
def calculate_trip_cost(days: int, tier: str, transport_cost: float, activities_cost: float) -> dict:
    """
    Calculate the total estimated trip cost. The LLM should call this instead of doing math.
    
    Args:
        days: Number of days for the trip.
        tier: Comfort tier ('budget', 'mid', 'comfort', 'luxury').
        transport_cost: Total calculated transport cost.
        activities_cost: Total known activities cost.
    """
    tier = tier.lower()
    if tier not in ACCOMMODATION_TIERS:
        tier = "mid"
        
    nights = max(1, days - 1)
    
    acc_cost = ACCOMMODATION_TIERS[tier]["avg"] * nights
    meal_cost = MEAL_TIERS[tier]["avg"] * days
    total_cost = acc_cost + meal_cost + transport_cost + activities_cost
    
    return {
        "tier": tier,
        "days": days,
        "nights": nights,
        "breakdown": {
            "accommodation": round(acc_cost, 2),
            "food": round(meal_cost, 2),
            "transportation": round(transport_cost, 2),
            "activities": round(activities_cost, 2)
        },
        "total_estimated_cost": round(total_cost, 2)
    }

@mcp.tool()
def validate_budget(estimated_cost: float, user_budget: float) -> dict:
    """
    Evaluate if the estimated trip cost exceeds the user's maximum budget.
    """
    conflict = estimated_cost > user_budget
    difference = estimated_cost - user_budget
    
    return {
        "budget_conflict": conflict,
        "estimated_cost": estimated_cost,
        "user_budget": user_budget,
        "variance": round(abs(difference), 2),
        "status": "EXCEEDED" if conflict else "WITHIN_BUDGET",
        "message": f"Cost exceeds budget by ₹{round(difference, 2)}." if conflict else f"Under budget by ₹{round(abs(difference), 2)}."
    }

@mcp.tool()
def evaluate_constraints(
    travel_time_mins: float, 
    max_travel_mins: float, 
    weather_conflicts_exist: bool,
    planned_transport_mode: str,
    preferred_transport_mode: str
) -> dict:
    """
    Deterministically evaluates travel time, transport modes, and weather suitability constraints.
    """
    conflicts = []
    
    if travel_time_mins > max_travel_mins:
        conflicts.append(f"Travel time ({travel_time_mins} mins) exceeds maximum allowed ({max_travel_mins} mins).")
        
    if weather_conflicts_exist:
        conflicts.append("Weather conflicts were detected for the planned activities.")
        
    # Standardize strings for comparison just in case
    planned_t = planned_transport_mode.lower()
    pref_t = preferred_transport_mode.lower()
    
    # Simple heuristic to flag if they are vastly different (e.g. foot-walking vs driving)
    if pref_t not in planned_t and planned_t not in pref_t and pref_t != "mixed":
        conflicts.append(f"Planned transport ({planned_transport_mode}) does not match preference ({preferred_transport_mode}).")
        
    return {
        "is_valid": len(conflicts) == 0,
        "total_conflicts": len(conflicts),
        "conflict_reasons": conflicts
    }

@mcp.tool()
def compare_trip_options(
    option_a_cost: float, option_a_time: float, 
    option_b_cost: float, option_b_time: float,
    user_budget: float, max_travel_mins: float
) -> dict:
    """
    Compares two trip options and recommends the best one deterministically based on budget and time.
    """
    a_valid = option_a_cost <= user_budget and option_a_time <= max_travel_mins
    b_valid = option_b_cost <= user_budget and option_b_time <= max_travel_mins
    
    if a_valid and not b_valid:
        recommendation = "Option A"
        reason = "Option B violates constraints."
    elif b_valid and not a_valid:
        recommendation = "Option B"
        reason = "Option A violates constraints."
    elif not a_valid and not b_valid:
        recommendation = "Neither"
        reason = "Both options violate constraints (budget or travel time)."
    else:
        # Both are valid, recommend the cheaper one
        if option_a_cost < option_b_cost:
            recommendation = "Option A"
            reason = "Both are valid, but Option A is cheaper."
        elif option_b_cost < option_a_cost:
            recommendation = "Option B"
            reason = "Both are valid, but Option B is cheaper."
        else:
            # Same cost, recommend shorter travel time
            if option_a_time < option_b_time:
                recommendation = "Option A"
                reason = "Both cost the same, but Option A has a shorter travel time."
            else:
                recommendation = "Option B"
                reason = "Both cost the same, but Option B has a shorter travel time."
                
    return {
        "recommended_option": recommendation,
        "reason": reason,
        "option_a_status": "Valid" if a_valid else "Invalid",
        "option_b_status": "Valid" if b_valid else "Invalid"
    }

if __name__ == "__main__":
    mcp.run()
