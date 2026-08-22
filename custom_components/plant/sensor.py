"""Meter entities for the plant integration"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import inspect
import logging
import random
from statistics import quantiles
from typing import Any

from homeassistant.components.integration.const import METHOD_TRAPEZOIDAL
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.components.integration.sensor import IntegrationSensor
from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorExtraStoredData,
    SensorStateClass,
)
from homeassistant.components.statistics.sensor import StatisticsSensor
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
    FLOW_SENSOR_ILLUMINANCE,
    FLOW_SENSOR_MOISTURE,
    FLOW_SENSOR_TEMPERATURE,
    FLOW_SENSOR_POWER_CONSUMPTION,
    FLOW_SENSOR_PH,
    ICON_CONDUCTIVITY,
    ICON_DLI,
    ICON_HUMIDITY,
    ICON_ILLUMINANCE,
    ICON_MOISTURE,
    ICON_PPFD,
    ICON_TEMPERATURE,
    ICON_POWER_CONSUMPTION,
    ICON_PH,
    READING_CONDUCTIVITY,
    READING_DLI,
    READING_HUMIDITY,
    READING_ILLUMINANCE,
    READING_MOISTURE,
    READING_PPFD,
    READING_TEMPERATURE,
    READING_POWER_CONSUMPTION,
    READING_PH,
    UNIT_CONDUCTIVITY,
    UNIT_CONDUCTIVITY_MILLI,
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
    ATTR_KWH_PRICE,
    DEFAULT_KWH_PRICE,
    READING_ENERGY_COST,
    ICON_ENERGY_COST,
    DEVICE_CLASS_PH,  # Importiere unsere eigene Device Class
)

_LOGGER = logging.getLogger(__name__)


def _init_accepts_hass(cls: type) -> bool:
    """Nimmt cls.__init__ noch ein hass-Argument entgegen?

    HA 2026.8 (Core-PRs #177596/#177597/#177603, "Do not set a device on YAML
    integration / statistics / utility_meter entities") hat das führende
    hass-Argument aus IntegrationSensor/StatisticsSensor/UtilityMeterSensor
    entfernt. Wir übergeben hass deshalb nur noch auf HA < 2026.8; neuere Kerne
    bekommen ihr Gerät weiterhin über die device_info-Property der Subklasse.
    """
    return "hass" in inspect.signature(cls.__init__).parameters


_INTEGRATION_SENSOR_ACCEPTS_HASS = _init_accepts_hass(IntegrationSensor)
_STATISTICS_SENSOR_ACCEPTS_HASS = _init_accepts_hass(StatisticsSensor)


@dataclass
class PlantHistoryExtraStoredData(SensorExtraStoredData):
    """Restore-Daten eines Sensors samt seinem 24-Stunden-Fenster.

    SensorExtraStoredData bringt native_value und Einheit mit; hier kommt die
    Messreihe dazu, die die Verbrauchs- und DLI-Sensoren zum Weiterrechnen nach
    einem Neustart brauchen.
    """

    history: list | None = None

    def as_dict(self) -> dict:
        daten = super().as_dict()
        daten["history"] = self.history or []
        return daten

    @classmethod
    def from_dict(cls, restored: dict) -> PlantHistoryExtraStoredData | None:
        basis = SensorExtraStoredData.from_dict(restored)
        if basis is None:
            return None
        return cls(
            basis.native_value,
            basis.native_unit_of_measurement,
            restored.get("history") or [],
        )
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
        pcurph = PlantCurrentPh(hass, entry, plant)  # Neuer pH Sensor
        
        plant_sensors = [pcurb, pcurc, pcurm, pcurt, pcurh, pcurph]  # pH Sensor hinzugefügt
        
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
            power_consumption=None,  # Wird später gesetzt
            ph=pcurph,  # pH Sensor hinzugefügt
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
            )
            async_add_entities([total_fertilizer_consumption])

        # Jetzt können wir add_calculations aufrufen
        plant.add_calculations(pcurppfd, pintegral, moisture_consumption, fertilizer_consumption)
        # Füge die Total Consumption Sensoren hinzu
        plant.total_water_consumption = total_water_consumption
        plant.total_fertilizer_consumption = total_fertilizer_consumption

        pdli = PlantDailyLightIntegral(hass, entry, pintegral, plant)
        async_add_entities(new_entities=[pdli], update_before_add=True)

        plant.add_dli(dli=pdli)
        
        # Füge zuerst den Total Power Consumption Sensor hinzu
        if plant.device_type != DEVICE_TYPE_CYCLE:
            total_power_consumption = PlantTotalPowerConsumption(hass, entry, plant)
            async_add_entities([total_power_consumption])
            
            # Weise den externen Sensor zu
            if entry.data[FLOW_PLANT_INFO].get(FLOW_SENSOR_POWER_CONSUMPTION):
                total_power_consumption.replace_external_sensor(entry.data[FLOW_PLANT_INFO][FLOW_SENSOR_POWER_CONSUMPTION])
            
            # Dann erst den Current Power Consumption Sensor erstellen
            pcurp = PlantCurrentPowerConsumption(hass, entry, plant)
            async_add_entities([pcurp])
            
            # Jetzt können wir beide Sensoren der Plant hinzufügen
            plant.add_power_consumption_sensors(
                current=pcurp,
                total=total_power_consumption
            )

            # Der Total-Power-Sensor ist der einzige Verbrauchs-Meter mit einem
            # externen Quell-Sensor (PlantCurrentPowerConsumption rechnet nur
            # daraus ab). Er muss deshalb mit in ATTR_SENSORS, sonst findet ihn
            # der replace_sensor-Service nicht, lehnt ihn als "non-plant entity"
            # ab und jede Zuweisung einer Stromverbrauchs-Quelle schlägt still
            # fehl — nur bei diesem einen Sensortyp.
            hass.data[DOMAIN][entry.entry_id].setdefault(ATTR_SENSORS, []).append(
                total_power_consumption
            )

    # Erstelle die Median-Sensoren für Cycles
    if plant.device_type == DEVICE_TYPE_CYCLE:
        cycle_sensors = []
        
        # Erstelle die Basis-Sensoren
        for sensor_type in ["temperature", "moisture", "conductivity", "illuminance", "humidity", "ph"]:
            sensor = CycleMedianSensor(hass, entry, plant, sensor_type)
            cycle_sensors.append(sensor)
            
        # Erstelle die berechneten Sensoren
        for sensor_type in [
            "ppfd", 
            "dli", 
            "total_integral", 
            "moisture_consumption",
            "total_water_consumption",  # Füge Total Water hinzu
            "fertilizer_consumption",
            "total_fertilizer_consumption",  # Füge Total Fertilizer hinzu
            "power_consumption",
            "total_power_consumption"  # Füge Total Power hinzu
        ]:
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
            power_consumption=cycle_sensors[13],  # Aktualisiere Index für Power Consumption (eins mehr wegen pH)
            ph=cycle_sensors[5],  # pH-Sensor hinzugefügt
        )
        
        # Füge die berechneten Sensoren hinzu
        plant.add_calculations(
            ppfd=cycle_sensors[6],
            total_integral=cycle_sensors[8],
            moisture_consumption=cycle_sensors[9],
            fertilizer_consumption=cycle_sensors[11]
        )
        plant.add_dli(dli=cycle_sensors[7])
        
        # Füge auch für Cycles die Total Consumption Sensoren direkt hinzu
        plant.total_water_consumption = cycle_sensors[10]
        plant.total_fertilizer_consumption = cycle_sensors[12]
        
        # Korrigierte Verwendung der add_power_consumption_sensors Methode
        # Der aktuelle Sensor wurde bereits durch add_sensors hinzugefügt, hier nur total hinzufügen
        plant.add_power_consumption_sensors(
            current=plant.sensor_power_consumption,  # Bereits zugewiesen
            total=cycle_sensors[14]
        )

    # Füge Energiekosten-Sensor hinzu
    energy_cost = PlantEnergyCost(hass, entry, plant)
    plant.energy_cost = energy_cost  # Speichere Referenz in der Plant
    
    async_add_entities([energy_cost])

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
        self._hass = hass
        self._config = config
        # Kein Messwert heisst "unbekannt", nicht 0. Mit 0 meldete jede Pflanze
        # direkt nach dem Start 0 % Bodenfeuchte bzw. 0 °C -- ein Wert, der als
        # echte Messung durchgeht: er loest den Problemzustand aus und landet in
        # der Statistik, bis der externe Sensor das erste Mal sendet.
        self._default_state = None
        self._plant = plantdevice
        if not self._attr_native_value or self._attr_native_value == STATE_UNKNOWN:
            self._attr_native_value = self._default_state

    @property
    def state_class(self):
        """Return the state class."""
        return self._attr_state_class if hasattr(self, '_attr_state_class') else SensorStateClass.MEASUREMENT

    @property
    def device_class(self):
        """Return the device class."""
        return self._attr_device_class if hasattr(self, '_attr_device_class') else None

    @property
    def device_info(self) -> DeviceInfo:
        """Device info for devices"""
        return DeviceInfo(identifiers={(DOMAIN, self._plant.unique_id)})

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
        if self._external_sensor:
            async_track_state_change_event(
                self._hass,
                [self._external_sensor],
                self._state_changed_event,
            )

        # Beim Setup weist die Plattform den externen Sensor zu, bevor
        # async_add_entities die Entity fertig hinzugefuegt hat -- dann ist hass
        # noch None und async_write_ha_state wirft, was den kompletten
        # Plattform-Aufbau abbricht. Den Zustand schreibt HA ohnehin, sobald die
        # Entity hinzugefuegt ist.
        if self.hass is None:
            return

        # Den Messwert der bisherigen Quelle nicht stehen lassen: bis der neue
        # Sensor das erste Mal meldet, zeigte die Entity sonst weiter den Wert
        # der alten Zuweisung -- bei einem Sensor, der nur alle paar Minuten
        # sendet, minutenlang. state_changed uebernimmt den aktuellen Stand der
        # neuen Quelle (und setzt ohne Quelle auf unbekannt zurueck).
        self.state_changed(
            self._external_sensor,
            self._hass.states.get(self._external_sensor) if self._external_sensor else None,
        )

        self.async_write_ha_state()

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

        async_dispatcher_connect(
            self._hass, DATA_UPDATED, self._schedule_immediate_update
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

    async def async_update(self) -> None:
        """Set state and unit to the parent sensor state and unit"""
        if self.external_sensor:
            try:
                state = self._hass.states.get(self.external_sensor)
                if state:
                    self._attr_native_value = float(state.state)
                    if ATTR_UNIT_OF_MEASUREMENT in state.attributes:
                        self._attr_native_unit_of_measurement = state.attributes[ATTR_UNIT_OF_MEASUREMENT]
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


class PlantCurrentIlluminance(PlantCurrentStatus):
    """Entity class for the current illuminance meter"""


    _attr_has_entity_name = True
    _attr_translation_key = "current_illuminance"
    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_unique_id = f"{config.entry_id}-current-illuminance"
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


    _attr_has_entity_name = True
    _attr_translation_key = "current_conductivity"
    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_unique_id = f"{config.entry_id}-current-conductivity"
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
                    "factor": round(moisture_sensor._normalize_factor, 2) if getattr(moisture_sensor, '_normalize_factor', None) is not None else None,
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


    _attr_has_entity_name = True
    _attr_translation_key = "current_moisture"
    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_unique_id = f"{config.entry_id}-current-moisture"
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

    def _apply_normalization(self) -> None:
        """Skaliert den Rohwert mit dem zwischengespeicherten Maximum."""
        if not self._normalize or not self._max_moisture or self._attr_native_value is None:
            return
        try:
            normalized = min(100, (float(self._attr_native_value) / self._max_moisture) * 100)
            self._attr_native_value = round(normalized, 1)
        except (ValueError, TypeError):
            pass

    @callback
    def state_changed(self, entity_id, new_state):
        """Uebernimmt den Messwert des externen Sensors.

        Die Basisklasse schreibt den Rohwert. Normalisiert wurde bisher nur in
        async_update -- wer den Zustand vorher schrieb, zeigte den Rohwert an:
        61 % statt der skalierten 96 %, ohne dass irgendetwas gegossen wurde.
        Das zuletzt berechnete Maximum liegt zwischengespeichert vor, es wird
        alle fuenf Minuten in async_update aufgefrischt.
        """
        super().state_changed(entity_id, new_state)
        if self._attr_native_value is not None:
            self._raw_value = self._attr_native_value
        self._apply_normalization()

    async def async_update(self) -> None:
        """Update the sensor."""
        await super().async_update()
        
        # Speichere den Rohwert vor der Normalisierung
        if self._attr_native_value is not None:
            self._raw_value = self._attr_native_value
        
        # Aktualisiere Normalisierung
        await self._update_normalization()
        
        self._apply_normalization()

    @property
    def device_class(self) -> str:
        """Device class"""
        return ATTR_MOISTURE


class PlantCurrentTemperature(PlantCurrentStatus):
    """Entity class for the current temperature meter"""


    _attr_has_entity_name = True
    _attr_translation_key = "current_temperature"
    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_unique_id = f"{config.entry_id}-current-temperature"
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


    _attr_has_entity_name = True
    _attr_translation_key = "current_humidity"
    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_unique_id = f"{config.entry_id}-current-humidity"
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


    _attr_has_entity_name = True
    _attr_translation_key = "current_ppfd"
    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_unique_id = f"{config.entry_id}-current-ppfd"
        self._attr_unit_of_measurement = UNIT_PPFD
        self._attr_native_unit_of_measurement = UNIT_PPFD
        self._plant = plantdevice
        self._external_sensor = self._plant.sensor_illuminance.entity_id
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
            factor = DEFAULT_LUX_TO_PPFD
            if self._plant.lux_to_ppfd and self._plant.lux_to_ppfd.native_value is not None:
                factor = self._plant.lux_to_ppfd.native_value
            value = float(value) * factor / 1000000
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
    """Entity class to calculate PPFD from LX.

    Erbt von IntegrationSensor und nutzt dessen name-Parameter — kein
    translation_key-Pattern hier, sonst kollidieren beide Naming-Wege.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        illuminance_ppfd_sensor: Entity,
        plantdevice: Entity,
    ) -> None:
        """Initialize the sensor"""
        self._config = config  # Speichere config für späteren Zugriff
        integration_kwargs = {
            "integration_method": METHOD_TRAPEZOIDAL,
            "name": f"{plantdevice.name} Total {READING_PPFD} Integral",
            # PPFD liegt in der Groessenordnung 1e-6 mol/s⋅m². Mit nur zwei
            # Nachkommastellen faellt jeder Zuwachs unter eine Stunde beim
            # Runden weg und das Integral bleibt auf demselben Wert stehen -
            # der DLI, der die Aenderung ueber 24 h misst, sieht dann 0.
            "round_digits": 6,
            "source_entity": illuminance_ppfd_sensor.entity_id,
            "unique_id": f"{config.entry_id}-ppfd-integral",
            "unit_prefix": None,
            "unit_time": UnitOfTime.SECONDS,
            # Ohne Takt rechnet das Integral nur, wenn die Quelle ihren
            # Zustand aendert. Bei konstantem Licht schreibt es dann stunden-
            # lang nichts. Eine Minute Takt haelt es am Laufen.
            "max_sub_interval": timedelta(minutes=1),
        }
        if _INTEGRATION_SENSOR_ACCEPTS_HASS:
            integration_kwargs["hass"] = hass
        super().__init__(**integration_kwargs)
        self._attr_has_entity_name = False
        self._unit_of_measurement = UNIT_PPFD  # Benutze PPFD Einheit statt DLI
        self._attr_native_unit_of_measurement = UNIT_PPFD  # Setze auch native unit
        self._attr_icon = ICON_DLI
        self._plant = plantdevice
        self._attr_native_value = 0  # Starte immer bei 0
        
        # Setze Wert bei Neuerstellung zurück
        if config.data[FLOW_PLANT_INFO].get(ATTR_IS_NEW_PLANT, False):
            self._attr_native_value = 0
            self._state = 0  # Wichtig für IntegrationSensor

    @property
    def entity_category(self) -> str:
        """The entity category"""
        return EntityCategory.DIAGNOSTIC

    @property
    def device_info(self) -> DeviceInfo:
        """Device info for devices"""
        return DeviceInfo(identifiers={(DOMAIN, self._plant.unique_id)})

    @property
    def entity_registry_visible_default(self) -> str:
        return False

    def _unit(self, source_unit: str) -> str:
        """Override unit"""
        return UNIT_PPFD  # Benutze immer PPFD als Einheit

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        
        # Bei einer neuen Plant nicht den alten State wiederherstellen
        if self._config.data[FLOW_PLANT_INFO].get(ATTR_IS_NEW_PLANT, False):
            self._attr_native_value = 0
            self._state = 0  # Wichtig für IntegrationSensor


