"""Max/Min threshold classes for the plant device"""

from __future__ import annotations

import logging

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberMode,
    RestoreNumber,
)
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_NAME,
    ATTR_UNIT_OF_MEASUREMENT,
    LIGHT_LUX,
    PERCENTAGE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import (
    Entity,
    EntityCategory,
    async_generate_entity_id,
)
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util.unit_conversion import TemperatureConverter

from .const import (
    ATTR_CONDUCTIVITY,
    ATTR_LIMITS,
    ATTR_MAX,
    ATTR_MIN,
    CONF_MAX_CONDUCTIVITY,
    CONF_MAX_DLI,
    CONF_MAX_HUMIDITY,
    CONF_MAX_CO2,
    CONF_MAX_ILLUMINANCE,
    CONF_MAX_MOISTURE,
    CONF_MAX_TEMPERATURE,
    CONF_MIN_CONDUCTIVITY,
    CONF_MIN_DLI,
    CONF_MIN_HUMIDITY,
    CONF_MIN_CO2,
    CONF_MIN_ILLUMINANCE,
    CONF_MIN_MOISTURE,
    CONF_MIN_TEMPERATURE,
    CONF_MAX_WATER_CONSUMPTION,
    CONF_MIN_WATER_CONSUMPTION,
    CONF_MAX_FERTILIZER_CONSUMPTION,
    CONF_MIN_FERTILIZER_CONSUMPTION,
    DATA_UPDATED,
    DEFAULT_MAX_CONDUCTIVITY,
    DEFAULT_MAX_DLI,
    DEFAULT_MAX_HUMIDITY,
    DEFAULT_MAX_CO2,
    DEFAULT_MAX_ILLUMINANCE,
    DEFAULT_MAX_MOISTURE,
    DEFAULT_MAX_TEMPERATURE,
    DEFAULT_MAX_WATER_CONSUMPTION,
    DEFAULT_MIN_WATER_CONSUMPTION,
    DEFAULT_MAX_FERTILIZER_CONSUMPTION,
    DEFAULT_MIN_FERTILIZER_CONSUMPTION,
    DEFAULT_MIN_CONDUCTIVITY,
    DEFAULT_MIN_DLI,
    DEFAULT_MIN_HUMIDITY,
    DEFAULT_MIN_CO2,
    DEFAULT_MIN_ILLUMINANCE,
    DEFAULT_MIN_MOISTURE,
    DEFAULT_MIN_TEMPERATURE,
    DOMAIN,
    CYCLE_DOMAIN,
    DEVICE_TYPE_PLANT,
    FLOW_PLANT_INFO,
    FLOW_PLANT_LIMITS,
    READING_CONDUCTIVITY,
    READING_DLI,
    READING_HUMIDITY,
    READING_CO2,
    READING_ILLUMINANCE,
    READING_MOISTURE,
    READING_TEMPERATURE,
    READING_MOISTURE_CONSUMPTION,
    READING_FERTILIZER_CONSUMPTION,
    UNIT_CONDUCTIVITY,
    UNIT_PPFD,
    UNIT_VOLUME,
    ATTR_IS_NEW_PLANT,
    ICON_CONDUCTIVITY,
    ICON_DLI,
    ICON_HUMIDITY,
    ICON_CO2,
    ICON_ILLUMINANCE,
    ICON_MOISTURE,
    ICON_PPFD,
    ICON_TEMPERATURE,
    ICON_WATER_CONSUMPTION,
    ICON_FERTILIZER_CONSUMPTION,
    CONF_MAX_POWER_CONSUMPTION,
    CONF_MIN_POWER_CONSUMPTION,
    DEFAULT_MAX_POWER_CONSUMPTION,
    DEFAULT_MIN_POWER_CONSUMPTION,
    READING_POWER_CONSUMPTION,
    ICON_POWER_CONSUMPTION,
    CONF_MAX_PH,
    CONF_MIN_PH,
    DEFAULT_MAX_PH,
    DEFAULT_MIN_PH,
    ICON_PH,
    READING_PH,
    ATTR_PH,
)

