#!/usr/bin/env python3
"""Test script to verify create_tent service registration and functionality."""

import sys
import os
import asyncio
import logging

# Add the custom_components directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components', 'plant'))

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from unittest.mock import Mock, MagicMock, patch
from custom_components.plant.services import async_setup_services, CREATE_TENT_SCHEMA
from custom_components.plant.const import DOMAIN

# Set up logging
logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

async def test_create_tent_service_registration():
    """Test create_tent service registration."""
    print("Testing create_tent service registration...")
    
    # Create hass instance
    hass = Mock(spec=HomeAssistant)
    
    # Mock services registration
    hass.services = Mock()
    hass.services.async_register = Mock()
    hass.services.has_service = Mock(return_value=False)
    
    # Mock config entries
    hass.config_entries = Mock()
    hass.config_entries.async_entries = Mock(return_value=[])
    hass.config_entries.flow = Mock()
    hass.config_entries.flow.async_init = Mock()
    
    # Mock data registry
    hass.data = {}
    
    try:
        # Test schema definition
        assert CREATE_TENT_SCHEMA is not None
        assert isinstance(CREATE_TENT_SCHEMA, object)  # vol.Schema type
        print("✓ CREATE_TENT_SCHEMA is properly defined")
        
        # Test service setup
        await async_setup_services(hass)
        print("✓ async_setup_services completed without errors")
        
        # Check if create_tent service was registered
        service_registered = False
        for call in hass.services.async_register.call_args_list:
            args, kwargs = call
            if len(args) >= 2 and args[0] == DOMAIN and args[1] == "create_tent":
                service_registered = True
                break
        
        if service_registered:
            print("✓ create_tent service is properly registered")
        else:
            print("✗ create_tent service is NOT registered")
            return False
            
        print("✓ create_tent service registration test passed")
        return True
        
    except Exception as e:
        print(f"✗ create_tent service registration test failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_create_tent_service_registration())
    if result:
        print("All create_tent service tests passed!")
    else:
        print("Some create_tent service tests failed!")
        sys.exit(1)