class PlantDailyLightIntegral(StatisticsSensor):
    """Rollierender 24-Stunden-DLI.

    Zeigt die in den letzten 24 Stunden aufgenommene Lichtmenge, gleitend und
    ohne Reset um Mitternacht - das Verhalten, das dieser Sensor immer hatte.

    Neu ist nur der Unterbau: statt einer selbst gefuehrten Messreihe im
    Speicher rechnet jetzt Home Assistants Statistik-Sensor mit der Kennzahl
    "change" ueber einem 24-Stunden-Fenster. Das ist dieselbe Rechnung
    (Zaehlerstand jetzt minus Zaehlerstand vor 24 Stunden), nur dass HA die
    Messwerte haelt und aus der Recorder-Datenbank speist.
    """

    _attr_has_entity_name = True
    _attr_device_class = ATTR_DLI
    _attr_icon = ICON_DLI
    _attr_suggested_display_precision = 2
    _attr_translation_key = "dli"

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        illuminance_integration_sensor: Entity,
        plantdevice: Entity,
    ) -> None:
        """Initialize the sensor"""
        self._plant = plantdevice

        statistics_kwargs = {
            "source_entity_id": illuminance_integration_sensor.entity_id,
            "name": READING_DLI,
            "unique_id": f"{config.entry_id}-dli",
            "state_characteristic": "change",
            "samples_max_buffer_size": None,  # unbegrenzt, das Fenster steuert max_age
            "samples_max_age": timedelta(hours=24),
            "samples_keep_last": True,
            "precision": 2,
            "percentile": 50,  # fuer "change" ohne Bedeutung, aber Pflichtargument
        }
        if _STATISTICS_SENSOR_ACCEPTS_HASS:
            statistics_kwargs["hass"] = hass
        super().__init__(**statistics_kwargs)
        # StatisticsSensor setzt _attr_name aus dem name-Argument. Das Attribut
        # muss weg - nicht auf None gesetzt: HA nimmt die Uebersetzung nur,
        # wenn _attr_name gar nicht existiert. None hiesse "kein Name".
        if hasattr(self, "_attr_name"):
            del self._attr_name

    @property
    def native_unit_of_measurement(self) -> str:
        """Einheit fest auf DLI statt der Einheit des Quellsensors."""
        return UNIT_DLI

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(identifiers={(DOMAIN, self._plant.unique_id)})

    async def async_will_remove_from_hass(self) -> None:
        """Den Aufraeum-Timer beim Entfernen abbestellen.

        StatisticsSensor legt seinen Purge-Timer ueber
        async_track_point_in_utc_time an, meldet ihn aber - anders als seine
        State-Listener - nicht bei async_on_remove an. Er ueberlebt sonst die
        Entitaet. _async_cancel_update_listener ist private HA-API, deshalb
        abgesichert aufgerufen.
        """
        await super().async_will_remove_from_hass()
        abbestellen = getattr(self, "_async_cancel_update_listener", None)
        if abbestellen is not None:
            abbestellen()


