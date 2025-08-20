"""Services for plant integration."""
import logging
import voluptuous as vol
import aiohttp
import os
from datetime import datetime
import asyncio
import json
import zipfile
import shutil
import csv
import io
import re
from statistics import mean, median

from homeassistant.core import HomeAssistant, ServiceCall, callback, ServiceResponse
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.const import ATTR_NAME, ATTR_ENTITY_PICTURE
from homeassistant.exceptions import HomeAssistantError
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import selector
from homeassistant.helpers.template import Template
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.core import SupportsResponse
from homeassistant.components.recorder import history, get_instance

from .const import (
    DOMAIN,
    ATTR_PLANT,
    ATTR_SENSORS,
    FLOW_PLANT_INFO,
    SERVICE_REPLACE_SENSOR,
    SERVICE_REMOVE_PLANT,
    SERVICE_CREATE_PLANT,
    SERVICE_CREATE_CYCLE,
    SERVICE_MOVE_TO_CYCLE,
    SERVICE_REMOVE_CYCLE,
    ATTR_STRAIN,
    ATTR_BREEDER,
    DEFAULT_GROWTH_PHASE,
    FLOW_SENSOR_TEMPERATURE,
    FLOW_SENSOR_MOISTURE,
    FLOW_SENSOR_CONDUCTIVITY,
    FLOW_SENSOR_ILLUMINANCE,
    FLOW_SENSOR_HUMIDITY,
    FLOW_SENSOR_CO2,
    DEVICE_TYPE_CYCLE,
    DEVICE_TYPE_PLANT,
    SERVICE_CLONE_PLANT,
    ATTR_IS_NEW_PLANT,
    ATTR_DEVICE_TYPE,
    ATTR_FLOWERING_DURATION,
    ATTR_ORIGINAL_FLOWERING_DURATION,
    SERVICE_MOVE_TO_AREA,
    SERVICE_ADD_IMAGE,
    FLOW_DOWNLOAD_PATH,
    DEFAULT_IMAGE_PATH,
    DEFAULT_IMAGE_LOCAL_URL,
    FLOW_SENSOR_POWER_CONSUMPTION,
    ATTR_POSITION_X,
    ATTR_POSITION_Y,
    SERVICE_CHANGE_POSITION,
    DATA_SOURCE,
    DATA_SOURCE_PLANTBOOK,
    FLOW_SENSOR_PH,
    SERVICE_EXPORT_PLANTS,
    SERVICE_IMPORT_PLANTS,
    SERVICE_ADD_WATERING,
    SERVICE_ADD_CONDUCTIVITY,
    SERVICE_ADD_PH,

)
from .plant_helpers import PlantHelper

_LOGGER = logging.getLogger(__name__)

# Service Schemas
REPLACE_SENSOR_SCHEMA = vol.Schema({
    vol.Required("meter_entity"): cv.string,
    vol.Optional("new_sensor"): cv.string,
})

CREATE_PLANT_SCHEMA = vol.Schema({
    vol.Required(ATTR_NAME): cv.string,
    vol.Required(ATTR_STRAIN): cv.string,
    vol.Optional(ATTR_BREEDER): cv.string,
    vol.Optional("growth_phase", default=DEFAULT_GROWTH_PHASE): cv.string,
    vol.Optional("plant_emoji", default="🌿"): cv.string,
    vol.Optional(FLOW_SENSOR_TEMPERATURE): cv.string,
    vol.Optional(FLOW_SENSOR_MOISTURE): cv.string,
    vol.Optional(FLOW_SENSOR_CONDUCTIVITY): cv.string,
    vol.Optional(FLOW_SENSOR_ILLUMINANCE): cv.string,
    vol.Optional(FLOW_SENSOR_HUMIDITY): cv.string,
    vol.Optional(FLOW_SENSOR_CO2): cv.string,
    vol.Optional(FLOW_SENSOR_POWER_CONSUMPTION): cv.string,
    vol.Optional(FLOW_SENSOR_PH): cv.string,
})

UPDATE_PLANT_ATTRIBUTES_SCHEMA = vol.Schema({
    vol.Optional("phenotype"): cv.string,
    vol.Optional("hunger"): cv.string,
    vol.Optional("growth_stretch"): cv.string,
    vol.Optional("flower_stretch"): cv.string,
    vol.Optional("mold_resistance"): cv.string,
    vol.Optional("difficulty"): cv.string,
    vol.Optional("yield"): cv.string,
    vol.Optional("notes"): cv.string,
    vol.Optional("taste"): cv.string,
    vol.Optional("smell"): cv.string,
    vol.Optional("website"): cv.string,
    vol.Optional("infotext1"): cv.string,
    vol.Optional("infotext2"): cv.string,
    vol.Optional("strain"): cv.string,
    vol.Optional("breeder"): cv.string,
    vol.Optional("flowering_duration"): cv.positive_int,
    vol.Optional("pid"): cv.string,
            vol.Optional("type"): cv.string,
    vol.Optional("feminized"): cv.string,
    vol.Optional("timestamp"): cv.string,
    vol.Optional("effects"): cv.string,
    vol.Optional("lineage"): cv.string,
})

# Schema für add_image Service
ADD_IMAGE_SCHEMA = vol.Schema({
    vol.Required("entity_id"): cv.entity_id,
    vol.Required("image_url"): cv.url,
})

# Schema für export_plants Service
EXPORT_PLANTS_SCHEMA = vol.Schema({
    vol.Required("plant_entities"): vol.All(cv.ensure_list, [cv.entity_id]),
    vol.Optional("file_path", default="/config/plants_export.zip"): cv.string,
    vol.Optional("include_images"): cv.boolean,
    vol.Optional("include_sensor_data"): cv.boolean,
    vol.Optional("sensor_data_days"): vol.All(vol.Coerce(int), vol.Range(min=1, max=365)),
})

# Schema für import_plants Service
IMPORT_PLANTS_SCHEMA = vol.Schema({
    vol.Required("file_path"): cv.string,  # ZIP file (contains plants_config.json + images)
    vol.Optional("new_plant_name"): cv.string,
    vol.Optional("overwrite_existing"): cv.boolean,
    vol.Optional("include_images"): cv.boolean,
})


# Schema for add_watering Service
ADD_WATERING_SCHEMA = vol.Schema({
    vol.Required("entity_id"): cv.entity_id,
    vol.Required("amount_liters"): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1000.0)),
    vol.Optional("note"): cv.string,
})

# Schema for add_conductivity Service
ADD_CONDUCTIVITY_SCHEMA = vol.Schema({
    vol.Required("entity_id"): cv.entity_id,
    vol.Required("value_us_cm"): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=100000.0)),
})

# Schema for add_ph Service
ADD_PH_SCHEMA = vol.Schema({
    vol.Required("entity_id"): cv.entity_id,
    vol.Required("value"): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=14.0)),
})



