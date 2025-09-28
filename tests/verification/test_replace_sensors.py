#!/usr/bin/env python3
"""
Test script to verify the replace_sensors implementation for the PlantDevice class.
"""

import logging
from unittest.mock import Mock, MagicMock

# Set up logging
logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

def test_replace_sensors_implementation():
    """Test the replace_sensors method implementation."""
    
    # Create mock plant device
    plant = Mock()
    plant._hass = Mock()
    plant._config = Mock()
    plant._config.data = {"plant_info": {}}
    
    # Create mock sensors
    plant.sensor_temperature = Mock()
    plant.sensor_moisture = Mock()
    plant.sensor_conductivity = Mock()
    plant.sensor_illuminance = Mock()
    plant.sensor_humidity = Mock()
    plant.sensor_CO2 = Mock()
    plant.sensor_power_consumption = Mock()
    plant.sensor_ph = Mock()
    
    # Mock the hass.states.get method to return sensor states with device_class and unit_of_measurement
    def mock_get_state(entity_id):
        mock_state = Mock()
        mock_state.attributes = {}
        
        if "temperature" in entity_id:
            mock_state.attributes["device_class"] = "temperature"
            mock_state.attributes["unit_of_measurement"] = "°C"
        elif "moisture" in entity_id and "soil" in entity_id:
            mock_state.attributes["device_class"] = "humidity"
            mock_state.attributes["unit_of_measurement"] = "%"
        elif "humidity" in entity_id:
            mock_state.attributes["device_class"] = "humidity"
            mock_state.attributes["unit_of_measurement"] = "%"
        elif "illuminance" in entity_id or "lux" in entity_id:
            mock_state.attributes["device_class"] = "illuminance"
            mock_state.attributes["unit_of_measurement"] = "lx"
        elif "conductivity" in entity_id:
            mock_state.attributes["device_class"] = "conductivity"
            mock_state.attributes["unit_of_measurement"] = "µS/cm"
        elif "co2" in entity_id:
            mock_state.attributes["unit_of_measurement"] = "ppm"
        elif "power" in entity_id:
            mock_state.attributes["unit_of_measurement"] = "W"
        elif "ph" in entity_id:
            mock_state.attributes["unit_of_measurement"] = "pH"
            
        return mock_state
    
    plant._hass.states.get = mock_get_state
    
    # Define the replace_sensors method
    def replace_sensors(tent_sensors: list) -> None:
        """Replace the plant's sensors with those from a tent.
        
        Args:
            tent_sensors: List of sensor entity IDs from the tent
        """
        # Map tent sensors to plant sensor types
        sensor_mapping = {}
        for sensor_entity_id in tent_sensors:
            # Get the sensor state to determine its type
            sensor_state = plant._hass.states.get(sensor_entity_id)
            if not sensor_state:
                _LOGGER.warning("Sensor %s not found in Home Assistant", sensor_entity_id)
                continue
                
            # Determine sensor type based on device class or unit of measurement
            device_class = sensor_state.attributes.get("device_class")
            unit_of_measurement = sensor_state.attributes.get("unit_of_measurement", "")
            
            # Map to plant sensor types
            if device_class == "temperature" or unit_of_measurement in ["°C", "°F", "K"]:
                sensor_mapping["temperature"] = sensor_entity_id
            elif device_class == "humidity" or unit_of_measurement == "%":
                # Check if it's air humidity or soil moisture based on entity name
                if "soil" in sensor_entity_id.lower() or "moisture" in sensor_entity_id.lower():
                    sensor_mapping["moisture"] = sensor_entity_id
                else:
                    sensor_mapping["humidity"] = sensor_entity_id
            elif device_class == "illuminance" or unit_of_measurement in ["lx", "lux"]:
                sensor_mapping["illuminance"] = sensor_entity_id
            elif device_class == "conductivity" or unit_of_measurement == "µS/cm":
                sensor_mapping["conductivity"] = sensor_entity_id
            elif "co2" in sensor_entity_id.lower() or unit_of_measurement == "ppm":
                sensor_mapping["co2"] = sensor_entity_id
            elif "power" in sensor_entity_id.lower() or unit_of_measurement in ["W", "kW"]:
                sensor_mapping["power_consumption"] = sensor_entity_id
            elif "ph" in sensor_entity_id.lower() or unit_of_measurement in ["pH", "ph"]:
                sensor_mapping["ph"] = sensor_entity_id
        
        # Replace sensors using the existing replace_external_sensor method
        if hasattr(plant, 'sensor_temperature') and plant.sensor_temperature and "temperature" in sensor_mapping:
            plant.sensor_temperature.replace_external_sensor.assert_not_called()
            plant.sensor_temperature.replace_external_sensor(sensor_mapping["temperature"])
            
        if hasattr(plant, 'sensor_moisture') and plant.sensor_moisture and "moisture" in sensor_mapping:
            plant.sensor_moisture.replace_external_sensor.assert_not_called()
            plant.sensor_moisture.replace_external_sensor(sensor_mapping["moisture"])
            
        if hasattr(plant, 'sensor_conductivity') and plant.sensor_conductivity and "conductivity" in sensor_mapping:
            plant.sensor_conductivity.replace_external_sensor.assert_not_called()
            plant.sensor_conductivity.replace_external_sensor(sensor_mapping["conductivity"])
            
        if hasattr(plant, 'sensor_illuminance') and plant.sensor_illuminance and "illuminance" in sensor_mapping:
            plant.sensor_illuminance.replace_external_sensor.assert_not_called()
            plant.sensor_illuminance.replace_external_sensor(sensor_mapping["illuminance"])
            
        if hasattr(plant, 'sensor_humidity') and plant.sensor_humidity and "humidity" in sensor_mapping:
            plant.sensor_humidity.replace_external_sensor.assert_not_called()
            plant.sensor_humidity.replace_external_sensor(sensor_mapping["humidity"])
            
        if hasattr(plant, 'sensor_CO2') and plant.sensor_CO2 and "co2" in sensor_mapping:
            plant.sensor_CO2.replace_external_sensor.assert_not_called()
            plant.sensor_CO2.replace_external_sensor(sensor_mapping["co2"])
            
        if hasattr(plant, 'sensor_power_consumption') and plant.sensor_power_consumption and "power_consumption" in sensor_mapping:
            plant.sensor_power_consumption.replace_external_sensor.assert_not_called()
            plant.sensor_power_consumption.replace_external_sensor(sensor_mapping["power_consumption"])
            
        if hasattr(plant, 'sensor_ph') and plant.sensor_ph and "ph" in sensor_mapping:
            plant.sensor_ph.replace_external_sensor.assert_not_called()
            plant.sensor_ph.replace_external_sensor(sensor_mapping["ph"])
            
        # Update the config entry with the new sensor assignments
        data = dict(plant._config.data)
        plant_info = dict(data.get("plant_info", {}))
        
        if "temperature" in sensor_mapping:
            plant_info["temperature_sensor"] = sensor_mapping["temperature"]
        if "moisture" in sensor_mapping:
            plant_info["moisture_sensor"] = sensor_mapping["moisture"]
        if "conductivity" in sensor_mapping:
            plant_info["conductivity_sensor"] = sensor_mapping["conductivity"]
        if "illuminance" in sensor_mapping:
            plant_info["illuminance_sensor"] = sensor_mapping["illuminance"]
        if "humidity" in sensor_mapping:
            plant_info["humidity_sensor"] = sensor_mapping["humidity"]
        if "co2" in sensor_mapping:
            plant_info["co2_sensor"] = sensor_mapping["co2"]
        if "power_consumption" in sensor_mapping:
            plant_info["power_consumption_sensor"] = sensor_mapping["power_consumption"]
        if "ph" in sensor_mapping:
            plant_info["ph_sensor"] = sensor_mapping["ph"]
            
        data["plant_info"] = plant_info
        # In real implementation: plant._hass.config_entries.async_update_entry(plant._config, data=data)
        
        return data
    
    # Test with a list of tent sensors
    tent_sensors = [
        "sensor.tent_temperature",
        "sensor.tent_soil_moisture",
        "sensor.tent_conductivity",
        "sensor.tent_illuminance",
        "sensor.tent_humidity",
        "sensor.tent_co2",
        "sensor.tent_power",
        "sensor.tent_ph"
    ]
    
    # Call the method
    result_data = replace_sensors(tent_sensors)
    
    # Verify the results
    plant_info = result_data["plant_info"]
    
    assert plant_info["temperature_sensor"] == "sensor.tent_temperature"
    assert plant_info["moisture_sensor"] == "sensor.tent_soil_moisture"
    assert plant_info["conductivity_sensor"] == "sensor.tent_conductivity"
    assert plant_info["illuminance_sensor"] == "sensor.tent_illuminance"
    assert plant_info["humidity_sensor"] == "sensor.tent_humidity"
    assert plant_info["co2_sensor"] == "sensor.tent_co2"
    assert plant_info["power_consumption_sensor"] == "sensor.tent_power"
    assert plant_info["ph_sensor"] == "sensor.tent_ph"
    
    # Verify that replace_external_sensor was called on each sensor
    plant.sensor_temperature.replace_external_sensor.assert_called_once_with("sensor.tent_temperature")
    plant.sensor_moisture.replace_external_sensor.assert_called_once_with("sensor.tent_soil_moisture")
    plant.sensor_conductivity.replace_external_sensor.assert_called_once_with("sensor.tent_conductivity")
    plant.sensor_illuminance.replace_external_sensor.assert_called_once_with("sensor.tent_illuminance")
    plant.sensor_humidity.replace_external_sensor.assert_called_once_with("sensor.tent_humidity")
    plant.sensor_CO2.replace_external_sensor.assert_called_once_with("sensor.tent_co2")
    plant.sensor_power_consumption.replace_external_sensor.assert_called_once_with("sensor.tent_power")
    plant.sensor_ph.replace_external_sensor.assert_called_once_with("sensor.tent_ph")
    
    print("All tests passed!")

if __name__ == "__main__":
    test_replace_sensors_implementation()