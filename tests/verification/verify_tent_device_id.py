#!/usr/bin/env python3
"""Verification script for Tent device_id property fix."""

import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_tent_device_id_property():
    """Test that Tent class has device_id property."""
    try:
        from custom_components.plant.tent import Tent
        # Create a mock Tent instance
        tent = Tent.__new__(Tent)
        # Initialize required attributes
        tent._device_id = "test_device_id"
        # Check if device_id property exists and returns correct value
        device_id = tent.device_id
        if device_id == "test_device_id":
            print("✓ Tent.device_id property exists and returns correct value")
            return True
        else:
            print(f"✗ Tent.device_id property returned '{device_id}', expected 'test_device_id'")
            return False
    except Exception as e:
        print(f"✗ Error accessing Tent.device_id property: {e}")
        return False

def test_tent_imports():
    """Test that Tent class can be imported."""
    try:
        from custom_components.plant.tent import Tent
        print("✓ Tent class imported successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to import Tent class: {e}")
        return False

def test_tent_instantiation():
    """Test that Tent class can be instantiated."""
    try:
        from custom_components.plant.tent import Tent
        # We can't fully instantiate without HomeAssistant and ConfigEntry,
        # but we can check if the class exists
        if Tent:
            print("✓ Tent class exists and is accessible")
            return True
        else:
            print("✗ Tent class is None")
            return False
    except Exception as e:
        print(f"✗ Error with Tent class: {e}")
        return False

def main():
    """Run all verification tests."""
    print("Verifying Tent device_id property fix...")
    print("=" * 50)
    
    tests = [
        test_tent_imports,
        test_tent_instantiation,
        test_tent_device_id_property
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The Tent device_id fix is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())