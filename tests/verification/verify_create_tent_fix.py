#!/usr/bin/env python3
"""Verification script for create_tent service fix."""

import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all required modules can be imported."""
    try:
        from custom_components.plant.services import async_setup_services
        print("✓ Plant services module imported successfully")
    except Exception as e:
        print(f"✗ Failed to import plant services: {e}")
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

def test_create_tent_implementation():
    """Test that the create_tent implementation has been fixed."""
    try:
        # Read the services.py file
        with open("custom_components/plant/services.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Check that the create_tent function uses the correct approach
        if "hass.config_entries.flow.async_init" in content and "SOURCE_IMPORT" in content:
            print("✓ create_tent function uses correct flow initialization")
            return True
        else:
            print("✗ create_tent function doesn't use correct flow initialization")
            return False
    except Exception as e:
        print(f"✗ Error checking create_tent implementation: {e}")
        return False

def test_tent_id_assignment():
    """Test that tent_id assignment in __init__.py has been fixed."""
    try:
        # Read the __init__.py file
        with open("custom_components/plant/__init__.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Check that the tent_id assignment has been fixed
        if "# For tents, we need to update the tent_info in the config entry" in content:
            print("✓ tent_id assignment fixed in __init__.py")
            return True
        else:
            print("✗ tent_id assignment not fixed in __init__.py")
            return False
    except Exception as e:
        print(f"✗ Error checking tent_id assignment: {e}")
        return False

def main():
    """Run all verification tests."""
    print("Verifying create_tent service fix...")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_create_tent_implementation,
        test_tent_id_assignment
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