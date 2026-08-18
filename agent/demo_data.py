"""
Predefined static data for the Presentation Demo Mode.
Ensures the presentation runs flawlessly without requiring live API keys or internet.
"""

import copy

# --- INITIAL DEMO STATE (AHMEDABAD) ---
DEMO_INITIAL_STATE = {
    "location": "Ahmedabad",
    "destination_location": "Vadodara",
    "sub_location": "Alkapuri",
    "origin_details": {
        "place_name": "Ahmedabad",
        "full_address": "Ahmedabad, Gujarat, India",
        "latitude": 23.0225,
        "longitude": 72.5714,
        "place_id": "ChIJS-X6rJmEXjkR888Y0-k3ygg"
    },
    "destination_details": {
        "place_name": "Vadodara",
        "full_address": "Vadodara, Gujarat, India",
        "latitude": 22.3072,
        "longitude": 73.1812,
        "place_id": "ChIJbU6663XvXzkR2t2Y_64q1gg"
    },
    "duration_days": 2,

    "budget": 5000.0,
    "interests": ["Nature", "Food"],
    "transport_mode": "Public Transport",
    "max_travel_mins": 180.0,
    "messages": [],
    "candidates": [
        {
            "name": "Kankaria Lake Area", 
            "score": 1200.0, 
            "valid": True,
            "rejection_reason": ""
        },
        {
            "name": "Thol Bird Sanctuary", 
            "score": -500.0, 
            "valid": False,
            "rejection_reason": "Cost exceeds budget by ₹500.0."
        }
    ],
    "technical_logs": [
        "Agent → Places MCP → search_destinations({'location': 'Ahmedabad', 'interests': ['Nature']})",
        "Agent → Weather MCP → get_weather_forecast({'location': 'Ahmedabad'}) → Returned 'Clear Skies'",
        "Agent → Places MCP → search_attractions({'location': 'Kankaria Lake Area'}) → Found 5 activities",
        "Agent → Transport MCP → find_transport_options({'to': 'Kankaria', 'mode': 'Public Transport'}) → 45 mins",
        "Agent → Budget MCP → validate_budget({'estimated_cost': 3800, 'budget': 5000}) → Valid",
        "Agent → Budget MCP → validate_budget({'estimated_cost': 5500, 'budget': 5000}) → Failed for Thol Bird Sanctuary",
        "Agent Decision → Selected 'Kankaria Lake Area' as the primary destination"
    ],
    "current_candidate_index": 1,
    "selected_candidate": {
        "name": "Kankaria Lake Area", 
        "score": 1200.0, 
        "valid": True
    },
    "original_itinerary": "",
    "changed_condition": "",
    "affected_components": [],
    "adaptation_context": {},
    "adaptation_summary": "",
    "final_itinerary": """
# Weekend Trip to Ahmedabad: Nature & Local Food
**Budget:** ₹5,000 | **Transport Mode:** Public Transport

### 🏨 Recommended Hotel & Accommodation
- **Hotel:** Hyatt Regency Ahmedabad
- **Location & Address:** Ashram Road, Usmanpura, Ahmedabad, Gujarat 380014 (Near Sabarmati Riverfront)
- **Estimated Rate:** ₹1,800/night

## Day 1
- **Morning (9:00 AM):** Take the BRTS from Hyatt Regency to Kankaria Lake. Walk around the lush green pathways.
- **Afternoon (1:00 PM):** Picnic lunch by the lake and visit to the Kamala Nehru Zoo.
- **Evening (6:00 PM):** Head to Manek Chowk (2.5 km from hotel) for famous local street food (Pav Bhaji, Dosa).

## Day 2
- **Morning (9:30 AM):** Visit the Sabarmati Riverfront Park (5 mins walk from hotel) for nature walks.
- **Afternoon (1:30 PM):** Lunch at Agashiye (Lal Darwaja) for traditional Gujarati Thali.
- **Evening (5:00 PM):** Explore the Flower Park and return via Metro.
"""
}


# --- ADAPTED DEMO STATE ---
# Triggered when user enters bad weather condition
DEMO_ADAPTED_STATE = copy.deepcopy(DEMO_INITIAL_STATE)

# Preserve original
DEMO_ADAPTED_STATE["original_itinerary"] = DEMO_INITIAL_STATE["final_itinerary"]

# Update with adaptation logic
DEMO_ADAPTED_STATE["changed_condition"] = "Heavy rain expected on Day 1 afternoon."
DEMO_ADAPTED_STATE["affected_components"] = ["Kamala Nehru Zoo", "Picnic lunch by the lake"]
DEMO_ADAPTED_STATE["adaptation_summary"] = "Due to the expected heavy rain on Day 1, the outdoor picnic and zoo visit have been cancelled. Instead, the itinerary now includes a visit to the indoor Calico Museum of Textiles. This alternative saved ₹200 on outdoor activity fees and keeps you perfectly dry!"

DEMO_ADAPTED_STATE["technical_logs"] = [
    "Agent Detected Conflict → Rain invalidates outdoor 'Zoo' & 'Picnic'",
    "Agent → Places MCP → search_attractions({'location': 'Ahmedabad', 'type': 'Indoor Museum'}) → Found 'Calico Museum'",
    "Agent → Transport MCP → find_transport_options({'to': 'Calico Museum'}) → Taxi (₹300)",
    "Agent → Budget MCP → validate_budget({'new_total': 3900, 'budget': 5000}) → Valid",
    "Agent Decision → Spliced 'Calico Museum' into Day 1 Afternoon"
]

DEMO_ADAPTED_STATE["final_itinerary"] = """
# Weekend Trip to Ahmedabad: Nature & Local Food
**Budget:** ₹5,000 | **Transport Mode:** Public Transport

## Day 1
- **Morning (9:00 AM):** Take the BRTS to Kankaria Lake early before the rain starts.
- **Afternoon (1:00 PM):** *[ADJUSTED]* Take a cab to the Calico Museum of Textiles to avoid the heavy rain. Indoor historical exploration.
- **Evening (6:00 PM):** Head to Manek Chowk (covered areas) for famous local street food.

## Day 2
- **Morning (9:30 AM):** Visit the Sabarmati Riverfront Park (weather clearing up).
- **Afternoon (1:30 PM):** Lunch at Agashiye for traditional Gujarati Thali.
- **Evening (5:00 PM):** Explore the Flower Park and return via Metro.
"""
