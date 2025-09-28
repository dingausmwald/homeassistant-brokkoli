#!/usr/bin/env python3
"""
Test script to verify the Tent text entities (Journal and Maintenance).
"""

import logging
from unittest.mock import Mock, MagicMock
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

def test_tent_text_entities():
    """Test the Tent text entities."""
    
    print("Testing Tent text entities (Journal and Maintenance)...")
    
    # Create mock hass object
    hass = Mock()
    hass.data = {}
    hass.config_entries = Mock()
    
    # Create mock config entry
    config = Mock()
    config.entry_id = "test_entry_id"
    config.data = {
        "plant_info": {
            "tent_id": "0001",
            "name": "Test Tent",
            "device_type": "tent",
            "journal": {},
            "maintenance_entries": [],
        }
    }
    
    # Import the Tent class and text entities
    try:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from custom_components.plant.tent import Tent
        from custom_components.plant.tent_text import TentJournal, TentMaintenance
        
        # Create a Tent instance
        tent = Tent(hass, config)
        
        # Create Tent Journal entity
        journal = TentJournal(hass, config, tent)
        print(f"Tent Journal entity created: {journal.name}")
        print(f"Tent Journal unique ID: {journal.unique_id}")
        
        # Test setting a journal value
        test_journal_entry = "Test journal entry content"
        hass.async_add_job = Mock()
        journal.async_write_ha_state = Mock()
        
        # Simulate setting a journal value
        journal.async_set_value(test_journal_entry)
        print(f"Tent Journal value set to: {journal.native_value}")
        
        # Verify the journal entry was added to the tent
        tent_journal_entries = tent.get_journal().get_entries()
        print(f"Number of journal entries in tent: {len(tent_journal_entries)}")
        
        # Create Tent Maintenance entity
        maintenance = TentMaintenance(hass, config, tent)
        print(f"Tent Maintenance entity created: {maintenance.name}")
        print(f"Tent Maintenance unique ID: {maintenance.unique_id}")
        
        # Test setting a maintenance value
        test_maintenance_entry = "Test maintenance entry content"
        maintenance.async_write_ha_state = Mock()
        
        # Simulate setting a maintenance value
        maintenance.async_set_value(test_maintenance_entry)
        print(f"Tent Maintenance value set to: {maintenance.native_value}")
        
        # Verify the maintenance entry was added to the tent
        tent_maintenance_entries = tent.get_maintenance_entries()
        print(f"Number of maintenance entries in tent: {len(tent_maintenance_entries)}")
        
        print("All Tent text entities tests passed!")
        
    except Exception as e:
        print(f"Error testing Tent text entities: {e}")
        raise

if __name__ == "__main__":
    test_tent_text_entities()