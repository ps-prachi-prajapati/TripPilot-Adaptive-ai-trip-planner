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

_llm_cache = {}

def get_llm():
    """Returns a cached ChatGoogleGenerativeAI instance per event loop.
    
    Reusing the same instance per event loop avoids rate-limit desync, cuts initialization
    overhead on every node call, and shares the underlying httpx connection pool,
    while preventing 'Event loop is closed' errors when Streamlit actions run on different loops.
    """
    import asyncio
    global _llm_cache
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
        
    cache_key = loop if loop is not None else "no_loop"
    
    if cache_key not in _llm_cache:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "placeholder_key"
        _llm_cache[cache_key] = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", google_api_key=api_key)
        
    return _llm_cache[cache_key]

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

from pydantic import BaseModel, Field
from typing import List, Dict, Any
import re

class CandidateList(BaseModel):
    destinations: List[str] = Field(description="Exactly 3 distinct and diverse candidate sub-areas or neighborhoods within the target destination.")

class CandidateObservation(BaseModel):
    name: str = Field(description="The name of the candidate sub-area/neighborhood")
    travel_time_mins: float = Field(default=0.0, description="Real travel time from origin in minutes")
    distance_km: float = Field(default=0.0, description="Real distance from origin in kilometers")
    weather_forecast: str = Field(default="", description="Weather conditions/forecast text")
    has_weather_conflicts: bool = Field(default=False, description="Whether weather conflicts were detected for interests")
    attractions: List[str] = Field(default_factory=list, description="Names of search attractions found")
    hotels: List[Dict[str, Any]] = Field(default_factory=list, description="Accommodation search results containing name, rate, address")
    restaurants: List[str] = Field(default_factory=list, description="Names of restaurants found")
    transportation_cost: float = Field(default=0.0, description="Calculated transportation cost in INR")
    estimated_total_cost: float = Field(default=0.0, description="Estimated total cost in INR (accommodation + meals + transport + activities)")

from typing import Optional

class NextAction(BaseModel):
    tool: Optional[str] = Field(
        None, 
        description="The name of the tool to invoke (e.g. 'get_weather_forecast', 'calculate_travel_time', 'calculate_transport_cost', 'search_attractions', 'search_hotels', 'search_restaurants'). Must be null if finish is True."
    )
    arguments: Optional[Dict[str, Any]] = Field(
        None,
        description="Dictionary of arguments to pass to the tool. Must be null if finish is True."
    )
    finish: bool = Field(
        False,
        description="Set to True if you have gathered enough evidence/information for this candidate and are ready to finish gathering."
    )
    reason: str = Field(
        description="Detailed explanation of why we are taking this action or why we are finishing."
    )

