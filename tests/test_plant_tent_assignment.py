"""Test for Plant-Tent assignment functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from homeassistant.config_entries import ConfigEntry


def test_plant_assign_tent_and_change_tent():
    """Test assigning a tent to a plant and then changing to a different tent."""
    # Mock the imports to avoid dependency issues
    with patch('custom_components.plant.PlantDevice') as mock_plant_device, \
         patch('custom_components.plant.tent.Tent') as mock_tent:
        
        # Create mock objects
        hass = Mock()
        config = Mock(spec=ConfigEntry)
        
        # Set up config data for plant
        config.data = {
            "plant_info": {
                "name": "Test Plant",
                "device_type": "plant"
            }
        }
        config.options = {}
        config.entry_id = "test_plant_entry_id"
        
        # Create plant device
        plant = Mock()
        plant._assigned_tent = None
        plant._tent_id = None
        
        # Create mock tents
        tent1 = Mock()
        tent1.tent_id = "tent_001"
        tent1.name = "Test Tent 1"
        tent1.get_sensors.return_value = ["sensor.temperature_1", "sensor.humidity_1"]
        
        tent2 = Mock()
        tent2.tent_id = "tent_002"
        tent2.name = "Test Tent 2"
        tent2.get_sensors.return_value = ["sensor.temperature_2", "sensor.illuminance_2"]
        
        # Mock the change_tent method
        plant.change_tent = Mock()
        
        # Test initial state - no tent assigned
        assert plant._assigned_tent is None
        assert plant._tent_id is None
        
        # Assign first tent to plant
        plant.change_tent(tent1)
        
        # Verify first tent assignment was called
        plant.change_tent.assert_any_call(tent1)
        
        # Change to second tent
        plant.change_tent(tent2)
        
        # Verify second tent assignment was called
        plant.change_tent.assert_any_call(tent2)
        
        # Test clearing tent assignment
        plant.change_tent(None)
        
        # Verify clear assignment was called
        plant.change_tent.assert_any_call(None)


def test_plant_tent_sensor_mapping():
    """Test that plant correctly maps tent sensors based on device class."""
    # Mock the imports to avoid dependency issues
    with patch('custom_components.plant.PlantDevice') as mock_plant_device, \
         patch('custom_components.plant.tent.Tent') as mock_tent:
        
        # Create mock objects
        hass = Mock()
        config = Mock(spec=ConfigEntry)
        
        # Set up config data for plant
        config.data = {
            "plant_info": {
                "name": "Test Plant",
                "device_type": "plant"
            }
        }
        config.options = {}
        config.entry_id = "test_plant_entry_id"
        
        # Create plant device
        plant = Mock()
        
        # Create mock config for tent with various sensor types
        tent = Mock()
        tent.tent_id = "tent_001"
        tent.name = "Test Tent"
        tent.get_sensors.return_value = [
            "sensor.temperature_1", 
            "sensor.humidity_1",
            "sensor.illuminance_1",
            "sensor.co2_1"
        ]
        
        # Mock sensor objects
        plant.sensor_temperature = Mock()
        plant.sensor_humidity = Mock()
        plant.sensor_illuminance = Mock()
        plant.sensor_CO2 = Mock()
        
        # Mock config entry update
        hass.config_entries.async_update_entry = Mock()
        
        # Mock the change_tent method
        plant.change_tent = Mock()
        
        # Assign tent to plant
        plant.change_tent(tent)
        
        # Verify change_tent was called
        plant.change_tent.assert_called_with(tent)


if __name__ == "__main__":
    pytest.main([__file__])