"""Meter entities for the plant integration"""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.components.integration.const import METHOD_TRAPEZOIDAL
from homeassistant.components.integration.sensor import IntegrationSensor
from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.components.utility_meter.const import DAILY
from homeassistant.components.utility_meter.sensor import UtilityMeterSensor
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ICON,
    ATTR_NAME,
    ATTR_UNIT_OF_MEASUREMENT,
    LIGHT_LUX,
    PERCENTAGE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfConductivity,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import (
    Entity,
    EntityCategory,
    async_generate_entity_id,
)
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    ATTR_CONDUCTIVITY,
    ATTR_IS_NEW_PLANT,
    DATA_UPDATED,
    DEFAULT_LUX_TO_PPFD,
    DOMAIN,
    FLOW_PLANT_INFO,
    FLOW_SENSOR_CONDUCTIVITY,
    FLOW_SENSOR_HUMIDITY,
    FLOW_SENSOR_CO2,
    FLOW_SENSOR_ILLUMINANCE,
    FLOW_SENSOR_MOISTURE,
    FLOW_SENSOR_TEMPERATURE,
    FLOW_SENSOR_POWER_CONSUMPTION,
    FLOW_SENSOR_PH,
    READING_CONDUCTIVITY,
    READING_DLI,
    READING_HUMIDITY,
    READING_CO2,
    READING_ILLUMINANCE,
    READING_MOISTURE,
    READING_PPFD,
    READING_TEMPERATURE,
    READING_POWER_CONSUMPTION,
    READING_MOISTURE_CONSUMPTION,
    READING_FERTILIZER_CONSUMPTION,
    READING_PH,
    UNIT_DLI,
    UNIT_PPFD,
    ICON_PPFD,
    ICON_PH,
    ATTR_PH,
)

_LOGGER = logging.getLogger(__name__)


