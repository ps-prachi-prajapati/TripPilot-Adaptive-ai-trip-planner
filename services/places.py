import os
import requests
from dotenv import load_dotenv

load_dotenv()

FOURSQUARE_API_KEY = os.getenv("FOURSQUARE_API_KEY")

DEFAULT_DESTINATIONS = {
    "vadodara": [
        {"fsq_id": "mock_dest_1", "name": "Sayajigunj, Vadodara", "categories": [{"name": "Neighborhood"}], "location": {"formatted_address": "Sayajigunj, Vadodara, Gujarat, India"}, "geocodes": {"main": {"latitude": 22.3106, "longitude": 73.1868}}},
        {"fsq_id": "mock_dest_2", "name": "Alkapuri, Vadodara", "categories": [{"name": "Neighborhood"}], "location": {"formatted_address": "Alkapuri, Vadodara, Gujarat, India"}, "geocodes": {"main": {"latitude": 22.3129, "longitude": 73.1678}}},
        {"fsq_id": "mock_dest_3", "name": "Karelibaug, Vadodara", "categories": [{"name": "Neighborhood"}], "location": {"formatted_address": "Karelibaug, Vadodara, Gujarat, India"}, "geocodes": {"main": {"latitude": 22.3325, "longitude": 73.2005}}}
    ],
    "default": [
        {"fsq_id": "mock_dest_default_1", "name": "Downtown Area", "categories": [{"name": "Neighborhood"}], "location": {"formatted_address": "Downtown"}, "geocodes": {"main": {"latitude": 40.7128, "longitude": -74.0060}}}
    ]
}

DEFAULT_ATTRACTIONS = {
    "sayajigunj": [
        {"fsq_id": "mock_att_1", "name": "Sayaji Baug Zoo & Park", "categories": [{"name": "Park"}], "location": {"formatted_address": "Sayajigunj, Vadodara, Gujarat"}, "rating": 4.5, "geocodes": {"main": {"latitude": 22.3106, "longitude": 73.1868}}},
        {"fsq_id": "mock_att_2", "name": "Baroda Museum & Picture Gallery", "categories": [{"name": "Museum"}], "location": {"formatted_address": "Sayajigunj, Vadodara, Gujarat"}, "rating": 4.6, "geocodes": {"main": {"latitude": 22.3112, "longitude": 73.1872}}},
        {"fsq_id": "mock_att_3", "name": "Kirti Mandir", "categories": [{"name": "Monument"}], "location": {"formatted_address": "Sayajigunj, Vadodara, Gujarat"}, "rating": 4.2, "geocodes": {"main": {"latitude": 22.3102, "longitude": 73.1855}}}
    ],
    "alkapuri": [
        {"fsq_id": "mock_att_4", "name": "Inorbit Mall Vadodara", "categories": [{"name": "Shopping Mall"}], "location": {"formatted_address": "Alkapuri, Vadodara, Gujarat"}, "rating": 4.4, "geocodes": {"main": {"latitude": 22.3129, "longitude": 73.1678}}},
        {"fsq_id": "mock_att_5", "name": "Alkapuri Club Ground", "categories": [{"name": "Park"}], "location": {"formatted_address": "Alkapuri, Vadodara, Gujarat"}, "rating": 4.0, "geocodes": {"main": {"latitude": 22.3135, "longitude": 73.1685}}}
    ],
    "karelibaug": [
        {"fsq_id": "mock_att_6", "name": "Kamati Baug Garden", "categories": [{"name": "Park"}], "location": {"formatted_address": "Karelibaug, Vadodara, Gujarat"}, "rating": 4.3, "geocodes": {"main": {"latitude": 22.3325, "longitude": 73.2005}}},
        {"fsq_id": "mock_att_7", "name": "Sardar Patel Planetarium", "categories": [{"name": "Planetarium"}], "location": {"formatted_address": "Karelibaug, Vadodara, Gujarat"}, "rating": 4.5, "geocodes": {"main": {"latitude": 22.3331, "longitude": 73.2012}}}
    ],
    "fatehgunj": [
        {"fsq_id": "mock_att_8", "name": "MSU Dome", "categories": [{"name": "University Complex"}], "location": {"formatted_address": "Fatehgunj, Vadodara, Gujarat"}, "rating": 4.4, "geocodes": {"main": {"latitude": 22.3218, "longitude": 73.1888}}},
        {"fsq_id": "mock_att_9", "name": "Fatehgunj Garden", "categories": [{"name": "Park"}], "location": {"formatted_address": "Fatehgunj, Vadodara, Gujarat"}, "rating": 4.1, "geocodes": {"main": {"latitude": 22.3224, "longitude": 73.1895}}}
    ],
    "default": [
        {"fsq_id": "mock_att_default_1", "name": "Laxmi Vilas Palace", "categories": [{"name": "Historic Site"}], "location": {"formatted_address": "Vadodara, Gujarat"}, "rating": 4.8, "geocodes": {"main": {"latitude": 22.3022, "longitude": 73.1812}}},
        {"fsq_id": "mock_att_default_2", "name": "Sayaji Baug", "categories": [{"name": "Park"}], "location": {"formatted_address": "Vadodara, Gujarat"}, "rating": 4.6, "geocodes": {"main": {"latitude": 22.3106, "longitude": 73.1868}}},
        {"fsq_id": "mock_att_default_3", "name": "EME Temple", "categories": [{"name": "Temple"}], "location": {"formatted_address": "Vadodara, Gujarat"}, "rating": 4.5, "geocodes": {"main": {"latitude": 22.3285, "longitude": 73.1782}}}
    ]
}

