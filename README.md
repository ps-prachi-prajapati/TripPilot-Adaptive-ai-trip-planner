<div align="center">

# 🌍 TripPilot — Adaptive AI Trip Planner

**A multi-agent AI travel planner that uses real-world data tools to plan, evaluate, and adaptively re-plan trips.**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.40+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

</div>

---

## 📸 Screenshots

<div align="center">

| **Home Screen** | **Generated Itinerary** |
| :---: | :---: |
| <img src="https://github.com/user-attachments/assets/c029b5d5-a6fb-4dce-a2eb-051f7995a6d2" width="100%" alt="Home Screen" /> | <img src="https://github.com/user-attachments/assets/8a4c3918-f8e8-4b2f-830b-8118712fe2dc" width="100%" alt="Generated Itinerary" /> |
| **Budget Breakdown** | **Agent Activity Log** |
| <img src="https://github.com/user-attachments/assets/62e235b8-90b5-476c-adf3-bc55c92f6274" width="100%" alt="Budget Breakdown" /> | _(Screenshot to be added)_ |

</div>

---

## 🎯 What Problem Does This Solve?

Standard LLM-based travel planners have two major issues:

| Problem | Standard AI | TripPilot |
|---|---|---|
| **Hallucinations** | LLM guesses distances, costs, weather | MCP tools fetch real data from live APIs |
| **Plan disruptions** | Regenerates entire itinerary from scratch | Surgically patches only the affected segments |

---

## ✨ Key Features

- **📍 Location Autocomplete** — Geoapify-powered search restricted to India with live suggestions
- **🤖 Multi-Candidate Evaluation** — AI evaluates 3–5 destinations and picks the best one based on real constraints
- **🌦️ Weather-Aware Planning** — Automatically swaps outdoor activities when rain is forecasted
- **💰 Deterministic Budget Math** — All cost calculations are done by isolated Python tools, never by the LLM
- **🔄 Adaptive Re-planning** — A dedicated second agent surgically patches broken itinerary segments
- **🎥 Demo Mode** — Fully pre-baked scenario for presentations without needing live API keys
- **📊 Agent Activity Log** — Full transparency into every tool call and LLM decision

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                  STREAMLIT FRONTEND                  │
│  Sidebar (Inputs) → Itinerary / Budget / Map Tabs   │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│               app.py  (Orchestrator)                │
│   Builds TripState → asyncio → LangGraph graphs     │
└────────────────────┬────────────────────────────────┘
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
   trip_graph              adapt_graph
   (Plan new trip)         (Fix disrupted trip)
          │                     │
          └──────────┬──────────┘
                     ▼
┌─────────────────────────────────────────────────────┐
│          MCP CLIENT  (stdio transport)               │
│   Connects to 4 servers · exposes 15 LangChain tools│
└──────┬──────────┬────────────┬──────────────────────┘
       │          │            │           │
       ▼          ▼            ▼           ▼
  Budget       Places      Transport   Weather
  Server       Server       Server     Server
  (4 tools)   (5 tools)   (3 tools)  (3 tools)
  No API      Foursquare  OpenRoute  OpenWeather
