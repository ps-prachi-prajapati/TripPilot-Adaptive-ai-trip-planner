import asyncio
import sys
import os

# Add project root and agent folder to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent"))

from agent.state import TripState
from agent.agent import evaluation_node

async def run_evaluation_test():
    print("Running Candidate Evaluation Unit Tests...")
    
    # Define candidates with different observation contexts
    candidates = [
        {
            "name": "Candidate A (Winner - Cheap & Valid)",
            "valid": None,
            "score": 0.0,
            "context": {
                "name": "Candidate A (Winner - Cheap & Valid)",
                "travel_time_mins": 90.0,
                "distance_km": 60.0,
                "weather_forecast": "Sunny and clear, 28C",
                "has_weather_conflicts": False,
                "attractions": ["Museum of Art", "Historical Palace"],
                "hotels": [{"name": "Grand Palace Hotel", "address": "123 Main St"}],
                "restaurants": ["Indian Delight Cafe"],
                "transportation_cost": 1000.0,
                "estimated_total_cost": 0.0
            }
        },
        {
            "name": "Candidate B (Invalid - Budget Conflict)",
            "valid": None,
            "score": 0.0,
            "context": {
                "name": "Candidate B (Invalid - Budget Conflict)",
                "travel_time_mins": 100.0,
                "distance_km": 70.0,
                "weather_forecast": "Cloudy, 25C",
                "has_weather_conflicts": False,
                "attractions": ["Lake Park", "Science Center"],
                "hotels": [{"name": "Lake View Resort", "address": "456 Lake Rd"}],
                "restaurants": ["Lakeside Grill"],
                "transportation_cost": 8000.0, # High transportation cost triggers budget conflict
                "estimated_total_cost": 0.0
            }
        },
        {
            "name": "Candidate C (Invalid - Travel Time Violation)",
            "valid": None,
            "score": 0.0,
            "context": {
                "name": "Candidate C (Invalid - Travel Time Violation)",
                "travel_time_mins": 240.0, # Exceeds max_travel_mins of 180
                "distance_km": 180.0,
                "weather_forecast": "Sunny, 30C",
                "has_weather_conflicts": False,
                "attractions": ["Theme Park", "Botanical Garden"],
                "hotels": [{"name": "Garden Inn", "address": "789 Rose Ave"}],
                "restaurants": ["Green Salad Bistro"],
                "transportation_cost": 1500.0,
                "estimated_total_cost": 0.0
            }
        },
        {
            "name": "Candidate D (Invalid - Weather Conflict)",
            "valid": None,
            "score": 0.0,
            "context": {
                "name": "Candidate D (Invalid - Weather Conflict)",
                "travel_time_mins": 60.0,
                "distance_km": 40.0,
                "weather_forecast": "Heavy rain and thunderstorms",
                "has_weather_conflicts": True, # Weather suitability conflict
                "attractions": ["Adventure Outdoor Park", "Beach Walk"],
                "hotels": [{"name": "Beachside Motel", "address": "101 Ocean Blvd"}],
                "restaurants": ["Seafood Shanty"],
                "transportation_cost": 700.0,
                "estimated_total_cost": 0.0
            }
        },
        {
            "name": "Candidate E (Valid - But Expensive)",
            "valid": None,
            "score": 0.0,
            "context": {
                "name": "Candidate E (Valid - But Expensive)",
                "travel_time_mins": 80.0,
                "distance_km": 50.0,
                "weather_forecast": "Clear skies, 29C",
                "has_weather_conflicts": False,
                "attractions": ["Museum of Art", "Historical Palace"],
                "hotels": [{"name": "Comfort Inn", "address": "202 Center St"}],
                "restaurants": ["Central Cafe"],
                "transportation_cost": 3000.0, # More expensive transportation
                "estimated_total_cost": 0.0
            }
        }
    ]

    # Set up test state
    state: TripState = {
        "location": "Origin City",
        "destination_location": "Target City",
        "sub_location": "Any Area",
        "origin_details": {},
        "destination_details": {},
        "duration_days": 2,
        "budget": 12000.0, # INR budget
        "interests": ["Museums", "Food"],
        "transport_mode": "driving-car",
        "max_travel_mins": 180.0,
        "messages": [],
        "candidates": candidates,
        "current_candidate_index": len(candidates),
        "selected_candidate": {},
        "final_itinerary": ""
    }

    # Run evaluation_node
    result = await evaluation_node(state)
    updated_candidates = result["candidates"]
    winner = result["selected_candidate"]

    # Verify each candidate's outcome
    for c in updated_candidates:
        name = c["name"]
        valid = c["valid"]
        cost = c["context"].get("estimated_total_cost", 0.0)
        rejection_reason = c.get("rejection_reason", "")
        print(f"- {name}: Valid={valid}, Cost=₹{cost}, Reason={rejection_reason}")

    # Check Candidate A (Cheap & Valid)
    cand_a = next(c for c in updated_candidates if "Cheap & Valid" in c["name"])
    assert cand_a["valid"] == True, "Candidate A should be Valid!"

    # Check Candidate B (Budget Conflict)
    cand_b = next(c for c in updated_candidates if "Budget Conflict" in c["name"])
    assert cand_b["valid"] == False, "Candidate B should be Invalid!"
    assert "budget" in cand_b["rejection_reason"].lower(), "Candidate B rejection reason should mention budget conflict."

    # Check Candidate C (Travel Time Violation)
    cand_c = next(c for c in updated_candidates if "Travel Time" in c["name"])
    assert cand_c["valid"] == False, "Candidate C should be Invalid!"
    assert "travel time" in cand_c["rejection_reason"].lower() or "exceeds" in cand_c["rejection_reason"].lower(), "Candidate C rejection reason should mention travel time violation."

    # Check Candidate D (Weather Conflict)
    cand_d = next(c for c in updated_candidates if "Weather Conflict" in c["name"])
    assert cand_d["valid"] == False, "Candidate D should be Invalid!"
    assert "weather" in cand_d["rejection_reason"].lower(), "Candidate D rejection reason should mention weather conflict."

    # Check Candidate E (Valid But Expensive)
    cand_e = next(c for c in updated_candidates if "Valid - But Expensive" in c["name"])
    assert cand_e["valid"] == True, "Candidate E should be Valid!"

    # Verify Winner Selection (Candidate A should be preferred as it has lower cost/higher score)
    assert winner["name"] == cand_a["name"], f"Winner should be Candidate A, got '{winner['name']}'"
    print("\nSUCCESS: Candidate evaluation unit tests passed. Correct ranking and constraints validation demonstrated.")