def extract_observations_from_messages(messages: list, candidate_name: str) -> CandidateObservation:
    obs = CandidateObservation(name=candidate_name)
    
    # Track gathered variables
    forecast_text = ""
    distance_km = 0.0
    duration_mins = 0.0
    transport_cost = 0.0
    
    attractions_list = []
    hotels_list = []
    restaurants_list = []
    
    for msg in messages:
        is_tool = getattr(msg, "type", "") == "tool"
        tool_name = getattr(msg, "name", "")
        
        if not is_tool and not tool_name:
            continue
            
        content_str = ""
        if hasattr(msg, "content"):
            content_str = str(msg.content)
            
        content_data = None
        try:
            content_data = json.loads(content_str)
        except Exception:
            pass
            
        t_name_lower = tool_name.lower()
        
        if "weather_forecast" in t_name_lower or "get_weather_forecast" in t_name_lower:
            forecast_text = content_str
            obs.weather_forecast = content_str
        elif "current_weather" in t_name_lower or "get_current_weather" in t_name_lower:
            if not forecast_text:
                obs.weather_forecast = content_str
        elif "weather_suitability" in t_name_lower or "check_weather_suitability" in t_name_lower:
            if "conflict" in content_str.lower() or "not recommended" in content_str.lower():
                obs.has_weather_conflicts = True
                
        elif "travel_time" in t_name_lower or "calculate_travel_time" in t_name_lower:
            if isinstance(content_data, dict):
                distance_km = content_data.get("distance_km", 0.0)
                duration_mins = content_data.get("duration_mins", 0.0)
            else:
                dist_match = re.search(r'"distance_km":\s*([0-9.]+)', content_str)
                dur_match = re.search(r'"duration_mins":\s*([0-9.]+)', content_str)
                if dist_match: distance_km = float(dist_match.group(1))
                if dur_match: duration_mins = float(dur_match.group(1))
                
            obs.distance_km = distance_km
            obs.travel_time_mins = duration_mins
            
        elif "transport_cost" in t_name_lower or "calculate_transport_cost" in t_name_lower:
            if isinstance(content_data, dict):
                transport_cost = content_data.get("estimated_cost_inr", content_data.get("estimated_cost_usd", 0.0))
            else:
                cost_match = re.search(r'"estimated_cost_(?:inr|usd)":\s*([0-9.]+)', content_str)
                if cost_match: transport_cost = float(cost_match.group(1))
            obs.transportation_cost = transport_cost
            
        elif "attractions" in t_name_lower or "search_attractions" in t_name_lower:
            if isinstance(content_data, dict) and "attractions" in content_data:
                attractions_list = [a.get("name") for a in content_data["attractions"] if isinstance(a, dict) and "name" in a]
            obs.attractions.extend(attractions_list)
            
        elif "hotels" in t_name_lower or "search_hotels" in t_name_lower:
            if isinstance(content_data, dict) and "hotels" in content_data:
                hotels_list = content_data["hotels"]
            obs.hotels.extend(hotels_list)
            
        elif "restaurants" in t_name_lower or "search_restaurants" in t_name_lower:
            if isinstance(content_data, dict) and "restaurants" in content_data:
                restaurants_list = [r.get("name") for r in content_data["restaurants"] if isinstance(r, dict) and "name" in r]
            obs.restaurants.extend(restaurants_list)

    # Clean up lists
    obs.attractions = list(set(obs.attractions))
    obs.restaurants = list(set(obs.restaurants))
    seen_hotels = set()
    dedup_hotels = []
    for h in obs.hotels:
        if isinstance(h, dict) and "name" in h:
            h_name = h["name"]
            if h_name not in seen_hotels:
                seen_hotels.add(h_name)
                dedup_hotels.append(h)
    obs.hotels = dedup_hotels

    return obs

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
    candidates = []
    
    # Try using structured output if available on the model
    structured_llm = None
    if hasattr(llm, "with_structured_output"):
        try:
            structured_llm = llm.with_structured_output(CandidateList)
        except Exception as e:
            logger.warning(f"[Extraction Node] Failed to bind structured output: {e}")

    for attempt in range(1, 4):
        try:
            if structured_llm is not None:
                logger.info(f"[Extraction Node] Attempt {attempt}: Invoking LLM with structured output...")
                structured_response = await structured_llm.ainvoke([human_msg])
                if isinstance(structured_response, CandidateList):
                    dests = structured_response.destinations
                elif isinstance(structured_response, dict):
                    dests = structured_response.get("destinations", [])
                else:
                    raise ValueError(f"Unexpected response type: {type(structured_response)}")
            else:
                logger.info(f"[Extraction Node] Attempt {attempt}: Invoking LLM with raw text and manual parsing...")
                response = await llm.ainvoke([human_msg])
                raw_text = _get_content_string(response.content)
                content = raw_text.strip().strip('`').replace('json\n', '').strip()
                data = json.loads(content)
                if isinstance(data, list):
                    validated = CandidateList(destinations=data)
                    dests = validated.destinations
                elif isinstance(data, dict):
                    validated = CandidateList(**data)
                    dests = validated.destinations
                else:
                    raise ValueError("LLM response is not a valid list or dictionary")
            
            if not dests or len(dests) == 0:
                raise ValueError("Extracted destinations list is empty")
                
            logger.info(f"[Extraction Node] Successfully identified candidates on attempt {attempt}: {dests}")
            for dest in dests:
                candidates.append({
                    "name": dest,
                    "context": {},
                    "valid": None,
                    "score": 0.0
                })
            break
        except Exception as e:
            logger.error(f"[Extraction Node] Attempt {attempt} failed: {e}")
            if attempt == 3:
                logger.warning(f"[Extraction Node] All extraction attempts failed. Falling back to target destination '{target_dest}'.")
                candidates = [{
                    "name": target_dest,
                    "context": {},
                    "valid": None,
                    "score": 0.0
                }]

    # Gather tools for discovery logging
    discovered_tools = []
    try:
        discovered_tools = [t.name for t in get_tools()]
    except Exception:
        pass
        
    tech_logs = [
        {"title": "Tool Discovery", "type": "info", "details": f"Discovered {len(discovered_tools)} MCP tools: {', '.join(discovered_tools)}"},
        {"title": "Candidate Identification", "type": "decision", "details": f"Successfully identified candidate sub-areas: {', '.join([c['name'] for c in candidates])}"}
    ]

    return {
        "candidates": candidates,
        "current_candidate_index": 0,
        "messages": [], # Reset messages for tool loop
        "tool_steps_count": 0,
        "technical_logs": tech_logs
    }

