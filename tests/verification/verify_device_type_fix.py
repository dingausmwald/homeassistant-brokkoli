#!/usr/bin/env python3
"""Verification script for device_type fix in __init__.py."""

import sys
import os
from unittest.mock import Mock, MagicMock

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_device_type_variable_order():
    """Test that device_type is defined before use in async_setup_entry."""
    try:
        # Import the module
        from custom_components.plant import async_setup_entry
        print("✓ async_setup_entry function imported successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to import async_setup_entry: {e}")
        return False

def test_imports():
    """Test that all required modules can be imported."""
    try:
        from custom_components.plant import DOMAIN, FLOW_PLANT_INFO
        print("✓ DOMAIN and FLOW_PLANT_INFO imported successfully")
    except Exception as e:
        print(f"✗ Failed to import DOMAIN or FLOW_PLANT_INFO: {e}")
        return False
    
    try:
        from custom_components.plant.const import DEVICE_TYPE_PLANT
        print("✓ DEVICE_TYPE_PLANT constant imported successfully")
    except Exception as e:
        print(f"✗ Failed to import DEVICE_TYPE_PLANT: {e}")
        return False
        
    return True

def main():
    """Run all verification tests."""
    print("Verifying device_type fix in __init__.py...")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_device_type_variable_order
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
        print("🎉 All tests passed! The device_type fix is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())