"""Meter entities for the plant integration"""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
import random
from statistics import quantiles
from typing import Any

from homeassistant.components.integration.const import METHOD_TRAPEZOIDAL
from homeassistant.components.integration.sensor import IntegrationSensor
from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
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
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util
from homeassistant.components.recorder import history, get_instance

from . import SETUP_DUMMY_SENSORS
from .const import (
    ATTR_CONDUCTIVITY,
    ATTR_DLI,
    ATTR_MOISTURE,
    ATTR_PLANT,
    ATTR_SENSORS,
    DATA_UPDATED,
    DEFAULT_LUX_TO_PPFD,
    DOMAIN,
    DOMAIN_SENSOR,
    FLOW_PLANT_INFO,
    FLOW_SENSOR_CONDUCTIVITY,
    FLOW_SENSOR_HUMIDITY,
    FLOW_SENSOR_ILLUMINANCE,
    FLOW_SENSOR_MOISTURE,
    FLOW_SENSOR_TEMPERATURE,
    ICON_CONDUCTIVITY,
    ICON_DLI,
    ICON_HUMIDITY,
    ICON_ILLUMINANCE,
    ICON_MOISTURE,
    ICON_PPFD,
    ICON_TEMPERATURE,
    READING_CONDUCTIVITY,
    READING_DLI,
    READING_HUMIDITY,
    READING_ILLUMINANCE,
    READING_MOISTURE,
    READING_PPFD,
    READING_TEMPERATURE,
    UNIT_CONDUCTIVITY,
    UNIT_DLI,
    UNIT_PPFD,
    DEVICE_TYPE_CYCLE,
    DEFAULT_AGGREGATIONS,
    ATTR_IS_NEW_PLANT,
    ATTR_NORMALIZE_MOISTURE,
    ATTR_NORMALIZE_WINDOW,
    ATTR_NORMALIZE_PERCENTILE,
    DEFAULT_NORMALIZE_WINDOW,
    DEFAULT_NORMALIZE_PERCENTILE,
    ICON_WATER_CONSUMPTION,
    UNIT_VOLUME,
    READING_MOISTURE_CONSUMPTION,
    READING_FERTILIZER_CONSUMPTION,
    ICON_FERTILIZER_CONSUMPTION,
)

