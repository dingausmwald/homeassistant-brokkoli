"""Services for plant integration."""
import logging
import voluptuous as vol
import aiohttp
import os
from datetime import datetime

from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.const import ATTR_NAME
from homeassistant.exceptions import HomeAssistantError
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import selector
from homeassistant.helpers.template import Template
from homeassistant.helpers import area_registry as ar

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
)

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
    vol.Optional("sorte"): cv.string,
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

    async def create_plant(call: ServiceCall) -> None:
        """Create a new plant."""
        user_input = {
            ATTR_DEVICE_TYPE: DEVICE_TYPE_PLANT,
            ATTR_NAME: call.data[ATTR_NAME],
            ATTR_STRAIN: call.data[ATTR_STRAIN],
            ATTR_BREEDER: call.data.get(ATTR_BREEDER, ""),
            "growth_phase": call.data.get("growth_phase", DEFAULT_GROWTH_PHASE),
            "plant_emoji": call.data.get("plant_emoji", "🌿"),
        }

        # Füge optionale Sensoren hinzu
        if call.data.get(FLOW_SENSOR_TEMPERATURE):
            user_input[FLOW_SENSOR_TEMPERATURE] = call.data[FLOW_SENSOR_TEMPERATURE]
        if call.data.get(FLOW_SENSOR_MOISTURE):
            user_input[FLOW_SENSOR_MOISTURE] = call.data[FLOW_SENSOR_MOISTURE]
        if call.data.get(FLOW_SENSOR_CONDUCTIVITY):
            user_input[FLOW_SENSOR_CONDUCTIVITY] = call.data[FLOW_SENSOR_CONDUCTIVITY]
        if call.data.get(FLOW_SENSOR_ILLUMINANCE):
            user_input[FLOW_SENSOR_ILLUMINANCE] = call.data[FLOW_SENSOR_ILLUMINANCE]
        if call.data.get(FLOW_SENSOR_HUMIDITY):
            user_input[FLOW_SENSOR_HUMIDITY] = call.data[FLOW_SENSOR_HUMIDITY]

        # Erstelle die neue Config Entry
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
            data=user_input
        )

        if result["type"] != FlowResultType.CREATE_ENTRY:
            raise HomeAssistantError(
                f"Failed to create new plant: {result.get('reason', 'unknown error')}"
            )

    async def create_cycle(call: ServiceCall) -> None:
        """Create a new cycle via service call."""
        user_input = {
            ATTR_NAME: call.data.get(ATTR_NAME),
            "device_type": DEVICE_TYPE_CYCLE,
            "plant_emoji": call.data.get("plant_emoji", "🔄"),
        }

        _LOGGER.debug("Creating cycle with data: %s", user_input)

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user", "source_type": "service"},
            data=user_input
        )

        if result["type"] not in ["create_entry", "abort"]:
            _LOGGER.error(
                "Failed to create cycle %s: %s",
                call.data.get(ATTR_NAME),
                result.get("reason", "unknown error"),
            )
            return False

        # Aktualisiere alle Plant Cycle Selects
        for entry_id in hass.data[DOMAIN]:
            if ATTR_PLANT in hass.data[DOMAIN][entry_id]:
                plant = hass.data[DOMAIN][entry_id][ATTR_PLANT]
                if plant.device_type == DEVICE_TYPE_PLANT and plant.cycle_select:
                    plant.cycle_select._update_cycle_options()
                    plant.cycle_select.async_write_ha_state()

        return True

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

    async def handle_clone_plant(call: ServiceCall) -> None:
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
            FLOW_SENSOR_HUMIDITY
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

        _LOGGER.debug("Creating plant clone with data: %s", plant_info)

        # Erstelle die Plant direkt mit allen Daten
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "import"},
            data={FLOW_PLANT_INFO: plant_info}
        )

        if result["type"] != FlowResultType.CREATE_ENTRY:
            raise HomeAssistantError(
                f"Failed to create new plant: {result.get('reason', 'unknown error')}"
            )

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
                    "sorte", "feminized", "timestamp", "effects", "smell",
                    "taste", "phenotype", "hunger", "growth_stretch",
                    "flower_stretch", "mold_resistance", "difficulty",
                    "yield", "notes", "website", "infotext1", "infotext2",
                    "lineage"]:  # images entfernt aus der Liste
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
        
        # Update Growth Phase Attribute wenn vorhanden
        if hasattr(target_plant, "growth_phase_select"):
            phase_attrs = target_plant.growth_phase_select.extra_state_attributes.copy()
            
            # Update Datums-Attribute
            for date_attr in [
                "samen_beginn", "keimen_beginn", "wurzeln_beginn",
                "wachstum_beginn", "blüte_beginn", "geerntet", "entfernt"
            ]:
                if date_attr in call.data:
                    phase_attrs[date_attr] = call.data[date_attr]

            # Update Dauer-Attribute
            for duration_attr in [
                "samen_dauer", "keimen_dauer", "wurzeln_dauer",
                "wachstum_dauer", "blüte_dauer", "geerntet_dauer", "entfernt_dauer"
            ]:
                if duration_attr in call.data:
                    phase_attrs[duration_attr] = call.data[duration_attr]

            # Aktualisiere die Attribute der Growth Phase Entity
            target_plant.growth_phase_select._attr_extra_state_attributes = phase_attrs
            target_plant.growth_phase_select.async_write_ha_state()
        
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
        entity_registry = er.async_get(hass)
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

            # Find plant entity for this device
            plant_entity_id = None
            for entity_entry in entity_registry.entities.values():
                if entity_entry.device_id == device_id and entity_entry.domain == DOMAIN:
                    plant_entity_id = entity_entry.entity_id
                    break

            if area_id:
                area = area_registry.async_get_area(area_id)
                _LOGGER.info(
                    f"Device {device_id} successfully moved to area {area.name}"
                )
            else:
                _LOGGER.info(
                    f"Device {device_id} successfully removed from area"
                )

            # Fire event if we found the plant entity
            if plant_entity_id:
                hass.bus.async_fire(
                    "plant_area_changed",
                    {
                        "plant_entity_id": plant_entity_id,
                        "device_id": device_id,
                        "area_id": area_id,
                        "area_name": area.name if area_id else None
                    }
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

    # Register services
    hass.services.async_register(
        DOMAIN, 
        SERVICE_REPLACE_SENSOR, 
        replace_sensor, 
        schema=REPLACE_SENSOR_SCHEMA
    )
    
    # Schema für update_plant_attributes
    UPDATE_PLANT_SCHEMA = vol.Schema({
        vol.Required("entity_id"): cv.entity_id,
        vol.Optional("strain"): cv.string,
        vol.Optional("breeder"): cv.string,
        vol.Optional("original_flowering_duration"): cv.positive_int,
        vol.Optional("pid"): cv.string,
        vol.Optional("sorte"): cv.string,
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
        # Growth Phase Attribute
        vol.Optional("samen_beginn"): cv.string,
        vol.Optional("samen_dauer"): cv.positive_int,
        vol.Optional("keimen_beginn"): cv.string,
        vol.Optional("keimen_dauer"): cv.positive_int,
        vol.Optional("wurzeln_beginn"): cv.string,
        vol.Optional("wurzeln_dauer"): cv.positive_int,
        vol.Optional("wachstum_beginn"): cv.string,
        vol.Optional("wachstum_dauer"): cv.positive_int,
        vol.Optional("blüte_beginn"): cv.string,
        vol.Optional("blüte_dauer"): cv.positive_int,
        vol.Optional("geerntet"): cv.string,
        vol.Optional("geerntet_dauer"): cv.positive_int,
        vol.Optional("entfernt"): cv.string,
        vol.Optional("entfernt_dauer"): cv.positive_int,
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
        schema=CREATE_PLANT_SCHEMA
    )
    hass.services.async_register(DOMAIN, SERVICE_CREATE_CYCLE, create_cycle)
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
        }),
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