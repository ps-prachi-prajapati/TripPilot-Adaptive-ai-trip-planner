import pytest
import asyncio
import os
import sys
from langchain_core.messages import AIMessage, ToolMessage, HumanMessage
from mcp_client.client import MultiServerMCPClient
from agent.state import TripState
from agent.graph import trip_graph

@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.mark.asyncio
async def test_mcp_integration():
    print("\nStarting Real MCP Client...")
    client = MultiServerMCPClient()
    
    # 1. MCP tool discovery
    await client.connect()
    assert len(client.available_tools) > 0, "No tools discovered!"
    print(f"[OK] Discovered {len(client.available_tools)} tools.")
    
    tool_names = [t["name"] for t in client.available_tools]
    assert "calculate_trip_cost" in tool_names, "Budget tool calculate_trip_cost not discovered!"
    assert "get_weather_forecast" in tool_names, "Weather tool get_weather_forecast not discovered!"
    assert "search_attractions" in tool_names, "Places tool search_attractions not discovered!"
    assert "calculate_travel_time" in tool_names, "Transport tool calculate_travel_time not discovered!"
    print("[OK] Discovery verified for all 4 MCP servers.")
    
    # 2. Weather suitability tool
    res_weather = await client.call_tool("check_weather_suitability", {
        "forecast_text": "Heavy rain and thunderstorms",
        "activities": ["Hiking", "Museum"]
    })
    content_weather = "".join(c.text for c in res_weather.content if hasattr(c, "text"))
    assert "Weather Conflicts Detected" in content_weather
    assert "Hiking" in content_weather
    print("[OK] Weather tool constraints checked successfully.")
    
    # 3. Places tool
    res_places = await client.call_tool("search_destinations", {"query": ""})
    content_places = "".join(c.text for c in res_places.content if hasattr(c, "text"))
    assert "Query cannot be empty" in content_places
    print("[OK] Places tool empty input validation checked successfully.")
    
    # 4. Transport tool
    res_transport = await client.call_tool("find_transport_options", {})
    content_transport = "".join(c.text for c in res_transport.content if hasattr(c, "text"))
    assert "driving-car" in content_transport
    print("[OK] Transport tool supported modes checked successfully.")
    
    # 5. Budget tool
    res_budget = await client.call_tool("calculate_trip_cost", {
        "days": 3,
        "tier": "mid",
        "transport_cost": 100.0,
        "activities_cost": 150.0
    })
    content_budget = "".join(c.text for c in res_budget.content if hasattr(c, "text"))
    assert "11850" in content_budget
    print("[OK] Budget tool calculate_trip_cost checked successfully.")
    
    # 6. Unknown tool/error handling
    with pytest.raises(ValueError) as excinfo:
        await client.call_tool("unknown_tool_xyz", {})
    assert "Tool unknown_tool_xyz not found" in str(excinfo.value)
    print("[OK] Unknown tool error handling checked successfully.")
    
    # 7. Empty result handling
    lc_tools = client.get_langchain_tools()
    weather_tool_lc = next(t for t in lc_tools if t.name == "check_weather_suitability")
    res_lc = await weather_tool_lc.coroutine(forecast_text="Sunny", activities=["Hiking"])
    assert "All activities appear suitable" in res_lc
    
    # Verify empty/error wrap logic
    res_empty = await weather_tool_lc.coroutine(forecast_text=" ", activities=[" "])
    assert "returned empty results" in res_empty or "Error" in res_empty or "cannot be empty" in res_empty
    print("[OK] Empty results handling verified.")
    
    # 8. API failure handling
    res_fail = await client.call_tool("get_weather_forecast", {
        "location": "London, UK",
        "days": 1
    })
    content_fail = "".join(c.text for c in res_fail.content if hasattr(c, "text"))
    assert "Error" in content_fail or "Valid OPENWEATHERMAP_API_KEY is not set" in content_fail
    print("[OK] API failure/missing-key handling verified.")
    
    # 9. LangGraph tool-calling loop (Integration Test)
    print("Testing LangGraph integration loop...")
    import agent.agent
    orig_client = agent.agent.mcp_client
    agent.agent.mcp_client = client
    
    from agent.graph import build_graph
    integration_graph = build_graph()
    
    class MockStatefulLLM:
        async def ainvoke(self, messages):
            has_tool_results = any(getattr(msg, "type", "") == "tool" for msg in messages)
            content_lower = str(messages[-1].content).lower() if messages else ""
            
            # QA/Verification Node mock
            if "quality assurance" in content_lower or "verify" in content_lower:
                return AIMessage(content='{"passed": true, "reasons": [], "days_count": 2, "total_cost": 4000.0, "travel_time_valid": true, "interests_matched": true, "grounded_in_observations": true, "weather_suitable": true}')
                
            # Candidates Extraction mock
            if "candidates" in content_lower or "destination" in content_lower:
                if "identify" in content_lower or "extract" in content_lower:
                    return AIMessage(content='["Washington DC"]')
            
            # Data Gathering node: first call tool, second call finish
            if "washington dc" in content_lower or "gather" in content_lower or "nudge" in content_lower or "tool output" in content_lower:
                if not has_tool_results:
                    return AIMessage(
                        content="Decided to query trip cost.",
                        tool_calls=[{
                            "name": "calculate_trip_cost",
                            "args": {"days": 3, "tier": "mid", "transport_cost": 100.0, "activities_cost": 150.0},
                            "id": "call_integration_1"
                        }]
                    )
                else:
                    return AIMessage(content='{"finish": true, "reason": "Gathered budget details successfully."}')
                    
            return AIMessage(content="Final Integration Itinerary")
            
    orig_get_llm = agent.agent.get_llm
    mock_llm = MockStatefulLLM()
    agent.agent.get_llm = lambda: mock_llm
    
    initial_state: TripState = {
        "location": "New York, NY",
        "duration_days": 2,
        "budget": 5000.0,
        "interests": ["Museums"],
        "transport_mode": "driving-car",
        "max_travel_mins": 180.0,
        "messages": [],
        "candidates": [],
        "current_candidate_index": 0,
        "selected_candidate": {},
        "final_itinerary": "",
        "tool_steps_count": 0,
        "is_verified": False,
        "verification_attempts": 0,
        "changed_condition": "",
        "original_itinerary": "",
        "affected_components": [],
        "adaptation_context": {},
        "adaptation_summary": "",
        "technical_logs": []
    }
    
    final_state = await integration_graph.ainvoke(initial_state, config={"recursion_limit": 20})
    
    assert len(final_state["candidates"]) > 0
    washington = final_state["candidates"][0]
    assert washington["name"] == "Washington DC"
    print("FINAL STATE MESSAGES:")
    for m in final_state["messages"]:
        if type(m).__name__ == "ToolMessage":
            print(f"- ToolMessage: {m.content}")
        else:
            print(f"- {type(m).__name__} (name={getattr(m, 'name', '')}): {str(m.content)[:100]}")
    assert any("11850" in str(msg.content) for msg in final_state["messages"]), "ToolMessage containing real calculate_trip_cost result (11850) not found in messages!"
    print("[OK] LangGraph tool-calling loop executed successfully (Mock LLM -> ToolNode/MCP -> Observation -> LLM -> Response)!")
    
    # Restore overrides
    agent.agent.mcp_client = orig_client
    agent.agent.get_llm = orig_get_llm
    
    await client.disconnect()
    print("All Real MCP Integration Tests completed successfully.")
