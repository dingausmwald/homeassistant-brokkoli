"""Tests for tent-plant integration functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from custom_components.plant import PlantDevice
from custom_components.plant.tent import Tent


class TestTentPlantIntegration:
    """Test tent-plant integration functionality."""

    @pytest.fixture
    def hass(self):
        """Mock Home Assistant instance."""
        return Mock(spec=HomeAssistant)

    @pytest.fixture
    def config_entry(self):
        """Mock config entry."""
        entry = Mock(spec=ConfigEntry)
        entry.data = {
            "plant_info": {
                "name": "Test Plant",
                "device_type": "plant"
            }
        }
        entry.entry_id = "test_entry_id"
        return entry

    @pytest.fixture
    def tent(self):
        """Mock tent instance."""
        tent = Mock(spec=Tent)
        tent.tent_id = "tent_0001"
        tent.name = "Test Tent"
        tent.get_sensors.return_value = ["sensor.temperature", "sensor.humidity"]
        return tent

    def test_assign_tent_success(self, hass, config_entry, tent):
        """Test successful tent assignment to plant."""
        # Create plant device
        plant = PlantDevice(hass, config_entry)
        
        # Mock the replace_sensors method
        plant.replace_sensors = Mock()
        
        # Assign tent to plant
        plant.assign_tent(tent)
        
        # Verify tent was assigned
        assert plant.get_assigned_tent() == tent
        assert plant.get_tent_id() == "tent_0001"
        
        # Verify replace_sensors was called
        tent.get_sensors.assert_called_once()
        plant.replace_sensors.assert_called_once_with(["sensor.temperature", "sensor.humidity"])

    def test_assign_tent_none_raises_error(self, hass, config_entry):
        """Test that assigning None tent raises ValueError."""
        plant = PlantDevice(hass, config_entry)
        
        with pytest.raises(ValueError, match="Tent cannot be None"):
            plant.assign_tent(None)

    def test_change_tent_success(self, hass, config_entry, tent):
        """Test successful tent change for plant."""
        # Create plant device
        plant = PlantDevice(hass, config_entry)
        
        # Mock the replace_sensors method
        plant.replace_sensors = Mock()
        
        # Change tent
        plant.change_tent(tent)
        
        # Verify tent was assigned
        assert plant.get_assigned_tent() == tent
        assert plant.get_tent_id() == "tent_0001"
        
        # Verify replace_sensors was called
        tent.get_sensors.assert_called_once()
        plant.replace_sensors.assert_called_once_with(["sensor.temperature", "sensor.humidity"])

    def test_change_tent_none_raises_error(self, hass, config_entry):
        """Test that changing to None tent raises ValueError."""
        plant = PlantDevice(hass, config_entry)
        
        with pytest.raises(ValueError, match="New tent cannot be None"):
            plant.change_tent(None)

    def test_replace_sensors_with_empty_list(self, hass, config_entry):
        """Test replace_sensors with empty sensor list."""
        plant = PlantDevice(hass, config_entry)
        
        # Mock plant sensors
        plant.sensor_temperature = Mock()
        plant.sensor_humidity = Mock()
        
        # Call replace_sensors with empty list
        plant.replace_sensors([])
        
        # Verify no sensors were replaced
        plant.sensor_temperature.replace_external_sensor.assert_not_called()
        plant.sensor_humidity.replace_external_sensor.assert_not_called()

    @patch('homeassistant.core.StateMachine.get')
    def test_replace_sensors_with_valid_sensors(self, mock_state_get, hass, config_entry):
        """Test replace_sensors with valid sensor list."""
        # Mock sensor states
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
        
        def state_get_side_effect(entity_id):
            if entity_id == "sensor.temperature":
                return temp_sensor_state
            elif entity_id == "sensor.humidity":
                return humidity_sensor_state
            return None
            
        mock_state_get.side_effect = state_get_side_effect
        
        # Create plant device
        plant = PlantDevice(hass, config_entry)
        
        # Mock plant sensors with replace_external_sensor methods
        plant.sensor_temperature = Mock()
        plant.sensor_humidity = Mock()
        plant.sensor_illuminance = Mock()
        plant.sensor_conductivity = Mock()
        plant.sensor_moisture = Mock()
        plant.sensor_CO2 = Mock()
        plant.sensor_power_consumption = Mock()
        plant.sensor_ph = Mock()
        
        # Call replace_sensors with sensor list
        tent_sensors = ["sensor.temperature", "sensor.humidity"]
        plant.replace_sensors(tent_sensors)
        
        # Verify sensors were replaced
        plant.sensor_temperature.replace_external_sensor.assert_called_once_with("sensor.temperature")
        plant.sensor_humidity.replace_external_sensor.assert_called_once_with("sensor.humidity")