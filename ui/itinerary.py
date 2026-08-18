import streamlit as st
from ui.components import render_travel_timing_card
from ui.map import render_google_map

def render_itinerary_tab(state):
    selected_cand = state.get("selected_candidate", {})
    dest_name = selected_cand.get("name") if isinstance(selected_cand, dict) else None
    if not dest_name:
        dest_name = state.get("destination_location") or state.get("location", "Trip Destination")

    # 1. Top Prominent Travel Logistics & Departure Timing Banner
    render_travel_timing_card(
        start_location=state.get("location"),
        destination_name=dest_name,
        transport_mode=state.get("transport_mode"),
        max_travel_mins=state.get("max_travel_mins")
    )

    col_it, col_map = st.columns([3, 2])
    
    with col_it:
        # Display adaptation summary if it exists
        if state.get("adaptation_summary"):
            st.markdown(f"<div class='adapt-summary'><h4>⚠️ Adaptation Summary</h4>{state['adaptation_summary']}</div>", unsafe_allow_html=True)
        
        st.markdown(state.get("final_itinerary", "*No itinerary generated.*"))
    
    with col_map:
        st.markdown(f"#### 🗺️ Google Maps Navigation ({dest_name})")
        
        map_tab1, map_tab2 = st.tabs(["📍 City & Area View", "🏨 Hotel Locations"])
        
        with map_tab1:
            try:
                render_google_map(dest_name, show_hotels=False, height=520)
            except Exception as e:
                st.warning(f"Google Map unavailable: {e}")
                
        with map_tab2:
            try:
                render_google_map(dest_name, show_hotels=True, height=520)
            except Exception as e:
                st.warning(f"Hotel Map unavailable: {e}")