class PlantDummyStatus(SensorEntity):
    """Simple dummy sensors. Parent class"""

    _attr_has_entity_name = True

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the dummy sensor."""
        self._config = config
        self._default_state = STATE_UNKNOWN
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


    _attr_translation_key = "dummy_illuminance"
    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Init the dummy sensor"""
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


    _attr_translation_key = "dummy_conductivity"
    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Init the dummy sensor"""
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


    _attr_translation_key = "dummy_moisture"
    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Init the dummy sensor"""
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


    _attr_translation_key = "dummy_temperature"
    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Init the dummy sensor"""
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


    _attr_translation_key = "dummy_humidity"
    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Init the dummy sensor"""
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
        # hass wird von HA's Entity.add_to_platform automatisch gesetzt —
        # nicht via self.hass = hass überschreiben (HA-Pattern). hass-Argument
        # nur lokal in __init__ verwenden, falls Units etc. nötig.
        self.config_entry = config_entry
        self.plant = plant
        self._sensor_type = sensor_type
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{config_entry.entry_id}-median-{sensor_type}"

        # translation_key pro sensor_type — HA wählt den passenden
        # Übersetzungs-Eintrag aus entity.sensor.{key}.name.
        self._attr_translation_key = f"median_{sensor_type}"

        # Setze Icon und Unit basierend auf Sensor-Typ
        if sensor_type == "temperature":
            self._attr_native_unit_of_measurement = hass.config.units.temperature_unit
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
        elif sensor_type == "ph":  # Neuer pH Sensor
            self._attr_native_unit_of_measurement = None  # pH hat keine Einheit
            self._attr_icon = ICON_PH
            self._attr_device_class = SensorDeviceClass.PH
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
        elif sensor_type == "total_water_consumption":
            self._attr_native_unit_of_measurement = UNIT_VOLUME
            self._attr_icon = ICON_WATER_CONSUMPTION
            self._attr_device_class = None
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        elif sensor_type == "fertilizer_consumption":
            self._attr_native_unit_of_measurement = UNIT_CONDUCTIVITY_MILLI
            self._attr_icon = ICON_FERTILIZER_CONSUMPTION
            self._attr_device_class = None
        elif sensor_type == "total_fertilizer_consumption":
            self._attr_native_unit_of_measurement = UNIT_CONDUCTIVITY_MILLI
            self._attr_icon = ICON_FERTILIZER_CONSUMPTION
            self._attr_device_class = None
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        elif sensor_type == "power_consumption":
            self._attr_native_unit_of_measurement = "W"  # Watt für aktuelle Leistung
            self._attr_icon = ICON_POWER_CONSUMPTION
            self._attr_device_class = SensorDeviceClass.POWER
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif sensor_type == "total_power_consumption":  # Füge Total Power Consumption hinzu
            self._attr_native_unit_of_measurement = "kWh"
            self._attr_icon = ICON_POWER_CONSUMPTION
            self._attr_device_class = SensorDeviceClass.ENERGY
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

        self._attr_native_value = None
        self._attr_should_poll = False

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(identifiers={(DOMAIN, self.plant.unique_id)})

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
    def state_class(self):
        return SensorStateClass.MEASUREMENT


