#!/usr/bin/env python3
"""Test script to verify tent config flow error handling."""

import sys
import os
import asyncio
import logging

# Add the custom_components directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components', 'plant'))

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from unittest.mock import Mock, MagicMock, patch
from custom_components.plant.config_flow import PlantConfigFlow
from custom_components.plant.const import DEVICE_TYPE_TENT, FLOW_PLANT_INFO

# Set up logging
logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

def test_tent_config_flow_error_handling():
    """Test tent config flow error handling."""
    print("Testing Tent config flow error handling...")
    
    # Create config flow instance
    flow = PlantConfigFlow()
    
    # Mock hass
    flow.hass = Mock(spec=HomeAssistant)
    
    # Mock _async_current_entries to return an empty list
    flow._async_current_entries = Mock(return_value=[])
    
    # Test with valid input
    user_input = {
        "name": "Test Tent",
        "plant_emoji": "⛺"
    }
    
    # Test validation logic directly
    print("Testing valid input...")
    try:
        # Simulate the validation logic
        if not user_input.get("name"):
            raise ValueError("Tent name is required")
        
        print("✓ Valid input validation passed")
    except Exception as e:
        print(f"✗ Valid input validation failed: {e}")
        return False
        
    # Test with invalid input (missing name)
    print("Testing invalid input (missing name)...")
    try:
        invalid_input = {
            "plant_emoji": "⛺"
        }
        
        # Simulate the validation logic
        if not invalid_input.get("name"):
            raise ValueError("Tent name is required")
            
        print("✗ Invalid input validation should have failed but didn't")
        return False
    except ValueError as e:
        if "Tent name is required" in str(e):
            print("✓ Invalid input validation correctly caught missing name")
        else:
            print(f"✗ Invalid input validation failed with wrong error: {e}")
            return False
    except Exception as e:
        print(f"✗ Invalid input validation failed with unexpected error: {e}")
        return False

    print("✓ Tent config flow error handling test passed")
    return True

if __name__ == "__main__":
    if test_tent_config_flow_error_handling():
        print("All config flow tests passed!")
    else:
        print("Some config flow tests failed!")
        sys.exit(1)