import streamlit as st
import os
import re

def inject_custom_css():
    """Reads the custom CSS file and injects it into Streamlit."""
    css_path = os.path.join(os.path.dirname(__file__), 'styles.css')
    try:
        with open(css_path, 'r') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        pass
def render_clean_html(html_str: str):
    """Strips linebreaks and leading spaces so Streamlit never parses HTML as markdown code blocks."""
    clean = "".join([line.strip() for line in html_str.splitlines()])
    st.markdown(clean, unsafe_allow_html=True)

def render_empty_state():
    """Renders a beautiful welcome screen before a trip is generated."""
    html = """
    <div class="empty-state">
        <h1>🌍 TripPilot &mdash; Adaptive AI Trip Planner</h1>
        <p>Your intelligent, self-correcting travel companion.</p>
        <p style="font-size: 0.9rem; margin-top: 10px; color: #475569;">Use the sidebar to define your ideal getaway. The AI will cross-reference real-time weather, routing, and venue data to build the perfect itinerary.</p>
    </div>
    """
    render_clean_html(html)

def render_travel_timing_card(start_location: str, destination_name: str, transport_mode: str, max_travel_mins: float):
    """Renders a prominent header showing starting location, destination, and travel timings."""
    origin = start_location if start_location else "Starting Location"
    dest = destination_name if destination_name else "Destination"
    mode = transport_mode if transport_mode else "driving-car"
    mins = int(max_travel_mins) if max_travel_mins else 180
    
    html = f"""
    <div style="background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%); border: 1px solid #334155; border-radius: 12px; padding: 20px; margin-bottom: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); color: #F8FAFC;">
        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 16px;">
            <div style="flex: 1; min-width: 200px;">
                <span style="font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.08em; color: #94A3B8; font-weight: 600;">Origin</span>
                <h3 style="margin: 4px 0 0 0; color: #F8FAFC; font-size: 1.25rem;">📍 {origin}</h3>
            </div>
            
            <div style="text-align: center; flex: 1; min-width: 180px;">
                <div style="display: inline-block; background: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.3); padding: 6px 14px; border-radius: 20px; color: #38BDF8; font-size: 0.85rem; font-weight: 600;">
                    🚘 {mode.replace('-', ' ').title()} (~{mins} mins max)
                </div>
                <div style="font-size: 0.8rem; color: #94A3B8; margin-top: 6px;">Recommended Departure: <strong>8:00 AM</strong></div>
            </div>
            
            <div style="flex: 1; min-width: 200px; text-align: right;">
                <span style="font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.08em; color: #94A3B8; font-weight: 600;">Destination</span>
                <h3 style="margin: 4px 0 0 0; color: #34D399; font-size: 1.25rem;">🏁 {dest}</h3>
            </div>
        </div>
    </div>
    """
    render_clean_html(html)

def render_destination_card(candidate: dict, is_selected: bool = False):
    """Renders a premium HTML card for a candidate destination using flex layouts."""
    name = candidate.get("name", "Unknown Destination")
    score = candidate.get("score", 0.0)
    valid = candidate.get("valid", False)
    rejection_reason = candidate.get("rejection_reason", "")
    
    # Border color should reflect validity and selection
    border_color = "#34D399" if is_selected and valid else ("#F87171" if not valid else "#4A5568")
    status_color = "#34D399" if valid else "#F87171"
    
    # Construct tags
    tags_html = ""
    if is_selected:
        if valid:
            tags_html += '<span class="tag success">🏆 Selected Match</span>'
        else:
            tags_html += '<span class="tag warning" style="background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.3); color: #F59E0B; padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600;">⚠️ Selected Match (Budget Exceeded)</span>'
    elif not valid:
        tags_html += '<span class="tag danger">❌ Rejected</span>'
    else:
        tags_html += '<span class="tag">✅ Valid Alternative</span>'
        
    html = f"""
    <div class="premium-card" style="border-top: 3px solid {border_color};">
        <h3>Candidate</h3>
        <h2>{name}</h2>
        <div style="margin-bottom: 12px;">{tags_html}</div>
        
        <div class="card-row">
            <div class="card-stat">
                <span class="card-stat-label">Budget Fit</span>
                <span class="card-stat-value">₹{abs(round(score, 2))} {'Under' if valid else 'Variance'}</span>
            </div>
            <div class="card-stat" style="text-align: right;">
                <span class="card-stat-label">Status</span>
                <span class="card-stat-value" style="color: {status_color};">{'Approved' if valid else 'Failed'}</span>
            </div>
        </div>
    """
    
    if not valid and rejection_reason:
        html += f"""
        <div style="margin-top: 20px; padding: 12px; background: rgba(248,113,113,0.1); border-left: 3px solid #F87171; border-radius: 4px; color: #FCA5A5; font-size: 0.85rem;">
            <strong>Constraint Failed:</strong> {rejection_reason}
        </div>
        """
        
    html += "</div>"
    render_clean_html(html)

