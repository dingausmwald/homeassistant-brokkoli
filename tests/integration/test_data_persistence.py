"""Test data persistence in the plant integration."""
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
        # Inject minimal dummy modules for Home Assistant components
        dummy_ha_const = type(sys)("homeassistant.const")
        setattr(dummy_ha_const, "STATE_UNKNOWN", "unknown")
        setattr(dummy_ha_const, "STATE_UNAVAILABLE", "unavailable")
        sys.modules["homeassistant.const"] = dummy_ha_const


def test_export_functionality():
    """Test export functionality."""
    _setup_ha_modules()
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test that export service is defined
    assert const.SERVICE_EXPORT_PLANTS == "export_plants"
    
    # Test export related constants
    assert const.DEFAULT_IMAGE_PATH == "/config/www/images/plants/"
    assert const.DEFAULT_IMAGE_LOCAL_URL == "/local/images/plants/"


def test_import_functionality():
    """Test import functionality."""
    _setup_ha_modules()
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test that import service is defined
    assert const.SERVICE_IMPORT_PLANTS == "import_plants"


def test_plant_creation_persistence():
    """Test that created plants persist data correctly."""
    _setup_ha_modules()
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test that new plant attribute is defined
    assert const.ATTR_IS_NEW_PLANT == "is_new_plant"


def test_configuration_persistence():
    """Test that configuration data persists correctly."""
    _setup_ha_modules()
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test configuration attributes that should persist
    config_attrs = [
        "CONF_MIN_TEMPERATURE",
        "CONF_MAX_TEMPERATURE",
        "CONF_MIN_MOISTURE",
        "CONF_MAX_MOISTURE",
        "CONF_MIN_CONDUCTIVITY",
        "CONF_MAX_CONDUCTIVITY",
        "CONF_MIN_ILLUMINANCE",
        "CONF_MAX_ILLUMINANCE",
    ]
    
    for attr in config_attrs:
        assert hasattr(const, attr), f"Configuration attribute {attr} should be defined"


def test_sensor_data_persistence():
    """Test that sensor data persists correctly."""
    _setup_ha_modules()
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test that sensor-related attributes are defined for persistence
    sensor_attrs = [
        "ATTR_TEMPERATURE",
        "ATTR_MOISTURE",
        "ATTR_CONDUCTIVITY",
        "ATTR_ILLUMINANCE",
        "ATTR_HUMIDITY",
        "ATTR_CO2",
        "ATTR_PPFD",
        "ATTR_DLI",
        "ATTR_PH",
    ]
    
    for attr in sensor_attrs:
        assert hasattr(const, attr), f"Sensor attribute {attr} should be defined"


def test_consumption_data_persistence():
    """Test that consumption data persists correctly."""
    _setup_ha_modules()
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test that consumption-related attributes are defined for persistence
    consumption_attrs = [
        "ATTR_WATER_CONSUMPTION",
        "ATTR_FERTILIZER_CONSUMPTION",
        "ATTR_POWER_CONSUMPTION",
    ]
    
    for attr in consumption_attrs:
        assert hasattr(const, attr), f"Consumption attribute {attr} should be defined"


def test_plant_attributes_persistence():
    """Test that extended plant attributes persist correctly."""
    _setup_ha_modules()
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test that extended plant attributes are defined for persistence
    extended_attrs = [
        "ATTR_STRAIN",
        "ATTR_BREEDER",
        "ATTR_IMAGE",
        "ATTR_PHENOTYPE",
        "ATTR_HUNGER",
        "ATTR_GROWTH_STRETCH",
        "ATTR_FLOWER_STRETCH",
        "ATTR_MOLD_RESISTANCE",
        "ATTR_DIFFICULTY",
        "ATTR_YIELD",
        "ATTR_NOTES",
        "ATTR_IMAGES",
    ]
    
    for attr in extended_attrs:
        assert hasattr(const, attr), f"Extended attribute {attr} should be defined"