#!/usr/bin/env python3
"""Validation script for services.yaml file."""

import sys
import os
import yaml

def validate_services_yaml():
    """Validate the services.yaml file."""
    try:
        # Path to the services.yaml file
        yaml_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "custom_components",
            "plant",
            "services.yaml"
        )
        
        # Load and parse the YAML file
        with open(yaml_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
        
        # Check if create_tent service exists
        if 'create_tent' not in data:
            print("✗ create_tent service not found in services.yaml")
            return False
            
        create_tent = data['create_tent']
        
        # Check if fields exist
        if 'fields' not in create_tent:
            print("✗ fields section not found in create_tent service")
            return False
            
        fields = create_tent['fields']
        
        # Check required fields
        required_fields = [
            'name',
            'illuminance_sensor',
            'humidity_sensor',
            'co2_sensor',
            'power_consumption_sensor',
            'ph_sensor'
        ]
        
        for field in required_fields:
            if field not in fields:
                print(f"✗ Required field '{field}' not found in create_tent service")
                return False
                
            field_data = fields[field]
            
            # Check if each field has the required properties
            if 'name' not in field_data:
                print(f"✗ 'name' property missing in field '{field}'")
                return False
                
            if 'selector' not in field_data:
                print(f"✗ 'selector' property missing in field '{field}'")
                return False
                
            # Check selector structure (different for text vs entity selectors)
            selector = field_data['selector']
            if field == 'name':
                # Name field uses text selector
                if 'text' not in selector:
                    print(f"✗ 'text' property missing in selector for field '{field}'")
                    return False
            else:
                # Sensor fields use entity selector
                if 'entity' not in selector:
                    print(f"✗ 'entity' property missing in selector for field '{field}'")
                    return False
                
        print("✓ services.yaml validation passed")
        print(f"✓ Found {len(fields)} fields in create_tent service")
        return True
        
    except yaml.YAMLError as e:
        print(f"✗ YAML parsing error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error validating services.yaml: {e}")
        return False

def main():
    """Run the validation."""
    print("Validating services.yaml file...")
    print("=" * 40)
    
    if validate_services_yaml():
        print("=" * 40)
        print("🎉 services.yaml validation successful!")
        return 0
    else:
        print("=" * 40)
        print("❌ services.yaml validation failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())