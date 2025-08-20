"""Config flow for Custom Plant integration."""
from __future__ import annotations

# Standard Library Imports
import logging
import re
from typing import Any
import urllib.parse

# Third Party Imports
import voluptuous as vol

# Home Assistant Imports
from homeassistant import config_entries, data_entry_flow
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_DOMAIN,
    ATTR_ENTITY_PICTURE,
    ATTR_NAME,
    ATTR_UNIT_OF_MEASUREMENT,
    UnitOfConductivity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.network import NoURLAvailableError, get_url
from homeassistant.helpers.selector import selector

# Local Imports
from .const import (
    AGGREGATION_MEDIAN,
    AGGREGATION_MEAN,
    AGGREGATION_MIN,
    AGGREGATION_MAX,
    AGGREGATION_METHODS,
    AGGREGATION_METHODS_EXTENDED,
    AGGREGATION_ORIGINAL,
    DEFAULT_AGGREGATIONS,
    CONF_AGGREGATION,
    ATTR_NORMALIZE_MOISTURE,
    ATTR_NORMALIZE_WINDOW,
    ATTR_NORMALIZE_PERCENTILE,
    DEFAULT_NORMALIZE_WINDOW,
    DEFAULT_NORMALIZE_PERCENTILE,
    ATTR_ENTITY,
    ATTR_LIMITS,
    ATTR_OPTIONS,
    ATTR_SEARCH_FOR,
    ATTR_SELECT,
    ATTR_SENSORS,
    ATTR_STRAIN,
    ATTR_BREEDER,
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
    CONF_MIN_WATER_CONSUMPTION,
    CONF_MIN_FERTILIZER_CONSUMPTION,
    CONF_MAX_WATER_CONSUMPTION,
    CONF_MAX_FERTILIZER_CONSUMPTION,
    CONF_MIN_POWER_CONSUMPTION,
    CONF_MAX_POWER_CONSUMPTION,
    CONF_MAX_PH,
    CONF_MIN_PH,
    DATA_SOURCE,
    DATA_SOURCE_PLANTBOOK,
    DOMAIN,
    DOMAIN_PLANTBOOK,
    DOMAIN_SENSOR,
    FLOW_CONDUCTIVITY_TRIGGER,
    FLOW_DLI_TRIGGER,
    FLOW_ERROR_NOTFOUND,
    FLOW_FORCE_SPECIES_UPDATE,
    FLOW_HUMIDITY_TRIGGER,
    FLOW_CO2_TRIGGER,
    FLOW_ILLUMINANCE_TRIGGER,
    FLOW_MOISTURE_TRIGGER,
    FLOW_PLANT_INFO,
    FLOW_PLANT_LIMITS,
    FLOW_RIGHT_PLANT,
    FLOW_SENSOR_CONDUCTIVITY,
    FLOW_SENSOR_HUMIDITY,
    FLOW_SENSOR_CO2,
    FLOW_SENSOR_ILLUMINANCE,
    FLOW_SENSOR_MOISTURE,
    FLOW_SENSOR_TEMPERATURE,
    FLOW_SENSOR_POWER_CONSUMPTION,
    FLOW_SENSOR_PH,
    FLOW_STRING_DESCRIPTION,
    FLOW_TEMP_UNIT,
    FLOW_TEMPERATURE_TRIGGER,
    FLOW_WATER_CONSUMPTION_TRIGGER,
    FLOW_FERTILIZER_CONSUMPTION_TRIGGER,
    FLOW_POWER_CONSUMPTION_TRIGGER,
    OPB_DISPLAY_PID,
    DEFAULT_GROWTH_PHASE,
    GROWTH_PHASES,
    ATTR_FLOWERING_DURATION,
    ATTR_WEBSITE,
    ATTR_INFOTEXT1,
    ATTR_INFOTEXT2,
    ATTR_EFFECTS,
    ATTR_SMELL,
    ATTR_TASTE,
    ATTR_LINEAGE,
    ATTR_PHENOTYPE,
    ATTR_HUNGER,
    ATTR_GROWTH_STRETCH,
    ATTR_FLOWER_STRETCH,
    ATTR_MOLD_RESISTANCE,
    ATTR_DIFFICULTY,
    ATTR_YIELD,
    ATTR_NOTES,
    ATTR_IS_NEW_PLANT,
    DEVICE_TYPE_PLANT,
    DEVICE_TYPE_CYCLE,
    DEVICE_TYPE_CONFIG,
    DEVICE_TYPES,
    ATTR_DEVICE_TYPE,
    ATTR_MOISTURE,
    ATTR_CONDUCTIVITY,
    ATTR_POT_SIZE,
    DEFAULT_POT_SIZE,
    ATTR_WATER_CAPACITY,
    DEFAULT_WATER_CAPACITY,
    # Neue Konstanten für Default-Werte
    CONF_DEFAULT_MAX_MOISTURE,
    CONF_DEFAULT_MIN_MOISTURE,
    CONF_DEFAULT_MAX_ILLUMINANCE,
    CONF_DEFAULT_MIN_ILLUMINANCE,
    CONF_DEFAULT_MAX_DLI,
    CONF_DEFAULT_MIN_DLI,
    CONF_DEFAULT_MAX_TEMPERATURE,
    CONF_DEFAULT_MIN_TEMPERATURE,
    CONF_DEFAULT_MAX_CONDUCTIVITY,
    CONF_DEFAULT_MIN_CONDUCTIVITY,
    CONF_DEFAULT_MIN_HUMIDITY,
    CONF_DEFAULT_MIN_CO2,
    CONF_DEFAULT_MAX_HUMIDITY,
    CONF_DEFAULT_MAX_CO2,
    ATTR_ORIGINAL_FLOWERING_DURATION,
    CONF_DEFAULT_MAX_WATER_CONSUMPTION,
    CONF_DEFAULT_MIN_WATER_CONSUMPTION,
    CONF_DEFAULT_MAX_FERTILIZER_CONSUMPTION,
    CONF_DEFAULT_MIN_FERTILIZER_CONSUMPTION,
    CONF_DEFAULT_MAX_POWER_CONSUMPTION,
    CONF_DEFAULT_MIN_POWER_CONSUMPTION,
    CONF_DEFAULT_MAX_PH,
    CONF_DEFAULT_MIN_PH,
    ATTR_KWH_PRICE,
    DEFAULT_KWH_PRICE,
    FLOW_DOWNLOAD_PATH,
    DEFAULT_IMAGE_PATH,
    ATTR_PH,
)
from .plant_helpers import PlantHelper

_LOGGER = logging.getLogger(__name__)


