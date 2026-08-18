from streamlit.testing.v1 import AppTest
import os

def test_app():
    print("Initializing AppTest...")
    at = AppTest.from_file("app.py")
    
    # Run the app
    at.run(timeout=15)
    
    assert not at.exception, f"App crashed on startup: {at.exception}"
    print("SUCCESS: Application Startup OK")
    
    # Check Demo Mode toggle exists in sidebar
    assert len(at.sidebar.toggle) > 0 or len(at.toggle) > 0, "Demo Mode toggle not found"
    
    # Enable demo mode
    at.sidebar.toggle[0].set_value(True).run(timeout=15)
    
    assert not at.exception, f"App crashed on toggling Demo mode: {at.exception}"
    
    # Test generation (click button)
    at.sidebar.button[0].click().run(timeout=15)
    
    assert not at.exception, f"App crashed during generation: {at.exception}"
    
    # Check if main tabs are rendered
    assert len(at.tabs) >= 4, "Tabs not rendered properly"
    print("SUCCESS: Main Generation Flow (Demo Mode) OK")
    
    # Test adaptation (Text area + Adapt button)
    assert len(at.text_area) > 0, "Adaptation text area not found"
    
    # Set text and click adapt button
    at.text_area[0].input("It is raining").run(timeout=15)
    # The adapt button is the main button on the page (index 0 on main page, after sidebar button)
    if len(at.button) > 0:
        at.button[0].click().run(timeout=15)
    
    assert not at.exception, f"App crashed during adaptation: {at.exception}"
    print("SUCCESS: Adaptation Flow (Demo Mode) OK")

def test_validation():
    print("Testing Validation...")
    at2 = AppTest.from_file("app.py")
    at2.run(timeout=15)
    assert not at2.exception, f"App crashed on startup: {at2.exception}"
    
    # Demo Mode is OFF by default or set to False
    at2.sidebar.toggle[0].set_value(False).run(timeout=15)
    
    # Clear the Starting Location text input directly
    at2.sidebar.text_input[0].input("").run(timeout=15)
    
    # Click the Generate button
    at2.sidebar.button[0].click().run(timeout=15)
    
    # Should show a warning somewhere
    warnings = list(at2.sidebar.warning) + list(at2.warning)
    assert len(warnings) > 0, "Warning for missing location not found"
    assert any("Please provide a starting location" in w.value for w in warnings)
    print("SUCCESS: User Input Validation OK")






if __name__ == "__main__":
    test_app()
    test_validation()

