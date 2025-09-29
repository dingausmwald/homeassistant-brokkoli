import importlib.machinery
import importlib.util
import sys
from pathlib import Path


def _load_module_from_path(name: str, rel_path: str):
    path = Path(rel_path).resolve()
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


def test_config_flow_defaults_include_decimals():
    # Only load sensor_configuration to verify defaults structure without importing HA deps
    sensor_cfg = _load_module_from_path(
        "sensor_configuration_decimals", "custom_components/plant/sensor_configuration.py"
    )

    DEFAULT_DECIMALS = sensor_cfg.DEFAULT_DECIMALS
    assert DEFAULT_DECIMALS["temperature"].decimals >= 0
    # Ensure we have keys we expect to later surface via config UI
    required = [
        "moisture",
        "dli",
        "total_water_consumption",
        "energy_cost",
    ]
    for key in required:
        assert key in DEFAULT_DECIMALS

