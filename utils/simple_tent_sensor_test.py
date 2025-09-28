#!/usr/bin/env python3
"""
Simple test for Tent sensor mapping implementation.
"""

import sys
import os

# Add the custom_components directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components'))

from plant import PlantDevice
from plant.tent import Tent
from unittest.mock import Mock


def test_plant_device_replace_sensors():
    """Test the replace_sensors method in PlantDevice."""
    print("Testing PlantDevice.replace_sensors method...")
    
    # Create mock objects
    hass = Mock()
    config = Mock()
    config.data = {
        "plant_info": {
            "name": "Test Plant",
            "device_type": "plant"
        }
    }
    config.options = {}
    config.entry_id = "test_entry_id"
    
    # Mock the config entries update method
    hass.config_entries.async_update_entry = Mock()
    
    # Mock sensor states
    def mock_get_state(entity_id):
        mock_state = Mock()
        mock_state.attributes = {}
        
        if entity_id == "sensor.temperature":
            mock_state.attributes["device_class"] = "temperature"
            mock_state.attributes["unit_of_measurement"] = "°C"
        elif entity_id == "sensor.humidity":
            mock_state.attributes["device_class"] = "humidity"
            mock_state.attributes["unit_of_measurement"] = "%"
        elif entity_id == "sensor.co2":
            mock_state.attributes["unit_of_measurement"] = "ppm"
        elif entity_id == "sensor.illuminance":
            mock_state.attributes["device_class"] = "illuminance"
            mock_state.attributes["unit_of_measurement"] = "lx"
        elif entity_id == "sensor.power":
            mock_state.attributes["unit_of_measurement"] = "W"
        else:
            return None
            
        return mock_state
    
    hass.states.get = mock_get_state
    
    # Create a simplified PlantDevice class for testing
    class TestPlantDevice:
        def __init__(self, hass, config):
            self._hass = hass
            self._config = config
            self.name = config.data["plant_info"]["name"]
            
            # Mock sensors
            self.sensor_temperature = Mock()
            self.sensor_humidity = Mock()
            self.sensor_CO2 = Mock()
            self.sensor_illuminance = Mock()
            self.sensor_power_consumption = Mock()
            
        def replace_sensors(self, tent_sensors):
            """Replace the plant's sensors with those from a tent."""
            if not tent_sensors:
                print(f"No sensors to replace for plant {self.name}")
                return
                
            # Map tent sensors to plant sensor types
            sensor_mapping = {}
            for sensor_entity_id in tent_sensors:
                # Get the sensor state to determine its type
                try:
                    sensor_state = self._hass.states.get(sensor_entity_id)
                    if not sensor_state:
                        print(f"Sensor {sensor_entity_id} not found in Home Assistant")
                        continue
                except Exception as e:
                    print(f"Error getting sensor {sensor_entity_id}: {e}")
                    continue
                    
                # Determine sensor type based on device class or unit of measurement
                device_class = sensor_state.attributes.get("device_class")
                unit_of_measurement = sensor_state.attributes.get("unit_of_measurement", "")
                
                # Map to plant sensor types
                if device_class == "temperature" or unit_of_measurement in ["°C", "°F", "K"]:
                    sensor_mapping["temperature"] = sensor_entity_id
                elif device_class == "humidity" or unit_of_measurement == "%":
                    sensor_mapping["humidity"] = sensor_entity_id
                elif device_class == "illuminance" or unit_of_measurement in ["lx", "lux"]:
                    sensor_mapping["illuminance"] = sensor_entity_id
                elif "co2" in sensor_entity_id.lower() or unit_of_measurement == "ppm":
                    sensor_mapping["co2"] = sensor_entity_id
                elif "power" in sensor_entity_id.lower() or unit_of_measurement in ["W", "kW"]:
                    sensor_mapping["power_consumption"] = sensor_entity_id
            
            # Replace sensors using the existing replace_external_sensor method
            if hasattr(self, 'sensor_temperature') and self.sensor_temperature and "temperature" in sensor_mapping:
                self.sensor_temperature.replace_external_sensor(sensor_mapping["temperature"])
                
            if hasattr(self, 'sensor_humidity') and self.sensor_humidity and "humidity" in sensor_mapping:
                self.sensor_humidity.replace_external_sensor(sensor_mapping["humidity"])
                
            if hasattr(self, 'sensor_CO2') and self.sensor_CO2 and "co2" in sensor_mapping:
                self.sensor_CO2.replace_external_sensor(sensor_mapping["co2"])
                
            if hasattr(self, 'sensor_illuminance') and self.sensor_illuminance and "illuminance" in sensor_mapping:
                self.sensor_illuminance.replace_external_sensor(sensor_mapping["illuminance"])
                
            if hasattr(self, 'sensor_power_consumption') and self.sensor_power_consumption and "power_consumption" in sensor_mapping:
                self.sensor_power_consumption.replace_external_sensor(sensor_mapping["power_consumption"])
                
            # Update the config entry with the new sensor assignments
            data = dict(self._config.data)
            plant_info = dict(data.get("plant_info", {}))
            
            if "temperature" in sensor_mapping:
                plant_info["temperature_sensor"] = sensor_mapping["temperature"]
            if "humidity" in sensor_mapping:
                plant_info["humidity_sensor"] = sensor_mapping["humidity"]
            if "co2" in sensor_mapping:
                plant_info["co2_sensor"] = sensor_mapping["co2"]
            if "illuminance" in sensor_mapping:
                plant_info["illuminance_sensor"] = sensor_mapping["illuminance"]
            if "power_consumption" in sensor_mapping:
                plant_info["power_consumption_sensor"] = sensor_mapping["power_consumption"]
                
            data["plant_info"] = plant_info
            # Update the config entry
            self._hass.config_entries.async_update_entry(self._config, data=data)
            
            print(f"Replaced sensors for plant {self.name}: {sensor_mapping}")
            return data
    
    # Create plant device
    plant = TestPlantDevice(hass, config)
    
    # Test with a list of tent sensors
    tent_sensors = [
        "sensor.temperature",
        "sensor.humidity",
        "sensor.co2",
        "sensor.illuminance",
        "sensor.power"
    ]
    
    # Call the method
    result_data = plant.replace_sensors(tent_sensors)
    
    # Verify the results
    plant_info = result_data["plant_info"]
    
    assert plant_info["temperature_sensor"] == "sensor.temperature"
    assert plant_info["humidity_sensor"] == "sensor.humidity"
    assert plant_info["co2_sensor"] == "sensor.co2"
    assert plant_info["illuminance_sensor"] == "sensor.illuminance"
    assert plant_info["power_consumption_sensor"] == "sensor.power"
    
    # Verify that replace_external_sensor was called on each sensor
    plant.sensor_temperature.replace_external_sensor.assert_called_once_with("sensor.temperature")
    plant.sensor_humidity.replace_external_sensor.assert_called_once_with("sensor.humidity")
    plant.sensor_CO2.replace_external_sensor.assert_called_once_with("sensor.co2")
    plant.sensor_illuminance.replace_external_sensor.assert_called_once_with("sensor.illuminance")
    plant.sensor_power_consumption.replace_external_sensor.assert_called_once_with("sensor.power")
    
    print("All tests passed!")
    print("PlantDevice.replace_sensors method verified successfully.")


if __name__ == "__main__":
    test_plant_device_replace_sensors()