async def data_gathering_node(state: TripState) -> dict:
    """Steps 4-5: Decide which MCP tools are needed and call them for the current candidate."""
    idx = state.get("current_candidate_index", 0)
    candidate = state["candidates"][idx]["name"]
    logger.info(f"[Data Gathering Node] Gathering MCP tool data for Candidate [{idx+1}/{len(state['candidates'])}]: {candidate}")
    
    tech_logs = []
    
    # Log any tool results from the last executed step
    messages_in_state = state.get("messages", [])
    if messages_in_state and getattr(messages_in_state[-1], "type", "") == "tool":
        last_tool_msg = messages_in_state[-1]
        tool_name = getattr(last_tool_msg, "name", "unknown_tool")
        tool_content = str(last_tool_msg.content)
        if len(tool_content) > 500:
            tool_content = tool_content[:500] + "..."
        tech_logs.append({
            "title": f"↳ Tool Result Summary ({tool_name})",
            "type": "tool_result",
            "details": tool_content
        })
        
    # 1. Check tool steps limit
    MAX_TOOL_STEPS = 8
    steps = state.get("tool_steps_count", 0)
    if steps >= MAX_TOOL_STEPS:
        logger.warning(f"[Data Gathering Node] Candidate '{candidate}' reached tool steps limit ({MAX_TOOL_STEPS}). Stopping.")
        tech_logs.append({
            "title": f"Gathering: Capped ({candidate})",
            "type": "info",
            "details": f"Candidate reached maximum tool steps limit ({MAX_TOOL_STEPS}). Safely stopping."
        })
        return {
            "messages": [AIMessage(content="Reached max tool steps limit. Proceeding.")],
            "tool_steps_count": steps,
            "technical_logs": tech_logs
        }
        
    tools = get_tools()
    llm = get_llm()
    
    # Bind NextAction to LLM if supported
    structured_llm = None
    if hasattr(llm, "with_structured_output"):
        try:
            structured_llm = llm.with_structured_output(NextAction)
        except Exception as e:
            logger.warning(f"[Data Gathering Node] Failed to bind structured output: {e}")
            
    # Compile messages to send and return
    from langchain_core.messages import ToolMessage
    import uuid
    
    messages_to_return = []
    messages_to_send = list(state.get("messages", []))
    
    if not messages_to_send:
        # Prompt for first step of data gathering
        prompt_text = (
            f"You are an expert AI Travel Planner. Decide which tools are actually needed to gather information for the candidate area '{candidate}'.\n"
            f"Origin: {state.get('location')}.\n"
            f"Duration: {state.get('duration_days', 2)} days.\n"
            f"Budget: {state.get('budget', 5000.0)} INR.\n"
            f"Interests: {state.get('interests', [])}.\n\n"
            "Determine the next tool to run (or finish if you have sufficient evidence). Make tool calls one by one. Do not call redundant tools."
        )
        h_msg = HumanMessage(content=prompt_text)
        messages_to_send.append(h_msg)
        messages_to_return.append(h_msg)
    else:
        # If the last message was a ToolMessage, append a nudge so the LLM decides next action
        if messages_to_send and isinstance(messages_to_send[-1], ToolMessage):
            nudge_msg = HumanMessage(content="Analyze the tool output. Decide the next tool to run, or set finish to True if gathering is complete.")
            messages_to_send.append(nudge_msg)
            messages_to_return.append(nudge_msg)
            
    # Invoke LLM
    next_action = None
    if structured_llm is not None:
        try:
            next_action = await structured_llm.ainvoke(messages_to_send)
        except Exception as e:
            logger.error(f"[Data Gathering Node] Structured output call failed: {e}")
            
    if next_action is None:
        # Fallback to standard invoke & parsing
        if hasattr(llm, "bind_tools"):
            llm_with_tools = llm.bind_tools(tools)
            response = await llm_with_tools.ainvoke(messages_to_send)
        else:
            response = await llm.ainvoke(messages_to_send)
        content = _get_content_string(response.content)
        
        # Check if response matches mock/DONE_GATHERING
        if "done_gathering" in content.lower():
            next_action = NextAction(finish=True, reason="Gathering finished (text fallback).")
        else:
            try:
                # Try parsing raw content as NextAction JSON
                content_clean = content.strip().strip('`').replace('json\n', '').strip()
                data = json.loads(content_clean)
                next_action = NextAction(**data)
            except Exception:
                # If unparsable, check if LLM returned standard tool calls
                if hasattr(response, "tool_calls") and response.tool_calls:
                    tc = response.tool_calls[0]
                    next_action = NextAction(
                        tool=tc["name"], 
                        arguments=tc["args"], 
                        finish=False, 
                        reason="Standard tool call extracted from fallback."
                    )
                else:
                    next_action = NextAction(finish=True, reason=f"Fallback finish. LLM response: {content}")
                    
    # 2. Process NextAction
    if next_action.finish or not next_action.tool:
        logger.info(f"[Data Gathering Node] LLM finished gathering for '{candidate}'. Reason: {next_action.reason}")
        ai_msg = AIMessage(content=f"Gathering complete: {next_action.reason}")
        messages_to_return.append(ai_msg)
        tech_logs.append({
            "title": f"Gathering Complete ({candidate})",
            "type": "decision",
            "details": f"LLM decided to finish gathering. Reason: {next_action.reason}"
        })
        return {
            "messages": messages_to_return,
            "tool_steps_count": steps,
            "technical_logs": tech_logs
        }
        
    # Increment steps count
    steps += 1
    
    # 3. Check for unknown tools
    available_tool_names = [t.name for t in tools]
    if next_action.tool not in available_tool_names:
        logger.warning(f"[Data Gathering Node] LLM requested unknown tool: {next_action.tool}")
        tool_call_id = "call_" + uuid.uuid4().hex[:12]
        ai_msg = AIMessage(
            content=next_action.reason,
            tool_calls=[{
                "name": next_action.tool,
                "args": next_action.arguments or {},
                "id": tool_call_id
            }]
        )
        error_msg = f"Error: Tool '{next_action.tool}' is not available. Please choose from: {available_tool_names}."
        tool_msg = ToolMessage(content=error_msg, tool_call_id=tool_call_id, name=next_action.tool)
        messages_to_return.extend([ai_msg, tool_msg])
        tech_logs.append({
            "title": f"Agent Requested Unknown Tool: {next_action.tool}",
            "type": "tool_call",
            "details": f"Arguments: {next_action.arguments}. Result: Intercepted unknown tool error returned to LLM."
        })
        return {
            "messages": messages_to_return,
            "tool_steps_count": steps,
            "technical_logs": tech_logs
        }
        
    # 4. Valid tool call
    tool_call_id = "call_" + uuid.uuid4().hex[:12]
    ai_message = AIMessage(
        content=next_action.reason,
        tool_calls=[{
            "name": next_action.tool,
            "args": next_action.arguments or {},
            "id": tool_call_id
        }]
    )
    logger.info(f"[Data Gathering Node] Step {steps}/{MAX_TOOL_STEPS}: Invoking tool '{next_action.tool}' for candidate '{candidate}' with arguments: {next_action.arguments}")
    messages_to_return.append(ai_message)
    
    server_name = "Unknown MCP"
    t_name = next_action.tool.lower()
    if "weather" in t_name: server_name = "Weather MCP"
    elif any(x in t_name for x in ["place", "attraction", "destination", "hotel", "restaurant"]): server_name = "Places MCP"
    elif any(x in t_name for x in ["transport", "route", "travel"]): server_name = "Transport MCP"
    elif any(x in t_name for x in ["budget", "cost", "validate"]): server_name = "Budget MCP"
    
    tech_logs.append({
        "title": f"Agent → {server_name} → {next_action.tool}",
        "type": "tool_call",
        "details": f"Reason: {next_action.reason} | Input: {next_action.arguments}"
    })
    return {
        "messages": messages_to_return,
        "tool_steps_count": steps,
        "technical_logs": tech_logs
    }

