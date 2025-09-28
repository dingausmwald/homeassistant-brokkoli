# Installation Parameters

This document describes all integration installation parameters for the Brokkoli Plant Manager.

## Prerequisites

Before installing the Brokkoli Plant Manager, ensure you have the following:

1. **Home Assistant**: Version 2024.8 or later
2. **HACS** (optional but recommended): For easy installation and updates
3. **Supported Sensors**: Compatible sensors for monitoring your cannabis plants

## Required Dependencies

The integration requires the following Home Assistant components to be installed and configured:

- **recorder**: For data persistence and history
- **seedfinder**: For strain information and data (Brokkoli Seedfinder Integration)
- **integration**: For sensor integration calculations
- **utility_meter**: For consumption tracking
- **diagnostics**: For diagnostic information

These dependencies are automatically declared in the manifest.json file.

## Installation Methods

### HACS Installation (Recommended)

1. Add this repository as a [Custom Repository](https://hacs.xyz/docs/faq/custom_repositories/) in HACS
2. Set the category to "Integration"
3. Click "Install" on the "Brokkoli Cannabis Management" card
4. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/plant/` directory to your `<config>/custom_components/` directory
2. Restart Home Assistant

## Configuration Variables

During installation, you may need to configure the following parameters:

### Python Requirements
- **async-timeout**: Version 4.0.2 or later

This requirement is automatically installed by Home Assistant when the integration is loaded.

### Integration Manifest Parameters

The integration manifest defines the following parameters:

- **domain**: "plant" - The Home Assistant domain for this integration
- **name**: "Brokkoli Plant Manager" - The display name of the integration
- **version**: Current version of the integration
- **documentation**: URL to the documentation
- **issue_tracker**: URL to the issue tracker
- **iot_class**: "local_push" - Indicates the integration uses local push communication
- **config_flow**: true - Indicates the integration uses config flow for setup
- **after_dependencies**: List of required dependencies
- **codeowners**: List of maintainers
- **requirements**: List of Python package requirements
- **translations**: Language translation configuration
- **icon**: Path to the integration icon

## Supported Architectures

The integration supports the following architectures:

- **amd64**: 64-bit x86 processors
- **armv7**: ARM 32-bit processors
- **aarch64**: ARM 64-bit processors
- **i386**: 32-bit x86 processors

## Language Support

The integration currently supports the following languages:

- **English** (en)
- **German** (de)

Translations are provided through the config_flow platform.

## Minimum System Requirements

- **RAM**: 512MB available memory
- **Storage**: 100MB available disk space
- **Network**: Local network access for sensor communication
- **Processing Power**: 1GHz CPU or equivalent

## Network Requirements

- **Local Network Access**: The integration communicates with local sensors
- **No Internet Required**: For basic functionality (though some features may require internet)
- **Port Requirements**: No specific ports need to be opened

## Storage Requirements

- **Configuration Storage**: Configuration data is stored in Home Assistant's configuration storage
- **History Storage**: Historical data is stored in the Home Assistant recorder database
- **Image Storage**: Plant images are stored in the `/config/www/images/plants/` directory by default

## Performance Considerations

- **Update Frequency**: Sensors are updated based on their native update intervals
- **Resource Usage**: Minimal CPU and memory usage during normal operation
- **Database Impact**: Historical data is stored in the recorder database, which may impact database size over time

## Security Considerations

- **Local Processing**: All data processing occurs locally within Home Assistant
- **No Cloud Communication**: The integration does not communicate with external cloud services
- **Data Privacy**: All plant data remains local to your Home Assistant instance
- **Access Control**: Integration follows Home Assistant's standard access control mechanisms