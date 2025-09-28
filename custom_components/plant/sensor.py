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
    STATE_OK,
    STATE_PROBLEM,
    UnitOfConductivity,
    UnitOfTemperature,
    UnitOfTime,
    Platform,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import (
    Entity,
    EntityCategory,
    async_generate_entity_id,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event, async_call_later
from homeassistant.util import dt as dt_util
from homeassistant.components.recorder import history, get_instance

# Import the sensor classes from plant_meters
from .plant_meters import (
    PlantCurrentIlluminance,
    PlantCurrentConductivity,
    PlantCurrentMoisture,
    PlantCurrentTemperature,
    PlantCurrentHumidity,
    PlantCurrentCO2,
    PlantCurrentPh,
    PlantCurrentPpfd,
    PlantTotalLightIntegral,
    PlantDailyLightIntegral,
)

from . import SETUP_DUMMY_SENSORS
from .const import (
    ATTR_CONDUCTIVITY,
    ATTR_DLI,
    ATTR_MOISTURE,
    ATTR_PLANT,
    ATTR_SENSORS,
    ATTR_PH,
    DATA_UPDATED,
    DEFAULT_LUX_TO_PPFD,
    DOMAIN,
    DOMAIN_SENSOR,
    FLOW_PLANT_INFO,
    FLOW_SENSOR_CONDUCTIVITY,
    FLOW_SENSOR_HUMIDITY,
    FLOW_SENSOR_CO2,
    FLOW_SENSOR_ILLUMINANCE,
    FLOW_SENSOR_MOISTURE,
    FLOW_SENSOR_TEMPERATURE,
    FLOW_SENSOR_POWER_CONSUMPTION,
    FLOW_SENSOR_PH,
    ICON_CONDUCTIVITY,
    ICON_DLI,
    ICON_HUMIDITY,
    ICON_CO2,
    ICON_ILLUMINANCE,
    ICON_MOISTURE,
    ICON_PPFD,
    ICON_TEMPERATURE,
    ICON_POWER_CONSUMPTION,
    ICON_PH,
    READING_CONDUCTIVITY,
    READING_DLI,
    READING_HUMIDITY,
    READING_CO2,
    READING_ILLUMINANCE,
    READING_MOISTURE,
    READING_PPFD,
    READING_TEMPERATURE,
    READING_POWER_CONSUMPTION,
    READING_PH,
    UNIT_CONDUCTIVITY,
    UNIT_DLI,
    UNIT_PPFD,
    DEVICE_TYPE_CYCLE,
    DEVICE_TYPE_PLANT,
    DEVICE_TYPE_TENT,
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
    ATTR_KWH_PRICE,
    DEFAULT_KWH_PRICE,
    READING_ENERGY_COST,
    ICON_ENERGY_COST,
    DEVICE_CLASS_PH,  # Importiere unsere eigene Device Class
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up Plant Sensors from a config entry."""
    plant = hass.data[DOMAIN][entry.entry_id][ATTR_PLANT]

    # Erstelle die Standard-Sensoren für Plants
    if plant.device_type == DEVICE_TYPE_PLANT:
        # Standard Sensoren erstellen
        pcurb = PlantCurrentIlluminance(hass, entry, plant)
        pcurc = PlantCurrentConductivity(hass, entry, plant)
        pcurm = PlantCurrentMoisture(hass, entry, plant)
        pcurt = PlantCurrentTemperature(hass, entry, plant)
        pcurh = PlantCurrentHumidity(hass, entry, plant)
        pcurCO2 = PlantCurrentCO2(hass, entry, plant)
        pcurph = PlantCurrentPh(hass, entry, plant)  # Neuer pH Sensor

        plant_sensors = [
            pcurb,
            pcurc,
            pcurm,
            pcurt,
            pcurh,
            pcurph,
            pcurCO2,
        ]  # pH Sensor hinzugefügt

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
            CO2=pcurCO2,
            power_consumption=None,  # Wird später gesetzt
            ph=pcurph,  # pH Sensor hinzugefügt
        )
        if entry.data[FLOW_PLANT_INFO].get(FLOW_SENSOR_HUMIDITY):
            pcurh.replace_external_sensor(
                entry.data[FLOW_PLANT_INFO][FLOW_SENSOR_HUMIDITY]
            )
        if entry.data[FLOW_PLANT_INFO].get(FLOW_SENSOR_CO2):
            pcurCO2.replace_external_sensor(
                entry.data[FLOW_PLANT_INFO][FLOW_SENSOR_CO2]
            )
        if entry.data[FLOW_PLANT_INFO].get(FLOW_SENSOR_PH):  # pH Sensor zuweisen
            pcurph.replace_external_sensor(entry.data[FLOW_PLANT_INFO][FLOW_SENSOR_PH])

        # PPFD und DLI für Plants
        pcurppfd = PlantCurrentPpfd(hass, entry, plant)
        async_add_entities([pcurppfd])

        pintegral = PlantTotalLightIntegral(hass, entry, pcurppfd, plant)
        async_add_entities([pintegral], update_before_add=True)

        # Consumption Sensoren erstellen
        moisture_consumption = None
        total_water_consumption = None  # Initialisiere Total Water
        fertilizer_consumption = None
        total_fertilizer_consumption = None  # Initialisiere Total Fertilizer

        if plant.sensor_moisture:
            moisture_consumption = PlantCurrentMoistureConsumption(
                hass,
                entry,
                plant,
            )
            async_add_entities([moisture_consumption])

            # Total Water Consumption hinzufügen
            total_water_consumption = PlantTotalWaterConsumption(
                hass,
                entry,
                plant,
                moisture_consumption,  # Pass the source sensor
            )
            async_add_entities([total_water_consumption])

        if plant.sensor_conductivity:
            fertilizer_consumption = PlantCurrentFertilizerConsumption(
                hass,
                entry,
                plant,
            )
            async_add_entities([fertilizer_consumption])

            # Total Fertilizer Consumption hinzufügen
            total_fertilizer_consumption = PlantTotalFertilizerConsumption(
                hass,
                entry,
                plant,
                fertilizer_consumption,  # Pass the source sensor
            )
            async_add_entities([total_fertilizer_consumption])

        # Jetzt können wir add_calculations aufrufen
        plant.add_calculations(
            ppfd=pcurppfd,
            total_integral=pintegral,
            moisture_consumption=moisture_consumption,
            fertilizer_consumption=fertilizer_consumption,
        )
        # Füge die Total Consumption Sensoren hinzu
        plant.total_water_consumption = total_water_consumption
        plant.total_fertilizer_consumption = total_fertilizer_consumption

        pdli = PlantDailyLightIntegral(hass, entry, pintegral)
        async_add_entities(new_entities=[pdli], update_before_add=True)

        plant.add_dli(dli=pdli)

        # Füge zuerst den Total Power Consumption Sensor hinzu
        total_power_consumption = PlantTotalPowerConsumption(hass, entry, plant)
        async_add_entities([total_power_consumption])

        # Weise den externen Sensor zu
        if entry.data[FLOW_PLANT_INFO].get(FLOW_SENSOR_POWER_CONSUMPTION):
            total_power_consumption.replace_external_sensor(
                entry.data[FLOW_PLANT_INFO][FLOW_SENSOR_POWER_CONSUMPTION]
            )

        # Dann erst den Current Power Consumption Sensor erstellen
        pcurp = PlantCurrentPowerConsumption(hass, entry, plant)
        async_add_entities([pcurp])

        # Jetzt können wir beide Sensoren der Plant hinzufügen
        plant.add_power_consumption_sensors(
            current=pcurp, total=total_power_consumption
        )

        # Füge Energiekosten-Sensor hinzu
        energy_cost = PlantEnergyCost(hass, entry, plant)
        plant.energy_cost = energy_cost
        async_add_entities([energy_cost])

    elif plant.device_type == DEVICE_TYPE_CYCLE:
        cycle_sensors = {}

        # Basis-Sensoren
        base_sensor_types = [
            "temperature",
            "moisture",
            "conductivity",
            "illuminance",
            "humidity",
            "ph",
            "CO2",
        ]
        for sensor_type in base_sensor_types:
            cycle_sensors[sensor_type] = CycleMedianSensor(
                hass, entry, plant, sensor_type
            )

        # Berechnete Sensoren
        calculated_sensor_types = [
            "ppfd",
            "dli",
            "total_integral",
            "moisture_consumption",
            "total_water_consumption",  # Füge Total Water hinzu
            "fertilizer_consumption",
            "total_fertilizer_consumption",  # Füge Total Fertilizer hinzu
            "power_consumption",
            "total_power_consumption",  # Füge Total Power hinzu
        ]
        for sensor_type in calculated_sensor_types:
            cycle_sensors[sensor_type] = CycleMedianSensor(
                hass, entry, plant, sensor_type
            )

        # Füge alle Sensoren zu Home Assistant hinzu
        async_add_entities(cycle_sensors.values())

        # Füge die Sensoren der Plant hinzu
        plant.add_sensors(
            temperature=cycle_sensors["temperature"],
            moisture=cycle_sensors["moisture"],
            conductivity=cycle_sensors["conductivity"],
            illuminance=cycle_sensors["illuminance"],
            humidity=cycle_sensors["humidity"],
            CO2=cycle_sensors["CO2"],
            power_consumption=cycle_sensors["power_consumption"],
            ph=cycle_sensors["ph"],
        )

        # Füge die berechneten Sensoren hinzu
        plant.add_calculations(
            ppfd=cycle_sensors["ppfd"],
            total_integral=cycle_sensors["total_integral"],
            moisture_consumption=cycle_sensors["moisture_consumption"],
            fertilizer_consumption=cycle_sensors["fertilizer_consumption"],
        )
        plant.add_dli(dli=cycle_sensors["dli"])

        # Total Consumption Sensoren
        plant.total_water_consumption = cycle_sensors["total_water_consumption"]
        plant.total_fertilizer_consumption = cycle_sensors[
            "total_fertilizer_consumption"
        ]

        # Power Consumption Sensoren
        plant.add_power_consumption_sensors(
            current=cycle_sensors["power_consumption"],
            total=cycle_sensors["total_power_consumption"],
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return True


class PlantCurrentStatus(RestoreSensor):
    """Base device for plants"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the Plant component."""
        super().__init__()
        self.hass = hass
        self._config = config
        self._default_state = None  # Use None instead of 0
        self._plant = plantdevice
        self._external_sensor = None  # Initialize _external_sensor attribute
        self.entity_id = async_generate_entity_id(
            f"{DOMAIN}.{{}}", self.name, current_ids={}
        )
        if not self._attr_native_value:
            self._attr_native_value = None  # Use None instead of 0 for default state

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
        """Return the state class."""
        return (
            self._attr_state_class
            if hasattr(self, "_attr_state_class")
            else SensorStateClass.MEASUREMENT
        )

    @property
    def device_class(self):
        """Return the device class."""
        return self._attr_device_class if hasattr(self, "_attr_device_class") else None

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
            }
            return attributes

    @property
    def external_sensor(self) -> str:
        """The external sensor we are tracking"""
        return self._external_sensor

    def replace_external_sensor(self, new_sensor: str | None) -> None:
        """Modify the external sensor"""
        _LOGGER.info("Setting %s external sensor to %s", self.entity_id, new_sensor)
        self._external_sensor = new_sensor
        if new_sensor:
            async_track_state_change_event(
                self.hass,
                [self._external_sensor],
                self._state_changed_event,
            )
            # Immediately update the sensor value after assigning a new external sensor
            self._update_from_external_sensor()

        self.async_write_ha_state()

    def _update_from_external_sensor(self) -> None:
        """Update the sensor value from the external sensor immediately."""
        if self._external_sensor:
            try:
                state = self.hass.states.get(self._external_sensor)
                if state and state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                    self._attr_native_value = self._apply_rounding(state.state)
                    # Only copy the unit of measurement if we don't have a specific device class that requires a specific unit
                    if (not hasattr(self, 'device_class') or (hasattr(self, 'device_class') and self.device_class is None)) and ATTR_UNIT_OF_MEASUREMENT in state.attributes:
                        self._attr_native_unit_of_measurement = state.attributes[
                            ATTR_UNIT_OF_MEASUREMENT
                        ]
                    self.async_write_ha_state()
                elif state:
                    # State is known but unavailable/unknown
                    self._attr_native_value = self._default_state
                    self.async_write_ha_state()
            except Exception as e:
                _LOGGER.debug(
                    "Error updating from external sensor %s for %s: %s",
                    self._external_sensor,
                    self.entity_id,
                    e,
                )
                self._attr_native_value = self._default_state
                self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()

        # We do not restore the state for these.
        # They are read from the external sensor anyway
        self._attr_native_value = None  # Use None instead of STATE_UNKNOWN
        if state:
            if "external_sensor" in state.attributes:
                self.replace_external_sensor(state.attributes["external_sensor"])
            # Fallback: if we have an _external_sensor from __init__ but no state attribute, 
            # make sure we're tracking it
            elif hasattr(self, '_external_sensor') and self._external_sensor:
                # Re-register the state change listener
                async_track_state_change_event(
                    self.hass,
                    [self._external_sensor],
                    self._state_changed_event,
                )

        async_dispatcher_connect(
            self.hass, DATA_UPDATED, self._schedule_immediate_update
        )

    @callback
    def _schedule_immediate_update(self):
        """Schedule an immediate update."""
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
            self._external_sensor
            and new_state
            and new_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE)
        ):
            self._attr_native_value = self._apply_rounding(new_state.state)
            # Only copy the unit of measurement if we don't have a specific device class that requires a specific unit
            if (not hasattr(self, 'device_class') or (hasattr(self, 'device_class') and self.device_class is None)) and ATTR_UNIT_OF_MEASUREMENT in new_state.attributes:
                self._attr_native_unit_of_measurement = new_state.attributes[
                    ATTR_UNIT_OF_MEASUREMENT
                ]
        else:
            # Only set to default if we don't have an external sensor
            if not self._external_sensor:
                self._attr_native_value = self._default_state

    async def async_update(self) -> None:
        """Set state and unit to the parent sensor state and unit"""
        if self._external_sensor:
            try:
                state = self.hass.states.get(self._external_sensor)
                if state and state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                    self._attr_native_value = self._apply_rounding(state.state)
                    # Only copy the unit of measurement if we don't have a specific device class that requires a specific unit
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
            # Only set to default if we don't have an external sensor
            if not self._external_sensor:
                self._attr_native_value = self._default_state


