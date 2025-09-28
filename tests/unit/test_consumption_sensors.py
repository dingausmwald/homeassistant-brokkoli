"""Test consumption sensor functionality in the plant integration."""
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


def test_consumption_sensor_constants():
    """Test that consumption sensor constants are defined."""
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
    
    # Test energy cost constants
    assert const.READING_ENERGY_COST == "energy cost"
    assert const.ICON_ENERGY_COST == "mdi:currency-eur"
    assert const.ATTR_KWH_PRICE == "kwh_price"
    assert const.DEFAULT_KWH_PRICE == 0.3684


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


def test_aggregation_methods_for_consumption():
    """Test that aggregation methods for consumption sensors are defined."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test that consumption sensor types have appropriate default aggregations
    assert const.DEFAULT_AGGREGATIONS["moisture_consumption"] == const.AGGREGATION_ORIGINAL
    assert const.DEFAULT_AGGREGATIONS["fertilizer_consumption"] == const.AGGREGATION_ORIGINAL
    assert const.DEFAULT_AGGREGATIONS["total_water_consumption"] == const.AGGREGATION_ORIGINAL
    assert const.DEFAULT_AGGREGATIONS["total_fertilizer_consumption"] == const.AGGREGATION_ORIGINAL
    assert const.DEFAULT_AGGREGATIONS["power_consumption"] == const.AGGREGATION_MEAN
    assert const.DEFAULT_AGGREGATIONS["total_power_consumption"] == const.AGGREGATION_ORIGINAL
    assert const.DEFAULT_AGGREGATIONS["energy_cost"] == const.AGGREGATION_MEAN


def test_plant_current_moisture_consumption():
    """Test PlantCurrentMoistureConsumption sensor class."""
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
    
    # Create the sensor instance
    sensor = sensor_module.PlantCurrentMoistureConsumption(hass, config, plant_device)
    
    # Test sensor properties
    assert sensor.name == "Test Plant water consumption"
    assert sensor.unique_id == "test_entry_id-current-moisture-consumption"
    assert sensor.icon == const.ICON_WATER_CONSUMPTION
    assert sensor.native_unit_of_measurement == const.UNIT_VOLUME
    assert sensor.device_class is None
    assert sensor.state_class == "measurement"
    assert sensor.entity_category == "diagnostic"
    assert sensor.sensor_type() == "moisture_consumption"


def test_plant_current_fertilizer_consumption():
    """Test PlantCurrentFertilizerConsumption sensor class."""
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
    
    # Create the sensor instance
    sensor = sensor_module.PlantCurrentFertilizerConsumption(hass, config, plant_device)
    
    # Test sensor properties
    assert sensor.name == "Test Plant fertilizer consumption"
    assert sensor.unique_id == "test_entry_id-current-fertilizer-consumption"
    assert sensor.icon == const.ICON_FERTILIZER_CONSUMPTION
    assert sensor.native_unit_of_measurement == const.UNIT_CONDUCTIVITY
    assert sensor.device_class is None
    assert sensor.state_class == "measurement"
    assert sensor.entity_category == "diagnostic"
    assert sensor.sensor_type() == "fertilizer_consumption"


def test_plant_current_power_consumption():
    """Test PlantCurrentPowerConsumption sensor class."""
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
    
    # Create the sensor instance
    sensor = sensor_module.PlantCurrentPowerConsumption(hass, config, plant_device)
    
    # Test sensor properties
    assert sensor.name == "Test Plant power consumption"
    assert sensor.unique_id == "test_entry_id-current-power-consumption"
    assert sensor.icon == const.ICON_POWER_CONSUMPTION
    assert sensor.native_unit_of_measurement == "W"
    assert sensor.device_class == "power"
    assert sensor.state_class == "measurement"
    assert sensor.sensor_type() == "power_consumption"


def test_plant_total_power_consumption():
    """Test PlantTotalPowerConsumption sensor class."""
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
    
    # Create the sensor instance
    sensor = sensor_module.PlantTotalPowerConsumption(hass, config, plant_device)
    
    # Test sensor properties
    assert sensor.name == "Test Plant Total power consumption"
    assert sensor.unique_id == "test_entry_id-total-power-consumption"
    assert sensor.icon == const.ICON_POWER_CONSUMPTION
    assert sensor.native_unit_of_measurement == "kWh"
    assert sensor.device_class == "energy"
    assert sensor.state_class == "total_increasing"
    assert sensor.entity_category == "diagnostic"
    assert sensor.sensor_type() == "total_power_consumption"


def test_plant_energy_cost():
    """Test PlantEnergyCost sensor class."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    sensor_module = _load_module("custom_components.plant.sensor", "custom_components/plant/sensor.py")
    
    # Create mock objects
    hass = Mock()
    config = Mock()
    config.entry_id = "test_entry_id"
    config.data = {const.ATTR_KWH_PRICE: const.DEFAULT_KWH_PRICE}
    
    plant_device = Mock()
    plant_device.name = "Test Plant"
    plant_device.unique_id = "test_plant_id"
    
    # Create the sensor instance
    sensor = sensor_module.PlantEnergyCost(hass, config, plant_device)
    
    # Test sensor properties
    assert sensor.name == "Test Plant energy cost"
    assert sensor.unique_id == "test_entry_id-energy-cost"
    assert sensor.icon == const.ICON_ENERGY_COST
    assert sensor.native_unit_of_measurement == "€"
    assert sensor.device_class == "monetary"
    assert sensor.state_class == "total"
    assert sensor.entity_category == "diagnostic"
    
    # Test device info
    device_info = sensor.device_info
    assert device_info["identifiers"] == {("plant", "test_plant_id")}