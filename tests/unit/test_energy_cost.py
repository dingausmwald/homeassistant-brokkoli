"""Test energy cost functionality in the plant integration."""
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


def test_energy_cost_constants():
    """Test that energy cost constants are defined."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test energy cost constants
    assert const.READING_ENERGY_COST == "energy cost"
    assert const.ICON_ENERGY_COST == "mdi:currency-eur"
    assert const.ATTR_KWH_PRICE == "kwh_price"
    assert const.DEFAULT_KWH_PRICE == 0.3684
    
    # Test that energy cost sensor uses MEAN aggregation method
    assert const.DEFAULT_AGGREGATIONS["energy_cost"] == const.AGGREGATION_MEAN


def test_energy_cost_config_constants():
    """Test that energy cost config constants are defined."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test energy cost config
    assert const.CONF_DEFAULT_KWH_PRICE == "default_kwh_price"


def test_energy_cost_calculation_logic():
    """Test energy cost calculation logic."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test basic energy cost calculation
    kwh_price = const.DEFAULT_KWH_PRICE
    consumption_kwh = 10.0
    expected_cost = kwh_price * consumption_kwh
    
    assert expected_cost == 3.684  # 0.3684 * 10
    
    # Test with different values
    consumption_kwh = 25.5
    expected_cost = kwh_price * consumption_kwh
    
    assert round(expected_cost, 4) == 9.3942  # 0.3684 * 25.5


def test_energy_cost_rounding():
    """Test energy cost rounding."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test rounding to 2 decimal places (typical for currency)
    kwh_price = const.DEFAULT_KWH_PRICE
    consumption_kwh = 7.333
    cost = kwh_price * consumption_kwh
    
    # Should round to 2 decimal places
    rounded_cost = round(cost, 2)
    assert rounded_cost == 2.70  # 0.3684 * 7.333 = 2.701692 ≈ 2.70


def test_energy_cost_edge_cases():
    """Test energy cost calculation edge cases."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test zero consumption
    kwh_price = const.DEFAULT_KWH_PRICE
    consumption_kwh = 0.0
    cost = kwh_price * consumption_kwh
    assert cost == 0.0
    
    # Test high consumption
    consumption_kwh = 1000.0
    cost = kwh_price * consumption_kwh
    assert cost == 368.4  # 0.3684 * 1000


def test_energy_cost_calculation():
    """Test energy cost calculation based on power consumption."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    sensor_module = _load_module("custom_components.plant.sensor", "custom_components/plant/sensor.py")
    
    # Create mock objects
    hass = Mock()
    config = Mock()
    config.entry_id = "test_entry_id"
    config.data = {const.ATTR_KWH_PRICE: 0.30}  # 0.30 € per kWh
    
    plant_device = Mock()
    plant_device.name = "Test Plant"
    plant_device.unique_id = "test_plant_id"
    plant_device.decimals_for = Mock(return_value=2)  # 2 decimal places
    
    # Create total power consumption sensor mock
    total_power_sensor = Mock()
    total_power_sensor.entity_id = "sensor.test_total_power"
    total_power_sensor.native_value = 10.5  # 10.5 kWh
    
    plant_device.total_power_consumption = total_power_sensor
    
    # Create the energy cost sensor instance
    sensor = sensor_module.PlantEnergyCost(hass, config, plant_device)
    
    # Test energy cost calculation
    sensor._update_energy_cost()
    
    # Expected cost: 10.5 kWh * 0.30 €/kWh = 3.15 €
    assert sensor.native_value == 3.15


