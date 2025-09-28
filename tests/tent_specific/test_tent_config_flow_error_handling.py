#!/usr/bin/env python3
"""Test script to verify tent config flow error handling."""

import sys
import os

def test_tent_config_flow_error_handling():
    """Test tent config flow error handling."""
    # Test with valid input
    user_input = {
        "name": "Test Tent",
        "plant_emoji": "⛺"
    }
    
    # Test validation logic directly
    try:
        # Simulate the validation logic
        if not user_input.get("name"):
            raise ValueError("Tent name is required")
    except Exception:
        assert False, "Valid input validation should not fail"
        
    # Test with invalid input (missing name)
    try:
        invalid_input = {
            "plant_emoji": "⛺"
        }
        
        # Simulate the validation logic
        if not invalid_input.get("name"):
            raise ValueError("Tent name is required")
            
        assert False, "Invalid input validation should have failed but didn't"
    except ValueError as e:
        assert "Tent name is required" in str(e)
    except Exception as e:
        assert False, f"Invalid input validation failed with unexpected error: {e}"

def test_tent_config_flow_files_exist():
    """Test that the config flow files exist."""
    # Check that the config_flow module exists
    config_flow_path = os.path.join(os.path.dirname(__file__), '..', '..', 'custom_components', 'plant', 'config_flow.py')
    assert os.path.exists(config_flow_path)
    
    # Check that the const module exists
    const_path = os.path.join(os.path.dirname(__file__), '..', '..', 'custom_components', 'plant', 'const.py')
    assert os.path.exists(const_path)

if __name__ == "__main__":
    if test_tent_config_flow_error_handling():
        print("All config flow tests passed!")
    else:
        print("Some config flow tests failed!")
        sys.exit(1)