def render_budget_breakdown(budget: float, estimated_cost: float, breakdown: dict):
    """Renders an upgraded visual breakdown of the trip cost."""
    variance = budget - estimated_cost
    is_under = variance >= 0
    status_color = "#059669" if is_under else "#DC2626"
    status_text = "Under Budget" if is_under else "Over Budget"
    
    # Calculate percentages for the bars
    total = max(budget, estimated_cost)
    if total == 0: total = 1
    
    def bar(val, color):
        pct = min(100, (val / total) * 100)
        return f"""
        <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 0.85rem; color: #334155;">
            <span>₹{round(val, 2)}</span>
            <span style="color: #64748B;">{round(pct)}%</span>
        </div>
        <div style="width: 100%; background: #E2E8F0; height: 8px; border-radius: 4px; margin-bottom: 16px;">
            <div style="width: {pct}%; background: {color}; height: 100%; border-radius: 4px; transition: width 1s ease;"></div>
        </div>
        """
    
    html = f"""
    <div class="premium-card">
        <h3>Total Estimated Cost</h3>
        <h2 style="color: {status_color}; margin-bottom: 8px;">₹{round(estimated_cost, 2)} <span style="font-size: 1.1rem; color: #64748B; font-weight: 500;">/ ₹{budget} max</span></h2>
        <span class="tag {'success' if is_under else 'danger'}" style="margin-bottom: 24px;">{status_text} (₹{abs(round(variance, 2))})</span>
        
        <div>
            <h3 style="margin-bottom: 12px; font-size: 0.8rem;">Category Breakdown</h3>
            <p style="margin-bottom: 2px; font-size: 0.85rem; color: #475569; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">🏨 Accommodation</p>
            {bar(breakdown.get('accommodation', 0), '#6366F1')}
            
            <p style="margin-bottom: 2px; font-size: 0.85rem; color: #475569; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">🚗 Transportation</p>
            {bar(breakdown.get('transportation', 0), '#2563EB')}
            
            <p style="margin-bottom: 2px; font-size: 0.85rem; color: #475569; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">🍽️ Food & Dining</p>
            {bar(breakdown.get('food', 0), '#D97706')}
            
            <p style="margin-bottom: 2px; font-size: 0.85rem; color: #475569; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">🎟️ Activities</p>
            {bar(breakdown.get('activities', 0), '#059669')}
        </div>
    </div>
    """
    render_clean_html(html)

def render_agent_activity(logs: list):
    """Renders a beautiful timeline of agent activity."""
    if not logs:
        st.info("No technical logs available for this session.")
        return
        
    html = '<div class="agent-log-container">'
    for log in logs:
        title = log.get("title", "")
        details = log.get("details", "")
        log_type = log.get("type", "info")
        
        icon = "⚙️"
        if log_type == "decision": icon = "🧠"
        elif log_type == "tool_result": icon = "📥"
        elif log_type == "tool_call": icon = "🔧"
        
        html += f'''
        <div class="agent-log-item">
            <div class="log-indicator"></div>
            <div class="log-header">
                <span class="log-icon">{icon}</span>
                <span class="log-title">{title}</span>
            </div>
        '''
        if details:
            html += f'''
            <div class="log-content">
                <code>{details}</code>
            </div>
            '''
        html += '</div>'
        
    html += '</div>'
    render_clean_html(html)