_LOGGER = logging.getLogger(__name__)


class PlantMinMax(RestoreNumber):
    """Parent class for the min/max classes below"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the Plant component."""
        self._config = config
        self._hass = hass
        self._plant = plantdevice
        self._attr_mode = NumberMode.BOX

        # Hole globale Standardwerte
        self._global_config = None
        for entry in self._hass.config_entries.async_entries(DOMAIN):
            if entry.data.get("is_global_config", False):
                self._global_config = entry.data
                break

        # Wähle Domain basierend auf Parent Device Type
        domain = DOMAIN if self._plant.device_type == DEVICE_TYPE_PLANT else CYCLE_DOMAIN
        
        self.entity_id = async_generate_entity_id(
            f"{domain}.{{}}", self.name, current_ids={}
        )
        # Werte aus Config übernehmen
        if hasattr(self, '_attr_native_value') and self._attr_native_value is not None:
            _LOGGER.debug("Using configured value: %s", self._attr_native_value)
        # Icon basierend auf dem Entity-Typ setzen
        if "temperature" in self.entity_id:
            self._attr_icon = ICON_TEMPERATURE
        elif "moisture" in self.entity_id:
            self._attr_icon = ICON_MOISTURE
        elif "conductivity" in self.entity_id:
            self._attr_icon = ICON_CONDUCTIVITY
        elif "humidity" in self.entity_id:
            self._attr_icon = ICON_HUMIDITY
        elif "CO2" in self.entity_id:
            self._attr_icon = ICON_CO2
        elif "illuminance" in self.entity_id:
            self._attr_icon = ICON_ILLUMINANCE
        elif "dli" in self.entity_id:
            self._attr_icon = ICON_DLI

    @property
    def entity_category(self) -> str:
        """The entity category"""
        return EntityCategory.CONFIG

    # @property
    # def unit_of_measurement(self) -> str | None:
    #     """The unit of measurement"""
    #     return self._attr_unit_of_measurement

    def _state_changed_event(self, event: Event) -> None:
        if event.data.get("old_state") is None or event.data.get("new_state") is None:
            return
        if event.data.get("old_state").state == event.data.get("new_state").state:
            self.state_attributes_changed(
                old_attributes=event.data.get("old_state").attributes,
                new_attributes=event.data.get("new_state").attributes,
            )
            return
        self.state_changed(
            old_state=event.data.get("old_state").state,
            new_state=event.data.get("new_state").state,
        )

    def state_changed(self, old_state, new_state):
        """Ensure that we store the state if changed from the UI"""
        _LOGGER.debug(
            "State of %s changed from %s to %s, attr_state = %s",
            self.entity_id,
            old_state,
            new_state,
            self._attr_state,
        )
        self._attr_state = new_state

    def state_attributes_changed(self, old_attributes, new_attributes):
        """Placeholder"""

    def self_updated(self) -> None:
        """Allow the state to be changed from the UI and saved in restore_state."""
        if self._attr_state != self.hass.states.get(self.entity_id).state:
            _LOGGER.debug(
                "Updating state of %s from %s to %s",
                self.entity_id,
                self._attr_state,
                self.hass.states.get(self.entity_id).state,
            )
            self._attr_state = self.hass.states.get(self.entity_id).state
            self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Restore state of thresholds on startup."""
        await super().async_added_to_hass()
        
        # Prüfe ob es eine Neuerstellung ist
        if self._config.data[FLOW_PLANT_INFO].get(ATTR_IS_NEW_PLANT, False):
            # Neue Plant - nutze Config Flow Werte oder globale Standardwerte
            if self._global_config and hasattr(self, 'limit_key'):
                default_key = f"default_{self.limit_key}"
                self._attr_native_value = self._global_config.get(default_key, self.default_value)
            else:
                self._attr_native_value = self._config.data[FLOW_PLANT_INFO][ATTR_LIMITS].get(
                    self.limit_key, self.default_value
                )
        else:
            # Neustart - stelle letzten Zustand wieder her
            state = await self.async_get_last_number_data()
            if state:
                self._attr_native_value = state.native_value
                self._attr_native_unit_of_measurement = state.native_unit_of_measurement

        async_track_state_change_event(
            self._hass,
            list([self.entity_id]),
            self._state_changed_event,
        )

        async_dispatcher_connect(
            self.hass, DATA_UPDATED, self._schedule_immediate_update
        )

    @callback
    def _schedule_immediate_update(self):
        self.async_schedule_update_ha_state(True)

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        self._attr_native_value = value
        self.async_write_ha_state()


class PlantMaxMoisture(PlantMinMax):
    """Entity class for max moisture threshold"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the component."""
        self._attr_name = f"{plantdevice.name} {ATTR_MAX} {READING_MOISTURE}"
        self._attr_native_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MAX_MOISTURE, DEFAULT_MAX_MOISTURE
        )
        self._attr_unique_id = f"{config.entry_id}-max-moisture"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_native_max_value = 100
        self._attr_native_min_value = 0
        self._attr_native_step = 1

        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return f"{SensorDeviceClass.HUMIDITY} threshold"
        # return f"{SensorDeviceClass.MOISTURE} threshold" #FIXME

    limit_key = CONF_MAX_MOISTURE
    default_value = DEFAULT_MAX_MOISTURE


