"""Tent class for managing sensors in Home Assistant plant integration."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import Entity
from homeassistant.helpers import device_registry as dr
from homeassistant.const import ATTR_NAME, STATE_OK

from .const import (
    DOMAIN, 
    FLOW_PLANT_INFO, 
    DEVICE_TYPE_TENT,
    FLOW_SENSOR_TEMPERATURE,
    FLOW_SENSOR_MOISTURE,
    FLOW_SENSOR_CONDUCTIVITY,
    FLOW_SENSOR_ILLUMINANCE,
    FLOW_SENSOR_HUMIDITY,
    FLOW_SENSOR_CO2,
    FLOW_SENSOR_POWER_CONSUMPTION,
    FLOW_SENSOR_PH,
)

_LOGGER = logging.getLogger(__name__)


class JournalEntry:
    """Represents a single journal entry."""

    def __init__(self, content: str, author: str = "System") -> None:
        """Initialize the journal entry."""
        self.timestamp = datetime.now()
        self.content = content
        self.author = author

    def to_dict(self) -> dict:
        """Convert journal entry to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "content": self.content,
            "author": self.author,
        }

    @classmethod
    def from_dict(cls, data: dict) -> JournalEntry:
        """Create journal entry from dictionary."""
        entry = cls(data["content"], data.get("author", "System"))
        entry.timestamp = datetime.fromisoformat(data["timestamp"])
        return entry


class Journal:
    """Represents a journal for documenting events."""

    def __init__(self) -> None:
        """Initialize the journal."""
        self.entries: List[JournalEntry] = []

    def add_entry(self, entry: JournalEntry) -> None:
        """Add an entry to the journal."""
        self.entries.append(entry)

    def get_entries(self) -> List[JournalEntry]:
        """Get all journal entries."""
        return self.entries.copy()

    def to_dict(self) -> dict:
        """Convert journal to dictionary."""
        return {
            "entries": [entry.to_dict() for entry in self.entries]
        }

    @classmethod
    def from_dict(cls, data: dict) -> Journal:
        """Create journal from dictionary."""
        journal = cls()
        if data:
            journal.entries = [JournalEntry.from_dict(entry_data) for entry_data in data.get("entries", [])]
        return journal