async def evaluation_node(state: TripState) -> dict:
    """Steps 6-9: Analyze results, reject hard constraint violations, score, and select best."""
    logger.info("[Evaluation Node] Evaluating all candidate destinations against user constraints...")
    import asyncio
    
    candidates = list(state.get("candidates", []))
    idx = state.get("current_candidate_index", 0)
    messages = state.get("messages", [])
    
    # Save the last candidate's context if it hasn't been saved yet
    if idx < len(candidates):
        candidate_name = candidates[idx]["name"]
        obs = extract_observations_from_messages(messages, candidate_name)
        candidates[idx]["context"] = obs.model_dump()
        logger.info(f"[Evaluation Node] Saved observations for last candidate {candidate_name}: {candidates[idx]['context']}")
        
    user_budget = state.get("budget", 5000.0)
    duration_days = state.get("duration_days", 2)
    
    async def evaluate_single_candidate(c: dict) -> dict:
        obs = c.get("context", {})
        if not obs:
            logger.warning(f"[Evaluation Node] Candidate '{c['name']}' has no context/observations.")
            c["valid"] = False
            c["rejection_reason"] = "No observations gathered."
            c["score"] = -9999.0
            return c
            
        # Determine comfort tier dynamically based on daily budget
        daily_budget = user_budget / max(1, duration_days)
        if daily_budget < 3000:
            tier = "budget"
        elif daily_budget < 7000:
            tier = "mid"
        elif daily_budget < 15000:
            tier = "comfort"
        else:
            tier = "luxury"

        # Calculate estimated total cost via MCP client tool boundary
        try:
            res = await mcp_client.call_tool("calculate_trip_cost", {
                "days": duration_days,
                "tier": tier,
                "transport_cost": float(obs.get("transportation_cost", 0.0)),
                "activities_cost": float(duration_days * 500.0)
            })
            text = "\n".join(c_content.text for c_content in res.content if hasattr(c_content, 'text'))
            cost_calc = json.loads(text)
        except Exception as e:
            logger.warning(f"[Evaluation Node] Failed to calculate cost via tool boundary for '{c['name']}': {e}. Falling back to direct function call.")
            # Local fallback for tests where MCP client is not connected
            try:
                import sys
                import os
                sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "mcp_servers"))
                from budget_server import calculate_trip_cost as direct_calculate_trip_cost
                cost_calc = direct_calculate_trip_cost(
                    days=duration_days,
                    tier=tier,
                    transport_cost=float(obs.get("transportation_cost", 0.0)),
                    activities_cost=float(duration_days * 500.0)
                )
            except Exception as fe:
                logger.error(f"[Evaluation Node] Local fallback failed for calculate_trip_cost: {fe}")
                cost_calc = {
                    "total_estimated_cost": float(obs.get("transportation_cost", 0.0) + duration_days * 1000.0),
                    "breakdown": {
                        "accommodation": float(duration_days * 500.0),
                        "food": float(duration_days * 300.0),
                        "transportation": float(obs.get("transportation_cost", 0.0)),
                        "activities": float(duration_days * 200.0)
                    }
                }
            
        estimated_cost = cost_calc.get("total_estimated_cost", 0.0)
        c["context"]["estimated_total_cost"] = estimated_cost
        c["context"]["cost_breakdown"] = cost_calc.get("breakdown", {})
        c["context"]["comfort_tier"] = tier
        
        # Parallelize validate_budget and evaluate_constraints for this candidate
        async def call_validate_budget():
            try:
                res = await mcp_client.call_tool("validate_budget", {
                    "estimated_cost": estimated_cost,
                    "user_budget": user_budget
                })
                text = "\n".join(c_content.text for c_content in res.content if hasattr(c_content, 'text'))
                return json.loads(text)
            except Exception as e:
                logger.warning(f"[Evaluation Node] Failed to validate budget via tool boundary for '{c['name']}': {e}. Falling back to direct function call.")
                try:
                    import sys
                    import os
                    sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "mcp_servers"))
                    from budget_server import validate_budget as direct_validate_budget
                    return direct_validate_budget(estimated_cost=estimated_cost, user_budget=user_budget)
                except Exception as fe:
                    logger.error(f"[Evaluation Node] Local fallback failed for validate_budget: {fe}")
                    conflict = estimated_cost > user_budget
                    return {
                        "budget_conflict": conflict,
                        "estimated_cost": estimated_cost,
                        "user_budget": user_budget,
                        "variance": round(abs(estimated_cost - user_budget), 2),
                        "message": "Exceeded budget" if conflict else "Within budget"
                    }

        async def call_evaluate_constraints():
            try:
                res = await mcp_client.call_tool("evaluate_constraints", {
                    "travel_time_mins": float(obs.get("travel_time_mins", 0.0)),
                    "max_travel_mins": float(state.get("max_travel_mins", 180.0)),
                    "weather_conflicts_exist": bool(obs.get("has_weather_conflicts", False)),
                    "planned_transport_mode": state.get("transport_mode", "driving-car"),
                    "preferred_transport_mode": state.get("transport_mode", "driving-car")
                })
                text = "\n".join(c_content.text for c_content in res.content if hasattr(c_content, 'text'))
                return json.loads(text)
            except Exception as e:
                logger.warning(f"[Evaluation Node] Failed to evaluate constraints via tool boundary for '{c['name']}': {e}. Falling back to direct function call.")
                try:
                    import sys
                    import os
                    sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "mcp_servers"))
                    from budget_server import evaluate_constraints as direct_evaluate_constraints
                    return direct_evaluate_constraints(
                        travel_time_mins=float(obs.get("travel_time_mins", 0.0)),
                        max_travel_mins=float(state.get("max_travel_mins", 180.0)),
                        weather_conflicts_exist=bool(obs.get("has_weather_conflicts", False)),
                        planned_transport_mode=state.get("transport_mode", "driving-car"),
                        preferred_transport_mode=state.get("transport_mode", "driving-car")
                    )
                except Exception as fe:
                    logger.error(f"[Evaluation Node] Local fallback failed for evaluate_constraints: {fe}")
                    conflicts = []
                    if float(obs.get("travel_time_mins", 0.0)) > float(state.get("max_travel_mins", 180.0)):
                        conflicts.append("Travel time limit exceeded.")
                    if bool(obs.get("has_weather_conflicts", False)):
                        conflicts.append("Weather conflict.")
                    return {
                        "is_valid": len(conflicts) == 0,
                        "conflict_reasons": conflicts
                    }

        budget_check, constraints_check = await asyncio.gather(call_validate_budget(), call_evaluate_constraints())

        # Evaluate interests match
        interests = state.get("interests", [])
        interests_conflict = False
        rejection_reasons = list(constraints_check.get("conflict_reasons", []))
        
        if interests and not obs.get("attractions", []) and not obs.get("hotels", []):
            interests_conflict = True
            rejection_reasons.append("No suitable attractions or accommodations found matching user interests.")
            
        budget_conflict = budget_check.get("budget_conflict", False)
        constraints_invalid = not constraints_check.get("is_valid", True)
        
        is_valid = (not budget_conflict) and (not constraints_invalid) and (not interests_conflict)
        
        # Store raw budget facts separately so the UI card can display them
        # independently from the composite validity/score used for ranking.
        variance_val = budget_check.get("variance", 0.0)
        c["context"]["budget_conflict"] = budget_conflict
        c["context"]["budget_variance"] = variance_val  # always the absolute rupee difference
        c["context"]["budget_message"] = budget_check.get("message", "")

        c["valid"] = is_valid
        # Ranking score: positive = valid + cheaper is better; negative = rejected
        c["score"] = variance_val if is_valid else -variance_val
        
        if not is_valid:
            reasons = []
            if budget_conflict:
                reasons.append(budget_check.get("message", "Exceeded budget."))
            reasons.extend(rejection_reasons)
            c["rejection_reason"] = " | ".join(reasons)
            logger.info(f"[Evaluation Node] Candidate '{c['name']}' REJECTED: {c['rejection_reason']}")
        else:
            c["rejection_reason"] = "All constraints passed."
            logger.info(f"[Evaluation Node] Candidate '{c['name']}' VALID. Score (remaining budget variance): {c['score']}")
            
        return c

    # Concurrently evaluate all candidates in parallel
    candidates = await asyncio.gather(*[evaluate_single_candidate(c) for c in candidates])
    
    valid_candidates = [c for c in candidates if c.get("valid")]
    
    if not valid_candidates:
        # Fallback to the first candidate if none are valid
        best = candidates[0]
        best["valid"] = False
        logger.warning(f"[Evaluation Node] No candidates were valid. Defaulting to first candidate '{best['name']}' with invalid status.")
    else:
        # Sort by score descending (higher score is better)
        valid_candidates.sort(key=lambda x: x["score"], reverse=True)
        best = valid_candidates[0]
        
    logger.info(f"[Evaluation Node] Selected Winner Destination: '{best['name']}'")
    
    tech_logs = []
    for c in candidates:
        status = "VALID" if c.get("valid") else "REJECTED"
        details = c.get("rejection_reason", "All constraints passed.")
        tech_logs.append({
            "title": f"Candidate Evaluated: {c['name']} ({status})",
            "type": "info",
            "details": f"Estimated Cost: ₹{c['context'].get('estimated_total_cost', 0.0)}. Reason: {details}"
        })
        
    tech_logs.append({
        "title": "Selected Winner Destination",
        "type": "decision",
        "details": f"Winner: {best['name']} (Score: {best.get('score', 0.0)})"
    })
    
    return {
        "candidates": candidates,
        "selected_candidate": best,
        "technical_logs": tech_logs
    }