class PlantMinMoisture(PlantMinMax):
    """Entity class for min moisture threshold"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the Plant component."""
        self._attr_name = f"{plantdevice.name} {ATTR_MIN} {READING_MOISTURE}"
        self._attr_native_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MIN_MOISTURE, DEFAULT_MIN_MOISTURE
        )
        self._attr_unique_id = f"{config.entry_id}-min-moisture"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_native_max_value = 100
        self._attr_native_min_value = 0
        self._attr_native_step = 1

        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return f"{SensorDeviceClass.HUMIDITY} threshold"
        # return f"{SensorDeviceClass.MOISTURE} threshold" #FIXME

    limit_key = CONF_MIN_MOISTURE
    default_value = DEFAULT_MIN_MOISTURE


class PlantMaxTemperature(PlantMinMax):
    """Entity class for max temperature threshold"""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity) -> None:
        # Erst die Basisklasse initialisieren
        super().__init__(hass, config, plantdevice)
        
        # Dann können wir auf self._hass zugreifen
        self._attr_name = f"{plantdevice.name} {ATTR_MAX} {READING_TEMPERATURE}"
        self._attr_native_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MAX_TEMPERATURE, DEFAULT_MAX_TEMPERATURE
        )
        self._attr_unique_id = f"{config.entry_id}-max-temperature"
        self.entity_id = async_generate_entity_id(
            f"{DOMAIN}.{{}}", f"{plantdevice.name}_max_temperature", hass=hass
        )
        self._attr_native_unit_of_measurement = self._hass.config.units.temperature_unit
        self._attr_native_max_value = 100
        self._attr_native_min_value = 0
        self._attr_native_step = 1
        self._attr_icon = ICON_TEMPERATURE

    @property
    def device_class(self):
        return f"{SensorDeviceClass.TEMPERATURE} threshold"

    @property
    def not_unit_of_measurement(self) -> str | None:
        """Get unit of measurement from the temperature meter"""
        if (
            not hasattr(self, "_attr_unit_of_measurement")
            or self._attr_native_unit_of_measurement is None
        ):
            self._attr_native_unit_of_measurement = self._default_unit_of_measurement

        if self._plant.sensor_temperature:
            if not self._plant.sensor_temperature.unit_of_measurement:
                return self._attr_native_unit_of_measurement
            if (
                self._attr_native_unit_of_measurement
                != self._plant.sensor_temperature.unit_of_measurement
            ):
                self._attr_native_unit_of_measurement = (
                    self._plant.sensor_temperature.unit_of_measurement
                )

        return self._attr_native_unit_of_measurement

    def state_attributes_changed(self, old_attributes, new_attributes):
        """Calculate C or F"""
        if new_attributes.get(ATTR_UNIT_OF_MEASUREMENT) is None:
            return
        if old_attributes.get(ATTR_UNIT_OF_MEASUREMENT) is None:
            return
        if new_attributes.get(ATTR_UNIT_OF_MEASUREMENT) == old_attributes.get(
            ATTR_UNIT_OF_MEASUREMENT
        ):
            return
        new_state = self._attr_state
        if (
            old_attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "°F"
            and new_attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "°C"
        ):
            new_state = round(
                TemperatureConverter.convert(
                    temperature=float(self.state),
                    from_unit=UnitOfTemperature.FAHRENHEIT,
                    to_unit=UnitOfTemperature.CELSIUS,
                )
            )
            _LOGGER.debug(
                "Changing from F to C measurement is %s new is %s",
                self.state,
                new_state,
            )

        if (
            old_attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "°C"
            and new_attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "°F"
        ):
            new_state = round(
                TemperatureConverter.convert(
                    temperature=float(self.state),
                    from_unit=UnitOfTemperature.CELSIUS,
                    to_unit=UnitOfTemperature.FAHRENHEIT,
                )
            )
            _LOGGER.debug(
                "Changing from C to F measurement is %s new is %s",
                self.state,
                new_state,
            )

        self._hass.states.set(self.entity_id, new_state, new_attributes)

    limit_key = CONF_MAX_TEMPERATURE
    default_value = DEFAULT_MAX_TEMPERATURE


