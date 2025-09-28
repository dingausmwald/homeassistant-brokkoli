#!/usr/bin/env python3
"""
Test script to verify the Tent entity improvements.
"""

import logging
from unittest.mock import Mock, MagicMock
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

def test_tent_improvements():
    """Test the Tent entity improvements."""
    
    print("Testing Tent entity improvements...")
    
    # Create mock hass object
    hass = Mock()
    hass.data = {}
    hass.config_entries = Mock()
    
    # Mock the states.get method to return sensor information
    def mock_get_state(entity_id):
        mock_state = Mock()
        if "temperature" in entity_id:
            mock_state.state = "22.5"
            mock_state.attributes = {"unit_of_measurement": "°C", "device_class": "temperature"}
        elif "humidity" in entity_id:
            mock_state.state = "65"
            mock_state.attributes = {"unit_of_measurement": "%", "device_class": "humidity"}
        elif "ph" in entity_id:
            mock_state.state = "6.5"
            mock_state.attributes = {"unit_of_measurement": "pH", "device_class": "ph"}
        else:
            mock_state.state = "unknown"
            mock_state.attributes = {}
        return mock_state
    
    hass.states.get = Mock(side_effect=mock_get_state)
    
    # Create mock config entry
    config = Mock()
    config.data = {
        "plant_info": {
            "tent_id": "0001",
            "name": "Test Tent",
            "sensors": ["sensor.tent_temperature", "sensor.tent_humidity", "sensor.tent_ph"],
            "journal": {
                "entries": [
                    {
                        "timestamp": datetime.now().isoformat(),
                        "content": "Test journal entry",
                        "author": "Test User"
                    }
                ]
            },
            "maintenance_entries": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "description": "Test maintenance",
                    "performed_by": "Test Technician",
                    "cost": 25.0
                }
            ],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "device_id": "test_device_id"
        }
    }
    
    # Import the Tent class
    try:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from custom_components.plant.tent import Tent, JournalEntry, MaintenanceEntry
        
        # Create a Tent instance
        tent = Tent(hass, config)
        
        # Test state property
        state = tent.state
        print(f"Tent state: {state}")
        assert state == "ok", f"Expected state 'ok', got '{state}'"
        
        # Test extra_state_attributes property
        attributes = tent.extra_state_attributes
        print(f"Tent attributes: {attributes}")
        
        # Verify that the attributes contain the expected keys
        expected_keys = [
            "tent_id", "sensors", "sensor_details", "maintenance_entries", 
            "journal_entries", "created_at", "updated_at", "sensor_count", 
            "maintenance_count", "journal_entry_count"
        ]
        
        for key in expected_keys:
            assert key in attributes, f"Missing key '{key}' in attributes"
            
        # Verify sensor details
        assert len(attributes["sensor_details"]) == 3, "Expected 3 sensor details"
        assert attributes["sensor_count"] == 3, "Expected sensor_count to be 3"
        
        # Verify maintenance entries
        assert len(attributes["maintenance_entries"]) == 1, "Expected 1 maintenance entry"
        assert attributes["maintenance_count"] == 1, "Expected maintenance_count to be 1"
        
        # Verify journal entries
        assert len(attributes["journal_entries"]) == 1, "Expected 1 journal entry"
        assert attributes["journal_entry_count"] == 1, "Expected journal_entry_count to be 1"
        
        # Test adding a journal entry
        journal_entry = JournalEntry("Added test entry", "Tester")
        tent.add_journal_entry(journal_entry)
        
        # Verify the journal entry was added
        updated_attributes = tent.extra_state_attributes
        assert updated_attributes["journal_entry_count"] == 2, "Expected journal_entry_count to be 2 after adding entry"
        
        # Test adding a maintenance entry
        maintenance_entry = MaintenanceEntry("Added maintenance", "Tester", 50.0)
        tent.add_maintenance_entry(maintenance_entry)
        
        # Verify the maintenance entry was added
        updated_attributes = tent.extra_state_attributes
        assert updated_attributes["maintenance_count"] == 2, "Expected maintenance_count to be 2 after adding entry"
        
        print("All Tent entity improvements tests passed!")
        
    except Exception as e:
        print(f"Error testing Tent entity improvements: {e}")
        raise

if __name__ == "__main__":
    test_tent_improvements()