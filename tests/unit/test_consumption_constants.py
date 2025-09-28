"""Test consumption constants and configuration in the plant integration."""
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
    if "homeassistant.const" not in sys.modules:
        # Inject minimal dummy module for homeassistant.const
        dummy_ha_const = type(sys)("homeassistant.const")
        setattr(dummy_ha_const, "STATE_UNKNOWN", "unknown")
        setattr(dummy_ha_const, "STATE_UNAVAILABLE", "unavailable")
        sys.modules["homeassistant.const"] = dummy_ha_const


def test_consumption_constants():
    """Test that all consumption-related constants are defined."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test consumption attributes
    assert const.ATTR_WATER_CONSUMPTION == "water_consumption"
    assert const.ATTR_FERTILIZER_CONSUMPTION == "fertilizer_consumption"
    assert const.ATTR_POWER_CONSUMPTION == "power_consumption"
    
    # Test consumption readings
    assert const.READING_MOISTURE_CONSUMPTION == "water consumption"
    assert const.READING_FERTILIZER_CONSUMPTION == "fertilizer consumption"
    assert const.READING_POWER_CONSUMPTION == "power consumption"
    
    # Test consumption icons
    assert const.ICON_WATER_CONSUMPTION == "mdi:water-pump"
    assert const.ICON_FERTILIZER_CONSUMPTION == "mdi:chart-line-variant"
    assert const.ICON_POWER_CONSUMPTION == "mdi:flash"
    
    # Test consumption units
    assert const.UNIT_VOLUME == "L"
    assert const.UNIT_CONDUCTIVITY == "μS/cm"


def test_consumption_default_values():
    """Test that consumption default values are defined."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test water consumption defaults
    assert const.DEFAULT_MIN_WATER_CONSUMPTION == 0.1
    assert const.DEFAULT_MAX_WATER_CONSUMPTION == 2.0
    
    # Test fertilizer consumption defaults
    assert const.DEFAULT_MIN_FERTILIZER_CONSUMPTION == 0.1
    assert const.DEFAULT_MAX_FERTILIZER_CONSUMPTION == 2.0
    
    # Test power consumption defaults
    assert const.DEFAULT_MIN_POWER_CONSUMPTION == 0.1
    assert const.DEFAULT_MAX_POWER_CONSUMPTION == 5.0


def test_consumption_config_constants():
    """Test that consumption config constants are defined."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test water consumption config
    assert const.CONF_MIN_WATER_CONSUMPTION == "min_water_consumption"
    assert const.CONF_MAX_WATER_CONSUMPTION == "max_water_consumption"
    
    # Test fertilizer consumption config
    assert const.CONF_MIN_FERTILIZER_CONSUMPTION == "min_fertilizer_consumption"
    assert const.CONF_MAX_FERTILIZER_CONSUMPTION == "max_fertilizer_consumption"
    
    # Test power consumption config
    assert const.CONF_MIN_POWER_CONSUMPTION == "min_power_consumption"
    assert const.CONF_MAX_POWER_CONSUMPTION == "max_power_consumption"
    
    # Test default config values
    assert const.CONF_DEFAULT_MIN_WATER_CONSUMPTION == "default_min_water_consumption"
    assert const.CONF_DEFAULT_MAX_WATER_CONSUMPTION == "default_max_water_consumption"
    assert const.CONF_DEFAULT_MIN_FERTILIZER_CONSUMPTION == "default_min_fertilizer_consumption"
    assert const.CONF_DEFAULT_MAX_FERTILIZER_CONSUMPTION == "default_max_fertilizer_consumption"
    assert const.CONF_DEFAULT_MIN_POWER_CONSUMPTION == "default_min_power_consumption"
    assert const.CONF_DEFAULT_MAX_POWER_CONSUMPTION == "default_max_power_consumption"


def test_consumption_aggregation_methods():
    """Test that consumption sensors have appropriate aggregation methods."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test that consumption sensor types exist in default aggregations
    assert "moisture_consumption" in const.DEFAULT_AGGREGATIONS
    assert "fertilizer_consumption" in const.DEFAULT_AGGREGATIONS
    assert "power_consumption" in const.DEFAULT_AGGREGATIONS
    assert "total_water_consumption" in const.DEFAULT_AGGREGATIONS
    assert "total_fertilizer_consumption" in const.DEFAULT_AGGREGATIONS
    assert "total_power_consumption" in const.DEFAULT_AGGREGATIONS
    
    # Test that consumption sensors use appropriate aggregation methods
    assert const.DEFAULT_AGGREGATIONS["moisture_consumption"] == const.AGGREGATION_ORIGINAL
    assert const.DEFAULT_AGGREGATIONS["fertilizer_consumption"] == const.AGGREGATION_ORIGINAL
    assert const.DEFAULT_AGGREGATIONS["power_consumption"] == const.AGGREGATION_MEAN
    assert const.DEFAULT_AGGREGATIONS["total_water_consumption"] == const.AGGREGATION_ORIGINAL
    assert const.DEFAULT_AGGREGATIONS["total_fertilizer_consumption"] == const.AGGREGATION_ORIGINAL
    assert const.DEFAULT_AGGREGATIONS["total_power_consumption"] == const.AGGREGATION_ORIGINAL


def test_total_consumption_constants():
    """Test that total consumption constants are defined."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test total consumption readings
    assert "total_water_consumption" in const.DEFAULT_AGGREGATIONS
    assert "total_fertilizer_consumption" in const.DEFAULT_AGGREGATIONS
    assert "total_power_consumption" in const.DEFAULT_AGGREGATIONS


def test_aggregation_method_constants():
    """Test that aggregation method constants are defined."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test aggregation method constants
    assert const.AGGREGATION_ORIGINAL == "original"
    assert const.AGGREGATION_MEAN == "mean"
    assert const.AGGREGATION_MEDIAN == "median"
    assert const.AGGREGATION_MIN == "min"
    assert const.AGGREGATION_MAX == "max"
    
    # Test that AGGREGATION_METHODS contains the basic methods
    assert const.AGGREGATION_MEDIAN in const.AGGREGATION_METHODS
    assert const.AGGREGATION_MEAN in const.AGGREGATION_METHODS
    assert const.AGGREGATION_MIN in const.AGGREGATION_METHODS
    assert const.AGGREGATION_MAX in const.AGGREGATION_METHODS
    
    # Test that AGGREGATION_METHODS_EXTENDED includes original
    assert const.AGGREGATION_ORIGINAL in const.AGGREGATION_METHODS_EXTENDED
    for method in const.AGGREGATION_METHODS:
        assert method in const.AGGREGATION_METHODS_EXTENDED