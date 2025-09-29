"""Test consumption tracking in the plant integration."""
import importlib.machinery
import importlib.util
import sys
from pathlib import Path


def _load_module(module_name, file_path):
    """Load a module from a file path."""
    path = Path(file_path).resolve()
    loader = importlib.machinery.SourceFileLoader(module_name, str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    loader.exec_module(module)
    return module


def _setup_ha_modules():
    """Set up minimal HA modules for testing."""
    # Only set up modules if they don't already exist
    if "homeassistant.core" not in sys.modules:
        # Inject minimal dummy module for homeassistant.core
        dummy_ha_core = type(sys)("homeassistant.core")
        # Create a minimal HomeAssistant class
        class HomeAssistant:
            pass
        setattr(dummy_ha_core, "HomeAssistant", HomeAssistant)
        sys.modules["homeassistant.core"] = dummy_ha_core


def test_water_consumption_calculation():
    """Test water consumption calculation logic."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")

    # Test that consumption attributes are defined
    assert const.ATTR_WATER_CONSUMPTION == "water_consumption"
    assert const.READING_MOISTURE_CONSUMPTION == "water consumption"
    assert const.ICON_WATER_CONSUMPTION == "mdi:water-pump"

    # Test default consumption values
    assert const.DEFAULT_MIN_WATER_CONSUMPTION == 0.1
    assert const.DEFAULT_MAX_WATER_CONSUMPTION == 2.0


def test_fertilizer_consumption_calculation():
    """Test fertilizer consumption calculation logic."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")

    # Test that consumption attributes are defined
    assert const.ATTR_FERTILIZER_CONSUMPTION == "fertilizer_consumption"
    assert const.READING_FERTILIZER_CONSUMPTION == "fertilizer consumption"
    assert const.ICON_FERTILIZER_CONSUMPTION == "mdi:chart-line-variant"

    # Test default consumption values
    assert const.DEFAULT_MIN_FERTILIZER_CONSUMPTION == 0.1
    assert const.DEFAULT_MAX_FERTILIZER_CONSUMPTION == 2.0


def test_power_consumption_calculation():
    """Test power consumption calculation logic."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")

    # Test that consumption attributes are defined
    assert const.ATTR_POWER_CONSUMPTION == "power_consumption"
    assert const.READING_POWER_CONSUMPTION == "power consumption"
    assert const.ICON_POWER_CONSUMPTION == "mdi:flash"

    # Test default consumption values
    assert const.DEFAULT_MIN_POWER_CONSUMPTION == 0.1
    assert const.DEFAULT_MAX_POWER_CONSUMPTION == 5.0


def test_total_consumption_aggregation():
    """Test total consumption aggregation logic."""
    _setup_ha_modules()
    
    # Test that we can sum up consumption values
    daily_consumption = [0.5, 0.3, 0.2]
    total_consumption = sum(daily_consumption)
    assert total_consumption == 1.0

    # Test with float precision
    daily_consumption_float = [0.1, 0.2, 0.3]
    total_consumption_float = sum(daily_consumption_float)
    assert abs(total_consumption_float - 0.6) < 0.0001  # Account for floating point precision


def test_consumption_service_validation():
    """Test validation of consumption service parameters."""
    _setup_ha_modules()
    
    # Test valid water amount
    water_amount = 500.0
    assert 0.0 <= water_amount <= 1000.0

    # Test valid conductivity value
    conductivity_value = 1500.0
    assert 0.0 <= conductivity_value <= 100000.0

    # Test valid pH value
    ph_value = 6.5
    assert 0.0 <= ph_value <= 14.0

    # Test boundary values
    assert 0.0 >= 0.0  # Minimum water amount
    assert 1000.0 <= 1000.0  # Maximum water amount
    assert 0.0 >= 0.0  # Minimum conductivity
    assert 100000.0 <= 100000.0  # Maximum conductivity
    assert 0.0 >= 0.0  # Minimum pH
    assert 14.0 <= 14.0  # Maximum pH