async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for plant integration."""

    async def replace_sensor(call: ServiceCall) -> None:
        """Replace a sensor entity within a plant device"""
        meter_entity = call.data.get("meter_entity")
        new_sensor = call.data.get("new_sensor")
        found = False
        for entry_id in hass.data[DOMAIN]:
            if ATTR_SENSORS in hass.data[DOMAIN][entry_id]:
                for sensor in hass.data[DOMAIN][entry_id][ATTR_SENSORS]:
                    if sensor.entity_id == meter_entity:
                        found = True
                        break
        if not found:
            _LOGGER.warning(
                "Refuse to update non-%s entities: %s", DOMAIN, meter_entity
            )
            return False
        if new_sensor and new_sensor != "" and not new_sensor.startswith("sensor."):
            _LOGGER.warning("%s is not a sensor", new_sensor)
            return False

        try:
            meter = hass.states.get(meter_entity)
        except AttributeError:
            _LOGGER.error("Meter entity %s not found", meter_entity)
            return False
        if meter is None:
            _LOGGER.error("Meter entity %s not found", meter_entity)
            return False

        if new_sensor and new_sensor != "":
            try:
                test = hass.states.get(new_sensor)
            except AttributeError:
                _LOGGER.error("New sensor entity %s not found", meter_entity)
                return False
            if test is None:
                _LOGGER.error("New sensor entity %s not found", meter_entity)
                return False
        else:
            new_sensor = None

        _LOGGER.info(
            "Going to replace the external sensor for %s with %s",
            meter_entity,
            new_sensor,
        )
        for key in hass.data[DOMAIN]:
            if ATTR_SENSORS in hass.data[DOMAIN][key]:
                meters = hass.data[DOMAIN][key][ATTR_SENSORS]
                for meter in meters:
                    if meter.entity_id == meter_entity:
                        meter.replace_external_sensor(new_sensor)
        return

    async def remove_plant(call: ServiceCall) -> None:
        """Remove a plant entity and all its associated entities."""
        plant_entity = call.data.get("plant_entity")

        found = False
        target_entry_id = None
        target_plant = None
        for entry_id in hass.data[DOMAIN]:
            if ATTR_PLANT in hass.data[DOMAIN][entry_id]:
                plant = hass.data[DOMAIN][entry_id][ATTR_PLANT]
                if plant.entity_id == plant_entity:
                    found = True
                    target_entry_id = entry_id
                    target_plant = plant
                    break

        if not found:
            _LOGGER.warning(
                "Refuse to remove non-%s entity: %s", DOMAIN, plant_entity
            )
            return False

        # Prüfe ob die Plant einem Cycle zugeordnet ist und aktualisiere dessen Phase
        device_registry = dr.async_get(hass)
        plant_device = device_registry.async_get_device(
            identifiers={(DOMAIN, target_plant.unique_id)}
        )
        
        if plant_device and plant_device.via_device_id:
            # Suche das Cycle Device
            for device in device_registry.devices.values():
                if device.id == plant_device.via_device_id:
                    cycle_device = device
                    # Finde den zugehörigen Cycle
                    for entry_id in hass.data[DOMAIN]:
                        if ATTR_PLANT in hass.data[DOMAIN][entry_id]:
                            cycle = hass.data[DOMAIN][entry_id][ATTR_PLANT]
                            if (cycle.device_type == DEVICE_TYPE_CYCLE and 
                                cycle.unique_id == next(iter(cycle_device.identifiers))[1]):
                                # Entferne die Plant aus dem Cycle
                                cycle.remove_member_plant(plant_entity)
                                # Aktualisiere Flowering Duration
                                if cycle.flowering_duration:
                                    await cycle.flowering_duration._update_cycle_duration()
                                break
                    break

        # Entferne die Config Entry
        await hass.config_entries.async_remove(target_entry_id)
        return True

    async def create_plant(call: ServiceCall) -> ServiceResponse:
        """Create a new plant."""
        try:
            # Erstelle ein vollständiges plant_info Objekt
            plant_info = {
                ATTR_DEVICE_TYPE: DEVICE_TYPE_PLANT,
                ATTR_NAME: call.data[ATTR_NAME],
                ATTR_STRAIN: call.data[ATTR_STRAIN],
                ATTR_BREEDER: call.data.get(ATTR_BREEDER, ""),
                "growth_phase": call.data.get("growth_phase", DEFAULT_GROWTH_PHASE),
                "plant_emoji": call.data.get("plant_emoji", "🌿"),
                ATTR_IS_NEW_PLANT: True,
            }

            # Füge optionale Sensoren hinzu
            if call.data.get(FLOW_SENSOR_TEMPERATURE):
                plant_info[FLOW_SENSOR_TEMPERATURE] = call.data[FLOW_SENSOR_TEMPERATURE]
            if call.data.get(FLOW_SENSOR_MOISTURE):
                plant_info[FLOW_SENSOR_MOISTURE] = call.data[FLOW_SENSOR_MOISTURE]
            if call.data.get(FLOW_SENSOR_CONDUCTIVITY):
                plant_info[FLOW_SENSOR_CONDUCTIVITY] = call.data[FLOW_SENSOR_CONDUCTIVITY]
            if call.data.get(FLOW_SENSOR_ILLUMINANCE):
                plant_info[FLOW_SENSOR_ILLUMINANCE] = call.data[FLOW_SENSOR_ILLUMINANCE]
            if call.data.get(FLOW_SENSOR_HUMIDITY):
                plant_info[FLOW_SENSOR_HUMIDITY] = call.data[FLOW_SENSOR_HUMIDITY]
            if call.data.get(FLOW_SENSOR_CO2):
                plant_info[FLOW_SENSOR_CO2] = call.data[FLOW_SENSOR_CO2]
            if call.data.get(FLOW_SENSOR_POWER_CONSUMPTION):
                plant_info[FLOW_SENSOR_POWER_CONSUMPTION] = call.data[FLOW_SENSOR_POWER_CONSUMPTION]
            if call.data.get(FLOW_SENSOR_PH):
                plant_info[FLOW_SENSOR_PH] = call.data[FLOW_SENSOR_PH]

            # Hole Daten von OpenPlantbook
            plant_helper = PlantHelper(hass=hass)
            plant_config = await plant_helper.get_plantbook_data({
                ATTR_STRAIN: plant_info[ATTR_STRAIN],
                ATTR_BREEDER: plant_info[ATTR_BREEDER]
            })

            if plant_config and plant_config.get(FLOW_PLANT_INFO, {}).get(DATA_SOURCE) == DATA_SOURCE_PLANTBOOK:
                opb_info = plant_config[FLOW_PLANT_INFO]
                # Füge den Namen mit Emoji hinzu
                plant_emoji = plant_info.get("plant_emoji", "")
                opb_info[ATTR_NAME] = plant_info[ATTR_NAME] + (f" {plant_emoji}" if plant_emoji else "")
                opb_info["plant_emoji"] = plant_emoji
                
                # Übernehme die Sensorzuweisungen
                for sensor_key in [FLOW_SENSOR_TEMPERATURE, FLOW_SENSOR_MOISTURE, FLOW_SENSOR_CONDUCTIVITY, 
                                  FLOW_SENSOR_ILLUMINANCE, FLOW_SENSOR_HUMIDITY, FLOW_SENSOR_POWER_CONSUMPTION,
                                  FLOW_SENSOR_PH, FLOW_SENSOR_CO2]:
                    if sensor_key in plant_info:
                        opb_info[sensor_key] = plant_info[sensor_key]
                
                # Übernehme andere wichtige Attribute
                opb_info[ATTR_DEVICE_TYPE] = DEVICE_TYPE_PLANT
                opb_info[ATTR_IS_NEW_PLANT] = True
                opb_info["growth_phase"] = plant_info["growth_phase"]
                
                plant_info = opb_info
            else:
                # Wenn keine OpenPlantbook-Daten verfügbar sind, füge trotzdem das Emoji zum Namen hinzu
                plant_emoji = plant_info.get("plant_emoji", "")
                plant_info[ATTR_NAME] = plant_info[ATTR_NAME] + (f" {plant_emoji}" if plant_emoji else "")
                
                # Generiere Standard-Grenzwerte
                default_config = await plant_helper.generate_configentry(
                    config={
                        ATTR_NAME: plant_info[ATTR_NAME],
                        ATTR_STRAIN: plant_info[ATTR_STRAIN],
                        ATTR_BREEDER: plant_info.get(ATTR_BREEDER, ""),
                        ATTR_SENSORS: {},
                        "plant_emoji": plant_info.get("plant_emoji", ""),
                    }
                )
                
                # Übernehme die Standard-Grenzwerte
                plant_info.update(default_config[FLOW_PLANT_INFO])

            # Erstelle die Config Entry direkt
            _LOGGER.debug("Initialisiere Config Entry für Pflanze %s", plant_info[ATTR_NAME])
            result = await hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "import"},
                data={FLOW_PLANT_INFO: plant_info}
            )

            if result["type"] != FlowResultType.CREATE_ENTRY:
                _LOGGER.error("Failed to create plant: %s", result)
                raise HomeAssistantError(
                    f"Failed to create new plant: {result.get('reason', 'unknown error')}"
                )
            
            _LOGGER.debug("Config Entry erstellt mit ID: %s", result["result"].entry_id)
            
            # Verzögerung für die Entityerstellung
            await asyncio.sleep(2)
            
            # Direkter Zugriff auf das PlantDevice-Objekt über den Entry
            entry_id = result["result"].entry_id
            
            # Zugriff auf die PlantDevice-Instanz
            for _ in range(10):  # Mehrere Versuche
                if entry_id in hass.data.get(DOMAIN, {}):
                    if ATTR_PLANT in hass.data[DOMAIN][entry_id]:
                        plant_device = hass.data[DOMAIN][entry_id][ATTR_PLANT]
                        device_id = plant_device.device_id
                        _LOGGER.debug("Pflanze gefunden: %s mit entity_id: %s, device_id: %s", 
                                      plant_device.name, plant_device.entity_id, device_id)
                        return {
                            "entity_id": plant_device.entity_id,
                            "device_id": device_id
                        }
                await asyncio.sleep(0.5)
            
            # Wenn das nicht funktioniert, stattdessen im Entity Registry suchen
            _LOGGER.debug("Suche im Entity Registry nach Config Entry ID: %s", entry_id)
            entity_registry = er.async_get(hass)
            device_registry = dr.async_get(hass)
            
            for entity in entity_registry.entities.values():
                if entity.config_entry_id == entry_id and entity.domain == DOMAIN:
                    _LOGGER.debug("Entity in Registry gefunden: %s", entity.entity_id)
                    
                    # Suche das zugehörige Device
                    device_id = None
                    if entity.device_id:
                        device_id = entity.device_id
                    
                    return {
                        "entity_id": entity.entity_id,
                        "device_id": device_id
                    }
            
            # Letzte Chance: Suche nach einem State mit den richtigen Attributen
            _LOGGER.debug("Suche in allen States nach Pflanze mit Strain=%s, Breeder=%s", 
                         plant_info.get(ATTR_STRAIN), plant_info.get(ATTR_BREEDER))
            for state in hass.states.async_all():
                if state.entity_id.startswith(f"{DOMAIN}."):
                    state_attrs = state.attributes
                    if (state_attrs.get("strain") == plant_info.get(ATTR_STRAIN) and 
                        state_attrs.get("breeder") == plant_info.get(ATTR_BREEDER)):
                        _LOGGER.debug("Passender State gefunden: %s", state.entity_id)
                        
                        # Suche das zugehörige Device
                        device_id = None
                        for entity in entity_registry.entities.values():
                            if entity.entity_id == state.entity_id:
                                device_id = entity.device_id
                                break
                        
                        return {
                            "entity_id": state.entity_id,
                            "device_id": device_id
                        }
            
            # Wenn wirklich nichts funktioniert, liefere eine Info-Antwort zurück
            _LOGGER.warning("Konnte keine entity_id für die erstellte Pflanze finden!")
            return {"info": "Pflanze wurde erstellt, entity_id konnte nicht ermittelt werden."}
            
        except Exception as e:
            _LOGGER.exception("Error creating plant: %s", e)
            raise HomeAssistantError(f"Error creating plant: {str(e)}")

    async def create_cycle(call: ServiceCall) -> ServiceResponse:
        """Create a new cycle via service call."""
        try:
            # Erstelle ein vollständiges cycle_info Objekt
            cycle_info = {
                ATTR_NAME: call.data.get(ATTR_NAME),
                ATTR_DEVICE_TYPE: DEVICE_TYPE_CYCLE,
                "plant_emoji": call.data.get("plant_emoji", "🔄"),
                ATTR_IS_NEW_PLANT: True,
            }

            # Hole die Default-Werte aus dem Konfigurationsknoten
            config_entry = None
            for entry in hass.config_entries.async_entries(DOMAIN):
                if entry.data.get("is_config", False):
                    config_entry = entry
                    break

            if config_entry:
                config_data = config_entry.data[FLOW_PLANT_INFO]
                
                # Füge Default-Aggregationsmethoden hinzu
                cycle_info["growth_phase_aggregation"] = config_data.get("default_growth_phase_aggregation", "min")
                cycle_info["flowering_duration_aggregation"] = config_data.get("default_flowering_duration_aggregation", "mean")
                cycle_info["pot_size_aggregation"] = config_data.get("default_pot_size_aggregation", "mean")
                cycle_info["water_capacity_aggregation"] = config_data.get("default_water_capacity_aggregation", "mean")
                cycle_info["aggregations"] = {
                    'temperature': config_data.get("default_temperature_aggregation", "mean"),
                    'moisture': config_data.get("default_moisture_aggregation", "median"),
                    'conductivity': config_data.get("default_conductivity_aggregation", "median"),
                    'illuminance': config_data.get("default_illuminance_aggregation", "mean"),
                    'humidity': config_data.get("default_humidity_aggregation", "mean"),
                    'CO2': config_data.get("default_CO2_aggregation", "mean"),
                    'ppfd': config_data.get("default_ppfd_aggregation", "original"),
                    'dli': config_data.get("default_dli_aggregation", "original"),
                    'total_integral': config_data.get("default_total_integral_aggregation", "original"),
                    'moisture_consumption': config_data.get("default_moisture_consumption_aggregation", "original"),
                    'fertilizer_consumption': config_data.get("default_fertilizer_consumption_aggregation", "original"),
                    'total_water_consumption': config_data.get("default_total_water_consumption_aggregation", "original"),
                    'total_fertilizer_consumption': config_data.get("default_total_fertilizer_consumption_aggregation", "original"),
                    'power_consumption': config_data.get("default_power_consumption_aggregation", "mean"),
                    'total_power_consumption': config_data.get("default_total_power_consumption_aggregation", "original"),
                    'health': config_data.get("default_health_aggregation", "mean"),
                }
            
            # Nutze PlantHelper für die Standard-Grenzwerte
            plant_helper = PlantHelper(hass=hass)
            cycle_config = await plant_helper.generate_configentry(
                config={
                    ATTR_NAME: cycle_info[ATTR_NAME],
                    ATTR_STRAIN: "",
                    ATTR_BREEDER: "",
                    ATTR_SENSORS: {},
                    "plant_emoji": cycle_info.get("plant_emoji", ""),
                    ATTR_DEVICE_TYPE: DEVICE_TYPE_CYCLE,
                }
            )
            
            # Übernehme die Standard-Grenzwerte
            cycle_info.update(cycle_config[FLOW_PLANT_INFO])
            
            # Erstelle die Config Entry direkt
            _LOGGER.debug("Initialisiere Config Entry für Cycle %s", cycle_info[ATTR_NAME])
            result = await hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "import"},
                data={FLOW_PLANT_INFO: cycle_info}
            )

            if result["type"] != FlowResultType.CREATE_ENTRY:
                _LOGGER.error("Failed to create cycle: %s", result)
                raise HomeAssistantError(
                    f"Failed to create cycle: {result.get('reason', 'unknown error')}"
                )
            
            _LOGGER.debug("Config Entry erstellt mit ID: %s", result["result"].entry_id)
            
            # Aktualisiere alle Plant Cycle Selects
            for entry_id in hass.data[DOMAIN]:
                if ATTR_PLANT in hass.data[DOMAIN][entry_id]:
                    plant = hass.data[DOMAIN][entry_id][ATTR_PLANT]
                    if plant.device_type == DEVICE_TYPE_PLANT and plant.cycle_select:
                        plant.cycle_select._update_cycle_options()
                        plant.cycle_select.async_write_ha_state()
            
            # Verzögerung für die Entityerstellung
            await asyncio.sleep(2)
            
            # Direkter Zugriff auf das CycleDevice-Objekt über den Entry
            entry_id = result["result"].entry_id
            
            # Zugriff auf die CycleDevice-Instanz
            for _ in range(10):  # Mehrere Versuche
                if entry_id in hass.data.get(DOMAIN, {}):
                    if ATTR_PLANT in hass.data[DOMAIN][entry_id]:
                        cycle_device = hass.data[DOMAIN][entry_id][ATTR_PLANT]
                        device_id = cycle_device.device_id
                        _LOGGER.debug("Cycle gefunden: %s mit entity_id: %s, device_id: %s", 
                                      cycle_device.name, cycle_device.entity_id, device_id)
                        return {
                            "entity_id": cycle_device.entity_id,
                            "device_id": device_id
                        }
                await asyncio.sleep(0.5)
            
            # Wenn das nicht funktioniert, stattdessen im Entity Registry suchen
            _LOGGER.debug("Suche im Entity Registry nach Config Entry ID: %s", entry_id)
            entity_registry = er.async_get(hass)
            device_registry = dr.async_get(hass)
            
            for entity in entity_registry.entities.values():
                if entity.config_entry_id == entry_id and entity.domain == DOMAIN:
                    _LOGGER.debug("Entity in Registry gefunden: %s", entity.entity_id)
                    
                    # Suche das zugehörige Device
                    device_id = None
                    if entity.device_id:
                        device_id = entity.device_id
                    
                    return {
                        "entity_id": entity.entity_id,
                        "device_id": device_id
                    }
            
            # Letzte Chance: Suche nach einem State mit dem richtigen Namen
            _LOGGER.debug("Suche in allen States nach Cycle mit Name=%s", cycle_info[ATTR_NAME])
            for state in hass.states.async_all():
                if state.entity_id.startswith(f"{DOMAIN}."):
                    state_attrs = state.attributes
                    if state_attrs.get("friendly_name") == cycle_info[ATTR_NAME]:
                        _LOGGER.debug("Passender State gefunden: %s", state.entity_id)
                        
                        # Suche das zugehörige Device
                        device_id = None
                        for entity in entity_registry.entities.values():
                            if entity.entity_id == state.entity_id:
                                device_id = entity.device_id
                                break
                        
                        return {
                            "entity_id": state.entity_id,
                            "device_id": device_id
                        }
            
            # Wenn wirklich nichts funktioniert, liefere eine Info-Antwort zurück
            _LOGGER.warning("Konnte keine entity_id für den erstellten Cycle finden!")
            return {"info": "Cycle wurde erstellt, entity_id konnte nicht ermittelt werden."}
            
        except Exception as e:
            _LOGGER.exception("Error creating cycle: %s", e)
            raise HomeAssistantError(f"Error creating cycle: {str(e)}")

    async def move_to_cycle(call: ServiceCall) -> None:
        """Move plants to a cycle or remove them from cycle."""
        plant_entity_ids = call.data.get("plant_entity")
        cycle_entity_id = call.data.get("cycle_entity")

        # Convert to list if single string
        if isinstance(plant_entity_ids, str):
            plant_entity_ids = [plant_entity_ids]

        device_registry = dr.async_get(hass)
        entity_registry = er.async_get(hass)

        # Get cycle device if specified
        cycle_device = None
        cycle = None
        if cycle_entity_id:
            cycle_entity = entity_registry.async_get(cycle_entity_id)
            if not cycle_entity:
                _LOGGER.error(f"Cycle entity {cycle_entity_id} not found")
                return
            
            # Finde zuerst das Cycle Objekt
            for entry_id in hass.data[DOMAIN]:
                if ATTR_PLANT in hass.data[DOMAIN][entry_id]:
                    if hass.data[DOMAIN][entry_id][ATTR_PLANT].entity_id == cycle_entity_id:
                        cycle = hass.data[DOMAIN][entry_id][ATTR_PLANT]
                        break

            if not cycle:
                _LOGGER.error(f"Cycle object for {cycle_entity_id} not found")
                return

            # Hole das cycle device über die unique_id des Cycles
            cycle_device = device_registry.async_get_device(
                identifiers={(DOMAIN, cycle.unique_id)}
            )
            if not cycle_device:
                _LOGGER.error(f"Cycle device for {cycle_entity_id} not found")
                return

        # Process each plant entity
        for plant_entity_id in plant_entity_ids:
            plant_entity = entity_registry.async_get(plant_entity_id)
            if not plant_entity:
                _LOGGER.error(f"Plant entity {plant_entity_id} not found")
                continue

            plant_device = device_registry.async_get_device(
                identifiers={(DOMAIN, plant_entity.unique_id)}
            )
            if not plant_device:
                _LOGGER.error(f"Plant device for {plant_entity_id} not found")
                continue

            # Wenn die Plant bereits einem Cycle zugeordnet ist, entferne sie dort
            if plant_device.via_device_id:
                # Suche das alte Cycle Device über alle Devices
                old_cycle_device = None
                for device in device_registry.devices.values():
                    if device.id == plant_device.via_device_id:
                        old_cycle_device = device
                        break

                if old_cycle_device:
                    old_cycle = None
                    for entry_id in hass.data[DOMAIN]:
                        if ATTR_PLANT in hass.data[DOMAIN][entry_id]:
                            device = hass.data[DOMAIN][entry_id][ATTR_PLANT]
                            if device.device_type == DEVICE_TYPE_CYCLE and device.device_id == old_cycle_device.id:
                                old_cycle = device
                                break
                    
                    if old_cycle:
                        old_cycle.remove_member_plant(plant_entity_id)

            # Update device registry
            device_registry.async_update_device(
                plant_device.id,
                via_device_id=cycle_device.id if cycle_device else None
            )

            # Add plant to new cycle
            if cycle:
                cycle.add_member_plant(plant_entity_id)
                # Aktualisiere Flowering Duration
                if cycle.flowering_duration:
                    await cycle.flowering_duration._update_cycle_duration()

            if cycle_device:
                _LOGGER.info(
                    f"Plant {plant_entity_id} successfully assigned to cycle {cycle_entity_id}"
                )
            else:
                _LOGGER.info(
                    f"Plant {plant_entity_id} successfully removed from cycle"
                )

    async def remove_cycle(call: ServiceCall) -> None:
        """Remove a cycle entity and all its associated entities."""
        cycle_entity = call.data.get("cycle_entity")

        found = False
        target_entry_id = None
        for entry_id in hass.data[DOMAIN]:
            if ATTR_PLANT in hass.data[DOMAIN][entry_id]:
                device = hass.data[DOMAIN][entry_id][ATTR_PLANT]
                if device.entity_id == cycle_entity and device.device_type == DEVICE_TYPE_CYCLE:
                    found = True
                    target_entry_id = entry_id
                    break

        if not found:
            _LOGGER.warning(
                "Refuse to remove non-cycle entity: %s", cycle_entity
            )
            return False

        await hass.config_entries.async_remove(target_entry_id)

        # Aktualisiere alle Plant Cycle Selects
        for entry_id in hass.data[DOMAIN]:
            if ATTR_PLANT in hass.data[DOMAIN][entry_id]:
                plant = hass.data[DOMAIN][entry_id][ATTR_PLANT]
                if plant.device_type == DEVICE_TYPE_PLANT and plant.cycle_select:
                    plant.cycle_select._update_cycle_options()
                    plant.cycle_select.async_write_ha_state()

        return True

    async def handle_clone_plant(call: ServiceCall) -> ServiceResponse:
        """Handle the clone plant service call."""
        source_entity_id = call.data.get("source_entity_id")
        
        # Finde das Quell-Device
        source_plant = None
        for entry_id in hass.data[DOMAIN]:
            if ATTR_PLANT in hass.data[DOMAIN][entry_id]:
                plant = hass.data[DOMAIN][entry_id][ATTR_PLANT]
                if plant.entity_id == source_entity_id:
                    source_plant = plant
                    break

        if not source_plant:
            raise HomeAssistantError(f"Source plant {source_entity_id} not found")

        # Hole zuerst den flowering_duration Wert von der Quell-Plant
        flowering_duration = 0
        if hasattr(source_plant, 'flowering_duration'):
            try:
                duration = source_plant.flowering_duration.native_value
                if duration is not None:
                    flowering_duration = int(duration)
            except (ValueError, TypeError, AttributeError):
                pass

        # Bestimme den Namen für den Klon
        if "name" in call.data:
            new_name = call.data["name"]
        else:
            # Verwende den Namen der Quell-Plant als Basis
            base_name = source_plant._plant_info[ATTR_NAME]
            
            # Prüfe systematisch, welche Namen bereits existieren
            entity_registry = er.async_get(hass)
            counter = 1
            test_name = base_name
            
            # Prüfe ob der Basis-Name bereits existiert (entweder als original_name oder in entity_id)
            while any(
                (entity.original_name == test_name or 
                 entity.entity_id == f"{DOMAIN}.{test_name.lower().replace(' ', '_')}")
                for entity in entity_registry.entities.values()
                if entity.domain == DOMAIN
            ):
                counter += 1
                test_name = f"{base_name}_{counter}"
            
            new_name = test_name

        # Kopiere alle Daten von der Quell-Plant
        plant_info = dict(source_plant._plant_info)
        
        # Setze beide flowering_duration Werte
        plant_info[ATTR_FLOWERING_DURATION] = flowering_duration
        plant_info[ATTR_ORIGINAL_FLOWERING_DURATION] = source_plant._plant_info.get(ATTR_ORIGINAL_FLOWERING_DURATION, flowering_duration)
        
        # Markiere als neue Plant
        plant_info[ATTR_IS_NEW_PLANT] = True
        
        _LOGGER.debug("Cloning plant with flowering duration: %s", flowering_duration)

        # Entferne die plant_id damit eine neue generiert wird
        if "plant_id" in plant_info:
            del plant_info["plant_id"]
        
        # Entferne alle Sensor-Zuweisungen
        sensor_keys = [
            FLOW_SENSOR_TEMPERATURE,
            FLOW_SENSOR_MOISTURE,
            FLOW_SENSOR_CONDUCTIVITY,
            FLOW_SENSOR_ILLUMINANCE,
            FLOW_SENSOR_HUMIDITY,
            FLOW_SENSOR_CO2,
            FLOW_SENSOR_POWER_CONSUMPTION,
            FLOW_SENSOR_PH
        ]
        for key in sensor_keys:
            plant_info.pop(key, None)

        # Setze den neuen Namen und Device-Typ
        plant_info[ATTR_NAME] = new_name
        plant_info[ATTR_DEVICE_TYPE] = DEVICE_TYPE_PLANT

        # Füge nur die im Service angegebenen Sensoren hinzu
        if call.data.get(FLOW_SENSOR_TEMPERATURE):
            plant_info[FLOW_SENSOR_TEMPERATURE] = call.data[FLOW_SENSOR_TEMPERATURE]
        if call.data.get(FLOW_SENSOR_MOISTURE):
            plant_info[FLOW_SENSOR_MOISTURE] = call.data[FLOW_SENSOR_MOISTURE]
        if call.data.get(FLOW_SENSOR_CONDUCTIVITY):
            plant_info[FLOW_SENSOR_CONDUCTIVITY] = call.data[FLOW_SENSOR_CONDUCTIVITY]
        if call.data.get(FLOW_SENSOR_ILLUMINANCE):
            plant_info[FLOW_SENSOR_ILLUMINANCE] = call.data[FLOW_SENSOR_ILLUMINANCE]
        if call.data.get(FLOW_SENSOR_HUMIDITY):
            plant_info[FLOW_SENSOR_HUMIDITY] = call.data[FLOW_SENSOR_HUMIDITY]
        if call.data.get(FLOW_SENSOR_CO2):
            plant_info[FLOW_SENSOR_CO2] = call.data[FLOW_SENSOR_CO2]
        if call.data.get(FLOW_SENSOR_POWER_CONSUMPTION):
            plant_info[FLOW_SENSOR_POWER_CONSUMPTION] = call.data[FLOW_SENSOR_POWER_CONSUMPTION]
        if call.data.get(FLOW_SENSOR_PH):
            plant_info[FLOW_SENSOR_PH] = call.data[FLOW_SENSOR_PH]

        _LOGGER.debug("Creating plant clone with data: %s", plant_info)

        # Erstelle die Plant direkt mit allen Daten
        _LOGGER.debug("Initialisiere Config Entry für geklonte Pflanze %s", plant_info[ATTR_NAME])
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "import"},
            data={FLOW_PLANT_INFO: plant_info}
        )

        if result["type"] != FlowResultType.CREATE_ENTRY:
            raise HomeAssistantError(
                f"Failed to create new plant: {result.get('reason', 'unknown error')}"
            )

        _LOGGER.debug("Config Entry erstellt mit ID: %s", result["result"].entry_id)
        
        # Verzögerung für die Entityerstellung
        await asyncio.sleep(2)
        
        # Direkter Zugriff auf das PlantDevice-Objekt über den Entry
        entry_id = result["result"].entry_id
        
        # Zugriff auf die PlantDevice-Instanz
        for _ in range(10):  # Mehrere Versuche
            if entry_id in hass.data.get(DOMAIN, {}):
                if ATTR_PLANT in hass.data[DOMAIN][entry_id]:
                    plant_device = hass.data[DOMAIN][entry_id][ATTR_PLANT]
                    device_id = plant_device.device_id
                    _LOGGER.debug("Geklonte Pflanze gefunden: %s mit entity_id: %s, device_id: %s", 
                                  plant_device.name, plant_device.entity_id, device_id)
                    return {
                        "entity_id": plant_device.entity_id,
                        "device_id": device_id
                    }
            await asyncio.sleep(0.5)
        
        # Wenn das nicht funktioniert, stattdessen im Entity Registry suchen
        _LOGGER.debug("Suche im Entity Registry nach Config Entry ID: %s", entry_id)
        entity_registry = er.async_get(hass)
        device_registry = dr.async_get(hass)
        
        for entity in entity_registry.entities.values():
            if entity.config_entry_id == entry_id and entity.domain == DOMAIN:
                _LOGGER.debug("Entity in Registry gefunden: %s", entity.entity_id)
                
                # Suche das zugehörige Device
                device_id = None
                if entity.device_id:
                    device_id = entity.device_id
                
                return {
                    "entity_id": entity.entity_id,
                    "device_id": device_id
                }
        
        # Letzte Chance: Suche nach einem State mit den richtigen Attributen
        _LOGGER.debug("Suche in allen States nach Pflanze mit Name=%s", new_name)
        for state in hass.states.async_all():
            if state.entity_id.startswith(f"{DOMAIN}."):
                state_attrs = state.attributes
                if state_attrs.get("friendly_name") == new_name:
                    _LOGGER.debug("Passender State gefunden: %s", state.entity_id)
                    
                    # Suche das zugehörige Device
                    device_id = None
                    for entity in entity_registry.entities.values():
                        if entity.entity_id == state.entity_id:
                            device_id = entity.device_id
                            break
                    
                    return {
                        "entity_id": state.entity_id,
                        "device_id": device_id
                    }
        
        # Wenn wirklich nichts funktioniert, liefere eine Info-Antwort zurück
        _LOGGER.warning("Konnte keine entity_id für die geklonte Pflanze finden!")
        return {"info": "Pflanze wurde geklont, entity_id konnte nicht ermittelt werden."}

    async def update_plant_attributes(call: ServiceCall) -> None:
        """Update plant attributes."""
        entity_id = call.data.get("entity_id")
        if not entity_id:
            raise HomeAssistantError("No plant entity specified")
            
        # Finde die Plant
        target_plant = None
        target_entry = None
        for entry_id in hass.data[DOMAIN]:
            if ATTR_PLANT in hass.data[DOMAIN][entry_id]:
                plant = hass.data[DOMAIN][entry_id][ATTR_PLANT]
                if plant.entity_id == entity_id:
                    target_plant = plant
                    target_entry = hass.config_entries.async_get_entry(entry_id)
                    break

        if not target_plant or not target_entry:
            raise HomeAssistantError(f"Plant {entity_id} not found")

        # Erstelle eine tiefe Kopie der bestehenden Daten
        new_data = dict(target_entry.data)
        plant_info = dict(new_data.get(FLOW_PLANT_INFO, {}))
        new_data[FLOW_PLANT_INFO] = plant_info
        
        # Update attributes in der Config
        for attr in ["strain", "breeder", "original_flowering_duration", "pid", 
                    "type", "feminized", "timestamp", "effects", "smell",
                    "taste", "phenotype", "hunger", "growth_stretch",
                    "flower_stretch", "mold_resistance", "difficulty",
                    "yield", "notes", "website", "infotext1", "infotext2",
                    "lineage"]:  # Positionsdaten entfernt
            if attr in call.data:
                plant_info[attr] = call.data[attr]

        # Verarbeite images separat
        if "images" in call.data:
            # Teile den String an Kommas und entferne Leerzeichen
            images = [img.strip() for img in call.data["images"].split(",") if img.strip()]
            plant_info["images"] = images

        # Aktualisiere die Config Entry mit den neuen Daten
        hass.config_entries.async_update_entry(
            target_entry,
            data=new_data,
        )

        # Aktualisiere das Plant-Objekt mit den neuen Daten
        target_plant._plant_info = plant_info
        if "images" in call.data:
            target_plant._images = plant_info["images"]
        
        # Update Growth Phase Attribute
        growth_phase_attrs = [
            "seeds_start", "seeds_duration", "germination_start", "germination_duration",
            "rooting_start", "rooting_duration", "growing_start", "growing_duration", 
            "flowering_start", "flower_duration", "harvested_date", "harvested_duration",
            "removed_date", "removed_duration"
        ]
        
        growth_phase_updates = {}
        for attr in growth_phase_attrs:
            if attr in call.data:
                growth_phase_updates[attr] = call.data[attr]
        
        # Update Growth Phase Select Entity wenn Updates vorhanden sind
        if growth_phase_updates and target_plant.growth_phase_select:
            for attr, value in growth_phase_updates.items():
                target_plant.growth_phase_select._attr_extra_state_attributes[attr] = value
            target_plant.growth_phase_select.async_write_ha_state()
        
        # Update Positions-Attribute
        if ATTR_POSITION_X in call.data or ATTR_POSITION_Y in call.data:
            # Hole die aktuellen Positionswerte
            new_position_x = call.data.get(ATTR_POSITION_X)
            new_position_y = call.data.get(ATTR_POSITION_Y)
            
            # Verwende den Location Sensor
            if hasattr(target_plant, "location_history") and target_plant.location_history:
                # Aktualisiere die Position über den Location Sensor
                target_plant.location_history.add_position(new_position_x, new_position_y)
            else:
                _LOGGER.warning(
                    f"Location Sensor für Pflanze {entity_id} nicht gefunden"
                )
        
        # Update entity state
        target_plant.async_write_ha_state()

    async def async_extract_entities(hass: HomeAssistant, call: ServiceCall):
        """Extract target entities from service call."""
        if not call.data.get("target"):
            return []
            
        entities = []
        for target in call.data["target"].get("entity_id", []):
            if target.startswith(f"{DOMAIN}."):
                entities.append(target)
                
        return entities

    async def move_to_area(call: ServiceCall) -> None:
        """Move plants to an area."""
        device_ids = call.data.get("device_id")
        area_id = call.data.get("area_id")

        # Convert to list if single string
        if isinstance(device_ids, str):
            device_ids = [device_ids]

        device_registry = dr.async_get(hass)
        area_registry = ar.async_get(hass)

        # Validate area_id
        if area_id and not area_registry.async_get_area(area_id):
            _LOGGER.error(f"Area {area_id} not found")
            return

        # Process each device
        for device_id in device_ids:
            # Get device directly by ID
            device = device_registry.async_get(device_id)
            if not device:
                _LOGGER.error(f"Device {device_id} not found")
                continue

            # Update device registry
            device_registry.async_update_device(
                device_id,
                area_id=area_id
            )

            if area_id:
                area = area_registry.async_get_area(area_id)
                _LOGGER.info(
                    f"Device {device_id} successfully moved to area {area.name}"
                )
            else:
                _LOGGER.info(
                    f"Device {device_id} successfully removed from area"
                )

    async def add_image(call: ServiceCall) -> None:
        """Add an image to a plant or cycle."""
        entity_id = call.data.get("entity_id")
        image_url = call.data.get("image_url")

        if not entity_id or not image_url:
            return

        # Finde die Entity (Plant oder Cycle)
        target_entity = None
        for entry_id in hass.data[DOMAIN]:
            if ATTR_PLANT in hass.data[DOMAIN][entry_id]:
                entity = hass.data[DOMAIN][entry_id][ATTR_PLANT]
                if entity.entity_id == entity_id:
                    target_entity = entity
                    break

        if not target_entity:
            return

        # Hole den Download-Pfad aus der Konfiguration
        config_entry = None
        for entry in hass.config_entries.async_entries(DOMAIN):
            if entry.data.get("is_config", False):
                config_entry = entry
                break

        download_path = config_entry.data[FLOW_PLANT_INFO].get(FLOW_DOWNLOAD_PATH, DEFAULT_IMAGE_PATH) if config_entry else DEFAULT_IMAGE_PATH

        try:
            # Erstelle den Download-Pfad falls er nicht existiert
            if not os.path.exists(download_path):
                os.makedirs(download_path)

            # Generiere Dateinamen aus entity_id und Timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{entity_id}_{timestamp}.jpg"
            filepath = os.path.join(download_path, filename)

            # Lade das Bild herunter
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        return
                    image_data = await response.read()

            # Speichere das Bild
            def write_file():
                with open(filepath, "wb") as f:
                    f.write(image_data)

            await hass.async_add_executor_job(write_file)

            # Hole die aktuelle Bilderliste
            current_images = target_entity._images if hasattr(target_entity, '_images') else []
            
            # Füge den neuen Dateinamen zur Liste hinzu
            current_images.append(filename)
            
            # Aktualisiere die Attribute über den update_plant_attributes Service
            # Konvertiere die Liste in einen komma-getrennten String ohne Leerzeichen
            images_string = ",".join(str(img).strip() for img in current_images)
            
            await hass.services.async_call(
                DOMAIN,
                "update_plant_attributes",
                {
                    "entity_id": entity_id,
                    "images": images_string
                },
                blocking=True
            )

        except Exception as e:
            _LOGGER.error("Error adding image: %s", e)

    async def change_position(call: ServiceCall) -> None:
        """Ändert die Position einer Pflanze mit x- und y-Koordinaten."""
        entity_id = call.data.get("entity_id")
        position_x = call.data.get(ATTR_POSITION_X)
        position_y = call.data.get(ATTR_POSITION_Y)
        
        if not entity_id:
            raise HomeAssistantError("Keine Pflanzen-Entity angegeben")
            
        # Finde die Plant
        target_plant = None
        for entry_id in hass.data[DOMAIN]:
            if ATTR_PLANT in hass.data[DOMAIN][entry_id]:
                plant = hass.data[DOMAIN][entry_id][ATTR_PLANT]
                if plant.entity_id == entity_id:
                    target_plant = plant
                    break

        if not target_plant:
            raise HomeAssistantError(f"Pflanze {entity_id} nicht gefunden")

        # Verwende den Location Sensor
        if hasattr(target_plant, "location_history") and target_plant.location_history:
            # Aktualisiere die Position über den Location Sensor
            target_plant.location_history.add_position(position_x, position_y)
        else:
            _LOGGER.warning(
                f"Location Sensor für Pflanze {entity_id} nicht gefunden"
            )

    async def add_watering(call: ServiceCall) -> None:
        """Add a manual watering entry and update totals."""
        entity_id = call.data.get("entity_id")
        amount_liters = call.data.get("amount_liters")
        note = call.data.get("note")

        if amount_liters is None:
            return

        # Find target plant/cycle
        target_plant = None
        for entry_id in hass.data.get(DOMAIN, {}):
            if ATTR_PLANT in hass.data[DOMAIN][entry_id]:
                plant = hass.data[DOMAIN][entry_id][ATTR_PLANT]
                if plant.entity_id == entity_id:
                    target_plant = plant
                    break

        if not target_plant:
            _LOGGER.warning("Plant entity %s not found for add_watering", entity_id)
            return

        # Update journal entry (prepend concise log)
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            journal_line = f"{timestamp}: Gegossen {amount_liters} L" + (f" - {note}" if note else "")
            if hasattr(target_plant, "journal") and target_plant.journal:
                current = target_plant.journal.state or ""
                new_text = f"{journal_line}\n{current}" if current else journal_line
                await target_plant.journal.async_set_value(new_text)
        except Exception as e:
            _LOGGER.debug("Could not update journal on add_watering: %s", e)

        # Update total water consumption sensor value via helper method if available
        try:
            twc = getattr(target_plant, "total_water_consumption", None)
            if twc and hasattr(twc, "add_manual_watering"):
                await twc.add_manual_watering(float(amount_liters), note)
            elif twc is not None:
                # Fallback: direct increment
                current_state = twc.state
                try:
                    current_value = float(current_state) if current_state not in (None, "unknown", "unavailable") else 0.0
                except (TypeError, ValueError):
                    current_value = 0.0
                twc._attr_native_value = round(current_value + float(amount_liters), 2)
                try:
                    twc._last_update = datetime.utcnow().isoformat()
                except Exception:
                    pass
                twc.async_write_ha_state()
            else:
                _LOGGER.warning("total_water_consumption sensor not available for %s", entity_id)
        except Exception as e:
            _LOGGER.error("Error updating total water consumption on add_watering: %s", e)

    async def add_conductivity(call: ServiceCall) -> None:
        """Add a manual EC measurement (uS/cm) to the current conductivity sensor."""
        entity_id = call.data.get("entity_id")
        value = call.data.get("value_us_cm")
        if value is None:
            return
        # Find target plant
        target_plant = None
        for entry_id in hass.data.get(DOMAIN, {}):
            if ATTR_PLANT in hass.data[DOMAIN][entry_id]:
                plant = hass.data[DOMAIN][entry_id][ATTR_PLANT]
                if plant.entity_id == entity_id:
                    target_plant = plant
                    break
        if not target_plant or not getattr(target_plant, "sensor_conductivity", None):
            _LOGGER.warning("Conductivity sensor not available for %s", entity_id)
            return
        sensor = target_plant.sensor_conductivity
        if hasattr(sensor, "set_manual_value"):
            await sensor.set_manual_value(float(value))
        else:
            try:
                sensor._attr_native_value = float(value)
                sensor.async_write_ha_state()
            except Exception:
                pass

        # Update journal entry (prepend concise log)
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            journal_line = f"{timestamp}: EC gesetzt {value} uS/cm"
            if hasattr(target_plant, "journal") and target_plant.journal:
                current = target_plant.journal.state or ""
                new_text = f"{journal_line}\n{current}" if current else journal_line
                await target_plant.journal.async_set_value(new_text)
        except Exception as e:
            _LOGGER.debug("Could not update journal on add_conductivity: %s", e)

    async def add_ph(call: ServiceCall) -> None:
        """Add a manual pH measurement to the current pH sensor."""
        entity_id = call.data.get("entity_id")
        value = call.data.get("value")
        if value is None:
            return
        # Find target plant
        target_plant = None
        for entry_id in hass.data.get(DOMAIN, {}):
            if ATTR_PLANT in hass.data[DOMAIN][entry_id]:
                plant = hass.data[DOMAIN][entry_id][ATTR_PLANT]
                if plant.entity_id == entity_id:
                    target_plant = plant
                    break
        if not target_plant or not getattr(target_plant, "sensor_ph", None):
            # sensor_ph is stored via add_sensors as 'ph'
            sensor = None
            if target_plant and hasattr(target_plant, "ph"):
                sensor = target_plant.ph
        else:
            sensor = target_plant.sensor_ph
        if not sensor:
            _LOGGER.warning("pH sensor not available for %s", entity_id)
            return
        if hasattr(sensor, "set_manual_value"):
            await sensor.set_manual_value(float(value))
        else:
            try:
                sensor._attr_native_value = float(value)
                sensor.async_write_ha_state()
            except Exception:
                pass

        # Update journal entry (prepend concise log)
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            journal_line = f"{timestamp}: pH gesetzt {value}"
            if hasattr(target_plant, "journal") and target_plant.journal:
                current = target_plant.journal.state or ""
                new_text = f"{journal_line}\n{current}" if current else journal_line
                await target_plant.journal.async_set_value(new_text)
        except Exception as e:
            _LOGGER.debug("Could not update journal on add_ph: %s", e)

    async def export_plants(call: ServiceCall) -> ServiceResponse:
        """Export selected plant configurations to a ZIP archive."""
        plant_entities = call.data.get("plant_entities", [])
        file_path = call.data.get("file_path", "/config/plants_export.zip")
        include_images = call.data.get("include_images")
        include_sensor_data = call.data.get("include_sensor_data")
        sensor_data_days = call.data.get("sensor_data_days")
        
        # Generate filename based on plant names if default path
        if file_path == "/config/plants_export.zip" and plant_entities:
            plant_names = []
            for entity_id in plant_entities:
                state = hass.states.get(entity_id)
                if state:
                    plant_names.append(state.attributes.get("friendly_name", entity_id.split(".")[-1]))
            
            if plant_names:
                safe_name = "_".join(plant_names).replace(" ", "_").lower()
                file_path = f"/config/{safe_name}.zip"
        
        try:
            # Collect selected plant configurations
            plants_data = []
            all_image_files = []
            
            # Get the config entry to find the image download path
            config_entry = next(
                (entry for entry in hass.config_entries.async_entries(DOMAIN) 
                 if entry.data.get("is_config", False)), 
                None
            )
            download_path = config_entry.data[FLOW_PLANT_INFO].get(FLOW_DOWNLOAD_PATH, DEFAULT_IMAGE_PATH) if config_entry else DEFAULT_IMAGE_PATH
            
            # Find config entries for selected plant entities
            for plant_entity_id in plant_entities:
                # Find the corresponding config entry
                found_entry = None
                for entry_id in hass.data[DOMAIN]:
                    if ATTR_PLANT in hass.data[DOMAIN][entry_id]:
                        plant = hass.data[DOMAIN][entry_id][ATTR_PLANT]
                        if plant.entity_id == plant_entity_id:
                            found_entry = next(
                                (entry for entry in hass.config_entries.async_entries(DOMAIN) 
                                 if entry.entry_id == entry_id), None
                            )
                            break
                
                if found_entry and found_entry.data.get(FLOW_PLANT_INFO):
                    plant_info = found_entry.data[FLOW_PLANT_INFO]
                    device_type = plant_info.get(ATTR_DEVICE_TYPE, DEVICE_TYPE_PLANT)
                    
                    if device_type == DEVICE_TYPE_PLANT:
                        # Create a clean export data structure
                        export_data = {
                            "entry_id": found_entry.entry_id,
                            "title": found_entry.title,
                            "plant_info": dict(plant_info),
                            "options": dict(found_entry.options),
                            "export_timestamp": datetime.now().isoformat()
                        }
                        
                        # Add sensor data if requested
                        if include_sensor_data:
                            sensors = hass.data[DOMAIN][found_entry.entry_id].get(ATTR_SENSORS, [])
                            sensor_entities = []
                            
                            for sensor in sensors:
                                if sensor and hasattr(sensor, 'entity_id'):
                                    sensor_entities.append(sensor.entity_id)
                            
                            # Add the plant entity itself
                            sensor_entities.append(plant_entity_id)
                            
                            # Store sensor entity IDs for history export
                            export_data["sensor_entities"] = sensor_entities
                        
                        # Collect image files if include_images is True
                        if include_images:
                            image_files = []
                            main_image_missing = False
                            
                            # 1. Main image from config entry
                            main_image = plant_info.get(ATTR_ENTITY_PICTURE, "")
                            if main_image:
                                if main_image.startswith("/local/images/plants/"):
                                    # Local file - extract filename
                                    filename = main_image.split("/")[-1]
                                    if filename:
                                        image_files.append(filename)
                                else:
                                    # Web URL - can't export
                                    main_image_missing = True
                            
                            # 2. Additional images from config entry
                            additional_images = plant_info.get("images", [])
                            if isinstance(additional_images, list):
                                image_files.extend(additional_images)
                            
                            # Always set main_image_missing flag in export_data
                            export_data["main_image_missing"] = main_image_missing
                            
                            # Check which files actually exist on disk
                            if image_files:
                                export_data["image_files"] = image_files
                                
                                for image_file in image_files:
                                    image_path = os.path.join(download_path, image_file)
                                    if os.path.exists(image_path):
                                        all_image_files.append((image_path, image_file))
                                        pass
                                    else:
                                        _LOGGER.warning(f"Image not found: {image_file} at {image_path}")
                            
                            # Add warning if main image is missing
                            if main_image_missing:
                                _LOGGER.warning(f"Plant {plant_entity_id}: Main image is web URL, cannot export to ZIP")
                        
                        plants_data.append(export_data)
            
            # Create export structure
            export_structure = {
                "version": "1.0",
                "export_timestamp": datetime.now().isoformat(),
                "total_plants": len(plants_data),
                "include_images": bool(include_images),
                "include_sensor_data": bool(include_sensor_data),
                "plants": plants_data
            }
            
            # Get sensor history data first if requested
            sensor_csv_data = {}
            if include_sensor_data:
                from datetime import timedelta
                end_time = datetime.now()
                # Use all available data if no specific days requested
                if sensor_data_days:
                    start_time = end_time - timedelta(days=sensor_data_days)
                else:
                    # Get all available history (last 365 days max)
                    start_time = end_time - timedelta(days=365)
                
                for plant_data in plants_data:
                    if "sensor_entities" in plant_data:
                        plant_name = plant_data["title"].replace(" ", "_").lower()
                        
                        for entity_id in plant_data["sensor_entities"]:
                            try:
                                # Get history for this sensor
                                recorder = get_instance(hass)
                                history_data = await recorder.async_add_executor_job(
                                    history.state_changes_during_period,
                                    hass,
                                    start_time,
                                    end_time,
                                    entity_id
                                )
                                
                                if entity_id in history_data and history_data[entity_id]:
                                    # Create CSV content
                                    csv_content = "timestamp,state,unit\n"
                                    data_count = 0
                                    
                                    for state in history_data[entity_id]:
                                        if state.state not in ("unknown", "unavailable"):
                                            timestamp = state.last_changed.isoformat()
                                            unit = state.attributes.get("unit_of_measurement", "")
                                            # Fix encoding issues with degree symbol
                                            unit = unit.replace("°", "deg") if unit else ""
                                            csv_content += f"{timestamp},{state.state},{unit}\n"
                                            data_count += 1
                                    
                                    # Only create file if we have actual data
                                    if data_count > 0:
                                        sensor_name = entity_id.replace(".", "_")
                                        csv_filename = f"sensor_data/{plant_name}_{sensor_name}.csv"
                                        sensor_csv_data[csv_filename] = csv_content
                                        _LOGGER.info(f"Exported {data_count} history entries for {entity_id}")
                                    else:
                                        _LOGGER.warning(f"No valid history data found for {entity_id}")
                                else:
                                    _LOGGER.warning(f"No history data returned for {entity_id}")
                                    
                            except Exception as e:
                                _LOGGER.warning(f"Could not export history for {entity_id}: {e}")
            
            # Create ZIP file with everything
            def create_zip():
                with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # Always include the JSON configuration
                    zipf.writestr("plants_config.json", json.dumps(export_structure, indent=2, ensure_ascii=False))
                    
                    # Add images if requested and found
                    if include_images:
                        for image_path, image_filename in all_image_files:
                            zipf.write(image_path, f"images/{image_filename}")
                    
                    # Add sensor history CSV files
                    for csv_filename, csv_content in sensor_csv_data.items():
                        zipf.writestr(csv_filename, csv_content)
            
            await hass.async_add_executor_job(create_zip)
            
            
            # Collect response data
            response_data = {
                "exported_plants": len(plants_data),
                "file_path": file_path
            }
            
            # Add image info if requested
            if include_images:
                response_data["exported_images"] = len(all_image_files)
                
                # Only add missing main images warning if there actually are missing ones
                missing_main_images = []
                for plant_data in plants_data:
                    if plant_data.get("main_image_missing", False):
                        missing_main_images.append(plant_data.get("title", "Unknown"))
                
                if missing_main_images:
                    response_data["missing_main_images"] = missing_main_images
            
            # Add sensor data info if requested
            if include_sensor_data:
                response_data["exported_sensor_files"] = len(sensor_csv_data)
                if sensor_data_days:
                    response_data["sensor_data_days"] = sensor_data_days
                else:
                    response_data["sensor_data_days"] = "all_available"
            
            return response_data
            
        except Exception as e:
            _LOGGER.error(f"Error exporting plants: {e}")
            raise HomeAssistantError(f"Error exporting plants: {e}")

    async def import_plants(call: ServiceCall) -> ServiceResponse:
        """Import plant configurations from a ZIP archive."""
        file_path = call.data.get("file_path")
        new_plant_name = call.data.get("new_plant_name")
        overwrite_existing = call.data.get("overwrite_existing")
        include_images = call.data.get("include_images")
        
        try:
            # Handle ZIP file import
            def read_zip_import():
                with zipfile.ZipFile(file_path, 'r') as zipf:
                    # Check if plants_config.json exists
                    if "plants_config.json" not in zipf.namelist():
                        raise HomeAssistantError("Invalid ZIP file: plants_config.json not found")
                    
                    # Read JSON configuration
                    json_content = zipf.read("plants_config.json").decode('utf-8')
                    data = json.loads(json_content)
                    
                    # Extract images if requested and they exist in the ZIP
                    image_files = [f for f in zipf.namelist() if f.startswith("images/")]
                    extracted_images = {}  # filename -> new_filename mapping
                    
                    if include_images and image_files:
                        # Get the config entry to find the image download path
                        config_entry = next(
                            (entry for entry in hass.config_entries.async_entries(DOMAIN) 
                             if entry.data.get("is_config", False)), 
                            None
                        )
                        download_path = config_entry.data[FLOW_PLANT_INFO].get(FLOW_DOWNLOAD_PATH, DEFAULT_IMAGE_PATH) if config_entry else DEFAULT_IMAGE_PATH
                        
                        # Ensure download directory exists
                        os.makedirs(download_path, exist_ok=True)
                        
                        # Extract all image files
                        for image_file in image_files:
                            # Get just the filename without the 'images/' prefix
                            original_filename = os.path.basename(image_file)
                            target_path = os.path.join(download_path, original_filename)
                            
                            # Extract the image
                            with zipf.open(image_file) as source, open(target_path, "wb") as target:
                                shutil.copyfileobj(source, target)
                            
                            extracted_images[original_filename] = original_filename
                    
                    return data, extracted_images
            
            import_data, extracted_images = await hass.async_add_executor_job(read_zip_import)
            
            if not import_data.get("plants"):
                raise HomeAssistantError("No plants found in import file")
            
            imported_count = 0
            skipped_count = 0
            errors = []
            
            for plant_data in import_data["plants"]:
                try:
                    plant_info = plant_data.get("plant_info", {})
                    original_name = plant_info.get(ATTR_NAME, "Unknown")
                    plant_name = new_plant_name if new_plant_name else original_name
                    
                    # Update plant name in plant_info if new name provided
                    if new_plant_name:
                        plant_info = dict(plant_info)  # Create copy
                        plant_info[ATTR_NAME] = new_plant_name
                        
                        # Rename images if plant is renamed and images were imported
                        if include_images and extracted_images:
                            # Get the config entry to find the image download path
                            config_entry = next(
                                (entry for entry in hass.config_entries.async_entries(DOMAIN) 
                                 if entry.data.get("is_config", False)), 
                                None
                            )
                            download_path = config_entry.data[FLOW_PLANT_INFO].get(FLOW_DOWNLOAD_PATH, DEFAULT_IMAGE_PATH) if config_entry else DEFAULT_IMAGE_PATH
                            
                            # Rename additional images (not main image)
                            if "images" in plant_info and isinstance(plant_info["images"], list):
                                new_images = []
                                for old_image in plant_info["images"]:
                                    if old_image in extracted_images:
                                        # Extract plant name from filename (format: plant.plant_name_timestamp.ext)
                                        if old_image.startswith("plant."):
                                            # Remove "plant." prefix
                                            without_prefix = old_image[6:]  # Remove "plant."
                                            # Find first underscore followed by digits (start of timestamp)
                                            match = re.search(r'_(\d{8}_\d{6})', without_prefix)
                                            if match:
                                                # Extract timestamp and extension
                                                timestamp_with_ext = without_prefix[match.start()+1:]  # +1 to skip the underscore
                                                new_plant_safe = new_plant_name.lower().replace(' ', '_')
                                                new_filename = f"plant.{new_plant_safe}_{timestamp_with_ext}"
                                                
                                                # Rename physical file
                                                old_path = os.path.join(download_path, old_image)
                                                new_path = os.path.join(download_path, new_filename)
                                                
                                                if os.path.exists(old_path):
                                                    try:
                                                        os.rename(old_path, new_path)
                                                        new_images.append(new_filename)
                                                        extracted_images[old_image] = new_filename
                                                        _LOGGER.info(f"Renamed image: {old_image} -> {new_filename}")
                                                    except Exception as e:
                                                        _LOGGER.warning(f"Could not rename image {old_image}: {e}")
                                                        new_images.append(old_image)
                                                else:
                                                    new_images.append(old_image)
                                            else:
                                                new_images.append(old_image)
                                        else:
                                            # Image doesn't start with "plant." - keep as is
                                            new_images.append(old_image)
                                    else:
                                        new_images.append(old_image)
                                
                                plant_info["images"] = new_images
                    
                    # Check if plant already exists
                    existing_entry = None
                    for entry in hass.config_entries.async_entries(DOMAIN):
                        if (entry.data.get(FLOW_PLANT_INFO, {}).get(ATTR_NAME) == plant_name and 
                            entry.data.get(FLOW_PLANT_INFO, {}).get(ATTR_DEVICE_TYPE, DEVICE_TYPE_PLANT) == DEVICE_TYPE_PLANT):
                            existing_entry = entry
                            break
                    
                    if existing_entry and not overwrite_existing:
                        _LOGGER.info(f"Skipping existing plant: {plant_name}")
                        skipped_count += 1
                        continue
                    
                    # Prepare the import data
                    import_config = {
                        FLOW_PLANT_INFO: plant_info
                    }
                    
                    if existing_entry and overwrite_existing:
                        # Update existing entry
                        hass.config_entries.async_update_entry(
                            existing_entry,
                            data=import_config,
                            options=plant_data.get("options", {})
                        )
                        await hass.config_entries.async_reload(existing_entry.entry_id)
                        _LOGGER.info(f"Updated existing plant: {plant_name}")
                    else:
                        # Create new entry
                        await hass.config_entries.flow.async_init(
                            DOMAIN,
                            context={"source": "import"},
                            data=import_config
                        )
                        _LOGGER.info(f"Imported new plant: {plant_name}")
                    
                    imported_count += 1
                    
                except Exception as e:
                    error_msg = f"Error importing plant {plant_name}: {e}"
                    _LOGGER.error(error_msg)
                    errors.append(error_msg)
            
            # Build response data
            response_data = {
                "imported_plants": imported_count,
                "file_path": file_path
            }
            
            if skipped_count > 0:
                response_data["skipped_plants"] = skipped_count
            
            if include_images and extracted_images:
                response_data["imported_images"] = len(extracted_images)
            
            if errors:
                response_data["errors"] = errors
            
            return response_data
            
        except FileNotFoundError:
            raise HomeAssistantError(f"Import file not found: {file_path}")
        except zipfile.BadZipFile:
            raise HomeAssistantError(f"Invalid ZIP file: {file_path}")
        except json.JSONDecodeError as e:
            raise HomeAssistantError(f"Invalid JSON in import file: {e}")
        except Exception as e:
            _LOGGER.error(f"Error importing plants: {e}")
            raise HomeAssistantError(f"Error importing plants: {e}")



    # Register services
    hass.services.async_register(
        DOMAIN, 
        SERVICE_REPLACE_SENSOR, 
        replace_sensor, 
        schema=REPLACE_SENSOR_SCHEMA
    )
    
    # Schema für change_position
    CHANGE_POSITION_SCHEMA = vol.Schema({
        vol.Required("entity_id"): cv.entity_id,
        vol.Optional(ATTR_POSITION_X): vol.Coerce(float),
        vol.Optional(ATTR_POSITION_Y): vol.Coerce(float),
    })
    
    # Registriere den change_position Service
    hass.services.async_register(
        DOMAIN,
        SERVICE_CHANGE_POSITION,
        change_position,
        schema=CHANGE_POSITION_SCHEMA
    )
    
    # Schema für update_plant_attributes
    UPDATE_PLANT_SCHEMA = vol.Schema({
        vol.Required("entity_id"): cv.entity_id,
        vol.Optional("strain"): cv.string,
        vol.Optional("breeder"): cv.string,
        vol.Optional("original_flowering_duration"): cv.positive_int,
        vol.Optional("pid"): cv.string,
        vol.Optional("type"): cv.string,
        vol.Optional("feminized"): cv.boolean,
        vol.Optional("timestamp"): cv.string,
        vol.Optional("effects"): cv.string,
        vol.Optional("smell"): cv.string,
        vol.Optional("taste"): cv.string,
        vol.Optional("phenotype"): cv.string,
        vol.Optional("hunger"): cv.string,
        vol.Optional("growth_stretch"): cv.string,
        vol.Optional("flower_stretch"): cv.string,
        vol.Optional("mold_resistance"): cv.string,
        vol.Optional("difficulty"): cv.string,
        vol.Optional("yield"): cv.string,
        vol.Optional("notes"): cv.string,
        vol.Optional("website"): cv.string,
        vol.Optional("infotext1"): cv.string,
        vol.Optional("infotext2"): cv.string,
        vol.Optional("lineage"): cv.string,
        vol.Optional("images"): cv.string,  # String statt Liste
        vol.Optional(ATTR_POSITION_X): vol.Coerce(float),
        vol.Optional(ATTR_POSITION_Y): vol.Coerce(float),
        # Growth Phase Attribute
        vol.Optional("seeds_start"): cv.string,
        vol.Optional("seeds_duration"): cv.positive_int,
        vol.Optional("germination_start"): cv.string,
        vol.Optional("germination_duration"): cv.positive_int,
        vol.Optional("rooting_start"): cv.string,
        vol.Optional("rooting_duration"): cv.positive_int,
        vol.Optional("growing_start"): cv.string,
        vol.Optional("growing_duration"): cv.positive_int,
        vol.Optional("flowering_start"): cv.string,
        vol.Optional("flower_duration"): cv.positive_int,
        vol.Optional("harvested_date"): cv.string,
        vol.Optional("harvested_duration"): cv.positive_int,
        vol.Optional("removed_date"): cv.string,
        vol.Optional("removed_duration"): cv.positive_int,
    })

    hass.services.async_register(
        DOMAIN,
        "update_plant_attributes",
        update_plant_attributes,
        schema=UPDATE_PLANT_SCHEMA
    )
    hass.services.async_register(DOMAIN, SERVICE_REMOVE_PLANT, remove_plant)
    hass.services.async_register(
        DOMAIN, 
        SERVICE_CREATE_PLANT, 
        create_plant,
        schema=CREATE_PLANT_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL
    )
    hass.services.async_register(DOMAIN, SERVICE_CREATE_CYCLE, create_cycle, supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, SERVICE_MOVE_TO_CYCLE, move_to_cycle)
    hass.services.async_register(DOMAIN, SERVICE_REMOVE_CYCLE, remove_cycle)
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLONE_PLANT,
        handle_clone_plant,
        schema=vol.Schema({
            vol.Required("source_entity_id"): cv.entity_id,
            vol.Optional("name"): cv.string,
            vol.Optional(FLOW_SENSOR_TEMPERATURE): cv.entity_id,
            vol.Optional(FLOW_SENSOR_MOISTURE): cv.entity_id,
            vol.Optional(FLOW_SENSOR_CONDUCTIVITY): cv.entity_id,
            vol.Optional(FLOW_SENSOR_ILLUMINANCE): cv.entity_id,
            vol.Optional(FLOW_SENSOR_HUMIDITY): cv.entity_id,
            vol.Optional(FLOW_SENSOR_CO2): cv.entity_id,
        }),
        supports_response=SupportsResponse.OPTIONAL
    )
    hass.services.async_register(
        DOMAIN, 
        SERVICE_MOVE_TO_AREA,
        move_to_area,
        schema=vol.Schema({
            vol.Required("device_id"): vol.Any(cv.string, [cv.string]),
            vol.Optional("area_id"): cv.string,
        }),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_IMAGE,
        add_image,
        schema=ADD_IMAGE_SCHEMA
    )
    
    # Register add_watering service
    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_WATERING,
        add_watering,
        schema=ADD_WATERING_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_CONDUCTIVITY,
        add_conductivity,
        schema=ADD_CONDUCTIVITY_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_PH,
        add_ph,
        schema=ADD_PH_SCHEMA,
    )
    
    # Register export/import services
    hass.services.async_register(
        DOMAIN,
        SERVICE_EXPORT_PLANTS,
        export_plants,
        schema=EXPORT_PLANTS_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL
    )
    
    hass.services.async_register(
        DOMAIN,
        SERVICE_IMPORT_PLANTS,
        import_plants,
        schema=IMPORT_PLANTS_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL
    )
    


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload Plant services."""
    hass.services.async_remove(DOMAIN, SERVICE_REPLACE_SENSOR)
    hass.services.async_remove(DOMAIN, SERVICE_REMOVE_PLANT)
    hass.services.async_remove(DOMAIN, SERVICE_CREATE_PLANT)
    hass.services.async_remove(DOMAIN, SERVICE_CREATE_CYCLE)
    hass.services.async_remove(DOMAIN, SERVICE_MOVE_TO_CYCLE)
    hass.services.async_remove(DOMAIN, SERVICE_REMOVE_CYCLE)
    hass.services.async_remove(DOMAIN, SERVICE_MOVE_TO_AREA)
    hass.services.async_remove(DOMAIN, SERVICE_ADD_IMAGE)
    hass.services.async_remove(DOMAIN, SERVICE_ADD_WATERING)
    hass.services.async_remove(DOMAIN, SERVICE_ADD_CONDUCTIVITY)
    hass.services.async_remove(DOMAIN, SERVICE_ADD_PH)
    hass.services.async_remove(DOMAIN, SERVICE_CHANGE_POSITION) 
    hass.services.async_remove(DOMAIN, SERVICE_EXPORT_PLANTS)
    hass.services.async_remove(DOMAIN, SERVICE_IMPORT_PLANTS)
 