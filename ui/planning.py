import streamlit as st
import os
from utils.place_search import clean_place_name, get_geoapify_autocomplete, get_geoapify_place_details




GOOGLE_MAPS_PLACES = [
    "Ahmedabad, Gujarat, India",
    "Kankaria Lake & Manek Chowk, Ahmedabad",
    "Sabarmati Riverfront & Ashram, Ahmedabad",
    "SG Highway & Bodakdev, Ahmedabad",
    "Sardar Vallabhbhai Patel Int'l Airport (AMD), Ahmedabad",
    "Vadodara, Gujarat, India",
    "Laxmi Vilas Palace, Vadodara, Gujarat",
    "Alkapuri Commercial Hub, Vadodara",
    "Sayajigunj & Sayaji Garden, Vadodara",
    "Statue of Unity, Kevadia, Gujarat",
    "Surat (Silk & Diamond City), Gujarat, India",
    "Dumas Beach & Vesu, Surat",
    "Mumbai, Maharashtra, India",
    "Gateway of India & Colaba, South Mumbai",
    "Marine Drive & Nariman Point, Mumbai",
    "Chhatrapati Shivaji Int'l Airport (BOM), Mumbai",
    "New Delhi & NCR, India",
    "Connaught Place, New Delhi",
    "Chandni Chowk & Red Fort, Old Delhi",
    "Jaipur (Pink City), Rajasthan, India",
    "Amber Fort & Hawa Mahal, Jaipur",
    "Udaipur (City of Lakes), Rajasthan, India",
    "City Palace & Lake Pichola, Udaipur",
    "Goa (Beach Coast), India",
    "Calangute & Baga Beach, North Goa",
    "Pune, Maharashtra, India",
    "Bangalore, Karnataka, India",
    "Kochi & Fort Kochi, Kerala, India",
    "Shimla & Mall Road, Himachal Pradesh",
    "Manali & Solang Valley, Himachal Pradesh",
    "Agra (Taj Mahal), Uttar Pradesh, India",
    "Varanasi (Ghats), Uttar Pradesh, India",
    "New York City, NY, USA",
    "London, UK",
    "Paris, France",
    "Tokyo, Japan",
    "Dubai, UAE",
    "Singapore",
    "Custom..."
]


CITY_SUB_LOCATIONS = {
    "Vadodara": ["Any Area / Mixed", "Alkapuri", "Sayajigunj", "Fatehgunj", "Akota & Laxmi Vilas", "Gotri", "Manjalpur", "VIP Road", "Custom..."],
    "Ahmedabad": ["Any Area / Mixed", "Kankaria & Manek Chowk", "Sabarmati Riverfront", "Bodakdev & SG Highway", "Navrangpura", "Satellite", "Law Garden Area", "Custom..."],
    "Mumbai": ["Any Area / Mixed", "South Mumbai & Colaba", "Bandra & Khar", "Juhu & Versova", "Andheri East & Powai", "Marine Drive & Nariman Point", "Custom..."],
    "Delhi": ["Any Area / Mixed", "Connaught Place & Central Delhi", "Hauz Khas & South Delhi", "Old Delhi & Chandni Chowk", "Aerocity & Gurgaon", "Custom..."],
    "Udaipur": ["Any Area / Mixed", "City Palace & Lake Pichola", "Fateh Sagar Lake", "Sukhadia Circle", "Hiran Magri", "Custom..."],
    "Jaipur": ["Any Area / Mixed", "Pink City & Hawa Mahal", "C-Scheme", "Malviya Nagar", "Amer & Fort Circuit", "Custom..."],
    "Surat": ["Any Area / Mixed", "Vesu & Dumas", "Adajan", "Ring Road & Textile Market", "Piplod", "Custom..."],
    "Pune": ["Any Area / Mixed", "Koregaon Park", "Kothrud & FC Road", "Baner & Balewadi", "Viman Nagar", "Custom..."],
    "Bangalore": ["Any Area / Mixed", "Indiranagar", "Koramangala", "MG Road & Cubbon Park", "Whitefield", "Jayanagar", "Custom..."],
    "Goa": ["Any Area / Mixed", "North Goa (Calangute & Baga)", "Panaji & Fontainhas", "South Goa (Colva & Palolem)", "Anjuna & Vagator", "Custom..."],
}

