"""Test for Tent configuration flow."""

import pytest
from unittest.mock import Mock, patch
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from custom_components.plant.config_flow import PlantConfigFlow
from custom_components.plant.const import DEVICE_TYPE_TENT


def test_get_available_tents():
    """Test getting available tents."""
    flow = PlantConfigFlow()
    tents = flow._get_available_tents()
    # For now, this returns an empty list as we haven't implemented tent storage
    assert tents == []


def test_tent_step():
    """Test the tent configuration step."""
    flow = PlantConfigFlow()
    
    # Mock the hass attribute
    flow.hass = Mock(spec=HomeAssistant)
    
    # Mock the _async_current_entries method
    flow._async_current_entries = Mock(return_value=[])
    
    # Test the tent step with no user input
    result = flow.async_step_tent(user_input=None)
    
    # Check that it returns a form
    assert result["type"] == "form"
    assert result["step_id"] == "tent"


def test_tent_step_with_input():
    """Test the tent configuration step with user input."""
    flow = PlantConfigFlow()
    
    # Mock the hass attribute
    flow.hass = Mock(spec=HomeAssistant)
    
    # Mock the _async_current_entries method
    flow._async_current_entries = Mock(return_value=[])
    
    # Mock the async_create_entry method
    flow.async_create_entry = Mock(return_value={"type": "create_entry"})
    
    # Test the tent step with user input
    user_input = {
        "name": "Test Tent",
        "plant_emoji": "⛺"
    }
    
    result = flow.async_step_tent(user_input=user_input)
    
    # Check that it creates an entry
    assert result["type"] == "create_entry"
    flow.async_create_entry.assert_called_once()


def test_user_step_with_tent_selection():
    """Test the user step when tent is selected."""
    flow = PlantConfigFlow()
    
    # Mock the hass attribute
    flow.hass = Mock(spec=HomeAssistant)
    
    # Mock the _async_current_entries method
    flow._async_current_entries = Mock(return_value=[])
    
    # Mock the async_step_tent method
    flow.async_step_tent = Mock(return_value={"type": "form", "step_id": "tent"})
    
    # Test the user step with tent device type
    user_input = {
        "device_type": DEVICE_TYPE_TENT
    }
    
    result = flow.async_step_user(user_input=user_input)
    
    # Check that it calls the tent step
    flow.async_step_tent.assert_called_once()
    assert result["step_id"] == "tent"


if __name__ == "__main__":
    pytest.main([__file__])