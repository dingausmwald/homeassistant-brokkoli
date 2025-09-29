"""Simple test runner to verify that our tests can be executed."""
import sys
import os

# Add the current directory to the path so we can import the test modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

def run_test_module(module_name):
    """Run a test module and report results."""
    try:
        # Import the module
        module = __import__(module_name)
        
        # Get all functions that start with 'test_'
        test_functions = [getattr(module, name) for name in dir(module) if name.startswith('test_')]
        
        # Run each test function
        passed = 0
        failed = 0
        
        for test_func in test_functions:
            try:
                test_func()
                print(f"✓ {test_func.__name__}")
                passed += 1
            except Exception as e:
                print(f"✗ {test_func.__name__}: {e}")
                failed += 1
        
        print(f"\n{module_name}: {passed} passed, {failed} failed")
        return failed == 0
    except Exception as e:
        print(f"Error importing {module_name}: {e}")
        return False

if __name__ == "__main__":
    # List of test modules to run
    test_modules = [
        "test_constant_validation",
        "test_sensor_value_processing",
        "test_consumption_tracking",
        "test_service_functionality",
        "test_plant_entity",
        "test_integration_scenarios",
        "test_data_persistence"
    ]
    
    all_passed = True
    
    for module_name in test_modules:
        print(f"\nRunning tests in {module_name}...")
        if not run_test_module(module_name):
            all_passed = False
    
    if all_passed:
        print("\nAll tests passed!")
        sys.exit(0)
    else:
        print("\nSome tests failed!")
        sys.exit(1)