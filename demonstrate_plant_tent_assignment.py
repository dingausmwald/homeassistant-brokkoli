#!/usr/bin/env python3
"""
Demonstration script showing how a Plant can receive a Tent entity 
and easily change tents in the Home Assistant Brokkoli integration.
"""

from unittest.mock import Mock


def demonstrate_plant_tent_assignment():
    """Demonstrate assigning a tent to a plant and changing tents."""
    print("=== Plant-Tent Assignment Demonstration ===\n")
    
    # Create mock objects to simulate the Home Assistant environment
    hass = Mock()
    plant = Mock()
    plant._assigned_tent = None
    plant._tent_id = None
    
    # Create mock tents
    tent1 = Mock()
    tent1.tent_id = "tent_001"
    tent1.name = "Grow Tent 1"
    tent1.get_sensors.return_value = [
        "sensor.temperature_1", 
        "sensor.humidity_1",
        "sensor.illuminance_1"
    ]
    
    tent2 = Mock()
    tent2.tent_id = "tent_002"
    tent2.name = "Grow Tent 2"
    tent2.get_sensors.return_value = [
        "sensor.temperature_2", 
        "sensor.co2_2",
        "sensor.illuminance_2"
    ]
    
    # Mock the change_tent method to show what it does
    def change_tent(tent_entity):
        """Simulate the change_tent method from PlantDevice class."""
        plant._assigned_tent = tent_entity
        plant._tent_id = tent_entity.tent_id if tent_entity else None
        
        if tent_entity:
            print(f"Assigned plant to tent: {tent_entity.name} (ID: {tent_entity.tent_id})")
            sensors = tent_entity.get_sensors()
            print(f"  Inheriting sensors: {sensors}")
        else:
            print("Cleared tent assignment")
    
    plant.change_tent = change_tent
    
    # Demonstrate the functionality
    print("1. Initial state:")
    print(f"   Assigned tent: {plant._assigned_tent}")
    print(f"   Tent ID: {plant._tent_id}\n")
    
    print("2. Assigning first tent to plant:")
    plant.change_tent(tent1)
    print(f"   Assigned tent: {plant._assigned_tent.name}")
    print(f"   Tent ID: {plant._tent_id}\n")
    
    print("3. Changing to second tent:")
    plant.change_tent(tent2)
    print(f"   Assigned tent: {plant._assigned_tent.name}")
    print(f"   Tent ID: {plant._tent_id}\n")
    
    print("4. Clearing tent assignment:")
    plant.change_tent(None)
    print(f"   Assigned tent: {plant._assigned_tent}")
    print(f"   Tent ID: {plant._tent_id}\n")
    
    print("=== Demonstration Complete ===")