_LOGGER = logging.getLogger(__name__)
async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up Plant Sensors from a config entry."""
    plant = hass.data[DOMAIN][entry.entry_id][ATTR_PLANT]

    # Erstelle die Standard-Sensoren für Plants
    if plant.device_type != DEVICE_TYPE_CYCLE:
        # Standard Sensoren erstellen
        pcurb = PlantCurrentIlluminance(hass, entry, plant)
        pcurc = PlantCurrentConductivity(hass, entry, plant)
        pcurm = PlantCurrentMoisture(hass, entry, plant)
        pcurt = PlantCurrentTemperature(hass, entry, plant)
        pcurh = PlantCurrentHumidity(hass, entry, plant)
        
        plant_sensors = [pcurb, pcurc, pcurm, pcurt, pcurh]
        
        # Erst die Entities zu HA hinzufügen
        async_add_entities(plant_sensors)
        hass.data[DOMAIN][entry.entry_id][ATTR_SENSORS] = plant_sensors
        
        # Dann die Sensoren der Plant hinzufügen
        plant.add_sensors(
            temperature=pcurt,
            moisture=pcurm,
            conductivity=pcurc,
            illuminance=pcurb,
            humidity=pcurh,
        )

        # Jetzt erst die externen Sensoren zuweisen
        if entry.data[FLOW_PLANT_INFO].get(FLOW_SENSOR_ILLUMINANCE):
            pcurb.replace_external_sensor(entry.data[FLOW_PLANT_INFO][FLOW_SENSOR_ILLUMINANCE])
        if entry.data[FLOW_PLANT_INFO].get(FLOW_SENSOR_CONDUCTIVITY):
            pcurc.replace_external_sensor(entry.data[FLOW_PLANT_INFO][FLOW_SENSOR_CONDUCTIVITY])
        if entry.data[FLOW_PLANT_INFO].get(FLOW_SENSOR_MOISTURE):
            pcurm.replace_external_sensor(entry.data[FLOW_PLANT_INFO][FLOW_SENSOR_MOISTURE])
        if entry.data[FLOW_PLANT_INFO].get(FLOW_SENSOR_TEMPERATURE):
            pcurt.replace_external_sensor(entry.data[FLOW_PLANT_INFO][FLOW_SENSOR_TEMPERATURE])
        if entry.data[FLOW_PLANT_INFO].get(FLOW_SENSOR_HUMIDITY):
            pcurh.replace_external_sensor(entry.data[FLOW_PLANT_INFO][FLOW_SENSOR_HUMIDITY])

        # PPFD und DLI für Plants
        pcurppfd = PlantCurrentPpfd(hass, entry, plant)
        async_add_entities([pcurppfd])

        pintegral = PlantTotalLightIntegral(hass, entry, pcurppfd, plant)
        async_add_entities([pintegral], update_before_add=True)

        # Consumption Sensoren erstellen
        moisture_consumption = None
        fertilizer_consumption = None

        if plant.sensor_moisture:
            moisture_consumption = PlantCurrentMoistureConsumption(
                hass,
                entry,
                plant,
            )
            async_add_entities([moisture_consumption])

        if plant.sensor_conductivity:
            fertilizer_consumption = PlantCurrentFertilizerConsumption(
                hass,
                entry,
                plant,
            )
            async_add_entities([fertilizer_consumption])

        # Jetzt können wir add_calculations aufrufen
        plant.add_calculations(pcurppfd, pintegral, moisture_consumption, fertilizer_consumption)

        pdli = PlantDailyLightIntegral(hass, entry, pintegral, plant)
        async_add_entities(new_entities=[pdli], update_before_add=True)

        plant.add_dli(dli=pdli)

    # Erstelle die Median-Sensoren für Cycles
    if plant.device_type == DEVICE_TYPE_CYCLE:
        cycle_sensors = []
        
        # Erstelle die Basis-Sensoren
        for sensor_type in ["temperature", "moisture", "conductivity", "illuminance", "humidity"]:
            sensor = CycleMedianSensor(hass, entry, plant, sensor_type)
            cycle_sensors.append(sensor)
            
        # Erstelle die berechneten Sensoren
        for sensor_type in ["ppfd", "dli", "total_integral", "moisture_consumption", "fertilizer_consumption"]:
            sensor = CycleMedianSensor(hass, entry, plant, sensor_type)
            cycle_sensors.append(sensor)
        
        # Füge alle Sensoren zu Home Assistant hinzu
        async_add_entities(cycle_sensors)
        
        # Füge die Sensoren der Plant hinzu
        plant.add_sensors(
            temperature=cycle_sensors[0],
            moisture=cycle_sensors[1],
            conductivity=cycle_sensors[2],
            illuminance=cycle_sensors[3],
            humidity=cycle_sensors[4],
        )
        
        # Füge die berechneten Sensoren hinzu
        plant.add_calculations(
            ppfd=cycle_sensors[5],
            total_integral=cycle_sensors[7],
            moisture_consumption=cycle_sensors[8],
            fertilizer_consumption=cycle_sensors[9]
        )
        plant.add_dli(dli=cycle_sensors[6])

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return True


class PlantCurrentStatus(RestoreSensor):
    """Parent class for the meter classes below"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the Plant component."""
        self._hass = hass
        self._config = config
        self._default_state = None
        self._plant = plantdevice
        self._tracker = []
        self._follow_external = True
        self._attr_has_entity_name = False
        # self._conf_check_days = self._plant.check_days
        self.entity_id = async_generate_entity_id(
            f"{DOMAIN}.{{}}", self.name, current_ids={}
        )
        if (
            not self._attr_native_value
            or self._attr_native_value == STATE_UNKNOWN
            or self._attr_native_value == STATE_UNAVAILABLE
        ):
            _LOGGER.debug(
                "Unknown native value for %s, setting to default: %s",
                self.entity_id,
                self._default_state,
            )
            self._attr_native_value = self._default_state

    @property
    def state_class(self):
        return SensorStateClass.MEASUREMENT

    @property
    def device_info(self) -> dict:
        """Device info for devices"""
        return {
            "identifiers": {(DOMAIN, self._plant.unique_id)},
        }

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
        self.async_track_entity(self.entity_id)
        self.async_track_entity(self.external_sensor)

        self.async_write_ha_state()

    def async_track_entity(self, entity_id: str) -> None:
        """Track state_changed of certain entities"""
        if entity_id and entity_id not in self._tracker:
            async_track_state_change_event(
                self._hass,
                list([entity_id]),
                self._state_changed_event,
            )
            self._tracker.append(entity_id)

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()

        # We do not restore the state for these.
        # They are read from the external sensor anyway
        self._attr_native_value = None
        if state:
            if "external_sensor" in state.attributes:
                self.replace_external_sensor(state.attributes["external_sensor"])
        self.async_track_entity(self.entity_id)
        if self.external_sensor:
            self.async_track_entity(self.external_sensor)

        async_dispatcher_connect(
            self._hass, DATA_UPDATED, self._schedule_immediate_update
        )

    async def async_update(self) -> None:
        """Set state and unit to the parent sensor state and unit"""
        if self.external_sensor:
            try:
                self._attr_native_value = float(
                    self._hass.states.get(self.external_sensor).state
                )
                if (
                    ATTR_UNIT_OF_MEASUREMENT
                    in self._hass.states.get(self.external_sensor).attributes
                ):
                    self._attr_native_unit_of_measurement = self._hass.states.get(
                        self.external_sensor
                    ).attributes[ATTR_UNIT_OF_MEASUREMENT]
            except AttributeError:
                _LOGGER.debug(
                    "Unknown external sensor for %s: %s, setting to default: %s",
                    self.entity_id,
                    self.external_sensor,
                    self._default_state,
                )
                self._attr_native_value = self._default_state
            except ValueError:
                _LOGGER.debug(
                    "Unknown external value for %s: %s = %s, setting to default: %s",
                    self.entity_id,
                    self.external_sensor,
                    self._hass.states.get(self.external_sensor).state,
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
        if entity_id == self.entity_id:
            current_attrs = self.hass.states.get(self.entity_id).attributes
            if current_attrs.get("external_sensor") != self.external_sensor:
                self.replace_external_sensor(current_attrs.get("external_sensor"))

            if (
                ATTR_ICON in new_state.attributes
                and self.icon != new_state.attributes[ATTR_ICON]
            ):
                self._attr_icon = new_state.attributes[ATTR_ICON]

        if (
            self.external_sensor
            and new_state
            and new_state.state != STATE_UNKNOWN
            and new_state.state != STATE_UNAVAILABLE
        ):
            self._attr_native_value = new_state.state
            if ATTR_UNIT_OF_MEASUREMENT in new_state.attributes:
                self._attr_native_unit_of_measurement = new_state.attributes[
                    ATTR_UNIT_OF_MEASUREMENT
                ]
        else:
            self._attr_native_value = self._default_state


class PlantCurrentIlluminance(PlantCurrentStatus):
    """Entity class for the current illuminance meter"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_name = f"{plantdevice.name} {READING_ILLUMINANCE}"
        self._attr_unique_id = f"{config.entry_id}-current-illuminance"
        self._attr_has_entity_name = False
        self._attr_icon = ICON_ILLUMINANCE
        self._external_sensor = config.data[FLOW_PLANT_INFO].get(
            FLOW_SENSOR_ILLUMINANCE
        )
        self._attr_native_unit_of_measurement = LIGHT_LUX
        super().__init__(hass, config, plantdevice)

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
        self._attr_name = f"{plantdevice.name} {READING_CONDUCTIVITY}"
        self._attr_unique_id = f"{config.entry_id}-current-conductivity"
        self._attr_has_entity_name = False
        self._external_sensor = config.data[FLOW_PLANT_INFO].get(FLOW_SENSOR_CONDUCTIVITY)
        self._attr_icon = ICON_CONDUCTIVITY
        self._attr_native_unit_of_measurement = UnitOfConductivity.MICROSIEMENS_PER_CM
        self._raw_value = None
        
        # Lese Normalisierungseinstellungen aus der Config
        self._normalize = config.data[FLOW_PLANT_INFO].get(ATTR_NORMALIZE_MOISTURE, False)
        
        super().__init__(hass, config, plantdevice)

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional sensor attributes."""
        attributes = super().extra_state_attributes or {}
        
        if self._normalize:
            moisture_sensor = self._plant.sensor_moisture
            attributes.update({
                "conductivity_normalization": {
                    "enabled": True,
                    "raw_value": self._raw_value,
                    "factor": round(moisture_sensor._normalize_factor, 2) if hasattr(moisture_sensor, '_normalize_factor') else None,
                }
            })
        
        return attributes

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        # Erzwinge sofortige Aktualisierung der Attribute
        self.async_write_ha_state()

    async def async_update(self) -> None:
        """Update the sensor."""
        await super().async_update()
        
        # Speichere den Rohwert vor der Normalisierung
        if self._attr_native_value is not None:
            self._raw_value = self._attr_native_value
        
        # Normalisiere den Wert wenn der Moisture Sensor normalisiert wird
        if self._normalize and self._attr_native_value is not None:
            moisture_sensor = self._plant.sensor_moisture
            if (hasattr(moisture_sensor, '_normalize_factor') and
                moisture_sensor._normalize_factor is not None):
                try:
                    normalized = float(self._attr_native_value) * moisture_sensor._normalize_factor
                    self._attr_native_value = round(normalized, 1)
                except (ValueError, TypeError):
                    pass

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
        self._attr_name = f"{plantdevice.name} {READING_MOISTURE}"
        self._attr_unique_id = f"{config.entry_id}-current-moisture"
        self._attr_has_entity_name = False
        self._external_sensor = config.data[FLOW_PLANT_INFO].get(FLOW_SENSOR_MOISTURE)
        self._attr_icon = ICON_MOISTURE
        self._attr_native_unit_of_measurement = PERCENTAGE

        self._raw_value = None  # Initialisiere _raw_value
        self._normalize_factor = None  # Initialisiere normalize_factor
        super().__init__(hass, config, plantdevice)

        self._normalize = config.data[FLOW_PLANT_INFO].get(ATTR_NORMALIZE_MOISTURE, False)
        self._normalize_window = config.data[FLOW_PLANT_INFO].get(
            ATTR_NORMALIZE_WINDOW, DEFAULT_NORMALIZE_WINDOW
        )
        self._normalize_percentile = config.data[FLOW_PLANT_INFO].get(
            ATTR_NORMALIZE_PERCENTILE, DEFAULT_NORMALIZE_PERCENTILE
        )
        self._max_moisture = None
        self._last_normalize_update = None

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        
        # Initialisiere Normalisierung beim Start
        if self._normalize:
            self._last_normalize_update = None  # Force update
            await self._update_normalization()
            
            # Wenn es eine Neuerstellung ist, aktualisiere sofort
            if self._config.data[FLOW_PLANT_INFO].get(ATTR_IS_NEW_PLANT, False):
                _LOGGER.debug("New plant created, updating normalization immediately")
                await self._update_normalization()

    async def _update_normalization(self) -> None:
        """Update the normalization max value"""
        if not self._normalize or not self._external_sensor:
            return

        now = dt_util.utcnow()
        
        # Aktualisiere nur alle 5 Minuten, außer bei None (Erststart/Neuerstellung)
        if (self._last_normalize_update is not None and 
            now - self._last_normalize_update < timedelta(minutes=5)):
            return

        # Hole historische Daten
        start_time = now - timedelta(days=self._normalize_window)
        
        # Korrigierter Aufruf der history API mit dem richtigen Executor
        recorder = get_instance(self._hass)
        history_list = await recorder.async_add_executor_job(
            history.state_changes_during_period,
            self._hass,
            start_time,
            now,
            self._external_sensor
        )

        if not history_list or self._external_sensor not in history_list:
            return

        # Extrahiere numerische Werte
        values = []
        for state in history_list[self._external_sensor]:
            try:
                if state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                    values.append(float(state.state))
            except (ValueError, TypeError):
                continue

        if values:
            # Berechne das Perzentil
            percentile_index = int(len(values) * self._normalize_percentile / 100)
            sorted_values = sorted(values)
            self._max_moisture = sorted_values[percentile_index]
            self._normalize_factor = 100 / self._max_moisture  # Exakter Wert für Berechnungen
            self._last_normalize_update = now
            _LOGGER.debug(
                "Updated moisture normalization: max=%s, factor=%s (from %s values)",
                self._max_moisture,
                round(self._normalize_factor, 2),  # Gerundeter Wert nur für Log
                len(values)
            )

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional sensor attributes."""
        attributes = super().extra_state_attributes or {}
        
        if self._normalize:
            attributes.update({
                "moisture_normalization": {
                    "enabled": True,
                    "window_days": self._normalize_window,
                    "percentile": self._normalize_percentile,
                    "current_max": self._max_moisture,
                    "raw_value": self._raw_value if hasattr(self, '_raw_value') else None,
                }
            })
        
        return attributes

    async def async_update(self) -> None:
        """Update the sensor."""
        await super().async_update()
        
        # Speichere den Rohwert vor der Normalisierung
        if self._attr_native_value is not None:
            self._raw_value = self._attr_native_value
        
        # Aktualisiere Normalisierung
        await self._update_normalization()
        
        # Normalisiere den Wert wenn nötig
        if (self._normalize and self._max_moisture and 
            self._attr_native_value is not None):
            try:
                normalized = min(100, (float(self._attr_native_value) / 
                                     self._max_moisture) * 100)
                self._attr_native_value = round(normalized, 1)
            except (ValueError, TypeError):
                pass

    @property
    def device_class(self) -> str:
        """Device class"""
        return ATTR_MOISTURE


class PlantCurrentTemperature(PlantCurrentStatus):
    """Entity class for the current temperature meter"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_name = f"{plantdevice.name} {READING_TEMPERATURE}"
        self._attr_unique_id = f"{config.entry_id}-current-temperature"
        self._attr_has_entity_name = False
        self._external_sensor = config.data[FLOW_PLANT_INFO].get(
            FLOW_SENSOR_TEMPERATURE
        )
        self._attr_icon = ICON_TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        super().__init__(hass, config, plantdevice)

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
        self._attr_name = f"{plantdevice.name} {READING_HUMIDITY}"
        self._attr_unique_id = f"{config.entry_id}-current-humidity"
        self._attr_has_entity_name = False
        self._external_sensor = config.data[FLOW_PLANT_INFO].get(FLOW_SENSOR_HUMIDITY)
        self._attr_icon = ICON_HUMIDITY
        self._attr_native_unit_of_measurement = PERCENTAGE
        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self) -> str:
        """Device class"""
        return SensorDeviceClass.HUMIDITY


