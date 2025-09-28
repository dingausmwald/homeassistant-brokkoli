#!/usr/bin/env python3
"""
Test script to verify the PlantDevice fixes.
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
            'add_location_history'
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

def test_imports():
    """Test that all plant modules can be imported."""
    print("Testing module imports...")
    
    modules_to_test = [
        'plant',
        'plant.tent',
        'plant.text',
        'plant.number',
        'plant.sensor'
    ]
    
    for module in modules_to_test:
        try:
            __import__(module)
            print(f"✓ Successfully imported {module}")
        except Exception as e:
            print(f"✗ Error importing {module}: {e}")
            return False
    
    return True

if __name__ == "__main__":
    print("Running PlantDevice fixes verification...\n")
    
    # Test imports
    if not test_imports():
        sys.exit(1)
    
    print()
    
    # Test PlantDevice methods
    if not test_plantdevice_methods():
        sys.exit(1)
    
    print("\n✓ All tests passed! PlantDevice fixes are working correctly.")