```

---

## 🛠️ MCP Tools — All 15 Tools

### Budget Server (`budget_server.py`) — No external API
| Tool | Purpose |
|---|---|
| `calculate_trip_cost` | Computes full cost breakdown by accommodation tier |
| `validate_budget` | Checks if estimated cost exceeds user budget |
| `evaluate_constraints` | Validates travel time, weather, transport mode |
| `compare_trip_options` | Deterministically ranks two destination options |

### Places Server (`places_server.py`) — Foursquare API
| Tool | Purpose |
|---|---|
| `search_destinations` | Finds candidate cities matching a query |
| `search_attractions` | Finds tourist landmarks & activities |
| `search_restaurants` | Finds dining options |
| `search_hotels` | Finds accommodation options |
| `get_place_details` | Gets full details for a specific place ID |

### Transport Server (`transport_server.py`) — OpenRouteService API
| Tool | Purpose |
|---|---|
| `find_transport_options` | Lists supported routing modes |
| `calculate_travel_time` | Real route distance & duration between coordinates |
| `calculate_transport_cost` | Estimates travel cost from distance |

### Weather Server (`weather_server.py`) — OpenWeatherMap API
| Tool | Purpose |
|---|---|
| `get_current_weather` | Live weather conditions |
| `get_weather_forecast` | Multi-day weather forecast |
| `check_weather_suitability` | Flags weather vs. activity conflicts |

---

## 📁 Project Structure

```
TripPilot/
│
├── app.py                    # Streamlit entry point
├── requirements.txt          # Python dependencies
├── .env.example              # Template for API keys
├── run.bat                   # Windows batch launcher
│
├── agent/
│   ├── agent.py              # All LangGraph node functions
│   ├── graph.py              # trip_graph & adapt_graph
│   ├── state.py              # TripState TypedDict
│   ├── prompts.py            # System prompts
│   └── demo_data.py          # Pre-baked demo scenario
│
├── mcp_servers/              # 4 FastMCP server scripts
│   ├── budget_server.py
│   ├── places_server.py
│   ├── transport_server.py
│   └── weather_server.py
│
├── mcp_client/
│   └── client.py             # MultiServerMCPClient
│
├── services/                 # Raw API layer
│   ├── places.py
│   ├── transport.py
│   └── weather.py
│
├── ui/
│   ├── planning.py           # Sidebar inputs
│   ├── itinerary.py          # Itinerary tab
│   ├── budget.py             # Budget tab
│   ├── recommendations.py    # Recommendations tab
│   ├── home.py               # Header
│   ├── components.py         # Shared UI helpers
│   └── styles.css            # Custom CSS theme
│
└── utils/
    ├── place_search.py       # Geoapify autocomplete
    ├── validation.py         # Input validation
    └── logging.py            # Logging setup
```

---

## ⚙️ Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/ps-prachi-prajapati/TripPilot-Adaptive-ai-trip-planner.git
cd TripPilot-Adaptive-ai-trip-planner
```

### 2. Create and activate virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example file and fill in your API keys:
```bash
cp .env.example .env
```

Edit `.env`:
```env
# Google Gemini (LLM)
GOOGLE_API_KEY=your_google_gemini_api_key

# Geoapify (Location Autocomplete)
GEOAPIFY_API_KEY=your_geoapify_api_key

# Foursquare (Places)
FOURSQUARE_API_KEY=your_foursquare_api_key

# OpenWeatherMap (Weather)
OPENWEATHER_API_KEY=your_openweathermap_api_key

# OpenRouteService (Routing)
OPENROUTE_API_KEY=your_openrouteservice_api_key
```

### 5. Run the app
```bash
streamlit run app.py
```

Or use the Windows launcher:
```bat
run.bat
```

---

## 🔑 Getting API Keys

| Service | Free Tier | Sign Up |
|---|---|---|
| Google Gemini | ✅ Yes | [aistudio.google.com](https://aistudio.google.com) |
| Geoapify | ✅ Yes (3000 req/day) | [geoapify.com](https://www.geoapify.com) |
| Foursquare | ✅ Yes | [foursquare.com/developers](https://foursquare.com/developers) |
| OpenWeatherMap | ✅ Yes (1000 req/day) | [openweathermap.org/api](https://openweathermap.org/api) |
| OpenRouteService | ✅ Yes (2000 req/day) | [openrouteservice.org](https://openrouteservice.org) |

---

## 🧪 Running Tests

```bash
# UI tests
python test_ui.py

# Agent logic tests (no real API calls needed)
python test_agent_mock.py

# MCP server unit tests
python test_mcps.py
```

---

## 🎥 Demo Mode

Don't have API keys yet? Enable **Demo Mode** in the sidebar toggle to run a fully pre-baked Ahmedabad → Vadodara scenario — no keys required.

---

## 🔄 How Adaptive Re-planning Works

```
User: "It's going to rain on Day 2"
          │
          ▼
  Conflict Identification Node
  → Identifies only Day 2 outdoor activities as affected
          │
          ▼
  Adaptation Data Gathering Node
  → Fetches indoor alternatives (museums, malls, cafes)
  → Confirms new weather forecast
          │
          ▼
  Adaptation Evaluation Node
  → Validates new activities are budget-safe & weather-suitable
          │
          ▼
  Regeneration Node
  → Splices fix into original plan
  → Only Day 2 changes; rest of itinerary unchanged ✅
```

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you'd like to change.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

Made with ❤️ by [Prachi Prajapati](https://github.com/ps-prachi-prajapati)

</div>
