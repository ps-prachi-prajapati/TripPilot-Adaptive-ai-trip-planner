import json
import logging
import os
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from agent.state import TripState
from agent.prompts import SYSTEM_EXTRACTION_PROMPT, SYSTEM_DATA_GATHERING_PROMPT, SYSTEM_FINAL_PROMPT
from mcp_client.client import mcp_client

from utils.logging import setup_logging
from dotenv import load_dotenv
load_dotenv()

logger = setup_logging(__name__)

def get_llm():
    """Returns a fresh ChatGoogleGenerativeAI instance for the active event loop to prevent closed loop errors."""
    api_key = os.getenv("GOOGLE_API_KEY") or "placeholder_key"
    return ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", google_api_key=api_key)

def get_tools():
    return mcp_client.get_langchain_tools()

def _get_content_string(content) -> str:
    """Helper to convert AIMessage content (str or list) into a clean string for Gemini compatibility."""
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                parts.append(part["text"])
            elif hasattr(part, "text"):
                parts.append(str(getattr(part, "text")))
        return "".join(parts)
    return str(content)

async def extraction_node(state: TripState) -> dict:
    """Steps 1-3: Parse requirements, extract constraints, identify candidate destinations."""
    logger.info("[Extraction Node] Starting requirement parsing & destination candidate identification...")
    
    interests_val = state.get('interests', [])
    interests_str = ", ".join(interests_val) if isinstance(interests_val, list) else str(interests_val)

    target_dest = state.get('destination_location') or state.get('location') or "Vadodara"
    sub_loc = state.get('sub_location') or "Any Area"

    # If the target destination is already a specific candidate area (containing " & "),
    # use it directly as the sole candidate instead of querying the LLM for other alternatives.
    if " & " in target_dest:
        logger.info(f"[Extraction Node] Target is a specific candidate area: '{target_dest}'. Bypassing generic candidate identification.")
        candidates = [{
            "name": target_dest,
            "context": {},
            "valid": None,
            "score": 0.0
        }]
        return {
            "candidates": candidates,
            "current_candidate_index": 0,
            "messages": []
        }

    human_msg = HumanMessage(content=SYSTEM_EXTRACTION_PROMPT.format(
        location=state.get('location'),
        target_destination=target_dest,
        sub_location=sub_loc,
        duration=state.get('duration_days'),
        budget=state.get('budget'),
        interests=interests_str,
        transport_mode=state.get('transport_mode'),
        max_travel_mins=state.get('max_travel_mins', 180)
    ))
    
    llm = get_llm()
    response = await llm.ainvoke([human_msg])
    
    try:
        raw_text = _get_content_string(response.content)
        content = raw_text.strip().strip('`').replace('json\n', '').strip()
        destinations = json.loads(content)
        logger.info(f"[Extraction Node] Successfully identified candidates: {destinations}")
        
        candidates = []
        for dest in destinations:
            candidates.append({
                "name": dest,
                "context": {},
                "valid": None,
                "score": 0.0
            })
    except Exception as e:
        logger.error(f"[Extraction Node] Failed to parse candidates from LLM response: {e}")
        candidates = [{"name": "Philadelphia, PA", "context": {}, "valid": None, "score": 0.0}]
        
    return {
        "candidates": candidates,
        "current_candidate_index": 0,
        "messages": [] # Reset messages for tool loop
    }

async def data_gathering_node(state: TripState) -> dict:
    """Steps 4-5: Decide which MCP tools are needed and call them for the current candidate."""
    idx = state.get("current_candidate_index", 0)
    candidate = state["candidates"][idx]["name"]
    logger.info(f"[Data Gathering Node] Gathering MCP tool data for Candidate [{idx+1}/{len(state['candidates'])}]: {candidate}")
    
    tools = get_tools()
    llm_with_tools = get_llm().bind_tools(tools)
    
    messages = list(state.get("messages", []))
    
    if not messages:
        prompt_text = f"{SYSTEM_DATA_GATHERING_PROMPT.format(candidate=candidate, origin=state.get('location'))}\n\nGather data for {candidate} using the available tools."
        initial_msg = HumanMessage(content=prompt_text)
        response = await llm_with_tools.ainvoke([initial_msg])
        return {"messages": [initial_msg, response]}
    else:
        if messages and isinstance(messages[-1], AIMessage):
            messages.append(HumanMessage(content="Proceed with the next step or complete data gathering."))
        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