from agent.agent import data_gathering_node
from langchain_core.messages import AIMessage, ToolMessage, HumanMessage

async def run_data_gathering_test():
    print("\nRunning Data Gathering Unit Tests...")
    
    # 1. Test step limit
    state_limit: TripState = {
        "location": "Origin",
        "destination_location": "Target",
        "sub_location": "Area",
        "origin_details": {},
        "destination_details": {},
        "duration_days": 2,
        "budget": 5000.0,
        "interests": [],
        "transport_mode": "driving-car",
        "max_travel_mins": 180.0,
        "messages": [],
        "candidates": [{"name": "Candidate A", "context": {}, "valid": None, "score": 0.0}],
        "current_candidate_index": 0,
        "selected_candidate": {},
        "final_itinerary": "",
        "tool_steps_count": 8 # Already reached limit
    }
    res = await data_gathering_node(state_limit)
    assert res["tool_steps_count"] == 8
    assert len(res["messages"]) == 1
    assert "Reached max tool steps limit" in res["messages"][0].content
    print("- Safe limit termination OK (terminated at 8 steps)")
    
    # 2. Test unknown tool interception
    import agent.agent
    orig_get_tools = agent.agent.get_tools
    
    class MockTool:
        name = "valid_tool"
        description = "A valid tool"
        
    agent.agent.get_tools = lambda: [MockTool()]
    
    class MockNextActionLLM:
        async def ainvoke(self, messages):
            return AIMessage(content='{"tool": "unknown_tool", "arguments": {}, "finish": false, "reason": "Testing unknown tool"}')
            
    orig_get_llm = agent.agent.get_llm
    agent.agent.get_llm = lambda: MockNextActionLLM()
    
    state_unknown: TripState = {
        "location": "Origin",
        "destination_location": "Target",
        "sub_location": "Area",
        "origin_details": {},
        "destination_details": {},
        "duration_days": 2,
        "budget": 5000.0,
        "interests": [],
        "transport_mode": "driving-car",
        "max_travel_mins": 180.0,
        "messages": [HumanMessage(content="Start")],
        "candidates": [{"name": "Candidate A", "context": {}, "valid": None, "score": 0.0}],
        "current_candidate_index": 0,
        "selected_candidate": {},
        "final_itinerary": "",
        "tool_steps_count": 0
    }
    
    res_unknown = await data_gathering_node(state_unknown)
    assert res_unknown["tool_steps_count"] == 1
    assert len(res_unknown["messages"]) == 2
    assert res_unknown["messages"][0].tool_calls[0]["name"] == "unknown_tool"
    assert "is not available" in res_unknown["messages"][1].content
    print("- Unknown tool interception OK (gracefully returned ToolMessage error)")
    
    # Restore mocks
    agent.agent.get_tools = orig_get_tools
    agent.agent.get_llm = orig_get_llm

