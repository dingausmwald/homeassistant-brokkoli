"""Text entities for plant integration."""
from __future__ import annotations

import logging
from datetime import datetime
import json

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import area_registry as ar

from .const import (
    ATTR_PLANT,
    DOMAIN,
    DEVICE_TYPE_PLANT,
    DEVICE_TYPE_CYCLE,
    DEVICE_TYPE_TENT,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the plant text entities."""
    plant = hass.data[DOMAIN][entry.entry_id][ATTR_PLANT]
    entities = []
    
    # Journal für alle Gerätetypen
    journal = PlantJournal(hass, entry, plant)
    entities.append(journal)
    # Für Tents verwenden wir add_journal, für Plants auch
    if hasattr(plant, 'add_journal'):
        plant.add_journal(journal)
    elif hasattr(plant, 'add_journal_text_entity'):
        plant.add_journal_text_entity(journal)
    
    # Location für alle Gerätetypen (jetzt auch für Cycles)
    location = PlantLocation(hass, entry, plant)
    entities.append(location)
    if hasattr(plant, 'add_location_history'):
        plant.add_location_history(location)
    
    async_add_entities(entities)

class PlantJournal(TextEntity, RestoreEntity):
    """Representation of a plant journal text entity."""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry, plant_device) -> None:
        """Initialize the plant journal."""
        self._attr_native_value = ""
        self._attr_mode = "text"
        self._config = config
        self._hass = hass
        self._plant = plant_device
        self._attr_name = f"{plant_device.name} Journal"
        self._attr_unique_id = f"{config.entry_id}-journal"
        # Journal ist keine Diagnose-Entity
        self._attr_entity_category = None
        self._attr_icon = "mdi:notebook"

    @property
    def device_info(self) -> dict:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._plant.unique_id)},
        }

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        
        # Stelle letzten Zustand wieder her
        last_state = await self.async_get_last_state()
        if last_state and last_state.state:
            self._attr_native_value = last_state.state

    async def async_set_value(self, value: str) -> None:
        """Set new value."""
        self._attr_native_value = value
        self.async_write_ha_state()

class PlantLocation(TextEntity, RestoreEntity):
    """Representation of a plant location entity."""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry, plant_device) -> None:
        """Initialize the plant location."""
        self._attr_native_value = "{}"  # Leeres JSON-Objekt als Standardwert
        self._attr_mode = "text"
        self._config = config
        self._hass = hass
        self._plant = plant_device
        self._attr_name = f"{plant_device.name} Location"
        self._attr_unique_id = f"{config.entry_id}-location"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:map-marker"
        
        # Aktuelle Location - Bei Cycles ohne Position-Informationen
        if plant_device.device_type == DEVICE_TYPE_CYCLE:
            self._location = {
                "area": None,
                "areas": []  # Liste für alle Member-Areas
            }
        else:
            self._location = {
                "area": None,
                "x": None,
                "y": None
            }

    @property
    def device_info(self) -> dict:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._plant.unique_id)},
        }

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        
        # Stelle letzten Zustand wieder her
        last_state = await self.async_get_last_state()
        if last_state and last_state.state:
            try:
                self._location = json.loads(last_state.state)
                self._attr_native_value = last_state.state
                
                # Stelle sicher, dass Cycles die "areas" Liste haben
                if self._plant.device_type == DEVICE_TYPE_CYCLE and "areas" not in self._location:
                    self._location["areas"] = []
                    self._attr_native_value = json.dumps(self._location)
            except json.JSONDecodeError:
                if self._plant.device_type == DEVICE_TYPE_CYCLE:
                    self._location = {"area": None, "areas": []}
                else:
                    self._location = {"area": None, "x": None, "y": None}
                self._attr_native_value = json.dumps(self._location)
        
        # Registriere Event Listener für Device Registry Updates
        self.async_on_remove(
            self.hass.bus.async_listen("device_registry_updated", self._handle_area_change)
        )
        
        # Initialisiere mit aktuellem Raum
        await self._update_current_area()
        
        # Für Cycles: Initialisiere mit aktuellen Member-Areas
        if self._plant.device_type == DEVICE_TYPE_CYCLE:
            await self._update_member_areas()

    async def _update_current_area(self):
        """Aktualisiere den aktuellen Raum."""
        device_registry = dr.async_get(self._hass)
        area_registry = ar.async_get(self._hass)
        
        # Hole das aktuelle Device
        device = device_registry.async_get_device(
            identifiers={(DOMAIN, self._plant.unique_id)}
        )
        
        if device and device.area_id:
            area = area_registry.async_get_area(device.area_id)
            if area:
                self._location["area"] = area.name
                # Für Cycles: Füge zu areas Liste hinzu wenn noch nicht vorhanden
                if self._plant.device_type == DEVICE_TYPE_CYCLE:
                    if area.name not in self._location.get("areas", []):
                        self._location["areas"] = list(set(self._location.get("areas", []) + [area.name]))
                self._attr_native_value = json.dumps(self._location)
                self.async_write_ha_state()
                
                # Für Cycles: Propagiere die Area zu den Member-Plants
                if self._plant.device_type == DEVICE_TYPE_CYCLE:
                    await self._propagate_area_to_members(device.area_id)

    async def _update_member_areas(self):
        """Aktualisiert die Areas-Liste basierend auf den Member-Plants (nur für Cycles)."""
        if self._plant.device_type != DEVICE_TYPE_CYCLE:
            return
            
        device_registry = dr.async_get(self._hass)
        area_registry = ar.async_get(self._hass)
        areas = []
        
        # Durchlaufe alle Member-Plants
        for plant_id in self._plant._member_plants:
            plant = None
            # Suche die Plant Entity
            for entry_id in self._hass.data[DOMAIN]:
                if ATTR_PLANT in self._hass.data[DOMAIN][entry_id]:
                    if self._hass.data[DOMAIN][entry_id][ATTR_PLANT].entity_id == plant_id:
                        plant = self._hass.data[DOMAIN][entry_id][ATTR_PLANT]
                        break
                        
            if not plant:
                continue
                
            # Hole das Device der Pflanze
            plant_device = device_registry.async_get_device(
                identifiers={(DOMAIN, plant.unique_id)}
            )
            
            if plant_device and plant_device.area_id:
                plant_area = area_registry.async_get_area(plant_device.area_id)
                if plant_area and plant_area.name not in areas:
                    areas.append(plant_area.name)
        
        # Aktualisiere die areas-Liste
        if areas:
            self._location["areas"] = areas
            self._attr_native_value = json.dumps(self._location)
            self.async_write_ha_state()
            
            # Wenn alle Member in der gleichen Area sind, setze diese als Area des Cycles
            if len(areas) == 1 and areas[0] != self._location.get("area"):
                await self._update_device_area(areas[0])

    async def _propagate_area_to_members(self, area_id):
        """Aktualisiert die Area für alle Member-Plants des Cycles."""
        if self._plant.device_type != DEVICE_TYPE_CYCLE or not area_id:
            return
            
        device_registry = dr.async_get(self._hass)
        
        # Durchlaufe alle Member-Plants
        for plant_id in self._plant._member_plants:
            plant = None
            # Suche die Plant Entity
            for entry_id in self._hass.data[DOMAIN]:
                if ATTR_PLANT in self._hass.data[DOMAIN][entry_id]:
                    if self._hass.data[DOMAIN][entry_id][ATTR_PLANT].entity_id == plant_id:
                        plant = self._hass.data[DOMAIN][entry_id][ATTR_PLANT]
                        break
                        
            if not plant:
                continue
                
            # Hole das Device der Pflanze
            plant_device = device_registry.async_get_device(
                identifiers={(DOMAIN, plant.unique_id)}
            )
            
            if plant_device:
                # Aktualisiere die Area des Plant-Devices
                device_registry.async_update_device(
                    plant_device.id,
                    area_id=area_id
                )
                _LOGGER.debug(f"Updated area for member plant {plant_id} to match cycle")

    async def _update_device_area(self, area_name):
        """Aktualisiert die Area des Devices basierend auf dem Area-Namen."""
        device_registry = dr.async_get(self._hass)
        area_registry = ar.async_get(self._hass)
        
        # Finde die Area ID
        area_id = None
        for area in area_registry.async_list_areas():
            if area.name == area_name:
                area_id = area.id
                break
                
        if not area_id:
            return
            
        # Hole das Device
        device = device_registry.async_get_device(
            identifiers={(DOMAIN, self._plant.unique_id)}
        )
        
        if device:
            # Aktualisiere die Area des Devices
            device_registry.async_update_device(
                device.id,
                area_id=area_id
            )
            _LOGGER.debug(f"Updated area for {self._plant.entity_id} to {area_name}")

    @callback
    def _handle_area_change(self, event):
        """Verarbeitet Device Registry Events für Raumänderungen."""
        # Prüfe ob es sich um unser Device handelt
        if event.data.get("action") == "update" and "area_id" in event.data.get("changes", {}):
            device_registry = dr.async_get(self._hass)
            area_registry = ar.async_get(self._hass)
            
            # Hole das aktuelle Device
            device = device_registry.async_get_device(
                identifiers={(DOMAIN, self._plant.unique_id)}
            )
            
            # Prüfe ob es das betroffene Device ist
            if device and device.id == event.data.get("device_id"):
                old_area_name = self._location.get("area")
                
                # Aktualisiere den Raum
                if device.area_id:
                    area = area_registry.async_get_area(device.area_id)
                    if area:
                        self._location["area"] = area.name
                        new_area_name = area.name
                        
                        # Für Cycles: Füge zu areas Liste hinzu, wenn nicht vorhanden
                        if self._plant.device_type == DEVICE_TYPE_CYCLE:
                            if area.name not in self._location.get("areas", []):
                                self._location["areas"] = list(set(self._location.get("areas", []) + [area.name]))
                            
                            # Propagiere Änderung an Member-Plants
                            self._hass.async_create_task(
                                self._propagate_area_to_members(device.area_id)
                            )
                else:
                    self._location["area"] = None
                    new_area_name = None
                
                # Aktualisiere den Wert
                self._attr_native_value = json.dumps(self._location)
                self.async_write_ha_state()
                
                # Löse ein eigenes plant_area_changed Event aus, falls sich die Area geändert hat
                if old_area_name != new_area_name:
                    # Prüfe, ob die Änderung von einem Cycle stammt
                    from_cycle = False
                    cycle_id = None
                    
                    if self._plant.device_type != DEVICE_TYPE_CYCLE:
                        # Prüfe, ob die Pflanze einem Cycle angehört
                        if device.via_device_id:
                            # Suche das Cycle-Device
                            for dev in device_registry.devices.values():
                                if dev.id == device.via_device_id:
                                    # Suche die zugehörige Cycle-Entity
                                    for entry_id in self._hass.data[DOMAIN]:
                                        if ATTR_PLANT in self._hass.data[DOMAIN][entry_id]:
                                            cycle = self._hass.data[DOMAIN][entry_id][ATTR_PLANT]
                                            if (cycle.device_type == DEVICE_TYPE_CYCLE and
                                                cycle.unique_id == next(iter(dev.identifiers))[1]):
                                                from_cycle = True
                                                cycle_id = cycle.entity_id
                                                break
                                    break
                    
                    event_data = {
                        "entity_id": self._plant.entity_id,
                        "device_id": device.id,
                        "old_area": old_area_name,
                        "new_area": new_area_name,
                        "device_type": self._plant.device_type
                    }
                    
                    # Füge Cycle-Informationen hinzu, wenn vorhanden
                    if from_cycle and cycle_id:
                        event_data["from_cycle"] = True
                        event_data["cycle_id"] = cycle_id
                    
                    self._hass.bus.async_fire("plant_area_changed", event_data)
                
                _LOGGER.debug(
                    "Updated location for %s with new area: %s",
                    self._plant.entity_id,
                    self._location["area"]
                )
            
            # Bei Cycle: Prüfe zusätzlich, ob es sich um ein Member-Plant handelt
            elif self._plant.device_type == DEVICE_TYPE_CYCLE:
                # Hole Member-Plant IDs
                for plant_id in self._plant._member_plants:
                    plant = None
                    # Suche die Plant Entity
                    for entry_id in self._hass.data[DOMAIN]:
                        if ATTR_PLANT in self._hass.data[DOMAIN][entry_id]:
                            if self._hass.data[DOMAIN][entry_id][ATTR_PLANT].entity_id == plant_id:
                                plant = self._hass.data[DOMAIN][entry_id][ATTR_PLANT]
                                break
                    
                    if not plant:
                        continue
                    
                    # Hole das Device der Pflanze
                    plant_device = device_registry.async_get_device(
                        identifiers={(DOMAIN, plant.unique_id)}
                    )
                    
                    # Prüfe ob es das betroffene Member-Device ist
                    if plant_device and plant_device.id == event.data.get("device_id"):
                        # Aktualisiere die Member-Areas
                        self._hass.async_create_task(self._update_member_areas())
                        break

    async def async_set_value(self, value: str) -> None:
        """Set new value."""
        try:
            # Validiere JSON
            new_location = json.loads(value)
            if not isinstance(new_location, dict):
                _LOGGER.error("Invalid location format: must be a JSON object")
                return
                
            # Sonderbehandlung für Cycles: Area-Änderung an Device weitergeben
            if self._plant.device_type == DEVICE_TYPE_CYCLE:
                # Prüfe, ob sich die primary area geändert hat
                old_area = self._location.get("area")
                new_area = new_location.get("area")
                
                if new_area != old_area and new_area is not None:
                    await self._update_device_area(new_area)
                
                # Stelle sicher, dass areas Liste vorhanden ist
                if "areas" not in new_location:
                    new_location["areas"] = self._location.get("areas", [])
                
            # Aktualisiere den Wert
            self._location = new_location
            self._attr_native_value = value
            self.async_write_ha_state()
                    
        except json.JSONDecodeError:
            _LOGGER.error("Invalid JSON format for location")

    def add_position(self, x: int, y: int) -> bool:
        """Aktualisiert die Position (nur für Plants)."""
        # Nicht für Cycles
        if self._plant.device_type == DEVICE_TYPE_CYCLE:
            return False
            
        # Konvertiere zu Integer
        x = int(x) if x is not None else None
        y = int(y) if y is not None else None
        
        # Prüfe ob sich die Position geändert hat
        if self._location.get("x") == x and self._location.get("y") == y:
            # Position hat sich nicht geändert
            return False
            
        # Aktualisiere die Position
        self._location["x"] = x
        self._location["y"] = y
        
        # Aktualisiere den Wert
        self._attr_native_value = json.dumps(self._location)
        self.async_write_ha_state()
        
        _LOGGER.debug(
            "Updated location for %s with new position: x=%s, y=%s",
            self._plant.entity_id,
            x,
            y
        )
        
        return True 