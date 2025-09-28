import importlib.machinery
import importlib.util
import sys
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

import requests_mock


class DummyConfigEntry:
    def __init__(self, data, options=None):
        self.data = data
        self.options = options or {}
        self.entry_id = "test123"


class DummyHass:
    def __init__(self, config_entries):
        self._entries = config_entries
        self._cfg = self._CfgEntries(config_entries)

    class _CfgEntries:
        def __init__(self, entries):
            self._entries = entries

        def async_entries(self, domain):
            return self._entries

    @property
    def config_entries(self):
        return self._cfg

    def set_entries(self, entries):
        self._cfg = DummyHass._CfgEntries(entries)


def _load(name: str, rel_path: str):
    path = Path(rel_path).resolve()
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module



@patch("homeassistant.core.HomeAssistant.async_start")
def test_plant_device_decimals_for_with_overrides(mock_async_start):
    # Inject a minimal dummy module for homeassistant.const used by const.py
    dummy_ha_const = type(sys)("homeassistant.const")
    setattr(dummy_ha_const, "ATTR_ICON", "mdi:icon")
    setattr(dummy_ha_const, "Platform", SimpleNamespace(NUMBER="number", SENSOR="sensor", SELECT="select", TEXT="text"))
    setattr(dummy_ha_const, "ATTR_ENTITY_PICTURE", "entity_picture")
    setattr(dummy_ha_const, "ATTR_NAME", "name")
    setattr(dummy_ha_const, "ATTR_UNIT_OF_MEASUREMENT", "unit_of_measurement")
    setattr(dummy_ha_const, "STATE_OK", "ok")
    setattr(dummy_ha_const, "STATE_PROBLEM", "problem")
    setattr(dummy_ha_const, "STATE_UNAVAILABLE", "unavailable")
    setattr(dummy_ha_const, "STATE_UNKNOWN", "unknown")
    sys.modules["homeassistant.const"] = dummy_ha_const

    # Stub websocket_api used in __init__
    dummy_ws = SimpleNamespace(
        websocket_command=lambda *args, **kwargs: (lambda f: f),
        async_response=(lambda f: f),
        async_register_command=lambda *args, **kwargs: None,
    )
    # Build nested package structure: homeassistant.components.utility_meter.const
    # Stub utility_meter.const symbols used
    dummy_um_const = SimpleNamespace(DATA_TARIFF_SENSORS="tariffs", DATA_UTILITY="utility")
    sys.modules["homeassistant.components.utility_meter.const"] = dummy_um_const
    # Stub utility_meter.sensor (referenced by sensor imports)
    sys.modules["homeassistant.components.utility_meter.sensor"] = SimpleNamespace(UtilityMeterSensor=object)
    sys.modules["homeassistant.components.integration.const"] = SimpleNamespace(METHOD_TRAPEZOIDAL="trapz")
    sys.modules["homeassistant.components.integration.sensor"] = SimpleNamespace(IntegrationSensor=object)
    # Stub additional HA modules referenced in __init__
    sys.modules["homeassistant.config_entries"] = SimpleNamespace(SOURCE_IMPORT="import", ConfigEntry=object)
    sys.modules["homeassistant.core"] = SimpleNamespace(HomeAssistant=object, callback=lambda f: f)
    # Provide helpers subpackages used in __init__ imports
    sys.modules["homeassistant.helpers.config_validation"] = SimpleNamespace()
    # Create helpers package root to satisfy 'from homeassistant.helpers import (...)'
    # Create helpers root as a proper module with attributes
    import types as _types
    helpers_root = _types.ModuleType("homeassistant.helpers")
    sys.modules["homeassistant.helpers"] = helpers_root
    # Also stub the 'entity' submodule required
    sys.modules["homeassistant.helpers.entity"] = SimpleNamespace(
        Entity=object, async_generate_entity_id=lambda fmt, name, current_ids=None: name
    )
    sys.modules["homeassistant.helpers.entity_component"] = SimpleNamespace(
        EntityComponent=object
    )
    sys.modules["homeassistant.helpers.device_registry"] = SimpleNamespace(
        async_get=lambda hass: SimpleNamespace(async_get_or_create=lambda **kwargs: None)
    )
    sys.modules["homeassistant.helpers.entity_registry"] = SimpleNamespace(
        async_get=lambda hass: SimpleNamespace(async_update_entity=lambda *a, **k: None)
    )
    sys.modules["homeassistant.helpers.storage"] = SimpleNamespace(Store=object)
    sys.modules["homeassistant.helpers.event"] = SimpleNamespace(
        async_call_later=lambda *args, **kwargs: None
    )
    # Provide components root with websocket_api
    dummy_components = type(sys)("homeassistant.components")
    setattr(dummy_components, "websocket_api", dummy_ws)
    sys.modules["homeassistant.components"] = dummy_components

    # Stub aiohttp used by services
    sys.modules["aiohttp"] = SimpleNamespace(ClientSession=object)
    # Stub services module to avoid heavy dependencies
    sys.modules["custom_components.plant.services"] = SimpleNamespace(
        async_setup_services=lambda hass: None,
        async_unload_services=lambda hass: None,
    )

    # Ensure package roots exist so relative imports work
    import types as _types
    if "custom_components" not in sys.modules:
        sys.modules["custom_components"] = _types.ModuleType("custom_components")
    if "custom_components.plant" not in sys.modules:
        sys.modules["custom_components.plant"] = _types.ModuleType("custom_components.plant")

    const = _load("custom_components.plant.const", "custom_components/plant/const.py")
    # Avoid importing full __init__ due to voluptuous dependency; load just PlantDevice
    # by creating a minimal shim module that replaces voluptuous import
    sys.modules["voluptuous"] = SimpleNamespace(
        Required=lambda x: x,
        Optional=lambda x, **kwargs: x,
        In=lambda x: x,
        Coerce=lambda t: (lambda v: v),
    )
    init_mod = _load("custom_components.plant", "custom_components/plant/__init__.py")
    PlantDevice = getattr(init_mod, "PlantDevice")

    # Create a config entry that mimics a plant
    FLOW_PLANT_INFO = getattr(const, "FLOW_PLANT_INFO")
    ATTR_NAME = "name"
    DEVICE_TYPE_PLANT = getattr(const, "DEVICE_TYPE_PLANT")

    plant_entry = DummyConfigEntry({FLOW_PLANT_INFO: {ATTR_NAME: "My Plant", "device_type": DEVICE_TYPE_PLANT}})

    # Central config entry with decimal overrides
    overrides = {
        FLOW_PLANT_INFO: {
            "decimals_temperature": 3,
            "decimals_dli": 5,
        },
        "is_config": True,
    }
    config_entry = DummyConfigEntry(overrides)

    # Assemble hass with central config
    hass = DummyHass([config_entry])

    # Instantiate PlantDevice
    device = PlantDevice(hass, plant_entry)

    assert device.decimals_for("temperature") == 3
    assert device.decimals_for("dli") == 5
    # default fallback from central table for unknown key
    assert isinstance(device.decimals_for("unknown"), int)