class PlantCurrentPpfd(PlantCurrentStatus):
    """Entity reporting current PPFD calculated from LX"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_name = f"{plantdevice.name} {READING_PPFD}"
        self._attr_unique_id = f"{config.entry_id}-current-ppfd"
        self._attr_has_entity_name = False
        self._attr_unit_of_measurement = UNIT_PPFD
        self._attr_native_unit_of_measurement = UNIT_PPFD
        self._plant = plantdevice
        self._external_sensor = self._plant.sensor_illuminance.entity_id
        self._attr_icon = ICON_PPFD
        super().__init__(hass, config, plantdevice)
        self._follow_unit = False
        self.entity_id = async_generate_entity_id(
            f"{DOMAIN_SENSOR}.{{}}", self.name, current_ids={}
        )
        
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
            value = float(value) * DEFAULT_LUX_TO_PPFD / 1000000
        else:
            value = None

        return value

    async def async_update(self) -> None:
        """Run on every update to allow for changes from the GUI and service call"""
        if not self.hass.states.get(self.entity_id):
            return
        if self.external_sensor != self._plant.sensor_illuminance.entity_id:
            self.replace_external_sensor(self._plant.sensor_illuminance.entity_id)
        if self.external_sensor:
            external_sensor = self.hass.states.get(self.external_sensor)
            if external_sensor:
                self._attr_native_value = self.ppfd(external_sensor.state)
            else:
                self._attr_native_value = None
        else:
            self._attr_native_value = None

    @callback
    def state_changed(self, entity_id: str, new_state: str) -> None:
        """Run on every update to allow for changes from the GUI and service call"""
        if not self.hass.states.get(self.entity_id):
            return
        if self._external_sensor != self._plant.sensor_illuminance.entity_id:
            self.replace_external_sensor(self._plant.sensor_illuminance.entity_id)
        if self.external_sensor:
            external_sensor = self.hass.states.get(self.external_sensor)
            if external_sensor:
                self._attr_native_value = self.ppfd(external_sensor.state)
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
        plantdevice: Entity,
    ) -> None:
        """Initialize the sensor"""
        super().__init__(
            integration_method=METHOD_TRAPEZOIDAL,
            name=f"{plantdevice.name} Total {READING_PPFD} Integral",
            round_digits=2,
            source_entity=illuminance_ppfd_sensor.entity_id,
            unique_id=f"{config.entry_id}-ppfd-integral",
            unit_prefix=None,
            unit_time=UnitOfTime.SECONDS,
            max_sub_interval=None,
        )
        self._attr_has_entity_name = False
        self._unit_of_measurement = UNIT_DLI
        self._attr_icon = ICON_DLI
        self.entity_id = async_generate_entity_id(
            f"{DOMAIN_SENSOR}.{{}}", self.name, current_ids={}
        )
        self._plant = plantdevice
        
        # Setze Wert bei Neuerstellung zurück
        if config.data[FLOW_PLANT_INFO].get(ATTR_IS_NEW_PLANT, False):
            self._attr_native_value = None

    @property
    def entity_category(self) -> str:
        """The entity category"""
        return EntityCategory.DIAGNOSTIC

    @property
    def device_info(self) -> dict:
        """Device info for devices"""
        return {
            "identifiers": {(DOMAIN, self._plant.unique_id)},
        }

    @property
    def entity_registry_visible_default(self) -> str:
        return False

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
        plantdevice: Entity,
    ) -> None:
        """Initialize the sensor"""
        self._attr_has_entity_name = False
        self._attr_native_unit_of_measurement = UNIT_DLI
        super().__init__(
            cron_pattern=None,
            delta_values=None,
            meter_offset=timedelta(seconds=0),
            meter_type=DAILY,
            name=f"{plantdevice.name} {READING_DLI}",
            net_consumption=None,
            parent_meter=config.entry_id,
            source_entity=illuminance_integration_sensor.entity_id,
            tariff_entity=None,
            tariff=None,
            unique_id=f"{config.entry_id}-dli",
            sensor_always_available=True,
            suggested_entity_id=None,
            periodically_resetting=True,
        )
        
        self.entity_id = async_generate_entity_id(
            f"{DOMAIN_SENSOR}.{{}}", self.name, current_ids={}
        )
        self._attr_icon = ICON_DLI
        self._plant = plantdevice
        
        # Setze Wert bei Neuerstellung zurück
        if config.data[FLOW_PLANT_INFO].get(ATTR_IS_NEW_PLANT, False):
            self._attr_native_value = None

    @property
    def device_class(self) -> str:
        return ATTR_DLI

    @property
    def device_info(self) -> dict:
        """Device info for devices"""
        return {
            "identifiers": {(DOMAIN, self._plant.unique_id)},
        }


class PlantDummyStatus(SensorEntity):
    """Simple dummy sensors. Parent class"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the dummy sensor."""
        self._config = config
        self._default_state = STATE_UNKNOWN
        self.entity_id = async_generate_entity_id(
            f"{DOMAIN}.{{}}", self.name, current_ids={}
        )
        self._plant = plantdevice

        if not self._attr_native_value or self._attr_native_value == STATE_UNKNOWN:
            self._attr_native_value = self._default_state

    # @property
    # def device_info(self) -> dict:
    #     """Device info for devices"""
    #     return {
    #         "identifiers": {(DOMAIN, self._plant.unique_id)},
    #     }