@config_entries.HANDLERS.register(DOMAIN)
class PlantConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Plant."""

    VERSION = 1

    def __init__(self):
        """Initialize flow."""
        self.plant_info = {}
        self.error = None

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)

    async def async_step_import(self, import_input):
        """Importing config from configuration.yaml"""
        _LOGGER.debug(import_input)
        # return FlowResultType.ABORT
        return self.async_create_entry(
            title=import_input[FLOW_PLANT_INFO][ATTR_NAME],
            data=import_input,
        )

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        
        # Prüfe ob bereits ein Konfigurationsknoten existiert
        config_entry_id = None
        for entry in self._async_current_entries():
            if entry.data.get(FLOW_PLANT_INFO, {}).get(ATTR_DEVICE_TYPE) == DEVICE_TYPE_CONFIG:
                config_entry_id = entry.entry_id
                break
        
        if config_entry_id is None:
            # Erstelle den Konfigurationsknoten wenn er noch nicht existiert
            config_data = {
                FLOW_PLANT_INFO: {
                    ATTR_NAME: "Plant Monitor Konfiguration",
                    ATTR_DEVICE_TYPE: DEVICE_TYPE_CONFIG,
                    # Standard Default-Werte
                    CONF_DEFAULT_MAX_MOISTURE: 60,
                    CONF_DEFAULT_MIN_MOISTURE: 20,
                    CONF_DEFAULT_MAX_ILLUMINANCE: 30000,
                    CONF_DEFAULT_MIN_ILLUMINANCE: 1500,
                    CONF_DEFAULT_MAX_DLI: 30,
                    CONF_DEFAULT_MIN_DLI: 8,
                    CONF_DEFAULT_MAX_TEMPERATURE: 30,
                    CONF_DEFAULT_MIN_TEMPERATURE: 10,
                    CONF_DEFAULT_MAX_CONDUCTIVITY: 2000,
                    CONF_DEFAULT_MIN_CONDUCTIVITY: 500,
                    CONF_DEFAULT_MAX_HUMIDITY: 60,
                    CONF_DEFAULT_MAX_CO2: 4000,
                    CONF_DEFAULT_MIN_HUMIDITY: 20,
                    CONF_DEFAULT_MIN_CO2: 300,
                    CONF_DEFAULT_MAX_WATER_CONSUMPTION: 2.0,
                    CONF_DEFAULT_MIN_WATER_CONSUMPTION: 0.1,
                    CONF_DEFAULT_MAX_FERTILIZER_CONSUMPTION: 2000,
                    CONF_DEFAULT_MIN_FERTILIZER_CONSUMPTION: 500,
                    CONF_DEFAULT_MAX_POWER_CONSUMPTION: 10.0,
                    CONF_DEFAULT_MIN_POWER_CONSUMPTION: 0.0,
                    CONF_DEFAULT_MAX_PH: 7.5,
                    CONF_DEFAULT_MIN_PH: 5.5,
                    # Füge kWh Preis hinzu
                    ATTR_KWH_PRICE: DEFAULT_KWH_PRICE,
                    # Default Icon für Cycle
                    "default_cycle_icon": "🔄",
                    "default_icon": "🥦",
                    "default_growth_phase": DEFAULT_GROWTH_PHASE,
                    "default_pot_size": DEFAULT_POT_SIZE,
                    "default_water_capacity": DEFAULT_WATER_CAPACITY,
                    "default_normalize_moisture": False,
                    "default_normalize_window": DEFAULT_NORMALIZE_WINDOW,
                    "default_normalize_percentile": DEFAULT_NORMALIZE_PERCENTILE,

                    # Default Aggregationsmethoden für Cycle
                    "default_growth_phase_aggregation": "min",
                    "default_flowering_duration_aggregation": "mean",
                    "default_pot_size_aggregation": "mean",
                    "default_water_capacity_aggregation": "mean",
                    "default_temperature_aggregation": DEFAULT_AGGREGATIONS['temperature'],
                    "default_moisture_aggregation": DEFAULT_AGGREGATIONS['moisture'],
                    "default_conductivity_aggregation": DEFAULT_AGGREGATIONS['conductivity'],
                    "default_illuminance_aggregation": DEFAULT_AGGREGATIONS['illuminance'],
                    "default_humidity_aggregation": DEFAULT_AGGREGATIONS['humidity'],
                    "default_CO2_aggregation": DEFAULT_AGGREGATIONS['CO2'],
                    "default_ppfd_aggregation": DEFAULT_AGGREGATIONS['ppfd'],
                    "default_dli_aggregation": DEFAULT_AGGREGATIONS['dli'],
                    "default_total_integral_aggregation": DEFAULT_AGGREGATIONS['total_integral'],
                    "default_moisture_consumption_aggregation": DEFAULT_AGGREGATIONS['moisture_consumption'],
                    "default_fertilizer_consumption_aggregation": DEFAULT_AGGREGATIONS['fertilizer_consumption'],
                    "default_total_water_consumption_aggregation": DEFAULT_AGGREGATIONS['total_water_consumption'],
                    "default_total_fertilizer_consumption_aggregation": DEFAULT_AGGREGATIONS['total_fertilizer_consumption'],
                    "default_power_consumption_aggregation": DEFAULT_AGGREGATIONS['power_consumption'],
                    "default_total_power_consumption_aggregation": DEFAULT_AGGREGATIONS['total_power_consumption'],
                    "default_health_aggregation": DEFAULT_AGGREGATIONS['health'],
                    "default_ph_aggregation": DEFAULT_AGGREGATIONS['ph'],
                    # Füge Download-Pfad für Bilder hinzu
                    FLOW_DOWNLOAD_PATH: DEFAULT_IMAGE_PATH,
                    "difficulty": "",
                    "yield": "",
                    "notes": "",
                    "images": [],  # Leeres Array für Bilder
                },
                # Flag um anzuzeigen, dass dies ein Konfigurationsknoten ist
                "is_config": True
            }
            return self.async_create_entry(
                title="Plant Monitor Konfiguration",
                data=config_data
            )

        # Normale Geräteauswahl fortsetzen
        if not user_input:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(ATTR_DEVICE_TYPE): vol.In(DEVICE_TYPES),
                    }
                ),
            )

        if user_input[ATTR_DEVICE_TYPE] == DEVICE_TYPE_CYCLE:
            return await self.async_step_cycle()
        else:
            return await self.async_step_plant()

    async def async_step_cycle(self, user_input=None):
        """Handle cycle configuration."""
        errors = {}

        # Hole die Default-Werte aus dem Konfigurationsknoten
        config_entry = None
        for entry in self._async_current_entries():
            if entry.data.get("is_config", False):
                config_entry = entry
                break

        if config_entry:
            config_data = config_entry.data[FLOW_PLANT_INFO]
        else:
            config_data = {}

        if user_input is not None:
            self.plant_info = {
                ATTR_NAME: user_input[ATTR_NAME],
                ATTR_DEVICE_TYPE: DEVICE_TYPE_CYCLE,
                ATTR_IS_NEW_PLANT: True,
                ATTR_STRAIN: "",
                ATTR_BREEDER: "",
                "growth_phase": DEFAULT_GROWTH_PHASE,
                "plant_emoji": user_input.get("plant_emoji", config_data.get("default_cycle_icon", "")),
                "growth_phase_aggregation": user_input.get("growth_phase_aggregation", config_data.get("default_growth_phase_aggregation", "min")),
                "flowering_duration_aggregation": user_input.get("flowering_duration_aggregation", config_data.get("default_flowering_duration_aggregation", "mean")),
                "pot_size_aggregation": user_input.get("pot_size_aggregation", config_data.get("default_pot_size_aggregation", "mean")),
                "water_capacity_aggregation": user_input.get("water_capacity_aggregation", config_data.get("default_water_capacity_aggregation", "mean")),
                "aggregations": {
                    'temperature': user_input.get('temperature_aggregation', config_data.get("default_temperature_aggregation", DEFAULT_AGGREGATIONS['temperature'])),
                    'moisture': user_input.get('moisture_aggregation', config_data.get("default_moisture_aggregation", DEFAULT_AGGREGATIONS['moisture'])),
                    'conductivity': user_input.get('conductivity_aggregation', config_data.get("default_conductivity_aggregation", DEFAULT_AGGREGATIONS['conductivity'])),
                    'illuminance': user_input.get('illuminance_aggregation', config_data.get("default_illuminance_aggregation", DEFAULT_AGGREGATIONS['illuminance'])),
                    'humidity': user_input.get('humidity_aggregation', config_data.get("default_humidity_aggregation", DEFAULT_AGGREGATIONS['humidity'])),
                    'CO2': user_input.get('CO2_aggregation', config_data.get("default_CO2_aggregation", DEFAULT_AGGREGATIONS['CO2'])),
                    'ppfd': user_input.get('ppfd_aggregation', config_data.get("default_ppfd_aggregation", DEFAULT_AGGREGATIONS['ppfd'])),
                    'dli': user_input.get('dli_aggregation', config_data.get("default_dli_aggregation", DEFAULT_AGGREGATIONS['dli'])),
                    'total_integral': user_input.get('total_integral_aggregation', config_data.get("default_total_integral_aggregation", DEFAULT_AGGREGATIONS['total_integral'])),
                    'moisture_consumption': user_input.get('moisture_consumption_aggregation', config_data.get("default_moisture_consumption_aggregation", DEFAULT_AGGREGATIONS['moisture_consumption'])),
                    'fertilizer_consumption': user_input.get('fertilizer_consumption_aggregation', config_data.get("default_fertilizer_consumption_aggregation", DEFAULT_AGGREGATIONS['fertilizer_consumption'])),
                    'total_water_consumption': user_input.get('total_water_consumption_aggregation', config_data.get("default_total_water_consumption_aggregation", DEFAULT_AGGREGATIONS['total_water_consumption'])),
                    'total_fertilizer_consumption': user_input.get('total_fertilizer_consumption_aggregation', config_data.get("default_total_fertilizer_consumption_aggregation", DEFAULT_AGGREGATIONS['total_fertilizer_consumption'])),
                    'power_consumption': user_input.get('power_consumption_aggregation', config_data.get("default_power_consumption_aggregation", DEFAULT_AGGREGATIONS['power_consumption'])),
                    'total_power_consumption': user_input.get('total_power_consumption_aggregation', config_data.get("default_total_power_consumption_aggregation", DEFAULT_AGGREGATIONS['total_power_consumption'])),
                    'health': user_input.get('health_aggregation', config_data.get("default_health_aggregation", DEFAULT_AGGREGATIONS['health'])),
                    'ph': user_input.get('ph_aggregation', config_data.get("default_ph_aggregation", DEFAULT_AGGREGATIONS['ph'])),
                }
            }
            
            # Nutze PlantHelper für die Standard-Grenzwerte
            plant_helper = PlantHelper(hass=self.hass)
            plant_config = await plant_helper.generate_configentry(
                config={
                    ATTR_NAME: self.plant_info[ATTR_NAME],
                    ATTR_STRAIN: "",
                    ATTR_BREEDER: "",
                    ATTR_SENSORS: {},
                    "plant_emoji": self.plant_info.get("plant_emoji", ""),
                    ATTR_DEVICE_TYPE: DEVICE_TYPE_CYCLE,
                }
            )
            
            # Übernehme die Standard-Grenzwerte
            self.plant_info.update(plant_config[FLOW_PLANT_INFO])
            
            # Erstelle direkt den Entry ohne weitere Schritte
            return self.async_create_entry(
                title=self.plant_info[ATTR_NAME],
                data={FLOW_PLANT_INFO: self.plant_info}
            )

        # Wenn der Aufruf vom Service kommt, nutzen wir die vorgegebenen Daten
        if self.context.get("source_type") == "service":
            return self.async_create_entry(
                title=user_input[ATTR_NAME],
                data={FLOW_PLANT_INFO: {
                    ATTR_NAME: user_input[ATTR_NAME],
                    ATTR_DEVICE_TYPE: DEVICE_TYPE_CYCLE,
                    ATTR_IS_NEW_PLANT: True,
                    ATTR_STRAIN: "",
                    ATTR_BREEDER: "",
                    "growth_phase": DEFAULT_GROWTH_PHASE,
                    "plant_emoji": user_input.get("plant_emoji", ""),
                }}
            )

        data_schema = {
            vol.Required(ATTR_NAME): cv.string,
            vol.Optional("plant_emoji", default=config_data.get("default_cycle_icon", "")): cv.string,
            vol.Optional("growth_phase_aggregation", 
                        default=config_data.get("default_growth_phase_aggregation", "min")): vol.In(["min", "max"]),
            vol.Optional("flowering_duration_aggregation", 
                        default=config_data.get("default_flowering_duration_aggregation", "mean")): vol.In(AGGREGATION_METHODS),
            vol.Optional("pot_size_aggregation", 
                        default=config_data.get("default_pot_size_aggregation", "mean")): vol.In(AGGREGATION_METHODS),
            vol.Optional("water_capacity_aggregation", 
                        default=config_data.get("default_water_capacity_aggregation", "mean")): vol.In(AGGREGATION_METHODS),
            vol.Optional("temperature_aggregation", 
                        default=config_data.get("default_temperature_aggregation", DEFAULT_AGGREGATIONS['temperature'])): vol.In(AGGREGATION_METHODS),
            vol.Optional("moisture_aggregation", 
                        default=config_data.get("default_moisture_aggregation", DEFAULT_AGGREGATIONS['moisture'])): vol.In(AGGREGATION_METHODS),
            vol.Optional("conductivity_aggregation", 
                        default=config_data.get("default_conductivity_aggregation", DEFAULT_AGGREGATIONS['conductivity'])): vol.In(AGGREGATION_METHODS),
            vol.Optional("illuminance_aggregation", 
                        default=config_data.get("default_illuminance_aggregation", DEFAULT_AGGREGATIONS['illuminance'])): vol.In(AGGREGATION_METHODS),
            vol.Optional("humidity_aggregation", 
                        default=config_data.get("default_humidity_aggregation", DEFAULT_AGGREGATIONS['humidity'])): vol.In(AGGREGATION_METHODS),
            vol.Optional("CO2_aggregation", 
                        default=config_data.get("default_CO2_aggregation", DEFAULT_AGGREGATIONS['CO2'])): vol.In(AGGREGATION_METHODS),
            # Erweiterte Aggregationsmethoden für DLI/PPFD
            vol.Optional("ppfd_aggregation", 
                        default=config_data.get("default_ppfd_aggregation", DEFAULT_AGGREGATIONS['ppfd'])): vol.In(AGGREGATION_METHODS_EXTENDED),
            vol.Optional("dli_aggregation", 
                        default=config_data.get("default_dli_aggregation", DEFAULT_AGGREGATIONS['dli'])): vol.In(AGGREGATION_METHODS_EXTENDED),
            vol.Optional("total_integral_aggregation", 
                        default=config_data.get("default_total_integral_aggregation", DEFAULT_AGGREGATIONS['total_integral'])): vol.In(AGGREGATION_METHODS_EXTENDED),
            # Neue Aggregationen für die Diagnosesensoren
            vol.Optional("moisture_consumption_aggregation",
                        default=config_data.get("default_moisture_consumption_aggregation", DEFAULT_AGGREGATIONS['moisture_consumption'])): vol.In(AGGREGATION_METHODS_EXTENDED),
            vol.Optional("fertilizer_consumption_aggregation",
                        default=config_data.get("default_fertilizer_consumption_aggregation", DEFAULT_AGGREGATIONS['fertilizer_consumption'])): vol.In(AGGREGATION_METHODS_EXTENDED),
            vol.Optional("total_water_consumption_aggregation",
                        default=config_data.get("default_total_water_consumption_aggregation", DEFAULT_AGGREGATIONS['total_water_consumption'])): vol.In(AGGREGATION_METHODS_EXTENDED),
            vol.Optional("total_fertilizer_consumption_aggregation",
                        default=config_data.get("default_total_fertilizer_consumption_aggregation", DEFAULT_AGGREGATIONS['total_fertilizer_consumption'])): vol.In(AGGREGATION_METHODS_EXTENDED),
            vol.Optional("power_consumption_aggregation",
                        default=config_data.get("default_power_consumption_aggregation", DEFAULT_AGGREGATIONS['power_consumption'])): vol.In(AGGREGATION_METHODS),
            vol.Optional("total_power_consumption_aggregation",
                        default=config_data.get("default_total_power_consumption_aggregation", DEFAULT_AGGREGATIONS['total_power_consumption'])): vol.In(AGGREGATION_METHODS_EXTENDED),
            vol.Optional("health_aggregation",
                        default=config_data.get("default_health_aggregation", DEFAULT_AGGREGATIONS['health'])): vol.In(AGGREGATION_METHODS),
            vol.Optional("ph_aggregation",
                        default=config_data.get("default_ph_aggregation", DEFAULT_AGGREGATIONS['ph'])): vol.In(AGGREGATION_METHODS),
        }

        return self.async_show_form(
            step_id="cycle",
            data_schema=vol.Schema(data_schema),
            errors=errors,
        )

    async def async_step_plant(self, user_input=None):
        """Handle plant configuration."""
        errors = {}

        # Hole die Default-Werte aus dem Konfigurationsknoten
        config_entry = None
        for entry in self._async_current_entries():
            if entry.data.get("is_config", False):
                config_entry = entry
                break

        if config_entry:
            config_data = config_entry.data[FLOW_PLANT_INFO]
        else:
            config_data = {}

        if user_input is not None:
            self.plant_info = {
                ATTR_NAME: user_input[ATTR_NAME],
                ATTR_DEVICE_TYPE: DEVICE_TYPE_PLANT,
                ATTR_IS_NEW_PLANT: True,
                ATTR_STRAIN: user_input[ATTR_STRAIN],
                ATTR_BREEDER: user_input.get(ATTR_BREEDER, ""),
                "growth_phase": user_input.get("growth_phase", DEFAULT_GROWTH_PHASE),
                "plant_emoji": user_input.get("plant_emoji", "🌱"),
                ATTR_POT_SIZE: user_input.get(ATTR_POT_SIZE, DEFAULT_POT_SIZE),
                ATTR_WATER_CAPACITY: user_input.get(ATTR_WATER_CAPACITY, DEFAULT_WATER_CAPACITY),
                ATTR_NORMALIZE_MOISTURE: user_input.get(ATTR_NORMALIZE_MOISTURE, False),
                ATTR_NORMALIZE_WINDOW: user_input.get(ATTR_NORMALIZE_WINDOW, DEFAULT_NORMALIZE_WINDOW),
                ATTR_NORMALIZE_PERCENTILE: user_input.get(ATTR_NORMALIZE_PERCENTILE, DEFAULT_NORMALIZE_PERCENTILE),
                # Füge die Sensorzuweisungen hinzu
                FLOW_SENSOR_TEMPERATURE: user_input.get(FLOW_SENSOR_TEMPERATURE),
                FLOW_SENSOR_MOISTURE: user_input.get(FLOW_SENSOR_MOISTURE),
                FLOW_SENSOR_CONDUCTIVITY: user_input.get(FLOW_SENSOR_CONDUCTIVITY),
                FLOW_SENSOR_ILLUMINANCE: user_input.get(FLOW_SENSOR_ILLUMINANCE),
                FLOW_SENSOR_HUMIDITY: user_input.get(FLOW_SENSOR_HUMIDITY),
                FLOW_SENSOR_CO2: user_input.get(FLOW_SENSOR_CO2),
                FLOW_SENSOR_POWER_CONSUMPTION: user_input.get(FLOW_SENSOR_POWER_CONSUMPTION),
                FLOW_SENSOR_PH: user_input.get(FLOW_SENSOR_PH),
            }

            plant_helper = PlantHelper(hass=self.hass)
            plant_config = await plant_helper.get_plantbook_data({
                ATTR_STRAIN: self.plant_info[ATTR_STRAIN],
                ATTR_BREEDER: self.plant_info[ATTR_BREEDER]
            })

            if plant_config and plant_config.get(FLOW_PLANT_INFO, {}).get(DATA_SOURCE) == DATA_SOURCE_PLANTBOOK:
                plant_info = plant_config[FLOW_PLANT_INFO]
                # Füge den Namen mit Emoji hinzu
                plant_emoji = self.plant_info.get("plant_emoji", "")
                plant_info[ATTR_NAME] = self.plant_info[ATTR_NAME] + (f" {plant_emoji}" if plant_emoji else "")
                plant_info["plant_emoji"] = plant_emoji
                self.plant_info.update(plant_info)
            else:
                # Wenn keine OpenPlantbook-Daten verfügbar sind, füge trotzdem das Emoji zum Namen hinzu
                plant_emoji = self.plant_info.get("plant_emoji", "")
                self.plant_info[ATTR_NAME] = self.plant_info[ATTR_NAME] + (f" {plant_emoji}" if plant_emoji else "")

            # Wenn der Aufruf vom Service kommt, erstelle direkt den Entry
            if self.context.get("source_type") == "service":
                # Nutze PlantHelper für die Standard-Grenzwerte
                plant_helper = PlantHelper(hass=self.hass)
                plant_config = await plant_helper.generate_configentry(
                    config={
                        ATTR_NAME: self.plant_info[ATTR_NAME],
                        ATTR_STRAIN: self.plant_info[ATTR_STRAIN],
                        ATTR_BREEDER: self.plant_info.get(ATTR_BREEDER, ""),
                        ATTR_SENSORS: {},
                        "plant_emoji": self.plant_info.get("plant_emoji", ""),
                    }
                )
                
                # Übernehme die Standard-Grenzwerte
                self.plant_info.update(plant_config[FLOW_PLANT_INFO])
                
                return self.async_create_entry(
                    title=self.plant_info[ATTR_NAME],
                    data={FLOW_PLANT_INFO: self.plant_info}
                )

            return await self.async_step_limits()

        data_schema = {
            # Basis-Informationen
            vol.Required(ATTR_NAME): cv.string,
            vol.Optional("plant_emoji", default=config_data.get("default_icon")): cv.string,
            vol.Required(ATTR_STRAIN): cv.string,
            vol.Required(ATTR_BREEDER): cv.string,
            vol.Optional("growth_phase", default=config_data.get("default_growth_phase")): vol.In(
                GROWTH_PHASES
            ),
            vol.Optional(ATTR_POT_SIZE, default=config_data.get("default_pot_size")): vol.Coerce(float),
            vol.Optional(ATTR_WATER_CAPACITY, default=config_data.get("default_water_capacity")): vol.Coerce(int),
           
            # Sensor Selektoren
            vol.Optional(FLOW_SENSOR_TEMPERATURE): selector(
                {
                    ATTR_ENTITY: {
                        ATTR_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
                        ATTR_DOMAIN: DOMAIN_SENSOR,
                    }
                }
            ),
            vol.Optional(FLOW_SENSOR_MOISTURE): selector(
                {
                    ATTR_ENTITY: {
                        ATTR_DEVICE_CLASS: SensorDeviceClass.MOISTURE,
                        ATTR_DOMAIN: DOMAIN_SENSOR,
                    }
                }
            ),
            vol.Optional(FLOW_SENSOR_CONDUCTIVITY): selector(
                {
                    ATTR_ENTITY: {
                        ATTR_DEVICE_CLASS: SensorDeviceClass.CONDUCTIVITY,
                        ATTR_DOMAIN: DOMAIN_SENSOR
                    }
                }
            ),
            vol.Optional(FLOW_SENSOR_ILLUMINANCE): selector(
                {
                    ATTR_ENTITY: {
                        ATTR_DEVICE_CLASS: SensorDeviceClass.ILLUMINANCE,
                        ATTR_DOMAIN: DOMAIN_SENSOR,
                    }
                }
            ),
            vol.Optional(FLOW_SENSOR_HUMIDITY): selector(
                {
                    ATTR_ENTITY: {
                        ATTR_DEVICE_CLASS: SensorDeviceClass.HUMIDITY,
                        ATTR_DOMAIN: DOMAIN_SENSOR,
                    }
                }
            ),
            vol.Optional(FLOW_SENSOR_CO2): selector(
                {
                    ATTR_ENTITY: {
                        ATTR_DEVICE_CLASS: SensorDeviceClass.CO2,
                        ATTR_DOMAIN: DOMAIN_SENSOR,
                    }
                }
            ),
            vol.Optional(FLOW_SENSOR_POWER_CONSUMPTION, description={
                "name": "Total Power Consumption Sensor"
            }): selector(
                {
                    ATTR_ENTITY: {
                        ATTR_DEVICE_CLASS: SensorDeviceClass.ENERGY,
                        ATTR_DOMAIN: DOMAIN_SENSOR,
                    }
                }
            ),
            vol.Optional(FLOW_SENSOR_PH, description={
                "name": "Soil pH Sensor"
            }): selector(
                {
                    ATTR_ENTITY: {
                        ATTR_DEVICE_CLASS: SensorDeviceClass.PH,
                        ATTR_DOMAIN: DOMAIN_SENSOR,
                    }
                }
            ),
            
            vol.Optional(ATTR_NORMALIZE_MOISTURE, default=config_data.get("default_normalize_moisture")): cv.boolean,
            vol.Optional(ATTR_NORMALIZE_WINDOW, default=config_data.get("default_normalize_window")): cv.positive_int,
            vol.Optional(ATTR_NORMALIZE_PERCENTILE, default=config_data.get("default_normalize_percentile")): cv.positive_int,
        }

        return self.async_show_form(
            step_id="plant",
            data_schema=vol.Schema(data_schema),
            errors=errors,
            description_placeholders={"opb_search": self.plant_info.get(ATTR_STRAIN)},
        )

    async def async_step_limits(self, user_input=None):
        """Handle limits step."""
        # Get default values from OpenPlantbook
        plant_helper = PlantHelper(hass=self.hass)
        plant_config = await plant_helper.generate_configentry(
            config={
                ATTR_NAME: self.plant_info[ATTR_NAME],
                ATTR_STRAIN: self.plant_info[ATTR_STRAIN],
                ATTR_BREEDER: self.plant_info.get(ATTR_BREEDER, ""),
                ATTR_SENSORS: {},
                "plant_emoji": self.plant_info.get("plant_emoji", ""),
            }
        )

        # Hole die Default-Werte aus dem Konfigurationsknoten
        config_entry = None
        for entry in self._async_current_entries():
            if entry.data.get("is_config", False):
                config_entry = entry
                break

        if config_entry:
            config_data = config_entry.data[FLOW_PLANT_INFO]
        else:
            # Fallback auf Standard-Werte wenn kein Konfigurationsknoten existiert
            config_data = {
                CONF_DEFAULT_MAX_MOISTURE: 60,
                CONF_DEFAULT_MIN_MOISTURE: 20,
                CONF_DEFAULT_MAX_ILLUMINANCE: 30000,
                CONF_DEFAULT_MIN_ILLUMINANCE: 1500,
                CONF_DEFAULT_MAX_DLI: 30,
                CONF_DEFAULT_MIN_DLI: 8,
                CONF_DEFAULT_MAX_TEMPERATURE: 30,
                CONF_DEFAULT_MIN_TEMPERATURE: 10,
                CONF_DEFAULT_MAX_CONDUCTIVITY: 2000,
                CONF_DEFAULT_MIN_CONDUCTIVITY: 500,
                CONF_DEFAULT_MAX_HUMIDITY: 60,
                CONF_DEFAULT_MAX_CO2: 4000,
                CONF_DEFAULT_MIN_HUMIDITY: 20,
                CONF_DEFAULT_MIN_CO2: 300,
                CONF_DEFAULT_MAX_WATER_CONSUMPTION: 2.0,
                CONF_DEFAULT_MIN_WATER_CONSUMPTION: 0.1,
                CONF_DEFAULT_MAX_FERTILIZER_CONSUMPTION: 2000,
                CONF_DEFAULT_MIN_FERTILIZER_CONSUMPTION: 500,
                CONF_DEFAULT_MAX_POWER_CONSUMPTION: 10.0,
                CONF_DEFAULT_MIN_POWER_CONSUMPTION: 0.0,
            }

        if user_input is not None:
            _LOGGER.debug("User Input %s", user_input)
            # Validate user input
            valid = await self.validate_step_3(user_input)
            if valid:
                if FLOW_RIGHT_PLANT in user_input and not user_input[FLOW_RIGHT_PLANT]:
                    # User says this is not the right plant
                    # Reset the search and go back to step 1
                    self.plant_info[ATTR_SEARCH_FOR] = ""
                    return await self.async_step_user()

                # Store info to use in next step
                self.plant_info[ATTR_LIMITS] = {}
                for key in user_input:
                    if key in [
                        CONF_MAX_MOISTURE,
                        CONF_MIN_MOISTURE,
                        CONF_MAX_ILLUMINANCE,
                        CONF_MIN_ILLUMINANCE,
                        CONF_MAX_DLI,
                        CONF_MIN_DLI,
                        CONF_MAX_TEMPERATURE,
                        CONF_MIN_TEMPERATURE,
                        CONF_MAX_CONDUCTIVITY,
                        CONF_MIN_CONDUCTIVITY,
                        CONF_MAX_HUMIDITY,
                        CONF_MAX_CO2,
                        CONF_MIN_HUMIDITY,
                        CONF_MIN_CO2,
                        CONF_MAX_WATER_CONSUMPTION,
                        CONF_MIN_WATER_CONSUMPTION,
                        CONF_MAX_FERTILIZER_CONSUMPTION,
                        CONF_MIN_FERTILIZER_CONSUMPTION,
                        CONF_MAX_POWER_CONSUMPTION,
                        CONF_MIN_POWER_CONSUMPTION,
                        CONF_MAX_PH,
                        CONF_MIN_PH,
                    ]:
                        self.plant_info[ATTR_LIMITS][key] = user_input[key]

                if OPB_DISPLAY_PID in user_input:
                    self.plant_info[OPB_DISPLAY_PID] = user_input[OPB_DISPLAY_PID]
                if ATTR_ENTITY_PICTURE not in user_input or not user_input[ATTR_ENTITY_PICTURE]:
                    # Wenn kein Bild im user_input ist, nehmen wir das aus OpenPlantbook
                    self.plant_info[ATTR_ENTITY_PICTURE] = plant_config[FLOW_PLANT_INFO].get(ATTR_ENTITY_PICTURE, "")
                else:
                    # Sonst nehmen wir das vom User eingegebene Bild
                    self.plant_info[ATTR_ENTITY_PICTURE] = user_input[ATTR_ENTITY_PICTURE]
                if ATTR_FLOWERING_DURATION in user_input:
                    try:
                        duration = int(user_input[ATTR_FLOWERING_DURATION])
                        self.plant_info[ATTR_FLOWERING_DURATION] = duration
                        # Setze auch original_flowering_duration wenn der User den Wert manuell ändert
                        self.plant_info[ATTR_ORIGINAL_FLOWERING_DURATION] = duration
                    except (ValueError, TypeError):
                        self.plant_info[ATTR_FLOWERING_DURATION] = 0
                        self.plant_info[ATTR_ORIGINAL_FLOWERING_DURATION] = 0

                # Speichere alle zusätzlichen Attribute
                for attr in ["pid", "type", "feminized", "timestamp", 
                            "website", "infotext1", "infotext2", 
                            "effects", "smell", "taste", "lineage",
                            ATTR_PHENOTYPE, ATTR_HUNGER, ATTR_GROWTH_STRETCH,
                            ATTR_FLOWER_STRETCH, ATTR_MOLD_RESISTANCE, ATTR_DIFFICULTY,
                            ATTR_YIELD, ATTR_NOTES]:
                    # Für pid und timestamp nehmen wir die Werte aus plant_config wenn sie nicht im user_input sind
                    if attr in ["pid", "timestamp"]:
                        self.plant_info[attr] = str(plant_config[FLOW_PLANT_INFO].get(attr, ""))
                    elif attr in user_input:
                        self.plant_info[attr] = str(user_input[attr])

                _LOGGER.debug("Plant info after saving: %s", self.plant_info)
                return await self.async_step_limits_done()

        data_schema = {}
        extra_desc = ""
        if plant_config[FLOW_PLANT_INFO].get(OPB_DISPLAY_PID):
            # We got data from OPB.  Display a "wrong plant" switch
            data_schema[vol.Optional(FLOW_RIGHT_PLANT, default=True)] = cv.boolean
            display_pid = plant_config[FLOW_PLANT_INFO].get(OPB_DISPLAY_PID)
        else:
            display_pid = self.plant_info[ATTR_STRAIN].title()

        data_schema[
            vol.Optional(
                OPB_DISPLAY_PID,
                description={"suggested_value": display_pid}
            )
        ] = cv.string

        data_schema[
            vol.Optional(
                ATTR_BREEDER,
                default=plant_config[FLOW_PLANT_INFO].get(ATTR_BREEDER, "")
            )
        ] = str

        # Füge Blütezeit zwischen Breeder und Sorte hinzu
        flowering_duration = plant_config[FLOW_PLANT_INFO].get(ATTR_FLOWERING_DURATION, 0)
        try:
            flowering_duration = int(flowering_duration)
        except (ValueError, TypeError):
            flowering_duration = 0

        data_schema[
            vol.Optional(
                ATTR_FLOWERING_DURATION,
                default=flowering_duration
            )
        ] = vol.Coerce(int)

        data_schema[
            vol.Optional(
                "type",
                default=plant_config[FLOW_PLANT_INFO].get("type", "")
            )
        ] = str

        data_schema[
            vol.Optional(
                "feminized",
                default=plant_config[FLOW_PLANT_INFO].get("feminized", "")
            )
        ] = str

        data_schema[
            vol.Optional(
                "effects",
                default=plant_config[FLOW_PLANT_INFO].get("effects", "")
            )
        ] = str

        data_schema[
            vol.Optional(
                "smell",
                default=plant_config[FLOW_PLANT_INFO].get("smell", "")
            )
        ] = str

        data_schema[
            vol.Optional(
                "taste",
                default=plant_config[FLOW_PLANT_INFO].get("taste", "")
            )
        ] = str

        # Benutzerdefinierte Felder
        for attr in [ATTR_PHENOTYPE, ATTR_HUNGER, ATTR_GROWTH_STRETCH,
                    ATTR_FLOWER_STRETCH, ATTR_MOLD_RESISTANCE, ATTR_DIFFICULTY,
                    ATTR_YIELD, ATTR_NOTES]:
            data_schema[
                vol.Optional(
                    attr,
                    default=plant_config[FLOW_PLANT_INFO].get(attr, "")
                )
            ] = str

        data_schema[
            vol.Optional(
                "website",
                default=plant_config[FLOW_PLANT_INFO].get("website", "")
            )
        ] = str

        data_schema[
            vol.Optional(
                "lineage",
                default=plant_config[FLOW_PLANT_INFO].get("lineage", "")
            )
        ] = str

        data_schema[
            vol.Optional(
                "infotext1",
                default=plant_config[FLOW_PLANT_INFO].get("infotext1", "")
            )
        ] = str

        data_schema[
            vol.Optional(
                "infotext2",
                default=plant_config[FLOW_PLANT_INFO].get("infotext2", "")
            )
        ] = str

        # Speichern der benutzerdefinierten Attribute
        if user_input is not None:
            for attr in [ATTR_PHENOTYPE, ATTR_HUNGER, ATTR_GROWTH_STRETCH, 
                        ATTR_FLOWER_STRETCH, ATTR_MOLD_RESISTANCE, ATTR_DIFFICULTY, 
                        ATTR_YIELD, ATTR_NOTES]:
                if attr in user_input:
                    self.plant_info[attr] = str(user_input[attr])

        # Get entity_picture from config
        entity_picture = plant_config[FLOW_PLANT_INFO].get(ATTR_ENTITY_PICTURE)
        preview_picture = entity_picture  # Speichere original Pfad für Vorschau

        if entity_picture and not entity_picture.startswith("http"):
            try:
                # Nur für die Vorschau die volle URL generieren
                preview_picture = f"{get_url(self.hass, require_current_request=True)}{urllib.parse.quote(entity_picture)}"
            except NoURLAvailableError:
                _LOGGER.error(
                    "No internal or external url found. Please configure these in HA General Settings"
                )
                preview_picture = ""

        # Füge die Grenzwerte hinzu
        data_schema[vol.Optional(CONF_MAX_MOISTURE, default=int(config_data.get(CONF_DEFAULT_MAX_MOISTURE, 60)))] = int
        data_schema[vol.Optional(CONF_MIN_MOISTURE, default=int(config_data.get(CONF_DEFAULT_MIN_MOISTURE, 20)))] = int
        data_schema[vol.Optional(CONF_MAX_ILLUMINANCE, default=int(config_data.get(CONF_DEFAULT_MAX_ILLUMINANCE, 30000)))] = int
        data_schema[vol.Optional(CONF_MIN_ILLUMINANCE, default=int(config_data.get(CONF_DEFAULT_MIN_ILLUMINANCE, 1500)))] = int
        data_schema[vol.Optional(CONF_MAX_DLI, default=float(config_data.get(CONF_DEFAULT_MAX_DLI, 30)))] = int
        data_schema[vol.Optional(CONF_MIN_DLI, default=float(config_data.get(CONF_DEFAULT_MIN_DLI, 8)))] = int
        data_schema[vol.Optional(CONF_MAX_TEMPERATURE, default=int(config_data.get(CONF_DEFAULT_MAX_TEMPERATURE, 30)))] = int
        data_schema[vol.Optional(CONF_MIN_TEMPERATURE, default=int(config_data.get(CONF_DEFAULT_MIN_TEMPERATURE, 10)))] = int
        data_schema[vol.Optional(CONF_MAX_CONDUCTIVITY, default=int(config_data.get(CONF_DEFAULT_MAX_CONDUCTIVITY, 2000)))] = int
        data_schema[vol.Optional(CONF_MIN_CONDUCTIVITY, default=int(config_data.get(CONF_DEFAULT_MIN_CONDUCTIVITY, 500)))] = int
        data_schema[vol.Optional(CONF_MAX_HUMIDITY, default=int(config_data.get(CONF_DEFAULT_MAX_HUMIDITY, 60)))] = int
        data_schema[vol.Optional(CONF_MIN_HUMIDITY, default=int(config_data.get(CONF_DEFAULT_MIN_HUMIDITY, 20)))] = int
        data_schema[vol.Optional(CONF_MAX_CO2, default=int(config_data.get(CONF_DEFAULT_MAX_CO2, 4000)))] = int
        data_schema[vol.Optional(CONF_MIN_CO2, default=int(config_data.get(CONF_DEFAULT_MIN_CO2, 300)))] = int
        data_schema[vol.Optional(CONF_MAX_WATER_CONSUMPTION, default=float(config_data.get(CONF_DEFAULT_MAX_WATER_CONSUMPTION, 2.0)))] = cv.positive_float
        data_schema[vol.Optional(CONF_MIN_WATER_CONSUMPTION, default=float(config_data.get(CONF_DEFAULT_MIN_WATER_CONSUMPTION, 0.1)))] = cv.positive_float
        data_schema[vol.Optional(CONF_MAX_FERTILIZER_CONSUMPTION, default=int(config_data.get(CONF_DEFAULT_MAX_FERTILIZER_CONSUMPTION, 2000)))] = int
        data_schema[vol.Optional(CONF_MIN_FERTILIZER_CONSUMPTION, default=int(config_data.get(CONF_DEFAULT_MIN_FERTILIZER_CONSUMPTION, 500)))] = int
        data_schema[vol.Optional(CONF_MAX_POWER_CONSUMPTION, default=float(config_data.get(CONF_DEFAULT_MAX_POWER_CONSUMPTION, 10.0)))] = cv.positive_float
        data_schema[vol.Optional(CONF_MIN_POWER_CONSUMPTION, default=float(config_data.get(CONF_DEFAULT_MIN_POWER_CONSUMPTION, 0.0)))] = cv.positive_float
        data_schema[vol.Optional(CONF_MAX_PH, default=float(config_data.get(CONF_DEFAULT_MAX_PH, 7.5)))] = cv.positive_float
        data_schema[vol.Optional(CONF_MIN_PH, default=float(config_data.get(CONF_DEFAULT_MIN_PH, 5.5)))] = cv.positive_float
        
        # Für das Eingabefeld den originalen Pfad verwenden
        data_schema[vol.Optional(ATTR_ENTITY_PICTURE, description={"suggested_value": entity_picture})] = str

        return self.async_show_form(
            step_id="limits",
            data_schema=vol.Schema(data_schema),
            description_placeholders={
                ATTR_ENTITY_PICTURE: preview_picture,  # Für die Vorschau die volle URL
                ATTR_NAME: self.plant_info.get(ATTR_NAME),
                FLOW_TEMP_UNIT: self.hass.config.units.temperature_unit,
                "br": "<br />",
                "extra_desc": extra_desc,
            },
        )

    async def async_step_limits_done(self, user_input=None):
        """After limits are set"""
        return self.async_create_entry(
            title=self.plant_info[ATTR_NAME],
            data={FLOW_PLANT_INFO: self.plant_info},
        )

    async def validate_step_1(self, user_input):
        """Validate step one"""
        _LOGGER.debug("Validating step 1: %s", user_input)
        return True

    async def validate_step_2(self, user_input):
        """Validate step two"""
        _LOGGER.debug("Validating step 2: %s", user_input)

        if not ATTR_STRAIN in user_input:
            return False
        if not isinstance(user_input[ATTR_STRAIN], str):
            return False
        if len(user_input[ATTR_STRAIN]) < 5:
            return False
        _LOGGER.debug("Valid")

        return True

    async def validate_step_3(self, user_input):
        """Validate step three"""
        _LOGGER.debug("Validating step 3: %s", user_input)

        return True

    async def validate_step_4(self, user_input):
        """Validate step four"""
        return True

    async def async_abort(self, reason: str):
        """Handle config flow abort."""
        if self.plant_info:
            self.plant_info[ATTR_IS_NEW_PLANT] = False
            # Update existing config entries if needed
            for entry in self._async_current_entries():
                if entry.data[FLOW_PLANT_INFO].get(ATTR_IS_NEW_PLANT):
                    data = dict(entry.data)
                    data[FLOW_PLANT_INFO][ATTR_IS_NEW_PLANT] = False
                    self.hass.config_entries.async_update_entry(entry, data=data)
        return self.async_abort(reason=reason)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handling opetions for plant"""

    def __init__(
        self,
        entry: config_entries.ConfigEntry,
    ) -> None:
        """Initialize options flow."""
        self.entry = entry
        self.is_config = entry.data.get("is_config", False)
        if not self.is_config:
            entry.async_on_unload(entry.add_update_listener(self.update_plant_options))
            self.plant = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Manage the options."""
        if user_input is not None:
            if self.is_config:
                # Für Konfigurationsknoten nur die Default-Werte aktualisieren
                data = dict(self.entry.data)
                defaults_changed = False
                
                # Neue Default-Einstellungen
                default_fields = {
                    "default_icon": "default_icon",
                    "default_growth_phase": "default_growth_phase",
                    "default_pot_size": "default_pot_size",
                    "default_water_capacity": "default_water_capacity",
                    "default_normalize_moisture": "default_normalize_moisture",
                    "default_normalize_window": "default_normalize_window",
                    "default_normalize_percentile": "default_normalize_percentile",
                    CONF_DEFAULT_MAX_MOISTURE: CONF_DEFAULT_MAX_MOISTURE,
                    CONF_DEFAULT_MIN_MOISTURE: CONF_DEFAULT_MIN_MOISTURE,
                    CONF_DEFAULT_MAX_ILLUMINANCE: CONF_DEFAULT_MAX_ILLUMINANCE,
                    CONF_DEFAULT_MIN_ILLUMINANCE: CONF_DEFAULT_MIN_ILLUMINANCE,
                    CONF_DEFAULT_MAX_DLI: CONF_DEFAULT_MAX_DLI,
                    CONF_DEFAULT_MIN_DLI: CONF_DEFAULT_MIN_DLI,
                    CONF_DEFAULT_MAX_TEMPERATURE: CONF_DEFAULT_MAX_TEMPERATURE,
                    CONF_DEFAULT_MIN_TEMPERATURE: CONF_DEFAULT_MIN_TEMPERATURE,
                    CONF_DEFAULT_MAX_CONDUCTIVITY: CONF_DEFAULT_MAX_CONDUCTIVITY,
                    CONF_DEFAULT_MIN_CONDUCTIVITY: CONF_DEFAULT_MIN_CONDUCTIVITY,
                    CONF_DEFAULT_MAX_HUMIDITY: CONF_DEFAULT_MAX_HUMIDITY,
                    CONF_DEFAULT_MIN_HUMIDITY: CONF_DEFAULT_MIN_HUMIDITY,
                    CONF_DEFAULT_MAX_CO2: CONF_DEFAULT_MAX_CO2,
                    CONF_DEFAULT_MIN_CO2: CONF_DEFAULT_MIN_CO2,
                    CONF_DEFAULT_MAX_WATER_CONSUMPTION: CONF_DEFAULT_MAX_WATER_CONSUMPTION,
                    CONF_DEFAULT_MIN_WATER_CONSUMPTION: CONF_DEFAULT_MIN_WATER_CONSUMPTION,
                    CONF_DEFAULT_MAX_FERTILIZER_CONSUMPTION: CONF_DEFAULT_MAX_FERTILIZER_CONSUMPTION,
                    CONF_DEFAULT_MIN_FERTILIZER_CONSUMPTION: CONF_DEFAULT_MIN_FERTILIZER_CONSUMPTION,
                    CONF_DEFAULT_MAX_POWER_CONSUMPTION: CONF_DEFAULT_MAX_POWER_CONSUMPTION,
                    CONF_DEFAULT_MIN_POWER_CONSUMPTION: CONF_DEFAULT_MIN_POWER_CONSUMPTION,
                    CONF_DEFAULT_MAX_PH: CONF_DEFAULT_MAX_PH,
                    CONF_DEFAULT_MIN_PH: CONF_DEFAULT_MIN_PH,
                    # Cycle-spezifische Defaults
                    "default_cycle_icon": "default_cycle_icon",
                    "default_growth_phase_aggregation": "default_growth_phase_aggregation",
                    "default_flowering_duration_aggregation": "default_flowering_duration_aggregation",
                    "default_pot_size_aggregation": "default_pot_size_aggregation",
                    "default_water_capacity_aggregation": "default_water_capacity_aggregation",
                    "default_temperature_aggregation": "default_temperature_aggregation",
                    "default_moisture_aggregation": "default_moisture_aggregation",
                    "default_conductivity_aggregation": "default_conductivity_aggregation",
                    "default_illuminance_aggregation": "default_illuminance_aggregation",
                    "default_humidity_aggregation": "default_humidity_aggregation",
                    "default_CO2_aggregation": "default_CO2_aggregation",
                    "default_ppfd_aggregation": "default_ppfd_aggregation",
                    "default_dli_aggregation": "default_dli_aggregation",
                    "default_total_integral_aggregation": "default_total_integral_aggregation",
                    "default_moisture_consumption_aggregation": "default_moisture_consumption_aggregation",
                    "default_fertilizer_consumption_aggregation": "default_fertilizer_consumption_aggregation",
                    "default_total_water_consumption_aggregation": "default_total_water_consumption_aggregation",
                    "default_total_fertilizer_consumption_aggregation": "default_total_fertilizer_consumption_aggregation",
                    "default_power_consumption_aggregation": "default_power_consumption_aggregation",
                    "default_total_power_consumption_aggregation": "default_total_power_consumption_aggregation",
                    "default_health_aggregation": "default_health_aggregation",
                    "default_ph_aggregation": "default_ph_aggregation",
                    # Füge Download-Pfad hinzu
                    FLOW_DOWNLOAD_PATH: FLOW_DOWNLOAD_PATH,
                }
                
                for default_key, limit_key in default_fields.items():
                    if default_key in user_input:
                        old_value = data[FLOW_PLANT_INFO].get(default_key)
                        new_value = user_input[default_key]
                        if new_value != old_value:
                            defaults_changed = True
                            data[FLOW_PLANT_INFO][default_key] = new_value

                if defaults_changed:
                    self.hass.config_entries.async_update_entry(self.entry, data=data)

                return self.async_create_entry(title="", data=user_input)
            else:
                # Normale Plant/Cycle Optionen
                self.plant = self.hass.data[DOMAIN][self.entry.entry_id]["plant"]
                
                # Prüfe ob sich Sensorzuweisungen geändert haben
                sensor_changed = False
                data = dict(self.entry.data)
                
                # Prüfe Änderungen für jeden Sensor-Typ
                sensor_mappings = {
                    FLOW_SENSOR_TEMPERATURE: self.plant.sensor_temperature,
                    FLOW_SENSOR_MOISTURE: self.plant.sensor_moisture,
                    FLOW_SENSOR_CONDUCTIVITY: self.plant.sensor_conductivity,
                    FLOW_SENSOR_ILLUMINANCE: self.plant.sensor_illuminance,
                    FLOW_SENSOR_HUMIDITY: self.plant.sensor_humidity,
                    FLOW_SENSOR_CO2: self.plant.sensor_CO2,
                    FLOW_SENSOR_POWER_CONSUMPTION: self.plant.total_power_consumption,
                    FLOW_SENSOR_PH: self.plant.sensor_ph,  # pH-Sensor zur Liste hinzufügen
                }
                
                for sensor_key, current_sensor in sensor_mappings.items():
                    new_sensor = user_input.get(sensor_key)
                    if new_sensor is not None:
                        old_sensor = data[FLOW_PLANT_INFO].get(sensor_key, "")
                        if new_sensor != old_sensor:
                            sensor_changed = True
                            data[FLOW_PLANT_INFO][sensor_key] = new_sensor
                            if current_sensor and hasattr(current_sensor, 'replace_external_sensor'):
                                current_sensor.replace_external_sensor(new_sensor)

                if sensor_changed:
                    self.hass.config_entries.async_update_entry(self.entry, data=data)

                # Prüfe ob sich Normalisierungseinstellungen geändert haben
                if self.plant.device_type == DEVICE_TYPE_PLANT:
                    normalize_changed = False
                    data = dict(self.entry.data)
                    
                    new_normalize = user_input.get(ATTR_NORMALIZE_MOISTURE)
                    new_window = user_input.get(ATTR_NORMALIZE_WINDOW)
                    new_percentile = user_input.get(ATTR_NORMALIZE_PERCENTILE)
                    
                    if new_normalize is not None:
                        old_normalize = data[FLOW_PLANT_INFO].get(ATTR_NORMALIZE_MOISTURE, False)
                        if new_normalize != old_normalize:
                            normalize_changed = True
                        data[FLOW_PLANT_INFO][ATTR_NORMALIZE_MOISTURE] = new_normalize
                        
                    if new_window is not None:
                        old_window = data[FLOW_PLANT_INFO].get(ATTR_NORMALIZE_WINDOW, DEFAULT_NORMALIZE_WINDOW)
                        if new_window != old_window:
                            normalize_changed = True
                        data[FLOW_PLANT_INFO][ATTR_NORMALIZE_WINDOW] = new_window
                        
                    if new_percentile is not None:
                        old_percentile = data[FLOW_PLANT_INFO].get(ATTR_NORMALIZE_PERCENTILE, DEFAULT_NORMALIZE_PERCENTILE)
                        if new_percentile != old_percentile:
                            normalize_changed = True
                        data[FLOW_PLANT_INFO][ATTR_NORMALIZE_PERCENTILE] = new_percentile

                    if normalize_changed:
                        self.hass.config_entries.async_update_entry(self.entry, data=data)
                        
                        # Sensoren direkt aktualisieren
                        if self.plant.sensor_moisture:
                            self.plant.sensor_moisture._normalize = new_normalize
                            self.plant.sensor_moisture._normalize_window = new_window
                            self.plant.sensor_moisture._normalize_percentile = new_percentile
                            self.plant.sensor_moisture._max_moisture = None
                            self.plant.sensor_moisture._last_normalize_update = None
                            await self.plant.sensor_moisture.async_update()
                        
                        if self.plant.sensor_conductivity:
                            self.plant.sensor_conductivity._normalize = new_normalize
                            await self.plant.sensor_conductivity.async_update()

                # Bestehende Validierung für andere Felder
                if ATTR_STRAIN in user_input and not re.match(r"\w+", user_input[ATTR_STRAIN]):
                    user_input[ATTR_STRAIN] = ""
                if ATTR_ENTITY_PICTURE in user_input and not re.match(r"(\/)?\w+", user_input[ATTR_ENTITY_PICTURE]):
                    user_input[ATTR_ENTITY_PICTURE] = ""
                if OPB_DISPLAY_PID in user_input and not re.match(r"\w+", user_input[OPB_DISPLAY_PID]):
                    user_input[OPB_DISPLAY_PID] = ""

                return self.async_create_entry(title="", data=user_input)

        # Erstelle das Formular basierend auf dem Typ
        data_schema = {}
        
        if self.is_config:
            # Formular für Konfigurationsknoten
            data_schema.update({
                vol.Optional(
                    "default_icon",
                    default=self.entry.data[FLOW_PLANT_INFO].get("default_icon","🥦")
                ): str,
                vol.Optional(
                    "default_growth_phase",
                    default=self.entry.data[FLOW_PLANT_INFO].get("default_growth_phase", DEFAULT_GROWTH_PHASE)
                ): vol.In(GROWTH_PHASES),
                vol.Optional(
                    "default_pot_size",
                    default=self.entry.data[FLOW_PLANT_INFO].get("default_pot_size", DEFAULT_POT_SIZE)
                ): vol.Coerce(float),
                vol.Optional(
                    "default_water_capacity",
                    default=self.entry.data[FLOW_PLANT_INFO].get("default_water_capacity", DEFAULT_WATER_CAPACITY)
                ): vol.Coerce(int),
                vol.Optional(
                    CONF_DEFAULT_MAX_MOISTURE,
                    default=self.entry.data[FLOW_PLANT_INFO].get(CONF_DEFAULT_MAX_MOISTURE, 60)
                ): int,
                vol.Optional(
                    CONF_DEFAULT_MIN_MOISTURE,
                    default=self.entry.data[FLOW_PLANT_INFO].get(CONF_DEFAULT_MIN_MOISTURE, 20)
                ): int,
                vol.Optional(
                    CONF_DEFAULT_MAX_ILLUMINANCE,
                    default=self.entry.data[FLOW_PLANT_INFO].get(CONF_DEFAULT_MAX_ILLUMINANCE, 30000)
                ): int,
                vol.Optional(
                    CONF_DEFAULT_MIN_ILLUMINANCE,
                    default=self.entry.data[FLOW_PLANT_INFO].get(CONF_DEFAULT_MIN_ILLUMINANCE, 1500)
                ): int,
                vol.Optional(
                    CONF_DEFAULT_MAX_DLI,
                    default=self.entry.data[FLOW_PLANT_INFO].get(CONF_DEFAULT_MAX_DLI, 30)
                ): int,
                vol.Optional(
                    CONF_DEFAULT_MIN_DLI,
                    default=self.entry.data[FLOW_PLANT_INFO].get(CONF_DEFAULT_MIN_DLI, 8)
                ): int,
                vol.Optional(
                    CONF_DEFAULT_MAX_TEMPERATURE,
                    default=self.entry.data[FLOW_PLANT_INFO].get(CONF_DEFAULT_MAX_TEMPERATURE, 30)
                ): int,
                vol.Optional(
                    CONF_DEFAULT_MIN_TEMPERATURE,
                    default=self.entry.data[FLOW_PLANT_INFO].get(CONF_DEFAULT_MIN_TEMPERATURE, 10)
                ): int,
                vol.Optional(
                    CONF_DEFAULT_MAX_CONDUCTIVITY,
                    default=self.entry.data[FLOW_PLANT_INFO].get(CONF_DEFAULT_MAX_CONDUCTIVITY, 2000)
                ): int,
                vol.Optional(
                    CONF_DEFAULT_MIN_CONDUCTIVITY,
                    default=self.entry.data[FLOW_PLANT_INFO].get(CONF_DEFAULT_MIN_CONDUCTIVITY, 500)
                ): int,
                vol.Optional(
                    CONF_DEFAULT_MAX_HUMIDITY,
                    default=self.entry.data[FLOW_PLANT_INFO].get(CONF_DEFAULT_MAX_HUMIDITY, 60)
                ): int,
                vol.Optional(
                    CONF_DEFAULT_MAX_CO2,
                    default=self.entry.data[FLOW_PLANT_INFO].get(CONF_DEFAULT_MAX_CO2, 60)
                ): int,
                vol.Optional(
                    CONF_DEFAULT_MIN_HUMIDITY,
                    default=self.entry.data[FLOW_PLANT_INFO].get(CONF_DEFAULT_MIN_HUMIDITY, 20)
                ): int,
                vol.Optional(
                    CONF_DEFAULT_MIN_CO2,
                    default=self.entry.data[FLOW_PLANT_INFO].get(CONF_DEFAULT_MIN_CO2, 20)
                ): int,
                vol.Optional(
                    CONF_DEFAULT_MAX_WATER_CONSUMPTION,
                    default=self.entry.data[FLOW_PLANT_INFO].get(CONF_DEFAULT_MAX_WATER_CONSUMPTION, 2.0)
                ): cv.positive_float,
                vol.Optional(
                    CONF_DEFAULT_MIN_WATER_CONSUMPTION,
                    default=self.entry.data[FLOW_PLANT_INFO].get(CONF_DEFAULT_MIN_WATER_CONSUMPTION, 0.1)
                ): cv.positive_float,
                vol.Optional(
                    CONF_DEFAULT_MAX_FERTILIZER_CONSUMPTION,
                    default=self.entry.data[FLOW_PLANT_INFO].get(CONF_DEFAULT_MAX_FERTILIZER_CONSUMPTION, 2000)
                ): int,
                vol.Optional(
                    CONF_DEFAULT_MIN_FERTILIZER_CONSUMPTION,
                    default=self.entry.data[FLOW_PLANT_INFO].get(CONF_DEFAULT_MIN_FERTILIZER_CONSUMPTION, 500)
                ): int,
                vol.Optional(
                    CONF_DEFAULT_MAX_POWER_CONSUMPTION,
                    default=self.entry.data[FLOW_PLANT_INFO].get(CONF_DEFAULT_MAX_POWER_CONSUMPTION, 10.0)
                ): cv.positive_float,
                vol.Optional(
                    CONF_DEFAULT_MIN_POWER_CONSUMPTION,
                    default=self.entry.data[FLOW_PLANT_INFO].get(CONF_DEFAULT_MIN_POWER_CONSUMPTION, 0.0)
                ): cv.positive_float,
                vol.Optional(
                    "default_normalize_moisture",
                    default=self.entry.data[FLOW_PLANT_INFO].get("default_normalize_moisture", False)
                ): cv.boolean,
                vol.Optional(
                    "default_normalize_window",
                    default=self.entry.data[FLOW_PLANT_INFO].get("default_normalize_window", DEFAULT_NORMALIZE_WINDOW)
                ): cv.positive_int,
                vol.Optional(
                    "default_normalize_percentile",
                    default=self.entry.data[FLOW_PLANT_INFO].get("default_normalize_percentile", DEFAULT_NORMALIZE_PERCENTILE)
                ): cv.positive_int,
                vol.Optional(
                    "default_cycle_icon",
                    default=self.entry.data[FLOW_PLANT_INFO].get("default_cycle_icon", "🔄")
                ): str,
                vol.Optional(
                    "default_growth_phase_aggregation",
                    default=self.entry.data[FLOW_PLANT_INFO].get("default_growth_phase_aggregation", "min")
                ): vol.In(["min", "max"]),
                vol.Optional(
                    "default_flowering_duration_aggregation",
                    default=self.entry.data[FLOW_PLANT_INFO].get("default_flowering_duration_aggregation", "max")
                ): vol.In(AGGREGATION_METHODS),
                vol.Optional(
                    "default_pot_size_aggregation",
                    default=self.entry.data[FLOW_PLANT_INFO].get("default_pot_size_aggregation", "max")
                ): vol.In(AGGREGATION_METHODS),
                vol.Optional(
                    "default_water_capacity_aggregation",
                    default=self.entry.data[FLOW_PLANT_INFO].get("default_water_capacity_aggregation", "max")
                ): vol.In(AGGREGATION_METHODS),
                vol.Optional(
                    "default_temperature_aggregation",
                    default=self.entry.data[FLOW_PLANT_INFO].get("default_temperature_aggregation", DEFAULT_AGGREGATIONS['temperature'])
                ): vol.In(AGGREGATION_METHODS),
                vol.Optional(
                    "default_moisture_aggregation",
                    default=self.entry.data[FLOW_PLANT_INFO].get("default_moisture_aggregation", DEFAULT_AGGREGATIONS['moisture'])
                ): vol.In(AGGREGATION_METHODS),
                vol.Optional(
                    "default_conductivity_aggregation",
                    default=self.entry.data[FLOW_PLANT_INFO].get("default_conductivity_aggregation", DEFAULT_AGGREGATIONS['conductivity'])
                ): vol.In(AGGREGATION_METHODS),
                vol.Optional(
                    "default_illuminance_aggregation",
                    default=self.entry.data[FLOW_PLANT_INFO].get("default_illuminance_aggregation", DEFAULT_AGGREGATIONS['illuminance'])
                ): vol.In(AGGREGATION_METHODS),
                vol.Optional(
                    "default_humidity_aggregation",
                    default=self.entry.data[FLOW_PLANT_INFO].get("default_humidity_aggregation", DEFAULT_AGGREGATIONS['humidity'])
                ): vol.In(AGGREGATION_METHODS),
                vol.Optional(
                    "default_co2_aggregation",
                    default=self.entry.data[FLOW_PLANT_INFO].get("default_co2_aggregation", DEFAULT_AGGREGATIONS['co2'])
                ): vol.In(AGGREGATION_METHODS),
                vol.Optional(
                    "default_dli_aggregation",
                    default=self.entry.data[FLOW_PLANT_INFO].get("default_dli_aggregation", DEFAULT_AGGREGATIONS['dli'])
                ): vol.In(AGGREGATION_METHODS_EXTENDED),
                vol.Optional(
                    "default_power_consumption_aggregation",
                    default=self.entry.data[FLOW_PLANT_INFO].get("default_power_consumption_aggregation", DEFAULT_AGGREGATIONS['power_consumption'])
                ): vol.In(AGGREGATION_METHODS_EXTENDED),     
                vol.Optional(
                    "default_ppfd_aggregation",
                    default=self.entry.data[FLOW_PLANT_INFO].get("default_ppfd_aggregation", DEFAULT_AGGREGATIONS['ppfd'])
                ): vol.In(AGGREGATION_METHODS_EXTENDED),
                vol.Optional(
                    "default_total_integral_aggregation",
                    default=self.entry.data[FLOW_PLANT_INFO].get("default_total_integral_aggregation", DEFAULT_AGGREGATIONS['total_integral'])
                ): vol.In(AGGREGATION_METHODS_EXTENDED),
                vol.Optional(
                    "default_moisture_consumption_aggregation",
                    default=self.entry.data[FLOW_PLANT_INFO].get("default_moisture_consumption_aggregation", DEFAULT_AGGREGATIONS['moisture_consumption'])
                ): vol.In(AGGREGATION_METHODS_EXTENDED),
                vol.Optional(
                    "default_fertilizer_consumption_aggregation",
                    default=self.entry.data[FLOW_PLANT_INFO].get("default_fertilizer_consumption_aggregation", DEFAULT_AGGREGATIONS['fertilizer_consumption'])
                ): vol.In(AGGREGATION_METHODS_EXTENDED),
                vol.Optional(
                    "default_total_water_consumption_aggregation",
                    default=self.entry.data[FLOW_PLANT_INFO].get("default_total_water_consumption_aggregation", DEFAULT_AGGREGATIONS['total_water_consumption'])
                ): vol.In(AGGREGATION_METHODS_EXTENDED),
                vol.Optional(
                    "default_total_fertilizer_consumption_aggregation",
                    default=self.entry.data[FLOW_PLANT_INFO].get("default_total_fertilizer_consumption_aggregation", DEFAULT_AGGREGATIONS['total_fertilizer_consumption'])
                ): vol.In(AGGREGATION_METHODS_EXTENDED),
                vol.Optional(
                    "default_total_power_consumption_aggregation",
                    default=self.entry.data[FLOW_PLANT_INFO].get("default_total_power_consumption_aggregation", DEFAULT_AGGREGATIONS['total_power_consumption'])
                ): vol.In(AGGREGATION_METHODS_EXTENDED),
                vol.Optional(
                    "default_health_aggregation",
                    default=self.entry.data[FLOW_PLANT_INFO].get("default_health_aggregation", DEFAULT_AGGREGATIONS['health'])
                ): vol.In(AGGREGATION_METHODS),
                vol.Optional(
                    "default_ph_aggregation",
                    default=self.entry.data[FLOW_PLANT_INFO].get("default_ph_aggregation", DEFAULT_AGGREGATIONS['ph'])
                ): vol.In(AGGREGATION_METHODS),
                vol.Optional(
                    ATTR_KWH_PRICE,
                    default=self.entry.data[FLOW_PLANT_INFO].get(ATTR_KWH_PRICE, DEFAULT_KWH_PRICE)
                ): vol.Coerce(float),
                vol.Optional(
                    FLOW_DOWNLOAD_PATH,
                    default=self.entry.data[FLOW_PLANT_INFO].get(FLOW_DOWNLOAD_PATH, DEFAULT_IMAGE_PATH)
                ): str,
            })
        else:
            # Normale Plant/Cycle Optionen
            self.plant = self.hass.data[DOMAIN][self.entry.entry_id]["plant"]
            plant_helper = PlantHelper(hass=self.hass)
            
            # Nur für Plants, nicht für Cycles
            if self.plant.device_type == DEVICE_TYPE_PLANT:
                data_schema[
                    vol.Optional(
                        ATTR_STRAIN, description={"suggested_value": self.plant.pid}
                    )
                ] = cv.string
                if plant_helper.has_openplantbook and self.plant.pid:
                    data_schema[vol.Optional(FLOW_FORCE_SPECIES_UPDATE, default=False)] = (
                        cv.boolean
                    )

                display_strain = self.plant.display_strain or ""
                data_schema[
                    vol.Optional(
                        OPB_DISPLAY_PID, description={"suggested_value": display_strain}
                    )
                ] = str
                entity_picture = self.plant.entity_picture or ""
                data_schema[
                    vol.Optional(
                        ATTR_ENTITY_PICTURE, description={"suggested_value": entity_picture}
                    )
                ] = str

                # Füge Normalisierungseinstellungen hinzu
                current_normalize = self.entry.data[FLOW_PLANT_INFO].get(ATTR_NORMALIZE_MOISTURE, False)
                current_window = self.entry.data[FLOW_PLANT_INFO].get(ATTR_NORMALIZE_WINDOW, DEFAULT_NORMALIZE_WINDOW)
                current_percentile = self.entry.data[FLOW_PLANT_INFO].get(ATTR_NORMALIZE_PERCENTILE, DEFAULT_NORMALIZE_PERCENTILE)

                data_schema[
                    vol.Optional(ATTR_NORMALIZE_MOISTURE, default=current_normalize)
                ] = cv.boolean
                data_schema[
                    vol.Optional(ATTR_NORMALIZE_WINDOW, default=current_window)
                ] = cv.positive_int
                data_schema[
                    vol.Optional(ATTR_NORMALIZE_PERCENTILE, default=current_percentile)
                ] = cv.positive_int

                # Füge Sensor-Auswahl hinzu
                # Hole alle verfügbaren Sensoren
                sensor_entities = {}
                for entity_id in self.hass.states.async_entity_ids("sensor"):
                    state = self.hass.states.get(entity_id)
                    if state is None:
                        continue
                        
                    device_class = state.attributes.get("device_class", "")
                    unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT, "")
                    
                    # Gruppiere Sensoren nach Device Class
                    if device_class == SensorDeviceClass.TEMPERATURE:
                        sensor_entities.setdefault("temperature", []).append(entity_id)
                    elif device_class == SensorDeviceClass.HUMIDITY:
                        sensor_entities.setdefault("humidity", []).append(entity_id)
                    elif device_class == SensorDeviceClass.CO2:
                        sensor_entities.setdefault("CO2", []).append(entity_id)
                    elif device_class == SensorDeviceClass.ILLUMINANCE:
                        sensor_entities.setdefault("illuminance", []).append(entity_id)
                    elif device_class == SensorDeviceClass.MOISTURE:
                        sensor_entities.setdefault("moisture", []).append(entity_id)
                    elif device_class == SensorDeviceClass.CONDUCTIVITY:  # Korrekte Device Class
                        sensor_entities.setdefault("conductivity", []).append(entity_id)
                    elif device_class == SensorDeviceClass.ENERGY:  # Füge Power Consumption hinzu
                        sensor_entities.setdefault("energy", []).append(entity_id)
                    elif device_class == SensorDeviceClass.PH or device_class == "ph":
                        sensor_entities.setdefault("ph", []).append(entity_id)

                # Füge Sensor-Auswahlfelder hinzu
                if sensor_entities.get("temperature"):
                    data_schema[
                        vol.Optional(FLOW_SENSOR_TEMPERATURE, default=self.plant.sensor_temperature.external_sensor if self.plant.sensor_temperature else None)
                    ] = selector(
                        {
                            ATTR_ENTITY: {
                                ATTR_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
                                ATTR_DOMAIN: DOMAIN_SENSOR,
                            }
                        }
                    )

                if sensor_entities.get("moisture"):
                    data_schema[
                        vol.Optional(FLOW_SENSOR_MOISTURE, default=self.plant.sensor_moisture.external_sensor if self.plant.sensor_moisture else None)
                    ] = selector(
                        {
                            ATTR_ENTITY: {
                                ATTR_DEVICE_CLASS: SensorDeviceClass.MOISTURE,
                                ATTR_DOMAIN: DOMAIN_SENSOR,
                            }
                        }
                    )

                if sensor_entities.get("conductivity"):
                    data_schema[
                        vol.Optional(FLOW_SENSOR_CONDUCTIVITY, default=self.plant.sensor_conductivity.external_sensor if self.plant.sensor_conductivity else None)
                    ] = selector(
                        {
                            ATTR_ENTITY: {
                                ATTR_DEVICE_CLASS: SensorDeviceClass.CONDUCTIVITY,
                                ATTR_DOMAIN: DOMAIN_SENSOR
                            }
                        }
                    )

                if sensor_entities.get("illuminance"):
                    data_schema[
                        vol.Optional(FLOW_SENSOR_ILLUMINANCE, default=self.plant.sensor_illuminance.external_sensor if self.plant.sensor_illuminance else None)
                    ] = selector(
                        {
                            ATTR_ENTITY: {
                                ATTR_DEVICE_CLASS: SensorDeviceClass.ILLUMINANCE,
                                ATTR_DOMAIN: DOMAIN_SENSOR,
                            }
                        }
                    )

                if sensor_entities.get("humidity"):
                    data_schema[
                        vol.Optional(FLOW_SENSOR_HUMIDITY, default=self.plant.sensor_humidity.external_sensor if self.plant.sensor_humidity else None)
                    ] = selector(
                        {
                            ATTR_ENTITY: {
                                ATTR_DEVICE_CLASS: SensorDeviceClass.HUMIDITY,
                                ATTR_DOMAIN: DOMAIN_SENSOR,
                            }
                        }
                    )

                if sensor_entities.get("co2"):
                    data_schema[
                        vol.Optional(FLOW_SENSOR_CO2, default=self.plant.sensor_co2.external_sensor if self.plant.sensor_co2 else None)
                    ] = selector(
                        {
                            ATTR_ENTITY: {
                                ATTR_DEVICE_CLASS: SensorDeviceClass.CO2,
                                ATTR_DOMAIN: DOMAIN_SENSOR,
                            }
                        }
                    )

                if sensor_entities.get("energy"):
                    data_schema[
                        vol.Optional(FLOW_SENSOR_POWER_CONSUMPTION, default=self.plant.total_power_consumption.external_sensor if hasattr(self.plant.total_power_consumption, 'external_sensor') else None)
                    ] = selector(
                        {
                            ATTR_ENTITY: {
                                ATTR_DEVICE_CLASS: SensorDeviceClass.ENERGY,
                                ATTR_DOMAIN: DOMAIN_SENSOR,
                            }
                        }
                    )

                # Füge pH-Sensor-Auswahlfeld hinzu
                if sensor_entities.get("ph"):
                    data_schema[
                        vol.Optional(FLOW_SENSOR_PH, default=self.plant.sensor_ph.external_sensor if self.plant.sensor_ph else None)
                    ] = selector(
                        {
                            ATTR_ENTITY: {
                                ATTR_DEVICE_CLASS: SensorDeviceClass.PH,
                                ATTR_DOMAIN: DOMAIN_SENSOR,
                            }
                        }
                    )

            # Gemeinsame Trigger-Optionen für Plants und Cycles
            data_schema[
                vol.Optional(
                    FLOW_ILLUMINANCE_TRIGGER, default=self.plant.illuminance_trigger
                )
            ] = cv.boolean
            data_schema[vol.Optional(FLOW_DLI_TRIGGER, default=self.plant.dli_trigger)] = (
                cv.boolean
            )
            data_schema[
                vol.Optional(FLOW_HUMIDITY_TRIGGER, default=self.plant.humidity_trigger)
            ] = cv.boolean
            data_schema[
                vol.Optional(FLOW_CO2_TRIGGER, default=self.plant.co2_trigger)
            ] = cv.boolean
            data_schema[
                vol.Optional(
                    FLOW_TEMPERATURE_TRIGGER, default=self.plant.temperature_trigger
                )
            ] = cv.boolean
            data_schema[
                vol.Optional(FLOW_MOISTURE_TRIGGER, default=self.plant.moisture_trigger)
            ] = cv.boolean
            data_schema[
                vol.Optional(
                    FLOW_CONDUCTIVITY_TRIGGER, default=self.plant.conductivity_trigger
                )
            ] = cv.boolean
            data_schema[
                vol.Optional(
                    FLOW_WATER_CONSUMPTION_TRIGGER, default=self.plant.water_consumption_trigger
                )
            ] = cv.boolean
            data_schema[
                vol.Optional(
                    FLOW_FERTILIZER_CONSUMPTION_TRIGGER, default=self.plant.fertilizer_consumption_trigger
                )
            ] = cv.boolean
            data_schema[
                vol.Optional(
                    FLOW_POWER_CONSUMPTION_TRIGGER, default=self.plant.power_consumption_trigger
                )
            ] = cv.boolean

        return self.async_show_form(step_id="init", data_schema=vol.Schema(data_schema))

    async def update_plant_options(
        self, hass: HomeAssistant, entry: config_entries.ConfigEntry
    ):
        """Handle options update."""
        _LOGGER.debug(
            "Update plant options begin for %s Data %s, Options: %s",
            entry.entry_id,
            entry.options,
            entry.data,
        )

        # Bild-Update
        entity_picture = entry.options.get(ATTR_ENTITY_PICTURE)
        if entity_picture is not None:
            if entity_picture == "":
                self.plant.add_image(entity_picture)
            else:
                # Entferne doppelte Slashes
                entity_picture = entity_picture.replace('//', '/')
                try:
                    if entity_picture.startswith("/local/"):
                        # Lokaler Pfad
                        url = cv.path(entity_picture)
                    else:
                        # Externe URL
                        url = cv.url(entity_picture)
                    _LOGGER.debug("Valid image path/url: %s", url)
                    self.plant.add_image(entity_picture)
                except vol.Invalid as exc:
                    _LOGGER.warning("Invalid image path/url: %s - %s", entity_picture, exc)

        # Display Strain Update
        new_display_strain = entry.options.get(OPB_DISPLAY_PID)
        if new_display_strain is not None:
            self.plant.display_strain = new_display_strain

        # Strain Update
        new_strain = entry.options.get(ATTR_STRAIN)
        force_new_strain = entry.options.get(FLOW_FORCE_SPECIES_UPDATE)
        
        if new_strain is not None and force_new_strain:
            _LOGGER.debug("Updating strain to: %s", new_strain)
            plant_helper = PlantHelper(hass=self.hass)
            plant_config = await plant_helper.generate_configentry(
                config={
                    ATTR_STRAIN: new_strain,
                    ATTR_ENTITY_PICTURE: entity_picture,
                    OPB_DISPLAY_PID: new_display_strain,
                    FLOW_FORCE_SPECIES_UPDATE: force_new_strain,
                }
            )
            
            if plant_config.get(DATA_SOURCE) == DATA_SOURCE_PLANTBOOK:
                # Update plant info
                self.plant.add_image(plant_config[FLOW_PLANT_INFO][ATTR_ENTITY_PICTURE])
                self.plant.display_strain = plant_config[FLOW_PLANT_INFO][OPB_DISPLAY_PID]
                
                # Update thresholds
                if FLOW_PLANT_LIMITS in plant_config[FLOW_PLANT_INFO]:
                    for key, value in plant_config[FLOW_PLANT_INFO][FLOW_PLANT_LIMITS].items():
                        set_entity = getattr(self.plant, key, None)
                        if set_entity:
                            set_entity_id = set_entity.entity_id
                            _LOGGER.debug("Setting %s to %s", set_entity_id, value)
                            self.hass.states.async_set(
                                set_entity_id,
                                new_state=value,
                                attributes=self.hass.states.get(set_entity_id).attributes,
                            )

            # Reset force update flag
            options = dict(entry.options)
            options[FLOW_FORCE_SPECIES_UPDATE] = False
            options[OPB_DISPLAY_PID] = self.plant.display_strain
            options[ATTR_ENTITY_PICTURE] = self.plant.entity_picture
            
            hass.config_entries.async_update_entry(entry, options=options)

        _LOGGER.debug("Update plant options done for %s", entry.entry_id)
        self.plant.update_registry()

