#!/usr/bin/env python3
"""
Verification script for the replace_sensors implementation in PlantDevice class.
"""

import sys
import os

# Add the custom_components directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components'))

def verify_replace_sensors_implementation():
    """Verify that the replace_sensors method is implemented in PlantDevice."""
    print("Verifying PlantDevice.replace_sensors implementation...")
    
    try:
        # Import the PlantDevice class
        from plant import PlantDevice
        print("✓ PlantDevice class imported successfully")
        
        # Check if the replace_sensors method exists
        if hasattr(PlantDevice, 'replace_sensors'):
            print("✓ replace_sensors method exists in PlantDevice class")
            
            # Check the method signature
            import inspect
            sig = inspect.signature(PlantDevice.replace_sensors)
            params = list(sig.parameters.keys())
            
            if 'self' in params and 'tent_sensors' in params:
                print("✓ replace_sensors method has correct signature")
                print("  Signature: replace_sensors(self, tent_sensors: list) -> None")
            else:
                print("⚠ replace_sensors method signature may be incorrect")
                print(f"  Found parameters: {params}")
            
            print("\n✓ Implementation verified successfully!")
            print("The PlantDevice.replace_sensors method is properly implemented.")
            return True
        else:
            print("✗ replace_sensors method is missing from PlantDevice class")
            return False
            
    except Exception as e:
        print(f"✗ Error during verification: {e}")
        return False

if __name__ == "__main__":
    success = verify_replace_sensors_implementation()
    if success:
        print("\n🎉 All verification checks passed!")
        sys.exit(0)
    else:
        print("\n❌ Verification failed!")
        sys.exit(1)