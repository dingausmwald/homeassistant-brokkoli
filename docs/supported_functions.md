# Supported Functionality

This document describes the supported functionality, including entities and platforms of the Brokkoli Plant Manager integration.

## Core Functionality

### Plant Management
- **Plant Creation**: Create individual cannabis plants with custom configurations
- **Plant Configuration**: Configure sensors, thresholds, and plant attributes
- **Plant Monitoring**: Continuous monitoring of plant health and environmental conditions
- **Plant Removal**: Remove plants and associated entities when no longer needed
- **Plant Cloning**: Create clones/cuttings of existing plants
- **Plant Positioning**: Track and manage plant positions within grow spaces

### Tent Management
- **Tent Creation**: Create grow tents for organizing plants
- **Tent Configuration**: Configure tent-level sensors and settings
- **Plant Assignment**: Assign plants to specific tents
- **Tent Monitoring**: Monitor tent-level environmental conditions
- **Tent Journal**: Maintain a journal of tent activities and maintenance

### Cycle Management
- **Cycle Creation**: Create growing cycles for grouping plants
- **Cycle Configuration**: Configure cycle-specific settings
- **Plant Assignment**: Move plants between cycles
- **Cycle Monitoring**: Track cycle progress and plant development

### Sensor Management
- **Sensor Assignment**: Assign sensors to specific plant parameters
- **Sensor Replacement**: Replace sensors without losing plant data
- **Dynamic Sensor Switching**: Change sensors based on plant location or conditions
- **Sensor Validation**: Validate sensor data and handle errors

## Entities

### Plant Entities

#### Main Plant Entity
- **Entity Type**: `plant`
- **Attributes**:
  - `name`: Plant name
  - `strain`: Cannabis strain
  - `breeder`: Strain breeder
  - `growth_phase`: Current growth phase
  - `problem`: Current problem state (ok, low, high)
  - `device_type`: Type of device (plant)
  - `tent_id`: Assigned tent ID
  - `cycle_id`: Assigned cycle ID
  - `position_x`: X coordinate in grow space
  - `position_y`: Y coordinate in grow space
  - `flowering_duration`: Current flowering duration
  - `health`: Plant health rating

#### Sensor Entities
Each plant has multiple sensor entities for monitoring different parameters:

- **Temperature Sensor**: `sensor.plant_name_temperature`
- **Moisture Sensor**: `sensor.plant_name_soil_moisture`
- **Conductivity Sensor**: `sensor.plant_name_conductivity`
- **Illuminance Sensor**: `sensor.plant_name_illuminance`
- **Humidity Sensor**: `sensor.plant_name_air_humidity`
- **CO2 Sensor**: `sensor.plant_name_air_co2`
- **Power Consumption Sensor**: `sensor.plant_name_power_consumption`
- **pH Sensor**: `sensor.plant_name_soil_ph`

#### Threshold Entities
Each sensor has associated threshold entities:

- **Temperature Thresholds**: `plant.plant_name_temperature_threshold`
- **Moisture Thresholds**: `plant.plant_name_moisture_threshold`
- **Conductivity Thresholds**: `plant.plant_name_conductivity_threshold`
- **Illuminance Thresholds**: `plant.plant_name_illuminance_threshold`
- **Humidity Thresholds**: `plant.plant_name_humidity_threshold`
- **CO2 Thresholds**: `plant.plant_name_co2_threshold`
- **pH Thresholds**: `plant.plant_name_ph_threshold`

#### Calculated Value Entities
- **DLI Sensor**: `sensor.plant_name_dli` (Daily Light Integral)
- **Health Helper**: `sensor.plant_name_health`
- **Water Consumption**: `sensor.plant_name_water_consumption`
- **Fertilizer Consumption**: `sensor.plant_name_fertilizer_consumption`
- **Total Water Consumption**: `sensor.plant_name_total_water_consumption`
- **Total Fertilizer Consumption**: `sensor.plant_name_total_fertilizer_consumption`
- **Total Power Consumption**: `sensor.plant_name_total_power_consumption`
- **Energy Cost**: `sensor.plant_name_energy_cost`

### Tent Entities

#### Main Tent Entity
- **Entity Type**: `plant` (device_type: tent)
- **Attributes**:
  - `name`: Tent name
  - `device_type`: Type of device (tent)
  - `journal`: Tent journal entries
  - `maintenance_entries`: Tent maintenance records

#### Tent Sensor Entities
- **Illuminance Sensor**: `sensor.tent_name_illuminance`
- **Humidity Sensor**: `sensor.tent_name_humidity`
- **CO2 Sensor**: `sensor.tent_name_co2`
- **Power Consumption Sensor**: `sensor.tent_name_power_consumption`
- **pH Sensor**: `sensor.tent_name_ph`

### Cycle Entities

#### Main Cycle Entity
- **Entity Type**: `plant` (device_type: cycle)
- **Attributes**:
  - `name`: Cycle name
  - `device_type`: Type of device (cycle)

### Configuration Entities

#### Global Configuration Entity
- **Entity Type**: `plant` (device_type: config)
- **Attributes**:
  - `kwh_price`: Price per kWh for energy cost calculations
  - `decimal settings`: Decimal precision for various sensor types

## Platforms

### Sensor Platform
- **Supported Features**:
  - Real-time sensor value monitoring
  - Historical data tracking
  - Unit conversion and formatting
  - Data validation and error handling
