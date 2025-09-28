# Plant-Tent Assignment in Home Assistant Brokkoli Integration

## Overview

This document explains how a Plant entity can receive a Tent entity in the Home Assistant Brokkoli integration, allowing for easy tent changes with automatic sensor inheritance.

## Implementation Details

### Core Functionality

The functionality is already implemented in the codebase through:

1. **PlantDevice Class** - Contains methods for tent assignment:
   - `_assigned_tent` - Stores the currently assigned tent object
   - `_tent_id` - Stores the ID of the assigned tent
   - `change_tent(tent_entity)` - Method to assign or change the tent

2. **Tent Class** - Manages sensors and can be assigned to plants:
   - `get_sensors()` - Returns list of sensor entity IDs
   - `assign_to_plant(plant)` - Assigns tent's sensors to a plant

3. **Services** - Provides external interface:
   - `change_tent` service - Allows changing a plant's tent assignment

### How It Works

1. **Tent Assignment**:
   - When a tent is assigned to a plant, the plant stores references to the tent
   - The tent's sensor list is retrieved using `get_sensors()`

2. **Sensor Mapping**:
   - Sensors are automatically mapped based on device class or unit of measurement:
     - Temperature: device_class="temperature" or units "°C", "°F", "K"
     - Humidity: device_class="humidity" or unit "%"
     - Illuminance: device_class="illuminance" or units "lx", "lux"
     - CO2: "co2" in entity name or unit "ppm"
     - Power: "power" in entity name or units "W", "kW"
     - pH: "ph" in entity name or unit "pH"

3. **Sensor Inheritance**:
   - Plant sensors are updated to use the tent's sensors
   - Configuration is updated to persist the sensor mappings

### Changing Tents

To change a plant's tent assignment:

1. Call the `change_tent` method with a new tent entity
2. The plant automatically:
   - Updates its internal tent references
   - Maps the new tent's sensors to its sensor types
   - Updates all sensor assignments
   - Persists the changes in configuration

### Clearing Tent Assignment

To clear a plant's tent assignment:

1. Call the `change_tent` method with `None`
2. The plant automatically:
   - Clears its tent references
   - Removes sensor mappings
   - Clears external sensor assignments

## Usage Examples

### In Code

```python
# Assign a tent to a plant
plant.change_tent(tent_entity)

# Change to a different tent
plant.change_tent(new_tent_entity)

# Clear tent assignment
plant.change_tent(None)
```

### Via Home Assistant Services

```yaml
# Change a plant's tent assignment
service: plant.change_tent
data:
  entity_id: plant.my_plant
  tent_id: tent.grow_tent_1
```

## Benefits

1. **Easy Tent Management** - Plants can be easily moved between tents
2. **Automatic Sensor Inheritance** - Sensors are automatically mapped based on type
3. **Persistent Configuration** - Changes are saved and restored
4. **Flexible** - Supports clearing tent assignments when needed

## Conclusion

The Plant-Tent assignment functionality is already fully implemented in the Home Assistant Brokkoli integration. Plants can easily receive Tent entities and change tents with automatic sensor inheritance, making it simple to manage cannabis plant monitoring in different growing environments.