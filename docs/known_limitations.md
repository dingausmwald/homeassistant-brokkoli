# Known Limitations

This document describes known limitations of the Brokkoli Plant Manager integration.

## Sensor Limitations

### Sensor Compatibility
- **Limited Sensor Types**: The integration currently supports a specific set of sensor types (temperature, moisture, conductivity, illuminance, humidity, CO2, power consumption, pH). Additional sensor types require custom development.
- **Sensor Quality**: The accuracy of plant monitoring is directly dependent on the quality and calibration of the connected sensors.
- **Sensor Update Frequency**: Some sensors may have slow update intervals, which can affect the responsiveness of the monitoring system.

### Data Gaps
- **Missing Data Handling**: Extended periods of sensor unavailability may result in gaps in data collection and calculation of derived values like DLI.
- **Interpolation Limitations**: While the system attempts to handle missing data, extended gaps may affect the accuracy of calculated metrics.

## Performance Limitations

### Resource Usage
- **Memory Consumption**: The integration may consume significant memory when monitoring large numbers of plants or storing extensive historical data.
- **Database Growth**: Continuous data recording can lead to rapid growth of the Home Assistant database, requiring periodic maintenance.
- **Processing Overhead**: Complex calculations like DLI and consumption tracking may introduce processing overhead, especially with many plants.

### Update Frequency
- **Calculation Delays**: Some calculated values (DLI, consumption totals) are updated on a schedule rather than in real-time, leading to potential delays in data availability.
- **Batch Processing**: Certain operations are processed in batches, which may introduce delays in state updates.

## Configuration Limitations

### Threshold Management
- **Static Thresholds**: Thresholds are static values that don't automatically adjust based on growth phase or plant conditions.
- **Limited Threshold Types**: Only min/max thresholds are supported; more complex threshold patterns require custom automations.

### Device Management
- **Manual Device Assignment**: Assigning plants to tents or cycles requires manual intervention or custom automations.
- **Limited Device Discovery**: The integration doesn't automatically discover or configure sensors; manual setup is required.

## Data Management Limitations

### Backup and Recovery
- **Manual Backup Process**: While export functionality exists, automated backup scheduling requires custom automations.
- **Import Limitations**: Imported data may not perfectly match the current system state, requiring manual verification.

### Historical Data
- **Data Retention**: Long-term data retention is dependent on Home Assistant's recorder settings and available storage.
- **Data Migration**: Configuration changes may require manual data migration or adjustment.

## Platform Limitations

### Home Assistant Dependencies
- **Version Requirements**: The integration requires specific versions of Home Assistant and dependent components.
- **Component Dependencies**: The integration depends on several other Home Assistant components that must be properly configured.

### Mobile Interface
- **Limited Mobile Optimization**: The integration is primarily designed for desktop use; mobile interface may have limitations.
- **Notification Handling**: Custom notification handling requires additional configuration and automations.

## Feature Limitations

### Growth Tracking
- **Manual Growth Phase Management**: Growth phase transitions require manual input or custom automations.
- **Limited Growth Models**: The integration doesn't include sophisticated growth modeling or prediction algorithms.

### Environmental Control
- **Basic Environmental Control**: Environmental control is limited to basic threshold-based actions; advanced control strategies require custom automations.
- **No PID Control**: The integration doesn't implement advanced control algorithms like PID controllers.

### Integration Capabilities
- **Limited Third-party Integration**: Direct integration with third-party systems is limited; most integration requires custom development.
- **No Cloud Sync**: The integration doesn't provide cloud synchronization capabilities.

## Technical Limitations

### Scalability
- **Large Installation Performance**: Performance may degrade with very large installations (hundreds of plants or sensors).
- **Network Dependency**: The integration requires reliable local network connectivity for sensor communication.

### Error Handling
- **Limited Error Recovery**: Some error conditions may require manual intervention to resolve.
- **Diagnostic Information**: Diagnostic information may be limited, making troubleshooting more difficult.

### Security
- **Local Network Security**: Security is dependent on the security of the local network.
- **No Encryption**: Data communication within the local network is not encrypted.

## User Interface Limitations

### Configuration UI
- **Complex Configuration**: Initial setup and configuration can be complex for new users.
- **Limited Validation**: Some configuration errors may not be detected until runtime.

### Visualization
- **Basic Visualization**: Built-in visualization is limited; advanced visualization requires custom dashboards.
- **No Graphing**: Native graphing capabilities are limited; external graphing tools are recommended.

## Future Development Limitations

### Development Roadmap
- **Feature Prioritization**: Not all requested features can be implemented immediately due to development resource constraints.
- **API Stability**: Some APIs may change in future versions, requiring updates to custom automations.

### Community Support
- **Documentation Gaps**: Some advanced features may have limited documentation.
- **Community Expertise**: Support for advanced customization may be limited to experienced users.

## Workarounds and Mitigations

### Performance Optimization
- **Database Maintenance**: Regular database maintenance can help manage performance.
- **Selective Recording**: Configuring recorder settings to limit data retention can help manage database growth.

### Data Management
- **Regular Backups**: Implementing regular backup automations can help protect data.
- **Monitoring**: Setting up monitoring for system performance can help identify issues early.

### Configuration Management
- **Documentation**: Maintaining good documentation of configurations can help with troubleshooting.
- **Testing**: Testing configuration changes in a development environment before applying to production.

These limitations are known issues that are being considered for future development. Users should be aware of these limitations when planning their installation and usage of the Brokkoli Plant Manager integration.