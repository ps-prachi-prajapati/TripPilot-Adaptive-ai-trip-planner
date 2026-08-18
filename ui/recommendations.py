import streamlit as st
from ui.components import render_destination_card

def render_recommendations_tab(state):
    st.markdown("### Destination Candidates")
    candidates = state.get("candidates", [])
    selected = state.get("selected_candidate", {})
    
    if not candidates:
        st.info("No candidates were evaluated.")
        
    cols = st.columns(2)
    for idx, cand in enumerate(candidates):
        with cols[idx % 2]:
            is_selected = (cand.get("name") == selected.get("name"))
            render_destination_card(cand, is_selected)
            if not is_selected:
                if st.button(f"🎯 Plan Trip to {cand.get('name')}", key=f"select_cand_{idx}", use_container_width=True):
                    st.session_state["pending_dest_query"] = cand.get("name")
                    st.session_state["auto_trigger_plan"] = True
                    st.rerun()