class PlantCurrentPpfd(PlantCurrentStatus):
    """Entity class to calculate PPFD from LX"""

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
        self._external_sensor = self._plant.sensor_illuminance.entity_id if self._plant.sensor_illuminance else None
        self._attr_icon = ICON_PPFD
        super().__init__(hass, config, plantdevice)
        self._follow_unit = False
        self.entity_id = async_generate_entity_id(
            f"{DOMAIN_SENSOR}.{{}}", self.name, current_ids={}
        )

        # Setze Wert bei Neuerstellung zurück
        if config.data[FLOW_PLANT_INFO].get(ATTR_IS_NEW_PLANT, False):
            self._attr_native_value = None

    def sensor_type(self) -> str | None:
        return "ppfd"

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

    def replace_external_sensor(self, new_sensor: str | None) -> None:
        """Modify the external sensor"""
        _LOGGER.info("Setting %s external sensor to %s", self.entity_id, new_sensor)
        self._external_sensor = new_sensor
        if new_sensor:
            async_track_state_change_event(
                self.hass,
                [self._external_sensor],
                self._state_changed_event,
            )
            # Immediately update the sensor value after assigning a new external sensor
            self._update_from_external_sensor()

        self.async_write_ha_state()

    def _update_from_external_sensor(self) -> None:
        """Update the sensor value from the external sensor immediately."""
        if self._external_sensor:
            try:
                state = self.hass.states.get(self._external_sensor)
                if state and state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                    # Calculate PPFD from illuminance
                    ppfd_value = self.ppfd(state.state)
                    self._attr_native_value = self._apply_rounding(ppfd_value)
                    self._attr_native_unit_of_measurement = UNIT_PPFD
                    self.async_write_ha_state()
                elif state:
                    # State is known but unavailable/unknown
                    self._attr_native_value = self._default_state
                    self.async_write_ha_state()
            except Exception as e:
                _LOGGER.debug(
                    "Error updating from external sensor %s for %s: %s",
                    self._external_sensor,
                    self.entity_id,
                    e,
                )
                self._attr_native_value = self._default_state
                self.async_write_ha_state()

    async def async_update(self) -> None:
        """Run on every update to allow for changes from the GUI and service call"""
        if not self.hass.states.get(self.entity_id):
            return
        if self._plant.sensor_illuminance and self._external_sensor != self._plant.sensor_illuminance.entity_id:
            self.replace_external_sensor(self._plant.sensor_illuminance.entity_id)
        if self._external_sensor:
            external_sensor = self.hass.states.get(self._external_sensor)
            if external_sensor:
                ppfd_value = self.ppfd(external_sensor.state)
                self._attr_native_value = self._apply_rounding(ppfd_value)
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
                ppfd_value = self.ppfd(external_sensor.state)
                self._attr_native_value = self._apply_rounding(ppfd_value)
            else:
                self._attr_native_value = None
        else:
            self._attr_native_value = None

    def _unit(self, source_unit: str) -> str:
        """Override unit"""
        return UNIT_PPFD  # Benutze immer PPFD als Einheit


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
        self._config = config  # Speichere config für späteren Zugriff
        super().__init__(
            hass,
            integration_method=METHOD_TRAPEZOIDAL,
            name=f"{plantdevice.name} Total {READING_PPFD} Integral",
            round_digits=0,  # Use 0 decimal places for integral values
            source_entity=illuminance_ppfd_sensor.entity_id,
            unique_id=f"{config.entry_id}-ppfd-integral",
            unit_prefix=None,
            unit_time=UnitOfTime.SECONDS,
            max_sub_interval=None,
        )
        self._attr_has_entity_name = False
        self._unit_of_measurement = UNIT_PPFD  # Benutze PPFD Einheit statt DLI
        self._attr_native_unit_of_measurement = UNIT_PPFD  # Setze auch native unit
        self._attr_icon = ICON_DLI
        self.entity_id = async_generate_entity_id(
            f"{DOMAIN_SENSOR}.{{}}", self.name, current_ids={}
        )
        self._plant = plantdevice
        self._attr_native_value = None  # Use None instead of 0
        self._history = []  # Initialize history for DLI calculations
        self._last_update = None

        # Setze Wert bei Neuerstellung zurück
        if config.data[FLOW_PLANT_INFO].get(ATTR_IS_NEW_PLANT, False):
            self._attr_native_value = None
            self._state = None  # Wichtig für IntegrationSensor

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
        return UNIT_PPFD  # Benutze immer PPFD als Einheit

    async def async_update(self):
        """Update the DLI calculation."""
        # Call the parent update method first to ensure we have the latest value
        # await super().async_update()
        
        try:
            # Get current time
            current_time = datetime.now()
            
            # Get current value
            current_value = self.native_value
            if current_value is None:
                return
                
            # Add current value to history
            self._history.append((current_time, current_value))
            
            # Entferne Einträge älter als 24 Stunden
            cutoff_time = current_time - timedelta(hours=24)
            self._history = [(t, v) for t, v in self._history if t >= cutoff_time]

            # Berechne DLI aus den letzten 24 Stunden
            if len(self._history) >= 2:
                # Konvertiere von mol/m²/s zu mol/m²/d (DLI)
                time_diff = (self._history[-1][0] - self._history[0][0]).total_seconds()
                if time_diff > 0:
                    dli = (current_value - self._history[0][1]) * (
                        24 * 3600 / time_diff
                    )
                    # Apply proper rounding based on sensor configuration
                    self._attr_native_value = round(
                        max(0, dli), self._plant.decimals_for("total_integral")
                    )
                    self._last_update = current_time.isoformat()
                    self.async_write_ha_state()

        except (TypeError, ValueError):
            pass