class PlantDummyIlluminance(PlantDummyStatus):
    """Dummy sensor"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Init the dummy sensor"""
        self._attr_name = (
            f"Dummy {plantdevice.name} {READING_ILLUMINANCE}"
        )
        self._attr_unique_id = f"{config.entry_id}-dummy-illuminance"
        self._attr_icon = ICON_ILLUMINANCE
        self._attr_native_unit_of_measurement = LIGHT_LUX
        self._attr_native_value = random.randint(20, 50) * 1000

        super().__init__(hass, config, plantdevice)

    async def async_update(self) -> int:
        """Give out a dummy value"""
        if datetime.now().hour < 5:
            self._attr_native_value = random.randint(1, 10) * 100
        elif datetime.now().hour < 15:
            self._attr_native_value = random.randint(20, 50) * 1000
        else:
            self._attr_native_value = random.randint(1, 10) * 100

    @property
    def device_class(self) -> str:
        """Device class"""
        return SensorDeviceClass.ILLUMINANCE


class PlantDummyConductivity(PlantDummyStatus):
    """Dummy sensor"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Init the dummy sensor"""
        self._attr_name = (
            f"Dummy {plantdevice.name} {READING_CONDUCTIVITY}"
        )
        self._attr_unique_id = f"{config.entry_id}-dummy-conductivity"
        self._attr_icon = ICON_CONDUCTIVITY
        self._attr_native_unit_of_measurement = UNIT_CONDUCTIVITY
        self._attr_native_value = random.randint(40, 200) * 10

        super().__init__(hass, config, plantdevice)

    async def async_update(self) -> int:
        """Give out a dummy value"""
        self._attr_native_value = random.randint(40, 200) * 10

    @property
    def device_class(self) -> str:
        """Device class"""
        return ATTR_CONDUCTIVITY


