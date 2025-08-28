"""Support for monitoring plants."""

from __future__ import annotations

import logging
import os
from datetime import datetime

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.components.utility_meter.const import (
    DATA_TARIFF_SENSORS,
    DATA_UTILITY,
)
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    Platform,
    ATTR_ENTITY_PICTURE,
    ATTR_NAME,
    ATTR_UNIT_OF_MEASUREMENT,
    ATTR_ICON,
    STATE_OK,
    STATE_PROBLEM,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
)
from homeassistant.helpers.entity import Entity, async_generate_entity_id
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.storage import Store
from homeassistant.helpers.event import async_call_later

from .const import (
    ATTR_CONDUCTIVITY,
    ATTR_CURRENT,
    ATTR_DLI,
    ATTR_HUMIDITY,
    ATTR_CO2,
    ATTR_ILLUMINANCE,
    ATTR_LIMITS,
    ATTR_MAX,
    ATTR_METERS,
    ATTR_MIN,
    ATTR_MOISTURE,
    ATTR_PLANT,
    ATTR_POWER_CONSUMPTION,
    ATTR_SENSOR,
    ATTR_SENSORS,
    ATTR_STRAIN,
    ATTR_TEMPERATURE,
    ATTR_THRESHOLDS,
    ATTR_TYPE,
    DATA_SOURCE,
    DOMAIN,
    DOMAIN_PLANTBOOK,
    FLOW_CONDUCTIVITY_TRIGGER,
    FLOW_DLI_TRIGGER,
    FLOW_HUMIDITY_TRIGGER,
    FLOW_CO2_TRIGGER,
    FLOW_ILLUMINANCE_TRIGGER,
    FLOW_MOISTURE_TRIGGER,
    FLOW_PLANT_INFO,
    FLOW_TEMPERATURE_TRIGGER,
    FLOW_WATER_CONSUMPTION_TRIGGER,
    FLOW_FERTILIZER_CONSUMPTION_TRIGGER,
    FLOW_POWER_CONSUMPTION_TRIGGER,
    FLOW_SENSOR_TEMPERATURE,
    FLOW_SENSOR_MOISTURE,
    FLOW_SENSOR_CONDUCTIVITY,
    FLOW_SENSOR_ILLUMINANCE,
    FLOW_SENSOR_HUMIDITY,
    FLOW_SENSOR_CO2,
    FLOW_SENSOR_POWER_CONSUMPTION,
    OPB_DISPLAY_PID,
    READING_CONDUCTIVITY,
    READING_DLI,
    READING_HUMIDITY,
    READING_CO2,
    READING_ILLUMINANCE,
    READING_MOISTURE,
    READING_TEMPERATURE,
    READING_POWER_CONSUMPTION,
    STATE_HIGH,
    STATE_LOW,
    ATTR_FLOWERING_DURATION,
    ATTR_BREEDER,
    ATTR_PID,
    ATTR_PHENOTYPE,
    ATTR_HUNGER,
    ATTR_GROWTH_STRETCH,
    ATTR_FLOWER_STRETCH,
    ATTR_MOLD_RESISTANCE,
    ATTR_DIFFICULTY,
    ATTR_YIELD,
    ATTR_NOTES,
    ATTR_IS_NEW_PLANT,
    DEFAULT_GROWTH_PHASE,
    DEVICE_TYPE_PLANT,
    DEVICE_TYPE_CYCLE,
    ATTR_DEVICE_TYPE,
    ICON_DEVICE_PLANT,
    ICON_DEVICE_CYCLE,
    CYCLE_DOMAIN,
    AGGREGATION_MEDIAN,
    AGGREGATION_MEAN,
    AGGREGATION_MIN,
    AGGREGATION_MAX,
    AGGREGATION_ORIGINAL,
    DEFAULT_AGGREGATIONS,
    ATTR_ORIGINAL_FLOWERING_DURATION,
    ATTR_WATER_CONSUMPTION,
    ATTR_FERTILIZER_CONSUMPTION,
    ATTR_KWH_PRICE,
    DEFAULT_KWH_PRICE,
    FLOW_DOWNLOAD_PATH,
    DEFAULT_IMAGE_PATH,
    ATTR_POSITION_X,
    ATTR_POSITION_Y,
    ATTR_PH,
)
from .plant_helpers import PlantHelper
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.NUMBER, Platform.SENSOR, Platform.SELECT, Platform.TEXT]

# Use this during testing to generate some dummy-sensors
# to provide random readings for temperature, moisture etc.
SETUP_DUMMY_SENSORS = False
USE_DUMMY_SENSORS = False

@callback
def _async_find_matching_config_entry(hass: HomeAssistant) -> ConfigEntry | None:
    """Check if there are migrated entities"""
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.source == SOURCE_IMPORT:
            return entry

async def _get_next_id(hass: HomeAssistant, device_type: str) -> str:
    """Get next ID from storage based on device type."""
    store = Store(hass, version=1, key=f"{DOMAIN}_{device_type}_counter")
    data = await store.async_load() or {"counter": 0}
    
    next_id = data["counter"] + 1
    await store.async_save({"counter": next_id})
    
    return f"{next_id:04d}"  # Formatiert als 4-stellige Nummer mit führenden Nullen

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Plant from a config entry."""
    
    # Wenn dies ein Konfigurationsknoten ist
    if entry.data.get("is_config", False):
        hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
            "config": entry.data[FLOW_PLANT_INFO]
        }
        
        # Aktualisiere den kWh Preis in allen Plants/Cycles
        kwh_price = entry.data[FLOW_PLANT_INFO].get(ATTR_KWH_PRICE, DEFAULT_KWH_PRICE)
        for domain_entry_id in hass.data[DOMAIN]:
            if ATTR_PLANT in hass.data[DOMAIN][domain_entry_id]:
                plant = hass.data[DOMAIN][domain_entry_id][ATTR_PLANT]
                plant.update_kwh_price(kwh_price)
        
        return True

    # Normale Plant/Cycle Initialisierung fortsetzen
    plant_data = entry.data[FLOW_PLANT_INFO]
    
    hass.data.setdefault(DOMAIN, {})
    if FLOW_PLANT_INFO not in entry.data:
        return True

    hass.data[DOMAIN].setdefault(entry.entry_id, {})
    _LOGGER.debug("Setting up config entry %s: %s", entry.entry_id, entry)

    # Erstelle PlantDevice und hole oder generiere ID
    plant = PlantDevice(hass, entry)
    
    # Prüfe ob bereits eine ID existiert
    device_type = entry.data[FLOW_PLANT_INFO].get(ATTR_DEVICE_TYPE, DEVICE_TYPE_PLANT)
    id_key = f"{device_type}_id"
    
    if id_key not in entry.data[FLOW_PLANT_INFO]:
        # Generiere neue ID nur wenn keine existiert
        new_id = await _get_next_id(hass, device_type)
        # Speichere ID in der Config Entry
        data = dict(entry.data)
        data[FLOW_PLANT_INFO][id_key] = new_id
        hass.config_entries.async_update_entry(entry, data=data)
    
    # Setze die ID (entweder die existierende oder neue)
    plant._plant_id = entry.data[FLOW_PLANT_INFO].get(id_key)

    # Korrekte Device-Registrierung
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        **plant.device_info
    )

    hass.data[DOMAIN][entry.entry_id][ATTR_PLANT] = plant

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    plant_entities = [
        plant,
    ]

    # Add all the entities to Hass
    component = EntityComponent(_LOGGER, plant.device_type, hass)
    await component.async_add_entities(plant_entities)

    # Add the rest of the entities to device registry together with plant
    device_id = plant.device_id
    await _plant_add_to_device_registry(hass, plant_entities, device_id)
    await _plant_add_to_device_registry(hass, plant.integral_entities, device_id)
    await _plant_add_to_device_registry(hass, plant.threshold_entities, device_id)
    await _plant_add_to_device_registry(hass, plant.meter_entities, device_id)

    #
    # Set up utility sensor
    hass.data.setdefault(DATA_UTILITY, {})
    hass.data[DATA_UTILITY].setdefault(entry.entry_id, {})
    hass.data[DATA_UTILITY][entry.entry_id].setdefault(DATA_TARIFF_SENSORS, [])
    hass.data[DATA_UTILITY][entry.entry_id][DATA_TARIFF_SENSORS].append(plant.dli)

    # Service Setup auslagern - ersetze den alten Service-Code durch:
    await async_setup_services(hass)
    
    # Registriere WebSocket Commands
    websocket_api.async_register_command(hass, ws_get_info)
    websocket_api.async_register_command(hass, ws_upload_image)
    websocket_api.async_register_command(hass, ws_delete_image)
    websocket_api.async_register_command(hass, ws_set_main_image)
    
    plant.async_schedule_update_ha_state(True)

    # Lets add the dummy sensors automatically if we are testing stuff
    if USE_DUMMY_SENSORS is True:
        for sensor in plant.meter_entities:
            if sensor.external_sensor is None:
                await hass.services.async_call(
                    domain=DOMAIN,
                    service=SERVICE_REPLACE_SENSOR,
                    service_data={
                        "meter_entity": sensor.entity_id,
                        "new_sensor": sensor.entity_id.replace(
                            "sensor.", "sensor.dummy_"
                        ),
                    },
                    blocking=False,
                    limit=30,
                )

    # Setze das Flag zurück nach vollständigem Setup
    if entry.data[FLOW_PLANT_INFO].get(ATTR_IS_NEW_PLANT, False):
        data = dict(entry.data)
        data[FLOW_PLANT_INFO][ATTR_IS_NEW_PLANT] = False
        hass.config_entries.async_update_entry(entry, data=data)

    # Wenn ein neuer Cycle erstellt wurde, aktualisiere alle Plant Cycle Selects
    if plant.device_type == DEVICE_TYPE_CYCLE:
        for entry_id in hass.data[DOMAIN]:
            if ATTR_PLANT in hass.data[DOMAIN][entry_id]:
                other_plant = hass.data[DOMAIN][entry_id][ATTR_PLANT]
                if other_plant.device_type == DEVICE_TYPE_PLANT and other_plant.cycle_select:
                    other_plant.cycle_select._update_cycle_options()
                    other_plant.cycle_select.async_write_ha_state()

    return True


async def _plant_add_to_device_registry(
    hass: HomeAssistant, plant_entities: list[Entity], device_id: str
) -> None:
    """Add all related entities to the correct device_id"""

    # There must be a better way to do this, but I just can't find a way to set the
    # device_id when adding the entities.
    erreg = er.async_get(hass)
    for entity in plant_entities:
        if entity is not None and hasattr(entity, 'registry_entry') and entity.registry_entry is not None:
            erreg.async_update_entity(entity.registry_entry.entity_id, device_id=device_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    
    # Wenn dies ein Konfigurationsknoten ist, einfach die Daten entfernen
    if entry.data.get("is_config", False):
        hass.data[DOMAIN].pop(entry.entry_id, None)
        return True

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Entferne zuerst die Daten
        hass.data[DOMAIN].pop(entry.entry_id)
        hass.data[DATA_UTILITY].pop(entry.entry_id)
        
        # Wenn ein Cycle entfernt wird, aktualisiere alle Plant Cycle Selects
        if FLOW_PLANT_INFO in entry.data and entry.data[FLOW_PLANT_INFO].get("device_type") == DEVICE_TYPE_CYCLE:
            _LOGGER.debug("Unloading cycle entry, updating cycle selects")
            
            async def update_cycle_selects(_now=None):
                for entry_id in hass.data[DOMAIN]:
                    if ATTR_PLANT in hass.data[DOMAIN][entry_id]:
                        plant = hass.data[DOMAIN][entry_id][ATTR_PLANT]
                        if plant.device_type == DEVICE_TYPE_PLANT and plant.cycle_select:
                            plant.cycle_select._update_cycle_options()
                            plant.cycle_select.async_write_ha_state()
            
            # Verzögere die Aktualisierung um 1 Sekunde
            async_call_later(hass, 1, update_cycle_selects)

        # Rest der Cleanup-Logik
        for entry_id in list(hass.data[DOMAIN].keys()):
            if len(hass.data[DOMAIN][entry_id]) == 0:
                _LOGGER.info("Removing entry %s", entry_id)
                del hass.data[DOMAIN][entry_id]
        if len(hass.data[DOMAIN]) == 0:
            _LOGGER.info("Removing domain %s", DOMAIN)
            await async_unload_services(hass)
            del hass.data[DOMAIN]
            
    return unload_ok


@websocket_api.websocket_command(
    {
        vol.Required("type"): "plant/get_info",
        vol.Required("entity_id"): str,
    }
)
@callback
def ws_get_info(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Handle the websocket command."""
    # _LOGGER.debug("Got websocket request: %s", msg)

    if DOMAIN not in hass.data:
        connection.send_error(
            msg["id"], "domain_not_found", f"Domain {DOMAIN} not found"
        )
        return

    for key in hass.data[DOMAIN]:
        if not ATTR_PLANT in hass.data[DOMAIN][key]:
            continue
        plant_entity = hass.data[DOMAIN][key][ATTR_PLANT]
        if plant_entity.entity_id == msg["entity_id"]:
            # _LOGGER.debug("Sending websocket response: %s", plant_entity.websocket_info)
            try:
                connection.send_result(
                    msg["id"], {"result": plant_entity.websocket_info}
                )
            except ValueError as e:
                _LOGGER.warning(e)
            return
    connection.send_error(
        msg["id"], "entity_not_found", f"Entity {msg['entity_id']} not found"
    )
    return

