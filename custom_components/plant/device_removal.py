"""Device removal for Brokkoli Plant Manager."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_remove_stale_devices(hass: HomeAssistant) -> None:
    """Remove stale devices from the plant integration."""
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    
    # Get all devices for the plant domain
    plant_devices = dr.async_entries_for_config_domain(device_registry, DOMAIN)
    
    for device in plant_devices:
        # Check if the device has any entities
        device_entities = er.async_entries_for_device(entity_registry, device.id)
        
        # If the device has no entities, it might be stale
        if not device_entities:
            _LOGGER.info("Removing stale device %s (%s) with no entities", device.name, device.id)
            device_registry.async_remove_device(device.id)
            continue
            
        # Check if the device's config entry still exists
        config_entry_exists = False
        for config_entry_id in device.config_entries:
            if hass.config_entries.async_get_entry(config_entry_id):
                config_entry_exists = True
                break
                
        # If no config entry exists for this device, it's stale
        if not config_entry_exists:
            _LOGGER.info("Removing stale device %s (%s) with no config entry", device.name, device.id)
            device_registry.async_remove_device(device.id)


async def async_check_and_remove_stale_device(hass: HomeAssistant, device_id: str) -> bool:
    """Check if a specific device is stale and remove it if it is.
    
    Returns True if the device was removed, False otherwise.
    """
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    
    device = device_registry.async_get(device_id)
    if not device:
        # Device doesn't exist, nothing to do
        return False
    
    # Check if this is a plant domain device
    if device.identifiers and not any(identifier[0] == DOMAIN for identifier in device.identifiers):
        # Not a plant device, don't remove
        return False
    
    # Check if the device has any entities
    device_entities = er.async_entries_for_device(entity_registry, device.id)
    
    # Check if the device's config entry still exists
    config_entry_exists = False
    for config_entry_id in device.config_entries:
        if hass.config_entries.async_get_entry(config_entry_id):
            config_entry_exists = True
            break
    
    # If the device has no entities and no config entry, it's stale
    if not device_entities and not config_entry_exists:
        _LOGGER.info("Removing stale device %s (%s)", device.name, device.id)
        device_registry.async_remove_device(device.id)
        return True
    
    return False


async def async_cleanup_orphaned_entities(hass: HomeAssistant) -> None:
    """Clean up entities that are no longer associated with valid devices."""
    entity_registry = er.async_get(hass)
    
    # Get all entities for the plant domain
    plant_entities = [
        entity for entity in entity_registry.entities.values()
        if entity.platform == DOMAIN
    ]
    
    for entity in plant_entities:
        # Check if the entity's device still exists
        if entity.device_id:
            device_registry = dr.async_get(hass)
            device = device_registry.async_get(entity.device_id)
            if not device:
                # Device doesn't exist, remove the entity
                _LOGGER.info("Removing orphaned entity %s with missing device", entity.entity_id)
                entity_registry.async_remove(entity.entity_id)


async def async_validate_and_cleanup_devices(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Validate and cleanup devices associated with a config entry."""
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    
    # Get all devices for this config entry
    config_entry_devices = dr.async_entries_for_config_entry(device_registry, config_entry.entry_id)
    
    for device in config_entry_devices:
        # Check if the device has any entities
        device_entities = er.async_entries_for_device(entity_registry, device.id)
        
        # If the device has no entities, consider removing it
        if not device_entities:
            # Check if this is a plant, tent, or cycle device
            is_plant_device = False
            if device.identifiers:
                for identifier in device.identifiers:
                    if identifier[0] == DOMAIN:
                        is_plant_device = True
                        break
            
            if is_plant_device:
                _LOGGER.info("Device %s (%s) has no entities, considering for removal", device.name, device.id)
                # In a real implementation, we might want to confirm with the user before removing
                # For now, we'll log and leave it for manual cleanup