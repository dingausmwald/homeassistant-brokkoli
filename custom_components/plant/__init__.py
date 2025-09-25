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
    FLOW_SENSOR_PH,
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
    DEVICE_TYPE_TENT,
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
from .sensor_configuration import get_decimals_for
from .tent import Tent
from .repairs import async_create_sensor_unavailability_issue, async_create_invalid_configuration_issue, async_create_missing_sensor_issue
from .device_removal import async_remove_stale_devices, async_check_and_remove_stale_device, async_cleanup_orphaned_entities

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

    # Normale Plant/Cycle/Tent Initialisierung fortsetzen
    plant_data = entry.data[FLOW_PLANT_INFO]
    
    hass.data.setdefault(DOMAIN, {})
    if FLOW_PLANT_INFO not in entry.data:
        return True

    hass.data[DOMAIN].setdefault(entry.entry_id, {})
    _LOGGER.debug("Setting up config entry %s: %s", entry.entry_id, entry)

    # Prüfe ob bereits eine ID existiert
    device_type = entry.data[FLOW_PLANT_INFO].get(ATTR_DEVICE_TYPE, DEVICE_TYPE_PLANT)
    
    # Für Tents verwenden wir "tent_id", für andere "plant_id"
    id_key = "tent_id" if device_type == DEVICE_TYPE_TENT else "plant_id"
    
    if id_key not in entry.data[FLOW_PLANT_INFO]:
        # Generiere neue ID nur wenn keine existiert
        new_id = await _get_next_id(hass, device_type)
        # Speichere ID in der Config Entry
        data = dict(entry.data)
        data[FLOW_PLANT_INFO][id_key] = new_id
        hass.config_entries.async_update_entry(entry, data=data)
    
    # Erstelle PlantDevice oder Tent basierend auf dem Gerätetyp
    if device_type == DEVICE_TYPE_TENT:
        # Für Tents erstellen wir ein Tent-Objekt
        from .tent import Tent
        plant = Tent(hass, entry)
        # Setze die tent_id direkt
        plant._tent_id = entry.data[FLOW_PLANT_INFO].get(id_key)
    else:
        # Für Plants und Cycles verwenden wir PlantDevice
        plant = PlantDevice(hass, entry)
        plant._plant_id = entry.data[FLOW_PLANT_INFO].get(id_key)

    # Korrekte Device-Registrierung
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        **plant.device_info
    )

    # Set the device_id on the plant object
    if hasattr(plant, '_device_id'):
        plant._device_id = device.id

    hass.data[DOMAIN][entry.entry_id][ATTR_PLANT] = plant

    # Für Tents brauchen wir keine Sensor-Plattformen
    # Tents verwenden die gleichen Plattformen wie Plants/Cycles, aber mit unterschiedlichen Entities
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    plant_entities = [
        plant,
    ]

    # Add all the entities to Hass
    component = EntityComponent(_LOGGER, plant.device_type, hass)
    await component.async_add_entities(plant_entities)

    # Add the rest of the entities to device registry together with plant
    device_id = plant.device_id
    if device_id is None:
        # Fallback to get device_id from the device registry
        device_registry = dr.async_get(hass)
        device = device_registry.async_get_device(
            identifiers={(DOMAIN, plant.unique_id)}
        )
        if device:
            device_id = device.id
    await _plant_add_to_device_registry(hass, plant_entities, device_id)
    
    # Für Tents nur die Haupt-Entity registrieren
    if device_type != DEVICE_TYPE_TENT:
        await _plant_add_to_device_registry(hass, plant.integral_entities, device_id)
        await _plant_add_to_device_registry(hass, plant.threshold_entities, device_id)
        await _plant_add_to_device_registry(hass, plant.meter_entities, device_id)

    # Set up utility sensor (nur für Plants und Cycles)
    if device_type != DEVICE_TYPE_TENT:
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
    # Nur für Plants und Cycles
    if device_type != DEVICE_TYPE_TENT and USE_DUMMY_SENSORS is True:
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
    # Nur für Plants und Cycles
    if device_type != DEVICE_TYPE_TENT and entry.data[FLOW_PLANT_INFO].get(ATTR_IS_NEW_PLANT, False):
        data = dict(entry.data)
        data[FLOW_PLANT_INFO][ATTR_IS_NEW_PLANT] = False
        hass.config_entries.async_update_entry(entry, data=data)

    # Wenn ein neuer Cycle erstellt wurde, aktualisiere alle Plant Cycle Selects
    # Nur für Cycles
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

    # Prüfe den Gerätetyp
    device_type = entry.data.get(FLOW_PLANT_INFO, {}).get(ATTR_DEVICE_TYPE, DEVICE_TYPE_PLANT)
    
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Entferne zuerst die Daten
        hass.data[DOMAIN].pop(entry.entry_id)
        
        # Entferne utility data nur für Plants und Cycles
        if device_type != DEVICE_TYPE_TENT and DATA_UTILITY in hass.data:
            hass.data[DATA_UTILITY].pop(entry.entry_id, None)
        
        # Wenn ein Cycle entfernt wird, aktualisiere alle Plant Cycle Selects
        if device_type == DEVICE_TYPE_CYCLE:
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
        self._hass = hass
        self._config = config
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
        
        # pH Thresholds
        self.max_ph = None
        self.min_ph = None

        self.sensor_moisture = None
        self.sensor_temperature = None
        self.sensor_conductivity = None
        self.sensor_illuminance = None
        self.sensor_humidity = None
        self.sensor_CO2 = None
        self.sensor_power_consumption = None
        self.total_power_consumption = None
        self.sensor_ph = None  # Add pH sensor attribute
        self.sensor_fertilizer_consumption = None  # Add fertilizer consumption sensor attribute

        self.dli = None
        self.micro_dli = None
        self.ppfd = None
        self.total_integral = None
        self.moisture_consumption = None
        self.total_water_consumption = None  # Füge Total Water Consumption hinzu
        self.fertilizer_consumption = None
        self.total_fertilizer_consumption = None  # Füge Total Fertilizer Consumption hinzu
        self.power_consumption = None
        self.energy_cost = None

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
        self.ph_status = None  # Add pH status attribute

        # Tent assignment
        self._assigned_tent = None
        self._tent_id = None

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

        # Neue Property für Tent Select
        self.tent_select = None

        # Neue Property für Pot Size
        self.pot_size = None
        
        # Neue Property für Water Capacity
        self.water_capacity = None

        # Initialisiere die Bilderliste
        self._images = self._plant_info.get("images", [])

        # Aggregationsmethode für health
        self.health_aggregation = (
            self._config.options.get("health_aggregation") or
            self._plant_info.get("health_aggregation", "mean")
        )

        # Cache for decimals overrides loaded from central config entry
        self._decimals_overrides = None
        for entry in hass.config_entries.async_entries(DOMAIN):
            if entry.data.get("is_config", False):
                info = entry.data.get(FLOW_PLANT_INFO, {})
                self._decimals_overrides = {
                    "temperature": info.get("decimals_temperature"),
                    "moisture": info.get("decimals_moisture"),
                    "conductivity": info.get("decimals_conductivity"),
                    "illuminance": info.get("decimals_illuminance"),
                    "humidity": info.get("decimals_humidity"),
                    "CO2": info.get("decimals_CO2"),
                    "ph": info.get("decimals_ph"),
                    "ppfd": info.get("decimals_ppfd"),
                    "dli": info.get("decimals_dli"),
                    "total_integral": info.get("decimals_total_integral"),
                    "moisture_consumption": info.get("decimals_moisture_consumption"),
                    "total_water_consumption": info.get("decimals_total_water_consumption"),
                    "fertilizer_consumption": info.get("decimals_fertilizer_consumption"),
                    "total_fertilizer_consumption": info.get("decimals_total_fertilizer_consumption"),
                    "power_consumption": info.get("decimals_power_consumption"),
                    "total_power_consumption": info.get("decimals_total_power_consumption"),
                    "energy_cost": info.get("decimals_energy_cost"),
                }
                break

        # Initialize state
        self._attr_state = STATE_UNKNOWN
        
        # Initialize update scheduler
        self._update_unsub = None
        self._schedule_regular_updates()

    def decimals_for(self, sensor_type: str) -> int:
        """Return configured decimals for a sensor type."""
        return get_decimals_for(sensor_type, self._decimals_overrides)

    @property
    def state(self):
        """Return the state of the plant."""
        if self._attr_state is None:
            return STATE_UNKNOWN
        return self._attr_state

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
        elif device_type == DEVICE_TYPE_CYCLE:
            info.update({
                "manufacturer": "Home Assistant",
                "model": "Cycle",
                "model_id": self._plant_info.get(ATTR_TYPE, ""),
            })
        else:  # DEVICE_TYPE_TENT
            info.update({
                "manufacturer": "Home Assistant",
                "model": "Tent",
                "model_id": "Tent",
            })
        
        # Optional website hinzufügen wenn vorhanden
        if self.website:
            info["configuration_url"] = self.website
        
        return info

    @property
    def name(self) -> str:
        """Return the name of the plant."""
        return self._plant_info.get(ATTR_NAME, "Unknown Plant")

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
    def ph_trigger(self) -> bool:
        """Whether we will generate alarms based on pH."""
        return self._config.options.get(FLOW_PH_TRIGGER, True)

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
    def kwh_price(self) -> float:
        """Return the kWh price."""
        return self._kwh_price

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

        # Add sensor names for debugging
        if self.sensor_temperature and self.sensor_temperature._external_sensor:
            attrs["temperature_sensor"] = self.sensor_temperature._external_sensor
        if self.sensor_moisture and self.sensor_moisture._external_sensor:
            attrs["moisture_sensor"] = self.sensor_moisture._external_sensor
        if self.sensor_conductivity and self.sensor_conductivity._external_sensor:
            attrs["conductivity_sensor"] = self.sensor_conductivity._external_sensor
        if self.sensor_illuminance and self.sensor_illuminance._external_sensor:
            attrs["illuminance_sensor"] = self.sensor_illuminance._external_sensor
        if self.sensor_humidity and self.sensor_humidity._external_sensor:
            attrs["humidity_sensor"] = self.sensor_humidity._external_sensor
        if self.sensor_CO2 and self.sensor_CO2._external_sensor:
            attrs["co2_sensor"] = self.sensor_CO2._external_sensor
        if self.sensor_power_consumption and self.sensor_power_consumption._external_sensor:
            attrs["power_consumption_sensor"] = self.sensor_power_consumption._external_sensor
        if self.sensor_ph and self.sensor_ph._external_sensor:
            attrs["ph_sensor"] = self.sensor_ph._external_sensor

        # Füge member_count für Cycles hinzu
        if self.device_type == DEVICE_TYPE_CYCLE:
            attrs = {"member_count": len(self._member_plants)} | attrs

        # Füge Plant-spezifische Attribute nur für Plants hinzu
        if self.device_type == DEVICE_TYPE_PLANT:
            attrs.update({
                "infotext1": self._plant_info.get("infotext1", ""),
                "infotext2": self._plant_info.get("infotext2", ""),
                "lineage": self._plant_info.get("lineage", ""),
                "tent_id": self._tent_id,
                "tent_name": self.get_tent_name(),
            })

        return attrs

    @property
    def websocket_info(self) -> dict:
        """Wesocket response"""
        # Remove the plant_complete check since it's never set to True
        # if not self.plant_complete:
        #     # We are not fully set up, so we just return an empty dict for now
        #     return {}

        # Hole den Download-Pfad aus der Konfiguration und konvertiere ihn
        config_entry = None
        for entry in self._hass.config_entries.async_entries(DOMAIN):
            if entry.data.get("is_config", False):
                config_entry = entry
                break

        download_path = config_entry.data[FLOW_PLANT_INFO].get(FLOW_DOWNLOAD_PATH, DEFAULT_IMAGE_PATH) if config_entry else DEFAULT_IMAGE_PATH
        # Konvertiere /config/www/ zu /local/
        web_path = download_path.replace("/config/www/", "/local/")

        # Force an update of all sensors to ensure we have current values
        # This is especially important after assigning a tent to a plant
        if hasattr(self, 'sensor_temperature') and self.sensor_temperature:
            self.sensor_temperature.async_schedule_update_ha_state(True)
        if hasattr(self, 'sensor_moisture') and self.sensor_moisture:
            self.sensor_moisture.async_schedule_update_ha_state(True)
        if hasattr(self, 'sensor_conductivity') and self.sensor_conductivity:
            self.sensor_conductivity.async_schedule_update_ha_state(True)
        if hasattr(self, 'sensor_illuminance') and self.sensor_illuminance:
            self.sensor_illuminance.async_schedule_update_ha_state(True)
        if hasattr(self, 'sensor_humidity') and self.sensor_humidity:
            self.sensor_humidity.async_schedule_update_ha_state(True)
        if hasattr(self, 'sensor_CO2') and self.sensor_CO2:
            self.sensor_CO2.async_schedule_update_ha_state(True)
        if hasattr(self, 'sensor_power_consumption') and self.sensor_power_consumption:
            self.sensor_power_consumption.async_schedule_update_ha_state(True)
        if hasattr(self, 'sensor_ph') and self.sensor_ph:
            self.sensor_ph.async_schedule_update_ha_state(True)
        
        # Update the plant state
        self.update()

        # Basis-Response mit Hauptsensoren
        response = {
            "path": web_path,  # Der konvertierte Pfad
            "device_type": self.device_type,  # Füge device_type hinzu (plant oder cycle)
            "entity_id": self.entity_id,  # Füge die Haupt-Entity-ID hinzu
            "name": self.name,  # Füge den Namen hinzu
            "icon": self.icon,  # Füge das Icon hinzu
            "state": self.state,  # Füge den Zustand hinzu
            
            # Ursprüngliche Sensor-Info beibehalten - Verwende native_value anstelle von state
            ATTR_TEMPERATURE: {
                ATTR_MAX: self.max_temperature.native_value if self.max_temperature else None,
                ATTR_MIN: self.min_temperature.native_value if self.min_temperature else None,
                ATTR_CURRENT: (
                    self._apply_rounding("temperature", self.sensor_temperature.native_value)
                    if self.sensor_temperature and self.sensor_temperature.native_value not in (STATE_UNKNOWN, STATE_UNAVAILABLE, None)
                    and self._is_valid_number(self.sensor_temperature.native_value)
                    else None
                ),
                ATTR_ICON: self.sensor_temperature.icon if self.sensor_temperature else None,
                ATTR_UNIT_OF_MEASUREMENT: self.sensor_temperature.unit_of_measurement if self.sensor_temperature else None,
                ATTR_SENSOR: self.sensor_temperature.entity_id if self.sensor_temperature else None,
            },
            ATTR_ILLUMINANCE: {
                ATTR_MAX: self.max_illuminance.native_value if self.max_illuminance else None,
                ATTR_MIN: self.min_illuminance.native_value if self.min_illuminance else None,
                ATTR_CURRENT: (
                    self._apply_rounding("illuminance", self.sensor_illuminance.native_value)
                    if self.sensor_illuminance and self.sensor_illuminance.native_value not in (STATE_UNKNOWN, STATE_UNAVAILABLE, None)
                    and self._is_valid_number(self.sensor_illuminance.native_value)
                    else None
                ),
                ATTR_ICON: self.sensor_illuminance.icon if self.sensor_illuminance else None,
                ATTR_UNIT_OF_MEASUREMENT: self.sensor_illuminance.unit_of_measurement if self.sensor_illuminance else None,
                ATTR_SENSOR: self.sensor_illuminance.entity_id if self.sensor_illuminance else None,
            },
            ATTR_MOISTURE: {
                ATTR_MAX: self.max_moisture.native_value if self.max_moisture else None,
                ATTR_MIN: self.min_moisture.native_value if self.min_moisture else None,
                ATTR_CURRENT: (
                    self._apply_rounding("moisture", self.sensor_moisture.native_value)
                    if self.sensor_moisture and self.sensor_moisture.native_value not in (STATE_UNKNOWN, STATE_UNAVAILABLE, None)
                    and self._is_valid_number(self.sensor_moisture.native_value)
                    else None
                ),
                ATTR_ICON: self.sensor_moisture.icon if self.sensor_moisture else None,
                ATTR_UNIT_OF_MEASUREMENT: self.sensor_moisture.unit_of_measurement if self.sensor_moisture else None,
                ATTR_SENSOR: self.sensor_moisture.entity_id if self.sensor_moisture else None,
            },
            ATTR_CONDUCTIVITY: {
                ATTR_MAX: self.max_conductivity.native_value if self.max_conductivity else None,
                ATTR_MIN: self.min_conductivity.native_value if self.min_conductivity else None,
                ATTR_CURRENT: (
                    self._apply_rounding("conductivity", self.sensor_conductivity.native_value)
                    if self.sensor_conductivity and self.sensor_conductivity.native_value not in (STATE_UNKNOWN, STATE_UNAVAILABLE, None)
                    and self._is_valid_number(self.sensor_conductivity.native_value)
                    else None
                ),
                ATTR_ICON: self.sensor_conductivity.icon if self.sensor_conductivity else None,
                ATTR_UNIT_OF_MEASUREMENT: self.sensor_conductivity.unit_of_measurement if self.sensor_conductivity else None,
                ATTR_SENSOR: self.sensor_conductivity.entity_id if self.sensor_conductivity else None,
            },
            ATTR_HUMIDITY: {
                ATTR_MAX: self.max_humidity.native_value if self.max_humidity else None,
                ATTR_MIN: self.min_humidity.native_value if self.min_humidity else None,
                ATTR_CURRENT: (
                    self._apply_rounding("humidity", self.sensor_humidity.native_value)
                    if self.sensor_humidity and self.sensor_humidity.native_value not in (STATE_UNKNOWN, STATE_UNAVAILABLE, None)
                    and self._is_valid_number(self.sensor_humidity.native_value)
                    else None
                ),
                ATTR_ICON: self.sensor_humidity.icon if self.sensor_humidity else None,
                ATTR_UNIT_OF_MEASUREMENT: self.sensor_humidity.unit_of_measurement if self.sensor_humidity else None,
                ATTR_SENSOR: self.sensor_humidity.entity_id if self.sensor_humidity else None,
            },
            ATTR_CO2: {
                ATTR_MAX: self.max_CO2.native_value if self.max_CO2 else None,
                ATTR_MIN: self.min_CO2.native_value if self.min_CO2 else None,
                ATTR_CURRENT: (
                    self._apply_rounding("CO2", self.sensor_CO2.native_value)
                    if self.sensor_CO2 and self.sensor_CO2.native_value not in (STATE_UNKNOWN, STATE_UNAVAILABLE, None)
                    and self._is_valid_number(self.sensor_CO2.native_value)
                    else None
                ),
                ATTR_ICON: self.sensor_CO2.icon if self.sensor_CO2 else None,
                ATTR_UNIT_OF_MEASUREMENT: self.sensor_CO2.unit_of_measurement if self.sensor_CO2 else None,
                ATTR_SENSOR: self.sensor_CO2.entity_id if self.sensor_CO2 else None,
            },
            ATTR_DLI: {
                ATTR_MAX: self.max_dli.native_value if self.max_dli else None,
                ATTR_MIN: self.min_dli.native_value if self.min_dli else None,
                ATTR_CURRENT: (
                    self._apply_rounding("dli", self.dli.native_value)
                    if self.dli and self.dli.native_value not in (STATE_UNKNOWN, STATE_UNAVAILABLE, None)
                    and self._is_valid_number(self.dli.native_value)
                    else None
                ),
                ATTR_ICON: self.dli.icon if self.dli else None,
                ATTR_UNIT_OF_MEASUREMENT: self.dli.unit_of_measurement if self.dli else None,
                ATTR_SENSOR: self.dli.entity_id if self.dli else None,
            },
            ATTR_WATER_CONSUMPTION: {
                ATTR_MAX: self.max_water_consumption.native_value if self.max_water_consumption else None,
                ATTR_MIN: self.min_water_consumption.native_value if self.min_water_consumption else None,
                ATTR_CURRENT: (
                    self._apply_rounding("moisture_consumption", self.moisture_consumption.native_value)
                    if self.moisture_consumption and self.moisture_consumption.native_value not in (STATE_UNKNOWN, STATE_UNAVAILABLE, None)
                    and self._is_valid_number(self.moisture_consumption.native_value)
                    else None
                ),
                ATTR_ICON: self.moisture_consumption.icon if self.moisture_consumption else None,
                ATTR_UNIT_OF_MEASUREMENT: self.moisture_consumption.unit_of_measurement if self.moisture_consumption else None,
                ATTR_SENSOR: self.moisture_consumption.entity_id if self.moisture_consumption else None,
            },
            ATTR_FERTILIZER_CONSUMPTION: {
                ATTR_MAX: self.max_fertilizer_consumption.native_value if self.max_fertilizer_consumption else None,
                ATTR_MIN: self.min_fertilizer_consumption.native_value if self.min_fertilizer_consumption else None,
                ATTR_CURRENT: (
                    self._apply_rounding("fertilizer_consumption", self.fertilizer_consumption.native_value)
                    if self.fertilizer_consumption and self.fertilizer_consumption.native_value not in (STATE_UNKNOWN, STATE_UNAVAILABLE, None)
                    and self._is_valid_number(self.fertilizer_consumption.native_value)
                    else None
                ),
                ATTR_ICON: self.fertilizer_consumption.icon if self.fertilizer_consumption else None,
                ATTR_UNIT_OF_MEASUREMENT: self.fertilizer_consumption.unit_of_measurement if self.fertilizer_consumption else None,
                ATTR_SENSOR: self.fertilizer_consumption.entity_id if self.fertilizer_consumption else None,
            },
            ATTR_POWER_CONSUMPTION: {
                ATTR_MAX: self.max_power_consumption.native_value if self.max_power_consumption else None,
                ATTR_MIN: self.min_power_consumption.native_value if self.min_power_consumption else None,
                ATTR_CURRENT: (
                    self._apply_rounding("power_consumption", self.sensor_power_consumption.native_value)
                    if self.sensor_power_consumption and self.sensor_power_consumption.native_value not in (STATE_UNKNOWN, STATE_UNAVAILABLE, None)
                    and self._is_valid_number(self.sensor_power_consumption.native_value)
                    else None
                ),
                ATTR_ICON: self.sensor_power_consumption.icon if self.sensor_power_consumption else None,
                ATTR_UNIT_OF_MEASUREMENT: self.sensor_power_consumption.unit_of_measurement if self.sensor_power_consumption else None,
                ATTR_SENSOR: self.sensor_power_consumption.entity_id if self.sensor_power_consumption else None,
            },
            ATTR_PH: {
                ATTR_MAX: self.max_ph.native_value if self.max_ph else None,
                ATTR_MIN: self.min_ph.native_value if self.min_ph else None,
                ATTR_CURRENT: (
                    self._apply_rounding("ph", self.sensor_ph.native_value)
                    if self.sensor_ph and self.sensor_ph.native_value not in (STATE_UNKNOWN, STATE_UNAVAILABLE, None)
                    and self._is_valid_number(self.sensor_ph.native_value)
                    else None
                ),
                ATTR_ICON: self.sensor_ph.icon if self.sensor_ph else None,
                ATTR_UNIT_OF_MEASUREMENT: self.sensor_ph.unit_of_measurement if self.sensor_ph else None,
                ATTR_SENSOR: self.sensor_ph.entity_id if self.sensor_ph else None,
            },
            
            # Neue Struktur: Separater Bereich für Diagnosesensoren
            "diagnostic_sensors": {},
            
            # Helper-Entities bleiben in eigener Kategorie
            "helpers": {}
        }

        # Diagnosesensoren hinzufügen
        diagnostics = response["diagnostic_sensors"]
        
        # Füge PPFD hinzu
        if self.ppfd:
            current_value = self.ppfd.native_value
            if current_value not in (STATE_UNAVAILABLE, STATE_UNKNOWN, None) and self._is_valid_number(current_value):
                try:
                    current_value = self._apply_rounding("ppfd", float(current_value))
                except (ValueError, TypeError):
                    current_value = None
            else:
                current_value = None
                
            diagnostics["ppfd"] = {
                "entity_id": self.ppfd.entity_id,
                "current": current_value,
                "icon": self.ppfd.icon,
                "unit_of_measurement": self.ppfd.native_unit_of_measurement,
            }
        
        if hasattr(self, 'energy_cost') and self.energy_cost:
            current_value = self.energy_cost.native_value
            if current_value not in (STATE_UNAVAILABLE, STATE_UNKNOWN, None) and self._is_valid_number(current_value):
                try:
                    current_value = self._apply_rounding("energy_cost", float(current_value))
                except (ValueError, TypeError):
                    current_value = None
            else:
                current_value = None
                
            diagnostics["energy_cost"] = {
                "entity_id": self.energy_cost.entity_id,
                "current": current_value,
                "icon": self.energy_cost.icon,
                "unit_of_measurement": self.energy_cost.native_unit_of_measurement,
            }
        
        if self.total_power_consumption:
            current_value = self.total_power_consumption.native_value
            if current_value not in (STATE_UNAVAILABLE, STATE_UNKNOWN, None) and self._is_valid_number(current_value):
                try:
                    current_value = self._apply_rounding("total_power_consumption", float(current_value))
                except (ValueError, TypeError):
                    current_value = None
            else:
                current_value = None
                
            diagnostics["total_power_consumption"] = {
                "entity_id": self.total_power_consumption.entity_id,
                "current": current_value,
                "icon": self.total_power_consumption.icon,
                "unit_of_measurement": self.total_power_consumption.native_unit_of_measurement,
            }
        
        if self.total_integral:
            # Der Wert kommt als decimal.Decimal vom Sensor
            current_value = self.total_integral.native_value
            
            # Konvertiere zu float für JSON-Serialisierung
            if current_value not in (STATE_UNAVAILABLE, STATE_UNKNOWN, None) and self._is_valid_number(current_value):
                try:
                    # Explizite Konvertierung zu float
                    current_value = self._apply_rounding("total_integral", float(current_value))
                except (ValueError, TypeError):
                    current_value = None
            else:
                current_value = None
                
            diagnostics["total_integral"] = {
                "entity_id": self.total_integral.entity_id,
                "current": current_value,  # Jetzt als float oder Fehlerstring
                "icon": self.total_integral.icon,
                "unit_of_measurement": self.total_integral.native_unit_of_measurement,
            }
        
        # Füge total_water_consumption hinzu
        if self.total_water_consumption:
            current_value = self.total_water_consumption.native_value
            if current_value not in (STATE_UNAVAILABLE, STATE_UNKNOWN, None) and self._is_valid_number(current_value):
                try:
                    current_value = self._apply_rounding("total_water_consumption", float(current_value))
                except (ValueError, TypeError):
                    current_value = None
            else:
                current_value = None
                
            diagnostics["total_water_consumption"] = {
                "entity_id": self.total_water_consumption.entity_id,
                "current": current_value,
                "icon": self.total_water_consumption.icon,
                "unit_of_measurement": self.total_water_consumption.native_unit_of_measurement,
            }
        
        # Füge total_fertilizer_consumption hinzu
        if self.total_fertilizer_consumption:
            current_value = self.total_fertilizer_consumption.native_value
            if current_value not in (STATE_UNAVAILABLE, STATE_UNKNOWN, None) and self._is_valid_number(current_value):
                try:
                    current_value = self._apply_rounding("total_fertilizer_consumption", float(current_value))
                except (ValueError, TypeError):
                    current_value = None
            else:
                current_value = None
                
            diagnostics["total_fertilizer_consumption"] = {
                "entity_id": self.total_fertilizer_consumption.entity_id,
                "current": current_value,
                "icon": self.total_fertilizer_consumption.icon,
                "unit_of_measurement": self.total_fertilizer_consumption.native_unit_of_measurement,
            }
        
        # Füge moisture_consumption hinzu
        if self.moisture_consumption:
            current_value = self.moisture_consumption.native_value
            if current_value not in (STATE_UNAVAILABLE, STATE_UNKNOWN, None) and self._is_valid_number(current_value):
                try:
                    current_value = self._apply_rounding("moisture_consumption", float(current_value))
                except (ValueError, TypeError):
                    current_value = None
            else:
                current_value = None
                
            diagnostics["moisture_consumption"] = {
                "entity_id": self.moisture_consumption.entity_id,
                "current": current_value,
                "icon": self.moisture_consumption.icon,
                "unit_of_measurement": self.moisture_consumption.native_unit_of_measurement,
            }
        
        # Füge fertilizer_consumption hinzu
        if self.fertilizer_consumption:
            current_value = self.fertilizer_consumption.native_value
            if current_value not in (STATE_UNAVAILABLE, STATE_UNKNOWN, None) and self._is_valid_number(current_value):
                try:
                    current_value = self._apply_rounding("fertilizer_consumption", float(current_value))
                except (ValueError, TypeError):
                    current_value = None
            else:
                current_value = None
                
            diagnostics["fertilizer_consumption"] = {
                "entity_id": self.fertilizer_consumption.entity_id,
                "current": current_value,
                "icon": self.fertilizer_consumption.icon,
                "unit_of_measurement": self.fertilizer_consumption.native_unit_of_measurement,
            }
        
        # Füge power_consumption hinzu
        if self.power_consumption:
            current_value = self.power_consumption.native_value
            if current_value not in (STATE_UNAVAILABLE, STATE_UNKNOWN, None) and self._is_valid_number(current_value):
                try:
                    current_value = self._apply_rounding("power_consumption", float(current_value))
                except (ValueError, TypeError):
                    current_value = None
            else:
                current_value = None
                
            diagnostics["power_consumption"] = {
                "entity_id": self.power_consumption.entity_id,
                "current": current_value,
                "icon": self.power_consumption.icon,
                "unit_of_measurement": self.power_consumption.native_unit_of_measurement,
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

    def _apply_rounding(self, sensor_type: str, value: Any) -> Any:
        """Apply centralized decimal rounding for websocket values."""
        if value in (STATE_UNKNOWN, STATE_UNAVAILABLE, None):
            return None
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        try:
            decimals = self.decimals_for(sensor_type)
        except Exception:
            decimals = 2
        return round(numeric, decimals)

    def _is_valid_number(self, value) -> bool:
        """Check if a value is a valid number."""
        if value is None:
            return False
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False

    @property
    def threshold_entities(self) -> list[Entity]:
        """List all threshold entities"""
        entities = [
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
        ]
        
        # Add pH entities if they exist
        if self.max_ph is not None:
            entities.append(self.max_ph)
        if self.min_ph is not None:
            entities.append(self.min_ph)
            
        return entities

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

    def update(self) -> None:
        """Run on every update to allow for changes from the GUI and service call."""
        _LOGGER.debug("Updating plant status for %s", self.name)
        new_state = STATE_OK
        known_state = False

        if self.sensor_temperature is not None:
            temperature = self.sensor_temperature.state
            if temperature is not None and temperature != STATE_UNAVAILABLE and temperature != STATE_UNKNOWN and self.min_temperature is not None and self.max_temperature is not None:
                try:
                    known_state = True
                    temp_value = float(temperature)
                    min_temp = float(self.min_temperature.native_value)
                    max_temp = float(self.max_temperature.native_value)
                    _LOGGER.debug("Evaluating temperature sensor: value=%s, min=%s, max=%s", temp_value, min_temp, max_temp)
                    if temp_value < min_temp:
                        self.temperature_status = STATE_LOW
                        if self.temperature_trigger:
                            new_state = STATE_PROBLEM
                            _LOGGER.debug("Temperature is LOW, setting plant state to PROBLEM")
                    elif temp_value > max_temp:
                        self.temperature_status = STATE_HIGH
                        if self.temperature_trigger:
                            new_state = STATE_PROBLEM
                            _LOGGER.debug("Temperature is HIGH, setting plant state to PROBLEM")
                    else:
                        self.temperature_status = STATE_OK
                        _LOGGER.debug("Temperature is OK")
                except (ValueError, TypeError) as e:
                    _LOGGER.warning("Invalid value for temperature sensor: %s", str(e))

        if self.sensor_conductivity is not None:
            conductivity = self.sensor_conductivity.state
            if conductivity is not None and conductivity != STATE_UNAVAILABLE and conductivity != STATE_UNKNOWN and self.min_conductivity is not None and self.max_conductivity is not None:
                try:
                    known_state = True
                    cond_value = float(conductivity)
                    min_cond = float(self.min_conductivity.native_value)
                    max_cond = float(self.max_conductivity.native_value)
                    _LOGGER.debug("Evaluating conductivity sensor: value=%s, min=%s, max=%s", cond_value, min_cond, max_cond)
                    if cond_value < min_cond:
                        self.conductivity_status = STATE_LOW
                        if self.conductivity_trigger:
                            new_state = STATE_PROBLEM
                            _LOGGER.debug("Conductivity is LOW, setting plant state to PROBLEM")
                    elif cond_value > max_cond:
                        self.conductivity_status = STATE_HIGH
                        if self.conductivity_trigger:
                            new_state = STATE_PROBLEM
                            _LOGGER.debug("Conductivity is HIGH, setting plant state to PROBLEM")
                    else:
                        self.conductivity_status = STATE_OK
                        _LOGGER.debug("Conductivity is OK")
                except (ValueError, TypeError) as e:
                    _LOGGER.warning("Invalid value for conductivity sensor: %s", str(e))

        if self.sensor_illuminance is not None:
            illuminance = self.sensor_illuminance.state
            if illuminance is not None and illuminance != STATE_UNAVAILABLE and illuminance != STATE_UNKNOWN and self.min_illuminance is not None and self.max_illuminance is not None:
                try:
                    known_state = True
                    illum_value = float(illuminance)
                    min_illum = float(self.min_illuminance.native_value)
                    max_illum = float(self.max_illuminance.native_value)
                    _LOGGER.debug("Evaluating illuminance sensor: value=%s, min=%s, max=%s", illum_value, min_illum, max_illum)
                    if illum_value < min_illum:
                        self.illuminance_status = STATE_LOW
                        if self.illuminance_trigger:
                            new_state = STATE_PROBLEM
                            _LOGGER.debug("Illuminance is LOW, setting plant state to PROBLEM")
                    elif illum_value > max_illum:
                        self.illuminance_status = STATE_HIGH
                        if self.illuminance_trigger:
                            new_state = STATE_PROBLEM
                            _LOGGER.debug("Illuminance is HIGH, setting plant state to PROBLEM")
                    else:
                        self.illuminance_status = STATE_OK
                        _LOGGER.debug("Illuminance is OK")
                except (ValueError, TypeError) as e:
                    _LOGGER.warning("Invalid value for illuminance sensor: %s", str(e))

        if self.sensor_humidity is not None:
            humidity = self.sensor_humidity.state
            if humidity is not None and humidity != STATE_UNAVAILABLE and humidity != STATE_UNKNOWN and self.min_humidity is not None and self.max_humidity is not None:
                try:
                    known_state = True
                    humid_value = float(humidity)
                    min_humid = float(self.min_humidity.native_value)
                    max_humid = float(self.max_humidity.native_value)
                    _LOGGER.debug("Evaluating humidity sensor: value=%s, min=%s, max=%s", humid_value, min_humid, max_humid)
                    if humid_value < min_humid:
                        self.humidity_status = STATE_LOW
                        if self.humidity_trigger:
                            new_state = STATE_PROBLEM
                            _LOGGER.debug("Humidity is LOW, setting plant state to PROBLEM")
                    elif humid_value > max_humid:
                        self.humidity_status = STATE_HIGH
                        if self.humidity_trigger:
                            new_state = STATE_PROBLEM
                            _LOGGER.debug("Humidity is HIGH, setting plant state to PROBLEM")
                    else:
                        self.humidity_status = STATE_OK
                        _LOGGER.debug("Humidity is OK")
                except (ValueError, TypeError) as e:
                    _LOGGER.warning("Invalid value for humidity sensor: %s", str(e))

        if self.sensor_CO2 is not None:
            CO2 = self.sensor_CO2.state
            if CO2 is not None and CO2 != STATE_UNAVAILABLE and CO2 != STATE_UNKNOWN and self.min_CO2 is not None and self.max_CO2 is not None:
                try:
                    known_state = True
                    co2_value = float(CO2)
                    min_co2 = float(self.min_CO2.native_value)
                    max_co2 = float(self.max_CO2.native_value)
                    _LOGGER.debug("Evaluating CO2 sensor: value=%s, min=%s, max=%s", co2_value, min_co2, max_co2)
                    if co2_value < min_co2:
                        self.CO2_status = STATE_LOW
                        if self.CO2_trigger:
                            new_state = STATE_PROBLEM
                            _LOGGER.debug("CO2 is LOW, setting plant state to PROBLEM")
                    elif co2_value > max_co2:
                        self.CO2_status = STATE_HIGH
                        if self.CO2_trigger:
                            new_state = STATE_PROBLEM
                            _LOGGER.debug("CO2 is HIGH, setting plant state to PROBLEM")
                    else:
                        self.CO2_status = STATE_OK
                        _LOGGER.debug("CO2 is OK")
                except (ValueError, TypeError) as e:
                    _LOGGER.warning("Invalid value for CO2 sensor: %s", str(e))

        if self.dli is not None:
            dli = self.dli.state
            if dli is not None and dli != STATE_UNAVAILABLE and dli != STATE_UNKNOWN and self.min_dli is not None and self.max_dli is not None:
                try:
                    known_state = True
                    dli_value = float(dli)
                    min_dli_val = float(self.min_dli.native_value)
                    max_dli_val = float(self.max_dli.native_value)
                    _LOGGER.debug("Evaluating DLI sensor: value=%s, min=%s, max=%s", dli_value, min_dli_val, max_dli_val)
                    if dli_value < min_dli_val:
                        self.dli_status = STATE_LOW
                        if self.dli_trigger:
                            new_state = STATE_PROBLEM
                            _LOGGER.debug("DLI is LOW, setting plant state to PROBLEM")
                    elif dli_value > max_dli_val:
                        self.dli_status = STATE_HIGH
                        if self.dli_trigger:
                            new_state = STATE_PROBLEM
                            _LOGGER.debug("DLI is HIGH, setting plant state to PROBLEM")
                    else:
                        self.dli_status = STATE_OK
                        _LOGGER.debug("DLI is OK")
                except (ValueError, TypeError) as e:
                    _LOGGER.warning("Invalid value for DLI sensor: %s", str(e))

        # Überprüfe Wasser-Verbrauch
        if self.moisture_consumption is not None:
            water_consumption = self.moisture_consumption.state
            if water_consumption is not None and water_consumption != STATE_UNAVAILABLE and water_consumption != STATE_UNKNOWN and self.min_water_consumption is not None and self.max_water_consumption is not None:
                try:
                    known_state = True
                    water_value = float(water_consumption)
                    min_water = float(self.min_water_consumption.native_value)
                    max_water = float(self.max_water_consumption.native_value)
                    _LOGGER.debug("Evaluating water consumption sensor: value=%s, min=%s, max=%s", water_value, min_water, max_water)
                    if water_value < min_water:
                        self.water_consumption_status = STATE_LOW
                        if self.water_consumption_trigger:
                            new_state = STATE_PROBLEM
                            _LOGGER.debug("Water consumption is LOW, setting plant state to PROBLEM")
                    elif water_value > max_water:
                        self.water_consumption_status = STATE_HIGH
                        if self.water_consumption_trigger:
                            new_state = STATE_PROBLEM
                            _LOGGER.debug("Water consumption is HIGH, setting plant state to PROBLEM")
                    else:
                        self.water_consumption_status = STATE_OK
                        _LOGGER.debug("Water consumption is OK")
                except (ValueError, TypeError) as e:
                    _LOGGER.warning("Invalid value for water consumption sensor: %s", str(e))

        # Überprüfe Dünger-Verbrauch
        if self.fertilizer_consumption is not None:
            fertilizer_consumption = self.fertilizer_consumption.state
            if fertilizer_consumption is not None and fertilizer_consumption != STATE_UNAVAILABLE and fertilizer_consumption != STATE_UNKNOWN and self.min_fertilizer_consumption is not None and self.max_fertilizer_consumption is not None:
                try:
                    known_state = True
                    fert_value = float(fertilizer_consumption)
                    min_fert = float(self.min_fertilizer_consumption.native_value)
                    max_fert = float(self.max_fertilizer_consumption.native_value)
                    _LOGGER.debug("Evaluating fertilizer consumption sensor: value=%s, min=%s, max=%s", fert_value, min_fert, max_fert)
                    if fert_value < min_fert:
                        self.fertilizer_consumption_status = STATE_LOW
                        if self.fertilizer_consumption_trigger:
                            new_state = STATE_PROBLEM
                            _LOGGER.debug("Fertilizer consumption is LOW, setting plant state to PROBLEM")
                    elif fert_value > max_fert:
                        self.fertilizer_consumption_status = STATE_HIGH
                        if self.fertilizer_consumption_trigger:
                            new_state = STATE_PROBLEM
                            _LOGGER.debug("Fertilizer consumption is HIGH, setting plant state to PROBLEM")
                    else:
                        self.fertilizer_consumption_status = STATE_OK
                        _LOGGER.debug("Fertilizer consumption is OK")
                except (ValueError, TypeError) as e:
                    _LOGGER.warning("Invalid value for fertilizer consumption sensor: %s", str(e))

        # Überprüfe Power Consumption
        if self.sensor_power_consumption is not None:
            power_consumption = self.sensor_power_consumption.state
            if power_consumption is not None and power_consumption != STATE_UNAVAILABLE and power_consumption != STATE_UNKNOWN and self.min_power_consumption is not None and self.max_power_consumption is not None:
                try:
                    known_state = True
                    power_value = float(power_consumption)
                    min_power = float(self.min_power_consumption.native_value)
                    max_power = float(self.max_power_consumption.native_value)
                    _LOGGER.debug("Evaluating power consumption sensor: value=%s, min=%s, max=%s", power_value, min_power, max_power)
                    if power_value < min_power:
                        self.power_consumption_status = STATE_LOW
                        if self.power_consumption_trigger:
                            new_state = STATE_PROBLEM
                            _LOGGER.debug("Power consumption is LOW, setting plant state to PROBLEM")
                    elif power_value > max_power:
                        self.power_consumption_status = STATE_HIGH
                        if self.power_consumption_trigger:
                            new_state = STATE_PROBLEM
                            _LOGGER.debug("Power consumption is HIGH, setting plant state to PROBLEM")
                    else:
                        self.power_consumption_status = STATE_OK
                        _LOGGER.debug("Power consumption is OK")
                except (ValueError, TypeError) as e:
                    _LOGGER.warning("Invalid value for power consumption sensor: %s", str(e))

        # Überprüfe pH Sensor
        if self.sensor_ph is not None:
            ph = self.sensor_ph.state
            if ph is not None and ph != STATE_UNAVAILABLE and ph != STATE_UNKNOWN and self.min_ph is not None and self.max_ph is not None:
                try:
                    known_state = True
                    ph_value = float(ph)
                    min_ph_val = float(self.min_ph.native_value)
                    max_ph_val = float(self.max_ph.native_value)
                    _LOGGER.debug("Evaluating pH sensor: value=%s, min=%s, max=%s", ph_value, min_ph_val, max_ph_val)
                    if ph_value < min_ph_val:
                        self.ph_status = STATE_LOW
                        if self.ph_trigger:
                            new_state = STATE_PROBLEM
                            _LOGGER.debug("pH is LOW, setting plant state to PROBLEM")
                    elif ph_value > max_ph_val:
                        self.ph_status = STATE_HIGH
                        if self.ph_trigger:
                            new_state = STATE_PROBLEM
                            _LOGGER.debug("pH is HIGH, setting plant state to PROBLEM")
                    else:
                        self.ph_status = STATE_OK
                        _LOGGER.debug("pH is OK")
                except (ValueError, TypeError) as e:
                    _LOGGER.warning("Invalid value for pH sensor: %s", str(e))

        # Set the state
        self._attr_state = new_state
        if not known_state:
            self._attr_state = STATE_UNKNOWN
            _LOGGER.debug("Plant %s has no known sensor data, setting state to UNKNOWN", self.name)
        else:
            _LOGGER.debug("Plant %s state updated to %s", self.name, new_state)



    def update_kwh_price(self, new_price) -> None:
        """Update the kWh price."""
        self._kwh_price = new_price
        # Aktualisiere den Energiekosten-Sensor wenn vorhanden
        if hasattr(self, 'energy_cost') and self.energy_cost:
            self.energy_cost.async_schedule_update_ha_state(True)

    def get_tent_name(self) -> str:
        """Get the name of the assigned tent."""
        if self._assigned_tent:
            return self._assigned_tent.name
        return "None"

    def add_growth_phase_select(self, growth_phase_select: Entity) -> None:
        """Add the growth phase select entity."""
        self.growth_phase_select = growth_phase_select

    def add_cycle_select(self, cycle_select: Entity) -> None:
        """Add the cycle select entity."""
        self.cycle_select = cycle_select

    def add_tent_select(self, tent_select: Entity) -> None:
        """Add the tent select entity."""
        self.tent_select = tent_select

    def add_flowering_duration(self, flowering_duration: Entity) -> None:
        """Füge die Blütedauer Number Entity hinzu."""
        self.flowering_duration = flowering_duration

    def add_treatment_select(self, treatment_select: Entity) -> None:
        """Add the treatment select entity."""
        self.treatment_select = treatment_select

    def add_pot_size(self, pot_size: Entity) -> None:
        """Add the pot size entity."""
        self.pot_size = pot_size

    def add_water_capacity(self, water_capacity: Entity) -> None:
        """Add the water capacity entity."""
        self.water_capacity = water_capacity

    def add_health_number(self, health_number: Entity) -> None:
        """Add the health number entity."""
        self.health_number = health_number

    def add_journal(self, journal: Entity) -> None:
        """Add the journal entity."""
        self.journal = journal

    def add_location_history(self, location_history: Entity) -> None:
        """Add the location history entity."""
        self.location_history = location_history

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

    def add_power_consumption_sensors(self, current: Entity, total: Entity) -> None:
        """Add the power consumption sensors."""
        self.power_consumption = current
        self.total_power_consumption = total
        if self.sensor_power_consumption is None:
            self.sensor_power_consumption = current

    def add_thresholds(
        self,
        max_moisture: Entity | None = None,
        min_moisture: Entity | None = None,
        max_temperature: Entity | None = None,
        min_temperature: Entity | None = None,
        max_conductivity: Entity | None = None,
        min_conductivity: Entity | None = None,
        max_illuminance: Entity | None = None,
        min_illuminance: Entity | None = None,
        max_humidity: Entity | None = None,
        min_humidity: Entity | None = None,
        max_CO2: Entity | None = None,
        min_CO2: Entity | None = None,
        max_dli: Entity | None = None,
        min_dli: Entity | None = None,
        max_water_consumption: Entity | None = None,
        min_water_consumption: Entity | None = None,
        max_fertilizer_consumption: Entity | None = None,
        min_fertilizer_consumption: Entity | None = None,
        max_power_consumption: Entity | None = None,
        min_power_consumption: Entity | None = None,
        max_ph: Entity | None = None,
        min_ph: Entity | None = None,
    ) -> None:
        """Add the threshold entities."""
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
        self.max_ph = max_ph
        self.min_ph = min_ph

    def add_calculations(
        self,
        ppfd: Entity | None = None,
        total_integral: Entity | None = None,
        moisture_consumption: Entity | None = None,
        fertilizer_consumption: Entity | None = None,
    ) -> None:
        """Add the calculation entities."""
        self.ppfd = ppfd
        self.total_integral = total_integral
        self.moisture_consumption = moisture_consumption
        self.fertilizer_consumption = fertilizer_consumption

    def add_dli(self, dli: Entity | None = None) -> None:
        """Add the DLI entity."""
        self.dli = dli

    def change_tent(self, tent_entity) -> None:
        """Change the tent assignment for this plant."""
        self._assigned_tent = tent_entity
        self._tent_id = tent_entity.unique_id if tent_entity else None
        
        # If no tent is assigned, clear the sensor mappings
        if not tent_entity:
            _LOGGER.debug("Clearing tent assignment for plant %s", self.name)
            # Clear sensor mappings in config
            data = dict(self._config.data)
            plant_info = dict(data.get(FLOW_PLANT_INFO, {}))
            
            # Clear all sensor mappings
            for sensor_key in [FLOW_SENSOR_TEMPERATURE, FLOW_SENSOR_MOISTURE, FLOW_SENSOR_CONDUCTIVITY, 
                              FLOW_SENSOR_ILLUMINANCE, FLOW_SENSOR_HUMIDITY, FLOW_SENSOR_CO2,
                              FLOW_SENSOR_POWER_CONSUMPTION, FLOW_SENSOR_PH]:
                if sensor_key in plant_info:
                    del plant_info[sensor_key]
            
            data[FLOW_PLANT_INFO] = plant_info
            self._hass.config_entries.async_update_entry(self._config, data=data)
            
            # Clear external sensors
            if hasattr(self, 'sensor_temperature') and self.sensor_temperature:
                self.sensor_temperature.replace_external_sensor(None)
            if hasattr(self, 'sensor_moisture') and self.sensor_moisture:
                self.sensor_moisture.replace_external_sensor(None)
            if hasattr(self, 'sensor_conductivity') and self.sensor_conductivity:
                self.sensor_conductivity.replace_external_sensor(None)
            if hasattr(self, 'sensor_illuminance') and self.sensor_illuminance:
                self.sensor_illuminance.replace_external_sensor(None)
            if hasattr(self, 'sensor_humidity') and self.sensor_humidity:
                self.sensor_humidity.replace_external_sensor(None)
            if hasattr(self, 'sensor_CO2') and self.sensor_CO2:
                self.sensor_CO2.replace_external_sensor(None)
            if hasattr(self, 'sensor_power_consumption') and self.sensor_power_consumption:
                self.sensor_power_consumption.replace_external_sensor(None)
            if hasattr(self, 'sensor_ph') and self.sensor_ph:
                self.sensor_ph.replace_external_sensor(None)
            
            self.async_write_ha_state()
            return

        # Get tent sensors
        tent_sensors = tent_entity.get_sensors()
        _LOGGER.debug("Tent %s has sensors: %s", tent_entity.name, tent_sensors)
        
        if not tent_sensors:
            _LOGGER.debug("No sensors to replace for plant %s", self.name)
            return
            
        # Map tent sensors to plant sensor types
        sensor_mapping = {}
        for sensor_entity_id in tent_sensors:
            # Get the sensor state to determine its type
            try:
                sensor_state = self._hass.states.get(sensor_entity_id)
                if not sensor_state:
                    _LOGGER.warning("Sensor %s not found in Home Assistant", sensor_entity_id)
                    continue
            except Exception as e:
                _LOGGER.warning("Error getting sensor %s: %s", sensor_entity_id, e)
                continue
                
            # Determine sensor type based on device class or unit of measurement
            device_class = sensor_state.attributes.get("device_class", "")
            unit_of_measurement = sensor_state.attributes.get("unit_of_measurement", "")
            
            _LOGGER.debug("Sensor %s: device_class=%s, unit=%s", sensor_entity_id, device_class, unit_of_measurement)
            
            # Map to plant sensor types
            if device_class == "temperature" or unit_of_measurement in ["°C", "°F", "K"]:
                sensor_mapping["temperature"] = sensor_entity_id
            elif device_class == "humidity" or unit_of_measurement == "%":
                # Check if it's air humidity or soil moisture based on entity name
                if "soil" in sensor_entity_id.lower() or "moisture" in sensor_entity_id.lower():
                    sensor_mapping["moisture"] = sensor_entity_id
                else:
                    sensor_mapping["humidity"] = sensor_entity_id
            elif device_class == "illuminance" or unit_of_measurement in ["lx", "lux"]:
                sensor_mapping["illuminance"] = sensor_entity_id
            elif device_class == "conductivity" or unit_of_measurement == "µS/cm":
                sensor_mapping["conductivity"] = sensor_entity_id
            elif "co2" in sensor_entity_id.lower() or unit_of_measurement == "ppm":
                sensor_mapping["co2"] = sensor_entity_id
            elif "power" in sensor_entity_id.lower() or unit_of_measurement in ["W", "kW"]:
                sensor_mapping["power_consumption"] = sensor_entity_id
            elif "ph" in sensor_entity_id.lower() or unit_of_measurement in ["pH", "ph"]:
                sensor_mapping["ph"] = sensor_entity_id
        
        _LOGGER.debug("Sensor mapping for plant %s: %s", self.name, sensor_mapping)
        
        # Update the config entry with the new sensor assignments FIRST
        data = dict(self._config.data)
        plant_info = dict(data.get(FLOW_PLANT_INFO, {}))
        
        # Clear existing sensor mappings
        for sensor_key in [FLOW_SENSOR_TEMPERATURE, FLOW_SENSOR_MOISTURE, FLOW_SENSOR_CONDUCTIVITY, 
                          FLOW_SENSOR_ILLUMINANCE, FLOW_SENSOR_HUMIDITY, FLOW_SENSOR_CO2,
                          FLOW_SENSOR_POWER_CONSUMPTION, FLOW_SENSOR_PH]:
            if sensor_key in plant_info:
                del plant_info[sensor_key]
        
        # Set new sensor mappings
        if "temperature" in sensor_mapping:
            plant_info[FLOW_SENSOR_TEMPERATURE] = sensor_mapping["temperature"]
        if "moisture" in sensor_mapping:
            plant_info[FLOW_SENSOR_MOISTURE] = sensor_mapping["moisture"]
        if "conductivity" in sensor_mapping:
            plant_info[FLOW_SENSOR_CONDUCTIVITY] = sensor_mapping["conductivity"]
        if "illuminance" in sensor_mapping:
            plant_info[FLOW_SENSOR_ILLUMINANCE] = sensor_mapping["illuminance"]
        if "humidity" in sensor_mapping:
            plant_info[FLOW_SENSOR_HUMIDITY] = sensor_mapping["humidity"]
        if "co2" in sensor_mapping:
            plant_info[FLOW_SENSOR_CO2] = sensor_mapping["co2"]
        if "power_consumption" in sensor_mapping:
            plant_info[FLOW_SENSOR_POWER_CONSUMPTION] = sensor_mapping["power_consumption"]
        if "ph" in sensor_mapping:
            plant_info[FLOW_SENSOR_PH] = sensor_mapping["ph"]
            
        data[FLOW_PLANT_INFO] = plant_info
        self._hass.config_entries.async_update_entry(self._config, data=data)
        
        # Replace sensors using the existing replace_external_sensor method
        # Only replace sensors that actually exist
        updated_sensors = []
        
        if hasattr(self, 'sensor_temperature') and self.sensor_temperature and "temperature" in sensor_mapping:
            self.sensor_temperature.replace_external_sensor(sensor_mapping["temperature"])
            updated_sensors.append(self.sensor_temperature)
            _LOGGER.debug("Assigned temperature sensor %s to plant %s", sensor_mapping["temperature"], self.name)
            
        if hasattr(self, 'sensor_moisture') and self.sensor_moisture and "moisture" in sensor_mapping:
            self.sensor_moisture.replace_external_sensor(sensor_mapping["moisture"])
            updated_sensors.append(self.sensor_moisture)
            _LOGGER.debug("Assigned moisture sensor %s to plant %s", sensor_mapping["moisture"], self.name)
            
        if hasattr(self, 'sensor_conductivity') and self.sensor_conductivity and "conductivity" in sensor_mapping:
            self.sensor_conductivity.replace_external_sensor(sensor_mapping["conductivity"])
            updated_sensors.append(self.sensor_conductivity)
            _LOGGER.debug("Assigned conductivity sensor %s to plant %s", sensor_mapping["conductivity"], self.name)
            
        if hasattr(self, 'sensor_illuminance') and self.sensor_illuminance and "illuminance" in sensor_mapping:
            self.sensor_illuminance.replace_external_sensor(sensor_mapping["illuminance"])
            updated_sensors.append(self.sensor_illuminance)
            _LOGGER.debug("Assigned illuminance sensor %s to plant %s", sensor_mapping["illuminance"], self.name)
            
        if hasattr(self, 'sensor_humidity') and self.sensor_humidity and "humidity" in sensor_mapping:
            self.sensor_humidity.replace_external_sensor(sensor_mapping["humidity"])
            updated_sensors.append(self.sensor_humidity)
            _LOGGER.debug("Assigned humidity sensor %s to plant %s", sensor_mapping["humidity"], self.name)
            
        if hasattr(self, 'sensor_CO2') and self.sensor_CO2 and "co2" in sensor_mapping:
            self.sensor_CO2.replace_external_sensor(sensor_mapping["co2"])
            updated_sensors.append(self.sensor_CO2)
            _LOGGER.debug("Assigned CO2 sensor %s to plant %s", sensor_mapping["co2"], self.name)
            
        if hasattr(self, 'sensor_power_consumption') and self.sensor_power_consumption and "power_consumption" in sensor_mapping:
            self.sensor_power_consumption.replace_external_sensor(sensor_mapping["power_consumption"])
            updated_sensors.append(self.sensor_power_consumption)
            _LOGGER.debug("Assigned power consumption sensor %s to plant %s", sensor_mapping["power_consumption"], self.name)
            
        if hasattr(self, 'sensor_ph') and self.sensor_ph and "ph" in sensor_mapping:
            self.sensor_ph.replace_external_sensor(sensor_mapping["ph"])
            updated_sensors.append(self.sensor_ph)
            _LOGGER.debug("Assigned pH sensor %s to plant %s", sensor_mapping["ph"], self.name)
            
        # Force an update of the plant state to reflect the new sensor assignments
        self.async_write_ha_state()
        _LOGGER.info("Replaced sensors for plant %s: %s", self.name, sensor_mapping)

    def _schedule_regular_updates(self) -> None:
        """Schedule regular updates for the plant status."""
        # Cancel any existing update schedule
        if self._update_unsub:
            self._update_unsub()
            self._update_unsub = None
        
        # Schedule updates every 30 seconds
        from homeassistant.helpers.event import async_track_time_interval
        from datetime import timedelta
        
        async def _regular_update_callback(now):
            """Callback for regular updates."""
            self.update()
            self.async_write_ha_state()
        
        self._update_unsub = async_track_time_interval(
            self._hass, _regular_update_callback, timedelta(seconds=30)
        )
        _LOGGER.debug("Scheduled regular updates for plant %s", self.name)

    def replace_sensors(self, tent_sensors: dict) -> None:
        """Replace sensors based on tent sensor mapping."""
        _LOGGER.debug("Replacing sensors for plant %s with tent sensors: %s", self.name, tent_sensors)
        
        if not tent_sensors:
            _LOGGER.debug("No sensors to replace for plant %s", self.name)
            return
            
        # Map tent sensors to plant sensor types
        sensor_mapping = {}
        for sensor_entity_id in tent_sensors:
            # Get the sensor state to determine its type
            try:
                sensor_state = self._hass.states.get(sensor_entity_id)
                if not sensor_state:
                    _LOGGER.warning("Sensor %s not found in Home Assistant", sensor_entity_id)
                    continue
            except Exception as e:
                _LOGGER.warning("Error getting sensor %s: %s", sensor_entity_id, e)
                continue
                
            # Determine sensor type based on device class or unit of measurement
            device_class = sensor_state.attributes.get("device_class", "")
            unit_of_measurement = sensor_state.attributes.get("unit_of_measurement", "")
            
            _LOGGER.debug("Sensor %s: device_class=%s, unit=%s", sensor_entity_id, device_class, unit_of_measurement)
            
            # Map to plant sensor types
            if device_class == "temperature" or unit_of_measurement in ["°C", "°F", "K"]:
                sensor_mapping["temperature"] = sensor_entity_id
            elif device_class == "humidity" or unit_of_measurement == "%":
                # Check if it's air humidity or soil moisture based on entity name
                if "soil" in sensor_entity_id.lower() or "moisture" in sensor_entity_id.lower():
                    sensor_mapping["moisture"] = sensor_entity_id
                else:
                    sensor_mapping["humidity"] = sensor_entity_id
            elif device_class == "illuminance" or unit_of_measurement in ["lx", "lux"]:
                sensor_mapping["illuminance"] = sensor_entity_id
            elif device_class == "conductivity" or unit_of_measurement == "µS/cm":
                sensor_mapping["conductivity"] = sensor_entity_id
            elif "co2" in sensor_entity_id.lower() or unit_of_measurement == "ppm":
                sensor_mapping["co2"] = sensor_entity_id
            elif "power" in sensor_entity_id.lower() or unit_of_measurement in ["W", "kW"]:
                sensor_mapping["power_consumption"] = sensor_entity_id
            elif "ph" in sensor_entity_id.lower() or unit_of_measurement in ["pH", "ph"]:
                sensor_mapping["ph"] = sensor_entity_id
        
        _LOGGER.debug("Sensor mapping for plant %s: %s", self.name, sensor_mapping)
        
        # Update the config entry with the new sensor assignments FIRST
        data = dict(self._config.data)
        plant_info = dict(data.get(FLOW_PLANT_INFO, {}))
        
        # Clear existing sensor mappings
        for sensor_key in [FLOW_SENSOR_TEMPERATURE, FLOW_SENSOR_MOISTURE, FLOW_SENSOR_CONDUCTIVITY, 
                          FLOW_SENSOR_ILLUMINANCE, FLOW_SENSOR_HUMIDITY, FLOW_SENSOR_CO2,
                          FLOW_SENSOR_POWER_CONSUMPTION, FLOW_SENSOR_PH]:
            if sensor_key in plant_info:
                del plant_info[sensor_key]
        
        # Set new sensor mappings
        if "temperature" in sensor_mapping:
            plant_info[FLOW_SENSOR_TEMPERATURE] = sensor_mapping["temperature"]
        if "moisture" in sensor_mapping:
            plant_info[FLOW_SENSOR_MOISTURE] = sensor_mapping["moisture"]
        if "conductivity" in sensor_mapping:
            plant_info[FLOW_SENSOR_CONDUCTIVITY] = sensor_mapping["conductivity"]
        if "illuminance" in sensor_mapping:
            plant_info[FLOW_SENSOR_ILLUMINANCE] = sensor_mapping["illuminance"]
        if "humidity" in sensor_mapping:
            plant_info[FLOW_SENSOR_HUMIDITY] = sensor_mapping["humidity"]
        if "co2" in sensor_mapping:
            plant_info[FLOW_SENSOR_CO2] = sensor_mapping["co2"]
        if "power_consumption" in sensor_mapping:
            plant_info[FLOW_SENSOR_POWER_CONSUMPTION] = sensor_mapping["power_consumption"]
        if "ph" in sensor_mapping:
            plant_info[FLOW_SENSOR_PH] = sensor_mapping["ph"]
            
        data[FLOW_PLANT_INFO] = plant_info
        self._hass.config_entries.async_update_entry(self._config, data=data)
        
        # Replace sensors using the existing replace_external_sensor method
        # Only replace sensors that actually exist
        updated_sensors = []
        
        if hasattr(self, 'sensor_temperature') and self.sensor_temperature and "temperature" in sensor_mapping:
            self.sensor_temperature.replace_external_sensor(sensor_mapping["temperature"])
            updated_sensors.append(self.sensor_temperature)
            _LOGGER.debug("Assigned temperature sensor %s to plant %s", sensor_mapping["temperature"], self.name)
            
        if hasattr(self, 'sensor_moisture') and self.sensor_moisture and "moisture" in sensor_mapping:
            self.sensor_moisture.replace_external_sensor(sensor_mapping["moisture"])
            updated_sensors.append(self.sensor_moisture)
            _LOGGER.debug("Assigned moisture sensor %s to plant %s", sensor_mapping["moisture"], self.name)
            
        if hasattr(self, 'sensor_conductivity') and self.sensor_conductivity and "conductivity" in sensor_mapping:
            self.sensor_conductivity.replace_external_sensor(sensor_mapping["conductivity"])
            updated_sensors.append(self.sensor_conductivity)
            _LOGGER.debug("Assigned conductivity sensor %s to plant %s", sensor_mapping["conductivity"], self.name)
            
        if hasattr(self, 'sensor_illuminance') and self.sensor_illuminance and "illuminance" in sensor_mapping:
            self.sensor_illuminance.replace_external_sensor(sensor_mapping["illuminance"])
            updated_sensors.append(self.sensor_illuminance)
            _LOGGER.debug("Assigned illuminance sensor %s to plant %s", sensor_mapping["illuminance"], self.name)
            
        if hasattr(self, 'sensor_humidity') and self.sensor_humidity and "humidity" in sensor_mapping:
            self.sensor_humidity.replace_external_sensor(sensor_mapping["humidity"])
            updated_sensors.append(self.sensor_humidity)
            _LOGGER.debug("Assigned humidity sensor %s to plant %s", sensor_mapping["humidity"], self.name)
            
        if hasattr(self, 'sensor_CO2') and self.sensor_CO2 and "co2" in sensor_mapping:
            self.sensor_CO2.replace_external_sensor(sensor_mapping["co2"])
            updated_sensors.append(self.sensor_CO2)
            _LOGGER.debug("Assigned CO2 sensor %s to plant %s", sensor_mapping["co2"], self.name)
            
        if hasattr(self, 'sensor_power_consumption') and self.sensor_power_consumption and "power_consumption" in sensor_mapping:
            self.sensor_power_consumption.replace_external_sensor(sensor_mapping["power_consumption"])
            updated_sensors.append(self.sensor_power_consumption)
            _LOGGER.debug("Assigned power consumption sensor %s to plant %s", sensor_mapping["power_consumption"], self.name)
            
        if hasattr(self, 'sensor_ph') and self.sensor_ph and "ph" in sensor_mapping:
            self.sensor_ph.replace_external_sensor(sensor_mapping["ph"])
            updated_sensors.append(self.sensor_ph)
            _LOGGER.debug("Assigned pH sensor %s to plant %s", sensor_mapping["ph"], self.name)
            
        # Force an update of the plant state to reflect the new sensor assignments
        self.async_write_ha_state()
        _LOGGER.info("Replaced sensors for plant %s: %s", self.name, sensor_mapping)

