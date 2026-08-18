import operator
from typing import Annotated, TypedDict, Any
from langchain_core.messages import BaseMessage

class TripState(TypedDict):
    """
    The state dictionary for the 10-step LangGraph Trip Planner Agent.
    """
    # User Inputs
    location: str
    destination_location: str
    sub_location: str
    origin_details: dict
    destination_details: dict
    duration_days: int
    budget: float
    interests: list[str]
    transport_mode: str
    max_travel_mins: float

    
    # LangChain Message History (For Tool execution)
    messages: Annotated[list[BaseMessage], operator.add]
    
    # Extracted Candidates (Steps 1-3)
    # List of dicts: {"name": str, "description": str, "valid": bool, "score": float, "context": dict}
    candidates: list[dict]
    
    # Active Candidate Tracking (for looping)
    current_candidate_index: int
    
    # Evaluation & Final Selection (Steps 7-9)
    selected_candidate: dict
    
    # Final Output (Step 10)
    final_itinerary: str
    
    # --- Adaptive Re-planning State ---
    original_itinerary: str
    changed_condition: str
    affected_components: list[str]
    adaptation_context: dict
    adaptation_summary: str