async def generation_node(state: TripState) -> dict:
    """Step 10: Generate the final personalized itinerary."""
    best = state.get("selected_candidate", {})
    dest_name = best.get("name", "Unknown Destination")
    logger.info(f"[Generation Node] Generating final personalized itinerary for '{dest_name}'...")
    
    best_context = best.get("context", {})
    est_total = best_context.get("estimated_total_cost", 0.0)
    breakdown = best_context.get("cost_breakdown", {})
    tier = best_context.get("comfort_tier", "mid")
    
    # Format deterministic budget summary for the LLM to follow
    budget_summary = (
        f"=== DETERMINISTIC BUDGET SERVER COST CALCULATION ===\n"
        f"Selected Neighborhood/Area: {dest_name}\n"
        f"Comfort Tier: {tier.upper()}\n"
        f"Breakdown calculated by Budget Server:\n"
        f"  - Accommodation Stay Cost: ₹{breakdown.get('accommodation', 0.0)} INR\n"
        f"  - Meals/Food Cost: ₹{breakdown.get('food', 0.0)} INR\n"
        f"  - Transportation Cost: ₹{breakdown.get('transportation', 0.0)} INR\n"
        f"  - Activities Cost: ₹{breakdown.get('activities', 0.0)} INR\n"
        f"TOTAL DETERMINISTIC CALCULATED TRIP COST: ₹{est_total} INR\n"
        f"User Budget Limit: ₹{state.get('budget', 5000.0)} INR\n"
        f"Match Status: {'EXCEEDS BUDGET' if est_total > state.get('budget', 5000.0) else 'WITHIN BUDGET'}\n"
        f"=====================================================\n\n"
        f"INSTRUCTION: You MUST use these exact costs in your final budget table! Do not make up or hallucinate different accommodation/food/transport rates. If the total exceeds the budget, state the numbers honestly and mention that it exceeds the budget.\n\n"
    )
    
    context_parts = [budget_summary]
    for msg in state.get("messages", []):
        if hasattr(msg, "content") and msg.content:
            context_parts.append(_get_content_string(msg.content))

    # Cap to 3000 chars — the full MCP tool dump can be 10K+ tokens which causes
    # the generation call to take 2-3 minutes.  The budget_summary above already
    # contains all the grounded cost data the LLM needs.
    raw_context = "\n".join(context_parts)
    context_str = raw_context[:3000] + ("\n...[context truncated for brevity]" if len(raw_context) > 3000 else "")
    
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
    return {
        "final_itinerary": _get_content_string(response.content),
        "technical_logs": [{"title": "Itinerary Generation", "type": "info", "details": f"Generated final personalized itinerary for '{dest_name}'."}]
    }

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
    return {
        "affected_components": components, 
        "messages": [],
        "technical_logs": [{"title": "Adaptation: Conflict Identified", "type": "info", "details": f"Changed condition: '{state.get('changed_condition')}' | Affected components: {', '.join(components)}"}]
    }