class PlantCurrentStatus(RestoreSensor):
    """Parent class for the meter classes below"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the Plant component."""
        self._hass = hass
        self._config = config
        self._default_state = None  # Use None instead of 0
        self._plant = plantdevice
        self._external_sensor = None
        # self._conf_check_days = self._plant.check_days
        self.entity_id = async_generate_entity_id(
            f"{DOMAIN}.{{}}", self.name, current_ids={}
        )
        if not self._attr_native_value:
            self._attr_native_value = None  # Use None instead of STATE_UNKNOWN

    def sensor_type(self) -> str | None:
        """Logical sensor type key used for decimals config. Override in subclasses."""
        return None

    def _apply_rounding(self, value: Any) -> Any:
        """Apply centralized decimal rounding if applicable."""
        sensor_key = self.sensor_type()
        if sensor_key is None:
            return self._default_state if value in (STATE_UNKNOWN, STATE_UNAVAILABLE, None) else value
        # Treat unknown/unavailable/non-numeric as default numeric state
        if value in (STATE_UNKNOWN, STATE_UNAVAILABLE, None):
            return self._default_state
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return self._default_state
        try:
            decimals = self._plant.decimals_for(sensor_key)
        except Exception:
            decimals = 2
        return round(numeric, decimals)

    @property
    def state_class(self):
        return SensorStateClass.MEASUREMENT

    @property
    def extra_state_attributes(self) -> dict:
        if self._external_sensor:
            attributes = {
                "external_sensor": self.external_sensor,
                # "history_max": self._history.max,
                # "history_min": self._history.min,
            }
            return attributes

    @property
    def external_sensor(self) -> str:
        """The external sensor we are tracking"""
        return self._external_sensor

    def replace_external_sensor(self, new_sensor: str | None) -> None:
        """Modify the external sensor"""
        _LOGGER.info("Setting %s external sensor to %s", self.entity_id, new_sensor)
        # pylint: disable=attribute-defined-outside-init
        self._external_sensor = new_sensor
        async_track_state_change_event(
            self._hass,
            list([self.entity_id, self._external_sensor]),
            self._state_changed_event,
        )

        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()

        # We do not restore the state for these they are read from the external sensor anyway
        self._attr_native_value = None  # Use None instead of STATE_UNKNOWN
        if state:
            if "external_sensor" in state.attributes:
                self.replace_external_sensor(state.attributes["external_sensor"])
        tracker = [self.entity_id]
        if self._external_sensor:
            tracker.append(self._external_sensor)
        async_track_state_change_event(
            self._hass,
            tracker,
            self._state_changed_event,
        )
        async_dispatcher_connect(
            self._hass, DATA_UPDATED, self._schedule_immediate_update
        )

    @callback
    def _schedule_immediate_update(self):
        self.async_schedule_update_ha_state(True)

    @callback
    def _state_changed_event(self, event):
        """Sensor state change event."""
        self.state_changed(event.data.get("entity_id"), event.data.get("new_state"))

    @callback
    def state_changed(self, entity_id, new_state):
        """Run on every update to allow for changes from the GUI and service call"""
        if not self.hass.states.get(self.entity_id):
            return
        current_attrs = self.hass.states.get(self.entity_id).attributes
        if current_attrs.get("external_sensor") != self._external_sensor:
            self.replace_external_sensor(current_attrs.get("external_sensor"))
        if self._external_sensor:
            external_sensor = self.hass.states.get(self._external_sensor)
            if external_sensor and external_sensor.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                self._attr_native_value = self._apply_rounding(external_sensor.state)
                # Only copy the unit of measurement if we don't have a specific device class that requires a specific unit
                # This prevents CO2 sensors from inheriting 'lx' units from illuminance sensors
                if (not hasattr(self, 'device_class') or (hasattr(self, 'device_class') and self.device_class is None)) and ATTR_UNIT_OF_MEASUREMENT in external_sensor.attributes:
                    self._attr_native_unit_of_measurement = external_sensor.attributes[
                        ATTR_UNIT_OF_MEASUREMENT
                    ]
            else:
                self._attr_native_value = None  # Use None instead of STATE_UNKNOWN for numeric sensors
        else:
            self._attr_native_value = None  # Use None instead of STATE_UNKNOWN for numeric sensors

        if self.state is None:
            return

    async def async_update(self) -> None:
        """Set state and unit to the parent sensor state and unit"""
        if self._external_sensor:
            try:
                state = self.hass.states.get(self._external_sensor)
                if state and state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                    self._attr_native_value = self._apply_rounding(state.state)
                    # Only copy the unit of measurement if we don't have a specific device class that requires a specific unit
                    # This prevents CO2 sensors from inheriting 'lx' units from illuminance sensors
                    if (not hasattr(self, 'device_class') or (hasattr(self, 'device_class') and self.device_class is None)) and ATTR_UNIT_OF_MEASUREMENT in state.attributes:
                        self._attr_native_unit_of_measurement = state.attributes[
                            ATTR_UNIT_OF_MEASUREMENT
                        ]
                elif state:
                    # State is known but unavailable/unknown
                    self._attr_native_value = self._default_state
                else:
                    # Sensor not found
                    _LOGGER.debug(
                        "External sensor %s not found for %s, setting to default: %s",
                        self._external_sensor,
                        self.entity_id,
                        self._default_state,
                    )
                    self._attr_native_value = self._default_state
            except AttributeError:
                _LOGGER.debug(
                    "Unknown external sensor for %s: %s, setting to default: %s",
                    self.entity_id,
                    self._external_sensor,
                    self._default_state,
                )
                self._attr_native_value = self._default_state
            except ValueError:
                _LOGGER.debug(
                    "Unknown external value for %s: %s = %s, setting to default: %s",
                    self.entity_id,
                    self._external_sensor,
                    self.hass.states.get(self._external_sensor).state if self.hass.states.get(self._external_sensor) else "None",
                    self._default_state,
                )
                self._attr_native_value = self._default_state
        else:
            _LOGGER.debug(
                "External sensor not set for %s, setting to default: %s",
                self.entity_id,
                self._default_state,
            )
            self._attr_native_value = self._default_state