class PlantDummyStatus(PlantCurrentStatus):
    """Base class for dummy sensors"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Init the dummy sensor"""
        super().__init__(hass, config, plantdevice)

    async def async_update(self) -> None:
        """Give out a dummy value"""
        test = random.randint(0, 100)
        if test > 50:
            if hasattr(self, '_attr_native_value'):
                # Generate a new random value within a reasonable range
                if self._attr_native_unit_of_measurement == PERCENTAGE:
                    self._attr_native_value = random.randint(25, 90)
                elif self._attr_native_unit_of_measurement == "ppm":
                    self._attr_native_value = random.randint(400, 2000)
                else:
                    # For other units, generate a value based on the current value
                    if self._attr_native_value is not None:
                        variation = random.randint(-5, 5)
                        self._attr_native_value = max(0, self._attr_native_value + variation)
            else:
                # Set initial value based on unit
                if self._attr_native_unit_of_measurement == PERCENTAGE:
                    self._attr_native_value = random.randint(25, 90)
                elif self._attr_native_unit_of_measurement == "ppm":
                    self._attr_native_value = random.randint(400, 2000)
                else:
                    self._attr_native_value = random.randint(10, 50)


class PlantDummyCO2(PlantDummyStatus):
    """Dummy sensor"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Init the dummy sensor"""
        self._attr_name = f"Dummy {plantdevice.name} {READING_CO2}"
        self._attr_unique_id = f"{config.entry_id}-dummy-CO2"
        self._attr_icon = ICON_CO2
        self._attr_native_unit_of_measurement = "ppm"
        super().__init__(hass, config, plantdevice)
        self._attr_native_value = random.randint(400, 2000)

    @property
    def device_class(self) -> str:
        """Device class"""
        return SensorDeviceClass.CO2


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
        elif sensor_type == "CO2":
            self._attr_name = f"{plant.name} {READING_CO2}"
        elif sensor_type == "moisture":
            self._attr_name = f"{plant.name} {READING_MOISTURE}"
        elif sensor_type == "moisture_consumption":
            self._attr_name = f"{plant.name} {READING_MOISTURE_CONSUMPTION}"
        elif sensor_type == "total_water_consumption":
            self._attr_name = f"{plant.name} Total {READING_MOISTURE_CONSUMPTION}"
        elif sensor_type == "fertilizer_consumption":
            self._attr_name = f"{plant.name} {READING_FERTILIZER_CONSUMPTION}"
        elif sensor_type == "total_fertilizer_consumption":
            self._attr_name = f"{plant.name} Total {READING_FERTILIZER_CONSUMPTION}"
        elif sensor_type == "power_consumption":
            self._attr_name = f"{plant.name} {READING_POWER_CONSUMPTION}"
        elif sensor_type == "total_power_consumption":
            self._attr_name = f"{plant.name} Total {READING_POWER_CONSUMPTION}"
        elif sensor_type == "ph":  # Neuer pH Sensor
            self._attr_name = f"{plant.name} {READING_PH}"
        else:
            self._attr_name = f"{plant.name} {sensor_type}"

        # Setze Icon und Unit basierend auf Sensor-Typ
        if sensor_type == "temperature":
            self._attr_native_unit_of_measurement = (
                self.hass.config.units.temperature_unit
            )
            self._attr_icon = ICON_TEMPERATURE
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
        elif sensor_type == "moisture":
            self._attr_native_unit_of_measurement = PERCENTAGE
            self._attr_icon = ICON_MOISTURE
            self._attr_device_class = "moisture"
        elif sensor_type == "conductivity":
            self._attr_native_unit_of_measurement = UNIT_CONDUCTIVITY
            self._attr_icon = ICON_CONDUCTIVITY
            self._attr_device_class = "conductivity"
        elif sensor_type == "illuminance":
            self._attr_native_unit_of_measurement = LIGHT_LUX
            self._attr_icon = ICON_ILLUMINANCE
            self._attr_device_class = SensorDeviceClass.ILLUMINANCE
        elif sensor_type == "humidity":
            self._attr_native_unit_of_measurement = PERCENTAGE
            self._attr_icon = ICON_HUMIDITY
            self._attr_device_class = SensorDeviceClass.HUMIDITY
        elif sensor_type == "CO2":
            self._attr_native_unit_of_measurement = "ppm"
            self._attr_icon = ICON_CO2
            self._attr_device_class = SensorDeviceClass.CO2
        elif sensor_type == "ph":  # Neuer pH Sensor
            self._attr_native_unit_of_measurement = None  # pH hat keine Einheit
            self._attr_icon = ICON_PH
            self._attr_device_class = "ph"
        elif sensor_type == "ppfd":
            self._attr_native_unit_of_measurement = UNIT_PPFD
            self._attr_icon = ICON_PPFD
            self._attr_device_class = None
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        elif sensor_type == "dli":
            self._attr_native_unit_of_measurement = UNIT_DLI
            self._attr_icon = ICON_DLI
            self._attr_device_class = "dli"
        elif sensor_type == "total_integral":
            self._attr_native_unit_of_measurement = UNIT_DLI
            self._attr_icon = ICON_DLI
            self._attr_device_class = None
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        elif sensor_type == "moisture_consumption":
            self._attr_native_unit_of_measurement = UNIT_VOLUME
            self._attr_icon = ICON_WATER_CONSUMPTION
            self._attr_device_class = None
        elif sensor_type == "total_water_consumption":
            self._attr_native_unit_of_measurement = UNIT_VOLUME
            self._attr_icon = ICON_WATER_CONSUMPTION
            self._attr_device_class = None
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        elif sensor_type == "fertilizer_consumption":
            self._attr_native_unit_of_measurement = UNIT_CONDUCTIVITY
            self._attr_icon = ICON_FERTILIZER_CONSUMPTION
            self._attr_device_class = None
        elif sensor_type == "total_fertilizer_consumption":
            self._attr_native_unit_of_measurement = UNIT_CONDUCTIVITY
            self._attr_icon = ICON_FERTILIZER_CONSUMPTION
            self._attr_device_class = None
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        elif sensor_type == "power_consumption":
            self._attr_native_unit_of_measurement = "W"  # Watt für aktuelle Leistung
            self._attr_icon = ICON_POWER_CONSUMPTION
            self._attr_device_class = SensorDeviceClass.POWER
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif (
            sensor_type == "total_power_consumption"
        ):  # Füge Total Power Consumption hinzu
            self._attr_native_unit_of_measurement = "kWh"
            self._attr_icon = ICON_POWER_CONSUMPTION
            self._attr_device_class = SensorDeviceClass.ENERGY
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

        self._attr_native_value = None  # Use None instead of 0
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
        value = self.plant._median_sensors.get(self._sensor_type)
        return value if value is not None else None

    @property
    def extra_state_attributes(self):
        """Return additional sensor attributes."""
        aggregation_method = self.plant._plant_info.get("aggregations", {}).get(
            self._sensor_type, DEFAULT_AGGREGATIONS[self._sensor_type]
        )
        return {
            "member_plants": self.plant._member_plants,
            "aggregation_method": aggregation_method,
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
            "pot_size": self._plant.pot_size.native_value
            if self._plant.pot_size
            else None,
            "water_capacity": self._plant.water_capacity.native_value
            if self._plant.water_capacity
            else None,
            "last_update": self._last_update,
        }

    def _unit(self, source_unit: str) -> str:
        """Override unit"""
        return UNIT_PPFD  # Benutze immer PPFD als Einheit

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        
        # Restore previous state
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            try:
                if not self._config.data[FLOW_PLANT_INFO].get(ATTR_IS_NEW_PLANT, False):
                    self._attr_native_value = float(last_state.state)
                    if last_state.attributes.get("last_update"):
                        self._last_update = last_state.attributes["last_update"]
            except (TypeError, ValueError):
                self._attr_native_value = None

        # Track PPFD sensor changes
        async_track_state_change_event(
            self.hass,
            [self._sensor_ppfd.entity_id],
            self._state_changed_event,
        )

    @callback
    def _state_changed_event(self, event):
        """Handle PPFD sensor state changes."""
        if self._config.data[FLOW_PLANT_INFO].get(ATTR_IS_NEW_PLANT, False):
            return  # Bei neuer Plant keine Änderungen verarbeiten

        new_state = event.data.get("new_state")
        if not new_state or new_state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return

        try:
            # Get total energy consumption in kWh
            total_energy_kwh = float(new_state.state)
            
            # Get kWh price from plant or use default
            kwh_price = getattr(self._plant, '_kwh_price', DEFAULT_KWH_PRICE)
            if kwh_price is None:
                kwh_price = DEFAULT_KWH_PRICE
                
            # Calculate cost
            cost = total_energy_kwh * kwh_price
            
            self._attr_native_value = round(
                cost,
                self._plant.decimals_for("energy_cost"),
            )
            self._last_update = dt_util.utcnow().isoformat()
            self.async_write_ha_state()

        except (TypeError, ValueError):
            self._attr_native_value = None  # Set to None on error

    async def async_update(self) -> None:
        """Update the sensor."""
        if self._plant.total_power_consumption:
            try:
                state = self.hass.states.get(self._plant.total_power_consumption.entity_id)
                if state and state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                    # Trigger the state change event to recalculate
                    self._state_changed_event(
                        type('Event', (), {
                            'data': {
                                'new_state': state
                            }
                        })()
                    )
            except Exception:
                self._attr_native_value = None


