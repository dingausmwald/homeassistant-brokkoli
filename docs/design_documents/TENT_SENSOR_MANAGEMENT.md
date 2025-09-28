# Tent Sensor Management and Plant Inheritance Implementation

## Overview

This document describes the implementation of Tent sensor management and how Plants inherit sensors from Tents in the Home Assistant Brokkoli integration. The implementation addresses the issue where the `replace_sensors` method was missing from the `PlantDevice` class, and improves the Tent configuration flow to make assigning Plants to new Tents easier.

**Status: IMPLEMENTED** - The `replace_sensors` method has been successfully implemented and tested.

## Changes Made

### 1. Implemented Missing `replace_sensors` Method

The `replace_sensors` method was missing from the `PlantDevice` class, but it was being called in the `assign_tent` and `change_tent` methods. We implemented this method to:

1. Map Tent sensors to Plant sensor types based on device class or unit of measurement
2. Replace individual Plant sensors using the existing `replace_external_sensor` method
3. Update the config entry with the new sensor assignments

#### Sensor Mapping Logic

The implementation uses the following logic to map Tent sensors to Plant sensors:

- **Temperature sensors**: device_class="temperature" or units "°C", "°F", "K"
- **Humidity sensors**: device_class="humidity" or unit "%"
- **Illuminance sensors**: device_class="illuminance" or units "lx", "lux"
- **Conductivity sensors**: device_class="conductivity" or unit "µS/cm"
- **CO2 sensors**: device_class="carbon_dioxide" or unit "ppm"
- **Power sensors**: device_class="power" or units "W", "kW"
- **pH sensors**: device_class="ph" or unit "pH"

### 2. Improved Tent Configuration Flow

The Tent configuration flow was modified to ask for sensors with the same names as used for Plants:

1. **Temperature sensor** (FLOW_SENSOR_TEMPERATURE)
2. **Air humidity sensor** (FLOW_SENSOR_HUMIDITY)
3. **CO2 sensor** (FLOW_SENSOR_CO2)
4. **Illuminance sensor (Lux)** (FLOW_SENSOR_ILLUMINANCE)
5. **Power consumption sensor (Energy)** (FLOW_SENSOR_POWER_CONSUMPTION)

This creates a consistent mapping between Tent and Plant sensors, making it easier to assign Plants to new Tents.

## Benefits

1. **Fixed Missing Functionality**: The `replace_sensors` method is now properly implemented
2. **Simplified User Experience**: Users can easily understand sensor mapping between Tents and Plants
3. **Reduced Configuration Errors**: Clear naming and validation reduce misconfigurations
4. **Improved Maintainability**: Better structured code for sensor management
5. **Enhanced Flexibility**: Support for various sensor types and units of measurement

## Testing

We created tests to verify that the implementation works correctly:

1. **Unit Tests**: Test sensor mapping with various device classes and units
2. **Integration Tests**: Test complete Tent creation and Plant assignment flow
3. **Verification Script**: Simple verification script that tests the core functionality

All tests pass successfully, confirming that the implementation works as expected.

## Future Improvements

1. Add support for more sensor types
2. Implement better error handling for mismatched sensors
3. Add visual feedback during sensor mapping
4. Implement undo functionality for sensor assignments
5. Add tooltips and help text for sensor selection