# Configuration Parameters

This document describes all integration configuration options for the Brokkoli Plant Manager.

## Plant Configuration Options

### Basic Plant Information
- **name**: The name of your cannabis plant (required)
- **strain**: The strain of your cannabis plant (required)
- **breeder**: The breeder of the strain (optional)
- **growth_phase**: The current growth phase of the plant (default: "rooting")
- **plant_emoji**: An emoji to represent the plant (default: "🌿")

### Sensor Configuration
Each sensor can be configured with a specific entity from your Home Assistant setup:

- **temperature_sensor**: Entity ID for temperature monitoring
- **moisture_sensor**: Entity ID for soil moisture monitoring
- **conductivity_sensor**: Entity ID for soil conductivity monitoring
- **illuminance_sensor**: Entity ID for light intensity monitoring
- **humidity_sensor**: Entity ID for air humidity monitoring
- **co2_sensor**: Entity ID for CO2 monitoring
- **power_consumption_sensor**: Entity ID for power consumption monitoring
- **ph_sensor**: Entity ID for soil pH monitoring

### Threshold Configuration
Each sensor type has configurable minimum and maximum thresholds:

- **min_temperature**: Minimum acceptable temperature (default: 10°C)
- **max_temperature**: Maximum acceptable temperature (default: 40°C)
- **min_moisture**: Minimum acceptable soil moisture (default: 20%)
- **max_moisture**: Maximum acceptable soil moisture (default: 60%)
- **min_conductivity**: Minimum acceptable soil conductivity (default: 500 μS/cm)
- **max_conductivity**: Maximum acceptable soil conductivity (default: 3000 μS/cm)
- **min_illuminance**: Minimum acceptable light intensity (default: 0 lux)
- **max_illuminance**: Maximum acceptable light intensity (default: 100000 lux)
- **min_humidity**: Minimum acceptable air humidity (default: 20%)
- **max_humidity**: Maximum acceptable air humidity (default: 60%)
- **min_co2**: Minimum acceptable CO2 level (default: 60 ppm)
- **max_co2**: Maximum acceptable CO2 level (default: 60 ppm)
- **min_ph**: Minimum acceptable soil pH (default: 5.5)
- **max_ph**: Maximum acceptable soil pH (default: 7.5)

### Advanced Configuration
- **flowering_duration**: Expected flowering duration in days (optional)
- **pot_size**: Size of the pot in liters (default: 0.4L)
- **water_capacity**: Water capacity percentage (default: 50%)

### Status Stabilization Configuration
These settings help prevent rapid state changes (flickering) between "Problem" and "OK" states by adding stabilization mechanisms:

- **status_debounce_time**: Minimum time (in seconds) that a status change must be sustained before it's applied (default: 0 seconds, 0 = disabled)
- **hysteresis_percentage**: Percentage of the threshold range to use as hysteresis margin to prevent rapid switching near thresholds (default: 0.0%, 0 = disabled)
- **stabilization_window**: Minimum time (in seconds) that a sensor issue must be sustained before triggering a problem state (default: 0 seconds, 0 = disabled)
- **verbose_logging**: Enable verbose logging for debugging status changes (default: false, true = more detailed logs)

## Tent Configuration Options

### Basic Tent Information
- **name**: The name of your tent (required)
- **tent_emoji**: An emoji to represent the tent (default: "⛺")

### Sensor Configuration
Each tent can be configured with sensors that will be automatically assigned to plants in the tent:

- **illuminance_sensor**: Entity ID for tent light intensity monitoring
- **humidity_sensor**: Entity ID for tent air humidity monitoring
- **co2_sensor**: Entity ID for tent CO2 monitoring
- **power_consumption_sensor**: Entity ID for tent power consumption monitoring
- **ph_sensor**: Entity ID for tent pH monitoring

## Cycle Configuration Options

### Basic Cycle Information
- **name**: The name of your cycle (required)
- **cycle_emoji**: An emoji to represent the cycle (default: "🔁")

## Global Configuration Options

### Decimal Precision
- **decimals_temperature**: Number of decimal places for temperature values
- **decimals_humidity**: Number of decimal places for humidity values
- **decimals_illuminance**: Number of decimal places for illuminance values
- **decimals_conductivity**: Number of decimal places for conductivity values
- **decimals_moisture**: Number of decimal places for moisture values
- **decimals_co2**: Number of decimal places for CO2 values
- **decimals_ph**: Number of decimal places for pH values
- **decimals_power_consumption**: Number of decimal places for power consumption values
- **decimals_dli**: Number of decimal places for DLI values
- **decimals_total_water_consumption**: Number of decimal places for total water consumption values
- **decimals_total_fertilizer_consumption**: Number of decimal places for total fertilizer consumption values
- **decimals_total_power_consumption**: Number of decimal places for total power consumption values

### kWh Price
- **kwh_price**: Price per kWh for energy cost calculations (default: 0.3684 EUR)

## Default Thresholds Configuration
These settings allow you to configure default threshold values that will be applied to new plants:

- **default_min_temperature**: Default minimum temperature
- **default_max_temperature**: Default maximum temperature
- **default_min_moisture**: Default minimum moisture
- **default_max_moisture**: Default maximum moisture
- **default_min_conductivity**: Default minimum conductivity
- **default_max_conductivity**: Default maximum conductivity
- **default_min_illuminance**: Default minimum illuminance
- **default_max_illuminance**: Default maximum illuminance
- **default_min_humidity**: Default minimum humidity
- **default_max_humidity**: Default maximum humidity
- **default_min_co2**: Default minimum CO2
- **default_max_co2**: Default maximum CO2
- **default_min_ph**: Default minimum pH
- **default_max_ph**: Default maximum pH