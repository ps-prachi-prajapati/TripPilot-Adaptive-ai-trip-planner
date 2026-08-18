import streamlit as st
from ui.components import render_budget_breakdown

def render_budget_tab(state):
    selected = state.get("selected_candidate", {})
    variance = selected.get("score", 150.0)
    est_cost = max(0, state["budget"] - variance)
    
    mock_breakdown = {
        "accommodation": est_cost * 0.4,
        "food": est_cost * 0.3,
        "transportation": est_cost * 0.1,
        "activities": est_cost * 0.2
    }
    render_budget_breakdown(state["budget"], est_cost, mock_breakdown)
