import asyncio
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "agent"))

# Mock GROQ_API_KEY before importing anything that initializes ChatGroq
os.environ["GROQ_API_KEY"] = "gsk_1234567890123456789012345678901234567890"

from agent.state import TripState
from agent.graph import trip_graph, adapt_graph

# We need to patch the ChatGroq llm used in agent.py
import agent.agent
from langchain_core.messages import AIMessage

class MockLLM:
    def bind_tools(self, tools):
        return self
        
    async def ainvoke(self, messages):
        # Determine response based on the system prompt context
        if "candidates" in str(messages[0].content).lower() or "destination" in str(messages[0].content).lower():
            if "identify" in str(messages[0].content).lower() or "extract" in str(messages[0].content).lower():
                return AIMessage(content='["Mock City A", "Mock City B"]')
        
        if "changed condition" in str(messages[0].content).lower() or "repair" in str(messages[0].content).lower():
            return AIMessage(content='["Mock Component"]')

                
        # For data gathering node
        if "gather" in str(messages[0].content).lower() or "alternatives" in str(messages[0].content).lower():
            return AIMessage(content="DONE_GATHERING")
                
        return AIMessage(content="Mocked LLM Response Itinerary")

# Apply patch
agent.agent.get_llm = lambda: MockLLM()

async def test_trip_graph():
    print("Testing Trip Graph transitions...")
    initial_state: TripState = {
        "location": "New York, NY",
        "duration_days": 2,
        "budget": 800.0,
        "interests": ["Museums", "Food"],
        "transport_mode": "driving-car",
        "max_travel_mins": 180.0,
        "messages": [],
        "candidates": [],
        "current_candidate_index": 0,
        "selected_candidate": {},
        "final_itinerary": ""
    }
    
    final_state = await trip_graph.ainvoke(initial_state, config={"recursion_limit": 20})
    assert "Mock City A" in [c["name"] for c in final_state["candidates"]]
    print("SUCCESS: Trip Graph state transitions OK")

async def test_adapt_graph():
    print("Testing Adapt Graph transitions...")
    initial_state: TripState = {
        "location": "New York, NY",
        "duration_days": 2,
        "budget": 800.0,
        "interests": ["Museums", "Food"],
        "transport_mode": "driving-car",
        "max_travel_mins": 180.0,
        "messages": [],
        "candidates": [],
        "current_candidate_index": 0,
        "selected_candidate": {},
        "final_itinerary": "",
        "original_itinerary": "Original",
        "changed_condition": "Rain",
        "affected_components": [],
        "adaptation_context": {},
        "adaptation_summary": ""
    }
    
    final_state = await adapt_graph.ainvoke(initial_state, config={"recursion_limit": 20})
    assert "Mock Component" in final_state["affected_components"]
    print("SUCCESS: Adapt Graph state transitions OK")

if __name__ == "__main__":
    asyncio.run(test_trip_graph())
    asyncio.run(test_adapt_graph())
