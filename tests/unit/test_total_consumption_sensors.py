"""Test total consumption sensor functionality in the plant integration."""
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
        setattr(dummy_ha_const, "ATTR_DOMAIN", "domain")
        sys.modules["homeassistant.const"] = dummy_ha_const


def test_total_consumption_sensor_constants():
    """Test that total consumption sensor constants are defined."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test that total consumption sensor types exist in default aggregations
    assert "total_water_consumption" in const.DEFAULT_AGGREGATIONS
    assert "total_fertilizer_consumption" in const.DEFAULT_AGGREGATIONS
    assert "total_power_consumption" in const.DEFAULT_AGGREGATIONS
    
    # Test that total consumption sensors use ORIGINAL aggregation method
    assert const.DEFAULT_AGGREGATIONS["total_water_consumption"] == const.AGGREGATION_ORIGINAL
    assert const.DEFAULT_AGGREGATIONS["total_fertilizer_consumption"] == const.AGGREGATION_ORIGINAL
    assert const.DEFAULT_AGGREGATIONS["total_power_consumption"] == const.AGGREGATION_ORIGINAL


def test_total_consumption_sensor_names():
    """Test that total consumption sensor names are properly defined."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test that total consumption readings are defined
    assert "total_water_consumption" in const.DEFAULT_AGGREGATIONS
    assert "total_fertilizer_consumption" in const.DEFAULT_AGGREGATIONS
    assert "total_power_consumption" in const.DEFAULT_AGGREGATIONS


def test_integration_sensor_constants():
    """Test that integration sensor constants are defined."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test that integration sensor types exist in default aggregations
    assert "total_integral" in const.DEFAULT_AGGREGATIONS
    
    # Test that integration sensors use ORIGINAL aggregation method
    assert const.DEFAULT_AGGREGATIONS["total_integral"] == const.AGGREGATION_ORIGINAL


def test_light_integration_constants():
    """Test that light integration constants are defined."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test PPFD and DLI constants
    assert const.READING_PPFD == "ppfd (mol)"
    assert const.READING_DLI == "dli"
    assert const.UNIT_PPFD == "mol/s⋅m²s"
    assert const.UNIT_DLI == "mol/d⋅m²"
    assert const.ICON_PPFD == "mdi:white-balance-sunny"
    assert const.ICON_DLI == "mdi:counter"
    
    # Test that PPFD and DLI use ORIGINAL aggregation method
    assert const.DEFAULT_AGGREGATIONS["ppfd"] == const.AGGREGATION_ORIGINAL
    assert const.DEFAULT_AGGREGATIONS["dli"] == const.AGGREGATION_ORIGINAL


def test_aggregation_methods_extended():
    """Test that extended aggregation methods include original."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test that AGGREGATION_METHODS_EXTENDED contains all AGGREGATION_METHODS plus 'original'
    for method in const.AGGREGATION_METHODS:
        assert method in const.AGGREGATION_METHODS_EXTENDED
    assert const.AGGREGATION_ORIGINAL in const.AGGREGATION_METHODS_EXTENDED


def test_plant_total_water_consumption():
    """Test PlantTotalWaterConsumption sensor class."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    sensor_module = _load_module("custom_components.plant.sensor", "custom_components/plant/sensor.py")
    
    # Create mock objects
    hass = Mock()
    config = Mock()
    config.entry_id = "test_entry_id"
    
    plant_device = Mock()
    plant_device.name = "Test Plant"
    plant_device.unique_id = "test_plant_id"
    
    source_sensor = Mock()
    source_sensor.entity_id = "sensor.test_moisture_consumption"
    
    # Create the sensor instance
    sensor = sensor_module.PlantTotalWaterConsumption(hass, config, plant_device, source_sensor)
    
    # Test sensor properties
    assert sensor.name == "Test Plant Total water consumption"
    assert sensor.unique_id == "test_entry_id-total-water-consumption"
    assert sensor.icon == const.ICON_WATER_CONSUMPTION
    assert sensor.entity_category == "diagnostic"
    
    # Test device info
    device_info = sensor.device_info
    assert device_info["identifiers"] == {("plant", "test_plant_id")}
    
    # Test source entity
    assert sensor.source_entity == "sensor.test_moisture_consumption"