class MaintenanceEntry:
    """Represents a maintenance entry."""

    def __init__(self, description: str, performed_by: str = "System", cost: float = 0.0) -> None:
        """Initialize the maintenance entry."""
        self.timestamp = datetime.now()
        self.description = description
        self.performed_by = performed_by
        self.cost = cost

    def to_dict(self) -> dict:
        """Convert maintenance entry to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "description": self.description,
            "performed_by": self.performed_by,
            "cost": self.cost,
        }

    @classmethod
    def from_dict(cls, data: dict) -> MaintenanceEntry:
        """Create maintenance entry from dictionary."""
        entry = cls(
            data["description"],
            data.get("performed_by", "System"),
            data.get("cost", 0.0)
        )
        entry.timestamp = datetime.fromisoformat(data["timestamp"])
        return entry


class Tent(Entity):
    """Representation of a Tent that manages sensors."""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry) -> None:
        """Initialize the Tent."""
        self._hass = hass
        self._config = config
        plant_info = config.data.get(FLOW_PLANT_INFO, {})
        self._tent_id = plant_info.get("tent_id")
        self._name = plant_info.get("name", plant_info.get(ATTR_NAME, "Unnamed Tent"))
        # List of sensor entity IDs; if not present, derive from typed keys for backward compatibility
        self._sensors: List[str] = plant_info.get("sensors", [])
        if not self._sensors:
            derived_sensors: List[str] = []
            # Look for sensors stored with the new key format (FLOW_SENSOR_*)
            for key in (
                FLOW_SENSOR_TEMPERATURE,
                FLOW_SENSOR_MOISTURE,
                FLOW_SENSOR_CONDUCTIVITY,
                FLOW_SENSOR_ILLUMINANCE,
                FLOW_SENSOR_HUMIDITY,
                FLOW_SENSOR_CO2,
                FLOW_SENSOR_POWER_CONSUMPTION,
                FLOW_SENSOR_PH,
            ):
                sensor_id = plant_info.get(key)
                if sensor_id:
                    derived_sensors.append(sensor_id)
            # Also check for backward compatibility with old key format
            if not derived_sensors:
                for key in (
                    "temperature_sensor",
                    "moisture_sensor",
                    "conductivity_sensor",
                    "illuminance_sensor",
                    "humidity_sensor",
                    "co2_sensor",
                    "power_consumption_sensor",
                    "ph_sensor",
                ):
                    sensor_id = plant_info.get(key)
                    if sensor_id:
                        derived_sensors.append(sensor_id)
            if derived_sensors:
                self._sensors = derived_sensors
        self._journal = Journal.from_dict(plant_info.get("journal", {}))
        self._maintenance_entries: List[MaintenanceEntry] = []
        
        # Text entities for journal and maintenance
        self._journal_text_entity = None
        self._maintenance_text_entity = None
        
        # Load maintenance entries from config
        maintenance_data = plant_info.get("maintenance_entries", [])
        for entry_data in maintenance_data:
            self._maintenance_entries.append(MaintenanceEntry.from_dict(entry_data))
            
        created_at_str = plant_info.get("created_at", datetime.now().isoformat())
        updated_at_str = plant_info.get("updated_at", datetime.now().isoformat())
        
        try:
            self._created_at = datetime.fromisoformat(created_at_str)
        except ValueError:
            self._created_at = datetime.now()
            
        try:
            self._updated_at = datetime.fromisoformat(updated_at_str)
        except ValueError:
            self._updated_at = datetime.now()
            
        # Initialize device_id from config or generate it
        self._device_id = plant_info.get("device_id")
        if self._device_id is None:
            # Generate device ID if not present
            device_registry = dr.async_get(self._hass)
            device = device_registry.async_get_device(
                identifiers={(DOMAIN, self.unique_id)}
            )
            if device:
                self._device_id = device.id

    @property
    def device_type(self) -> str:
        """Return the device type."""
        return DEVICE_TYPE_TENT

    @property
    def device_id(self) -> str:
        """The device ID used for all the entities"""
        return self._device_id

    @property
    def tent_id(self) -> str:
        """Return the tent ID."""
        return self._tent_id

    @property
    def name(self) -> str:
        """Return the name of the tent."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return a unique ID for the tent."""
        if self._tent_id is None:
            return f"tent_unnamed"
        return f"tent_{self._tent_id}"

    @property
    def state(self) -> str:
        """Return the state of the tent."""
        return STATE_OK

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        # Format maintenance entries for display
        maintenance_list = []
        for entry in self._maintenance_entries:
            maintenance_list.append({
                "timestamp": entry.timestamp.isoformat(),
                "description": entry.description,
                "performed_by": entry.performed_by,
                "cost": entry.cost,
            })
        
        # Format journal entries for display
        journal_list = []
        for entry in self._journal.entries:
            journal_list.append({
                "timestamp": entry.timestamp.isoformat(),
                "content": entry.content,
                "author": entry.author,
            })
        
        # Get sensor details
        sensor_details = []
        for sensor_id in self._sensors:
            # Try to get sensor state from Home Assistant
            sensor_state = None
            try:
                state = self._hass.states.get(sensor_id)
                if state:
                    sensor_state = {
                        "state": state.state,
                        "unit": state.attributes.get("unit_of_measurement", ""),
                        "device_class": state.attributes.get("device_class", ""),
                    }
            except Exception:
                pass
            
            sensor_details.append({
                "entity_id": sensor_id,
                "state": sensor_state,
            })
        
        return {
            "tent_id": self._tent_id,
            "sensors": self._sensors,
            "sensor_details": sensor_details,
            "maintenance_entries": maintenance_list,
            "journal_entries": journal_list,
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
            "sensor_count": len(self._sensors),
            "maintenance_count": len(self._maintenance_entries),
            "journal_entry_count": len(self._journal.entries),
        }

    @property
    def device_info(self) -> dict:
        """Return device information about the tent."""
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "manufacturer": "Home Assistant",
            "model": "Tent",
        }

    def add_sensor(self, sensor_entity_id: str) -> None:
        """Add a sensor to this tent."""
        if sensor_entity_id not in self._sensors:
            self._sensors.append(sensor_entity_id)
            self._updated_at = datetime.now()
            self._update_config()

    def remove_sensor(self, sensor_entity_id: str) -> None:
        """Remove a sensor from this tent."""
        if sensor_entity_id in self._sensors:
            self._sensors.remove(sensor_entity_id)
            self._updated_at = datetime.now()
            self._update_config()

    def get_sensors(self) -> List[str]:
        """Get all sensors associated with this tent."""
        return self._sensors.copy()

    def add_journal_entry(self, entry: JournalEntry) -> None:
        """Add a journal entry to this tent."""
        self._journal.add_entry(entry)
        self._updated_at = datetime.now()
        self._update_config()

    def get_journal(self) -> Journal:
        """Get the journal for this tent."""
        return self._journal

    def add_maintenance_entry(self, entry: MaintenanceEntry) -> None:
        """Add a maintenance entry to this tent."""
        self._maintenance_entries.append(entry)
        self._updated_at = datetime.now()
        self._update_config()

    def get_maintenance_entries(self) -> List[MaintenanceEntry]:
        """Get all maintenance entries for this tent."""
        return self._maintenance_entries.copy()

    def assign_to_plant(self, plant) -> None:
        """Assign this tent's sensors to a plant."""
        plant.replace_sensors(self._sensors)

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

    def _update_config(self) -> None:
        """Update the config entry with current tent data."""
        if not self._config:
            return
            
        data = dict(self._config.data)
        plant_info = dict(data.get(FLOW_PLANT_INFO, {}))
        # Persist tent attributes inside FLOW_PLANT_INFO to be consistent with loader
        plant_info["sensors"] = self._sensors
        plant_info["journal"] = self._journal.to_dict()
        plant_info["maintenance_entries"] = [entry.to_dict() for entry in self._maintenance_entries]
        plant_info["updated_at"] = self._updated_at.isoformat()
        plant_info["device_id"] = self._device_id  # Persist device_id
        data[FLOW_PLANT_INFO] = plant_info
        
        # Update the config entry
        self._hass.config_entries.async_update_entry(self._config, data=data)

    def to_dict(self) -> dict:
        """Convert tent to dictionary for storage."""
        return {
            "tent_id": self._tent_id,
            "name": self._name,
            "sensors": self._sensors,
            "journal": self._journal.to_dict(),
            "maintenance_entries": [entry.to_dict() for entry in self._maintenance_entries],
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
        }

    def add_journal_text_entity(self, entity) -> None:
        """Add the journal text entity."""
        self._journal_text_entity = entity

    def add_maintenance_text_entity(self, entity) -> None:
        """Add the maintenance text entity."""
        self._maintenance_text_entity = entity

    def add_journal(self, journal) -> None:
        """Add journal entity (for compatibility with plant text setup)."""
        self._journal_text_entity = journal

    def add_maintenance_select(self, maintenance_select) -> None:
        """Add maintenance select entity."""
        # This method can be used to store a reference to the maintenance select entity if needed
        pass


    @classmethod
    def from_dict(cls, hass: HomeAssistant, data: dict) -> Tent:
        """Create tent from dictionary."""
        # This would be used for loading tents from storage
        pass