class PlantMinTemperature(PlantMinMax):
    """Entity class for min temperature threshold"""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity) -> None:
        # Erst die Basisklasse initialisieren
        super().__init__(hass, config, plantdevice)
        
        # Dann können wir auf self._hass zugreifen
        self._attr_name = f"{plantdevice.name} {ATTR_MIN} {READING_TEMPERATURE}"
        self._attr_native_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MIN_TEMPERATURE, DEFAULT_MIN_TEMPERATURE
        )
        self._attr_unique_id = f"{config.entry_id}-min-temperature"
        self.entity_id = async_generate_entity_id(
            f"{DOMAIN}.{{}}", f"{plantdevice.name}_min_temperature", hass=hass
        )
        self._attr_native_unit_of_measurement = self._hass.config.units.temperature_unit
        self._attr_native_max_value = 50
        self._attr_native_min_value = -50
        self._attr_native_step = 1
        self._attr_icon = ICON_TEMPERATURE

    @property
    def device_class(self):
        return f"{SensorDeviceClass.TEMPERATURE} threshold"

    @property
    def not_unit_of_measurement(self) -> str | None:
        if (
            not hasattr(self, "_attr_native_unit_of_measurement")
            or self._attr_native_unit_of_measurement is None
        ):
            self._attr_native_unit_of_measurement = self._default_unit_of_measurement

        if self._plant.sensor_temperature:
            if not self._plant.sensor_temperature.unit_of_measurement:
                return self._attr_native_unit_of_measurement
            if (
                self._attr_native_unit_of_measurement
                != self._plant.sensor_temperature.unit_of_measurement
            ):
                self._attr_native_unit_of_measurement = (
                    self._plant.sensor_temperature.unit_of_measurement
                )

        return self._attr_native_unit_of_measurement

    def state_attributes_changed(self, old_attributes, new_attributes):
        """Calculate C or F"""
        if new_attributes.get(ATTR_UNIT_OF_MEASUREMENT) is None:
            return
        if old_attributes.get(ATTR_UNIT_OF_MEASUREMENT) is None:
            return
        if new_attributes.get(ATTR_UNIT_OF_MEASUREMENT) == old_attributes.get(
            ATTR_UNIT_OF_MEASUREMENT
        ):
            return
        new_state = self._attr_state
        if (
            old_attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "°F"
            and new_attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "°C"
        ):
            new_state = round(
                TemperatureConverter.convert(
                    temperature=float(self.state),
                    from_unit=UnitOfTemperature.FAHRENHEIT,
                    to_unit=UnitOfTemperature.CELSIUS,
                )
            )
            _LOGGER.debug(
                "Changing from F to C measurement is %s new is %s",
                self.state,
                new_state,
            )

            # new_state = int(round((int(self.state) - 32) * 0.5556, 0))

        if (
            old_attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "°C"
            and new_attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "°F"
        ):
            new_state = round(
                TemperatureConverter.convert(
                    temperature=float(self.state),
                    from_unit=UnitOfTemperature.CELSIUS,
                    to_unit=UnitOfTemperature.FAHRENHEIT,
                )
            )
            _LOGGER.debug(
                "Changing from C to F measurement is %s new is %s",
                self.state,
                new_state,
            )

        self._hass.states.set(self.entity_id, new_state, new_attributes)

    limit_key = CONF_MIN_TEMPERATURE
    default_value = DEFAULT_MIN_TEMPERATURE


