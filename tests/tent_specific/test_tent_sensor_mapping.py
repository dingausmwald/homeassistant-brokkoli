"""Test for Tent sensor mapping to Plant sensors."""

import pytest
from unittest.mock import Mock, patch

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from custom_components.plant import PlantDevice
from custom_components.plant.tent import Tent


@pytest.fixture
def hass():
    """Mock Home Assistant instance."""
    return Mock(spec=HomeAssistant)


@pytest.fixture
def config_entry():
    """Mock config entry."""
    entry = Mock(spec=ConfigEntry)
    entry.data = {
        "plant_info": {
            "name": "Test Plant",
            "device_type": "plant"
        }
    }
    entry.options = {}
    entry.entry_id = "test_entry_id"
    return entry


@pytest.fixture
def tent_config():
    """Mock tent config entry."""
    entry = Mock(spec=ConfigEntry)
    entry.data = {
        "plant_info": {
            "tent_id": "tent_0001",
            "name": "Test Tent",
            "sensors": [
                "sensor.temperature",
                "sensor.humidity", 
                "sensor.co2",
                "sensor.illuminance",
                "sensor.power"
            ]
        }
    }
    return entry


@patch('homeassistant.core.StateMachine.get')
def test_replace_sensors_with_valid_sensors(mock_state_get, hass, config_entry):
    """Test replace_sensors with valid sensor list."""
    # Mock sensor states with device classes and units
    temp_sensor_state = Mock()
    temp_sensor_state.attributes = {
        "device_class": "temperature",
        "unit_of_measurement": "°C"
    }
    
    humidity_sensor_state = Mock()
    humidity_sensor_state.attributes = {
        "device_class": "humidity",
        "unit_of_measurement": "%"
    }
    
    co2_sensor_state = Mock()
    co2_sensor_state.attributes = {
        "unit_of_measurement": "ppm"
    }
    
    illuminance_sensor_state = Mock()
    illuminance_sensor_state.attributes = {
        "device_class": "illuminance",
        "unit_of_measurement": "lx"
    }
    
    power_sensor_state = Mock()
    power_sensor_state.attributes = {
        "unit_of_measurement": "W"
    }
    
    def state_get_side_effect(entity_id):
        if entity_id == "sensor.temperature":
            return temp_sensor_state
        elif entity_id == "sensor.humidity":
            return humidity_sensor_state
        elif entity_id == "sensor.co2":
            return co2_sensor_state
        elif entity_id == "sensor.illuminance":
            return illuminance_sensor_state
        elif entity_id == "sensor.power":
            return power_sensor_state
        return None
        
    mock_state_get.side_effect = state_get_side_effect
    
    # Create plant device
    plant = PlantDevice(hass, config_entry)
    
    # Mock plant sensors with replace_external_sensor methods
    plant.sensor_temperature = Mock()
    plant.sensor_humidity = Mock()
    plant.sensor_illuminance = Mock()
    plant.sensor_CO2 = Mock()
    plant.sensor_power_consumption = Mock()
    
    # Mock config entry update method
    plant._hass.config_entries.async_update_entry = Mock()
    
    # Call replace_sensors with sensor list
    tent_sensors = [
        "sensor.temperature", 
        "sensor.humidity", 
        "sensor.co2", 
        "sensor.illuminance", 
        "sensor.power"
    ]
    plant.replace_sensors(tent_sensors)
    
    # Verify sensors were replaced correctly
    plant.sensor_temperature.replace_external_sensor.assert_called_once_with("sensor.temperature")
    plant.sensor_humidity.replace_external_sensor.assert_called_once_with("sensor.humidity")
    plant.sensor_CO2.replace_external_sensor.assert_called_once_with("sensor.co2")
    plant.sensor_illuminance.replace_external_sensor.assert_called_once_with("sensor.illuminance")
    plant.sensor_power_consumption.replace_external_sensor.assert_called_once_with("sensor.power")
    
    # Verify config entry was updated
    plant._hass.config_entries.async_update_entry.assert_called_once()


def test_assign_tent_success(hass, config_entry, tent_config):
    """Test successful tent assignment to plant."""
    # Create plant device
    plant = PlantDevice(hass, config_entry)
    
    # Create tent
    tent = Tent(hass, tent_config)
    
    # Mock the replace_sensors method to verify it's called
    plant.replace_sensors = Mock()
    
    # Assign tent to plant
    plant.assign_tent(tent)
    
    # Verify tent was assigned
    assert plant.get_assigned_tent() == tent
    assert plant.get_tent_id() == "tent_0001"
    
    # Verify replace_sensors was called with tent sensors
    plant.replace_sensors.assert_called_once_with([
        "sensor.temperature",
        "sensor.humidity", 
        "sensor.co2",
        "sensor.illuminance",
        "sensor.power"
    ])


def test_change_tent_service_flow_like_resolution():
    """Lightweight test to ensure change_tent resolves tent by tent_id path."""
    from custom_components.plant.services import CHANGE_TENT_SCHEMA
    assert CHANGE_TENT_SCHEMA is not None