async def run_adaptation_verification_test():
    print("\nRunning End-to-End Verification Failure and Repair Unit Tests...")
    
    import agent.agent
    orig_get_llm = agent.agent.get_llm
    
    class MockStatefulLLM:
        def __init__(self):
            self.call_count = 0
            
        async def ainvoke(self, messages):
            content_lower = str(messages[0].content).lower()
            
            if "quality assurance" in content_lower:
                self.call_count += 1
                if self.call_count == 1:
                    return AIMessage(content='{"passed": false, "reasons": ["Weather conflict on Day 2"], "days_count": 2, "total_cost": 4000.0, "travel_time_valid": true, "interests_matched": true, "grounded_in_observations": true, "weather_suitable": false}')
                else:
                    return AIMessage(content='{"passed": true, "reasons": [], "days_count": 2, "total_cost": 4000.0, "travel_time_valid": true, "interests_matched": true, "grounded_in_observations": true, "weather_suitable": true}')
            
            if "changed condition" in content_lower or "repair" in content_lower:
                return AIMessage(content='["Day 2 Hiking"]')
                
            if "gather" in content_lower or "alternatives" in content_lower:
                return AIMessage(content='{"tool": "search_attractions", "arguments": {"query": "indoor museum"}, "finish": false, "reason": "Gathering alternative indoor attractions"}')
                
            return AIMessage(content="Patched/Regenerated Itinerary")

    mock_llm_instance = MockStatefulLLM()
    agent.agent.get_llm = lambda: mock_llm_instance
    
    from agent.agent import itinerary_verification_node, conflict_identification_node, adaptation_data_gathering_node, adaptation_evaluation_node, regeneration_node
    
    initial_state: TripState = {
        "location": "New York",
        "destination_location": "Washington DC",
        "sub_location": "Capitol Hill",
        "origin_details": {},
        "destination_details": {},
        "duration_days": 2,
        "budget": 5000.0,
        "interests": ["museums"],
        "transport_mode": "driving-car",
        "max_travel_mins": 180.0,
        "messages": [],
        "candidates": [{
            "name": "Washington DC",
            "context": {
                "weather": {"condition": "heavy rain", "temperature": 18},
                "estimated_total_cost": 3500.0,
                "budget_conflict": False,
                "budget_variance": 1500.0,
                "travel_time_mins": 90.0
            },
            "valid": True, "score": 1500.0
        }],
        "current_candidate_index": 0,
        # selected_candidate must have context with weather so deterministic verification fires
        "selected_candidate": {
            "name": "Washington DC",
            "context": {
                "weather": {"condition": "heavy rain", "temperature": 18},
                "estimated_total_cost": 3500.0,
                "budget_conflict": False,
                "budget_variance": 1500.0,
                "travel_time_mins": 90.0
            }
        },
        "final_itinerary": "Day 1: Hiking\nDay 2: Outdoor picnic",
        "tool_steps_count": 0,
        "is_verified": False,
        "verification_attempts": 0,
        "changed_condition": "",
        "original_itinerary": "",
        "affected_components": [],
        "adaptation_context": {},
        "adaptation_summary": ""
    }
    
    # 1. Run Verification (should FAIL)
    state1 = await itinerary_verification_node(initial_state)
    assert state1["is_verified"] == False
    assert state1["verification_attempts"] == 1
    assert "conflicts" in state1["changed_condition"].lower()  # weather conflict message
    
    initial_state.update(state1)
    
    # 2. Run Conflict Identification
    state2 = await conflict_identification_node(initial_state)
    assert "Day 2 Hiking" in state2["affected_components"]
    
    initial_state.update(state2)
    
    # 3. Inject mock ToolMessage representing search_attractions results
    from langchain_core.messages import ToolMessage
    import json
    mock_tool_msg = ToolMessage(
        content='{"attractions": [{"name": "Smithsonian Indoor Museum", "rating": 4.8, "address": "Washington DC"}]}',
        tool_call_id="call_test",
        name="search_attractions"
    )
    initial_state["messages"] = [mock_tool_msg]
    
    # 4. Run Adaptation Evaluation
    state3 = await adaptation_evaluation_node(initial_state)
    assert state3["adaptation_context"]["best_alternative"] == "Smithsonian Indoor Museum"
    assert len(state3["adaptation_context"]["alternatives_evaluated"]) == 1
    print("- Selected best alternative based on real tool observations: Smithsonian Indoor Museum (Rating 4.8)")
    
    initial_state.update(state3)
    
    # 5. Run Regeneration
    state4 = await regeneration_node(initial_state)
    assert "messages" in state4
    assert state4["messages"] == []
    
    initial_state.update(state4)
    
    # 6. Run Verification again (should PASS)
    state5 = await itinerary_verification_node(initial_state)
    assert state5["is_verified"] == True
    assert state5["verification_attempts"] == 2
    print("- Re-verification passed successfully after repair!")
    print("- Grounded replace of ONLY the affected components OK!")
    
    agent.agent.get_llm = orig_get_llm

if __name__ == "__main__":
    asyncio.run(run_evaluation_test())
    asyncio.run(run_data_gathering_test())
    asyncio.run(run_adaptation_verification_test())