class PlantCurrentMoistureConsumption(RestoreSensor):
    _attr_state_class = SensorStateClass.MEASUREMENT

    """Sensor to track water consumption based on moisture drop."""


    _attr_has_entity_name = True
    _attr_translation_key = "moisture_consumption"
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
        self._attr_unique_id = f"{config.entry_id}-moisture-consumption"
        self._attr_native_unit_of_measurement = UNIT_VOLUME
        self._attr_icon = ICON_WATER_CONSUMPTION
        self._history = []
        self._last_update = None
        self._attr_native_value = 0  # Starte immer bei 0
        
        # Bei Neuerstellung explizit auf 0 setzen
        if config.data[FLOW_PLANT_INFO].get(ATTR_IS_NEW_PLANT, False):
            self._attr_native_value = 0
            self._history = []

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(identifiers={(DOMAIN, self._plant.unique_id)})

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional sensor attributes."""
        return {
            "pot_size": self._plant.pot_size.native_value if self._plant.pot_size else None,
            "water_capacity": self._plant.water_capacity.native_value if self._plant.water_capacity else None,
            "last_update": self._last_update,
        }

    @property
    def extra_restore_state_data(self) -> PlantHistoryExtraStoredData:
        """Das 24h-Fenster über Neustarts hinweg sichern.

        Bewusst nicht als State-Attribut: Attribute schreibt der Recorder bei
        jeder Zustandsänderung vollständig in die Verlaufsdatenbank, was hier
        alle paar Minuten eine komplette Kopie der Messreihe bedeutete. Über
        extra_restore_state_data landen die Daten nur in core.restore_state,
        also genau dort, wo sie für den Neustart gebraucht werden.
        """
        return PlantHistoryExtraStoredData(
            self.native_value,
            self.native_unit_of_measurement,
            [(t.isoformat(), v) for t, v in self._history],
        )

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()

        if not self._config.data[FLOW_PLANT_INFO].get(ATTR_IS_NEW_PLANT, False):
            # Native value: bevorzugt aus async_get_last_sensor_data (überlebt UNAVAILABLE
            # beim Integration-Reload), Fallback last_state.
            last_data = await self.async_get_last_sensor_data()
            restored = False
            if last_data is not None and last_data.native_value is not None:
                try:
                    self._attr_native_value = float(last_data.native_value)
                    restored = True
                except (TypeError, ValueError):
                    pass
            last_state = await self.async_get_last_state()
            if not restored and last_state and last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                try:
                    self._attr_native_value = float(last_state.state)
                except (TypeError, ValueError):
                    pass
            # Attribute (last_update + _history) auch wenn state UNAVAILABLE war.
            if last_state:
                if last_state.attributes.get("last_update"):
                    self._last_update = last_state.attributes["last_update"]
                # Neu: aus den Restore-Daten. Der Rückfall auf das alte Attribut
                # greift genau einmal, beim ersten Start nach dem Update.
                extra = await self.async_get_last_extra_data()
                hist_json = None
                if extra is not None:
                    wieder = PlantHistoryExtraStoredData.from_dict(extra.as_dict())
                    if wieder is not None:
                        hist_json = wieder.history
                if not hist_json:
                    hist_json = last_state.attributes.get("history_json")
                if hist_json:
                    try:
                        self._history = [
                            (dt_util.parse_datetime(t), float(v))
                            for t, v in hist_json
                            if dt_util.parse_datetime(t) is not None
                        ]
                    except (TypeError, ValueError):
                        self._history = []

        # Track moisture sensor changes
        async_track_state_change_event(
            self._hass,
            [self._plant.sensor_moisture.entity_id],
            self._state_changed_event,
        )

    @callback
    def _state_changed_event(self, event):
        """Handle moisture sensor state changes."""
        if self._config.data[FLOW_PLANT_INFO].get(ATTR_IS_NEW_PLANT, False):
            return  # Bei neuer Plant keine Änderungen verarbeiten

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
    _attr_state_class = SensorStateClass.MEASUREMENT

    """Sensor to track fertilizer consumption based on conductivity drop."""


    _attr_has_entity_name = True
    _attr_translation_key = "fertilizer_consumption"
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
        self._attr_unique_id = f"{config.entry_id}-fertilizer-consumption"
        self._attr_native_unit_of_measurement = UNIT_CONDUCTIVITY_MILLI
        self._attr_icon = ICON_FERTILIZER_CONSUMPTION
        self._history = []
        self._last_update = None
        self._attr_native_value = 0  # Starte immer bei 0
        self._last_value = None  # Initialisiere _last_value

        # Bei Neuerstellung explizit auf 0 setzen
        if config.data[FLOW_PLANT_INFO].get(ATTR_IS_NEW_PLANT, False):
            self._attr_native_value = 0
            self._history = []

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(identifiers={(DOMAIN, self._plant.unique_id)})

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional sensor attributes."""
        return {
            "last_update": self._last_update,
        }

    @property
    def extra_restore_state_data(self) -> PlantHistoryExtraStoredData:
        """Das 24h-Fenster über Neustarts hinweg sichern.

        Bewusst nicht als State-Attribut: Attribute schreibt der Recorder bei
        jeder Zustandsänderung vollständig in die Verlaufsdatenbank, was hier
        alle paar Minuten eine komplette Kopie der Messreihe bedeutete. Über
        extra_restore_state_data landen die Daten nur in core.restore_state,
        also genau dort, wo sie für den Neustart gebraucht werden.
        """
        return PlantHistoryExtraStoredData(
            self.native_value,
            self.native_unit_of_measurement,
            [(t.isoformat(), v) for t, v in self._history],
        )

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()

        if not self._config.data[FLOW_PLANT_INFO].get(ATTR_IS_NEW_PLANT, False):
            # Native value über async_get_last_sensor_data (überlebt UNAVAILABLE),
            # fällt auf last_state zurück. KEINE µS→mS Migration mehr — die hat
            # legitime hohe mS-Werte (>100) fälschlich auf /1000 gestaucht und
            # damit kumulative Sensoren bei jedem Restart zerschossen.
            last_data = await self.async_get_last_sensor_data()
            restored = False
            if last_data is not None and last_data.native_value is not None:
                try:
                    self._attr_native_value = float(last_data.native_value)
                    restored = True
                except (TypeError, ValueError):
                    pass
            last_state = await self.async_get_last_state()
            if not restored and last_state and last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                try:
                    self._attr_native_value = float(last_state.state)
                except (TypeError, ValueError):
                    pass
            if last_state:
                if last_state.attributes.get("last_update"):
                    self._last_update = last_state.attributes["last_update"]
                # Neu: aus den Restore-Daten. Der Rückfall auf das alte Attribut
                # greift genau einmal, beim ersten Start nach dem Update.
                extra = await self.async_get_last_extra_data()
                hist_json = None
                if extra is not None:
                    wieder = PlantHistoryExtraStoredData.from_dict(extra.as_dict())
                    if wieder is not None:
                        hist_json = wieder.history
                if not hist_json:
                    hist_json = last_state.attributes.get("history_json")
                if hist_json:
                    try:
                        self._history = [
                            (dt_util.parse_datetime(t), float(v))
                            for t, v in hist_json
                            if dt_util.parse_datetime(t) is not None
                        ]
                    except (TypeError, ValueError):
                        self._history = []

        # Track conductivity sensor changes
        async_track_state_change_event(
            self._hass,
            [self._plant.sensor_conductivity.entity_id],
            self._state_changed_event,
        )

    @callback
    def _state_changed_event(self, event):
        """Handle conductivity sensor state changes."""
        if self._config.data[FLOW_PLANT_INFO].get(ATTR_IS_NEW_PLANT, False):
            return  # Bei neuer Plant keine Änderungen verarbeiten

        new_state = event.data.get("new_state")
        if not new_state or new_state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return

        try:
            current_value = float(new_state.state)
            current_time = dt_util.utcnow()

            # 24h-Rolling-Window analog MoistureConsumption.
            # Summe der positiven Anstiege (µS/cm) im Fenster, umgerechnet auf mS/cm.
            self._history.append((current_time, current_value))
            cutoff_time = current_time - timedelta(hours=24)
            self._history = [(t, v) for t, v in self._history if t >= cutoff_time]

            if len(self._history) >= 2:
                rises_us = sum(
                    self._history[i][1] - self._history[i-1][1]
                    for i in range(1, len(self._history))
                    if self._history[i][1] > self._history[i-1][1]
                )
                self._attr_native_value = round(rises_us / 1000.0, 3)
                self._last_update = current_time.isoformat()
                self.async_write_ha_state()

        except (TypeError, ValueError):
            pass


