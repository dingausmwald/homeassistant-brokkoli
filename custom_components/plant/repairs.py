"""Repairs for Brokkoli Plant Manager."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant import data_entry_flow
from homeassistant.components.repairs import RepairsFlow
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_create_issue(
    hass: HomeAssistant,
    issue_id: str,
    translation_key: str,
    *,
    translation_placeholders: dict[str, str] | None = None,
    severity: str = ir.IssueSeverity.WARNING,
) -> None:
    """Create an issue for the plant integration."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=True,
        severity=severity,
        translation_key=translation_key,
        translation_placeholders=translation_placeholders,
    )


async def async_delete_issue(hass: HomeAssistant, issue_id: str) -> None:
    """Remove an issue for the plant integration."""
    ir.async_delete_issue(hass, DOMAIN, issue_id)


class SensorUnavailabilityRepairFlow(RepairsFlow):
    """Handler for sensor unavailability repair flow."""

    def __init__(self, issue_id: str, data: dict[str, str]) -> None:
        """Initialize the repair flow."""
        self._issue_id = issue_id
        self._data = data

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the first step of repair flow."""
        if user_input is not None:
            # User has acknowledged the issue
            # In a real implementation, we might try to fix the sensor issue here
            _LOGGER.info("User acknowledged sensor unavailability issue: %s", self._data)
            
            # Remove the issue
            await async_delete_issue(self.hass, self._issue_id)
            
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=None,
            description_placeholders=self._data,
        )


class InvalidConfigurationRepairFlow(RepairsFlow):
    """Handler for invalid configuration repair flow."""

    def __init__(self, issue_id: str, data: dict[str, str]) -> None:
        """Initialize the repair flow."""
        self._issue_id = issue_id
        self._data = data

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the first step of repair flow."""
        if user_input is not None:
            # User has acknowledged the issue
            _LOGGER.info("User acknowledged invalid configuration issue: %s", self._data)
            
            # Remove the issue
            await async_delete_issue(self.hass, self._issue_id)
            
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=None,
            description_placeholders=self._data,
        )


class MissingSensorRepairFlow(RepairsFlow):
    """Handler for missing sensor repair flow."""

    def __init__(self, issue_id: str, data: dict[str, str]) -> None:
        """Initialize the repair flow."""
        self._issue_id = issue_id
        self._data = data

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the first step of repair flow."""
        if user_input is not None:
            # User has acknowledged the issue
            _LOGGER.info("User acknowledged missing sensor issue: %s", self._data)
            
            # Remove the issue
            await async_delete_issue(self.hass, self._issue_id)
            
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=None,
            description_placeholders=self._data,
        )


async def async_create_sensor_unavailability_issue(
    hass: HomeAssistant, plant_name: str, sensor_type: str
) -> None:
    """Create a sensor unavailability issue."""
    issue_id = f"sensor_unavailable_{plant_name}_{sensor_type}"
    
    await async_create_issue(
        hass,
        issue_id,
        "sensor_unavailable",
        translation_placeholders={
            "plant_name": plant_name,
            "sensor_type": sensor_type,
        },
        severity=ir.IssueSeverity.WARNING,
    )


async def async_create_invalid_configuration_issue(
    hass: HomeAssistant, plant_name: str, error: str
) -> None:
    """Create an invalid configuration issue."""
    issue_id = f"invalid_configuration_{plant_name}"
    
    await async_create_issue(
        hass,
        issue_id,
        "invalid_configuration",
        translation_placeholders={
            "plant_name": plant_name,
            "error": error,
        },
        severity=ir.IssueSeverity.ERROR,
    )


async def async_create_missing_sensor_issue(
    hass: HomeAssistant, plant_name: str, sensor_type: str
) -> None:
    """Create a missing sensor issue."""
    issue_id = f"missing_sensor_{plant_name}_{sensor_type}"
    
    await async_create_issue(
        hass,
        issue_id,
        "missing_sensor",
        translation_placeholders={
            "plant_name": plant_name,
            "sensor_type": sensor_type,
        },
        severity=ir.IssueSeverity.WARNING,
    )