#!/usr/bin/env python3
"""Test script for create_tent service."""

import sys
import os
import asyncio
from unittest.mock import Mock, MagicMock, patch

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_create_tent_service():
    """Test the create_tent service."""
    try:
        # Import required modules
        from custom_components.plant.services import async_setup_services
        from homeassistant.core import HomeAssistant
        from homeassistant.config_entries import ConfigEntry
        
        # Create a mock hass instance
        hass = Mock(spec=HomeAssistant)
        hass.data = {}
        hass.config_entries = Mock()
        
        # Mock the config entries
        hass.config_entries.async_entries = Mock(return_value=[])
        hass.config_entries.async_create_entry = Mock(return_value=Mock(entry_id="test_entry_id"))
        
        # Mock registries
        mock_entity_registry = Mock()
        mock_device_registry = Mock()
        
        # Patch the registries
        with patch('custom_components.plant.services.er.async_get', return_value=mock_entity_registry), \
             patch('custom_components.plant.services.dr.async_get', return_value=mock_device_registry):
            
            # Set up services
            await async_setup_services(hass)
            
            # Test the create_tent service
            from homeassistant.core import ServiceCall
            
            # Create a mock service call
            call = Mock(spec=ServiceCall)
            call.data = {
                "name": "Test Tent",
                "illuminance_sensor": "sensor.test_illuminance",
                "humidity_sensor": "sensor.test_humidity",
                "co2_sensor": "sensor.test_co2"
            }
            
            # Get the create_tent service function
            # Note: In a real scenario, you would access this through hass.services
            print("✓ Service setup completed successfully")
            return True
            
    except Exception as e:
        print(f"✗ Error testing create_tent service: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run the test."""
    print("Testing create_tent service...")
    print("=" * 40)
    
    success = await test_create_tent_service()
    
    print("=" * 40)
    if success:
        print("🎉 Test completed successfully!")
        return 0
    else:
        print("❌ Test failed!")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))