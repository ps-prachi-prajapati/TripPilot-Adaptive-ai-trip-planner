import streamlit as st
import re
from ui.components import render_travel_timing_card
from ui.map import render_google_map

def render_itinerary_tab(state):
    selected_cand = state.get("selected_candidate", {})
    dest_name = selected_cand.get("name") if isinstance(selected_cand, dict) else None
    if not dest_name:
        dest_name = state.get("destination_location") or state.get("location", "Trip Destination")

    # 1. Top Section: Prominent Travel Logistics & Departure Timing Banner (Fully Wide)
    render_travel_timing_card(
        start_location=state.get("location"),
        destination_name=dest_name,
        transport_mode=state.get("transport_mode"),
        max_travel_mins=state.get("max_travel_mins")
    )

    # 2. Extract metadata info from the LLM itinerary text to avoid duplicates
    itinerary_text = state.get("final_itinerary", "")
    
    meta_info = {
        "Starting Location": state.get("location", "Not specified"),
        "Selected Destination": dest_name,
        "Trip Duration": f"Exactly {state.get('duration_days', 2)} Days",
        "Transport Mode": str(state.get("transport_mode", "driving-car")).replace('-', ' ').title(),
        "Total Budget Limit": f"₹{state.get('budget', 5000.0)} INR",
        "Preferred Interests": ", ".join(state.get("interests", [])) if isinstance(state.get("interests"), list) else str(state.get("interests", "General"))
    }
    
    cleaned_itinerary = itinerary_text
    keys_to_strip = ["Starting Location", "Selected Destination", "Trip Duration", "Transport Mode", "Total Budget Limit", "Preferred Interests"]
    for key in keys_to_strip:
        # Match lines like "Starting Location: Vadodara" or "- Starting Location: Vadodara"
        pattern = rf"(?i)^\s*[\-\*]?\s*{key}\s*:\s*(.*)$"
        match = re.search(pattern, cleaned_itinerary, re.MULTILINE)
        if match:
            meta_info[key] = match.group(1).strip()
            cleaned_itinerary = re.sub(pattern, "", cleaned_itinerary, flags=re.MULTILINE)
            
    # Clean up excessive newlines left over from stripping
    cleaned_itinerary = re.sub(r'\n{3,}', '\n\n', cleaned_itinerary)

    # 3. Middle Section: Left column for Trip Summary details, Right column for Google Maps
    col_left, col_map = st.columns([1, 1])
    
    with col_left:
        st.markdown("#### 📋 Trip Summary & Constraints")
        info_html = f"""
        <div style="background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%); border: 1px solid #334155; border-radius: 12px; padding: 20px; color: #F8FAFC; min-height: 425px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
            <div style="margin-bottom: 14px;">
                <span style="font-size: 0.75rem; text-transform: uppercase; color: #94A3B8; font-weight: 600;">🛫 Starting Location</span>
                <div style="font-size: 1.05rem; font-weight: 500; margin-top: 2px;">{meta_info['Starting Location']}</div>
            </div>
            <div style="margin-bottom: 14px;">
                <span style="font-size: 0.75rem; text-transform: uppercase; color: #94A3B8; font-weight: 600;">🏁 Selected Destination</span>
                <div style="font-size: 1.05rem; font-weight: 500; margin-top: 2px; color: #34D399;">{meta_info['Selected Destination']}</div>
            </div>
            <div style="margin-bottom: 14px;">
                <span style="font-size: 0.75rem; text-transform: uppercase; color: #94A3B8; font-weight: 600;">📅 Trip Duration</span>
                <div style="font-size: 1.05rem; font-weight: 500; margin-top: 2px;">{meta_info['Trip Duration']}</div>
            </div>
            <div style="margin-bottom: 14px;">
                <span style="font-size: 0.75rem; text-transform: uppercase; color: #94A3B8; font-weight: 600;">🚘 Transport Mode</span>
                <div style="font-size: 1.05rem; font-weight: 500; margin-top: 2px;">{meta_info['Transport Mode']}</div>
            </div>
            <div style="margin-bottom: 14px;">
                <span style="font-size: 0.75rem; text-transform: uppercase; color: #94A3B8; font-weight: 600;">💰 Total Budget Limit</span>
                <div style="font-size: 1.05rem; font-weight: 500; margin-top: 2px; color: #38BDF8;">{meta_info['Total Budget Limit']}</div>
            </div>
            <div>
                <span style="font-size: 0.75rem; text-transform: uppercase; color: #94A3B8; font-weight: 600;">🎯 Preferred Interests</span>
                <div style="font-size: 0.95rem; font-weight: 500; margin-top: 2px; color: #F472B6; line-height: 1.4;">{meta_info['Preferred Interests']}</div>
            </div>
        </div>
        """
        st.markdown(info_html, unsafe_allow_html=True)
            
    with col_map:
        st.markdown(f"#### 🗺️ Google Maps Navigation ({dest_name})")
        
        map_tab1, map_tab2 = st.tabs(["📍 City & Area View", "🏨 Hotel Locations"])
        
        with map_tab1:
            try:
                render_google_map(dest_name, show_hotels=False, height=380)
            except Exception as e:
                st.warning(f"Google Map unavailable: {e}")
                
        with map_tab2:
            try:
                render_google_map(dest_name, show_hotels=True, height=380)
            except Exception as e:
                st.warning(f"Hotel Map unavailable: {e}")

    # 4. Bottom Section: Full-width Detailed Itinerary
    st.markdown("<br><hr>", unsafe_allow_html=True)
    st.markdown("### 📅 Detailed Daily Itinerary")
    st.markdown(cleaned_itinerary)