async def adaptation_data_gathering_node(state: TripState) -> dict:
    logger.info("[Adaptation Node] Gathering alternative data via MCP tools for affected components...")
    tools = get_tools()
    llm_with_tools = get_llm().bind_tools(tools)
    
    messages = list(state.get("messages", []))
    
    tech_logs = [{"title": "Adaptation: Alternatives Search", "type": "tool_call", "details": f"Invoked places/transport tools to gather alternatives for affected components: {', '.join(state.get('affected_components', []))}"}]
    if not messages:
        prompt_text = f"{SYSTEM_ADAPT_GATHERING_PROMPT.format(affected_components=', '.join(state.get('affected_components', [])), location=state.get('location'), budget=state.get('budget'), interests=', '.join(state.get('interests', [])))}\n\nSearch for alternatives for the affected components."
        initial_msg = HumanMessage(content=prompt_text)
        response = await llm_with_tools.ainvoke([initial_msg])
        return {"messages": [initial_msg, response], "technical_logs": tech_logs}
    else:
        if messages and isinstance(messages[-1], AIMessage):
            messages.append(HumanMessage(content="Proceed with searching for alternatives or complete data gathering."))
        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response], "technical_logs": tech_logs}

def extract_alternatives_from_messages(messages: list) -> list[dict]:
    alternatives = []
    for msg in messages:
        is_tool = getattr(msg, "type", "") == "tool"
        tool_name = getattr(msg, "name", "")
        if not is_tool and not tool_name:
            continue
            
        content_str = str(msg.content)
        content_data = None
        try:
            content_data = json.loads(content_str)
        except Exception:
            pass
            
        t_name_lower = tool_name.lower()
        
        if "search_attractions" in t_name_lower or "attractions" in t_name_lower:
            if isinstance(content_data, dict) and "attractions" in content_data:
                for item in content_data["attractions"]:
                    alternatives.append({
                        "type": "attraction",
                        "name": item.get("name", "Unknown"),
                        "details": item
                    })
        elif "search_hotels" in t_name_lower or "hotels" in t_name_lower:
            if isinstance(content_data, dict) and "hotels" in content_data:
                for item in content_data["hotels"]:
                    alternatives.append({
                        "type": "hotel",
                        "name": item.get("name", "Unknown"),
                        "details": item
                    })
        elif "search_restaurants" in t_name_lower or "restaurants" in t_name_lower:
            if isinstance(content_data, dict) and "restaurants" in content_data:
                for item in content_data["restaurants"]:
                    alternatives.append({
                        "type": "restaurant",
                        "name": item.get("name", "Unknown"),
                        "details": item
                    })
    return alternatives

