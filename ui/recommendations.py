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