class PlantCurrentMoistureConsumption(PlantCurrentStatus):
    """Entity class for current moisture consumption"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_name = f"{plantdevice.name} {READING_MOISTURE_CONSUMPTION}"
        self._attr_unique_id = f"{config.entry_id}-current-moisture-consumption"
        self._attr_icon = ICON_WATER_CONSUMPTION
        self._plant = plantdevice
        self._external_sensor = None
        self._attr_native_unit_of_measurement = UNIT_VOLUME
        super().__init__(hass, config, plantdevice)

    def sensor_type(self) -> str | None:
        """Logical sensor type key used for decimals config."""
        return "moisture_consumption"

    @property
    def device_class(self) -> str:
        """Device class"""
        return None

    @property
    def state_class(self):
        """Return the state class."""
        return SensorStateClass.MEASUREMENT

    @property
    def entity_category(self) -> str:
        """The entity category"""
        return EntityCategory.DIAGNOSTIC


class PlantTotalWaterConsumption(IntegrationSensor):
    """Entity class for total water consumption"""

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        plantdevice: Entity,
        source_sensor: Entity = None,
    ) -> None:
        """Initialize the sensor"""
        # Use the moisture_consumption sensor as the source if provided
        source_entity_id = source_sensor.entity_id if source_sensor else ""
        
        super().__init__(
            hass,
            integration_method=METHOD_TRAPEZOIDAL,
            name=f"{plantdevice.name} Total {READING_MOISTURE_CONSUMPTION}",
            round_digits=0,  # Use 0 decimal places for integral values
            source_entity=source_entity_id,
            unique_id=f"{config.entry_id}-total-water-consumption",
            unit_prefix=None,
            unit_time=UnitOfTime.SECONDS,
            max_sub_interval=None,
        )
        self._attr_icon = ICON_WATER_CONSUMPTION
        self._unit_of_measurement = UNIT_VOLUME
        self._attr_native_unit_of_measurement = UNIT_VOLUME
        self._plant = plantdevice
        self.entity_id = async_generate_entity_id(
            f"{DOMAIN_SENSOR}.{{}}", self.name, current_ids={}
        )

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

    def _unit(self, source_unit: str) -> str:
        """Override unit"""
        return UNIT_VOLUME

    def replace_external_sensor(self, new_sensor: str) -> None:
        """Modify the external sensor"""
        self._source_entity = new_sensor
        self.async_write_ha_state()


class PlantCurrentFertilizerConsumption(PlantCurrentStatus):
    """Entity class for current fertilizer consumption"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_name = f"{plantdevice.name} {READING_FERTILIZER_CONSUMPTION}"
        self._attr_unique_id = f"{config.entry_id}-current-fertilizer-consumption"
        self._attr_icon = ICON_FERTILIZER_CONSUMPTION
        self._plant = plantdevice
        self._external_sensor = None
        self._attr_native_unit_of_measurement = UNIT_CONDUCTIVITY
        super().__init__(hass, config, plantdevice)

    def sensor_type(self) -> str | None:
        """Logical sensor type key used for decimals config."""
        return "fertilizer_consumption"

    @property
    def device_class(self) -> str:
        """Device class"""
        return None

    @property
    def state_class(self):
        """Return the state class."""
        return SensorStateClass.MEASUREMENT

    @property
    def entity_category(self) -> str:
        """The entity category"""
        return EntityCategory.DIAGNOSTIC