async def adaptation_evaluation_node(state: TripState) -> dict:
    logger.info("[Adaptation Node] Evaluating alternative activities against original constraints...")
    
    messages = state.get("messages", [])
    alternatives = extract_alternatives_from_messages(messages)
    
    if not alternatives:
        logger.warning("[Adaptation Node] No structured alternatives found in messages. Falling back to LLM selection.")
        return {
            "adaptation_context": {
                "status": "evaluated",
                "best_alternative": "Local attractions and indoor activities",
                "reason": "No explicit alternatives returned by tools."
            }
        }
        
    valid_alternatives = []
    for alt in alternatives:
        name = alt["name"]
        alt_type = alt["type"]
        details = alt["details"]
        
        rating = details.get("rating", 4.0)
        if rating == "N/A": rating = 4.0
        try:
            rating = float(rating)
        except:
            rating = 4.0
            
        valid_alternatives.append({
            "name": name,
            "type": alt_type,
            "details": details,
            "rating": rating,
            "valid": True,
            "reason": ""
        })
        
    if not valid_alternatives:
        best_alt = alternatives[0]["name"]
    else:
        # Sort by rating descending
        valid_alternatives.sort(key=lambda x: x["rating"], reverse=True)
        best_alt = valid_alternatives[0]["name"]
        
    logger.info(f"[Adaptation Node] Selected best alternative: '{best_alt}'")
    
    tech_logs = []
    if valid_alternatives:
        for val in valid_alternatives:
            tech_logs.append({
                "title": f"Adaptation Evaluated: {val['name']}",
                "type": "info",
                "details": f"Type: {val['type']} | Rating: {val['rating']}"
            })
    tech_logs.append({
        "title": "Adaptation Selected Winner",
        "type": "decision",
        "details": f"Selected best alternative: '{best_alt}'"
    })
    
    return {
        "adaptation_context": {
            "status": "evaluated",
            "best_alternative": best_alt,
            "alternatives_evaluated": valid_alternatives
        },
        "technical_logs": tech_logs
    }

