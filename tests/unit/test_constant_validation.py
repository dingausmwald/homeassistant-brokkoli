"""Test validation of constants in the plant integration."""
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
        setattr(dummy_ha_const, "ATTR_ICON", "icon")
        setattr(dummy_ha_const, "STATE_UNKNOWN", "unknown")
        setattr(dummy_ha_const, "STATE_UNAVAILABLE", "unavailable")
        setattr(dummy_ha_const, "ATTR_NAME", "name")
        setattr(dummy_ha_const, "ATTR_ENTITY_PICTURE", "entity_picture")
        sys.modules["homeassistant.const"] = dummy_ha_const


def test_constants_defined():
    """Test that all required constants are defined."""
    _setup_ha_modules()
    
    # Load the const module
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test that basic constants are defined
    assert const.DOMAIN == "plant"
    assert const.DOMAIN_SENSOR == "sensor"
    
    # Test sensor attributes
    assert const.ATTR_TEMPERATURE == "temperature"
    assert const.ATTR_MOISTURE == "moisture"
    assert const.ATTR_CONDUCTIVITY == "conductivity"
    assert const.ATTR_ILLUMINANCE == "illuminance"
    assert const.ATTR_HUMIDITY == "humidity"
    assert const.ATTR_CO2 == "co2"
    assert const.ATTR_PPFD == "ppfd"
    assert const.ATTR_DLI == "dli"
    assert const.ATTR_PH == "ph"
    
    # Test reading constants
    assert const.READING_TEMPERATURE == "temperature"
    assert const.READING_MOISTURE == "soil moisture"
    assert const.READING_CONDUCTIVITY == "conductivity"
    assert const.READING_ILLUMINANCE == "illuminance"
    assert const.READING_HUMIDITY == "air humidity"
    assert const.READING_CO2 == "air CO2"
    assert const.READING_PPFD == "ppfd (mol)"
    assert const.READING_DLI == "dli"
    assert const.READING_PH == "soil pH"
    
    # Test units
    assert const.UNIT_PPFD == "mol/s⋅m²s"
    assert const.UNIT_DLI == "mol/d⋅m²"
    assert const.UNIT_CONDUCTIVITY == "μS/cm"
    assert const.UNIT_VOLUME == "L"
    
    # Test icons
    assert const.ICON_CONDUCTIVITY == "mdi:spa-outline"
    assert const.ICON_DLI == "mdi:counter"
    assert const.ICON_HUMIDITY == "mdi:water-percent"
    assert const.ICON_CO2 == "mdi:molecule-co2"
    assert const.ICON_ILLUMINANCE == "mdi:brightness-6"
    assert const.ICON_MOISTURE == "mdi:water"
    assert const.ICON_PPFD == "mdi:white-balance-sunny"
    assert const.ICON_TEMPERATURE == "mdi:thermometer"
    assert const.ICON_PH == "mdi:ph"
    
    # Test device types
    assert const.DEVICE_TYPE_PLANT == "plant"
    assert const.DEVICE_TYPE_CYCLE == "cycle"
    assert const.DEVICE_TYPE_CONFIG == "config"
    
    # Test aggregation methods
    assert const.AGGREGATION_MEDIAN == "median"
    assert const.AGGREGATION_MEAN == "mean"
    assert const.AGGREGATION_MIN == "min"
    assert const.AGGREGATION_MAX == "max"
    assert const.AGGREGATION_ORIGINAL == "original"
    
    # Test that AGGREGATION_METHODS contains required values
    assert "median" in const.AGGREGATION_METHODS
    assert "mean" in const.AGGREGATION_METHODS
    assert "min" in const.AGGREGATION_METHODS
    assert "max" in const.AGGREGATION_METHODS
    
    # Test that AGGREGATION_METHODS_EXTENDED contains all AGGREGATION_METHODS plus 'original'
    for method in const.AGGREGATION_METHODS:
        assert method in const.AGGREGATION_METHODS_EXTENDED
    assert "original" in const.AGGREGATION_METHODS_EXTENDED


def test_service_constants():
    """Test that service constants are defined."""
    _setup_ha_modules()
    
    # Load the const module
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test service constants
    assert const.SERVICE_REPLACE_SENSOR == "replace_sensor"
    assert const.SERVICE_REMOVE_PLANT == "remove_plant"
    assert const.SERVICE_CREATE_PLANT == "create_plant"
    assert const.SERVICE_CREATE_CYCLE == "create_cycle"
    assert const.SERVICE_EXPORT_PLANTS == "export_plants"
    assert const.SERVICE_IMPORT_PLANTS == "import_plants"
    assert const.SERVICE_CLONE_PLANT == "clone_plant"


def test_consumption_constants():
    """Test that consumption-related constants are defined."""
    _setup_ha_modules()
    
    # Load the const module
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


def test_config_flow_constants():
    """Test that config flow constants are defined."""
    _setup_ha_modules()
    
    # Load the const module
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test config flow sensor constants
    assert const.FLOW_SENSOR_TEMPERATURE == "temperature_sensor"
    assert const.FLOW_SENSOR_MOISTURE == "moisture_sensor"
    assert const.FLOW_SENSOR_CONDUCTIVITY == "conductivity_sensor"
    assert const.FLOW_SENSOR_ILLUMINANCE == "illuminance_sensor"
    assert const.FLOW_SENSOR_HUMIDITY == "humidity_sensor"
    assert const.FLOW_SENSOR_CO2 == "co2_sensor"
    assert const.FLOW_SENSOR_POWER_CONSUMPTION == "power_consumption_sensor"
    assert const.FLOW_SENSOR_PH == "ph_sensor"