class PlantTotalWaterConsumption(RestoreSensor):
    # MEASUREMENT (nicht TOTAL_INCREASING) damit Statistics mean/min/max
    # liefern — der Brokkoli-Graph nutzt rangeArea + line, beides braucht
    # diese Felder. Bei TOTAL_INCREASING wären mean/min/max null und der
    # ApexCharts-Renderer wirft "parser Error" beim Multiplizieren mit scale.
    _attr_state_class = SensorStateClass.MEASUREMENT


    _attr_has_entity_name = True
    _attr_translation_key = "total_water_consumption"
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
        self._attr_unique_id = f"{config.entry_id}-total-water-consumption"
        self._attr_native_unit_of_measurement = UNIT_VOLUME
        self._attr_icon = ICON_WATER_CONSUMPTION
        self._attr_entity_category = EntityCategory.DIAGNOSTIC  # Füge Entity-Kategorie hinzu
        self._history = []
        self._last_update = None
        self._last_value = None  # Für Diff-Tracking auf restaurierten Wert
        self._attr_native_value = 0  # Starte immer bei 0
        
        # Bei Neuerstellung explizit auf 0 setzen
        if config.data[FLOW_PLANT_INFO].get(ATTR_IS_NEW_PLANT, False):
            self._attr_native_value = 0
            self._history = []

    @property
    def entity_category(self) -> str:
        """The entity category"""
        return EntityCategory.DIAGNOSTIC

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(identifiers={(DOMAIN, self._plant.unique_id)})

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

        if not self._config.data[FLOW_PLANT_INFO].get(ATTR_IS_NEW_PLANT, False):
            # Native value über async_get_last_sensor_data (überlebt UNAVAILABLE).
            last_data = await self.async_get_last_sensor_data()
            restored = False
            if last_data is not None and last_data.native_value is not None:
                try:
                    self._attr_native_value = float(last_data.native_value)
                    restored = True
                except (TypeError, ValueError):
                    pass
            last_state = await self.async_get_last_state()
            if not restored and last_state and last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                try:
                    self._attr_native_value = float(last_state.state)
                except (TypeError, ValueError):
                    pass
            if last_state and last_state.attributes.get("last_update"):
                self._last_update = last_state.attributes["last_update"]

        # Track moisture sensor changes
        async_track_state_change_event(
            self._hass,
            [self._plant.sensor_moisture.entity_id],
            self._state_changed_event,
        )

    @callback
    def _state_changed_event(self, event):
        """Handle moisture sensor state changes."""
        if self._config.data[FLOW_PLANT_INFO].get(ATTR_IS_NEW_PLANT, False):
            return  # Bei neuer Plant keine Änderungen verarbeiten

        new_state = event.data.get("new_state")
        if not new_state or new_state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return

        try:
            current_value = float(new_state.state)
            current_time = dt_util.utcnow()

            # Diff-Tracking: addiere Drop (% -> Liter) zum bestehenden (restaurierten) Wert.
            # Kein _history-Rebuild — Overwrite würde nach HA-Restart den Total auf 0 setzen.
            if self._last_value is not None and current_value < self._last_value:
                if self._plant.pot_size and self._plant.water_capacity:
                    pot_size = self._plant.pot_size.native_value
                    water_capacity = self._plant.water_capacity.native_value / 100
                    drop_pct = self._last_value - current_value
                    volume = (drop_pct / 100) * pot_size * water_capacity
                    if self._attr_native_value is None:
                        self._attr_native_value = 0
                    self._attr_native_value = round(self._attr_native_value + volume, 2)
                    self._last_update = current_time.isoformat()
                    self.async_write_ha_state()

            self._last_value = current_value

        except (TypeError, ValueError):
            pass


