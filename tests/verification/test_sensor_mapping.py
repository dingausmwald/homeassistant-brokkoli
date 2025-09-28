#!/usr/bin/env python3
"""
Test script for sensor mapping functionality.
"""

import sys
sys.path.append("D:\\\\Python\\\\2\\\\homeassistant-brokkoli")

import os
from unittest.mock import Mock

# Add the custom_components directory to the path

#sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components'))


from custom_components.plant.const import (
    FLOW_SENSOR_MOISTURE,
    FLOW_SENSOR_CONDUCTIVITY,
    FLOW_SENSOR_ILLUMINANCE,
    FLOW_SENSOR_HUMIDITY,
    FLOW_SENSOR_CO2,
    FLOW_SENSOR_POWER_CONSUMPTION,
    FLOW_SENSOR_PH
)

def test_sensor_mapping():
    """Test the sensor mapping logic."""
    print("Testing sensor mapping logic...")
    
    # Create mock sensor states
    sensor_states = {
        "sensor.temperature": Mock(
            attributes={"device_class": "temperature", "unit_of_measurement": "°C"}
        ),
        "sensor.humidity": Mock(
            attributes={"device_class": "humidity", "unit_of_measurement": "%"}
        ),
        "sensor.soil_moisture": Mock(
            attributes={"device_class": "humidity", "unit_of_measurement": "%"}
        ),
        "sensor.illuminance": Mock(
            attributes={"device_class": "illuminance", "unit_of_measurement": "lx"}
        ),
        "sensor.conductivity": Mock(
            attributes={"device_class": "conductivity", "unit_of_measurement": "µS/cm"}
        ),
        "sensor.co2": Mock(
            attributes={"device_class": "carbon_dioxide", "unit_of_measurement": "ppm"}
        ),
        "sensor.power": Mock(
            attributes={"device_class": "power", "unit_of_measurement": "W"}
        ),
        "sensor.ph": Mock(
            attributes={"device_class": "ph", "unit_of_measurement": "pH"}
        ),
        "sensor.unknown": Mock(
            attributes={"device_class": None, "unit_of_measurement": "unknown"}
        )
    }
    
    # Mock hass.states.get method
    def mock_get_state(entity_id):
        return sensor_states.get(entity_id)
    
    # Test sensor mapping
    sensor_mapping = {}
    tent_sensors = list(sensor_states.keys())
    
    for sensor_entity_id in tent_sensors:
        try:
            sensor_state = mock_get_state(sensor_entity_id)
            if not sensor_state:
                print(f"Sensor {sensor_entity_id} not found")
                continue
        except Exception as e:
            print(f"Error getting sensor {sensor_entity_id}: {e}")
            continue
            
        device_class = sensor_state.attributes.get("device_class")
        unit_of_measurement = sensor_state.attributes.get("unit_of_measurement", "")
        
        print(f"Mapping sensor {sensor_entity_id}: device_class={device_class}, unit_of_measurement={unit_of_measurement}")
        
        # Map to plant sensor types
        if device_class == "temperature" or unit_of_measurement in ["°C", "°F", "K"]:
            sensor_mapping[FLOW_SENSOR_TEMPERATURE] = sensor_entity_id
            print(f"  -> Mapped to temperature sensor")
        elif device_class == "humidity" or unit_of_measurement == "%":
            # Check if it's air humidity or soil moisture based on entity name
            if "soil" in sensor_entity_id.lower() or "moisture" in sensor_entity_id.lower():
                sensor_mapping[FLOW_SENSOR_MOISTURE] = sensor_entity_id
                print(f"  -> Mapped to moisture sensor")
            else:
                sensor_mapping[FLOW_SENSOR_HUMIDITY] = sensor_entity_id
                print(f"  -> Mapped to humidity sensor")
        elif device_class == "illuminance" or unit_of_measurement in ["lx", "lux"]:
            sensor_mapping[FLOW_SENSOR_ILLUMINANCE] = sensor_entity_id
            print(f"  -> Mapped to illuminance sensor")
        elif device_class == "conductivity" or unit_of_measurement == "µS/cm":
            sensor_mapping[FLOW_SENSOR_CONDUCTIVITY] = sensor_entity_id
            print(f"  -> Mapped to conductivity sensor")
        elif device_class == "carbon_dioxide" or "co2" in sensor_entity_id.lower() or unit_of_measurement == "ppm":
            sensor_mapping[FLOW_SENSOR_CO2] = sensor_entity_id
            print(f"  -> Mapped to CO2 sensor")
        elif device_class == "power" or "power" in sensor_entity_id.lower() or unit_of_measurement in ["W", "kW"]:
            sensor_mapping[FLOW_SENSOR_POWER_CONSUMPTION] = sensor_entity_id
            print(f"  -> Mapped to power consumption sensor")
        elif device_class == "ph" or "ph" in sensor_entity_id.lower() or unit_of_measurement.lower() in ["ph", "pH"]:
            sensor_mapping[FLOW_SENSOR_PH] = sensor_entity_id
            print(f"  -> Mapped to pH sensor")
        else:
            print(f"  -> Could not map sensor")
    
    print(f"\nFinal sensor mapping: {sensor_mapping}")
    
    # Verify all expected sensors are mapped
    expected_mappings = {
        FLOW_SENSOR_TEMPERATURE: "sensor.temperature",
        FLOW_SENSOR_HUMIDITY: "sensor.humidity",
        FLOW_SENSOR_MOISTURE: "sensor.soil_moisture",
        FLOW_SENSOR_ILLUMINANCE: "sensor.illuminance",
        FLOW_SENSOR_CONDUCTIVITY: "sensor.conductivity",
        FLOW_SENSOR_CO2: "sensor.co2",
        FLOW_SENSOR_POWER_CONSUMPTION: "sensor.power",
        FLOW_SENSOR_PH: "sensor.ph"
    }
    
    print("\nVerifying mappings:")
    for sensor_key, expected_entity in expected_mappings.items():
        if sensor_key in sensor_mapping and sensor_mapping[sensor_key] == expected_entity:
            print(f"✓ {sensor_key} -> {expected_entity}")
        else:
            print(f"✗ {sensor_key} -> Expected: {expected_entity}, Got: {sensor_mapping.get(sensor_key, 'None')}")

if __name__ == "__main__":
    test_sensor_mapping()