DEFAULT_RESTAURANTS = {
    "sayajigunj": [
        {"fsq_id": "mock_rest_1", "name": "Sayaji Restaurant", "categories": [{"name": "Indian Restaurant"}], "location": {"formatted_address": "Sayajigunj, Vadodara"}, "rating": 4.2, "geocodes": {"main": {"latitude": 22.3106, "longitude": 73.1868}}},
        {"fsq_id": "mock_rest_2", "name": "Peshawri Mughlai Dining", "categories": [{"name": "Mughlai Restaurant"}], "location": {"formatted_address": "Sayajigunj, Vadodara"}, "rating": 4.5, "geocodes": {"main": {"latitude": 22.3112, "longitude": 73.1872}}}
    ],
    "alkapuri": [
        {"fsq_id": "mock_rest_3", "name": "Barbeque Nation Alkapuri", "categories": [{"name": "Barbecue Restaurant"}], "location": {"formatted_address": "Alkapuri, Vadodara"}, "rating": 4.4, "geocodes": {"main": {"latitude": 22.3129, "longitude": 73.1678}}},
        {"fsq_id": "mock_rest_4", "name": "22nd Parallel South Indian", "categories": [{"name": "South Indian Restaurant"}], "location": {"formatted_address": "Alkapuri, Vadodara"}, "rating": 4.6, "geocodes": {"main": {"latitude": 22.3135, "longitude": 73.1685}}}
    ],
    "default": [
        {"fsq_id": "mock_rest_default_1", "name": "Mandap Restaurant", "categories": [{"name": "Gujarati Restaurant"}], "location": {"formatted_address": "Vadodara, Gujarat"}, "rating": 4.5, "geocodes": {"main": {"latitude": 22.3072, "longitude": 73.1812}}},
        {"fsq_id": "mock_rest_default_2", "name": "Jassi De Parathe", "categories": [{"name": "Punjabi Restaurant"}], "location": {"formatted_address": "Vadodara, Gujarat"}, "rating": 4.3, "geocodes": {"main": {"latitude": 22.3080, "longitude": 73.1820}}}
    ]
}