class PlantDummyMoisture(PlantDummyStatus):
    """Dummy sensor"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Init the dummy sensor"""
        self._attr_name = (
            f"Dummy {plantdevice.name} {READING_MOISTURE}"
        )
        self._attr_unique_id = f"{config.entry_id}-dummy-moisture"
        self._attr_icon = ICON_MOISTURE
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_native_value = random.randint(10, 70)

        super().__init__(hass, config, plantdevice)

    async def async_update(self) -> None:
        """Give out a dummy value"""
        self._attr_native_value = random.randint(10, 70)

    @property
    def device_class(self) -> str:
        """Device class"""
        return ATTR_MOISTURE


class PlantDummyTemperature(PlantDummyStatus):
    """Dummy sensor"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Init the dummy sensor"""

        self._attr_name = (
            f"Dummy {plantdevice.name} {READING_TEMPERATURE}"
        )
        self._attr_unique_id = f"{config.entry_id}-dummy-temperature"
        self._attr_icon = ICON_TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_native_value = random.randint(15, 20)

        super().__init__(hass, config, plantdevice)

    async def async_update(self) -> int:
        """Give out a dummy value"""
        self._attr_native_value = random.randint(15, 20)

    @property
    def device_class(self) -> str:
        """Device class"""
        return SensorDeviceClass.TEMPERATURE


