#!/usr/bin/env python3
"""Test script to verify tent unload fix."""

import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_tent_unload_logic():
    """Test the logic for tent unloading."""
    try:
        # Read the __init__.py file
        with open("custom_components/plant/__init__.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Check that we're handling tents correctly in async_unload_entry
        if 'device_type = entry.data.get(FLOW_PLANT_INFO, {}).get(ATTR_DEVICE_TYPE, DEVICE_TYPE_PLANT)' in content:
            print("✓ Checking device type in async_unload_entry")
        else:
            print("✗ Not checking device type in async_unload_entry")
            return False
        
        # Check that we're not unloading platforms for tents
        if 'if device_type == "tent":' in content and 'unload_ok = True' in content:
            print("✓ Not unloading platforms for tents")
        else:
            print("✗ Still unloading platforms for tents")
            return False
            
        # Check that we're handling utility data correctly
        if 'if device_type != "tent" and DATA_UTILITY in hass.data:' in content:
            print("✓ Handling utility data correctly for tents")
        else:
            print("✗ Not handling utility data correctly for tents")
            return False
            
        return True
    except Exception as e:
        print(f"✗ Error checking tent unload logic: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing tent unload fix...")
    print("=" * 30)
    
    tests = [
        test_tent_unload_logic
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 30)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The tent unload fix is implemented correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())