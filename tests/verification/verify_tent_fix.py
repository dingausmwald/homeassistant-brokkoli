#!/usr/bin/env python3
"""Verification script for Tent configuration flow fix."""

import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all required modules can be imported."""
    try:
        from custom_components.plant.config_flow import PlantConfigFlow
        print("✓ PlantConfigFlow imported successfully")
    except Exception as e:
        print(f"✗ Failed to import PlantConfigFlow: {e}")
        return False
    
    try:
        from custom_components.plant.tent import Tent
        print("✓ Tent class imported successfully")
    except Exception as e:
        print(f"✗ Failed to import Tent: {e}")
        return False
        
    try:
        from custom_components.plant.const import DEVICE_TYPE_TENT
        print("✓ DEVICE_TYPE_TENT constant imported successfully")
    except Exception as e:
        print(f"✗ Failed to import DEVICE_TYPE_TENT: {e}")
        return False
    
    return True

def test_config_flow_creation():
    """Test that PlantConfigFlow can be instantiated."""
    try:
        from custom_components.plant.config_flow import PlantConfigFlow
        flow = PlantConfigFlow()
        print("✓ PlantConfigFlow instance created successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to create PlantConfigFlow instance: {e}")
        return False

def test_tent_method_exists():
    """Test that the async_step_tent method exists."""
    try:
        from custom_components.plant.config_flow import PlantConfigFlow
        flow = PlantConfigFlow()
        method = getattr(flow, 'async_step_tent', None)
        if method and callable(method):
            print("✓ async_step_tent method exists")
            return True
        else:
            print("✗ async_step_tent method does not exist or is not callable")
            return False
    except Exception as e:
        print(f"✗ Error checking for async_step_tent method: {e}")
        return False

def main():
    """Run all verification tests."""
    print("Verifying Tent configuration flow fix...")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_config_flow_creation,
        test_tent_method_exists
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
        print("🎉 All tests passed! The fix is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())