class PlantCurrentIlluminance(PlantCurrentStatus):
    """Entity class for the current illuminance meter"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_name = (
            f"{config.data[FLOW_PLANT_INFO][ATTR_NAME]} {READING_ILLUMINANCE}"
        )
        self._attr_unique_id = f"{config.entry_id}-current-illuminance"
        self._attr_icon = "mdi:brightness-6"
        self._external_sensor = config.data[FLOW_PLANT_INFO].get(
            FLOW_SENSOR_ILLUMINANCE
        )
        self._attr_native_unit_of_measurement = LIGHT_LUX

        _LOGGER.info(
            "Added external sensor for %s %s", self.entity_id, self._external_sensor
        )
        super().__init__(hass, config, plantdevice)

    def sensor_type(self) -> str | None:
        """Logical sensor type key used for decimals config."""
        return "illuminance"

    @property
    def device_class(self) -> str:
        """Device class"""
        return SensorDeviceClass.ILLUMINANCE


class PlantCurrentConductivity(PlantCurrentStatus):
    """Entity class for the current conductivity meter"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_name = (
            f"{config.data[FLOW_PLANT_INFO][ATTR_NAME]} {READING_CONDUCTIVITY}"
        )
        self._attr_unique_id = f"{config.entry_id}-current-conductivity"
        self._attr_icon = "mdi:flash-circle"
        self._external_sensor = config.data[FLOW_PLANT_INFO].get(
            FLOW_SENSOR_CONDUCTIVITY
        )
        self._attr_native_unit_of_measurement = UnitOfConductivity.MICROSIEMENS_PER_CM

        super().__init__(hass, config, plantdevice)

    def sensor_type(self) -> str | None:
        """Logical sensor type key used for decimals config."""
        return "conductivity"

    @property
    def device_class(self) -> str:
        """Device class"""
        return ATTR_CONDUCTIVITY


class PlantCurrentMoisture(PlantCurrentStatus):
    """Entity class for the current moisture meter"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_name = (
            f"{config.data[FLOW_PLANT_INFO][ATTR_NAME]} {READING_MOISTURE}"
        )
        self._attr_unique_id = f"{config.entry_id}-current-moisture"
        self._attr_icon = "mdi:water-percent"
        self._external_sensor = config.data[FLOW_PLANT_INFO].get(FLOW_SENSOR_MOISTURE)
        self._attr_native_unit_of_measurement = PERCENTAGE

        super().__init__(hass, config, plantdevice)

    def sensor_type(self) -> str | None:
        """Logical sensor type key used for decimals config."""
        return "moisture"

    @property
    def device_class(self) -> str:
        """Device class"""
        return ATTR_CONDUCTIVITY


class PlantCurrentTemperature(PlantCurrentStatus):
    """Entity class for the current temperature meter"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_name = (
            f"{config.data[FLOW_PLANT_INFO][ATTR_NAME]} {READING_TEMPERATURE}"
        )
        self._attr_unique_id = f"{config.entry_id}-current-temperature"
        self._attr_icon = "mdi:thermometer"
        self._external_sensor = config.data[FLOW_PLANT_INFO].get(
            FLOW_SENSOR_TEMPERATURE
        )
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

        super().__init__(hass, config, plantdevice)

    def sensor_type(self) -> str | None:
        """Logical sensor type key used for decimals config."""
        return "temperature"

    @property
    def device_class(self) -> str:
        """Device class"""
        return SensorDeviceClass.TEMPERATURE


