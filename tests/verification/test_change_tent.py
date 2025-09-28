#!/usr/bin/env python3
"""
Test script to verify the change_tent functionality.
"""

import logging
from unittest.mock import Mock, MagicMock

# Set up logging
logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

def test_change_tent_functionality():
    """Test the change_tent functionality."""
    
    print("Testing change_tent functionality...")
    
    # Create mock hass object
    hass = Mock()
    hass.data = {}
    hass.config_entries = Mock()
    
    # Create mock plant device
    plant = Mock()
    plant.device_type = "plant"
    plant.entity_id = "plant.test_plant"
    plant.name = "Test Plant"
    plant.change_tent = Mock()
    
    # Create mock tent
    tent = Mock()
    tent.tent_id = "0001"
    tent.name = "Test Tent"
    tent.get_sensors = Mock(return_value=["sensor.temperature", "sensor.humidity"])
    
    # Test the change_tent functionality
    print("Calling plant.change_tent(tent)...")
    plant.change_tent(tent)
    
    # Verify that change_tent was called with the correct tent
    plant.change_tent.assert_called_once_with(tent)
    
    # Verify that get_sensors was called
    tent.get_sensors.assert_called_once()
    
    print("change_tent functionality test passed!")

if __name__ == "__main__":
    test_change_tent_functionality()