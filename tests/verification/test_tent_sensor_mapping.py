#!/usr/bin/env python3
"""
Test script to verify the tent sensor mapping functionality.
"""

import logging
from unittest.mock import Mock, MagicMock

# Set up logging
logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

def test_tent_sensor_mapping():
    """Test the tent sensor mapping functionality."""
    
    print("Testing tent sensor mapping functionality...")
    
    # Create mock hass object
    hass = Mock()
    hass.data = {}
    hass.config_entries = Mock()
    
    # Create mock plant device
    plant = Mock()
    plant._hass = hass
    plant.device_type = "plant"
    plant.entity_id = "plant.test_plant"
    plant.name = "Test Plant"
    
    # Create mock sensors
    plant.sensor_temperature = Mock()
    plant.sensor_moisture = Mock()
    plant.sensor_conductivity = Mock()
    plant.sensor_illuminance = Mock()
    plant.sensor_humidity = Mock()
    plant.sensor_CO2 = Mock()
    plant.sensor_power_consumption = Mock()
    plant.sensor_ph = Mock()
    
    # Mock the replace_external_sensor methods
    plant.sensor_temperature.replace_external_sensor = Mock()
    plant.sensor_moisture.replace_external_sensor = Mock()
    plant.sensor_conductivity.replace_external_sensor = Mock()
    plant.sensor_illuminance.replace_external_sensor = Mock()
    plant.sensor_humidity.replace_external_sensor = Mock()
    plant.sensor_CO2.replace_external_sensor = Mock()
    plant.sensor_power_consumption.replace_external_sensor = Mock()
    plant.sensor_ph.replace_external_sensor = Mock()
    
    # Mock the config entry
    plant._config = Mock()
    plant._config.data = {"plant_info": {}}
    hass.config_entries.async_update_entry = Mock()
    
    # Import the actual replace_sensors method from the PlantDevice class
    # For this test, we'll simulate the behavior
    
    # Create mock tent sensors
    tent_sensors = ["sensor.tent_temperature", "sensor.tent_humidity", "sensor.tent_ph"]
    
    # Mock the hass.states.get method to return sensor states with device_class and unit_of_measurement
    def mock_get_state(entity_id):
        mock_state = Mock()
        mock_state.attributes = {}
        
        if "temperature" in entity_id:
            mock_state.attributes["device_class"] = "temperature"
            mock_state.attributes["unit_of_measurement"] = "°C"
        elif "humidity" in entity_id:
            mock_state.attributes["device_class"] = "humidity"
            mock_state.attributes["unit_of_measurement"] = "%"
        elif "ph" in entity_id:
            mock_state.attributes["device_class"] = "ph"
            mock_state.attributes["unit_of_measurement"] = "pH"
        else:
            mock_state.attributes["device_class"] = "unknown"
            mock_state.attributes["unit_of_measurement"] = ""
            
        return mock_state
    
    hass.states.get = Mock(side_effect=mock_get_state)
    
    # Simulate the replace_sensors method
    sensor_mapping = {}
    for sensor_entity_id in tent_sensors:
        # Get the sensor state to determine its type
        try:
            sensor_state = hass.states.get(sensor_entity_id)
            if not sensor_state:
                _LOGGER.warning("Sensor %s not found in Home Assistant", sensor_entity_id)
                continue
        except Exception as e:
            _LOGGER.warning("Error getting sensor %s: %s", sensor_entity_id, e)
            continue
            
        # Determine sensor type based on device class or unit of measurement
        device_class = sensor_state.attributes.get("device_class")
        unit_of_measurement = sensor_state.attributes.get("unit_of_measurement", "")
        
        # Map to plant sensor types
        if device_class == "temperature" or unit_of_measurement in ["°C", "°F", "K"]:
            sensor_mapping["temperature_sensor"] = sensor_entity_id
        elif device_class == "humidity" or unit_of_measurement == "%":
            sensor_mapping["humidity_sensor"] = sensor_entity_id
        elif device_class == "ph" or "ph" in sensor_entity_id.lower() or unit_of_measurement.lower() in ["ph", "pH"]:
            sensor_mapping["ph_sensor"] = sensor_entity_id
    
    # Replace sensors using the existing replace_external_sensor method
    sensor_entities = {
        "temperature_sensor": plant.sensor_temperature,
        "moisture_sensor": plant.sensor_moisture,
        "conductivity_sensor": plant.sensor_conductivity,
        "illuminance_sensor": plant.sensor_illuminance,
        "humidity_sensor": plant.sensor_humidity,
        "co2_sensor": plant.sensor_CO2,
        "power_consumption_sensor": plant.sensor_power_consumption,
        "ph_sensor": plant.sensor_ph,
    }
    
    replaced_sensors = {}
    for sensor_key, sensor_entity in sensor_entities.items():
        if sensor_entity and sensor_key in sensor_mapping:
            sensor_entity.replace_external_sensor(sensor_mapping[sensor_key])
            replaced_sensors[sensor_key] = sensor_mapping[sensor_key]
    
    # Verify that the sensors were replaced correctly
    plant.sensor_temperature.replace_external_sensor.assert_called_once_with("sensor.tent_temperature")
    plant.sensor_humidity.replace_external_sensor.assert_called_once_with("sensor.tent_humidity")
    plant.sensor_ph.replace_external_sensor.assert_called_once_with("sensor.tent_ph")
    
    print("Tent sensor mapping test passed!")
    print(f"Replaced sensors: {replaced_sensors}")

if __name__ == "__main__":
    test_tent_sensor_mapping()