class PlantMaxIlluminance(PlantMinMax):
    """Entity class for max illuminance threshold"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the component."""
        self._attr_name = f"{plantdevice.name} {ATTR_MAX} {READING_ILLUMINANCE}"
        self._attr_native_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MAX_ILLUMINANCE, DEFAULT_MAX_ILLUMINANCE
        )
        self._attr_unique_id = f"{config.entry_id}-max-illuminance"
        self._attr_native_unit_of_measurement = LIGHT_LUX
        self._attr_native_max_value = 200000
        self._attr_native_min_value = 0
        self._attr_native_step = 500
        
        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return f"{SensorDeviceClass.ILLUMINANCE} threshold"

    limit_key = CONF_MAX_ILLUMINANCE
    default_value = DEFAULT_MAX_ILLUMINANCE


class PlantMinIlluminance(PlantMinMax):
    """Entity class for min illuminance threshold"""

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity
    ) -> None:
        """Initialize the component."""
        self._attr_name = f"{plantdevice.name} {ATTR_MIN} {READING_ILLUMINANCE}"
        self._attr_native_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MIN_ILLUMINANCE, DEFAULT_MIN_ILLUMINANCE
        )
        self._attr_unique_id = f"{config.entry_id}-min-illuminance"
        self._attr_native_unit_of_measurement = LIGHT_LUX
        self._attr_native_max_value = 200000
        self._attr_native_min_value = 0
        self._attr_native_step = 500
        
        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return f"{SensorDeviceClass.ILLUMINANCE} threshold"

    limit_key = CONF_MIN_ILLUMINANCE
    default_value = DEFAULT_MIN_ILLUMINANCE


class PlantMaxDli(PlantMinMax):
    """Entity class for max illuminance threshold"""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity) -> None:
        self._attr_name = f"{plantdevice.name} {ATTR_MAX} {READING_DLI}"
        self._attr_native_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MAX_DLI, DEFAULT_MAX_DLI
        )
        self._attr_unique_id = f"{config.entry_id}-max-dli"
        self._attr_native_unit_of_measurement = UNIT_PPFD
        self._attr_native_max_value = 100
        self._attr_native_min_value = 0
        self._attr_native_step = 1
        
        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return f"{SensorDeviceClass.ILLUMINANCE} threshold"

    limit_key = CONF_MAX_DLI
    default_value = DEFAULT_MAX_DLI


class PlantMinDli(PlantMinMax):
    """Entity class for min illuminance threshold"""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity) -> None:
        self._attr_name = f"{plantdevice.name} {ATTR_MIN} {READING_DLI}"
        self._attr_native_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MIN_DLI, DEFAULT_MIN_DLI
        )
        self._attr_unique_id = f"{config.entry_id}-min-dli"
        self._attr_native_unit_of_measurement = UNIT_PPFD
        self._attr_native_max_value = 100
        self._attr_native_min_value = 0
        self._attr_native_step = 1
        
        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return SensorDeviceClass.ILLUMINANCE

    limit_key = CONF_MIN_DLI
    default_value = DEFAULT_MIN_DLI


