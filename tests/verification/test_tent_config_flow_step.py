#!/usr/bin/env python3
"""Test script to verify Tent config flow step functionality."""

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
from custom_components.plant.const import DEVICE_TYPE_TENT, FLOW_PLANT_INFO, ATTR_DEVICE_TYPE

# Set up logging
logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

async def test_tent_config_flow_step():
    """Test Tent config flow step functionality."""
    print("Testing Tent config flow step...")
    
    # Create config flow instance
    flow = PlantConfigFlow()
    
    # Mock hass
    flow.hass = Mock(spec=HomeAssistant)
    
    # Mock _async_current_entries to return a config entry with is_config=True
    config_entry = Mock()
    config_entry.data = {
        "is_config": True,
        FLOW_PLANT_INFO: {
            "default_icon": "⛺"
        }
    }
    
    flow._async_current_entries = Mock(return_value=[config_entry])
    
    try:
        # Test the tent config flow step
        result = await flow.async_step_tent(user_input=None)
        print("✓ async_step_tent executed without errors")
        
        # Check if the result is a form
        if 'type' in result and result['type'] == 'form':
            print("✓ async_step_tent returned a form")
            
            # Check if the form has the expected step_id
            if 'step_id' in result and result['step_id'] == 'tent':
                print("✓ async_step_tent returned the correct step_id")
            else:
                print(f"✗ async_step_tent returned incorrect step_id: {result.get('step_id')}")
                return False
                
            # Check if the form has a data_schema
            if 'data_schema' in result:
                print("✓ async_step_tent returned a data_schema")
            else:
                print("✗ async_step_tent did not return a data_schema")
                return False
                
        else:
            print(f"✗ async_step_tent did not return a form. Result type: {result.get('type')}")
            return False
            
        print("✓ Tent config flow step test passed")
        return True
        
    except Exception as e:
        print(f"✗ Tent config flow step test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_tent_config_flow_step())
    if result:
        print("All Tent config flow step tests passed!")
    else:
        print("Some Tent config flow step tests failed!")
        sys.exit(1)