class PlantTotalFertilizerConsumption(IntegrationSensor):
    """Entity class for total fertilizer consumption"""

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        plantdevice: Entity,
        source_sensor: Entity = None,
    ) -> None:
        """Initialize the sensor"""
        # Use the fertilizer_consumption sensor as the source if provided
        source_entity_id = source_sensor.entity_id if source_sensor else ""
        
        super().__init__(
            hass,
            integration_method=METHOD_TRAPEZOIDAL,
            name=f"{plantdevice.name} Total {READING_FERTILIZER_CONSUMPTION}",
            round_digits=0,  # Use 0 decimal places for integral values
            source_entity=source_entity_id,
            unique_id=f"{config.entry_id}-total-fertilizer-consumption",
            unit_prefix=None,
            unit_time=UnitOfTime.SECONDS,
            max_sub_interval=None,
        )
        self._attr_icon = ICON_FERTILIZER_CONSUMPTION
        self._unit_of_measurement = UNIT_CONDUCTIVITY
        self._attr_native_unit_of_measurement = UNIT_CONDUCTIVITY
        self._plant = plantdevice
        self.entity_id = async_generate_entity_id(
            f"{DOMAIN_SENSOR}.{{}}", self.name, current_ids={}
        )

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

    def _unit(self, source_unit: str) -> str:
        """Override unit"""
        return UNIT_CONDUCTIVITY

    def replace_external_sensor(self, new_sensor: str) -> None:
        """Modify the external sensor"""
        self._source_entity = new_sensor
        self.async_write_ha_state()


