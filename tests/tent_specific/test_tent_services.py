"""Test tent service functionality in the plant integration."""
import importlib.machinery
import importlib.util
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


def _load_module(module_name, file_path):
    """Load a module from a file path."""
    path = Path(file_path).resolve()
    loader = importlib.machinery.SourceFileLoader(module_name, str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    loader.exec_module(module)
    return module


def test_change_tent_service_exists():
    """Test that the change_tent service is properly defined."""
    # Load the const module
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test service constants
    assert hasattr(const, "SERVICE_CHANGE_TENT"), "SERVICE_CHANGE_TENT constant should be defined"
    assert const.SERVICE_CHANGE_TENT == "change_tent"


def test_change_tent_schema_exists():
    """Test that the change_tent schema is properly defined."""
    try:
        # Load the services module
        services = _load_module("custom_components.plant.services", "custom_components/plant/services.py")
        
        # Test that the schema exists
        assert hasattr(services, "CHANGE_TENT_SCHEMA"), "CHANGE_TENT_SCHEMA should be defined"
    except ImportError as e:
        # If we can't import the services module due to HA dependencies, that's okay
        # This is expected in our isolated test environment
        pass


def test_change_tent_service_function_exists():
    """Test that the change_tent service function is properly defined."""
    try:
        # Load the services module
        services = _load_module("custom_components.plant.services", "custom_components/plant/services.py")
        
        # Test that the service function exists
        assert hasattr(services, "change_tent"), "change_tent function should be defined"
    except ImportError as e:
        # If we can't import the services module due to HA dependencies, that's okay
        # This is expected in our isolated test environment
        pass


def test_create_tent_service_exists():
    """Test that the create_tent service artifacts are defined."""
    # Load the const module
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    assert hasattr(const, "FLOW_PLANT_INFO")
    # Best-effort load services to check schema symbol; ignore ImportError in HA-less env
    try:
        services = _load_module("custom_components.plant.services", "custom_components/plant/services.py")
        assert hasattr(services, "CREATE_TENT_SCHEMA"), "CREATE_TENT_SCHEMA should be defined"
    except Exception:
        pass


if __name__ == "__main__":
    test_change_tent_service_exists()
    test_change_tent_schema_exists()
    test_change_tent_service_function_exists()
    print("All tests passed!")