def _get_base_city(place_name: str) -> str:
    """Helper to extract main city from a full place string."""
    clean = clean_place_name(place_name)
    for c in ["Ahmedabad", "Vadodara", "Mumbai", "Delhi", "Jaipur", "Udaipur", "Surat", "Pune", "Bangalore", "Goa", "Kochi", "Shimla", "Agra", "Varanasi", "New York", "London", "Paris", "Tokyo"]:
        if c.lower() in clean.lower():
            return c
    return clean.split(",")[0].strip()

def render_planning_sidebar():
    with st.sidebar:
        st.markdown("### Plan New Trip")
        
        # 1. Starting Location (Origin) Autocomplete Search
        start_query = st.text_input(
            "📍 Starting Location (Origin)",
            value="Ahmedabad",
            help="Type to search starting city, landmark, or address (Geoapify Autocomplete).",
            placeholder="e.g. Ahmedabad, Surat..."
        )
        start_suggestions = get_geoapify_autocomplete(start_query)
        if start_suggestions:
            selected_start_desc = st.selectbox(
                "Select Matching Place (Origin)",
                [s["description"] for s in start_suggestions],
                index=0,
                key="start_loc_select"
            )
            origin_details = get_geoapify_place_details("", selected_start_desc)
            start_location = origin_details["place_name"]
        else:
            start_location = start_query
            origin_details = get_geoapify_place_details("", start_location)

        # 2. Target Destination Autocomplete Search
        dest_query = st.text_input(
            "🏁 Target Destination",
            value="Vadodara",
            help="Type to search destination city, landmark, or address (Geoapify Autocomplete).",
            placeholder="e.g. Vadodara, Jaipur..."
        )
        dest_suggestions = get_geoapify_autocomplete(dest_query)
        if dest_suggestions:
            selected_dest_desc = st.selectbox(
                "Select Matching Place (Destination)",
                [s["description"] for s in dest_suggestions],
                index=0,
                key="dest_loc_select"
            )
            dest_details = get_geoapify_place_details("", selected_dest_desc)
            target_destination = dest_details["place_name"]
        else:
            target_destination = dest_query
            dest_details = get_geoapify_place_details("", target_destination)


        sub_location = ""
        st.markdown("---")




        # 3. Expanded Interests Multiselect
        all_interests = [
            "Nature & Outdoors", "Museums & History", "Food & Street Dining",
            "Nightlife & Pubs", "Shopping & Malls", "Relaxation & Spa",
            "Adventure & Sports", "Photography", "Local Markets & Craft",
            "Culture & Arts", "Architecture & Temples", "Parks & Gardens",
            "Water Activities", "Heritage & Forts"
        ]
        interests = st.multiselect("Interests", all_interests, default=["Nature & Outdoors", "Food & Street Dining"])

        # 4. Budget, Duration, Transport & Travel Time
        budget = st.number_input("Budget (₹ / INR)", min_value=500.0, max_value=500000.0, value=5000.0, step=500.0)
        duration = st.slider("Duration (Days)", min_value=1, max_value=7, value=2)
        transport = st.selectbox("Preferred Transport", ["driving-car", "foot-walking", "cycling-regular"])
        max_travel_mins = st.number_input("Max Travel Time (mins)", value=180.0, step=30.0)
        
        generate_btn = st.button("Generate Trip Plan", use_container_width=True, type="primary")
        
        st.markdown("---")
        demo_mode = st.toggle("🎥 Presentation Demo Mode", value=False, help="Bypasses the real LLM/MCP APIs to return a reliable, pre-baked scenario for project presentations.")
        
        # Verify API key if not in demo mode
        if not demo_mode and (not os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY") == "your_google_api_key"):
            st.error("GOOGLE_API_KEY is not configured in .env. Enable Demo Mode to test the UI.")
            
        return {
            "location": start_location,
            "destination_location": target_destination,
            "sub_location": sub_location,
            "origin_details": origin_details,
            "destination_details": dest_details,
            "budget": budget,
            "duration": duration,
            "interests": interests,
            "transport": transport,
            "max_travel_mins": max_travel_mins,
            "generate_btn": generate_btn,
            "demo_mode": demo_mode
        }




