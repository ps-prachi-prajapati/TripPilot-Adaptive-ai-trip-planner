from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from agent.state import TripState
from agent.agent import extraction_node, data_gathering_node, evaluation_node, generation_node, get_tools
from utils.logging import setup_logging

logger = setup_logging(__name__)

def _get_msg_content(msg) -> str:
    content = getattr(msg, "content", "")
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        parts = []
        for p in content:
            if isinstance(p, str):
                parts.append(p)
            elif isinstance(p, dict) and "text" in p:
                parts.append(p["text"])
            elif hasattr(p, "text"):
                parts.append(str(getattr(p, "text")))
        return "".join(parts)
    return str(content)

def build_graph():
    """Builds and compiles the 10-step Rank & Select LangGraph workflow."""
    
    workflow = StateGraph(TripState)
    
    # Add nodes
    workflow.add_node("extraction", extraction_node)
    workflow.add_node("data_gathering", data_gathering_node)
    workflow.add_node("tools", ToolNode(get_tools()))
    workflow.add_node("evaluation", evaluation_node)
    workflow.add_node("generation", generation_node)
    
    # Set entry point
    workflow.set_entry_point("extraction")
    
    # From extraction, we move to data gathering (which starts with candidate index 0)
    workflow.add_edge("extraction", "data_gathering")
    
    # Routing logic for the ReAct tool loop
    def route_tool_execution(state: TripState):
        """
        If the LLM called a tool, route to 'tools'.
        Otherwise, proceed to next candidate or evaluation.
        """
        messages = state.get("messages", [])
        if not messages:
            logger.info("[Graph Router] No messages in state. Routing to evaluation.")
            return "evaluation"
        last_message = messages[-1]
        
        # Did it call a tool?
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            tool_names = [tc['name'] for tc in last_message.tool_calls]
            logger.info(f"[Graph Router] LLM invoked tool(s): {tool_names}. Routing to 'tools' node.")
            return "tools"
            
        # If no tool calls, move to next candidate or evaluation
        idx = state.get("current_candidate_index", 0)
        candidates = state.get("candidates", [])
        
        if idx + 1 < len(candidates):
            logger.info(f"[Graph Router] Completed gathering for Candidate {idx+1}/{len(candidates)}. Routing to next candidate setup.")
            return "next_candidate"
        else:
            logger.info(f"[Graph Router] Completed gathering for all candidates. Routing to evaluation.")
            return "evaluation"

    # We need a small passthrough node to increment the candidate index and clear messages for the next candidate
    def next_candidate_node(state: TripState) -> dict:
        return {
            "current_candidate_index": state.get("current_candidate_index", 0) + 1,
            "messages": [] # Clear message history so the agent starts fresh for the next city
        }
    workflow.add_node("next_candidate_setup", next_candidate_node)

    # Edge logic
    workflow.add_conditional_edges(
        "data_gathering",
        route_tool_execution,
        {
            "tools": "tools",
            "next_candidate": "next_candidate_setup",
            "evaluation": "evaluation"
        }
    )
    
    workflow.add_edge("tools", "data_gathering") # After tool executes, return to LLM to assess
    workflow.add_edge("next_candidate_setup", "data_gathering") # Loop to the next candidate
    
    workflow.add_edge("evaluation", "generation")
    workflow.add_edge("generation", END)
    
    return workflow.compile()

# Global graph instances
trip_graph = build_graph()

def build_adapt_graph():
    """Builds the dedicated LangGraph workflow for Adaptive Re-planning."""
    from agent.agent import conflict_identification_node, adaptation_data_gathering_node, adaptation_evaluation_node, regeneration_node
    
    adapt_workflow = StateGraph(TripState)
    
    adapt_workflow.add_node("conflict_id", conflict_identification_node)
    adapt_workflow.add_node("adapt_gather", adaptation_data_gathering_node)
    adapt_workflow.add_node("adapt_tools", ToolNode(get_tools()))
    adapt_workflow.add_node("adapt_eval", adaptation_evaluation_node)
    adapt_workflow.add_node("regeneration", regeneration_node)
    
    adapt_workflow.set_entry_point("conflict_id")
    
    adapt_workflow.add_edge("conflict_id", "adapt_gather")
    
    def route_adapt_tools(state: TripState):
        messages = state.get("messages", [])
        if not messages:
            return "adapt_eval"
        last_message = messages[-1]
        
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "adapt_tools"
            
        return "adapt_eval"
        
    adapt_workflow.add_conditional_edges(
        "adapt_gather",
        route_adapt_tools,
        {
            "adapt_tools": "adapt_tools",
            "adapt_eval": "adapt_eval"
        }
    )
    
    adapt_workflow.add_edge("adapt_tools", "adapt_gather")
    adapt_workflow.add_edge("adapt_eval", "regeneration")
    adapt_workflow.add_edge("regeneration", END)
    
    return adapt_workflow.compile()

adapt_graph = build_adapt_graph()