class PlantDummyHumidity(PlantDummyStatus):
    """Dummy sensor"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Init the dummy sensor"""
        self._attr_name = (
            f"Dummy {plantdevice.name} {READING_HUMIDITY}"
        )
        self._attr_unique_id = f"{config.entry_id}-dummy-humidity"
        self._attr_icon = ICON_HUMIDITY
        self._attr_native_unit_of_measurement = PERCENTAGE
        super().__init__(hass, config, plantdevice)
        self._attr_native_value = random.randint(25, 90)

    async def async_update(self) -> int:
        """Give out a dummy value"""
        test = random.randint(0, 100)
        if test > 50:
            self._attr_native_value = random.randint(25, 90)

    @property
    def device_class(self) -> str:
        """Device class"""
        return SensorDeviceClass.HUMIDITY


class CycleMedianSensor(SensorEntity):
    """Sensor that shows median values for a cycle."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        plant: PlantDevice,
        sensor_type: str,
    ) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self.config_entry = config_entry
        self.plant = plant
        self._sensor_type = sensor_type
        self._attr_has_entity_name = False
        self._attr_unique_id = f"{config_entry.entry_id}-median-{sensor_type}"
        
        # Name mit korrektem Reading für PPFD und Total Integral
        if sensor_type == "ppfd":
            self._attr_name = f"{plant.name} {READING_PPFD}"
        elif sensor_type == "total_integral":
            self._attr_name = f"{plant.name} Total {READING_PPFD} Integral"
        elif sensor_type == "humidity":
            self._attr_name = f"{plant.name} {READING_HUMIDITY}"
        elif sensor_type == "moisture":
            self._attr_name = f"{plant.name} {READING_MOISTURE}"
        elif sensor_type == "moisture_consumption":
            self._attr_name = f"{plant.name} {READING_MOISTURE_CONSUMPTION}"
        elif sensor_type == "fertilizer_consumption":
            self._attr_name = f"{plant.name} {READING_FERTILIZER_CONSUMPTION}"
        else:
            self._attr_name = f"{plant.name} {sensor_type}"

        # Setze Icon und Unit basierend auf Sensor-Typ
        if sensor_type == "temperature":
            self._attr_native_unit_of_measurement = self.hass.config.units.temperature_unit
            self._attr_icon = ICON_TEMPERATURE
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
        elif sensor_type == "moisture":
            self._attr_native_unit_of_measurement = PERCENTAGE
            self._attr_icon = ICON_MOISTURE
            self._attr_device_class = ATTR_MOISTURE
        elif sensor_type == "conductivity":
            self._attr_native_unit_of_measurement = UNIT_CONDUCTIVITY
            self._attr_icon = ICON_CONDUCTIVITY
            self._attr_device_class = ATTR_CONDUCTIVITY
        elif sensor_type == "illuminance":
            self._attr_native_unit_of_measurement = LIGHT_LUX
            self._attr_icon = ICON_ILLUMINANCE
            self._attr_device_class = SensorDeviceClass.ILLUMINANCE
        elif sensor_type == "humidity":
            self._attr_native_unit_of_measurement = PERCENTAGE
            self._attr_icon = ICON_HUMIDITY
            self._attr_device_class = SensorDeviceClass.HUMIDITY
        elif sensor_type == "ppfd":
            self._attr_native_unit_of_measurement = UNIT_PPFD
            self._attr_icon = ICON_PPFD
            self._attr_device_class = None
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        elif sensor_type == "dli":
            self._attr_native_unit_of_measurement = UNIT_DLI
            self._attr_icon = ICON_DLI
            self._attr_device_class = ATTR_DLI
        elif sensor_type == "total_integral":
            self._attr_native_unit_of_measurement = UNIT_DLI
            self._attr_icon = ICON_DLI
            self._attr_device_class = None
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        elif sensor_type == "moisture_consumption":
            self._attr_native_unit_of_measurement = UNIT_VOLUME
            self._attr_icon = ICON_WATER_CONSUMPTION
            self._attr_device_class = None
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        elif sensor_type == "fertilizer_consumption":
            self._attr_native_unit_of_measurement = UNIT_CONDUCTIVITY
            self._attr_icon = ICON_FERTILIZER_CONSUMPTION
            self._attr_device_class = None
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

        self._attr_native_value = None
        self._attr_should_poll = False

    @property
    def device_info(self) -> dict:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self.plant.unique_id)},
        }

    @property
    def state(self):
        """Return the median value."""
        return self.plant._median_sensors.get(self._sensor_type)

    @property
    def extra_state_attributes(self):
        """Return additional sensor attributes."""
        aggregation_method = self.plant._plant_info.get('aggregations', {}).get(
            self._sensor_type, DEFAULT_AGGREGATIONS[self._sensor_type]
        )
        return {
            "member_plants": self.plant._member_plants,
            "aggregation_method": aggregation_method
        }

    async def async_update(self) -> None:
        """Update the sensor."""
        self.plant._update_median_sensors()

    @property
    def should_poll(self) -> bool:
        """Return True as we want to poll for updates."""
        return True

    @property
    def state_class(self):
        return SensorStateClass.MEASUREMENT


class PlantCurrentMoistureConsumption(RestoreSensor):
    """Sensor to track water consumption based on moisture drop."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        plant_device: Entity,
    ) -> None:
        """Initialize the sensor."""
        self._hass = hass
        self._config = config
        self._plant = plant_device
        self._attr_name = f"{plant_device.name} {READING_MOISTURE_CONSUMPTION}"
        self._attr_unique_id = f"{config.entry_id}-moisture-consumption"
        self._attr_native_unit_of_measurement = UNIT_VOLUME
        self._attr_icon = ICON_WATER_CONSUMPTION
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._history = []
        self._last_update = None
        self._attr_native_value = 0

    @property
    def device_info(self) -> dict:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._plant.unique_id)},
        }

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional sensor attributes."""
        return {
            "pot_size": self._plant.pot_size.native_value if self._plant.pot_size else None,
            "water_capacity": self._plant.water_capacity.native_value if self._plant.water_capacity else None,
            "last_update": self._last_update,
        }

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        
        # Restore previous state
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            try:
                self._attr_native_value = float(last_state.state)
                if last_state.attributes.get("last_update"):
                    self._last_update = last_state.attributes["last_update"]
            except (TypeError, ValueError):
                self._attr_native_value = 0
        
        # Track moisture sensor changes
        async_track_state_change_event(
            self._hass,
            [self._plant.sensor_moisture.entity_id],
            self._state_changed_event,
        )

    @callback
    def _state_changed_event(self, event):
        """Handle moisture sensor state changes."""
        new_state = event.data.get("new_state")
        if not new_state or new_state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return

        try:
            current_value = float(new_state.state)
            current_time = dt_util.utcnow()
            
            # Add to history
            self._history.append((current_time, current_value))
            
            # Remove entries older than 24 hours
            cutoff_time = current_time - timedelta(hours=24)
            self._history = [(t, v) for t, v in self._history if t >= cutoff_time]
            
            if len(self._history) >= 2:
                # Calculate total moisture drop
                drops = []
                for i in range(1, len(self._history)):
                    if self._history[i][1] < self._history[i-1][1]:  # Only negative changes
                        drop = self._history[i-1][1] - self._history[i][1]
                        drops.append(drop)
                
                total_drop = sum(drops)
                
                # Convert moisture drop to volume
                if self._plant.pot_size and self._plant.water_capacity:
                    pot_size = self._plant.pot_size.native_value
                    water_capacity = self._plant.water_capacity.native_value / 100  # Convert from % to decimal
                    volume_drop = (total_drop / 100) * pot_size * water_capacity  # Convert from % to L
                    
                    self._attr_native_value = round(volume_drop, 2)
                    self._last_update = current_time.isoformat()
                    self.async_write_ha_state()
                
        except (TypeError, ValueError):
            pass


class PlantCurrentFertilizerConsumption(RestoreSensor):
    """Sensor to track fertilizer consumption based on conductivity drop."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        plant_device: Entity,
    ) -> None:
        """Initialize the sensor."""
        self._hass = hass
        self._config = config
        self._plant = plant_device
        self._attr_name = f"{plant_device.name} {READING_FERTILIZER_CONSUMPTION}"
        self._attr_unique_id = f"{config.entry_id}-fertilizer-consumption"
        self._attr_native_unit_of_measurement = UNIT_CONDUCTIVITY
        self._attr_icon = ICON_FERTILIZER_CONSUMPTION
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._history = []
        self._last_update = None
        self._attr_native_value = 0

    @property
    def device_info(self) -> dict:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._plant.unique_id)},
        }

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional sensor attributes."""
        return {
            "last_update": self._last_update,
        }

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        
        # Restore previous state
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            try:
                self._attr_native_value = float(last_state.state)
                if last_state.attributes.get("last_update"):
                    self._last_update = last_state.attributes["last_update"]
            except (TypeError, ValueError):
                self._attr_native_value = 0
        
        # Track conductivity sensor changes
        async_track_state_change_event(
            self._hass,
            [self._plant.sensor_conductivity.entity_id],
            self._state_changed_event,
        )

    @callback
    def _state_changed_event(self, event):
        """Handle conductivity sensor state changes."""
        new_state = event.data.get("new_state")
        if not new_state or new_state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return

        try:
            current_value = float(new_state.state)
            current_time = dt_util.utcnow()
            
            # Add to history
            self._history.append((current_time, current_value))
            
            # Remove entries older than 24 hours
            cutoff_time = current_time - timedelta(hours=24)
            self._history = [(t, v) for t, v in self._history if t >= cutoff_time]
            
            if len(self._history) >= 2:
                # Calculate total conductivity drop
                drops = []
                for i in range(1, len(self._history)):
                    if self._history[i][1] < self._history[i-1][1]:  # Only negative changes
                        drop = self._history[i-1][1] - self._history[i][1]
                        drops.append(drop)
                
                total_drop = sum(drops)
                self._attr_native_value = round(total_drop, 0)
                self._last_update = current_time.isoformat()
                self.async_write_ha_state()
                
        except (TypeError, ValueError):
            pass