class PlantTotalFertilizerConsumption(RestoreSensor):
    # MEASUREMENT siehe PlantTotalWaterConsumption-Begründung.
    _attr_state_class = SensorStateClass.MEASUREMENT


    _attr_has_entity_name = True
    _attr_translation_key = "total_fertilizer_consumption"
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
        self._attr_unique_id = f"{config.entry_id}-total-fertilizer-consumption"
        self._attr_native_unit_of_measurement = UNIT_CONDUCTIVITY_MILLI
        self._attr_icon = ICON_FERTILIZER_CONSUMPTION
        self._attr_entity_category = EntityCategory.DIAGNOSTIC  # Füge Entity-Kategorie hinzu
        self._history = []
        self._last_update = None
        self._attr_native_value = 0  # Starte immer bei 0
        self._last_value = None  # Initialisiere _last_value
    
        # Bei Neuerstellung explizit auf 0 setzen
        if config.data[FLOW_PLANT_INFO].get(ATTR_IS_NEW_PLANT, False):
            self._attr_native_value = 0
            self._history = []

    @property
    def entity_category(self) -> str:
        """The entity category"""
        return EntityCategory.DIAGNOSTIC

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(identifiers={(DOMAIN, self._plant.unique_id)})

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
                if not self._config.data[FLOW_PLANT_INFO].get(ATTR_IS_NEW_PLANT, False):
                    self._attr_native_value = float(last_state.state)
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
        if self._config.data[FLOW_PLANT_INFO].get(ATTR_IS_NEW_PLANT, False):
            return  # Bei neuer Plant keine Änderungen verarbeiten

        new_state = event.data.get("new_state")
        if not new_state or new_state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return

        try:
            current_value = float(new_state.state)

            # Source-Sensor in µS/cm — akkumuliert in mS/cm (/1000).
            if self._last_value is not None:
                if current_value > self._last_value:
                    increase_milli = (current_value - self._last_value) / 1000.0
                    self._attr_native_value = round(self._attr_native_value + increase_milli, 3)

            # Speichere aktuellen Wert für nächste Berechnung
            self._last_value = current_value
            self.async_write_ha_state()

        except (TypeError, ValueError):
            pass