class PlantCurrentPowerConsumption(PlantCurrentStatus):
    """Entity class for current power consumption"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_name = f"{plantdevice.name} {READING_POWER_CONSUMPTION}"
        self._attr_unique_id = f"{config.entry_id}-current-power-consumption"
        self._attr_icon = ICON_POWER_CONSUMPTION
        self._plant = plantdevice
        self._external_sensor = None
        self._attr_native_unit_of_measurement = "W"
        super().__init__(hass, config, plantdevice)

    def sensor_type(self) -> str | None:
        """Logical sensor type key used for decimals config."""
        return "power_consumption"

    @property
    def device_class(self) -> str:
        """Device class"""
        return SensorDeviceClass.POWER

    @property
    def state_class(self):
        """Return the state class."""
        return SensorStateClass.MEASUREMENT


class PlantTotalPowerConsumption(PlantCurrentStatus):
    """Entity class for total power consumption"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_name = f"{plantdevice.name} Total {READING_POWER_CONSUMPTION}"
        self._attr_unique_id = f"{config.entry_id}-total-power-consumption"
        self._attr_icon = ICON_POWER_CONSUMPTION
        self._plant = plantdevice
        self._external_sensor = None
        self._attr_native_unit_of_measurement = "kWh"
        super().__init__(hass, config, plantdevice)

    def sensor_type(self) -> str | None:
        """Logical sensor type key used for decimals config."""
        return "total_power_consumption"

    @property
    def device_class(self) -> str:
        """Device class"""
        return SensorDeviceClass.ENERGY

    @property
    def state_class(self):
        """Return the state class."""
        return SensorStateClass.TOTAL_INCREASING

    @property
    def entity_category(self) -> str:
        """The entity category"""
        return EntityCategory.DIAGNOSTIC


