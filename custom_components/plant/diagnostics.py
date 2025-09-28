"""Diagnostics support for Brokkoli Plant Manager."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

# Data that should be redacted from diagnostics
TO_REDACT = {
    "latitude",
    "longitude",
    "elevation",
    "address",
    "device_id",
    "entity_id",
    "unique_id",
    "device_identifiers",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    plant_data = {}
    
    # Get plant data from hass.data
    if DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]:
        plant_info = hass.data[DOMAIN][config_entry.entry_id]
        if "plant" in plant_info:
            plant = plant_info["plant"]
            plant_data = {
                "device_type": getattr(plant, "device_type", "unknown"),
                "name": getattr(plant, "name", "unknown"),
                "entity_id": getattr(plant, "entity_id", "unknown"),
                "unique_id": getattr(plant, "unique_id", "unknown"),
                "state": getattr(plant, "state", "unknown"),
                "extra_state_attributes": getattr(plant, "extra_state_attributes", {}),
                "device_info": getattr(plant, "device_info", {}),
            }
    
    # Get sensor data
    sensor_data = {}
    if DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]:
        if "sensors" in hass.data[DOMAIN][config_entry.entry_id]:
            sensors = hass.data[DOMAIN][config_entry.entry_id]["sensors"]
            sensor_data = {
                "count": len(sensors),
                "entities": [
                    {
                        "entity_id": getattr(sensor, "entity_id", "unknown"),
                        "name": getattr(sensor, "name", "unknown"),
                        "state": getattr(sensor, "state", "unknown"),
                        "unit_of_measurement": getattr(sensor, "unit_of_measurement", None),
                        "device_class": getattr(sensor, "device_class", None),
                    }
                    for sensor in sensors
                ],
            }
    
    # Get threshold data
    threshold_data = {}
    if DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]:
        if "thresholds" in hass.data[DOMAIN][config_entry.entry_id]:
            thresholds = hass.data[DOMAIN][config_entry.entry_id]["thresholds"]
            threshold_data = {
                "count": len(thresholds),
                "entities": [
                    {
                        "entity_id": getattr(threshold, "entity_id", "unknown"),
                        "name": getattr(threshold, "name", "unknown"),
                        "state": getattr(threshold, "state", "unknown"),
                        "min": getattr(threshold, "min", None),
                        "max": getattr(threshold, "max", None),
                    }
                    for threshold in thresholds
                ],
            }
    
    diagnostics_data = {
        "config_entry": {
            "entry_id": config_entry.entry_id,
            "version": config_entry.version,
            "domain": config_entry.domain,
            "title": config_entry.title,
            "data": dict(config_entry.data),
            "options": dict(config_entry.options),
            "pref_disable_new_entities": config_entry.pref_disable_new_entities,
            "pref_disable_polling": config_entry.pref_disable_polling,
            "source": config_entry.source,
            "state": config_entry.state,
            "supports_unload": config_entry.supports_unload,
        },
        "plant": plant_data,
        "sensors": sensor_data,
        "thresholds": threshold_data,
    }
    
    return async_redact_data(diagnostics_data, TO_REDACT)


async def async_get_device_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry, device
) -> dict[str, Any]:
    """Return diagnostics for a device."""
    # For now, we'll return the same data as config entry diagnostics
    # In a more complete implementation, we would filter by device
    return await async_get_config_entry_diagnostics(hass, config_entry)