DEFAULT_HOTELS = {
    "sayajigunj": [
        {"fsq_id": "mock_hotel_1", "name": "Grand Mercure Vadodara Surya Palace", "categories": [{"name": "Hotel"}], "location": {"formatted_address": "Sayajigunj, Vadodara"}, "rating": 4.4, "geocodes": {"main": {"latitude": 22.3106, "longitude": 73.1868}}},
        {"fsq_id": "mock_hotel_2", "name": "Surya Palace Hotel", "categories": [{"name": "Hotel"}], "location": {"formatted_address": "Sayajigunj, Vadodara"}, "rating": 4.2, "geocodes": {"main": {"latitude": 22.3112, "longitude": 73.1872}}}
    ],
    "alkapuri": [
        {"fsq_id": "mock_hotel_3", "name": "Welcomhotel by ITC Hotels Alkapuri", "categories": [{"name": "Hotel"}], "location": {"formatted_address": "Alkapuri, Vadodara"}, "rating": 4.6, "geocodes": {"main": {"latitude": 22.3129, "longitude": 73.1678}}},
        {"fsq_id": "mock_hotel_4", "name": "Hyatt Place Vadodara", "categories": [{"name": "Hotel"}], "location": {"formatted_address": "Alkapuri, Vadodara"}, "rating": 4.5, "geocodes": {"main": {"latitude": 22.3135, "longitude": 73.1685}}}
    ],
    "default": [
        {"fsq_id": "mock_hotel_default_1", "name": "Vivanta Vadodara", "categories": [{"name": "Hotel"}], "location": {"formatted_address": "Vadodara, Gujarat"}, "rating": 4.5, "geocodes": {"main": {"latitude": 22.3072, "longitude": 73.1812}}},
        {"fsq_id": "mock_hotel_default_2", "name": "Sayaji Hotel Vadodara", "categories": [{"name": "Hotel"}], "location": {"formatted_address": "Vadodara, Gujarat"}, "rating": 4.3, "geocodes": {"main": {"latitude": 22.3080, "longitude": 73.1820}}}
    ]
}

def _parse_foursquare_place(place: dict) -> dict:
    """Helper to parse raw place dict into agent-friendly format."""
    location = place.get("location", {})
    categories = place.get("categories", [])
    category_name = categories[0]["name"] if categories else "General"
    
    return {
        "id": place.get("fsq_id", ""),
        "name": place.get("name", "Unknown"),
        "category": category_name,
        "address": location.get("formatted_address", "No address available"),
        "distance": place.get("distance", 0),  # in meters
        "rating": place.get("rating", "N/A"),
        "lat": place.get("geocodes", {}).get("main", {}).get("latitude"),
        "lon": place.get("geocodes", {}).get("main", {}).get("longitude")
    }

def _customize_place_for_location(place: dict, location: str) -> dict:
    """Rewrite mock place details dynamically to match target city search context."""
    city = "Destination"
    if location:
        parts = [p.strip() for p in location.split(",")]
        if len(parts) > 0:
            city = parts[-1]
            if city.lower() in ["india", "usa", "uk"] and len(parts) > 1:
                city = parts[-2]
            else:
                city = parts[0]
                
    place_copy = dict(place)
    place_copy["address"] = f"{location}, India"
    name = place_copy["name"]
    
    # Map Vadodara defaults to target city
    name_map = {
        "Laxmi Vilas Palace": "Royal Heritage Palace",
        "Sayaji Baug": "Central Botanical Garden",
        "EME Temple": "Heritage Temple",
        "Mandap Restaurant": "Traditional Thali Restaurant",
        "Jassi De Parathe": "Punjabi Dhaba",
        "Vivanta Vadodara": "Luxury Palace Stay",
        "Sayaji Hotel Vadodara": "Heritage Boutique Hotel",
        "Sayaji Baug Zoo & Park": "Zoo & Nature Park",
        "Baroda Museum & Picture Gallery": "National Art Museum",
        "Kirti Mandir": "Memorial Heritage Site",
        "Inorbit Mall Vadodara": "Premier Shopping Mall",
        "Alkapuri Club Ground": "Recreation Club Ground",
        "Kamati Baug Garden": "Royal Garden Walkway",
        "Sardar Patel Planetarium": "Space Planetarium",
        "MSU Dome": "Historical University Dome",
        "Fatehgunj Garden": "Neighborhood Leisure Park",
        "Sayaji Restaurant": "Grand Buffet Dining",
        "Peshawri Mughlai Dining": "Fine Mughlai Diner",
        "Barbeque Nation Alkapuri": "Barbecue & Grill",
        "22nd Parallel South Indian": "Traditional South Indian Cafe",
        "Grand Mercure Vadodara Surya Palace": "Grand Luxury Hotel",
        "Surya Palace Hotel": "Plaza Hotel",
        "Welcomhotel by ITC Hotels Alkapuri": "Royal ITC Palace Hotel",
        "Hyatt Place Vadodara": "Premium Hyatt Regency Stay",
        "Downtown Area": "Central Plaza",
        "Recommended Place": "Signature Landmark"
    }
    
    for old_n, new_n in name_map.items():
        if old_n in name:
            place_copy["name"] = name.replace(old_n, f"{new_n} in {city}")
            break
            
    return place_copy

