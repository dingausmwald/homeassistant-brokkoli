"""Test integration scenarios in the plant integration."""
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
            async def async_start(self):
                pass
        setattr(dummy_ha_core, "HomeAssistant", HomeAssistant)
        sys.modules["homeassistant.core"] = dummy_ha_core
    
    if "homeassistant.const" not in sys.modules:
        # Inject minimal dummy module for homeassistant.const
        dummy_ha_const = type(sys)("homeassistant.const")
        setattr(dummy_ha_const, "STATE_UNKNOWN", "unknown")
        setattr(dummy_ha_const, "STATE_UNAVAILABLE", "unavailable")
        sys.modules["homeassistant.const"] = dummy_ha_const


def test_module_imports():
    """Test that all modules can be imported without errors."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    assert const.DOMAIN == "plant"
    
    # Test importing sensor_configuration module
    sensor_config = _load_module("custom_components.plant.sensor_configuration", "custom_components/plant/sensor_configuration.py")
    assert hasattr(sensor_config, "DEFAULT_DECIMALS")


def test_config_flow_integration():
    """Test config flow integration with constants."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test that flow constants are defined
    assert const.FLOW_PLANT_INFO == "plant_info"
    assert const.FLOW_PLANT_SPECIES == "plant_species"
    assert const.FLOW_PLANT_NAME == "plant_name"


def test_sensor_integration():
    """Test sensor integration with constants and configuration."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    sensor_config = _load_module("custom_components.plant.sensor_configuration", "custom_components/plant/sensor_configuration.py")
    
    # Test that sensor configuration uses correct constants
    assert hasattr(sensor_config, "DEFAULT_DECIMALS")
    assert "temperature" in sensor_config.DEFAULT_DECIMALS
    assert "moisture" in sensor_config.DEFAULT_DECIMALS
    assert "conductivity" in sensor_config.DEFAULT_DECIMALS
    
    # Test sensor readings constants
    assert const.READING_TEMPERATURE == "temperature"
    assert const.READING_MOISTURE == "soil moisture"
    assert const.READING_CONDUCTIVITY == "conductivity"


def test_service_integration():
    """Test service integration with constants."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test that services use correct constants
    assert const.SERVICE_CREATE_PLANT == "create_plant"
    assert const.SERVICE_REPLACE_SENSOR == "replace_sensor"
    assert const.SERVICE_EXPORT_PLANTS == "export_plants"
    assert const.SERVICE_IMPORT_PLANTS == "import_plants"


def test_data_persistence_integration():
    """Test data persistence integration."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test that persistence-related constants are defined
    assert const.ATTR_IS_NEW_PLANT == "is_new_plant"
    assert const.SERVICE_EXPORT_PLANTS == "export_plants"
    assert const.SERVICE_IMPORT_PLANTS == "import_plants"


def test_consumption_integration():
    """Test consumption tracking integration."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test that consumption-related integrations work
    assert const.ATTR_WATER_CONSUMPTION == "water_consumption"
    assert const.ATTR_FERTILIZER_CONSUMPTION == "fertilizer_consumption"
    assert const.ATTR_POWER_CONSUMPTION == "power_consumption"
    
    assert const.READING_MOISTURE_CONSUMPTION == "water consumption"
    assert const.READING_FERTILIZER_CONSUMPTION == "fertilizer consumption"
    assert const.READING_POWER_CONSUMPTION == "power consumption"
    
    assert const.ICON_WATER_CONSUMPTION == "mdi:water-pump"
    assert const.ICON_FERTILIZER_CONSUMPTION == "mdi:chart-line-variant"
    assert const.ICON_POWER_CONSUMPTION == "mdi:flash"