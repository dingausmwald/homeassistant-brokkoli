#!/usr/bin/env python3
"""Verification script for change_tent GUI support."""

import sys
import os
import yaml

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_services_yaml():
    """Test that change_tent service is properly defined in services.yaml."""
    try:
        # Load the services.yaml file
        with open("custom_components/plant/services.yaml", "r", encoding="utf-8") as f:
            services = yaml.safe_load(f)
        
        # Check if change_tent service exists
        if "change_tent" in services:
            change_tent_service = services["change_tent"]
            print("✓ change_tent service found in services.yaml")
            
            # Check required fields
            required_fields = ["name", "description", "fields"]
            for field in required_fields:
                if field in change_tent_service:
                    print(f"✓ {field} field found")
                else:
                    print(f"✗ {field} field missing")
                    return False
            
            # Check fields
            fields = change_tent_service.get("fields", {})
            required_field_names = ["entity_id", "tent_id"]
            for field_name in required_field_names:
                if field_name in fields:
                    print(f"✓ {field_name} field found")
                    field_def = fields[field_name]
                    
                    # Check field properties
                    field_props = ["name", "description", "example", "required"]
                    for prop in field_props:
                        if prop in field_def:
                            print(f"  ✓ {prop} property found")
                        else:
                            print(f"  ✗ {prop} property missing")
                else:
                    print(f"✗ {field_name} field missing")
                    return False
            
            return True
        else:
            print("✗ change_tent service not found in services.yaml")
            return False
    except Exception as e:
        print(f"✗ Error reading services.yaml: {e}")
        return False

def test_service_constants():
    """Test that service constants are defined."""
    try:
        from custom_components.plant.const import SERVICE_CHANGE_TENT
        print("✓ SERVICE_CHANGE_TENT constant found")
        if SERVICE_CHANGE_TENT == "change_tent":
            print("✓ SERVICE_CHANGE_TENT has correct value")
            return True
        else:
            print(f"✗ SERVICE_CHANGE_TENT has incorrect value: {SERVICE_CHANGE_TENT}")
            return False
    except Exception as e:
        print(f"✗ Error accessing SERVICE_CHANGE_TENT constant: {e}")
        return False

if __name__ == "__main__":
    print("Verifying change_tent GUI support...")
    print("=" * 50)
    
    tests = [
        test_services_yaml,
        test_service_constants
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
        print("🎉 All tests passed! The change_tent GUI support should work correctly.")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Please check the implementation.")
        sys.exit(1)