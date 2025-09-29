import importlib.machinery
import importlib.util
import sys
from types import SimpleNamespace
from pathlib import Path


def _load(name: str, rel_path: str):
    path = Path(rel_path).resolve()
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


def test_apply_rounding_for_temperature_humidity_illuminance():
    # Minimal HA consts
    sys.modules["homeassistant.const"] = SimpleNamespace(
        ATTR_ICON="mdi:icon",
        ATTR_NAME="name",
        ATTR_ENTITY_PICTURE="entity_picture",
        ATTR_UNIT_OF_MEASUREMENT="unit_of_measurement",
        LIGHT_LUX="lx",
        PERCENTAGE="%",
        STATE_UNKNOWN="unknown",
        STATE_UNAVAILABLE="unavailable",
        STATE_OK="ok",
        STATE_PROBLEM="problem",
        UnitOfConductivity=SimpleNamespace(MICROSIEMENS_PER_CM="μS/cm"),
        UnitOfTemperature=SimpleNamespace(CELSIUS="°C"),
        UnitOfTime=SimpleNamespace(HOURS="h"),
        Platform=SimpleNamespace(SENSOR="sensor", NUMBER="number", SELECT="select", TEXT="text"),
    )

    # Minimal sensor base classes
    sys.modules["homeassistant.components.sensor"] = SimpleNamespace(
        RestoreSensor=object,
        SensorDeviceClass=SimpleNamespace(TEMPERATURE="temp", HUMIDITY="hum", ILLUMINANCE="lx"),
        SensorEntity=object,
        SensorStateClass=SimpleNamespace(MEASUREMENT="m"),
    )
    sys.modules["homeassistant.core"] = SimpleNamespace(HomeAssistant=object, callback=lambda f: f)
    sys.modules["homeassistant.helpers.entity"] = SimpleNamespace(
        Entity=object,
        EntityCategory=SimpleNamespace(DIAGNOSTIC="diagnostic"),
        async_generate_entity_id=lambda fmt, name, current_ids=None: name,
    )
    # Additional modules imported by sensor.py
    sys.modules["homeassistant.components.integration.const"] = SimpleNamespace(METHOD_TRAPEZOIDAL="trapz")
    sys.modules["homeassistant.components.integration.sensor"] = SimpleNamespace(IntegrationSensor=object)
    sys.modules["homeassistant.components.utility_meter.const"] = SimpleNamespace(
        DAILY="daily",
        DATA_TARIFF_SENSORS="tariff_sensors",
        DATA_UTILITY="utility_data",
    )
    sys.modules["homeassistant.components.utility_meter.sensor"] = SimpleNamespace(UtilityMeterSensor=object)
    sys.modules["homeassistant.helpers.dispatcher"] = SimpleNamespace(async_dispatcher_connect=lambda *a, **k: None)
    sys.modules["homeassistant.helpers.event"] = SimpleNamespace(async_track_state_change_event=lambda *a, **k: None, async_call_later=lambda *a, **k: None)
    sys.modules["homeassistant.util.dt"] = SimpleNamespace(utcnow=lambda: None)
    sys.modules["homeassistant.util"] = SimpleNamespace(dt=sys.modules["homeassistant.util.dt"])  # stub package for 'from homeassistant.util import dt'
    sys.modules["homeassistant.components.recorder"] = SimpleNamespace(history=object, get_instance=lambda: None)
    sys.modules["homeassistant.config_entries"] = SimpleNamespace(ConfigEntry=object, SOURCE_IMPORT="import")
    sys.modules["homeassistant.helpers.entity_platform"] = SimpleNamespace(AddEntitiesCallback=object)
    # Stub voluptuous for __init__ import chain
    sys.modules["voluptuous"] = SimpleNamespace(Required=lambda x: x, Optional=lambda x, **k: x, In=lambda x: x, Coerce=lambda t: (lambda v: v))
    # Stub websocket_api for __init__ import chain
    sys.modules["homeassistant.components"] = SimpleNamespace(
        websocket_api=SimpleNamespace(
            websocket_command=lambda *a, **k: (lambda f: f),
            async_response=lambda f: f,
            async_register_command=lambda *a, **k: None,
        )
    )
    # Stub helpers package root as needed by __init__.py import
    import types as _types
    helpers_root = _types.ModuleType("homeassistant.helpers")
    helpers_root.config_validation = SimpleNamespace()
    helpers_root.device_registry = SimpleNamespace(async_get=lambda hass: SimpleNamespace(async_get_or_create=lambda **kwargs: None))
    helpers_root.entity_registry = SimpleNamespace(async_get=lambda hass: SimpleNamespace(async_update_entity=lambda *a, **k: None))
    sys.modules["homeassistant.helpers"] = helpers_root
    # Also register explicit submodules for import style
    sys.modules["homeassistant.helpers.entity_component"] = SimpleNamespace(EntityComponent=object)
    sys.modules["homeassistant.helpers.storage"] = SimpleNamespace(Store=object)

    # Domain constants needed by sensor.py
    const = _load("custom_components.plant.const", "custom_components/plant/const.py")

    sys.modules["custom_components.plant.services"] = SimpleNamespace(
        async_setup_services=lambda hass: None, async_unload_services=lambda hass: None
    )

    # Minimal plant device providing decimals_for
    class DummyPlant:
        def __init__(self):
            self.unique_id = "u"

        def decimals_for(self, key):
            mapping = {"temperature": 1, "humidity": 1, "illuminance": 0}
            return mapping.get(key, 2)

    # Prepare a fake hass state
    class DummyHass:
        def __init__(self):
            self._states = {}

        def states(self):
            return self

        def get(self, eid):
            return self._states.get(eid)

    # Load sensor module
    sensor_mod = _load("custom_components.plant.sensor", "custom_components/plant/sensor.py")

    # Use helper on a constructed base instance
    base = sensor_mod.PlantCurrentStatus.__new__(sensor_mod.PlantCurrentStatus)
    base._plant = DummyPlant()
    base.sensor_type = lambda: "temperature"
    assert base._apply_rounding("21.234") == 21.2
    base.sensor_type = lambda: "humidity"
    assert base._apply_rounding("50.67") == 50.7
    base.sensor_type = lambda: "illuminance"
    assert base._apply_rounding("1234.9") == 1235.0

