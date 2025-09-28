#!/usr/bin/env python3
"""Test script to verify create_tent fix v2."""

import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_create_tent_implementation_v2():
    """Test the create_tent implementation v2."""
    try:
        # Read the services.py file
        with open("custom_components/plant/services.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Find the create_tent function specifically
        lines = content.split('\n')
        in_create_tent = False
        create_tent_lines = []
        
        for line in lines:
            if 'async def create_tent(call: ServiceCall)' in line:
                in_create_tent = True
                create_tent_lines.append(line)
            elif in_create_tent:
                if line.startswith('    async def') and 'create_tent' not in line:
                    # We've reached the next function
                    break
                create_tent_lines.append(line)
        
        create_tent_content = '\n'.join(create_tent_lines)
        
        # Check that we're handling UnknownFlow exception
        if "except UnknownFlow:" in create_tent_content:
            print("✓ Handling UnknownFlow exception")
        else:
            print("✗ Not handling UnknownFlow exception")
            return False
            
        # Check that we're still using import flow
        if "SOURCE_IMPORT" in create_tent_content:
            print("✓ Using SOURCE_IMPORT for tent creation")
        else:
            print("✗ Not using SOURCE_IMPORT for tent creation")
            return False
            
        # Check that we're not trying to access the result directly
        if "result = await hass.config_entries.flow.async_init" not in create_tent_content:
            print("✓ Not trying to directly access flow result")
        else:
            print("✗ Still trying to directly access flow result")
            return False
            
        return True
    except Exception as e:
        print(f"✗ Error checking create_tent implementation: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing create_tent fix v2...")
    print("=" * 30)
    
    tests = [
        test_create_tent_implementation_v2
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
        print("🎉 All tests passed! The create_tent fix v2 is implemented correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())