@websocket_api.websocket_command(
    {
        vol.Required("type"): "plant/upload_image",
        vol.Required("entity_id"): str,
        vol.Required("filename"): str,
        vol.Required("chunk"): str,
        vol.Required("chunk_index"): int,
        vol.Required("total_chunks"): int,
    }
)
@websocket_api.async_response
async def ws_upload_image(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Handle image upload via websocket in chunks."""
    entity_id = msg["entity_id"]
    filename = msg["filename"]
    chunk = msg["chunk"]
    chunk_index = msg["chunk_index"]
    total_chunks = msg["total_chunks"]

    # Finde die Entity (Plant oder Cycle)
    target_entity = None
    target_entry = None
    for entry_id in hass.data[DOMAIN]:
        if ATTR_PLANT in hass.data[DOMAIN][entry_id]:
            entity = hass.data[DOMAIN][entry_id][ATTR_PLANT]
            if entity.entity_id == entity_id:
                target_entity = entity
                target_entry = hass.config_entries.async_get_entry(entry_id)
                break

    if not target_entity or not target_entry:
        connection.send_error(msg["id"], "entity_not_found", f"Entity {entity_id} not found")
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
        await hass.async_add_executor_job(lambda: os.makedirs(download_path, exist_ok=True))

        # Generiere Dateinamen nur für den ersten Chunk
        if chunk_index == 0:
            # Wenn kein entity_picture existiert, verwende Breeder_Strain Format
            if not target_entity._attr_entity_picture:
                breeder = target_entity._plant_info.get(ATTR_BREEDER, "Unknown")
                strain = target_entity._plant_info.get(ATTR_STRAIN, "Unknown")
                _, ext = os.path.splitext(filename)
                final_filename = f"{breeder}_{strain}{ext}".replace(" ", "_")
                
                # Hole die aktuelle Bilderliste aus der Config Entry
                data = dict(target_entry.data)
                plant_info = dict(data.get(FLOW_PLANT_INFO, {}))
                
                target_entity._attr_entity_picture = f"/local/images/plants/{final_filename}"
                plant_info[ATTR_ENTITY_PICTURE] = f"/local/images/plants/{final_filename}"
                
                # Aktualisiere die Config Entry
                data[FLOW_PLANT_INFO] = plant_info
                hass.config_entries.async_update_entry(target_entry, data=data)
            else:
                # Für alle weiteren Bilder verwende den Timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                _, ext = os.path.splitext(filename)
                final_filename = f"{entity_id}_{timestamp}{ext}"
                
            filepath = os.path.join(download_path, final_filename)
            temp_filepath = f"{filepath}.part"
            
            # Speichere die Pfade in hass.data für nachfolgende Chunks
            if DOMAIN not in hass.data:
                hass.data[DOMAIN] = {}
            if "uploads" not in hass.data[DOMAIN]:
                hass.data[DOMAIN]["uploads"] = {}
            hass.data[DOMAIN]["uploads"][entity_id] = {
                "filepath": filepath,
                "temp_filepath": temp_filepath,
                "final_filename": final_filename
            }
        else:
            # Hole die gespeicherten Pfade für nachfolgende Chunks
            upload_info = hass.data[DOMAIN]["uploads"].get(entity_id)
            if not upload_info:
                connection.send_error(msg["id"], "upload_error", "Upload session not found")
                return
            filepath = upload_info["filepath"]
            temp_filepath = upload_info["temp_filepath"]
            final_filename = upload_info["final_filename"]

        # Schreibe den Chunk in einem Executor
        chunk_data = bytes.fromhex(chunk)
        mode = "ab" if chunk_index > 0 else "wb"
        
        async def write_chunk():
            def _write():
                with open(temp_filepath, mode) as f:
                    f.write(chunk_data)
            await hass.async_add_executor_job(_write)
                
        await write_chunk()

        # Wenn dies der letzte Chunk ist, benenne die Datei um und aktualisiere die Entity
        if chunk_index == total_chunks - 1:
            async def finalize_upload():
                def _finalize():
                    if os.path.exists(temp_filepath):
                        os.rename(temp_filepath, filepath)
                await hass.async_add_executor_job(_finalize)
                    
            await finalize_upload()
            
            # Hole die aktuelle Bilderliste aus der Config Entry
            data = dict(target_entry.data)
            plant_info = dict(data.get(FLOW_PLANT_INFO, {}))
            current_images = list(plant_info.get("images", []))
            
            # Wenn kein Hauptbild existiert, setze dieses als Hauptbild
            if not target_entity._attr_entity_picture:
                breeder = target_entity._plant_info.get(ATTR_BREEDER, "Unknown")
                target_entity._attr_entity_picture = f"/local/images/plants/{final_filename}"
                plant_info[ATTR_ENTITY_PICTURE] = f"/local/images/plants/{final_filename}"
            else:
                # Füge das Bild zur Bilderliste hinzu, wenn es nicht das Entity Picture ist
                entity_picture_filename = target_entity._attr_entity_picture.split("/")[-1]
                if final_filename != entity_picture_filename:
                    if final_filename not in current_images:
                        current_images.append(final_filename)
                        plant_info["images"] = current_images
            
            # Aktualisiere die Config Entry
            data[FLOW_PLANT_INFO] = plant_info
            hass.config_entries.async_update_entry(target_entry, data=data)
            
            # Aktualisiere die Entity
            target_entity._images = current_images
            target_entity._plant_info = plant_info
            target_entity.async_write_ha_state()
            
            # Cleanup
            if entity_id in hass.data[DOMAIN]["uploads"]:
                del hass.data[DOMAIN]["uploads"][entity_id]

        connection.send_result(msg["id"], {"success": True, "chunk_index": chunk_index})

    except Exception as e:
        _LOGGER.error("Error processing image chunk: %s", e)
        # Bei einem Fehler lösche die temporäre Datei
        if "uploads" in hass.data.get(DOMAIN, {}) and entity_id in hass.data[DOMAIN]["uploads"]:
            temp_filepath = hass.data[DOMAIN]["uploads"][entity_id]["temp_filepath"]
            async def cleanup():
                def _cleanup():
                    if os.path.exists(temp_filepath):
                        os.unlink(temp_filepath)
                    if entity_id in hass.data[DOMAIN].get("uploads", {}):
                        del hass.data[DOMAIN]["uploads"][entity_id]
                await hass.async_add_executor_job(_cleanup)
                    
            await cleanup()
        connection.send_error(msg["id"], "upload_failed", str(e))

@websocket_api.websocket_command(
    {
        vol.Required("type"): "plant/delete_image",
        vol.Required("entity_id"): str,
        vol.Required("filename"): str,
    }
)
@websocket_api.async_response
async def ws_delete_image(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Handle image deletion via websocket."""
    entity_id = msg["entity_id"]
    filename = msg["filename"]

    # Finde die Entity (Plant oder Cycle)
    target_entity = None
    target_entry = None
    for entry_id in hass.data[DOMAIN]:
        if ATTR_PLANT in hass.data[DOMAIN][entry_id]:
            entity = hass.data[DOMAIN][entry_id][ATTR_PLANT]
            if entity.entity_id == entity_id:
                target_entity = entity
                target_entry = hass.config_entries.async_get_entry(entry_id)
                break

    if not target_entity or not target_entry:
        connection.send_error(msg["id"], "entity_not_found", f"Entity {entity_id} not found")
        return

    # Hole den Download-Pfad aus der Konfiguration
    config_entry = None
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.data.get("is_config", False):
            config_entry = entry
            break

    download_path = config_entry.data[FLOW_PLANT_INFO].get(FLOW_DOWNLOAD_PATH, DEFAULT_IMAGE_PATH) if config_entry else DEFAULT_IMAGE_PATH

    try:
        # Prüfe ob es sich um das Hauptbild handelt
        is_main_image = False
        if target_entity._attr_entity_picture:
            main_image_filename = target_entity._attr_entity_picture.split("/")[-1]
            if filename == main_image_filename:
                is_main_image = True
                
                # Lösche den entity_picture Pfad
                target_entity._attr_entity_picture = None
                
                # Aktualisiere die Config Entry
                data = dict(target_entry.data)
                plant_info = dict(data.get(FLOW_PLANT_INFO, {}))
                plant_info[ATTR_ENTITY_PICTURE] = None
                data[FLOW_PLANT_INFO] = plant_info
                hass.config_entries.async_update_entry(target_entry, data=data)
                
                # Aktualisiere die Entity
                target_entity._plant_info = plant_info
                target_entity.async_write_ha_state()

        # Lösche die Datei
        filepath = os.path.join(download_path, filename)
        
        def delete_file():
            if os.path.exists(filepath):
                os.unlink(filepath)
                
        await hass.async_add_executor_job(delete_file)

        # Wenn es kein Hauptbild ist, aktualisiere die images Liste
        if not is_main_image:
            # Aktualisiere die Config Entry
            data = dict(target_entry.data)
            plant_info = dict(data.get(FLOW_PLANT_INFO, {}))
            current_images = list(plant_info.get("images", []))
            
            if filename in current_images:
                current_images.remove(filename)
                
                # Aktualisiere die Config Entry
                plant_info["images"] = current_images
                data[FLOW_PLANT_INFO] = plant_info
                hass.config_entries.async_update_entry(target_entry, data=data)
                
                # Aktualisiere die Entity
                target_entity._images = current_images
                target_entity._plant_info = plant_info
                target_entity.async_write_ha_state()

        connection.send_result(msg["id"], {"success": True})

    except Exception as e:
        _LOGGER.error("Error deleting image: %s", e)
        connection.send_error(msg["id"], "delete_failed", str(e))

@websocket_api.websocket_command(
    {
        vol.Required("type"): "plant/set_main_image",
        vol.Required("entity_id"): str,
        vol.Required("filename"): str,
    }
)
@websocket_api.async_response
async def ws_set_main_image(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Handle setting the main image via websocket."""
    entity_id = msg["entity_id"]
    filename = msg["filename"]

    # Finde die Entity (Plant oder Cycle)
    target_entity = None
    target_entry = None
    for entry_id in hass.data[DOMAIN]:
        if ATTR_PLANT in hass.data[DOMAIN][entry_id]:
            entity = hass.data[DOMAIN][entry_id][ATTR_PLANT]
            if entity.entity_id == entity_id:
                target_entity = entity
                target_entry = hass.config_entries.async_get_entry(entry_id)
                break

    if not target_entity or not target_entry:
        connection.send_error(msg["id"], "entity_not_found", f"Entity {entity_id} not found")
        return

    # Hole den Download-Pfad aus der Konfiguration
    config_entry = None
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.data.get("is_config", False):
            config_entry = entry
            break

    download_path = config_entry.data[FLOW_PLANT_INFO].get(FLOW_DOWNLOAD_PATH, DEFAULT_IMAGE_PATH) if config_entry else DEFAULT_IMAGE_PATH

    try:
        # Prüfe ob das Bild existiert
        filepath = os.path.join(download_path, filename)
        if not os.path.exists(filepath):
            connection.send_error(msg["id"], "file_not_found", f"Image {filename} not found")
            return

        # Aktualisiere die Entity
        breeder = target_entity._plant_info.get(ATTR_BREEDER, "Unknown")
        target_entity._attr_entity_picture = f"/local/images/plants/{filename}"
        
        # Aktualisiere die Config Entry
        data = dict(target_entry.data)
        plant_info = dict(data.get(FLOW_PLANT_INFO, {}))
        plant_info[ATTR_ENTITY_PICTURE] = f"/local/images/plants/{filename}"
        data[FLOW_PLANT_INFO] = plant_info
        hass.config_entries.async_update_entry(target_entry, data=data)
        
        # Aktualisiere die Entity
        target_entity._plant_info = plant_info
        target_entity.async_write_ha_state()

        connection.send_result(msg["id"], {"success": True})

    except Exception as e:
        _LOGGER.error("Error setting main image: %s", e)
        connection.send_error(msg["id"], "set_main_image_failed", str(e))


class PlantDevice(Entity):
    """Base device for plants"""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry) -> None:
        """Initialize the Plant/Cycle component."""
        self._config = config
        self._hass = hass
        self._attr_name = config.data[FLOW_PLANT_INFO][ATTR_NAME]
        self._config_entries = []
        self._data_source = config.data[FLOW_PLANT_INFO].get(DATA_SOURCE)
        self._plant_id = None  # Neue Property für die ID
        
        # Get data from config - nur einmal initialisieren
        self._plant_info = config.data.get(FLOW_PLANT_INFO, {})
        
        # Get entity_picture from options or from initial config
        self._attr_entity_picture = self._config.options.get(
            ATTR_ENTITY_PICTURE,
            self._plant_info.get(ATTR_ENTITY_PICTURE),
        )
        
        # Get display_strain from options or from initial config
        self.display_strain = (
            self._config.options.get(
                OPB_DISPLAY_PID, self._plant_info.get(OPB_DISPLAY_PID)
            )
            or self.pid
        )
        
        self._attr_unique_id = self._config.entry_id

        self.device_type = config.data[FLOW_PLANT_INFO].get(ATTR_DEVICE_TYPE, DEVICE_TYPE_PLANT)
        
        # Generiere Entity ID basierend auf Device Type
        domain = DOMAIN if self.device_type == DEVICE_TYPE_PLANT else CYCLE_DOMAIN
        self.entity_id = async_generate_entity_id(
            f"{domain}.{{}}", self.name, current_ids={}
        )

        self.plant_complete = False
        self._device_id = None

        self._check_days = None

        self.max_moisture = None
        self.min_moisture = None
        self.max_temperature = None
        self.min_temperature = None
        self.max_conductivity = None
        self.min_conductivity = None
        self.max_illuminance = None
        self.min_illuminance = None
        self.max_humidity = None
        self.max_CO2 = None
        self.min_humidity = None
        self.min_CO2 = None
        self.max_dli = None
        self.min_dli = None
       
        # Neue Attribute ohne Unterstrich
        self.max_water_consumption = None
        self.min_water_consumption = None
        self.max_fertilizer_consumption = None
        self.min_fertilizer_consumption = None
        self.max_power_consumption = None
        self.min_power_consumption = None

        self.sensor_moisture = None
        self.sensor_temperature = None
        self.sensor_conductivity = None
        self.sensor_illuminance = None
        self.sensor_humidity = None
        self.sensor_CO2 = None
        self.sensor_power_consumption = None
        self.total_power_consumption = None

        self.dli = None
        self.micro_dli = None
        self.ppfd = None
        self.total_integral = None
        self.moisture_consumption = None
        self.total_water_consumption = None  # Füge Total Water Consumption hinzu
        self.fertilizer_consumption = None
        self.total_fertilizer_consumption = None  # Füge Total Fertilizer Consumption hinzu
        self.power_consumption = None

        self.conductivity_status = None
        self.illuminance_status = None
        self.moisture_status = None
        self.temperature_status = None
        self.humidity_status = None
        self.CO2_status = None
        self.dli_status = None
        self.water_consumption_status = None
        self.fertilizer_consumption_status = None
        self.power_consumption_status = None

        self.flowering_duration = None

        # Neue Attribute hinzufügen
        self.website = self._plant_info.get("website", "")
        self.effects = self._plant_info.get("effects", "")
        self.smell = self._plant_info.get("smell", "")
        self.taste = self._plant_info.get("taste", "")
        self.lineage = self._plant_info.get("lineage", "")

        # Diese Attribute nur für Plants setzen
        if self.device_type == DEVICE_TYPE_PLANT:
            self.infotext1 = self._plant_info.get("infotext1", "")
            self.infotext2 = self._plant_info.get("infotext2", "")

        # Benutzerdefinierte Attribute
        self.phenotype = self._plant_info.get(ATTR_PHENOTYPE, "")
        self.hunger = self._plant_info.get(ATTR_HUNGER, "")
        self.growth_stretch = self._plant_info.get(ATTR_GROWTH_STRETCH, "")
        self.flower_stretch = self._plant_info.get(ATTR_FLOWER_STRETCH, "")
        self.mold_resistance = self._plant_info.get(ATTR_MOLD_RESISTANCE, "")
        self.difficulty = self._plant_info.get(ATTR_DIFFICULTY, "")
        self.yield_info = self._plant_info.get(ATTR_YIELD, "")  # yield ist ein Python keyword
        self.notes = self._plant_info.get(ATTR_NOTES, "")

        # Liste der zugehörigen Plants (nur für Cycles)
        self._member_plants = []
        
        # Median Sensoren (nur für Cycles) 
        self._median_sensors = {}

        self.cycle_select = None  # Neue Property

        # Aggregationsmethode für flowering_duration
        self.flowering_duration_aggregation = (
            self._config.options.get("flowering_duration_aggregation") or
            self._plant_info.get("flowering_duration_aggregation", "mean")
        )
        
        # Aggregationsmethode für pot_size
        self.pot_size_aggregation = (
            self._config.options.get("pot_size_aggregation") or
            self._plant_info.get("pot_size_aggregation", "mean")
        )

        # Aggregationsmethode für water_capacity
        self.water_capacity_aggregation = (
            self._config.options.get("water_capacity_aggregation") or
            self._plant_info.get("water_capacity_aggregation", "mean")
        )

        # Neue Property für pot_size
        self.pot_size = None

        # Neue Property für water_capacity
        self.water_capacity = None

        # Hole den kWh Preis aus dem Konfigurationsknoten
        self._kwh_price = DEFAULT_KWH_PRICE
        for entry in hass.config_entries.async_entries(DOMAIN):
            if entry.data.get("is_config", False):
                self._kwh_price = entry.data[FLOW_PLANT_INFO].get(ATTR_KWH_PRICE, DEFAULT_KWH_PRICE)
                break

        # Neue Property für Treatment Select
        self.treatment_select = None

        # Neue Property für Health Number
        self.health_number = None

        # Neue Property für Journal
        self.journal = None
        
        # Neue Property für Location History
        self.location_history = None

        # Initialisiere die Bilderliste
        self._images = self._plant_info.get("images", [])

        # Aggregationsmethode für health
        self.health_aggregation = (
            self._config.options.get("health_aggregation") or
            self._plant_info.get("health_aggregation", "mean")
        )

    @property
    def entity_category(self) -> None:
        """The plant device itself does not have a category"""
        return None

    @property
    def device_class(self):
        """Return the device class."""
        return self.device_type  # Nutzt direkt den device_type (plant oder cycle)

    @property
    def device_id(self) -> str:
        """The device ID used for all the entities"""
        return self._device_id

    @property
    def device_info(self) -> dict:
        """Return device info."""
        device_type = self.device_type
        
        # Basis device_info
        info = {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "serial_number": self._plant_id,
        }
        
        # Spezifische Attribute je nach Device Type
        if device_type == DEVICE_TYPE_PLANT:
            info.update({
                "manufacturer": self._plant_info.get(ATTR_BREEDER, "Unknown"),
                "model": self._plant_info.get(ATTR_STRAIN, ""),
                "model_id": self._plant_info.get(ATTR_TYPE, ""),
            })
        else:  # DEVICE_TYPE_CYCLE
            info.update({
                "manufacturer": "Home Assistant",
                "model": "Cycle",
                "model_id": self._plant_info.get(ATTR_TYPE, ""),
            })
        
        # Optional website hinzufügen wenn vorhanden
        if self.website:
            info["configuration_url"] = self.website
        
        return info

    @property
    def illuminance_trigger(self) -> bool:
        """Whether we will generate alarms based on illuminance"""
        return self._config.options.get(FLOW_ILLUMINANCE_TRIGGER, True)

    @property
    def humidity_trigger(self) -> bool:
        """Whether we will generate alarms based on humidity"""
        return self._config.options.get(FLOW_HUMIDITY_TRIGGER, True)

    @property
    def CO2_trigger(self) -> bool:
        """Whether we will generate alarms based on CO2"""
        return self._config.options.get(FLOW_CO2_TRIGGER, True)

    @property
    def temperature_trigger(self) -> bool:
        """Whether we will generate alarms based on temperature"""
        return self._config.options.get(FLOW_TEMPERATURE_TRIGGER, True)

    @property
    def dli_trigger(self) -> bool:
        """Whether we will generate alarms based on dli"""
        return self._config.options.get(FLOW_DLI_TRIGGER, True)

    @property
    def moisture_trigger(self) -> bool:
        """Whether we will generate alarms based on moisture"""
        return self._config.options.get(FLOW_MOISTURE_TRIGGER, True)

    @property
    def conductivity_trigger(self) -> bool:
        """Whether we will generate alarms based on conductivity"""
        return self._config.options.get(FLOW_CONDUCTIVITY_TRIGGER, True)

    @property
    def water_consumption_trigger(self) -> bool:
        """Whether we will generate alarms based on water consumption"""
        return self._config.options.get(FLOW_WATER_CONSUMPTION_TRIGGER, True)

    @property
    def fertilizer_consumption_trigger(self) -> bool:
        """Whether we will generate alarms based on fertilizer consumption"""
        return self._config.options.get(FLOW_FERTILIZER_CONSUMPTION_TRIGGER, True)

    @property
    def power_consumption_trigger(self) -> bool:
        """Return if power consumption should trigger problems."""
        return self._config.data[FLOW_PLANT_INFO].get(FLOW_POWER_CONSUMPTION_TRIGGER, True)

    @property
    def breeder(self) -> str:
        """Return the breeder."""
        return self._plant_info.get(ATTR_BREEDER, "")

    @property
    def type(self) -> str:
        """Return the type."""
        return self._plant_info.get(ATTR_TYPE, "")

    @property
    def feminized(self) -> str:
        """Return the feminized status."""
        return self._plant_info.get("feminized", "")

    @property
    def timestamp(self) -> str:
        """Return the timestamp."""
        return self._plant_info.get("timestamp", "")

    @property
    def pid(self) -> str:
        """Return the pid."""
        return self._plant_info.get(ATTR_PID, "")

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attrs = {
            "strain": self._plant_info.get(ATTR_STRAIN, ""),
            "breeder": self._plant_info.get(ATTR_BREEDER, ""),
            "original_flowering_duration": self._plant_info.get(ATTR_ORIGINAL_FLOWERING_DURATION),
            "moisture_status": self.moisture_status,
            "temperature_status": self.temperature_status,
            "conductivity_status": self.conductivity_status,
            "illuminance_status": self.illuminance_status,
            "humidity_status": self.humidity_status,
            "CO2_status": self.CO2_status,
            "dli_status": self.dli_status,
            "water_consumption_status": self.water_consumption_status,
            "fertilizer_consumption_status": self.fertilizer_consumption_status,
            "power_consumption_status": self.power_consumption_status,
            "pid": self.pid,
            "type": self._plant_info.get(ATTR_TYPE, ""),
            "feminized": self._plant_info.get("feminized", ""),
            "timestamp": self._plant_info.get("timestamp", ""),
            "effects": self._plant_info.get("effects", ""),
            "smell": self._plant_info.get("smell", ""),
            "taste": self._plant_info.get("taste", ""),
            "phenotype": self._plant_info.get(ATTR_PHENOTYPE, ""),
            "hunger": self._plant_info.get(ATTR_HUNGER, ""),
            "growth_stretch": self._plant_info.get(ATTR_GROWTH_STRETCH, ""),
            "flower_stretch": self._plant_info.get(ATTR_FLOWER_STRETCH, ""),
            "mold_resistance": self._plant_info.get(ATTR_MOLD_RESISTANCE, ""),
            "difficulty": self._plant_info.get(ATTR_DIFFICULTY, ""),
            "yield": self._plant_info.get(ATTR_YIELD, ""),
            "notes": self._plant_info.get(ATTR_NOTES, ""),
            "website": self._plant_info.get("website", ""),
            "images": self._images,
        }

        # Füge member_count für Cycles hinzu
        if self.device_type == DEVICE_TYPE_CYCLE:
            attrs = {"member_count": len(self._member_plants)} | attrs

        # Füge Plant-spezifische Attribute nur für Plants hinzu
        if self.device_type == DEVICE_TYPE_PLANT:
            attrs.update({
                "infotext1": self._plant_info.get("infotext1", ""),
                "infotext2": self._plant_info.get("infotext2", ""),
                "lineage": self._plant_info.get("lineage", ""),
            })

        return attrs

    @property
    def websocket_info(self) -> dict:
        """Wesocket response"""
        if not self.plant_complete:
            # We are not fully set up, so we just return an empty dict for now
            return {}

        # Hole den Download-Pfad aus der Konfiguration und konvertiere ihn
        config_entry = None
        for entry in self._hass.config_entries.async_entries(DOMAIN):
            if entry.data.get("is_config", False):
                config_entry = entry
                break

        download_path = config_entry.data[FLOW_PLANT_INFO].get(FLOW_DOWNLOAD_PATH, DEFAULT_IMAGE_PATH) if config_entry else DEFAULT_IMAGE_PATH
        # Konvertiere /config/www/ zu /local/
        web_path = download_path.replace("/config/www/", "/local/")

        # Basis-Response mit Hauptsensoren
        response = {
            "path": web_path,  # Der konvertierte Pfad
            "device_type": self.device_type,  # Füge device_type hinzu (plant oder cycle)
            "entity_id": self.entity_id,  # Füge die Haupt-Entity-ID hinzu
            "name": self.name,  # Füge den Namen hinzu
            "icon": self.icon,  # Füge das Icon hinzu
            "state": self.state,  # Füge den Zustand hinzu
            
            # Ursprüngliche Sensor-Info beibehalten
            ATTR_TEMPERATURE: {
                ATTR_MAX: self.max_temperature.state,
                ATTR_MIN: self.min_temperature.state,
                ATTR_CURRENT: self.sensor_temperature.state or STATE_UNAVAILABLE,
                ATTR_ICON: self.sensor_temperature.icon,
                ATTR_UNIT_OF_MEASUREMENT: self.sensor_temperature.unit_of_measurement,
                ATTR_SENSOR: self.sensor_temperature.entity_id,
            },
            ATTR_ILLUMINANCE: {
                ATTR_MAX: self.max_illuminance.state,
                ATTR_MIN: self.min_illuminance.state,
                ATTR_CURRENT: self.sensor_illuminance.state or STATE_UNAVAILABLE,
                ATTR_ICON: self.sensor_illuminance.icon,
                ATTR_UNIT_OF_MEASUREMENT: self.sensor_illuminance.unit_of_measurement,
                ATTR_SENSOR: self.sensor_illuminance.entity_id,
            },
            ATTR_MOISTURE: {
                ATTR_MAX: self.max_moisture.state,
                ATTR_MIN: self.min_moisture.state,
                ATTR_CURRENT: self.sensor_moisture.state or STATE_UNAVAILABLE,
                ATTR_ICON: self.sensor_moisture.icon,
                ATTR_UNIT_OF_MEASUREMENT: self.sensor_moisture.unit_of_measurement,
                ATTR_SENSOR: self.sensor_moisture.entity_id,
            },
            ATTR_CONDUCTIVITY: {
                ATTR_MAX: self.max_conductivity.state,
                ATTR_MIN: self.min_conductivity.state,
                ATTR_CURRENT: self.sensor_conductivity.state or STATE_UNAVAILABLE,
                ATTR_ICON: self.sensor_conductivity.icon,
                ATTR_UNIT_OF_MEASUREMENT: self.sensor_conductivity.unit_of_measurement,
                ATTR_SENSOR: self.sensor_conductivity.entity_id,
            },
            ATTR_HUMIDITY: {
                ATTR_MAX: self.max_humidity.state,
                ATTR_MIN: self.min_humidity.state,
                ATTR_CURRENT: self.sensor_humidity.state or STATE_UNAVAILABLE,
                ATTR_ICON: self.sensor_humidity.icon,
                ATTR_UNIT_OF_MEASUREMENT: self.sensor_humidity.unit_of_measurement,
                ATTR_SENSOR: self.sensor_humidity.entity_id,
            },
            ATTR_CO2: {
                ATTR_MAX: self.max_CO2.state,
                ATTR_MIN: self.min_CO2.state,
                ATTR_CURRENT: self.sensor_CO2.state or STATE_UNAVAILABLE,
                ATTR_ICON: self.sensor_CO2.icon,
                ATTR_UNIT_OF_MEASUREMENT: self.sensor_CO2.unit_of_measurement,
                ATTR_SENSOR: self.sensor_CO2.entity_id,
            },
            ATTR_DLI: {
                ATTR_MAX: self.max_dli.state,
                ATTR_MIN: self.min_dli.state,
                ATTR_CURRENT: self.dli.state if self.dli.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE) else STATE_UNAVAILABLE,
                ATTR_ICON: self.dli.icon,
                ATTR_UNIT_OF_MEASUREMENT: self.dli.unit_of_measurement,
                ATTR_SENSOR: self.dli.entity_id,
            },
            ATTR_WATER_CONSUMPTION: {
                ATTR_MAX: self.max_water_consumption.state,
                ATTR_MIN: self.min_water_consumption.state,
                ATTR_CURRENT: self.moisture_consumption.state or STATE_UNAVAILABLE,
                ATTR_ICON: self.moisture_consumption.icon,
                ATTR_UNIT_OF_MEASUREMENT: self.moisture_consumption.unit_of_measurement,
                ATTR_SENSOR: self.moisture_consumption.entity_id,
            },
            ATTR_FERTILIZER_CONSUMPTION: {
                ATTR_MAX: self.max_fertilizer_consumption.state,
                ATTR_MIN: self.min_fertilizer_consumption.state,
                ATTR_CURRENT: self.fertilizer_consumption.state or STATE_UNAVAILABLE,
                ATTR_ICON: self.fertilizer_consumption.icon,
                ATTR_UNIT_OF_MEASUREMENT: self.fertilizer_consumption.unit_of_measurement,
                ATTR_SENSOR: self.fertilizer_consumption.entity_id,
            },
            ATTR_POWER_CONSUMPTION: {
                ATTR_MAX: self.max_power_consumption.state,
                ATTR_MIN: self.min_power_consumption.state,
                ATTR_CURRENT: self.sensor_power_consumption.state or STATE_UNAVAILABLE,
                ATTR_ICON: self.sensor_power_consumption.icon,
                ATTR_UNIT_OF_MEASUREMENT: self.sensor_power_consumption.unit_of_measurement,
                ATTR_SENSOR: self.sensor_power_consumption.entity_id,
            },
            ATTR_PH: {
                ATTR_MAX: self.max_ph.state,
                ATTR_MIN: self.min_ph.state,
                ATTR_CURRENT: self.sensor_ph.state or STATE_UNAVAILABLE,
                ATTR_ICON: self.sensor_ph.icon,
                ATTR_UNIT_OF_MEASUREMENT: self.sensor_ph.unit_of_measurement,
                ATTR_SENSOR: self.sensor_ph.entity_id,
            },
            
            # Neue Struktur: Separater Bereich für Diagnosesensoren
            "diagnostic_sensors": {},
            
            # Helper-Entities bleiben in eigener Kategorie
            "helpers": {}
        }

        # Diagnosesensoren hinzufügen
        diagnostics = response["diagnostic_sensors"]
        
        if hasattr(self, 'energy_cost') and self.energy_cost:
            diagnostics["energy_cost"] = {
                "entity_id": self.energy_cost.entity_id,
                "current": self.energy_cost.state,
                "icon": self.energy_cost.icon,
                "unit_of_measurement": self.energy_cost.native_unit_of_measurement,
            }
        
        if self.total_power_consumption:
            diagnostics["total_power_consumption"] = {
                "entity_id": self.total_power_consumption.entity_id,
                "current": self.total_power_consumption.state,
                "icon": self.total_power_consumption.icon,
                "unit_of_measurement": self.total_power_consumption.native_unit_of_measurement,
            }
        
        if self.total_integral:
            # Der Wert kommt als decimal.Decimal vom Sensor
            current_value = self.total_integral.state
            
            # Konvertiere zu float für JSON-Serialisierung
            if current_value not in (STATE_UNAVAILABLE, STATE_UNKNOWN, None):
                try:
                    # Explizite Konvertierung zu float
                    current_value = float(current_value)
                except (ValueError, TypeError):
                    current_value = STATE_UNAVAILABLE
                
            diagnostics["total_integral"] = {
                "entity_id": self.total_integral.entity_id,
                "current": current_value,  # Jetzt als float oder Fehlerstring
                "icon": self.total_integral.icon,
                "unit_of_measurement": self.total_integral.native_unit_of_measurement,
            }
        
        # Füge total_water_consumption hinzu
        if self.total_water_consumption:
            current_value = self.total_water_consumption.state
            if current_value not in (STATE_UNAVAILABLE, STATE_UNKNOWN, None):
                try:
                    current_value = float(current_value)
                except (ValueError, TypeError):
                    current_value = STATE_UNAVAILABLE
                
            diagnostics["total_water_consumption"] = {
                "entity_id": self.total_water_consumption.entity_id,
                "current": current_value,
                "icon": self.total_water_consumption.icon,
                "unit_of_measurement": self.total_water_consumption.native_unit_of_measurement,
            }
        
        # Füge total_fertilizer_consumption hinzu
        if self.total_fertilizer_consumption:
            current_value = self.total_fertilizer_consumption.state
            if current_value not in (STATE_UNAVAILABLE, STATE_UNKNOWN, None):
                try:
                    current_value = float(current_value)
                except (ValueError, TypeError):
                    current_value = STATE_UNAVAILABLE
                
            diagnostics["total_fertilizer_consumption"] = {
                "entity_id": self.total_fertilizer_consumption.entity_id,
                "current": current_value,
                "icon": self.total_fertilizer_consumption.icon,
                "unit_of_measurement": self.total_fertilizer_consumption.native_unit_of_measurement,
            }
        
        # Dann nur echte Helper Entities in "helpers" einfügen (Selects, Numbers, Texts)
        helpers = response["helpers"]
        
        # Growth Phase Select
        if self.growth_phase_select:
            helpers["growth_phase"] = {
                "entity_id": self.growth_phase_select.entity_id,
                "current": self.growth_phase_select.state,
                "icon": self.growth_phase_select.icon,
                "options": self.growth_phase_select.options,
                "type": "select"
            }
        
        # Flowering Duration Number
        if self.flowering_duration:
            helpers["flowering_duration"] = {
                "entity_id": self.flowering_duration.entity_id,
                "current": self.flowering_duration.state,
                "icon": self.flowering_duration.icon,
                "unit_of_measurement": self.flowering_duration.native_unit_of_measurement,
                "min": self.flowering_duration.native_min_value,
                "max": self.flowering_duration.native_max_value,
                "step": self.flowering_duration.native_step,
                "type": "number"
            }
        
        # Pot Size Number
        if self.pot_size:
            helpers["pot_size"] = {
                "entity_id": self.pot_size.entity_id,
                "current": self.pot_size.state,
                "icon": self.pot_size.icon,
                "unit_of_measurement": self.pot_size.native_unit_of_measurement,
                "min": self.pot_size.native_min_value,
                "max": self.pot_size.native_max_value,
                "step": self.pot_size.native_step,
                "type": "number"
            }
        
        # Water Capacity Number
        if self.water_capacity:
            helpers["water_capacity"] = {
                "entity_id": self.water_capacity.entity_id,
                "current": self.water_capacity.state,
                "icon": self.water_capacity.icon,
                "unit_of_measurement": self.water_capacity.native_unit_of_measurement,
                "min": self.water_capacity.native_min_value,
                "max": self.water_capacity.native_max_value,
                "step": self.water_capacity.native_step,
                "type": "number"
            }
        
        # Treatment Select
        if self.treatment_select:
            helpers["treatment"] = {
                "entity_id": self.treatment_select.entity_id,
                "current": self.treatment_select.state,
                "icon": self.treatment_select.icon,
                "options": self.treatment_select.options,
                "type": "select"
            }
        
        # Health Number
        if self.health_number:
            helpers["health"] = {
                "entity_id": self.health_number.entity_id,
                "current": self.health_number.state,
                "icon": self.health_number.icon,
                "unit_of_measurement": self.health_number.native_unit_of_measurement,
                "min": self.health_number.native_min_value,
                "max": self.health_number.native_max_value,
                "step": self.health_number.native_step,
                "type": "number"
            }
        
        # Journal Text
        if self.journal:
            helpers["journal"] = {
                "entity_id": self.journal.entity_id,
                "current": self.journal.state,
                "icon": self.journal.icon,
                "type": "text"
            }
        
        # Location History Text
        if self.location_history:
            helpers["location"] = {
                "entity_id": self.location_history.entity_id,
                "current": self.location_history.state,
                "icon": self.location_history.icon,
                "type": "text"
            }
        
        # Cycle Select (nur für Plants)
        if self.cycle_select:
            helpers["cycle"] = {
                "entity_id": self.cycle_select.entity_id,
                "current": self.cycle_select.state,
                "icon": self.cycle_select.icon,
                "options": self.cycle_select.options,
                "type": "select"
            }

        return response

    @property
    def threshold_entities(self) -> list[Entity]:
        """List all threshold entities"""
        return [
            self.max_conductivity,
            self.max_dli,
            self.max_humidity,
            self.max_CO2,
            self.max_illuminance,
            self.max_moisture,
            self.max_temperature,
            self.min_conductivity,
            self.min_dli,
            self.min_humidity,
            self.min_CO2,
            self.min_illuminance,
            self.min_moisture,
            self.min_temperature,
            self.max_water_consumption,
            self.min_water_consumption,
            self.max_fertilizer_consumption,
            self.min_fertilizer_consumption,
            self.max_power_consumption,
            self.min_power_consumption,
            self.max_ph,  # Neue pH Entities
            self.min_ph,
        ]

    @property
    def meter_entities(self) -> list[Entity]:
        """List all meter (sensor) entities"""
        return [
            self.sensor_conductivity,
            self.sensor_humidity,
            self.sensor_CO2,
            self.sensor_illuminance,
            self.sensor_moisture,
            self.sensor_temperature,
            self.sensor_power_consumption,
            self.sensor_ph,  # pH-Sensor hinzufügen
        ]

    @property
    def integral_entities(self) -> list(Entity):
        """List all integral entities"""
        return [
            self.dli,
            self.ppfd,
            self.total_integral,
            self.moisture_consumption,
            self.fertilizer_consumption,
        ]

    def add_image(self, image_url: str | None) -> None:
        """Set new entity_picture"""
        self._attr_entity_picture = image_url
        options = self._config.options.copy()
        options[ATTR_ENTITY_PICTURE] = image_url
        self._hass.config_entries.async_update_entry(self._config, options=options)

    def add_strain(self, strain: Entity | None) -> None:
        """Set new strain"""
        self.pid = strain

    def add_thresholds(
        self,
        max_moisture: Entity | None,
        min_moisture: Entity | None,
        max_temperature: Entity | None,
        min_temperature: Entity | None,
        max_conductivity: Entity | None,
        min_conductivity: Entity | None,
        max_illuminance: Entity | None,
        min_illuminance: Entity | None,
        max_humidity: Entity | None,
        min_humidity: Entity | None,
        max_CO2: Entity | None,
        min_CO2: Entity | None,
        max_dli: Entity | None,
        min_dli: Entity | None,
        max_water_consumption: Entity | None,
        min_water_consumption: Entity | None,
        max_fertilizer_consumption: Entity | None,
        min_fertilizer_consumption: Entity | None,
        max_power_consumption: Entity | None,
        min_power_consumption: Entity | None,
        max_ph: Entity | None,  # Neue Parameter
        min_ph: Entity | None,
    ) -> None:
        """Add threshold entities to the plant"""
        self.max_moisture = max_moisture
        self.min_moisture = min_moisture
        self.max_temperature = max_temperature
        self.min_temperature = min_temperature
        self.max_conductivity = max_conductivity
        self.min_conductivity = min_conductivity
        self.max_illuminance = max_illuminance
        self.min_illuminance = min_illuminance
        self.max_humidity = max_humidity
        self.min_humidity = min_humidity
        self.max_CO2 = max_CO2
        self.min_CO2 = min_CO2
        self.max_dli = max_dli
        self.min_dli = min_dli
        self.max_water_consumption = max_water_consumption
        self.min_water_consumption = min_water_consumption
        self.max_fertilizer_consumption = max_fertilizer_consumption
        self.min_fertilizer_consumption = min_fertilizer_consumption
        self.max_power_consumption = max_power_consumption
        self.min_power_consumption = min_power_consumption
        self.max_ph = max_ph  # Neue Zuweisungen
        self.min_ph = min_ph

    def add_sensors(
        self,
        moisture: Entity | None,
        temperature: Entity | None,
        conductivity: Entity | None,
        illuminance: Entity | None,
        humidity: Entity | None,
        CO2: Entity | None,
        power_consumption: Entity | None,
        ph: Entity | None,  # Neuer Parameter
    ) -> None:
        """Add the sensor entities"""
        self.sensor_moisture = moisture
        self.sensor_temperature = temperature
        self.sensor_conductivity = conductivity
        self.sensor_illuminance = illuminance
        self.sensor_humidity = humidity
        self.sensor_CO2 = CO2
        self.sensor_power_consumption = power_consumption
        self.sensor_ph = ph  # Neue Zuweisung

    def add_dli(
        self,
        dli: Entity | None,
    ) -> None:
        """Add the DLI-utility sensors"""
        self.dli = dli
        self.plant_complete = True

    def add_calculations(self, ppfd: Entity, total_integral: Entity, moisture_consumption: Entity, fertilizer_consumption: Entity) -> None:
        """Add the intermediate calculation entities"""
        self.ppfd = ppfd
        self.total_integral = total_integral
        self.moisture_consumption = moisture_consumption
        self.fertilizer_consumption = fertilizer_consumption

    def add_growth_phase_select(self, growth_phase_select: Entity) -> None:
        """Add the growth phase select entity."""
        self.growth_phase_select = growth_phase_select

    def add_flowering_duration(self, flowering_duration: Entity) -> None:
        """Füge die Blütedauer Number Entity hinzu."""
        self.flowering_duration = flowering_duration

    def update(self) -> None:
        """Run on every update of the entities"""
        new_state = STATE_OK
        known_state = False

        if self.device_type == DEVICE_TYPE_CYCLE:
            # Cycle-Update-Logik
            if self.sensor_temperature is not None:
                temperature = self._median_sensors.get('temperature')
                if temperature is not None:
                    known_state = True
                    if float(temperature) < float(self.min_temperature.state):
                        self.temperature_status = STATE_LOW
                        if self.temperature_trigger:
                            new_state = STATE_PROBLEM
                    elif float(temperature) > float(self.max_temperature.state):
                        self.temperature_status = STATE_HIGH
                        if self.temperature_trigger:
                            new_state = STATE_PROBLEM
                    else:
                        self.temperature_status = STATE_OK

            if self.sensor_moisture is not None:
                moisture = self._median_sensors.get('moisture')
                if moisture is not None:
                    known_state = True
                    if float(moisture) < float(self.min_moisture.state):
                        self.moisture_status = STATE_LOW
                        if self.moisture_trigger:
                            new_state = STATE_PROBLEM
                    elif float(moisture) > float(self.max_moisture.state):
                        self.moisture_status = STATE_HIGH
                        if self.moisture_trigger:
                            new_state = STATE_PROBLEM
                    else:
                        self.moisture_status = STATE_OK

            if self.sensor_conductivity is not None:
                conductivity = self._median_sensors.get('conductivity')
                if conductivity is not None:
                    known_state = True
                    if float(conductivity) < float(self.min_conductivity.state):
                        self.conductivity_status = STATE_LOW
                        if self.conductivity_trigger:
                            new_state = STATE_PROBLEM
                    elif float(conductivity) > float(self.max_conductivity.state):
                        self.conductivity_status = STATE_HIGH
                        if self.conductivity_trigger:
                            new_state = STATE_PROBLEM
                    else:
                        self.conductivity_status = STATE_OK

            if self.sensor_illuminance is not None:
                illuminance = self._median_sensors.get('illuminance')
                if illuminance is not None:
                    known_state = True
                    if float(illuminance) < float(self.min_illuminance.state):
                        self.illuminance_status = STATE_LOW
                        if self.illuminance_trigger:
                            new_state = STATE_PROBLEM
                    elif float(illuminance) > float(self.max_illuminance.state):
                        self.illuminance_status = STATE_HIGH
                        if self.illuminance_trigger:
                            new_state = STATE_PROBLEM
                    else:
                        self.illuminance_status = STATE_OK

            if self.sensor_humidity is not None:
                humidity = self._median_sensors.get('humidity')
                if humidity is not None:
                    known_state = True
                    if float(humidity) < float(self.min_humidity.state):
                        self.humidity_status = STATE_LOW
                        if self.humidity_trigger:
                            new_state = STATE_PROBLEM
                    elif float(humidity) > float(self.max_humidity.state):
                        self.humidity_status = STATE_HIGH
                        if self.humidity_trigger:
                            new_state = STATE_PROBLEM
                    else:
                        self.humidity_status = STATE_OK

            if self.sensor_CO2 is not None:
                CO2 = self._median_sensors.get('CO2')
                if CO2 is not None:
                    known_state = True
                    if float(CO2) < float(self.min_CO2.state):
                        self.CO2_status = STATE_LOW
                        if self.CO2_trigger:
                            new_state = STATE_PROBLEM
                    elif float(CO2) > float(self.max_CO2.state):
                        self.CO2_status = STATE_HIGH
                        if self.CO2_trigger:
                            new_state = STATE_PROBLEM
                    else:
                        self.CO2_status = STATE_OK

            if self.dli is not None:
                dli = self._median_sensors.get('dli')
                if dli is not None:
                    known_state = True
                    if float(dli) < float(self.min_dli.state):
                        self.dli_status = STATE_LOW
                        if self.dli_trigger:
                            new_state = STATE_PROBLEM
                    elif float(dli) > float(self.max_dli.state):
                        self.dli_status = STATE_HIGH
                        if self.dli_trigger:
                            new_state = STATE_PROBLEM
                    else:
                        self.dli_status = STATE_OK

            # Überprüfe Wasser-Verbrauch
            if self.moisture_consumption is not None:
                water_consumption = self.moisture_consumption.state
                if water_consumption is not None and water_consumption != STATE_UNAVAILABLE and water_consumption != STATE_UNKNOWN:
                    known_state = True
                    if float(water_consumption) < float(self.min_water_consumption.state):
                        self.water_consumption_status = STATE_LOW
                        if self.water_consumption_trigger:
                            new_state = STATE_PROBLEM
                    elif float(water_consumption) > float(self.max_water_consumption.state):
                        self.water_consumption_status = STATE_HIGH
                        if self.water_consumption_trigger:
                            new_state = STATE_PROBLEM
                    else:
                        self.water_consumption_status = STATE_OK

            # Überprüfe Dünger-Verbrauch
            if self.fertilizer_consumption is not None:
                fertilizer_consumption = self.fertilizer_consumption.state
                if fertilizer_consumption is not None and fertilizer_consumption != STATE_UNAVAILABLE and fertilizer_consumption != STATE_UNKNOWN:
                    known_state = True
                    if float(fertilizer_consumption) < float(self.min_fertilizer_consumption.state):
                        self.fertilizer_consumption_status = STATE_LOW
                        if self.fertilizer_consumption_trigger:
                            new_state = STATE_PROBLEM
                    elif float(fertilizer_consumption) > float(self.max_fertilizer_consumption.state):
                        self.fertilizer_consumption_status = STATE_HIGH
                        if self.fertilizer_consumption_trigger:
                            new_state = STATE_PROBLEM
                    else:
                        self.fertilizer_consumption_status = STATE_OK

            # Überprüfe Power Consumption
            if self.sensor_power_consumption is not None:
                power_consumption = self.sensor_power_consumption.state
                if power_consumption is not None and power_consumption != STATE_UNAVAILABLE and power_consumption != STATE_UNKNOWN:
                    known_state = True
                    if float(power_consumption) < float(self.min_power_consumption.state):
                        self.power_consumption_status = STATE_LOW
                        if self.power_consumption_trigger:
                            new_state = STATE_PROBLEM
                    elif float(power_consumption) > float(self.max_power_consumption.state):
                        self.power_consumption_status = STATE_HIGH
                        if self.power_consumption_trigger:
                            new_state = STATE_PROBLEM
                    else:
                        self.power_consumption_status = STATE_OK

        else:
            # Plant-Update-Logik
            if self.sensor_moisture is not None:
                moisture = self.sensor_moisture.state
                if moisture is not None and moisture != STATE_UNAVAILABLE and moisture != STATE_UNKNOWN:
                    known_state = True
                    if float(moisture) < float(self.min_moisture.state):
                        self.moisture_status = STATE_LOW
                        if self.moisture_trigger:
                            new_state = STATE_PROBLEM
                    elif float(moisture) > float(self.max_moisture.state):
                        self.moisture_status = STATE_HIGH
                        if self.moisture_trigger:
                            new_state = STATE_PROBLEM
                    else:
                        self.moisture_status = STATE_OK

            if self.sensor_conductivity is not None:
                conductivity = self.sensor_conductivity.state
                if conductivity is not None and conductivity != STATE_UNAVAILABLE and conductivity != STATE_UNKNOWN:
                    known_state = True
                    if float(conductivity) < float(self.min_conductivity.state):
                        self.conductivity_status = STATE_LOW
                        if self.conductivity_trigger:
                            new_state = STATE_PROBLEM
                    elif float(conductivity) > float(self.max_conductivity.state):
                        self.conductivity_status = STATE_HIGH
                        if self.conductivity_trigger:
                            new_state = STATE_PROBLEM
                    else:
                        self.conductivity_status = STATE_OK

            # Füge die fehlenden Sensor-Prüfungen hinzu
            if self.sensor_temperature is not None:
                temperature = self.sensor_temperature.state
                if temperature is not None and temperature != STATE_UNAVAILABLE and temperature != STATE_UNKNOWN:
                    known_state = True
                    if float(temperature) < float(self.min_temperature.state):
                        self.temperature_status = STATE_LOW
                        if self.temperature_trigger:
                            new_state = STATE_PROBLEM
                    elif float(temperature) > float(self.max_temperature.state):
                        self.temperature_status = STATE_HIGH
                        if self.temperature_trigger:
                            new_state = STATE_PROBLEM
                    else:
                        self.temperature_status = STATE_OK

            if self.sensor_illuminance is not None:
                illuminance = self.sensor_illuminance.state
                if illuminance is not None and illuminance != STATE_UNAVAILABLE and illuminance != STATE_UNKNOWN:
                    known_state = True
                    if float(illuminance) < float(self.min_illuminance.state):
                        self.illuminance_status = STATE_LOW
                        if self.illuminance_trigger:
                            new_state = STATE_PROBLEM
                    elif float(illuminance) > float(self.max_illuminance.state):
                        self.illuminance_status = STATE_HIGH
                        if self.illuminance_trigger:
                            new_state = STATE_PROBLEM
                    else:
                        self.illuminance_status = STATE_OK

            if self.sensor_humidity is not None:
                humidity = self.sensor_humidity.state
                if humidity is not None and humidity != STATE_UNAVAILABLE and humidity != STATE_UNKNOWN:
                    known_state = True
                    if float(humidity) < float(self.min_humidity.state):
                        self.humidity_status = STATE_LOW
                        if self.humidity_trigger:
                            new_state = STATE_PROBLEM
                    elif float(humidity) > float(self.max_humidity.state):
                        self.humidity_status = STATE_HIGH
                        if self.humidity_trigger:
                            new_state = STATE_PROBLEM
                    else:
                        self.humidity_status = STATE_OK

            if self.sensor_CO2 is not None:
                CO2 = self.sensor_CO2.state
                if CO2 is not None and CO2 != STATE_UNAVAILABLE and CO2 != STATE_UNKNOWN:
                    known_state = True
                    if float(CO2) < float(self.min_CO2.state):
                        self.CO2_status = STATE_LOW
                        if self.CO2_trigger:
                            new_state = STATE_PROBLEM
                    elif float(CO2) > float(self.max_CO2.state):
                        self.CO2_status = STATE_HIGH
                        if self.CO2_trigger:
                            new_state = STATE_PROBLEM
                    else:
                        self.CO2_status = STATE_OK

            if self.dli is not None:
                dli = self.dli.state
                if dli is not None and dli != STATE_UNAVAILABLE and dli != STATE_UNKNOWN:
                    known_state = True
                    if float(dli) < float(self.min_dli.state):
                        self.dli_status = STATE_LOW
                        if self.dli_trigger:
                            new_state = STATE_PROBLEM
                    elif float(dli) > float(self.max_dli.state):
                        self.dli_status = STATE_HIGH
                        if self.dli_trigger:
                            new_state = STATE_PROBLEM
                    else:
                        self.dli_status = STATE_OK

            # Überprüfe Wasser-Verbrauch
            if self.moisture_consumption is not None:
                water_consumption = self.moisture_consumption.state
                if water_consumption is not None and water_consumption != STATE_UNAVAILABLE and water_consumption != STATE_UNKNOWN:
                    known_state = True
                    if float(water_consumption) < float(self.min_water_consumption.state):
                        self.water_consumption_status = STATE_LOW
                        if self.water_consumption_trigger:
                            new_state = STATE_PROBLEM
                    elif float(water_consumption) > float(self.max_water_consumption.state):
                        self.water_consumption_status = STATE_HIGH
                        if self.water_consumption_trigger:
                            new_state = STATE_PROBLEM
                    else:
                        self.water_consumption_status = STATE_OK

            # Überprüfe Dünger-Verbrauch
            if self.fertilizer_consumption is not None:
                fertilizer_consumption = self.fertilizer_consumption.state
                if fertilizer_consumption is not None and fertilizer_consumption != STATE_UNAVAILABLE and fertilizer_consumption != STATE_UNKNOWN:
                    known_state = True
                    if float(fertilizer_consumption) < float(self.min_fertilizer_consumption.state):
                        self.fertilizer_consumption_status = STATE_LOW
                        if self.fertilizer_consumption_trigger:
                            new_state = STATE_PROBLEM
                    elif float(fertilizer_consumption) > float(self.max_fertilizer_consumption.state):
                        self.fertilizer_consumption_status = STATE_HIGH
                        if self.fertilizer_consumption_trigger:
                            new_state = STATE_PROBLEM
                    else:
                        self.fertilizer_consumption_status = STATE_OK

            # Überprüfe Power Consumption
            if self.sensor_power_consumption is not None:
                power_consumption = self.sensor_power_consumption.state
                if power_consumption is not None and power_consumption != STATE_UNAVAILABLE and power_consumption != STATE_UNKNOWN:
                    known_state = True
                    if float(power_consumption) < float(self.min_power_consumption.state):
                        self.power_consumption_status = STATE_LOW
                        if self.power_consumption_trigger:
                            new_state = STATE_PROBLEM
                    elif float(power_consumption) > float(self.max_power_consumption.state):
                        self.power_consumption_status = STATE_HIGH
                        if self.power_consumption_trigger:
                            new_state = STATE_PROBLEM
                    else:
                        self.power_consumption_status = STATE_OK

        if not known_state:
            new_state = STATE_UNKNOWN

        self._attr_state = new_state
        self.update_registry()

    @property
    def data_source(self) -> str | None:
        """Currently unused. For future use"""
        return None

    def update_registry(self) -> None:
        """Update registry with correct data"""
        if self._device_id is None:
            device_registry = dr.async_get(self._hass)
            device = device_registry.async_get_device(
                identifiers={(DOMAIN, self.unique_id)}
            )
            if device:
                self._device_id = device.id

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        self.update_registry()
        # Die Wiederherstellung der Member Plants erfolgt jetzt direkt in der PlantGrowthPhaseSelect Klasse

    @property
    def icon(self) -> str:
        """Return the icon."""
        if self.device_type == DEVICE_TYPE_CYCLE:
            return ICON_DEVICE_CYCLE
        return ICON_DEVICE_PLANT

    def add_member_plant(self, plant_entity_id: str) -> None:
        """Add a plant to the cycle."""
        if plant_entity_id not in self._member_plants:
            self._member_plants.append(plant_entity_id)
            self._update_cycle_attributes()
            self._update_median_sensors()
            
            # Aktualisiere Growth Phase sofort
            if self.growth_phase_select:
                # Aktualisiere das member_plants Attribut direkt in den extra_state_attributes
                if hasattr(self.growth_phase_select, '_attr_extra_state_attributes'):
                    self.growth_phase_select._attr_extra_state_attributes["member_plants"] = self._member_plants.copy()
                
                # Stelle sicher, dass die Änderungen in den Attributen gespeichert werden
                self.growth_phase_select.async_write_ha_state()
                self._hass.async_create_task(
                    self.growth_phase_select._update_cycle_phase()
                )
            
            # Aktualisiere die Flowering Duration
            if self.flowering_duration:
                self._hass.async_create_task(
                    self.flowering_duration._update_cycle_duration()
                )
            
            # Aktualisiere die Pot Size
            if self.pot_size:
                self._hass.async_create_task(
                    self.pot_size._update_cycle_pot_size()
                )
                
            # Aktualisiere die Water Capacity
            if self.water_capacity:
                self._hass.async_create_task(
                    self.water_capacity._update_cycle_water_capacity()
                )
                
            # Aktualisiere den Health-Wert
            if self.health_number:
                self._hass.async_create_task(
                    self.health_number._update_cycle_health()
                )

    def remove_member_plant(self, plant_entity_id: str) -> None:
        """Remove a plant from the cycle."""
        if plant_entity_id in self._member_plants:
            self._member_plants.remove(plant_entity_id)
            self._update_cycle_attributes()
            self._update_median_sensors()
            
            # Aktualisiere Growth Phase sofort
            if self.growth_phase_select:
                # Aktualisiere das member_plants Attribut direkt in den extra_state_attributes
                if hasattr(self.growth_phase_select, '_attr_extra_state_attributes'):
                    self.growth_phase_select._attr_extra_state_attributes["member_plants"] = self._member_plants.copy()
                
                # Stelle sicher, dass die Änderungen in den Attributen gespeichert werden
                self.growth_phase_select.async_write_ha_state()
                self._hass.async_create_task(
                    self.growth_phase_select._update_cycle_phase()
                )
            
            # Aktualisiere die Flowering Duration
            if self.flowering_duration:
                self._hass.async_create_task(
                    self.flowering_duration._update_cycle_duration()
                )
            
            # Aktualisiere die Pot Size
            if self.pot_size:
                self._hass.async_create_task(
                    self.pot_size._update_cycle_pot_size()
                )
                
            # Aktualisiere die Water Capacity
            if self.water_capacity:
                self._hass.async_create_task(
                    self.water_capacity._update_cycle_water_capacity()
                )
                
            # Aktualisiere den Health-Wert
            if self.health_number:
                self._hass.async_create_task(
                    self.health_number._update_cycle_health()
                )

    def _update_median_sensors(self) -> None:
        """Aktualisiere die Median-Werte für alle Sensoren."""
        if not self._member_plants:
            return

        # Dictionary für die Sensor-Werte
        sensor_values = {
            'temperature': [], 
            'moisture': [],
            'conductivity': [], 
            'illuminance': [],
            'humidity': [],
            'CO2': [],
            'ppfd': [],
            'dli': [],
            'total_integral': [],
            'moisture_consumption': [],
            'total_water_consumption': [],  # Füge Total Water hinzu
            'fertilizer_consumption': [],
            'total_fertilizer_consumption': [],  # Füge Total Fertilizer hinzu
            'power_consumption': [],
            'total_power_consumption': []  # Füge Total Power hinzu
        }

        for plant_id in self._member_plants:
            plant = None
            # Suche die Plant Entity
            for entry_id in self._hass.data[DOMAIN]:
                if ATTR_PLANT in self._hass.data[DOMAIN][entry_id]:
                    if self._hass.data[DOMAIN][entry_id][ATTR_PLANT].entity_id == plant_id:
                        plant = self._hass.data[DOMAIN][entry_id][ATTR_PLANT]
                        break

            if not plant:
                _LOGGER.warning("Could not find plant %s", plant_id)
                continue

            # Sammle die Sensor-Werte für alle Sensor-Typen
            sensors_to_check = {
                'temperature': plant.sensor_temperature,
                'moisture': plant.sensor_moisture,
                'conductivity': plant.sensor_conductivity,
                'illuminance': plant.sensor_illuminance,
                'humidity': plant.sensor_humidity,
                'CO2': plant.sensor_CO2,
                'ppfd': plant.ppfd,
                'dli': plant.dli,
                'total_integral': plant.total_integral,
                'moisture_consumption': plant.moisture_consumption,
                'total_water_consumption': plant.total_water_consumption,  # Füge Total Water hinzu
                'fertilizer_consumption': plant.fertilizer_consumption,
                'total_fertilizer_consumption': plant.total_fertilizer_consumption,  # Füge Total Fertilizer hinzu
                'power_consumption': plant.sensor_power_consumption,
                'total_power_consumption': plant.total_power_consumption  # Füge Total Power hinzu
            }

            for sensor_type, sensor in sensors_to_check.items():
                if sensor and hasattr(sensor, 'state') and sensor.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE, None):
                    try:
                        # Für DLI/PPFD/total_integral/consumption speichern wir auch den Sensor selbst
                        if sensor_type in ['ppfd', 'dli', 'total_integral', 
                                         'moisture_consumption', 'total_water_consumption',
                                         'fertilizer_consumption', 'total_fertilizer_consumption',
                                         'power_consumption', 'total_power_consumption']:
                            sensor_values[sensor_type].append((float(sensor.state), sensor))
                        else:
                            sensor_values[sensor_type].append(float(sensor.state))
                    except (TypeError, ValueError) as ex:
                        _LOGGER.debug("Could not convert %s value %s: %s",
                                    sensor_type, sensor.state, ex)
                        continue

        # Berechne Aggregate
        for sensor_type, values in sensor_values.items():
            if values:
                aggregation_method = self._plant_info.get('aggregations', {}).get(
                    sensor_type, DEFAULT_AGGREGATIONS.get(sensor_type, AGGREGATION_MEDIAN)
                )

                # Spezielle Behandlung für Sensoren mit Original-Berechnung
                if sensor_type in ['ppfd', 'dli', 'total_integral', 
                                 'moisture_consumption', 'total_water_consumption',
                                 'fertilizer_consumption', 'total_fertilizer_consumption',
                                 'power_consumption', 'total_power_consumption'] and aggregation_method == AGGREGATION_ORIGINAL:
                    # Bei Original-Berechnung nehmen wir den ersten gültigen Sensor
                    if values:
                        self._median_sensors[sensor_type] = values[0] if isinstance(values[0], (int, float)) else values[0][0]

                # Für alle anderen Fälle extrahieren wir nur die Werte
                if sensor_type in ['ppfd', 'dli', 'total_integral', 
                                 'moisture_consumption', 'total_water_consumption',
                                 'fertilizer_consumption', 'total_fertilizer_consumption',
                                 'power_consumption', 'total_power_consumption']:
                    values = [v[0] for v in values]  # Extrahiere nur die Werte, nicht die Sensoren

                if aggregation_method == AGGREGATION_MEAN:
                    value = sum(values) / len(values)
                elif aggregation_method == AGGREGATION_MIN:
                    value = min(values)
                elif aggregation_method == AGGREGATION_MAX:
                    value = max(values)
                else:  # AGGREGATION_MEDIAN
                    sorted_values = sorted(values)
                    n = len(sorted_values)
                    if n % 2 == 0:
                        value = (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
                    else:
                        value = sorted_values[n//2]

                # Runde die Werte entsprechend ihres Typs
                if sensor_type == "total_integral":
                    self._median_sensors[sensor_type] = round(value, 6)  # 6 Nachkommastellen wie bei Plant
                elif sensor_type in ["ppfd", "dli"]:
                    self._median_sensors[sensor_type] = round(value, 3)  # 3 Nachkommastellen
                elif sensor_type in ["temperature", "moisture", "humidity", "moisture_consumption", "CO2"]:
                    self._median_sensors[sensor_type] = round(value, 1)  # 1 Nachkommastelle
                else:  # conductivity, illuminance, fertilizer_consumption
                    self._median_sensors[sensor_type] = round(value)  # Keine Nachkommastellen

    def _update_cycle_attributes(self) -> None:
        """Update cycle attributes based on member plants."""
        if self.device_type != DEVICE_TYPE_CYCLE:
            return

        # Initialisiere leere Listen für alle Attribute
        attributes = {
            "member_count": [],
            "strain": [],
            "breeder": [],
            "type": [],
            "feminized": [],
            "timestamp": [],
            "pid": [],
            "effects": [],
            "smell": [],
            "taste": [],
            "phenotype": [],
            "hunger": [],
            "growth_stretch": [],
            "flower_stretch": [],
            "mold_resistance": [],
            "difficulty": [],
            "yield": [],
            "notes": [],
            "website": [],
            "infotext1": [],
            "infotext2": [],
            "lineage": [],
        }

        # Sammle die Attribute aller Member Plants
        member_count = len(self._member_plants)
        for plant_id in self._member_plants:
            found = False
            for entry_id in self._hass.data[DOMAIN]:
                if ATTR_PLANT in self._hass.data[DOMAIN][entry_id]:
                    plant = self._hass.data[DOMAIN][entry_id][ATTR_PLANT]
                    if plant.entity_id == plant_id:
                        found = True
                        # Füge die Werte zu den entsprechenden Listen hinzu
                        attributes["member_count"].append(str(member_count))
                        for attr in [key for key in attributes.keys() if key != "member_count"]:
                            value = plant._plant_info.get(attr, "")
                            attributes[attr].append(str(value) if value else "")
                        break
            
            # Wenn die Plant nicht gefunden wurde, füge leere Strings hinzu
            if not found:
                attributes["member_count"].append(str(member_count))
                for attr in [key for key in attributes.keys() if key != "member_count"]:
                    attributes[attr].append("")

        # Aktualisiere die Plant Info
        # Setze member_count direkt als Integer
        self._plant_info["member_count"] = member_count
        
        # Aktualisiere die restlichen Attribute
        for attr, values in [(key, val) for key, val in attributes.items() if key != "member_count"]:
            # Nur wenn mindestens ein nicht-leerer Wert existiert
            if any(value.strip() for value in values):
                self._plant_info[attr] = " | ".join(values)
            else:
                self._plant_info[attr] = ""

        self.async_write_ha_state()

    def add_cycle_select(self, cycle_select: Entity) -> None:
        """Füge den Cycle Select Helper hinzu."""
        self.cycle_select = cycle_select

    def add_pot_size(self, pot_size) -> None:
        """Fügt den Pot Size Helper hinzu."""
        self.pot_size = pot_size

    def add_water_capacity(self, water_capacity) -> None:
        """Add water capacity entity."""
        self.water_capacity = water_capacity

    def add_treatment_select(self, treatment_select: Entity) -> None:
        """Add the treatment select entity."""
        self.treatment_select = treatment_select

    def add_health_number(self, health_number: Entity) -> None:
        """Add the health number entity."""
        self.health_number = health_number

    def add_journal(self, journal: Entity) -> None:
        """Add the journal text entity."""
        self.journal = journal
        
    def add_location_history(self, location_history: Entity) -> None:
        """Add the location history text entity."""
        self.location_history = location_history

    @property
    def name(self) -> str:
        """Return the name with emojis for the device."""
        name = self._plant_info[ATTR_NAME]
        # Füge das Emoji hinzu, falls eines gesetzt ist
        plant_emoji = self._plant_info.get('plant_emoji')
        if plant_emoji and plant_emoji not in name:
            name = f"{name} {plant_emoji}"
        return name

    @property
    def _name(self) -> str:
        """Return the clean name without emojis for entities."""
        name = self._plant_info[ATTR_NAME]
        # Entferne das Emoji falls vorhanden
        plant_emoji = self._plant_info.get('plant_emoji')
        if plant_emoji and plant_emoji in name:
            name = name.replace(f" {plant_emoji}", "")
        return name

    @property
    def has_entity_name(self) -> bool:
        """Return False to use raw entity names without device prefix."""
        return False

    def add_power_consumption_sensors(self, current, total):
        """Add power consumption sensors."""
        self.sensor_power_consumption = current
        self.total_power_consumption = total

    @property
    def kwh_price(self) -> float:
        """Return the current kWh price."""
        return self._kwh_price

    def update_kwh_price(self, new_price: float) -> None:
        """Update the kWh price."""
        self._kwh_price = new_price
        # Aktualisiere den Energiekosten-Sensor wenn vorhanden
        if hasattr(self, 'energy_cost') and self.energy_cost:
            self.energy_cost.async_schedule_update_ha_state(True)


async def async_remove_config_entry_device(
    hass: HomeAssistant,
    config_entry: ConfigEntry, 
    device_entry: dr.DeviceEntry,) -> bool:
    """Delete device entry from device registry."""
    _LOGGER.debug(
        "async_remove_config_entry_device called for device %s (config: %s)", 
        device_entry.id,
        config_entry.data
    )
    
    # Prüfe ob dies der Konfigurationsknoten ist
    if config_entry.data.get("is_config", False):
        # Prüfe ob noch andere Plant/Cycle Einträge existieren
        for entry in hass.config_entries.async_entries(DOMAIN):
            if not entry.data.get("is_config", False):  # Wenn es ein Plant/Cycle ist
                _LOGGER.warning(
                    "Cannot remove configuration node while plants/cycles exist. "
                    "Please remove all plants and cycles first."
                )
                return False
    
    device_registry = dr.async_get(hass)
    
    # Wenn das Device eine Plant ist und einem Cycle zugeordnet ist
    if device_entry.via_device_id:
        _LOGGER.debug("Removing plant device with via_device_id %s", device_entry.via_device_id)
        # Finde die Plant Entity
        entity_registry = er.async_get(hass)
        plant_entity_id = None
        for entity_entry in entity_registry.entities.values():
            if entity_entry.device_id == device_entry.id and entity_entry.domain == DOMAIN:
                plant_entity_id = entity_entry.entity_id
                break
                
        if plant_entity_id:
            # Suche das Cycle Device
            for device in device_registry.devices.values():
                if device.id == device_entry.via_device_id:
                    cycle_device = device
                    # Finde den zugehörigen Cycle
                    for entry_id in hass.data[DOMAIN]:
                        if ATTR_PLANT in hass.data[DOMAIN][entry_id]:
                            cycle = hass.data[DOMAIN][entry_id][ATTR_PLANT]
                            if (cycle.device_type == DEVICE_TYPE_CYCLE and 
                                cycle.unique_id == next(iter(cycle_device.identifiers))[1]):
                                # Entferne die Plant aus dem Cycle
                                cycle.remove_member_plant(plant_entity_id)
                                # Aktualisiere Flowering Duration
                                if cycle.flowering_duration:
                                    await cycle.flowering_duration._update_cycle_duration()
                                break
                    break
    
    # Entferne das Device
    device_registry.async_remove_device(device_entry.id)
    
    # Entferne dann die Config Entry
    await hass.config_entries.async_remove(config_entry.entry_id)
    
    return True


