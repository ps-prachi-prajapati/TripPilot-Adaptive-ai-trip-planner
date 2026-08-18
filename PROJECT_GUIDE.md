# Adaptive AI Trip Planner — Complete Project Guide

> A comprehensive guide covering the architecture, features, MCP tools, data flow, and every component in the system.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Why This Project Exists — Core Problems Solved](#2-why-this-project-exists)
3. [Technology Stack](#3-technology-stack)
4. [Project Folder Structure](#4-project-folder-structure)
5. [MCP Tools Reference (All 15 Tools)](#5-mcp-tools-reference)
6. [System Architecture — How Everything Connects](#6-system-architecture)
7. [LangGraph Agent Workflows](#7-langgraph-agent-workflows)
8. [External APIs Used](#8-external-apis-used)
9. [Feature Walkthrough](#9-feature-walkthrough)
10. [Data Flow — Step by Step](#10-data-flow-step-by-step)
11. [Environment Configuration](#11-environment-configuration)
12. [Running the Project](#12-running-the-project)

---

## 1. Project Overview

The **Adaptive AI Trip Planner** is a full-stack, multi-agent AI travel planning system built with:

- **Streamlit** — Interactive user interface
- **LangGraph** — Orchestrates multi-node AI agent workflows
- **Google Gemini** — The core LLM reasoning engine
- **Model Context Protocol (MCP)** — Connects the LLM to deterministic external tools
- **FastMCP** — Server framework for building MCP-compliant tool servers
- **Geoapify + Foursquare + OpenWeatherMap + OpenRouteService** — Real-world data APIs

The planner solves two hard problems in AI-based travel planning:

| Problem | Traditional AI Approach | This Project's Approach |
|---|---|---|
| LLM makes up distances, costs & weather | LLM guesses | MCP tools call real APIs — deterministic |
| Plan is disrupted (rain, cancellation) | Regenerate entire plan | Surgically patch only affected components |

---

## 2. Why This Project Exists

### Problem 1: LLM Hallucinations in Travel Planning

A standard LLM asked "How long does it take to drive from Ahmedabad to Vadodara?" might confidently respond 2 hours, but the real value depends on real-time route data. The LLM is simply guessing from training data.

**Solution**: The agent never does math or routing itself. It calls the `calculate_travel_time` MCP tool, which queries **OpenRouteService** for the exact distance and travel time in real-time.

### Problem 2: Full Regeneration Wastes Context & Is Slow

If the user says "It's going to rain on Day 2 — change only that day", standard AI systems regenerate the entire 5-day itinerary from scratch, often losing the quality of previous days.

**Solution**: The **Adapt Graph** is a separate LangGraph workflow that:
1. Identifies which specific components are affected
2. Gathers alternative data **only for those components**
3. Regenerates only the broken segments
4. Splices the fix back into the original plan

---

## 3. Technology Stack

```
Frontend          → Streamlit (Python)
Orchestration     → LangGraph (StateGraph with conditional routing)
LLM Engine        → Google Gemini (gemini-3.5-flash-lite)
Tool Protocol     → Model Context Protocol (MCP) via FastMCP + stdio transport
Location Search   → Geoapify Geocode Autocomplete API
Places Data       → Foursquare Places API
Weather Data      → OpenWeatherMap API
Routing Data      → OpenRouteService API
Map Display       → Folium (interactive Leaflet maps in Streamlit)
Config            → python-dotenv (.env file)
Testing           → Streamlit AppTest + Python unittest
```

---

## 4. Project Folder Structure

```
l2 project/
│
├── app.py                    ← Main Streamlit entry point
├── requirements.txt          ← Python dependencies
├── .env                      ← Secret API keys (never committed)
├── .env.example              ← Template for required env variables
├── run.bat                   ← Windows batch launcher
│
├── agent/                    ← LangGraph agent logic
│   ├── agent.py              ← All node functions (extraction, gathering, evaluation, generation)
│   ├── graph.py              ← Builds trip_graph and adapt_graph
│   ├── state.py              ← TripState TypedDict definition
│   ├── prompts.py            ← System prompts for each LLM node
│   └── demo_data.py          ← Pre-baked demo state for presentations
│
├── mcp_servers/              ← 4 FastMCP server scripts (run as subprocesses)
│   ├── budget_server.py      ← 4 tools: cost calculation & constraint checking
│   ├── places_server.py      ← 5 tools: Foursquare POI search
│   ├── transport_server.py   ← 3 tools: routing & cost estimation
│   └── weather_server.py     ← 3 tools: weather forecasting & suitability
│
├── mcp_client/
│   └── client.py             ← MultiServerMCPClient — connects to all 4 MCP servers
│
├── services/                 ← Raw API integration layer (called by MCP servers)
│   ├── places.py             ← Foursquare API requests
│   ├── transport.py          ← OpenRouteService API requests
│   └── weather.py            ← OpenWeatherMap API requests
│
├── ui/                       ← Streamlit UI components
│   ├── planning.py           ← Sidebar: location inputs, interests, budget
│   ├── itinerary.py          ← Itinerary display tab
│   ├── recommendations.py    ← Recommendations tab
│   ├── budget.py             ← Budget breakdown tab
│   ├── home.py               ← Hero header section
│   └── components.py         ← CSS injection & shared UI helpers
│
├── utils/
│   ├── place_search.py       ← Geoapify autocomplete integration + cache
│   ├── validation.py         ← Input validation logic
│   └── logging.py            ← Logging setup
│
└── tests/
    ├── test_ui.py            ← Streamlit AppTest UI tests
    ├── test_agent_mock.py    ← Agent logic mock tests
    └── test_mcps.py          ← MCP server unit tests
```

---

## 5. MCP Tools Reference

The project runs **4 MCP servers** exposing a total of **15 tools**.

### Tool Map Overview

```
MCP Servers (4 servers, 15 tools total)
│
├── Budget Server (4 tools) — No external API, pure math
│   ├── calculate_trip_cost
│   ├── validate_budget
│   ├── evaluate_constraints
│   └── compare_trip_options
│
├── Places Server (5 tools) — Foursquare API
│   ├── search_destinations
│   ├── search_attractions
│   ├── search_restaurants
│   ├── search_hotels
│   └── get_place_details
│
├── Transport Server (3 tools) — OpenRouteService API
│   ├── find_transport_options
│   ├── calculate_travel_time
│   └── calculate_transport_cost
│
└── Weather Server (3 tools) — OpenWeatherMap API
    ├── get_current_weather
    ├── get_weather_forecast
    └── check_weather_suitability
```

---

### Budget Server — budget_server.py

> **Purpose**: Prevent LLM arithmetic mistakes. All financial math and constraint logic is performed deterministically inside this server.

| Tool | Inputs | What It Does | Returns |
|---|---|---|---|
| `calculate_trip_cost` | `days`, `tier` (budget/mid/comfort/luxury), `transport_cost`, `activities_cost` | Computes per-night accommodation, daily meal costs, adds transport & activity costs | Full cost breakdown + total |
| `validate_budget` | `estimated_cost`, `user_budget` | Checks if cost exceeds budget | WITHIN_BUDGET or EXCEEDED with exact variance amount |
| `evaluate_constraints` | `travel_time_mins`, `max_travel_mins`, `weather_conflicts_exist`, `planned_transport_mode`, `preferred_transport_mode` | Checks if travel time is too long, weather is bad for activities, transport mode mismatch | `is_valid: true/false` + list of conflict reasons |
| `compare_trip_options` | `option_a_cost`, `option_a_time`, `option_b_cost`, `option_b_time`, `user_budget`, `max_travel_mins` | Compares two candidate destinations deterministically | Recommended option + reason |

---

### Places Server — places_server.py

> **Purpose**: Discover real destinations, attractions, restaurants, and hotels using the Foursquare Places API. The agent calls these instead of hallucinating place names.

| Tool | Inputs | What It Does | Returns |
|---|---|---|---|
| `search_destinations` | `query`, `limit` | Searches for candidate cities/places matching a query string | List of matching places with names and IDs |
| `search_attractions` | `location`, `query`, `limit` | Finds landmarks and tourist activities in a city | Attraction names, addresses, categories |
| `search_restaurants` | `location`, `query`, `limit` | Finds dining options tailored to the city and preference | Restaurant names, addresses, ratings |
| `search_hotels` | `location`, `query`, `limit` | Finds lodging/accommodation options | Hotel names, addresses, contact info |
| `get_place_details` | `place_id` | Gets full details for a single Foursquare place by ID | Name, address, rating, phone, website |

---

### Transport Server — transport_server.py

> **Purpose**: Calculate real travel distances, times, and transport costs using the OpenRouteService API (not LLM guesses).

| Tool | Inputs | What It Does | Returns |
|---|---|---|---|
| `find_transport_options` | (none) | Lists the supported travel modes the routing API can handle | driving-car, cycling-regular, foot-walking |
| `calculate_travel_time` | `start_lat`, `start_lon`, `end_lat`, `end_lon`, `mode` | Queries OpenRouteService for real route distance and duration | `distance_km`, `duration_mins` |
| `calculate_transport_cost` | `distance_km`, `mode` | Applies standard cost heuristics to compute monetary travel cost | `estimated_cost_usd`, calculation basis |

---

### Weather Server — weather_server.py

> **Purpose**: Fetch real weather data to align trip activities with meteorological conditions. Prevents recommending beach hikes during a monsoon.

| Tool | Inputs | What It Does | Returns |
|---|---|---|---|
| `get_current_weather` | `location` | Gets live weather for a city right now | Temperature, condition, humidity, feels-like |
| `get_weather_forecast` | `location`, `days` (1-5) | Gets daily weather forecasts for the next N days | Per-day summaries: condition, temp, precipitation chance |
| `check_weather_suitability` | `forecast_text`, `activities` (list) | Compares weather description vs. planned activities to flag conflicts | Conflict list or "All activities appear suitable" |

---

## 6. System Architecture

### High-Level Architecture

```
+--------------------------------------------------------------------+
|                        STREAMLIT FRONTEND                          |
|  +---------------+  +----------------+  +----------------------+  |
|  | Sidebar       |  | Itinerary Tab  |  | Budget / Map Tabs    |  |
|  | (planning.py) |  | (itinerary.py) |  | (budget.py, etc.)    |  |
|  +-------+-------+  +-------+--------+  +----------------------+  |
+----------|--------------------|----------------------------------------+
           | User Inputs        | Displays Final State
           v                    ^
+--------------------------------------------------------------------+
|                         app.py (Orchestrator)                      |
|   Builds TripState -> runs asyncio event loop -> calls LangGraph   |
+----------------------------+---------------------------------------+
                             |
                             v
+--------------------------------------------------------------------+
|                      LANGGRAPH AGENT WORKFLOW                      |
|                                                                    |
|  trip_graph:                                                       |
|  extraction -> data_gathering <-> tools (ReAct) -> evaluation -> generation
|                                                                    |
|  adapt_graph:                                                      |
|  conflict_id -> adapt_gather <-> adapt_tools -> adapt_eval -> regeneration
|                                                                    |
+----------------------------+---------------------------------------+
                             | Tool calls via LangChain StructuredTool
                             v
+--------------------------------------------------------------------+
|                    MCP CLIENT (mcp_client/client.py)               |
|         MultiServerMCPClient — manages 4 stdio subprocesses        |
|         Converts MCP tools into LangChain StructuredTool objects   |
+------+-------------+---------------+------------------------------+
       | stdio        | stdio         | stdio              | stdio
       v              v               v                    v
+----------+  +---------------+  +----------+  +----------------+
|  Budget  |  | Places Server |  |Transport |  | Weather Server |
|  Server  |  | (5 tools)     |  | Server   |  | (3 tools)      |
|  (4 tools)|  | Foursquare   |  | (3 tools)|  | OpenWeatherMap |
|  No API  |  | API           |  | ORS API  |  |                |
+----------+  +---------------+  +----------+  +----------------+
                                 External APIs (Real-world data)
```

---

### MCP Communication Protocol

```
MCP Client                     MCP Server (subprocess)
    |                                  |
    |--- spawn subprocess ------------>|  python budget_server.py
    |                                  |
    |--- initialize() --------------->|
    |<-- session ready ----------------|
    |                                  |
    |--- list_tools() --------------->|  returns: [calculate_trip_cost, ...]
    |<-- tools registered -------------|
    |                                  |
    |--- call_tool(name, args) ------->|  executes Python function
    |<-- CallToolResult(text) ---------|
    |                                  |
    |--- aclose() ------------------->|  subprocess terminates
```

Each tool result is converted to a plain string and fed back to the LLM as a `ToolMessage` so the LLM can reason about real data.

---

## 7. LangGraph Agent Workflows

### Workflow 1: Trip Planning Graph (trip_graph)

```
[START]
   |
   v
+--------------------------------------------------+
|  EXTRACTION NODE                                 |
|  * Parses user preferences                       |
|  * Identifies 3-5 candidate destinations         |
|  * Uses Gemini LLM with SYSTEM_EXTRACTION_PROMPT |
|  * Outputs: state.candidates                     |
+------------------------+-------------------------+
                         |
                         v
+--------------------------------------------------+
|  DATA GATHERING NODE (ReAct Loop per candidate)  |
|  * search_attractions (Foursquare)               |
|  * get_current_weather (OpenWeatherMap)           |
|  * calculate_travel_time (OpenRouteService)       |
|  * calculate_transport_cost                      |
|  * check_weather_suitability                     |
+------------------------+-------------------------+
                         |
            +------------+-----------+
            |   Route Tool Execution |
            +------------+-----------+
                         |
            +------------+------------------+
            |                               |
            v                               v
     +-----------+               +--------------------+
     | TOOL NODE |               | NEXT CANDIDATE     |
     | (executes |-------------->| SETUP NODE         |
     |  the tool)|               | (increment index)  |
     +-----------+               +--------------------+
            |                               |
            +--- back to DATA GATHERING ----+
                         |
               (when all candidates done)
                         |
                         v
+--------------------------------------------------+
|  EVALUATION NODE                                 |
|  * evaluate_constraints per candidate            |
|  * validate_budget per candidate                 |
|  * compare_trip_options to rank finalists        |
|  * Outputs: state.selected_candidate             |
+------------------------+-------------------------+
                         |
                         v
+--------------------------------------------------+
|  GENERATION NODE                                 |
|  * Gemini + SYSTEM_FINAL_PROMPT                  |
|  * Formats Markdown itinerary                    |
|  * Outputs: state.final_itinerary                |
+------------------------+-------------------------+
                         |
                       [END]
```

---

### Workflow 2: Adaptive Re-planning Graph (adapt_graph)

```
User says: "It's going to rain heavily on Day 2"
   |
   v
+--------------------------------------------------+
|  CONFLICT IDENTIFICATION NODE                    |
|  * Reads original_itinerary from state           |
|  * Uses LLM to identify ONLY broken components   |
|  * Outputs: state.affected_components            |
+------------------------+-------------------------+
                         |
                         v
+--------------------------------------------------+
|  ADAPTATION DATA GATHERING NODE (ReAct Loop)     |
|  * Gathers alternatives for affected parts only  |
|  * Calls get_weather_forecast (confirm weather)  |
|  * Calls search_attractions (indoor alternatives)|
|  * Calls check_weather_suitability (validate)    |
+------------------------+-------------------------+
                         |
            +-adapt_tools route-+
            |                   |
            v                   |
     +-----------+              |
     | ADAPT     |<-------------+
     | TOOL NODE |
     +-----------+
                         |
                         v
+--------------------------------------------------+
|  ADAPTATION EVALUATION NODE                      |
|  * Validates alternatives are feasible           |
|  * Confirms new activities are weather-suitable  |
|  * Confirms budget is not exceeded by changes    |
+------------------------+-------------------------+
                         |
                         v
+--------------------------------------------------+
|  REGENERATION NODE                               |
|  * Splices validated fixes into original plan    |
|  * Generates updated Markdown for changed parts  |
|  * Produces adaptation_summary                   |
+------------------------+-------------------------+
                         |
                       [END]
```

---

## 8. External APIs Used

| API | Provider | Used For | Env Variable |
|---|---|---|---|
| Gemini LLM | Google | Core reasoning in all LangGraph nodes | `GOOGLE_API_KEY` |
| Geocode Autocomplete | Geoapify | Location search dropdown in sidebar | `GEOAPIFY_API_KEY` |
| Places Search | Foursquare | Finding attractions, restaurants, hotels | `FOURSQUARE_API_KEY` |
| Weather Current/Forecast | OpenWeatherMap | Real weather data | `OPENWEATHER_API_KEY` |
| Route Calculation | OpenRouteService | Travel time & distance calculation | `OPENROUTE_API_KEY` |
| Fallback Geocoding | OpenStreetMap Nominatim | Used when Geoapify is rate-limited | No key needed |

---

## 9. Feature Walkthrough

### Feature 1: Geoapify Location Autocomplete

When you type in the Starting Location or Target Destination fields:

```
User types: "Uma Vidhyalaya Vadodara"
                  |
                  v
    utils/place_search.py -> get_geoapify_autocomplete()
                  |
                  v
    GET https://api.geoapify.com/v1/geocode/autocomplete
        ?text=Uma+Vidhyalaya+Vadodara
        &filter=countrycode:in       <- restricted to India
        &apiKey=GEOAPIFY_API_KEY
                  |
                  v
    Returns list of matching places
    Cached in GEOAPIFY_CACHE dictionary
                  |
                  v
    Displayed as Streamlit selectbox dropdown
    User selects -> place_name, formatted_address,
                    lat, lon, place_id captured
```

**Fallback chain if API fails:**
1. Geoapify Autocomplete (primary)
2. OpenStreetMap Nominatim (if Geoapify returns 429/timeout)
3. Local coordinate database (hardcoded coordinates for major Indian cities)

---

### Feature 2: Multi-Candidate Destination Selection

The agent evaluates 3-5 nearby alternatives and picks the best based on real constraints:

```
User picks: "Vadodara"
      |
      v
Extraction Node asks Gemini:
"Given: budget 5000 INR, interests: Nature, starting from Ahmedabad,
 what are 3-5 candidate destinations near Vadodara?"
      |
      v
Candidates: ["Vadodara", "Pavagadh", "Champaner", "Anand"]
      |
      v
For each candidate: Data Gathering (MCP tools) -> Evaluation -> Select Best
```

---

### Feature 3: Deterministic Budget Calculation

```
LLM thinks: "I need to calculate if this trip fits the budget"
      |
      v
Tool call: calculate_trip_cost(days=3, tier="mid",
              transport_cost=150.0, activities_cost=80.0)
      |
      v
Budget Server computes:
  accommodation: 150 x 2 nights = 300
  food: 60 x 3 days = 180
  transport: 150
  activities: 80
  TOTAL: 710
      |
      v
Tool call: validate_budget(estimated_cost=710, user_budget=5000)
      |
      v
Result: {"status": "WITHIN_BUDGET", "variance": 4290}
```

---

### Feature 4: Weather-Aware Activity Planning

```
Tool call: get_weather_forecast("Vadodara", days=3)
-> "Day 2: Heavy Rain (thunderstorm), Temp: 27C, Precip: 90%"
      |
      v
Tool call: check_weather_suitability(
  forecast_text="Heavy Rain",
  activities=["Hiking at Pavagadh", "Museum Visit", "City Walk"]
)
      |
      v
Result: "Weather Conflicts Detected:
  - 'Hiking at Pavagadh' not recommended due to Heavy Rain"
      |
      v
LLM swaps outdoor activities -> recommends indoor alternatives
```

---

### Feature 5: Demo Mode

The app includes a **Presentation Demo Mode** toggle that bypasses all real API calls and returns pre-baked results from `agent/demo_data.py`. This is useful for:

- Demonstrating the app without live API keys
- Presentations where network reliability is uncertain
- Testing the full UI without incurring API costs

---

## 10. Data Flow — Step by Step

```
Step 1:  User fills sidebar (location, budget, interests)
         Clicks "Generate Trip Plan"

Step 2:  app.py reads sidebar values, builds TripState:
         {
           location: "Ahmedabad",
           destination_location: "Vadodara",
           budget: 5000.0,
           interests: ["Nature & Outdoors", "Food & Street Dining"],
           duration_days: 3,
           transport_mode: "driving-car",
           max_travel_mins: 180.0,
           origin_details: {lat, lon, place_id, ...},
           destination_details: {lat, lon, place_id, ...}
         }

Step 3:  app.py calls _run_async_task(generate_trip(initial_state))
         Creates fresh asyncio event loop

Step 4:  generate_trip() calls mcp_client.connect()
         Spawns 4 subprocess servers (budget, places, transport, weather)
         Each server initializes a session
         All 15 tools registered as LangChain StructuredTool objects

Step 5:  trip_graph.ainvoke(initial_state) starts execution

Step 6:  Extraction Node
         Gemini called with extraction prompt
         Returns JSON list of 3-5 candidate city names
         state.candidates populated

Step 7:  Data Gathering Node (runs for each candidate)
         LLM + tools in a ReAct loop:
           LLM -> tool_call -> ToolNode -> result -> LLM -> tool_call -> ... -> done
         Tools called: search_attractions, get_weather_forecast,
           calculate_travel_time, calculate_transport_cost, check_weather_suitability
         Data stored in candidate["context"]

Step 8:  Evaluation Node
         evaluate_constraints called per candidate
         validate_budget called per candidate
         compare_trip_options called to rank finalists
         state.selected_candidate = best option

Step 9:  Generation Node
         Gemini called with all gathered context + SYSTEM_FINAL_PROMPT
         Produces complete Markdown itinerary
         state.final_itinerary = itinerary string

Step 10: mcp_client.disconnect() -> all subprocesses terminated

Step 11: Streamlit displays:
         - Itinerary tab: formatted day-by-day plan
         - Budget tab: cost breakdown
         - Recommendations tab: curated places list
         - Agent Activity: reasoning log from LangGraph nodes
```

---

## 11. Environment Configuration

Copy `.env.example` to `.env` and fill in your API keys:

```env
# AI / LLM
GOOGLE_API_KEY=your_google_gemini_api_key

# Location Autocomplete
GEOAPIFY_API_KEY=your_geoapify_api_key

# Places Data
FOURSQUARE_API_KEY=your_foursquare_api_key

# Weather
OPENWEATHER_API_KEY=your_openweathermap_api_key

# Routing
OPENROUTE_API_KEY=your_openrouteservice_api_key
```

> **Security Note**: The `.env` file is never committed to version control. Keys are loaded via `python-dotenv` and never exposed in the UI or logs.

---

## 12. Running the Project

### Prerequisites

```bash
pip install -r requirements.txt
```

### Start the App

```bash
# Option 1: Direct
streamlit run app.py

# Option 2: Windows batch launcher
start.bat

# Option 3: Full-featured launcher with env checks
run.bat
```

### Run Tests

```bash
# UI tests
python test_ui.py

# Agent logic tests (no real API calls)
python test_agent_mock.py

# MCP server unit tests
python test_mcps.py
```

---

## Summary Table — All 15 MCP Tools

| # | Server | Tool Name | External API | Purpose |
|---|---|---|---|---|
| 1 | Budget | `calculate_trip_cost` | None (math) | Compute total trip cost by tier |
| 2 | Budget | `validate_budget` | None (math) | Check if cost exceeds user budget |
| 3 | Budget | `evaluate_constraints` | None (logic) | Validate travel time, weather & transport mode |
| 4 | Budget | `compare_trip_options` | None (logic) | Rank two trip alternatives deterministically |
| 5 | Places | `search_destinations` | Foursquare | Find candidate cities/places |
| 6 | Places | `search_attractions` | Foursquare | Find tourist landmarks & activities |
| 7 | Places | `search_restaurants` | Foursquare | Find dining options |
| 8 | Places | `search_hotels` | Foursquare | Find accommodation options |
| 9 | Places | `get_place_details` | Foursquare | Get full info for a specific place ID |
| 10 | Transport | `find_transport_options` | None | List supported routing modes |
| 11 | Transport | `calculate_travel_time` | OpenRouteService | Real route distance & duration between coords |
| 12 | Transport | `calculate_transport_cost` | None (heuristic) | Estimate travel cost from distance |
| 13 | Weather | `get_current_weather` | OpenWeatherMap | Live weather conditions |
| 14 | Weather | `get_weather_forecast` | OpenWeatherMap | Multi-day weather forecasts |
| 15 | Weather | `check_weather_suitability` | None (logic) | Match weather against planned activities |

---

*Generated: 2026-08-17 | Adaptive AI Trip Planner — Full Project Guide*