class PlantMaxConductivity(PlantMinMax):
    """Entity class for max conductivity threshold"""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity) -> None:
        self._attr_name = f"{plantdevice.name} {ATTR_MAX} {READING_CONDUCTIVITY}"
        self._attr_native_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MAX_CONDUCTIVITY, DEFAULT_MAX_CONDUCTIVITY
        )
        self._attr_unique_id = f"{config.entry_id}-max-conductivity"
        self._attr_native_unit_of_measurement = UNIT_CONDUCTIVITY
        self._attr_native_max_value = 3000
        self._attr_native_min_value = 0
        self._attr_native_step = 50
        
        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return f"{ATTR_CONDUCTIVITY} threshold"

    limit_key = CONF_MAX_CONDUCTIVITY
    default_value = DEFAULT_MAX_CONDUCTIVITY


class PlantMinConductivity(PlantMinMax):
    """Entity class for min conductivity threshold"""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity) -> None:
        self._attr_name = f"{plantdevice.name} {ATTR_MIN} {READING_CONDUCTIVITY}"
        self._attr_native_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MIN_CONDUCTIVITY, DEFAULT_MIN_CONDUCTIVITY
        )
        self._attr_unique_id = f"{config.entry_id}-min-conductivity"
        self._attr_native_unit_of_measurement = UNIT_CONDUCTIVITY
        self._attr_native_max_value = 3000
        self._attr_native_min_value = 0
        self._attr_native_step = 50
        
        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return f"{ATTR_CONDUCTIVITY} threshold"

    limit_key = CONF_MIN_CONDUCTIVITY
    default_value = DEFAULT_MIN_CONDUCTIVITY


class PlantMaxHumidity(PlantMinMax):
    """Entity class for max humidity threshold"""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity) -> None:
        self._attr_name = f"{plantdevice.name} {ATTR_MAX} {READING_HUMIDITY}"
        self._attr_native_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MAX_HUMIDITY, DEFAULT_MAX_HUMIDITY
        )
        self._attr_unique_id = f"{config.entry_id}-max-humidity"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_native_max_value = 100
        self._attr_native_min_value = 0
        self._attr_native_step = 1
        
        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return f"{SensorDeviceClass.HUMIDITY} threshold"

    limit_key = CONF_MAX_HUMIDITY
    default_value = DEFAULT_MAX_HUMIDITY


class PlantMinHumidity(PlantMinMax):
    """Entity class for min conductivity threshold"""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity) -> None:
        self._attr_name = f"{plantdevice.name} {ATTR_MIN} {READING_HUMIDITY}"
        self._attr_native_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MIN_HUMIDITY, DEFAULT_MIN_HUMIDITY
        )
        self._attr_unique_id = f"{config.entry_id}-min-humidity"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_native_max_value = 100
        self._attr_native_min_value = 0
        self._attr_native_step = 1
        
        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return f"{SensorDeviceClass.HUMIDITY} threshold"

    limit_key = CONF_MIN_HUMIDITY
    default_value = DEFAULT_MIN_HUMIDITY

class PlantMaxCO2(PlantMinMax):
    """Entity class for max CO2 threshold"""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity) -> None:
        self._attr_name = f"{plantdevice.name} {ATTR_MAX} {READING_CO2}"
        self._attr_native_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MAX_CO2, DEFAULT_MAX_CO2
        )
        self._attr_unique_id = f"{config.entry_id}-max-CO2"
        self._attr_native_unit_of_measurement = "ppm"
        self._attr_native_max_value = 5000
        self._attr_native_min_value = 1000
        self._attr_native_step = 100
        
        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return f"{SensorDeviceClass.CO2} threshold"

    limit_key = CONF_MAX_CO2
    default_value = DEFAULT_MAX_CO2