class PlantCurrentHumidity(PlantCurrentStatus):
    """Entity class for the current humidity meter"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_name = (
            f"{config.data[FLOW_PLANT_INFO][ATTR_NAME]} {READING_HUMIDITY}"
        )
        self._attr_unique_id = f"{config.entry_id}-current-humidity"
        self._attr_icon = "mdi:water-percent"
        self._external_sensor = config.data[FLOW_PLANT_INFO].get(FLOW_SENSOR_HUMIDITY)
        self._attr_native_unit_of_measurement = PERCENTAGE

        super().__init__(hass, config, plantdevice)

    def sensor_type(self) -> str | None:
        """Logical sensor type key used for decimals config."""
        return "humidity"

    @property
    def device_class(self) -> str:
        """Device class"""
        return SensorDeviceClass.HUMIDITY


class PlantCurrentCO2(PlantCurrentStatus):
    """Entity class for the current CO2 meter"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_name = f"{config.data[FLOW_PLANT_INFO][ATTR_NAME]} {READING_CO2}"
        self._attr_unique_id = f"{config.entry_id}-current-CO2"
        self._attr_icon = "mdi:molecule-co2"
        self._external_sensor = config.data[FLOW_PLANT_INFO].get(FLOW_SENSOR_CO2)
        self._attr_native_unit_of_measurement = "ppm"

        super().__init__(hass, config, plantdevice)

    def sensor_type(self) -> str | None:
        """Logical sensor type key used for decimals config."""
        return "CO2"

    @property
    def device_class(self) -> str:
        """Device class"""
        return SensorDeviceClass.CO2