class PlantCurrentPowerConsumption(RestoreSensor):
    """Power consumption sensor for a plant."""


    _attr_has_entity_name = True
    _attr_translation_key = "current_power_consumption"
    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor."""
        super().__init__()
        self._hass = hass
        self._config = config
        self._plant = plantdevice
        self._attr_unique_id = f"{config.entry_id}-current-power-consumption"
        self._attr_icon = ICON_POWER_CONSUMPTION
        self._attr_native_unit_of_measurement = "W"  # Watt statt kWh
        self._attr_device_class = SensorDeviceClass.POWER  # POWER statt ENERGY
        self._attr_state_class = SensorStateClass.MEASUREMENT  # MEASUREMENT statt TOTAL_INCREASING
        self._last_value = None
        self._last_time = None
        self._attr_native_value = 0  # Starte immer bei 0
        
        # Bei Neuerstellung explizit auf 0 setzen
        if config.data[FLOW_PLANT_INFO].get(ATTR_IS_NEW_PLANT, False):
            self._attr_native_value = 0
            self._last_value = None
            self._last_time = None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(identifiers={(DOMAIN, self._plant.unique_id)})

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()

        if self._plant.total_power_consumption:
            async_track_state_change_event(
                self._hass,
                [self._plant.total_power_consumption.entity_id],
                self._state_changed_event,
            )

    @callback
    def _state_changed_event(self, event):
        """Recalculate Watt only when the cumulative kWh sensor actually changes.

        Poll-based recalculation compared two arbitrary points in time that
        don't necessarily line up with when the source sensor itself ticked,
        so a burst of accumulated kWh landing just after a poll got divided by
        a much-too-short time_diff — producing unrealistic power spikes.
        """
        new_state = event.data.get("new_state")
        if not new_state or new_state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return

        try:
            current_value = float(new_state.state)
            current_time = dt_util.utcnow()

            # Berechne aktuelle Leistung in Watt
            if self._last_value is not None and self._last_time is not None:
                time_diff = (current_time - self._last_time).total_seconds()
                if time_diff > 0:
                    # Umrechnung von kWh/s in Watt
                    power = ((current_value - self._last_value) * 3600 * 1000) / time_diff
                    self._attr_native_value = max(0, round(power, 0))  # Keine Nachkommastellen

            # Speichere aktuelle Werte für nächste Berechnung
            self._last_value = current_value
            self._last_time = current_time
            self.async_write_ha_state()

        except (TypeError, ValueError):
            pass


class PlantTotalPowerConsumption(RestoreSensor):
    """Entity class to calculate total power consumption without 24h window"""


    _attr_has_entity_name = True
    _attr_translation_key = "total_power_consumption"
    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        plant_device: Entity,
    ) -> None:
        """Initialize the sensor."""
        super().__init__()
        self._hass = hass
        self._config = config
        self._plant = plant_device
        self._attr_unique_id = f"{config.entry_id}-total-power-consumption"
        self._external_sensor = config.data[FLOW_PLANT_INFO].get(FLOW_SENSOR_POWER_CONSUMPTION)
        self._attr_icon = ICON_POWER_CONSUMPTION
        self._attr_native_unit_of_measurement = "kWh"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_entity_category = EntityCategory.DIAGNOSTIC  # Füge Entity-Kategorie hinzu
        self._last_value = None
        self._attr_native_value = 0  # Starte immer bei 0
        
        # Bei Neuerstellung explizit auf 0 setzen
        if config.data[FLOW_PLANT_INFO].get(ATTR_IS_NEW_PLANT, False):
            self._attr_native_value = 0
            self._last_value = None

    @property
    def entity_category(self) -> str:
        """The entity category"""
        return EntityCategory.DIAGNOSTIC

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(identifiers={(DOMAIN, self._plant.unique_id)})

    @property
    def external_sensor(self) -> str:
        """The external sensor we are tracking"""
        return self._external_sensor

    @property
    def extra_state_attributes(self) -> dict:
        """Expose external_sensor wie die anderen Plant-Sensoren — sonst kann die
        Card nicht den aktuell konfigurierten Source-Sensor vor-auswählen."""
        return {"external_sensor": self._external_sensor} if self._external_sensor else {}

    def replace_external_sensor(self, new_sensor: str | None) -> None:
        """Modify the external sensor"""
        _LOGGER.info("Setting %s external sensor to %s", self.entity_id, new_sensor)
        self._external_sensor = new_sensor
        if self._external_sensor:
            async_track_state_change_event(
                self._hass,
                [self._external_sensor],
                self._state_changed_event,
            )
        else:
            self._attr_native_value = 0
        # Beim Setup weist die Plattform den externen Sensor zu, bevor
        # async_add_entities die Entity fertig hinzugefuegt hat -- dann ist hass
        # noch None und async_write_ha_state wirft, was den kompletten
        # Plattform-Aufbau abbricht. Den Zustand schreibt HA ohnehin, sobald die
        # Entity hinzugefuegt ist.
        if self.hass is None:
            return
        self.async_write_ha_state()


    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()

        # Restore previous state
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            try:
                if not self._config.data[FLOW_PLANT_INFO].get(ATTR_IS_NEW_PLANT, False):
                    self._attr_native_value = float(last_state.state)
            except (TypeError, ValueError):
                self._attr_native_value = 0

        if self._external_sensor:
            async_track_state_change_event(
                self._hass,
                [self._external_sensor],
                self._state_changed_event,
            )

    @callback
    def _state_changed_event(self, event):
        """Handle changes of the tracked external power-consumption sensor."""
        new_state = event.data.get("new_state")
        if not new_state or new_state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return

        try:
            current_value = float(new_state.state)

            # Berechne nur die Differenz seit dem letzten Wert
            if self._last_value is not None:
                if current_value > self._last_value:  # Nur positive Änderungen
                    increase = current_value - self._last_value
                    self._attr_native_value = round(self._attr_native_value + increase, 3)

            # Speichere aktuellen Wert für nächste Berechnung
            self._last_value = current_value
            self.async_write_ha_state()

        except (TypeError, ValueError):
            pass


# Neue Klasse für Energiekosten
class PlantEnergyCost(RestoreSensor):
    """Sensor für die Energiekosten."""


    _attr_has_entity_name = True
    _attr_translation_key = "energy_cost"
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
        self._attr_unique_id = f"{config.entry_id}_energy_cost"
        self._attr_native_unit_of_measurement = "EUR"
        self._attr_icon = ICON_ENERGY_COST  # Füge das Icon hinzu
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(identifiers={(DOMAIN, self._plant.unique_id)})

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        
        state = await self.async_get_last_state()
        if state:
            try:
                self._attr_native_value = float(state.state)
            except (TypeError, ValueError):
                self._attr_native_value = 0.0

    async def async_update(self) -> None:
        """Update the sensor."""
        if not self._plant.total_power_consumption:
            self._attr_native_value = 0.0
            return

        try:
            total_power = float(self._plant.total_power_consumption.state)
            self._attr_native_value = round(total_power * self._plant.kwh_price, 2)
        except (TypeError, ValueError):
            self._attr_native_value = 0.0


class PlantCurrentPh(PlantCurrentStatus):
    """Entity class for the current pH meter"""


    _attr_has_entity_name = True
    _attr_translation_key = "current_ph"
    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the sensor"""
        self._attr_unique_id = f"{config.entry_id}-current-ph"
        self._external_sensor = config.data[FLOW_PLANT_INFO].get(FLOW_SENSOR_PH)
        self._attr_icon = ICON_PH
        self._attr_native_unit_of_measurement = None  # pH hat keine Einheit
        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self) -> str:
        """Device class"""
        return DEVICE_CLASS_PH  # Verwende unsere eigene Device Class