class PlantEnergyCost(RestoreSensor):
    """Entity class for energy cost calculation"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        super().__init__()
        self.hass = hass
        self._config = config
        self._plant = plantdevice
        self._attr_name = f"{plantdevice.name} {READING_ENERGY_COST}"
        self._attr_unique_id = f"{config.entry_id}-energy-cost"
        self._attr_icon = ICON_ENERGY_COST
        self._attr_native_unit_of_measurement = "€"
        self._attr_native_value = None
        # Set default kWh price if not configured
        self._kwh_price = config.data.get(ATTR_KWH_PRICE, DEFAULT_KWH_PRICE)
        self.entity_id = async_generate_entity_id(
            f"{DOMAIN_SENSOR}.{{}}", self.name, current_ids={}
        )

    @property
    def device_class(self) -> str:
        """Device class"""
        return "monetary"

    @property
    def state_class(self):
        """Return the state class."""
        return SensorStateClass.TOTAL

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

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state and state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE, "unknown", "unavailable", None):
            try:
                self._attr_native_value = float(state.state)
            except (ValueureError, TypeError):
                self._attr_native_value = None
        else:
            self._attr_native_value = None
        
        # Track total power consumption changes
        if self._plant.total_power_consumption:
            async_track_state_change_event(
                self.hass,
                [self._plant.total_power_consumption.entity_id],
                self._state_changed_event,
            )

    @callback
    def _state_changed_event(self, event):
        """Handle total power consumption state changes."""
        self._update_energy_cost()

    def _update_energy_cost(self) -> None:
        """Calculate and update energy cost."""
        if (self._plant.total_power_consumption and 
            self._plant.total_power_consumption.native_value is not None and
            self._plant.total_power_consumption.native_value not in (STATE_UNKNOWN, STATE_UNAVAILABLE, "unknown", "unavailable")):
            try:
                total_kwh = float(self._plant.total_power_consumption.native_value)
                cost = total_kwh * self._kwh_price
                self._attr_native_value = round(cost, self._plant.decimals_for("energy_cost"))
                self.async_write_ha_state()
            except (TypeError, ValueError):
                self._attr_native_value = None
        else:
            self._attr_native_value = None

    async def async_update(self) -> None:
        """Calculate energy cost based on total power consumption"""
        self._update_energy_cost()