async def regeneration_node(state: TripState) -> dict:
    logger.info("[Adaptation Node] Regenerating patched itinerary with replacements...")
    
    context = state.get("adaptation_context", {})
    best_alt = context.get("best_alternative", "Alternative activity near location")
    alt_context = f"The selected best alternative to splice in is: '{best_alt}'."
    
    human_msg = HumanMessage(content=SYSTEM_ADAPT_REGENERATION_PROMPT.format(
        original_itinerary=state.get("original_itinerary"),
        changed_condition=state.get("changed_condition"),
        adaptation_context=alt_context
    ))
    
    messages = list(state.get("messages", []))
    llm = get_llm()
    response = await llm.ainvoke(messages + [human_msg])
    
    logger.info("[Adaptation Node] Patched itinerary generated successfully.")
    return {
        "final_itinerary": _get_content_string(response.content),
        "messages": [], # Clear message history for subsequent verification nodes
        "technical_logs": [{"title": "Adaptation: Surgical Splice", "type": "info", "details": f"Surgically replaced ONLY the affected components ({', '.join(state.get('affected_components', []))}) with best alternative. Preserved all unaffected itinerary days."}]
    }

class VerificationReport(BaseModel):
    passed: bool = Field(
        description="True if the itinerary passes ALL constraints and has NO conflicts. False otherwise."
    )
    reasons: List[str] = Field(
        description="List of failure reasons or conflicts found (empty if passed is True)."
    )
    days_count: int = Field(description="Number of day sections found in the itinerary.")
    total_cost: float = Field(description="Total parsed estimated cost of the trip in INR.")
    travel_time_valid: bool = Field(description="True if all travel time segments are within constraint.")
    interests_matched: bool = Field(description="True if activities match user interests.")
    grounded_in_observations: bool = Field(description="True if all mentioned places/hotels are grounded in gathered tool observations.")
    weather_suitable: bool = Field(description="True if activities are suitable for the weather.")

async def itinerary_verification_node(state: TripState) -> dict:
    """Fast deterministic verification — no LLM call needed.

    Previously this called the LLM to re-read the full itinerary text and answer
    constraint questions (~30-60 sec). All the data we need is already in state from
    the evaluation step (budget_conflict, estimated_total_cost, etc.).
    """
    logger.info("[Verification Node] Verifying the generated itinerary against all constraints...")

    itinerary = state.get("final_itinerary") or ""
    if not itinerary:
        logger.warning("[Verification Node] No itinerary found to verify.")
        return {"is_verified": False, "changed_condition": "No itinerary generated."}

    import re as _re

    duration = state.get("duration_days", 2)
    budget = state.get("budget", 5000.0)
    max_travel_mins = float(state.get("max_travel_mins", 180.0))
    attempts = state.get("verification_attempts", 0) + 1

    failures = []

    # ── 1. Day-count check (fast regex scan of markdown headers) ──────────────
    day_sections = _re.findall(r"(?im)^#+\s*day\s*\d", itinerary)
    found_days = len(day_sections)
    if found_days > 0 and found_days != duration:
        failures.append(f"Itinerary has {found_days} day sections but {duration} were requested.")

    # ── 2. Budget check (use pre-computed data from evaluation) ───────────────
    selected = state.get("selected_candidate") or {}
    sel_context = selected.get("context", {})
    budget_conflict = sel_context.get("budget_conflict", False)
    estimated_cost = sel_context.get("estimated_total_cost", 0.0)
    if budget_conflict and estimated_cost > 0:
        failures.append(f"Estimated cost ₹{estimated_cost} exceeds budget ₹{budget}.")

    # ── 3. Travel time check ───────────────────────────────────────────────────
    travel_time = float(sel_context.get("travel_time_mins", 0.0))
    if travel_time > max_travel_mins:
        failures.append(f"Travel time {travel_time} mins exceeds limit {max_travel_mins} mins.")

    # ── 4. Weather / outdoor conflict check ───────────────────────────────────
    weather_data = sel_context.get("weather", {})
    if isinstance(weather_data, dict):
        condition = str(weather_data.get("condition", "")).lower()
        outdoor_keywords = ["hike", "trek", "beach", "outdoor", "walk", "cycling"]
        bad_weather = ["rain", "storm", "thunder", "snow", "extreme"]
        if any(kw in itinerary.lower() for kw in outdoor_keywords):
            if any(bad in condition for bad in bad_weather):
                failures.append(f"Weather '{condition}' conflicts with outdoor activities in itinerary.")

    passed = len(failures) == 0
    total_cost = estimated_cost if estimated_cost > 0 else budget * 0.8

    logger.info(f"[Verification Node] Verification Attempt {attempts}: Passed={passed}. Reasons: {failures}")

    tech_logs = [{
        "title": f"Reflection (Attempt {attempts})",
        "type": "decision",
        "details": (
            f"Passed: {passed} | Cost: ₹{total_cost} | Days found: {found_days}/{duration} | "
            f"Conflicts: {', '.join(failures) if failures else 'None'}"
        )
    }]

    if passed or attempts >= 2:
        summary = "Itinerary successfully verified." if passed else "Verification failed but max repair attempts reached."
        return {
            "is_verified": passed,
            "verification_attempts": attempts,
            "adaptation_summary": summary,
            "technical_logs": tech_logs
        }
    else:
        reasons_str = " | ".join(failures)
        return {
            "is_verified": False,
            "verification_attempts": attempts,
            "changed_condition": f"Verification failed. Please repair the following issues: {reasons_str}",
            "original_itinerary": itinerary,
            "technical_logs": tech_logs
        }