class PlantCurrentPpfd(PlantCurrentStatus):
    """Entity reporting current PPFD calculated from LX"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_name = f"{config.data[FLOW_PLANT_INFO][ATTR_NAME]} {READING_PPFD}"
        self._attr_unique_id = f"{config.entry_id}-current-ppfd"
        self._attr_unit_of_measurement = UNIT_PPFD
        self._attr_native_unit_of_measurement = UNIT_PPFD
        self._plant = plantdevice
        self._external_sensor = self._plant.sensor_illuminance.entity_id if self._plant.sensor_illuminance else None
        self._attr_icon = ICON_PPFD
        super().__init__(hass, config, plantdevice)
        self._follow_unit = False

        # Setze Wert bei Neuerstellung zurück
        if config.data[FLOW_PLANT_INFO].get(ATTR_IS_NEW_PLANT, False):
            self._attr_native_value = None

    @property
    def device_class(self) -> str:
        """Device class"""
        return None

    @property
    def entity_category(self) -> str:
        """The entity category"""
        return EntityCategory.DIAGNOSTIC

    @property
    def entity_registry_visible_default(self) -> str:
        return False

    def ppfd(self, value: float | int | str) -> float | str:
        """
        Returns a calculated PPFD-value from the lx-value

        See https://community.home-assistant.io/t/light-accumulation-for-xiaomi-flower-sensor/111180/3
        https://www.apogeeinstruments.com/conversion-ppfd-to-lux/
        μmol/m²/s
        """
        if value is not None and value != STATE_UNAVAILABLE and value != STATE_UNKNOWN:
            try:
                value = float(value) * DEFAULT_LUX_TO_PPFD / 1000000
                # Apply rounding for PPFD (should have 0 decimal places)
                if hasattr(self, "_plant") and hasattr(self._plant, "decimals_for"):
                    decimals = self._plant.decimals_for("ppfd")
                    value = round(value, decimals)
            except (ValueError, TypeError):
                value = None
        else:
            value = None

        return value

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        
        # Make sure we're tracking the illuminance sensor
        if self._plant.sensor_illuminance:
            self.replace_external_sensor(self._plant.sensor_illuminance.entity_id)

    async def async_update(self) -> None:
        """Run on every update to allow for changes from the GUI and service call"""
        if not self.hass.states.get(self.entity_id):
            return
        if self._plant.sensor_illuminance and self._external_sensor != self._plant.sensor_illuminance.entity_id:
            self.replace_external_sensor(self._plant.sensor_illuminance.entity_id)
        if self._external_sensor:
            external_sensor = self.hass.states.get(self._external_sensor)
            if external_sensor:
                self._attr_native_value = self.ppfd(external_sensor.state)
                # Apply rounding after calculation
                if self._attr_native_value is not None:
                    self._attr_native_value = self._plant._apply_rounding("ppfd", self._attr_native_value)
            else:
                self._attr_native_value = None
        else:
            self._attr_native_value = None

    @callback
    def state_changed(self, entity_id: str, new_state: str) -> None:
        """Run on every update to allow for changes from the GUI and service call"""
        if not self.hass.states.get(self.entity_id):
            return
        if self._plant.sensor_illuminance and self._external_sensor != self._plant.sensor_illuminance.entity_id:
            self.replace_external_sensor(self._plant.sensor_illuminance.entity_id)
        if self._external_sensor:
            external_sensor = self.hass.states.get(self._external_sensor)
            if external_sensor:
                self._attr_native_value = self.ppfd(external_sensor.state)
                # Apply rounding after calculation
                if self._attr_native_value is not None:
                    self._attr_native_value = self._plant._apply_rounding("ppfd", self._attr_native_value)
            else:
                self._attr_native_value = None
        else:
            self._attr_native_value = None


class PlantTotalLightIntegral(IntegrationSensor):
    """Entity class to calculate PPFD from LX"""

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        illuminance_ppfd_sensor: Entity,
    ) -> None:
        """Initialize the sensor"""
        super().__init__(
            hass,
            integration_method=METHOD_TRAPEZOIDAL,
            name=f"{config.data[FLOW_PLANT_INFO][ATTR_NAME]} Total {READING_PPFD} Integral",
            round_digits=0,  # Use 0 decimal places for integral values
            source_entity=illuminance_ppfd_sensor.entity_id,
            unique_id=f"{config.entry_id}-ppfd-integral",
            unit_prefix=None,
            unit_time=UnitOfTime.SECONDS,
        )
        self._unit_of_measurement = UNIT_PPFD

    def _unit(self, source_unit: str) -> str:
        """Override unit"""
        return self._unit_of_measurement


class PlantDailyLightIntegral(UtilityMeterSensor):
    """Entity class to calculate Daily Light Integral from PPDF"""

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        illuminance_integration_sensor: Entity,
    ) -> None:
        """Initialize the sensor"""
        # Prepare parameters for UtilityMeterSensor
        params = {
            "cron_pattern": None,
            "delta_values": None,
            "hass": hass,
            "meter_offset": timedelta(seconds=0),
            "meter_type": DAILY,
            "name": f"{config.data[FLOW_PLANT_INFO][ATTR_NAME]} {READING_DLI}",
            "net_consumption": None,
            "parent_meter": config.entry_id,
            "periodically_resetting": True,
            "sensor_always_available": True,
            "source_entity": illuminance_integration_sensor.entity_id,
            "suggested_entity_id": None,
            "tariff_entity": None,
            "tariff": None,
            "unique_id": f"{config.entry_id}-dli",
        }
        
        # Call the parent constructor with all parameters
        super().__init__(**params)

        self._unit_of_measurement = UNIT_DLI


class PlantCurrentPh(PlantCurrentStatus):
    """Entity class for the current pH meter"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_name = (
            f"{config.data[FLOW_PLANT_INFO][ATTR_NAME]} {READING_PH}"
        )
        self._attr_unique_id = f"{config.entry_id}-current-ph"
        self._attr_icon = ICON_PH
        self._external_sensor = config.data[FLOW_PLANT_INFO].get(
            FLOW_SENSOR_PH
        )
        self._attr_native_unit_of_measurement = None  # pH hat keine Einheit
        self._default_state = 7.0  # Neutraler pH-Wert als Default

        super().__init__(hass, config, plantdevice)

    def sensor_type(self) -> str | None:
        """Logical sensor type key used for decimals config."""
        return "ph"

    @property
    def device_class(self) -> str:
        """Device class"""
        return "ph"  # Verwende unsere eigene Device Class

    async def set_manual_value(self, value: float) -> None:
        """Set a manual pH measurement (0-14)."""
        try:
            if value is None:
                return
            # clamp plausible pH range
            if value < 0:
                value = 0
            if value > 14:
                value = 14
            self._attr_native_value = float(value)
            self.async_write_ha_state()
        except (TypeError, ValueError):
            self._attr_native_value = None  # Set to None on error
