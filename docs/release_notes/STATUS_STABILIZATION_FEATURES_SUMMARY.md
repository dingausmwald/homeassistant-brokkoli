# Status Stabilization Features Implementation Summary

This document summarizes the implementation of status stabilization features to prevent rapid state changes (flickering) between "Problem" and "OK" states in the Home Assistant plant integration.

## Features Implemented

### 1. Configuration Parameters
Added new configuration parameters to the PlantDevice class:
- `status_debounce_time`: Minimum time (in seconds) that a status change must be sustained before it's applied
- `hysteresis_percentage`: Percentage of the threshold range to use as hysteresis margin
- `stabilization_window`: Minimum time (in seconds) that a sensor issue must be sustained before triggering a problem state
- `verbose_logging`: Enable verbose logging for debugging status changes

### 2. Debounce Logic
Implemented debounce mechanism in the PlantDevice.update() method:
- Status changes are not applied immediately
- A pending status is set with a timestamp
- The actual status change only occurs after the debounce time has passed
- Prevents rapid switching between states due to temporary sensor fluctuations

### 3. Hysteresis-aware Threshold Checking
Implemented hysteresis mechanism to prevent rapid switching near threshold values:
- Uses a margin around threshold values based on percentage of the threshold range
- When a sensor value is in the "low" state, it needs to exceed the minimum threshold plus hysteresis margin to switch to "OK"
- When a sensor value is in the "high" state, it needs to drop below the maximum threshold minus hysteresis margin to switch to "OK"
- When a sensor value is in the "OK" state, it uses normal thresholds but with hysteresis margins

### 4. Stabilization Window Tracking
Implemented stabilization window mechanism to require sustained sensor issues:
- Tracks when each sensor first reports an issue
- Only triggers a problem state after the sensor issue has been sustained for the configured stabilization window
- Clears the tracking when the sensor returns to normal values

### 5. Logging Optimization
Reduced excessive logging by:
- Adding a verbose logging configuration option
- Only logging status changes when they actually occur
- Moving most log messages from DEBUG to INFO level with conditional verbose logging

### 6. Configuration UI
Updated the config flow to include new configuration options:
- Added status_debounce_time input (positive integer)
- Added hysteresis_percentage input (float)
- Added stabilization_window input (positive integer)
- Added verbose_logging input (boolean)

### 7. Unit Tests
Created comprehensive unit tests for all new features:
- Tests for debounce functionality with various time intervals
- Tests for hysteresis with values near thresholds
- Tests for stabilization window behavior
- Tests for logging level configuration

### 8. Documentation Updates
Updated documentation to reflect the new configuration options:
- Added Status Stabilization Configuration section to configuration_parameters.md
- Added Status Stabilization section to README.md
- Added Status Stabilization section to supported_functions.md

### 9. Bug Fixes
Fixed missing moisture sensor evaluation in the update method.

## Files Modified

1. `custom_components/plant/__init__.py`:
   - Added configuration parameters to PlantDevice.__init__()
   - Implemented _check_sensor_with_hysteresis() method
   - Implemented _check_sensor_stabilization() method
   - Updated update() method with debounce logic
   - Added moisture sensor evaluation to update() method

2. `custom_components/plant/config_flow.py`:
   - Added new configuration options to the options flow UI

3. `custom_components/plant/test_plant_status.py`:
   - Added unit tests for all new stabilization features

4. `docs/configuration_parameters.md`:
   - Added Status Stabilization Configuration section

5. `README.md`:
   - Added Status Stabilization section to the Problem Detection configuration instructions

6. `docs/supported_functions.md`:
   - Added Status Stabilization section to the Notifications features

## Usage Instructions

To use the new status stabilization features:

1. Navigate to **Settings** → **Devices & Services** → **Plant Monitor**
2. Select your plant device
3. Click **Configure**
4. Adjust the following settings:
   - **Status Debounce Time**: Set minimum time (seconds) for status changes
   - **Hysteresis Percentage**: Set percentage margin around thresholds
   - **Stabilization Window**: Set minimum time (seconds) for sustained issues
   - **Verbose Logging**: Enable detailed logging for debugging

## Benefits

These features provide several benefits:
- Reduced "flickering" between Problem and OK states
- More stable plant status reporting
- Reduced excessive logging
- Better handling of sensor noise and temporary fluctuations
- Configurable behavior to match different growing environments

## Backward Compatibility

All new features are opt-in via configuration:
- Default values maintain existing behavior
- No changes to existing APIs or data structures
- Existing configurations continue to work without modification