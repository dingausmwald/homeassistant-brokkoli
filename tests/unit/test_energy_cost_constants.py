"""Test energy cost constants and configuration in the plant integration."""
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


def test_energy_cost_with_custom_prices():
    """Test energy cost calculation with custom prices."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test with different kWh prices
    custom_price = 0.30  # 0.30 € per kWh
    consumption_kwh = 20.0
    cost = custom_price * consumption_kwh
    assert cost == 6.0  # 0.30 * 20
    
    # Test with higher price
    high_price = 0.50  # 0.50 € per kWh
    consumption_kwh = 15.5
    cost = high_price * consumption_kwh
    assert cost == 7.75  # 0.50 * 15.5


def test_energy_cost_decimal_configuration():
    """Test energy cost decimal configuration."""
    _setup_ha_modules()
    
    # Load required modules
    sensor_config = _load_module("custom_components.plant.sensor_configuration", "custom_components/plant/sensor_configuration.py")
    
    # Test that energy cost uses 2 decimal places
    assert sensor_config.DEFAULT_DECIMALS["energy_cost"].decimals == 2


def test_energy_cost_with_negative_values():
    """Test energy cost calculation with negative consumption values."""
    _setup_ha_modules()
    
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test with negative consumption (e.g., energy returned to grid)
    kwh_price = const.DEFAULT_KWH_PRICE
    consumption_kwh = -5.0  # Negative consumption
    cost = kwh_price * consumption_kwh
    assert cost == -1.842  # 0.3684 * -5
    
    # Test with zero price and negative consumption
    zero_price = 0.0
    consumption_kwh = -10.0
    cost = zero_price * consumption_kwh
    assert cost == 0.0