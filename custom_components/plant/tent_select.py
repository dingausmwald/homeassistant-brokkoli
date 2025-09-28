"""Select entity for tent maintenance."""
from __future__ import annotations

import logging
from datetime import datetime
import asyncio

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    ATTR_PLANT,
    DOMAIN,
    DEVICE_TYPE_TENT,
)

_LOGGER = logging.getLogger(__name__)

# Predefined maintenance options for tents
MAINTENANCE_OPTIONS = [
    "Check ventilation",
    "Clean filters",
    "Replace bulbs",
    "Check water levels",
    "Inspect for pests",
    "Adjust humidity",
    "Calibrate sensors",
    "Clean reservoir",
    "Check pH levels",
    "Refill nutrients",
    "Inspect roots",
    "Prune plants",
    "Check drainage",
    "Replace growing medium",
    "Sanitize equipment",
    "Update journal",
]

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the tent maintenance select entity."""
    tent = hass.data[DOMAIN][entry.entry_id][ATTR_PLANT]
    
    # Only set up maintenance select for tents
    if tent.device_type != DEVICE_TYPE_TENT:
        return
        
    maintenance_select = TentMaintenanceSelect(hass, entry, tent)
    async_add_entities([maintenance_select])

class TentMaintenanceSelect(SelectEntity, RestoreEntity):
    """Representation of a tent maintenance selector."""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry, tent_device) -> None:
        """Initialize the tent maintenance select entity."""
        self._attr_options = MAINTENANCE_OPTIONS
        self._attr_current_option = ""  # Empty option as default
        self._config = config
        self._hass = hass
        self._tent = tent_device
        self._attr_name = f"{tent_device.name} Maintenance"
        self._attr_unique_id = f"{config.entry_id}-tent-maintenance"
        
        # Initialize basic attributes
        self._attr_extra_state_attributes = {
            "friendly_name": self._attr_name
        }

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
        if last_state:
            self._attr_current_option = last_state.state if last_state.state != "None" else ""

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if not option:  # If empty option selected
            self._attr_current_option = ""
            self.async_write_ha_state()
            return

        self._attr_current_option = option
        self.async_write_ha_state()

        _LOGGER.debug(
            "Selected maintenance %s for %s",
            option,
            self._tent.entity_id
        )

        # Add maintenance entry to tent
        if self._tent:
            from .tent import MaintenanceEntry, JournalEntry
            # Create maintenance entry
            entry = MaintenanceEntry(option, "User")
            self._tent.add_maintenance_entry(entry)
            
            # Also add to journal
            journal_entry = JournalEntry(f"Maintenance performed: {option}", "System")
            self._tent.add_journal_entry(journal_entry)

        # Reset to empty option after 2 seconds
        async def reset_maintenance():
            await asyncio.sleep(2)
            self._attr_current_option = ""
            self.async_write_ha_state()

        # Start the reset timer
        asyncio.create_task(reset_maintenance())