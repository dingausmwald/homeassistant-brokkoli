# Data Update Mechanisms

This document describes how data is updated in the Brokkoli Plant Manager integration.

## Sensor Data Updates

### Real-time Updates
Sensor data is updated in real-time based on the update intervals of the underlying sensors. When a sensor reports a new value, the integration immediately processes and updates the corresponding plant entity.

### Update Triggers
Data updates are triggered by:

1. **Sensor State Changes**: When any configured sensor reports a new state
2. **Time-based Updates**: Periodic updates for calculated values (DLI, consumption metrics)
3. **Manual Service Calls**: When services like `add_watering` or `add_conductivity` are called
4. **Configuration Changes**: When plant configuration is modified through the UI

### Update Processing Flow
1. Sensor state change is detected by Home Assistant
2. Integration receives the state change notification
3. New value is validated and processed
4. Plant entity state is updated
5. Threshold checks are performed
6. Problem state is updated if necessary
7. Calculated values (DLI, consumption) are updated
8. Entity state is published to Home Assistant

## DLI (Daily Light Integral) Calculation

### Update Frequency
DLI is calculated and updated every 5 minutes or when illuminance sensor values change.

### Calculation Method
DLI is calculated using the following process:
1. Collect illuminance readings over time
2. Convert illuminance to PPFD (Photosynthetic Photon Flux Density)
3. Integrate PPFD over 24 hours
4. Update the DLI entity with the calculated value

### Data Sources
- **Illuminance Sensor**: Primary data source for DLI calculation
- **Historical Data**: Previous illuminance readings from the recorder database

## Consumption Tracking Updates

### Water Consumption
- Updated when `add_watering` service is called
- Automatically calculated based on sensor data when configured
- Updated every 15 minutes with cumulative totals

### Fertilizer Consumption
- Updated when fertilizer application is recorded
- Automatically calculated based on sensor data when configured
- Updated every 15 minutes with cumulative totals

### Power Consumption
- Updated based on power sensor readings
- Calculated in real-time from power consumption sensors
- Updated every 5 minutes with cumulative totals

## Threshold Monitoring

### Update Mechanism
Threshold monitoring is performed continuously whenever sensor values change.

### Evaluation Process
1. New sensor value is received
2. Value is compared against configured min/max thresholds
3. Problem state is updated based on threshold violations
4. Notifications are triggered if configured

### Problem State Updates
- **Low**: Sensor value is below minimum threshold
- **High**: Sensor value is above maximum threshold
- **OK**: Sensor value is within acceptable range
- **DLI Low/High**: DLI value is outside optimal range

## Plant Attribute Updates

### Growth Phase Tracking
- Automatically advances based on time and manual input
- Updated when flowering duration is reached
- Modified through configuration UI

### Health Rating
- Updated based on sensor performance
- Manually adjustable through UI
- Influences problem state calculations

### Flowering Duration
- Automatically tracked from flowering start date
- Updated in real-time
- Used for growth phase transitions

## Configuration Updates

### UI-based Configuration
- Changes are applied immediately
- Entities are updated to reflect new configuration
- Threshold monitoring is adjusted

### Service-based Configuration
- Changes are processed and applied immediately
- Entities are updated to reflect new configuration
- Historical data is preserved

## Data Persistence

### State Persistence
- All entity states are persisted through Home Assistant's state machine
- Historical data is stored in the recorder database

### Configuration Persistence
- Plant configurations are stored in config entries
- Settings are preserved across Home Assistant restarts

### Image Data Persistence
- Plant images are stored in the file system
- Image references are stored in plant attributes
- Images are served through Home Assistant's web server

## Batch Updates

### Scheduled Updates
- DLI calculations: Every 5 minutes
- Consumption totals: Every 15 minutes
- Data aggregation: Hourly

### Bulk Operations
- When multiple sensors update simultaneously
- During plant creation or import
- During configuration migrations

## Error Handling

### Sensor Unavailability
- Unavailable sensors are marked as such
- Problem states are adjusted accordingly
- Notifications can be configured for sensor issues

### Data Validation
- Invalid sensor values are filtered out
- Entities maintain last known good values
- Error logs are generated for troubleshooting

### Recovery Mechanisms
- Automatic recovery when sensors become available
- Manual recovery through UI or services
- Data interpolation for missing values

## Performance Optimization

### Update Throttling
- High-frequency sensors are throttled to prevent excessive updates
- Calculated values are updated on a schedule rather than real-time
- Batch processing for multiple simultaneous updates

### Resource Management
- Memory-efficient data structures
- Database query optimization
- Caching of frequently accessed data