- **Entity Types**: Various sensor types as listed above
- **Update Mechanism**: Real-time updates from underlying sensors

### Number Platform
- **Supported Features**:
  - Configurable threshold values
  - Decimal precision control
  - Unit-specific formatting
- **Entity Types**: Threshold min/max values
- **Update Mechanism**: Configuration changes through UI

### Select Platform
- **Supported Features**:
  - Growth phase selection
  - Cycle assignment
  - Tent assignment
- **Entity Types**: 
  - `select.plant_name_growth_phase`
  - `select.plant_name_cycle`
  - `select.plant_name_tent`
- **Update Mechanism**: User selection through UI

### Text Platform
- **Supported Features**:
  - Plant attribute editing
  - Journal entry creation
  - Note taking
- **Entity Types**:
  - `text.plant_name_phenotype`
  - `text.plant_name_notes`
  - `text.plant_name_journal`
- **Update Mechanism**: Text input through UI

## Services

### Plant Services

#### `plant.create_plant`
Create a new cannabis plant with specified configuration.

#### `plant.remove_plant`
Remove a plant and all associated entities.

#### `plant.clone_plant`
Create a clone/cutting of an existing plant.

#### `plant.replace_sensor`
Replace the sensor for a specific plant parameter.

#### `plant.update_plant_attributes`
Update plant attributes and information.

#### `plant.move_to_area`
Move plants to different areas in Home Assistant.

#### `plant.move_to_cycle`
Move plants to a cycle or remove from cycle.

#### `plant.add_image`
Add images to plants for visual tracking.

#### `plant.change_position`
Change plant position coordinates in the grow space.

#### `plant.export_plants`
Export plant configurations and data.

#### `plant.import_plants`
Import plant configurations and data.

#### `plant.add_watering`
Add manual watering entries.

#### `plant.add_conductivity`
Add manual conductivity measurements.

#### `plant.add_ph`
Add manual pH measurements.

### Tent Services

#### `plant.create_tent`
Create a new grow tent.

#### `plant.change_tent`
Change the tent assigned to a plant.

#### `plant.list_tents`
List all available tents.

### Cycle Services

#### `plant.create_cycle`
Create a new growing cycle.

#### `plant.remove_cycle`
Remove a cycle and all associated entities.

### Utility Services

#### `plant.add_watering`
Add manual watering entries to track consumption.

## Integration Features

### Data Persistence
- **Configuration Storage**: Plant configurations stored in Home Assistant config entries
- **Historical Data**: Sensor data stored in recorder database
- **Image Storage**: Plant images stored in file system
- **Export/Import**: Configuration backup and restore functionality

### Notifications
- **Problem Detection**: Automatic detection of threshold violations
- **State Changes**: Notification of plant state changes
- **Custom Alerts**: Configurable alert conditions

### Status Stabilization
Prevent rapid state changes (flickering) between "Problem" and "OK" states with advanced stabilization mechanisms:

- **Status Debounce**: Configurable time delay before applying status changes
- **Hysteresis**: Margin around threshold values to prevent rapid switching
- **Stabilization Window**: Minimum duration for sustained sensor issues before triggering problems
- **Logging Optimization**: Configurable verbosity to reduce excessive debug output

### Automation Support
- **State Triggers**: Trigger automations based on plant states
- **Service Calls**: Call plant services from automations
- **Condition Evaluation**: Use plant states in automation conditions

### Visualization
- **Entity Cards**: Standard Home Assistant entity cards
- **Custom Cards**: Integration with Brokkoli Card for enhanced visualization
- **Graphing**: Historical data visualization through recorder integration

### Multi-Language Support
- **English**: Full support
- **German**: Full support
- **Extensible**: Framework for additional languages

### Device Registry Integration
- **Device Tracking**: Plants, tents, and cycles registered as devices
- **Entity Grouping**: All related entities grouped under parent device
- **Area Assignment**: Devices can be assigned to Home Assistant areas

### Diagnostic Support
- **Config Entry Diagnostics**: Detailed diagnostic information for troubleshooting
- **Device Diagnostics**: Device-specific diagnostic data
- **Data Redaction**: Sensitive information automatically redacted

## Advanced Features

### Consumption Tracking
- **Water Consumption**: Track water usage and costs
- **Fertilizer Consumption**: Track fertilizer usage
- **Power Consumption**: Track energy usage and costs
- **Aggregation**: Total consumption calculations across multiple plants

### DLI Calculation
- **Real-time Calculation**: Continuous DLI calculation from illuminance data
- **Historical Analysis**: DLI history tracking
- **Optimization**: DLI-based recommendations for lighting

### Growth Phase Management
- **Phase Tracking**: Automatic growth phase tracking
- **Duration Monitoring**: Flowering duration tracking
- **Transition Management**: Growth phase transitions

### Health Monitoring
- **Health Rating**: Numerical health rating system
- **Factor Analysis**: Health based on multiple sensor parameters
- **Trend Analysis**: Health trend tracking over time

### Data Analysis
- **Statistical Analysis**: Data aggregation and statistical calculations
- **Trend Detection**: Pattern recognition in plant data
- **Anomaly Detection**: Identification of unusual data patterns

This comprehensive functionality makes the Brokkoli Plant Manager a powerful tool for cannabis cultivation tracking within Home Assistant.