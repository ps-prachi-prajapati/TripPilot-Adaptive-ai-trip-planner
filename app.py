import streamlit as st
import asyncio
import time
from dotenv import load_dotenv

# Initialize basic logging
from utils.logging import setup_logging
logger = setup_logging(__name__)

# Load env variables
load_dotenv()

# Import backend dependencies safely
try:
    from agent.state import TripState
    from agent.graph import trip_graph, adapt_graph
    from mcp_client.client import mcp_client
    from ui.components import inject_custom_css, render_empty_state, render_agent_activity
    from ui.home import render_home_header
    from ui.planning import render_planning_sidebar
    from ui.itinerary import render_itinerary_tab
    from ui.recommendations import render_recommendations_tab
    from ui.budget import render_budget_tab
    from utils.validation import validate_trip_inputs
    from agent.demo_data import DEMO_INITIAL_STATE, DEMO_ADAPTED_STATE
except ImportError as e:
    st.error(f"Failed to load application modules: {e}")
    st.stop()

# Configure page
st.set_page_config(
    page_title="AI Adaptive Trip Planner",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject custom CSS for premium aesthetic
inject_custom_css()

def _run_async_task(coro):
    """
    Safely executes an async coroutine on Windows/Streamlit, 
    preventing 'Event loop is closed' errors during shutdown.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        try:
            pending = asyncio.all_tasks(loop)
            for t in pending:
                t.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.run_until_complete(loop.shutdown_asyncgens())
        except Exception:
            pass
        finally:
            loop.close()

async def generate_trip(initial_state: TripState):
    """Executes the full LangGraph Trip workflow with MCP."""
    try:
        await mcp_client.connect()
        final_state = await trip_graph.ainvoke(initial_state, config={"recursion_limit": 50})
        return final_state
    finally:
        await mcp_client.disconnect()

async def adapt_trip(state: TripState, condition: str):
    """Executes the LangGraph Adaptation workflow."""
    try:
        await mcp_client.connect()
        state["changed_condition"] = condition
        final_state = await adapt_graph.ainvoke(state, config={"recursion_limit": 50})
        return final_state
    finally:
        await mcp_client.disconnect()


def main():
    render_home_header()
    
    # Pre-process pending destination query before rendering widgets
    if "pending_dest_query" in st.session_state:
        st.session_state["dest_query_input"] = st.session_state.pop("pending_dest_query")
        st.session_state["auto_trigger_plan"] = True
        
    # Render Sidebar and get inputs
    inputs = render_planning_sidebar()
    
    # Handle Generation Trigger
    auto_trigger = st.session_state.get("auto_trigger_plan", False)
    if inputs["generate_btn"] or auto_trigger:
        st.session_state.pop("auto_trigger_plan", None)
        if not inputs["demo_mode"]:
            validation_error = validate_trip_inputs(inputs["location"], inputs["budget"])
            if validation_error:
                st.sidebar.warning(validation_error)
                return
            
        initial_state: TripState = {
            "location": inputs["location"],
            "destination_location": inputs["destination_location"],
            "sub_location": inputs["sub_location"],
            "origin_details": inputs.get("origin_details", {}),
            "destination_details": inputs.get("destination_details", {}),
            "duration_days": inputs["duration"],
            "budget": inputs["budget"],
            "interests": inputs["interests"],
            "transport_mode": inputs["transport"],
            "max_travel_mins": inputs["max_travel_mins"],
            "messages": [],
            "candidates": [],
            "current_candidate_index": 0,
            "selected_candidate": {},
            "final_itinerary": "",
            "original_itinerary": "",
            "changed_condition": "",
            "affected_components": [],
            "adaptation_context": {},
            "adaptation_summary": ""
        }

        
        # UI Status Display
        with st.status("AI Planning Status...", expanded=True) as status:
            st.write("✓ Understanding preferences")
            st.write("✓ Searching candidate destinations")
            st.write("✓ Checking weather & transport options (MCP)")
            st.write("✓ Evaluating options against constraints")
            
            try:
                if inputs["demo_mode"]:
                    time.sleep(2.5)
                    result = DEMO_INITIAL_STATE
                else:
                    result = _run_async_task(generate_trip(initial_state))
                    
                st.session_state['trip_state'] = result
                status.update(label="Trip Planning Complete!", state="complete", expanded=False)
            except Exception as e:
                logger.error(f"Trip generation failed: {e}", exc_info=True)
                status.update(label="Planning Failed", state="error", expanded=True)
                st.error(f"Integration Error: {str(e)}")
                return

    # Display Output if state exists
    if 'trip_state' in st.session_state:
        state = st.session_state['trip_state']
        
        # Create 4 tabs
        tab1, tab2, tab3, tab4 = st.tabs(["Itinerary & Map", "Recommendations", "Budget", "Adapt Trip"])
        
        with tab1:
            render_itinerary_tab(state)
            
        with tab2:
            render_recommendations_tab(state)
            
        with tab3:
            render_budget_tab(state)
            
        with tab4:
            st.markdown("### 🔄 Adapt My Trip")
            st.markdown("<p style='color: #94A3B8; margin-bottom: 24px;'>Did something go wrong? Enter a changed condition (e.g., 'It is raining on Day 2' or 'Museum is closed') and the AI will surgically repair your itinerary.</p>", unsafe_allow_html=True)
            
            changed_condition = st.text_area("What changed?", placeholder="e.g. Bad weather on Saturday afternoon.")
            
            if st.button("Adapt Itinerary", type="secondary", use_container_width=True):
                if not changed_condition:
                    st.warning("Please describe the changed condition.")
                else:
                    with st.status("Adapting Trip...", expanded=True) as status:
                        st.write("✓ Detecting conflicts")
                        st.write("✓ Searching alternatives (MCP)")
                        st.write("✓ Evaluating options")
                        try:
                            # We can't access demo_mode easily from session state if it's not saved, 
                            # but sidebar inputs are rerun on every interaction in streamlit.
                            # So inputs["demo_mode"] is fresh.
                            if inputs["demo_mode"]:
                                time.sleep(2.5)
                                new_state = DEMO_ADAPTED_STATE
                            else:
                                if not state.get("original_itinerary"):
                                    state["original_itinerary"] = state["final_itinerary"]
                                    
                                new_state = _run_async_task(adapt_trip(state, changed_condition))
                                
                            st.session_state['trip_state'] = new_state
                            status.update(label="Adaptation Complete!", state="complete", expanded=False)
                            st.rerun() 
                        except Exception as e:
                            logger.error(f"Trip adaptation failed: {e}", exc_info=True)
                            status.update(label="Adaptation Failed", state="error", expanded=True)
                            st.error(f"Integration Error: {str(e)}")
                            
            if state.get("original_itinerary"):
                st.markdown("<hr style='border-color: #1E293B; margin: 40px 0;'>", unsafe_allow_html=True)
                st.markdown("### 📊 Iteration Comparison")
                
                comp_tab1, comp_tab2 = st.tabs(["✨ Adapted Itinerary (Patched)", "📜 Original Itinerary"])
                
                with comp_tab1:
                    st.markdown("<div style='background: #0F172A; padding: 24px; border-radius: 12px; border: 1px solid #38BDF8;'>", unsafe_allow_html=True)
                    st.markdown(state["final_itinerary"])
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                with comp_tab2:
                    st.markdown("<div style='background: #0F172A; padding: 24px; border-radius: 12px; border: 1px solid #334155;'>", unsafe_allow_html=True)
                    st.markdown(state["original_itinerary"])
                    st.markdown("</div>", unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("#### Side-by-Side Overview")
                comp_col1, comp_col2 = st.columns(2)
                with comp_col1:
                    st.markdown("<h4 style='color: #94A3B8;'>Original Itinerary</h4>", unsafe_allow_html=True)
                    with st.container(height=650, border=True):
                        st.markdown(state["original_itinerary"])
                with comp_col2:
                    st.markdown("<h4 style='color: #38BDF8;'>Adapted Itinerary</h4>", unsafe_allow_html=True)
                    with st.container(height=650, border=True):
                        st.markdown(state["final_itinerary"])
                        
        # --- TECHNICAL MCP LOGS (Optional/Collapsible) ---
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.expander("⚙️ Technical MCP Logs (Agent Activity)"):
            st.markdown("This section exposes the raw underlying LangGraph & MCP engine logic for L2 Review demonstration.")
            
            logs = state.get("technical_logs", [])
            
            if not logs and state.get("messages"):
                messages = state.get("messages", [])
                for msg in messages:
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        for tc in msg.tool_calls:
                            tool_name = tc['name']
                            server = "Unknown MCP"
                            if "weather" in tool_name: server = "Weather MCP"
                            elif any(x in tool_name for x in ["places", "search", "attraction", "destination"]): server = "Places MCP"
                            elif any(x in tool_name for x in ["transport", "route"]): server = "Transport MCP"
                            elif any(x in tool_name for x in ["budget", "cost", "validate"]): server = "Budget MCP"
                            
                            args_str = str(tc.get('args', {}))
                            if len(args_str) > 100: args_str = args_str[:100] + "..."
                            
                            logs.append({
                                "title": f"Agent → {server} → {tool_name}",
                                "type": "tool_call",
                                "details": f"Input: {args_str}"
                            })
                    elif getattr(msg, 'type', '') == 'tool':
                        content = str(msg.content)
                        if len(content) > 150: content = content[:150] + "..."
                        logs.append({
                            "title": f"↳ Tool Result Summary",
                            "type": "tool_result",
                            "details": content
                        })
            
            structured_logs = []
            for log in logs:
                if isinstance(log, str):
                    if "→" in log:
                        parts = log.split("→", 1)
                        structured_logs.append({
                            "title": parts[0].strip() + (f" → {parts[1].split('(')[0].strip()}" if "(" in parts[1] else ""),
                            "type": "decision" if "Decision" in log else "tool_call",
                            "details": parts[1].strip() if "Decision" not in log else log
                        })
                    else:
                        structured_logs.append({"title": log, "type": "info", "details": ""})
                else:
                    structured_logs.append(log)
            
            render_agent_activity(structured_logs)
                    
    else:
        render_empty_state()

if __name__ == "__main__":
    main()
