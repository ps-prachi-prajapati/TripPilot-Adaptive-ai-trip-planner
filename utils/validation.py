def validate_trip_inputs(location: str, budget: float) -> str | None:
    """
    Validates basic user inputs from the UI.
    Returns an error message string if invalid, None if valid.
    """
    if not location or not location.strip():
        return "Please provide a starting location."
        
    if budget < 100:
        return "Budget must be at least $100."
        
    return None


