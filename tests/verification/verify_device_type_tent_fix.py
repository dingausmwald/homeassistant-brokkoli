#!/usr/bin/env python3
"""Verification script for DEVICE_TYPE_TENT import fix in config_flow.py."""

import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_device_type_tent_import():
    """Test that DEVICE_TYPE_TENT is properly imported in config_flow.py."""
    try:
        # Import the module and check if DEVICE_TYPE_TENT is available
        from custom_components.plant.config_flow import DEVICE_TYPE_TENT
        print("✓ DEVICE_TYPE_TENT imported successfully from config_flow")
        return True
    except Exception as e:
        print(f"✗ Failed to import DEVICE_TYPE_TENT from config_flow: {e}")
        return False

def test_config_flow_device_types():
    """Test that all device types are accessible in config_flow."""
    try:
        from custom_components.plant.config_flow import DEVICE_TYPE_PLANT, DEVICE_TYPE_CYCLE, DEVICE_TYPE_TENT
        print("✓ All device types imported successfully from config_flow")
        
        # Check that they have the expected values
        assert DEVICE_TYPE_PLANT == "plant"
        assert DEVICE_TYPE_CYCLE == "cycle"
        assert DEVICE_TYPE_TENT == "tent"
        print("✓ All device types have correct values")
        return True
    except Exception as e:
        print(f"✗ Error with device types in config_flow: {e}")
        return False

def test_async_step_tent_exists():
    """Test that async_step_tent method exists."""
    try:
        from custom_components.plant.config_flow import PlantConfigFlow
        flow = PlantConfigFlow()
        method = getattr(flow, 'async_step_tent', None)
        if method and callable(method):
            print("✓ async_step_tent method exists and is callable")
            return True
        else:
            print("✗ async_step_tent method does not exist or is not callable")
            return False
    except Exception as e:
        print(f"✗ Error checking for async_step_tent method: {e}")
        return False

def main():
    """Run all verification tests."""
    print("Verifying DEVICE_TYPE_TENT import fix in config_flow.py...")
    print("=" * 60)
    
    tests = [
        test_device_type_tent_import,
        test_config_flow_device_types,
        test_async_step_tent_exists
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The DEVICE_TYPE_TENT import fix is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())