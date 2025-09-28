import importlib.machinery
import importlib.util
import sys
from pathlib import Path


def _load_sensor_configuration_module():
    path = Path("custom_components/plant/sensor_configuration.py").resolve()
    name = "sensor_configuration_testmod"
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


def test_defaults_keys_and_values():
    mod = _load_sensor_configuration_module()
    DEFAULT_DECIMALS = mod.DEFAULT_DECIMALS

    expected_keys = {
        "temperature",
        "moisture",
        "conductivity",
        "illuminance",
        "humidity",
        "CO2",
        "ph",
        "ppfd",
        "dli",
        "total_integral",
        "moisture_consumption",
        "total_water_consumption",
        "fertilizer_consumption",
        "total_fertilizer_consumption",
        "power_consumption",
        "total_power_consumption",
        "energy_cost",
    }

    assert expected_keys.issubset(set(DEFAULT_DECIMALS.keys()))

    # Spot check a few defaults
    assert DEFAULT_DECIMALS["temperature"].decimals == 1
    assert DEFAULT_DECIMALS["conductivity"].decimals == 0
    assert DEFAULT_DECIMALS["dli"].decimals == 2
    assert DEFAULT_DECIMALS["ph"].decimals == 2


def test_get_decimals_for_defaults_and_overrides():
    mod = _load_sensor_configuration_module()
    get_decimals_for = mod.get_decimals_for

    # Defaults
    assert get_decimals_for("temperature") == 1
    assert get_decimals_for("unknown_sensor_type") == 2  # fallback

    # Overrides
    overrides = {
        "temperature": 3,
        "dli": 4,
        "conductivity": 0,
        "energy_cost": 5,
    }
    assert get_decimals_for("temperature", overrides) == 3
    assert get_decimals_for("dli", overrides) == 4
    assert get_decimals_for("conductivity", overrides) == 0
    assert get_decimals_for("energy_cost", overrides) == 5

    # Negative values are clamped to >= 0
    assert get_decimals_for("temperature", {"temperature": -2}) == 0

    # None or invalid overrides fall back to defaults, not crashing
    assert get_decimals_for("temperature", {"temperature": None}) == 1
    assert get_decimals_for("temperature", {"temperature": "not-a-number"}) == 1