def fetch_destinations(query: str, limit: int) -> list[dict]:
    # Return local catalog data directly
    loc_key = "default"
    for k in DEFAULT_DESTINATIONS.keys():
        if k in query.lower():
            loc_key = k
            break
    results = DEFAULT_DESTINATIONS[loc_key][:limit]
    parsed = [_parse_foursquare_place(r) for r in results]
    if loc_key == "default":
        # Rewrite candidate destinations to be sub-areas of the query city (e.g. "Jaipur")
        city = query.split(",")[0].strip().capitalize()
        # Create 3 diverse mock areas for the city
        parsed = [
            {"id": "mock_dest_custom_1", "name": f"Heritage Fort Area, {city}", "category": "Neighborhood", "address": f"Heritage District, {city}, India", "distance": 1000, "rating": 4.5, "lat": 23.0225, "lon": 72.5714},
            {"id": "mock_dest_custom_2", "name": f"Downtown Central, {city}", "category": "Neighborhood", "address": f"Commercial Zone, {city}, India", "distance": 2000, "rating": 4.3, "lat": 23.0225, "lon": 72.5714},
            {"id": "mock_dest_custom_3", "name": f"Lakeside Boulevard, {city}", "category": "Neighborhood", "address": f"Scenic Waterfront, {city}, India", "distance": 3000, "rating": 4.6, "lat": 23.0225, "lon": 72.5714}
        ][:limit]
    return parsed

def fetch_attractions(location: str, query: str, limit: int) -> list[dict]:
    # Return local catalog data directly
    loc_key = "default"
    for k in DEFAULT_ATTRACTIONS.keys():
        if k in location.lower():
            loc_key = k
            break
    results = DEFAULT_ATTRACTIONS[loc_key][:limit]
    parsed = [_parse_foursquare_place(r) for r in results]
    if "vadodara" not in location.lower():
        parsed = [_customize_place_for_location(p, location) for p in parsed]
    return parsed

def fetch_restaurants(location: str, query: str, limit: int) -> list[dict]:
    # Return local catalog data directly
    loc_key = "default"
    for k in DEFAULT_RESTAURANTS.keys():
        if k in location.lower():
            loc_key = k
            break
    results = DEFAULT_RESTAURANTS[loc_key][:limit]
    parsed = [_parse_foursquare_place(r) for r in results]
    if "vadodara" not in location.lower():
        parsed = [_customize_place_for_location(p, location) for p in parsed]
    return parsed

def fetch_hotels(location: str, query: str, limit: int) -> list[dict]:
    # Return local catalog data directly
    loc_key = "default"
    for k in DEFAULT_HOTELS.keys():
        if k in location.lower():
            loc_key = k
            break
    results = DEFAULT_HOTELS[loc_key][:limit]
    parsed = [_parse_foursquare_place(r) for r in results]
    if "vadodara" not in location.lower():
        parsed = [_customize_place_for_location(p, location) for p in parsed]
    return parsed

def fetch_place_details(place_id: str) -> dict:
    # Return default details directly
    return {
        "id": place_id,
        "name": f"Recommended Place ({place_id})",
        "category": "Sightseeing",
        "description": "A popular point of interest highly rated by visitors for its scenic view and local experience.",
        "address": "Local Area, India",
        "rating": 4.5,
        "website": "http://example.com",
        "phone": "+91 98765 43210"
    }