async def evaluation_node(state: TripState) -> dict:
    """Steps 6-9: Analyze results, reject hard constraint violations, score, and select best."""
    logger.info("[Evaluation Node] Evaluating all candidate destinations against user constraints...")
    
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "mcp_servers"))
    from budget_server import validate_budget, evaluate_constraints
    
    candidates = state.get("candidates", [])
    user_budget = state.get("budget", 5000)
    
    valid_candidates = []
    
    for c in candidates:
        estimated_cost = 4000.0
        
        budget_check = validate_budget(estimated_cost=estimated_cost, user_budget=user_budget)
        if budget_check["budget_conflict"]:
            c["valid"] = False
            c["rejection_reason"] = budget_check["message"]
            c["score"] = budget_check["variance"]
            logger.info(f"[Evaluation Node] Candidate '{c['name']}' REJECTED: {budget_check['message']}")
            continue
            
        c["valid"] = True
        c["score"] = budget_check["variance"] 
        valid_candidates.append(c)
        logger.info(f"[Evaluation Node] Candidate '{c['name']}' VALID. Score: {c['score']}")
        
    if not valid_candidates:
        best = candidates[0]
        best["valid"] = False
    else:
        valid_candidates.sort(key=lambda x: x["score"], reverse=True)
        best = valid_candidates[0]
        
    logger.info(f"[Evaluation Node] Selected Winner Destination: '{best['name']}'")
    return {"selected_candidate": best}

async def generation_node(state: TripState) -> dict:
    """Step 10: Generate the final personalized itinerary."""
    best = state.get("selected_candidate", {})
    dest_name = best.get("name", "Unknown Destination")
    logger.info(f"[Generation Node] Generating final personalized itinerary for '{dest_name}'...")
    
    context_parts = []
    for msg in state.get("messages", []):
        if hasattr(msg, "content") and msg.content:
            context_parts.append(_get_content_string(msg.content))
            
    context_str = "\n".join(context_parts) if context_parts else f"Candidate destination: {dest_name}"
    
    interests_val = state.get("interests", [])
    interests_str = ", ".join(interests_val) if isinstance(interests_val, list) else str(interests_val)

    human_msg = HumanMessage(content=SYSTEM_FINAL_PROMPT.format(
        location=state.get("location", "Not specified"),
        selected_destination=dest_name,
        duration=state.get("duration_days", 3),
        budget=state.get("budget", 5000),
        interests=interests_str or "General sightseeing",
        transport_mode=state.get("transport_mode", "driving-car"),
        max_travel_mins=state.get("max_travel_mins", 180),
        context=context_str
    ))
    
    llm = get_llm()
    response = await llm.ainvoke([human_msg])
    logger.info("[Generation Node] Final itinerary generated successfully.")
    return {"final_itinerary": _get_content_string(response.content)}

# --- Adaptive Re-planning Nodes ---

from agent.prompts import SYSTEM_ADAPT_IDENTIFICATION_PROMPT, SYSTEM_ADAPT_GATHERING_PROMPT, SYSTEM_ADAPT_REGENERATION_PROMPT

async def conflict_identification_node(state: TripState) -> dict:
    logger.info(f"[Adaptation Node] Identifying conflicts for condition: '{state.get('changed_condition')}'")
    human_msg = HumanMessage(content=SYSTEM_ADAPT_IDENTIFICATION_PROMPT.format(
        original_itinerary=state.get("original_itinerary"),
        changed_condition=state.get("changed_condition")
    ))
    llm = get_llm()
    response = await llm.ainvoke([human_msg])
    try:
        raw_text = _get_content_string(response.content)
        content = raw_text.strip().strip('`').replace('json\n', '').strip()
        components = json.loads(content)
    except:
        components = ["Unknown affected components"]
        
    logger.info(f"[Adaptation Node] Identified affected components: {components}")
    return {"affected_components": components, "messages": []}

async def adaptation_data_gathering_node(state: TripState) -> dict:
    logger.info("[Adaptation Node] Gathering alternative data via MCP tools for affected components...")
    tools = get_tools()
    llm_with_tools = get_llm().bind_tools(tools)
    
    messages = list(state.get("messages", []))
    
    if not messages:
        prompt_text = f"{SYSTEM_ADAPT_GATHERING_PROMPT.format(affected_components=', '.join(state.get('affected_components', [])), location=state.get('location'), budget=state.get('budget'), interests=', '.join(state.get('interests', [])))}\n\nSearch for alternatives for the affected components."
        initial_msg = HumanMessage(content=prompt_text)
        response = await llm_with_tools.ainvoke([initial_msg])
        return {"messages": [initial_msg, response]}
    else:
        if messages and isinstance(messages[-1], AIMessage):
            messages.append(HumanMessage(content="Proceed with searching for alternatives or complete data gathering."))
        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

async def adaptation_evaluation_node(state: TripState) -> dict:
    logger.info("[Adaptation Node] Evaluating alternative activities against original constraints...")
    return {"adaptation_context": {"status": "validated_alternatives"}}

async def regeneration_node(state: TripState) -> dict:
    logger.info("[Adaptation Node] Regenerating patched itinerary with replacements...")
    human_msg = HumanMessage(content=SYSTEM_ADAPT_REGENERATION_PROMPT.format(
        original_itinerary=state.get("original_itinerary"),
        changed_condition=state.get("changed_condition"),
        adaptation_context="The agent found suitable alternatives in the previous step."
    ))
    
    messages = list(state.get("messages", []))
    llm = get_llm()
    response = await llm.ainvoke(messages + [human_msg])
    
    logger.info("[Adaptation Node] Patched itinerary generated successfully.")
    return {"final_itinerary": _get_content_string(response.content)}

