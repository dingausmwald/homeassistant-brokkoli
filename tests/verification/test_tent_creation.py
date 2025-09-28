#!/usr/bin/env python3
"""Test script to verify tent creation fix."""

import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_tent_creation_logic():
    """Test the logic for tent creation."""
    try:
        # Read the services.py file
        with open("custom_components/plant/services.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Find the create_tent function specifically
        # Look for the function definition and extract its content
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
        
        # Check that we're using the import flow correctly
        if "hass.config_entries.flow.async_init" in create_tent_content and "SOURCE_IMPORT" in create_tent_content:
            print("✓ Using import flow for tent creation")
        else:
            print("✗ Not using import flow for tent creation")
            return False
        
        # Check that we're not trying to access the flow result directly
        # (We should not have "result = await" pattern in the create_tent function)
        if "result = await hass.config_entries.flow.async_init" not in create_tent_content:
            print("✓ Not trying to directly access flow result (correct approach)")
        else:
            print("✗ Still trying to directly access flow result")
            return False
        
        # Check that we find the entry after creation by searching entries
        if "hass.config_entries.async_entries(DOMAIN)" in create_tent_content:
            print("✓ Looking for created entry in config entries")
        else:
            print("✗ Not looking for created entry")
            return False
            
        return True
    except Exception as e:
        print(f"✗ Error checking tent creation logic: {e}")
        return False

def test_import_constants():
    """Test that required constants are properly imported."""
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
        
        # Check for required imports
        required_imports = [
            "from homeassistant.config_entries import SOURCE_IMPORT",
            "from .__init__ import _get_next_id"
        ]
        
        for imp in required_imports:
            if imp in create_tent_content:
                print(f"✓ Found required import: {imp}")
            else:
                print(f"✗ Missing required import: {imp}")
                return False
                
        return True
    except Exception as e:
        print(f"✗ Error checking imports: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing tent creation fix...")
    print("=" * 40)
    
    tests = [
        test_tent_creation_logic,
        test_import_constants
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 40)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The tent creation fix is implemented correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())