def demonstrate_sensor_mapping():
    """Demonstrate how tent sensors are mapped to plant sensors."""
    print("\n=== Sensor Mapping Demonstration ===\n")
    
    # Create mock objects
    hass = Mock()
    plant = Mock()
    
    # Create a mock tent with various sensor types
    tent = Mock()
    tent.tent_id = "tent_001"
    tent.name = "Main Grow Tent"
    tent.get_sensors.return_value = [
        "sensor.temperature_main",      # Temperature sensor
        "sensor.humidity_main",         # Air humidity sensor
        "sensor.soil_moisture_main",    # Soil moisture sensor
        "sensor.illuminance_main",      # Light sensor
        "sensor.co2_main",              # CO2 sensor
        "sensor.power_main",            # Power consumption sensor
        "sensor.ph_main",               # pH sensor
    ]
    
    # Mock plant sensor objects
    plant.sensor_temperature = Mock()
    plant.sensor_humidity = Mock()
    plant.sensor_moisture = Mock()  # Soil moisture
    plant.sensor_illuminance = Mock()
    plant.sensor_CO2 = Mock()
    plant.sensor_power_consumption = Mock()
    plant.sensor_ph = Mock()
    
    # Mock the replace_external_sensor method on each sensor
    for sensor in [plant.sensor_temperature, plant.sensor_humidity, plant.sensor_moisture,
                   plant.sensor_illuminance, plant.sensor_CO2, plant.sensor_power_consumption,
                   plant.sensor_ph]:
        sensor.replace_external_sensor = Mock()
    
    # Mock sensor states with device classes and units to simulate real Home Assistant sensors
    sensor_states = {
        "sensor.temperature_main": Mock(attributes={"device_class": "temperature", "unit_of_measurement": "°C"}),
        "sensor.humidity_main": Mock(attributes={"device_class": "humidity", "unit_of_measurement": "%"}),
        "sensor.soil_moisture_main": Mock(attributes={"device_class": "humidity", "unit_of_measurement": "%"}),
        "sensor.illuminance_main": Mock(attributes={"device_class": "illuminance", "unit_of_measurement": "lux"}),
        "sensor.co2_main": Mock(attributes={"unit_of_measurement": "ppm"}),
        "sensor.power_main": Mock(attributes={"device_class": "power", "unit_of_measurement": "W"}),
        "sensor.ph_main": Mock(attributes={"unit_of_measurement": "pH"}),
    }
    
    # Mock hass.states.get to return appropriate sensor states
    def mock_get_state(entity_id):
        return sensor_states.get(entity_id)
    
    hass.states.get = mock_get_state
    
    # Mock config entry update
    hass.config_entries.async_update_entry = Mock()
    
    # Simulate the sensor mapping process (simplified version of what happens in change_tent)
    print("Mapping tent sensors to plant sensors:")
    tent_sensors = tent.get_sensors()
    print(f"Tent sensors: {tent_sensors}")
    
    # This is a simplified version of the sensor mapping logic in the PlantDevice.change_tent method
    sensor_mapping = {}
    for sensor_entity_id in tent_sensors:
        # Get the sensor state to determine its type
        sensor_state = hass.states.get(sensor_entity_id)
        if not sensor_state:
            print(f"  Warning: Sensor {sensor_entity_id} not found")
            continue
            
        # Determine sensor type based on device class or unit of measurement
        device_class = sensor_state.attributes.get("device_class", "")
        unit_of_measurement = sensor_state.attributes.get("unit_of_measurement", "")
        
        print(f"  Sensor {sensor_entity_id}: device_class={device_class}, unit={unit_of_measurement}")
        
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
    
    print(f"\nMapped sensors: {sensor_mapping}")
    
    # Simulate assigning the mapped sensors to the plant
    print("\nAssigning mapped sensors to plant:")
    if "temperature" in sensor_mapping:
        plant.sensor_temperature.replace_external_sensor(sensor_mapping["temperature"])
        print(f"  Temperature sensor: {sensor_mapping['temperature']}")
        
    if "moisture" in sensor_mapping:
        plant.sensor_moisture.replace_external_sensor(sensor_mapping["moisture"])
        print(f"  Soil moisture sensor: {sensor_mapping['moisture']}")
        
    if "humidity" in sensor_mapping:
        plant.sensor_humidity.replace_external_sensor(sensor_mapping["humidity"])
        print(f"  Air humidity sensor: {sensor_mapping['humidity']}")
        
    if "illuminance" in sensor_mapping:
        plant.sensor_illuminance.replace_external_sensor(sensor_mapping["illuminance"])
        print(f"  Illuminance sensor: {sensor_mapping['illuminance']}")
        
    if "co2" in sensor_mapping:
        plant.sensor_CO2.replace_external_sensor(sensor_mapping["co2"])
        print(f"  CO2 sensor: {sensor_mapping['co2']}")
        
    if "power_consumption" in sensor_mapping:
        plant.sensor_power_consumption.replace_external_sensor(sensor_mapping["power_consumption"])
        print(f"  Power consumption sensor: {sensor_mapping['power_consumption']}")
        
    if "ph" in sensor_mapping:
        plant.sensor_ph.replace_external_sensor(sensor_mapping["ph"])
        print(f"  pH sensor: {sensor_mapping['ph']}")
    
    print("\n=== Sensor Mapping Complete ===")


if __name__ == "__main__":
    demonstrate_plant_tent_assignment()
    demonstrate_sensor_mapping()
    print("\nThis demonstrates how a Plant can receive a Tent entity and easily change tents,")
    print("with automatic sensor inheritance based on device class and unit of measurement.")