def test_plant_total_water_consumption_without_source():
    """Test PlantTotalWaterConsumption sensor class without source sensor."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    sensor_module = _load_module("custom_components.plant.sensor", "custom_components/plant/sensor.py")
    
    # Create mock objects
    hass = Mock()
    config = Mock()
    config.entry_id = "test_entry_id"
    
    plant_device = Mock()
    plant_device.name = "Test Plant"
    plant_device.unique_id = "test_plant_id"
    
    # Create the sensor instance without source sensor
    sensor = sensor_module.PlantTotalWaterConsumption(hass, config, plant_device, None)
    
    # Test sensor properties
    assert sensor.name == "Test Plant Total water consumption"
    assert sensor.unique_id == "test_entry_id-total-water-consumption"
    assert sensor.icon == const.ICON_WATER_CONSUMPTION
    assert sensor.entity_category == "diagnostic"
    
    # Test device info
    device_info = sensor.device_info
    assert device_info["identifiers"] == {("plant", "test_plant_id")}
    
    # Test source entity is empty
    assert sensor.source_entity == ""


def test_plant_total_fertilizer_consumption():
    """Test PlantTotalFertilizerConsumption sensor class."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    sensor_module = _load_module("custom_components.plant.sensor", "custom_components/plant/sensor.py")
    
    # Create mock objects
    hass = Mock()
    config = Mock()
    config.entry_id = "test_entry_id"
    
    plant_device = Mock()
    plant_device.name = "Test Plant"
    plant_device.unique_id = "test_plant_id"
    
    source_sensor = Mock()
    source_sensor.entity_id = "sensor.test_fertilizer_consumption"
    
    # Create the sensor instance
    sensor = sensor_module.PlantTotalFertilizerConsumption(hass, config, plant_device, source_sensor)
    
    # Test sensor properties
    assert sensor.name == "Test Plant Total fertilizer consumption"
    assert sensor.unique_id == "test_entry_id-total-fertilizer-consumption"
    assert sensor.icon == const.ICON_FERTILIZER_CONSUMPTION
    assert sensor.entity_category == "diagnostic"
    
    # Test device info
    device_info = sensor.device_info
    assert device_info["identifiers"] == {("plant", "test_plant_id")}
    
    # Test source entity
    assert sensor.source_entity == "sensor.test_fertilizer_consumption"


def test_plant_total_fertilizer_consumption_without_source():
    """Test PlantTotalFertilizerConsumption sensor class without source sensor."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    sensor_module = _load_module("custom_components.plant.sensor", "custom_components/plant/sensor.py")
    
    # Create mock objects
    hass = Mock()
    config = Mock()
    config.entry_id = "test_entry_id"
    
    plant_device = Mock()
    plant_device.name = "Test Plant"
    plant_device.unique_id = "test_plant_id"
    
    # Create the sensor instance without source sensor
    sensor = sensor_module.PlantTotalFertilizerConsumption(hass, config, plant_device, None)
    
    # Test sensor properties
    assert sensor.name == "Test Plant Total fertilizer consumption"
    assert sensor.unique_id == "test_entry_id-total-fertilizer-consumption"
    assert sensor.icon == const.ICON_FERTILIZER_CONSUMPTION
    assert sensor.entity_category == "diagnostic"
    
    # Test device info
    device_info = sensor.device_info
    assert device_info["identifiers"] == {("plant", "test_plant_id")}
    
    # Test source entity is empty
    assert sensor.source_entity == ""


def test_replace_external_sensor():
    """Test replace_external_sensor method."""
    _setup_ha_modules()
    
    # Load required modules
    sensor_module = _load_module("custom_components.plant.sensor", "custom_components/plant/sensor.py")
    
    # Create mock objects
    hass = Mock()
    config = Mock()
    config.entry_id = "test_entry_id"
    
    plant_device = Mock()
    plant_device.name = "Test Plant"
    plant_device.unique_id = "test_plant_id"
    
    # Create the sensor instance
    sensor = sensor_module.PlantTotalWaterConsumption(hass, config, plant_device, None)
    
    # Test replacing external sensor
    sensor.replace_external_sensor("sensor.new_moisture_sensor")
    assert sensor.source_entity == "sensor.new_moisture_sensor"