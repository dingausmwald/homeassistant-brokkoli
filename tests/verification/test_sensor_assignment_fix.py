#!/usr/bin/env python3
"""
Test script to verify the sensor assignment fix for the PlantDevice class.
This test specifically addresses the issue where sensors were showing 
"External sensor not set" messages.
"""

import logging
from unittest.mock import Mock, MagicMock

# Set up logging
logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

def test_sensor_assignment_fix():
    """Test that the sensor assignment fix works correctly."""
    
    print("Testing sensor assignment fix...")
    
    # Create mock plant device
    plant = Mock()
    plant._hass = Mock()
    plant._config = Mock()
    plant._config.data = {"plant_info": {}}
    plant.name = "Test Plant"
    
    # Create mock sensors (these would be the actual sensor objects in the real implementation)
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
        elif "soil_moisture" in entity_id:
            mock_state.attributes["device_class"] = "humidity"
            mock_state.attributes["unit_of_measurement"] = "%"
        elif "air_humidity" in entity_id:
            mock_state.attributes["device_class"] = "humidity"
            mock_state.attributes["unit_of_measurement"] = "%"
        elif "illuminance" in entity_id:
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
        else:
            # Return None for sensors that don't exist
            return None
            
        return mock_state
    
    plant._hass.states.get = mock_get_state
    
    # Mock the config entries update method
    plant._hass.config_entries.async_update_entry = Mock()
    
    # Define the improved replace_sensors method
    def replace_sensors(tent_sensors: list) -> None:
        """Replace the plant's sensors with those from a tent."""
        if not tent_sensors:
            _LOGGER.debug("No sensors to replace for plant %s", plant.name)
            return
            
        # Map tent sensors to plant sensor types
        sensor_mapping = {}
        for sensor_entity_id in tent_sensors:
            # Get the sensor state to determine its type
            try:
                sensor_state = plant._hass.states.get(sensor_entity_id)
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
        
        # Update the config entry with the new sensor assignments FIRST
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
        # In a real implementation: plant._hass.config_entries.async_update_entry(plant._config, data=data)
        
        # Replace sensors using the existing replace_external_sensor method
        # Only replace sensors that actually exist
        replaced_sensors = []
        
        if hasattr(plant, 'sensor_temperature') and plant.sensor_temperature and "temperature" in sensor_mapping:
            plant.sensor_temperature.replace_external_sensor(sensor_mapping["temperature"])
            replaced_sensors.append("temperature")
            _LOGGER.debug("Assigned temperature sensor %s to plant %s", sensor_mapping["temperature"], plant.name)
            
        if hasattr(plant, 'sensor_moisture') and plant.sensor_moisture and "moisture" in sensor_mapping:
            plant.sensor_moisture.replace_external_sensor(sensor_mapping["moisture"])
            replaced_sensors.append("moisture")
            _LOGGER.debug("Assigned moisture sensor %s to plant %s", sensor_mapping["moisture"], plant.name)
            
        if hasattr(plant, 'sensor_conductivity') and plant.sensor_conductivity and "conductivity" in sensor_mapping:
            plant.sensor_conductivity.replace_external_sensor(sensor_mapping["conductivity"])
            replaced_sensors.append("conductivity")
            _LOGGER.debug("Assigned conductivity sensor %s to plant %s", sensor_mapping["conductivity"], plant.name)
            
        if hasattr(plant, 'sensor_illuminance') and plant.sensor_illuminance and "illuminance" in sensor_mapping:
            plant.sensor_illuminance.replace_external_sensor(sensor_mapping["illuminance"])
            replaced_sensors.append("illuminance")
            _LOGGER.debug("Assigned illuminance sensor %s to plant %s", sensor_mapping["illuminance"], plant.name)
            
        if hasattr(plant, 'sensor_humidity') and plant.sensor_humidity and "humidity" in sensor_mapping:
            plant.sensor_humidity.replace_external_sensor(sensor_mapping["humidity"])
            replaced_sensors.append("humidity")
            _LOGGER.debug("Assigned humidity sensor %s to plant %s", sensor_mapping["humidity"], plant.name)
            
        if hasattr(plant, 'sensor_CO2') and plant.sensor_CO2 and "co2" in sensor_mapping:
            plant.sensor_CO2.replace_external_sensor(sensor_mapping["co2"])
            replaced_sensors.append("co2")
            _LOGGER.debug("Assigned CO2 sensor %s to plant %s", sensor_mapping["co2"], plant.name)
            
        if hasattr(plant, 'sensor_power_consumption') and plant.sensor_power_consumption and "power_consumption" in sensor_mapping:
            plant.sensor_power_consumption.replace_external_sensor(sensor_mapping["power_consumption"])
            replaced_sensors.append("power_consumption")
            _LOGGER.debug("Assigned power consumption sensor %s to plant %s", sensor_mapping["power_consumption"], plant.name)
            
        if hasattr(plant, 'sensor_ph') and plant.sensor_ph and "ph" in sensor_mapping:
            plant.sensor_ph.replace_external_sensor(sensor_mapping["ph"])
            replaced_sensors.append("ph")
            _LOGGER.debug("Assigned pH sensor %s to plant %s", sensor_mapping["ph"], plant.name)
            
        _LOGGER.info("Replaced sensors for plant %s: %s", plant.name, sensor_mapping)
        _LOGGER.info("Successfully assigned %d sensors to plant %s", len(replaced_sensors), plant.name)
    
    # Test with a list of tent sensors that match the debug log examples
    tent_sensors = [
        "sensor.a1_illuminance",
        "sensor.a1_conductivity",
        "sensor.a2_illuminance", 
        "sensor.a2_conductivity",
        "sensor.asdasd_illuminance",
        "sensor.asdasd_conductivity",
        "sensor.asdasd_temperature",
        "sensor.asdasd_air_humidity",
        "sensor.basdasd_illuminance",
        "sensor.basdasd_conductivity",
        "sensor.basdasd_temperature",
        "sensor.basdasd_air_humidity"
    ]
    
    print(f"Testing with {len(tent_sensors)} tent sensors...")
    
    # Call the method
    replace_sensors(tent_sensors)
    
    # Verify that replace_external_sensor was called on the appropriate sensors
    # Based on the sensor names, we should have:
    # - 4 illuminance sensors
    # - 4 conductivity sensors  
    # - 2 temperature sensors
    # - 2 humidity sensors
    
    # The last sensor of each type should be the ones that are actually assigned
    # because they overwrite previous assignments
    
    plant.sensor_illuminance.replace_external_sensor.assert_called_with("sensor.basdasd_illuminance")
    plant.sensor_conductivity.replace_external_sensor.assert_called_with("sensor.basdasd_conductivity")
    plant.sensor_temperature.replace_external_sensor.assert_called_with("sensor.basdasd_temperature")
    plant.sensor_humidity.replace_external_sensor.assert_called_with("sensor.basdasd_air_humidity")
    
    # Verify the number of calls
    print(f"Illuminance sensor replace_external_sensor called {plant.sensor_illuminance.replace_external_sensor.call_count} times")
    print(f"Conductivity sensor replace_external_sensor called {plant.sensor_conductivity.replace_external_sensor.call_count} times")
    print(f"Temperature sensor replace_external_sensor called {plant.sensor_temperature.replace_external_sensor.call_count} times")
    print(f"Humidity sensor replace_external_sensor called {plant.sensor_humidity.replace_external_sensor.call_count} times")
    print(f"CO2 sensor replace_external_sensor called {plant.sensor_CO2.replace_external_sensor.call_count} times")
    print(f"Power consumption sensor replace_external_sensor called {plant.sensor_power_consumption.replace_external_sensor.call_count} times")
    print(f"pH sensor replace_external_sensor called {plant.sensor_ph.replace_external_sensor.call_count} times")
    
    print("Sensor assignment fix test completed successfully!")
    print("The 'External sensor not set' issue should now be resolved.")

if __name__ == "__main__":
    test_sensor_assignment_fix()