class PlantMinCO2(PlantMinMax):
    """Entity class for min conductivity threshold"""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity) -> None:
        self._attr_name = f"{plantdevice.name} {ATTR_MIN} {READING_CO2}"
        self._attr_native_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MIN_CO2, DEFAULT_MIN_CO2
        )
        self._attr_unique_id = f"{config.entry_id}-min-CO2"
        self._attr_native_unit_of_measurement = "ppm"
        self._attr_native_max_value = 4000
        self._attr_native_min_value = 0
        self._attr_native_step = 100
        
        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return f"{SensorDeviceClass.CO2} threshold"

    limit_key = CONF_MIN_CO2
    default_value = DEFAULT_MIN_CO2


class PlantMaxWaterConsumption(PlantMinMax):
    """Entity class for max water consumption threshold"""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity) -> None:
        self._attr_name = f"{plantdevice.name} {ATTR_MAX} {READING_MOISTURE_CONSUMPTION}"
        self._attr_native_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MAX_WATER_CONSUMPTION, DEFAULT_MAX_WATER_CONSUMPTION
        )
        self._attr_unique_id = f"{config.entry_id}-max-water-consumption"
        self._attr_native_unit_of_measurement = UNIT_VOLUME
        self._attr_native_max_value = 10
        self._attr_native_min_value = 0
        self._attr_native_step = 0.1
        self._attr_icon = ICON_WATER_CONSUMPTION
        
        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return "water_consumption threshold"

    limit_key = CONF_MAX_WATER_CONSUMPTION
    default_value = DEFAULT_MAX_WATER_CONSUMPTION


class PlantMinWaterConsumption(PlantMinMax):
    """Entity class for min water consumption threshold"""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity) -> None:
        self._attr_name = f"{plantdevice.name} {ATTR_MIN} {READING_MOISTURE_CONSUMPTION}"
        self._attr_native_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MIN_WATER_CONSUMPTION, DEFAULT_MIN_WATER_CONSUMPTION
        )
        self._attr_unique_id = f"{config.entry_id}-min-water-consumption"
        self._attr_native_unit_of_measurement = UNIT_VOLUME
        self._attr_native_max_value = 10
        self._attr_native_min_value = 0
        self._attr_native_step = 0.1
        self._attr_icon = ICON_WATER_CONSUMPTION
        
        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return "water_consumption threshold"

    limit_key = CONF_MIN_WATER_CONSUMPTION
    default_value = DEFAULT_MIN_WATER_CONSUMPTION


class PlantMaxFertilizerConsumption(PlantMinMax):
    """Entity class for max fertilizer consumption threshold"""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity) -> None:
        self._attr_name = f"{plantdevice.name} {ATTR_MAX} {READING_FERTILIZER_CONSUMPTION}"
        self._attr_native_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MAX_FERTILIZER_CONSUMPTION, DEFAULT_MAX_FERTILIZER_CONSUMPTION
        )
        self._attr_unique_id = f"{config.entry_id}-max-fertilizer-consumption"
        self._attr_native_unit_of_measurement = UNIT_CONDUCTIVITY
        self._attr_native_max_value = 3000
        self._attr_native_min_value = 0
        self._attr_native_step = 50
        self._attr_icon = ICON_FERTILIZER_CONSUMPTION
        
        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return "fertilizer_consumption threshold"

    limit_key = CONF_MAX_FERTILIZER_CONSUMPTION
    default_value = DEFAULT_MAX_FERTILIZER_CONSUMPTION


