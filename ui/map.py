import urllib.parse
import streamlit as st
import streamlit.components.v1 as components

def render_google_map(location_name: str, show_hotels: bool = False, height: int = 480):
    """
    Renders an interactive Google Map iframe centered on location_name or hotels near location_name.
    """
    if not location_name:
        location_name = "India"
        
    query_str = f"hotels in {location_name}" if show_hotels else f"{location_name}"
    encoded_query = urllib.parse.quote(query_str)
    embed_url = f"https://maps.google.com/maps?q={encoded_query}&t=&z=13&ie=UTF8&iwloc=&output=embed"
    
    components.iframe(embed_url, height=height, scrolling=True)
