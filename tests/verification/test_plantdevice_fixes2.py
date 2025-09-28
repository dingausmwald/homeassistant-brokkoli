#!/usr/bin/env python3
"""
Test script to verify the PlantDevice fixes for missing methods and attributes.
"""

import sys
import os

# Add the custom_components directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components'))

def test_plantdevice_methods():
    """Test that PlantDevice has all the required methods and attributes."""
    print("Testing PlantDevice methods and attributes...")
    
    try:
        # Import the PlantDevice class
        from plant import PlantDevice
        print("✓ Successfully imported PlantDevice class")
        
        # Check that the class has the required methods
        required_methods = [
            'add_water_capacity',
            'add_sensors',
            'add_pot_size',
            'add_treatment_select',
            'add_health_number',
            'add_journal',
            'add_location_history',
            'add_thresholds',      # Newly added
            'add_calculations',    # Newly added
            'add_dli',             # Newly added
            'update_kwh_price',    # Newly added/fixed
        ]
        
        for method in required_methods:
            if hasattr(PlantDevice, method):
                print(f"✓ PlantDevice has method: {method}")
            else:
                print(f"✗ PlantDevice missing method: {method}")
                return False
        
        # Check that the class has the required attributes
        # We can't easily test this without instantiating the class
        # since many attributes are initialized in __init__
        print("✓ PlantDevice has all required methods")
        return True
        
    except Exception as e:
        print(f"✗ Error testing PlantDevice: {e}")
        return False

def test_plantdevice_attributes():
    """Test that PlantDevice has all the required attributes."""
    print("\nTesting PlantDevice attributes...")
    
    try:
        # Import the PlantDevice class
        from plant import PlantDevice
        
        # Create a mock hass object
        class MockHass:
            def __init__(self):
                self.data = {}
                self.config_entries = MockConfigEntries()
        
        class MockConfigEntries:
            def async_entries(self, domain):
                return []
        
        class MockConfig:
            def __init__(self):
                self.entry_id = "test_entry"
                self.data = {
                    "plant_info": {
                        "name": "Test Plant",
                        "device_type": "plant"
                    }
                }
                self.options = {}
        
        # Create a PlantDevice instance
        hass = MockHass()
        config = MockConfig()
        plant = PlantDevice(hass, config)
        
        # Check for required attributes
        required_attributes = [
            'max_ph',
            'min_ph',
            'max_water_consumption',
            'min_water_consumption',
            'max_fertilizer_consumption',
            'min_fertilizer_consumption',
            'max_power_consumption',
            'min_power_consumption',
        ]
        
        for attr in required_attributes:
            if hasattr(plant, attr):
                print(f"✓ PlantDevice has attribute: {attr}")
            else:
                print(f"✗ PlantDevice missing attribute: {attr}")
                return False
        
        print("✓ PlantDevice has all required attributes")
        return True
        
    except Exception as e:
        print(f"✗ Error testing PlantDevice attributes: {e}")
        return False

def test_method_functionality():
    """Test that the newly added methods work correctly."""
    print("\nTesting method functionality...")
    
    try:
        # Import the PlantDevice class
        from plant import PlantDevice
        
        # Create a mock hass object
        class MockHass:
            def __init__(self):
                self.data = {}
                self.config_entries = MockConfigEntries()
        
        class MockConfigEntries:
            def async_entries(self, domain):
                return []
        
        class MockConfig:
            def __init__(self):
                self.entry_id = "test_entry"
                self.data = {
                    "plant_info": {
                        "name": "Test Plant",
                        "device_type": "plant"
                    }
                }
                self.options = {}
        
        class MockEntity:
            def __init__(self, name="Mock Entity"):
                self.name = name
                self.state = "test_state"
        
        # Create a PlantDevice instance
        hass = MockHass()
        config = MockConfig()
        plant = PlantDevice(hass, config)
        
        # Test add_thresholds method
        mock_entity = MockEntity()
        plant.add_thresholds(
            max_ph=mock_entity,
            min_ph=mock_entity,
            max_water_consumption=mock_entity,
            min_water_consumption=mock_entity
        )
        
        if plant.max_ph == mock_entity and plant.min_ph == mock_entity:
            print("✓ add_thresholds method works correctly")
        else:
            print("✗ add_thresholds method failed")
            return False
        
        # Test add_calculations method
        plant.add_calculations(
            ppfd=mock_entity,
            total_integral=mock_entity,
            moisture_consumption=mock_entity,
            fertilizer_consumption=mock_entity
        )
        
        if (plant.ppfd == mock_entity and 
            plant.total_integral == mock_entity and 
            plant.moisture_consumption == mock_entity and 
            plant.fertilizer_consumption == mock_entity):
            print("✓ add_calculations method works correctly")
        else:
            print("✗ add_calculations method failed")
            return False
        
        # Test update_kwh_price method
        plant.update_kwh_price(0.35)
        if plant._kwh_price == 0.35:
            print("✓ update_kwh_price method works correctly")
        else:
            print("✗ update_kwh_price method failed")
            return False
        
        # Test add_dli method
        plant.add_dli(dli=mock_entity)
        if plant.dli == mock_entity:
            print("✓ add_dli method works correctly")
        else:
            print("✗ add_dli method failed")
            return False
        
        print("✓ All method functionality tests passed")
        return True
        
    except Exception as e:
        print(f"✗ Error testing method functionality: {e}")
        return False

if __name__ == "__main__":
    print("Running PlantDevice fixes verification...\n")
    
    # Test methods
    if not test_plantdevice_methods():
        sys.exit(1)
    
    # Test attributes
    if not test_plantdevice_attributes():
        sys.exit(1)
    
    # Test functionality
    if not test_method_functionality():
        sys.exit(1)
    
    print("\n✓ All tests passed! PlantDevice fixes are working correctly.")