class PlantMinFertilizerConsumption(PlantMinMax):
    """Entity class for min fertilizer consumption threshold"""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity) -> None:
        self._attr_name = f"{plantdevice.name} {ATTR_MIN} {READING_FERTILIZER_CONSUMPTION}"
        self._attr_native_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MIN_FERTILIZER_CONSUMPTION, DEFAULT_MIN_FERTILIZER_CONSUMPTION
        )
        self._attr_unique_id = f"{config.entry_id}-min-fertilizer-consumption"
        self._attr_native_unit_of_measurement = UNIT_CONDUCTIVITY
        self._attr_native_max_value = 3000
        self._attr_native_min_value = 0
        self._attr_native_step = 50
        self._attr_icon = ICON_FERTILIZER_CONSUMPTION
        
        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return "fertilizer_consumption threshold"

    limit_key = CONF_MIN_FERTILIZER_CONSUMPTION
    default_value = DEFAULT_MIN_FERTILIZER_CONSUMPTION


class PlantMaxPowerConsumption(PlantMinMax):
    """Entity class for max power consumption threshold"""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity) -> None:
        self._attr_name = f"{plantdevice.name} {ATTR_MAX} {READING_POWER_CONSUMPTION}"
        self._attr_native_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MAX_POWER_CONSUMPTION, DEFAULT_MAX_POWER_CONSUMPTION
        )
        self._attr_unique_id = f"{config.entry_id}-max-power-consumption"
        self._attr_native_unit_of_measurement = "kWh"
        self._attr_native_max_value = 10
        self._attr_native_min_value = 0
        self._attr_native_step = 0.1
        self._attr_icon = ICON_POWER_CONSUMPTION
        
        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return "power_consumption threshold"

    limit_key = CONF_MAX_POWER_CONSUMPTION
    default_value = DEFAULT_MAX_POWER_CONSUMPTION


class PlantMinPowerConsumption(PlantMinMax):
    """Entity class for min power consumption threshold"""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity) -> None:
        self._attr_name = f"{plantdevice.name} {ATTR_MIN} {READING_POWER_CONSUMPTION}"
        self._attr_native_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MIN_POWER_CONSUMPTION, DEFAULT_MIN_POWER_CONSUMPTION
        )
        self._attr_unique_id = f"{config.entry_id}-min-power-consumption"
        self._attr_native_unit_of_measurement = "kWh"
        self._attr_native_max_value = 10
        self._attr_native_min_value = 0
        self._attr_native_step = 0.1
        self._attr_icon = ICON_POWER_CONSUMPTION
        
        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return "power_consumption threshold"

    limit_key = CONF_MIN_POWER_CONSUMPTION
    default_value = DEFAULT_MIN_POWER_CONSUMPTION


class PlantMaxPh(PlantMinMax):
    """Entity class for max pH threshold"""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity) -> None:
        self._attr_name = f"{plantdevice.name} {ATTR_MAX} {READING_PH}"
        self._attr_native_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MAX_PH, DEFAULT_MAX_PH
        )
        self._attr_unique_id = f"{config.entry_id}-max-ph"
        self._attr_native_unit_of_measurement = None  # pH hat keine Einheit
        self._attr_native_max_value = 14.0  # Maximaler pH-Wert
        self._attr_native_min_value = 0.0  # Minimaler pH-Wert
        self._attr_native_step = 0.1
        self._attr_icon = ICON_PH
        
        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return "ph threshold"

    limit_key = CONF_MAX_PH
    default_value = DEFAULT_MAX_PH


class PlantMinPh(PlantMinMax):
    """Entity class for min pH threshold"""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry, plantdevice: Entity) -> None:
        self._attr_name = f"{plantdevice.name} {ATTR_MIN} {READING_PH}"
        self._attr_native_value = config.data[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].get(
            CONF_MIN_PH, DEFAULT_MIN_PH
        )
        self._attr_unique_id = f"{config.entry_id}-min-ph"
        self._attr_native_unit_of_measurement = None  # pH hat keine Einheit
        self._attr_native_max_value = 14.0  # Maximaler pH-Wert
        self._attr_native_min_value = 0.0  # Minimaler pH-Wert
        self._attr_native_step = 0.1
        self._attr_icon = ICON_PH
        
        super().__init__(hass, config, plantdevice)

    @property
    def device_class(self):
        return "ph threshold"

    limit_key = CONF_MIN_PH
    default_value = DEFAULT_MIN_PH