def test_energy_cost_with_zero_consumption():
    """Test energy cost calculation with zero power consumption."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    sensor_module = _load_module("custom_components.plant.sensor", "custom_components/plant/sensor.py")
    
    # Create mock objects
    hass = Mock()
    config = Mock()
    config.entry_id = "test_entry_id"
    config.data = {const.ATTR_KWH_PRICE: 0.30}  # 0.30 € per kWh
    
    plant_device = Mock()
    plant_device.name = "Test Plant"
    plant_device.unique_id = "test_plant_id"
    plant_device.decimals_for = Mock(return_value=2)  # 2 decimal places
    
    # Create total power consumption sensor mock with zero value
    total_power_sensor = Mock()
    total_power_sensor.entity_id = "sensor.test_total_power"
    total_power_sensor.native_value = 0.0
    
    plant_device.total_power_consumption = total_power_sensor
    
    # Create the energy cost sensor instance
    sensor = sensor_module.PlantEnergyCost(hass, config, plant_device)
    
    # Test energy cost calculation
    sensor._update_energy_cost()
    
    # Expected cost: 0.0 kWh * 0.30 €/kWh = 0.00 €
    assert sensor.native_value == 0.0


def test_energy_cost_with_no_power_sensor():
    """Test energy cost calculation when no power sensor is available."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    sensor_module = _load_module("custom_components.plant.sensor", "custom_components/plant/sensor.py")
    
    # Create mock objects
    hass = Mock()
    config = Mock()
    config.entry_id = "test_entry_id"
    config.data = {const.ATTR_KWH_PRICE: 0.30}  # 0.30 € per kWh
    
    plant_device = Mock()
    plant_device.name = "Test Plant"
    plant_device.unique_id = "test_plant_id"
    
    # No total power consumption sensor
    plant_device.total_power_consumption = None
    
    # Create the energy cost sensor instance
    sensor = sensor_module.PlantEnergyCost(hass, config, plant_device)
    
    # Test energy cost calculation
    sensor._update_energy_cost()
    
    # Should be None when no power sensor is available
    assert sensor.native_value is None


def test_energy_cost_with_invalid_power_value():
    """Test energy cost calculation with invalid power consumption value."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    sensor_module = _load_module("custom_components.plant.sensor", "custom_components/plant/sensor.py")
    
    # Create mock objects
    hass = Mock()
    config = Mock()
    config.entry_id = "test_entry_id"
    config.data = {const.ATTR_KWH_PRICE: 0.30}  # 0.30 € per kWh
    
    plant_device = Mock()
    plant_device.name = "Test Plant"
    plant_device.unique_id = "test_plant_id"
    plant_device.decimals_for = Mock(return_value=2)  # 2 decimal places
    
    # Create total power consumption sensor mock with invalid value
    total_power_sensor = Mock()
    total_power_sensor.entity_id = "sensor.test_total_power"
    total_power_sensor.native_value = "invalid"
    
    plant_device.total_power_consumption = total_power_sensor
    
    # Create the energy cost sensor instance
    sensor = sensor_module.PlantEnergyCost(hass, config, plant_device)
    
    # Test energy cost calculation
    sensor._update_energy_cost()
    
    # Should be None when power value is invalid
    assert sensor.native_value is None


def test_energy_cost_with_unavailable_power_sensor():
    """Test energy cost calculation when power sensor is unavailable."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    sensor_module = _load_module("custom_components.plant.sensor", "custom_components/plant/sensor.py")
    
    # Create mock objects
    hass = Mock()
    config = Mock()
    config.entry_id = "test_entry_id"
    config.data = {const.ATTR_KWH_PRICE: 0.30}  # 0.30 € per kWh
    
    plant_device = Mock()
    plant_device.name = "Test Plant"
    plant_device.unique_id = "test_plant_id"
    
    # Create total power consumption sensor mock with unavailable value
    total_power_sensor = Mock()
    total_power_sensor.entity_id = "sensor.test_total_power"
    total_power_sensor.native_value = "unavailable"
    
    plant_device.total_power_consumption = total_power_sensor
    
    # Create the energy cost sensor instance
    sensor = sensor_module.PlantEnergyCost(hass, config, plant_device)
    
    # Test energy cost calculation
    sensor._update_energy_cost()
    
    # Should be None when power sensor is unavailable
    assert sensor.native_value is None


def test_energy_cost_with_default_price():
    """Test energy cost calculation with default kWh price."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    sensor_module = _load_module("custom_components.plant.sensor", "custom_components/plant/sensor.py")
    
    # Create mock objects
    hass = Mock()
    config = Mock()
    config.entry_id = "test_entry_id"
    config.data = {}  # No kWh price configured, should use default
    
    plant_device = Mock()
    plant_device.name = "Test Plant"
    plant_device.unique_id = "test_plant_id"
    plant_device.decimals_for = Mock(return_value=2)  # 2 decimal places
    
    # Create total power consumption sensor mock
    total_power_sensor = Mock()
    total_power_sensor.entity_id = "sensor.test_total_power"
    total_power_sensor.native_value = 20.0  # 20.0 kWh
    
    plant_device.total_power_consumption = total_power_sensor
    
    # Create the energy cost sensor instance
    sensor = sensor_module.PlantEnergyCost(hass, config, plant_device)
    
    # Test energy cost calculation with default price
    sensor._update_energy_cost()
    
    # Expected cost: 20.0 kWh * 0.3684 €/kWh = 7.368 € ≈ 7.37 € (rounded to 2 decimals)
    assert round(sensor.native_value, 2) == 7.37
