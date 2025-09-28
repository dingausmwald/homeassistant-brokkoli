"""Text entities for tent integration."""
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

from .const import (
    ATTR_PLANT,
    DOMAIN,
    DEVICE_TYPE_TENT,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the tent text entities."""
    tent = hass.data[DOMAIN][entry.entry_id][ATTR_PLANT]
    
    # Only set up text entities for tents
    if tent.device_type != DEVICE_TYPE_TENT:
        return
        
    entities = []
    
    # Journal for tents
    journal = TentJournal(hass, entry, tent)
    entities.append(journal)
    tent.add_journal_text_entity(journal)
    
    # Maintenance for tents
    maintenance = TentMaintenance(hass, entry, tent)
    entities.append(maintenance)
    tent.add_maintenance_text_entity(maintenance)
    
    async_add_entities(entities)

class TentJournal(TextEntity, RestoreEntity):
    """Representation of a tent journal text entity."""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry, tent_device) -> None:
        """Initialize the tent journal."""
        self._attr_native_value = ""
        self._attr_mode = "text"
        self._config = config
        self._hass = hass
        self._tent = tent_device
        self._attr_name = f"{tent_device.name} Journal"
        self._attr_unique_id = f"{config.entry_id}-journal"
        # Journal is not a diagnostic entity
        self._attr_entity_category = None
        self._attr_icon = "mdi:notebook"

    @property
    def device_info(self) -> dict:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._tent.unique_id)},
        }

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        
        # Restore last state
        last_state = await self.async_get_last_state()
        if last_state and last_state.state:
            self._attr_native_value = last_state.state

    async def async_set_value(self, value: str) -> None:
        """Set new value."""
        self._attr_native_value = value
        self.async_write_ha_state()
        
        # Add journal entry to tent
        if self._tent:
            from .tent import JournalEntry
            entry = JournalEntry(value, "User")
            self._tent.add_journal_entry(entry)

class TentMaintenance(TextEntity, RestoreEntity):
    """Representation of a tent maintenance text entity."""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry, tent_device) -> None:
        """Initialize the tent maintenance."""
        self._attr_native_value = ""
        self._attr_mode = "text"
        self._config = config
        self._hass = hass
        self._tent = tent_device
        self._attr_name = f"{tent_device.name} Maintenance"
        self._attr_unique_id = f"{config.entry_id}-maintenance"
        # Maintenance is not a diagnostic entity
        self._attr_entity_category = None
        self._attr_icon = "mdi:toolbox"

    @property
    def device_info(self) -> dict:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._tent.unique_id)},
        }

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        
        # Restore last state
        last_state = await self.async_get_last_state()
        if last_state and last_state.state:
            self._attr_native_value = last_state.state

    async def async_set_value(self, value: str) -> None:
        """Set new value."""
        self._attr_native_value = value
        self.async_write_ha_state()
        
        # Add maintenance entry to tent
        if self._tent:
            from .tent import MaintenanceEntry, JournalEntry
            # Create maintenance entry
            entry = MaintenanceEntry(value, "User")
            self._tent.add_maintenance_entry(entry)
            
            # Also add to journal
            journal_entry = JournalEntry(f"Maintenance performed: {value}", "System")
            self._tent.add_journal_entry(journal_entry)