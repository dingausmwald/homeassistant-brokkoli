# Architecture Documentation

This document provides an overview of the Brokkoli Plant Integration architecture.

## System Overview

The Brokkoli Plant Integration is designed as a Home Assistant custom component that provides comprehensive plant monitoring and management capabilities.

## Core Components

### 1. Configuration Flow
File: [config_flow.py](file:///d:/Python/2/homeassistant-brokkoli/custom_components/plant/config_flow.py)

Handles the UI-based setup and configuration of plant entities:
- Plant creation and configuration
- Validation of user inputs
- Integration with Seedfinder for strain data
- Decimal precision configuration
- Aggregation method selection

### 2. Plant Device
File: [sensor.py](file:///d:/Python/2/homeassistant-brokkoli/custom_components/plant/sensor.py)

The main plant entity that groups all sensors:
- Problem state management
- Threshold validation
- Sensor value processing
- Consumption tracking integration
- Tent assignment management

### 3. Sensor Management
File: [sensor.py](file:///d:/Python/2/homeassistant-brokkoli/custom_components/plant/sensor.py)

Individual sensor entities for each metric:
- Temperature, moisture, conductivity, illuminance, humidity, CO2
- PPFD and DLI calculations
- External sensor integration
- Value processing and validation
- Decimal precision handling

### 4. Consumption Tracking
Files: 
- [plant_meters.py](file:///d:/Python/2/homeassistant-brokkoli/custom_components/plant/plant_meters.py)
- [sensor.py](file:///d:/Python/2/homeassistant-brokkoli/custom_components/plant/sensor.py)

Water, fertilizer, and power consumption meters:
- Utility meter integration
- Total consumption tracking
- Integration sensor implementation
- Energy cost calculation

### 5. Services
File: [services.py](file:///d:/Python/2/homeassistant-brokkoli/custom_components/plant/services.py)

Plant management services:
- Plant creation, removal, and cloning
- Sensor replacement
- Data export/import
- Cycle and tent management
- Manual watering and fertilization

### 6. Constants Management
File: [const.py](file:///d:/Python/2/homeassistant-brokkoli/custom_components/plant/const.py)

Centralized constant definitions:
- Domain and entity identifiers
- Sensor attributes and readings
- Default values and thresholds
- Aggregation methods
- Device types and service constants

### 7. Sensor Configuration
File: [sensor_configuration.py](file:///d:/Python/2/homeassistant-brokkoli/custom_components/plant/sensor_configuration.py)

Sensor configuration management:
- Decimal precision settings
- Aggregation method configuration
- Sensor-specific settings

## Data Flow

```
External Sensors → Plant Sensors → Plant Device → Consumption Meters → Home Assistant
                              ↘ Services & Config Flow
```

## Component Interactions

### Plant Creation Flow
1. User initiates plant creation through Config Flow
2. Config Flow validates inputs and creates plant configuration
3. Plant Device is instantiated with configuration
4. Sensor entities are created and registered with Home Assistant
5. Consumption meters are initialized if configured
6. Plant entity is available in Home Assistant

### Data Processing Flow
1. External sensors provide data updates
2. Plant sensors receive and process values
3. Values are validated against configured thresholds
4. Problem states are updated if thresholds are violated
5. Consumption meters track resource usage
6. Data is persisted for historical analysis

### Service Execution Flow
1. User triggers service through Home Assistant
2. Service handler validates parameters
3. Appropriate actions are executed on plant entities
4. State changes are propagated to Home Assistant
5. Data persistence is updated if needed

## Design Patterns

### Observer Pattern
Plant sensors observe external sensor state changes and update accordingly.

### Factory Pattern
Config Flow acts as a factory for creating plant entities with appropriate configurations.

### Strategy Pattern
Aggregation methods are implemented as strategies that can be selected per sensor.

### Singleton Pattern
Plant entities maintain singleton behavior within their configuration entries.

## Testing Architecture

The testing architecture is designed to validate each component in isolation:

```
Unit Tests → Individual Functions & Classes
Integration Tests → Component Interactions
Verification Tests → System Behavior Validation
```

See [testing.md](testing.md) for detailed testing documentation.

## Extensibility

The architecture is designed to be extensible:
- New sensor types can be added by extending the sensor base classes
- Additional consumption tracking can be implemented through new meter classes
- Custom services can be added to the services module
- New device types can be supported through the device type system