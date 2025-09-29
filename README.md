# Brokkoli Cannabis Management for Home Assistant (v2025.9.0)

**The foundation of the Brokkoli Suite - Cannabis monitoring integration for Home Assistant**

A Home Assistant integration for monitoring cannabis plants with sensors and configurable thresholds. Part of the Brokkoli Suite for cannabis cultivation tracking.

## 🌱 Features

### Device-based Plant Management
- Cannabis plants as Home Assistant devices with grouped sensor entities
- Configurable thresholds for each sensor type
- Problem state when sensor values exceed limits
- Individual plant helpers: health status, growing phase, flowering duration
- Cycle system for grouping plants together

### Supported Sensors
- **Moisture**: Soil moisture percentage 
- **Temperature**: Ambient temperature (°C/°F)
- **Light/Brightness**: Light intensity (lux)
- **Conductivity**: Soil conductivity (µS/cm)
- **pH**: Soil pH level
- **Humidity**: Air humidity percentage
- **Co2**: Air CO2 ppm
- **Power**: Power consumption monitoring
- **Daily Light Integral (DLI)**: Calculated from light sensors

### Seedfinder Integration
- Strain data fetching during setup
- Strain images and basic information
- Growth phase definitions

### Services & Configuration
- UI-based setup through config flow
- Various services to interact with plants
- Sensor changes directly in plant configuration
- Automation triggers for dynamic sensor switching (e.g., room changes)

## 🔧 Installation

### Prerequisites
For the complete Brokkoli Suite, install these complementary components:

- **[Brokkoli Card](https://github.com/dingausmwald/lovelace-brokkoli-card)** - Lovelace cards for cannabis visualization
- **[Seedfinder Integration](https://github.com/dingausmwald/homeassistant-seedfinder)** - Cannabis strain data and information

### HACS Installation (Recommended)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

1. Add this repository as a [Custom Repository](https://hacs.xyz/docs/faq/custom_repositories/) in HACS
2. Set the category to "Integration"
3. Click "Install" on the "Brokkoli Cannabis Management" card
4. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/plant/` directory to your `<config>/custom_components/` directory
2. Restart Home Assistant

## 🗑️ Removal

To remove a plant and all its associated entities:

1. Go to **Settings** → **Devices & Services**
2. Find your plant device in the list
3. Click on the plant device to open its details
4. Click the **Remove** button
5. Confirm the removal when prompted

Alternatively, you can use the `plant.remove_plant` service:

1. Go to **Developer Tools** → **Services**
2. Select `plant.remove_plant` from the service dropdown
3. Select the plant entity you want to remove
4. Click **Call Service**

### Step-by-Step Removal Process

When you remove a plant, the following happens:

1. **Entity Removal**: All sensor entities, threshold entities, and helper entities associated with the plant are removed
2. **Device Cleanup**: The plant device and all its entities are unregistered from Home Assistant
3. **Configuration Deletion**: The plant's configuration entry is removed from Home Assistant's configuration
4. **Data Purging**: All plant-specific data, including historical sensor data, is removed

**Note**: This action is irreversible. Make sure to export your plant configuration using the `plant.export_plants` service if you want to keep a backup before removal.

## 🚀 Quick Start

### 1. Set up your first cannabis plant
1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for "Plant" and select it
3. Follow the configuration flow to set up your cannabis plant
4. Assign your sensors (moisture, temperature, light, etc.)

### 2. Configure thresholds
- Each threshold (min/max values) becomes its own entity
- Adjust thresholds directly from the UI or via automations
- Changes take effect immediately without restart

### 3. Monitor and maintain
- View all cannabis plants under **Settings** → **Devices & Services** → **Devices**
- Check plant status and sensor readings
- Monitor problem states when sensor values exceed thresholds

## 📊 Sensor Management

Sensors can be changed directly in the plant's configuration interface or dynamically via automations when plants are moved between rooms.

## 🎨 Brokkoli Suite Integration

Brokkoli Cannabis Management is the foundation of the Brokkoli Suite:

### [Brokkoli Card](https://github.com/dingausmwald/lovelace-brokkoli-card)
- Individual cannabis plant cards
- Area cards for spatial plant arrangement
- List cards for tabular overview
- Interactive plant positioning

### [Seedfinder Integration](https://github.com/dingausmwald/homeassistant-seedfinder)
- Cannabis strain database access
- Strain data fetching during setup
- Strain imagery and basic information
- Growth phase definitions

## 🔧 Configuration

### Problem Detection
Customize which sensor violations trigger problem states:

1. Navigate to **Settings** → **Devices & Services** → **Plant Monitor**
2. Select your plant device
3. Click **Configure**
4. Choose which threshold violations should trigger alerts

### Status Stabilization
Prevent rapid state changes (flickering) between "Problem" and "OK" states with these advanced stabilization features:

- **Status Debounce**: Set a minimum time that a status change must be sustained before it's applied
- **Hysteresis**: Add a margin around threshold values to prevent rapid switching when sensor values are near thresholds
- **Stabilization Window**: Require sensor issues to be sustained for a minimum time before triggering problem states
- **Verbose Logging**: Enable detailed logging for debugging status changes

To configure these features:

1. Navigate to **Settings** → **Devices & Services** → **Plant Monitor**
2. Select your plant device
3. Click **Configure**
4. Adjust the status stabilization settings in the configuration panel

### Strain Management
Update cannabis strain and refresh data from Seedfinder:

1. Go to cannabis plant device configuration
2. Enter the exact strain name (Seedfinder PID format)
3. Enable "Force refresh" to update all data including images
4. Strain changes take effect immediately

### Central sensor decimals
- Centralized defaults are defined in `custom_components/plant/sensor_configuration.py`.
- The central config entry "Plant Monitor Konfiguration" exposes decimal options per sensor (e.g. `decimals_temperature`, `decimals_humidity`, `decimals_illuminance`, `decimals_ppfd`, `decimals_dli`, `decimals_total_water_consumption`, ...).
- All live current sensors (temperature, humidity, illuminance, moisture, conductivity, CO2, ppfd, pH) and derived values use these settings for consistent rounding.
- Manual updates (e.g. add watering) also respect the configured decimals.

## 📱 Available Services

The integration provides various services to interact with your cannabis plants:

- `plant.replace_sensor` - Replace sensors for a plant
- `plant.create_plant` - Create a new plant
- `plant.remove_plant` - Remove a plant and all its entities
  - **Example**: Remove a plant named "My Plant" by selecting the plant entity `plant.my_plant`
  - **Note**: This will permanently delete the plant and all associated sensor entities, thresholds, and configuration
- `plant.clone_plant` - Create a clone/cutting of an existing plant
- `plant.create_cycle` - Create a new cycle for grouping plants
- `plant.remove_cycle` - Remove a cycle and all its entities
- `plant.move_to_cycle` - Move plants to a cycle or remove from cycle
- `plant.update_plant_attributes` - Update plant attributes and information
- `plant.move_to_area` - Move plants to different areas
- `plant.add_image` - Add images to plants
- `plant.change_position` - Change plant position coordinates
- `plant.export_plants` - Export plant configurations
- `plant.import_plants` - Import plant configurations

These services are integrated into the [Brokkoli Card](https://github.com/dingausmwald/lovelace-brokkoli-card) interface for convenient operation, or can be used directly in automations and scripts.

## 🧪 Development and Testing

For developers interested in contributing to the Brokkoli integration, comprehensive technical documentation is available in the [DEVELOPMENT.md](file:///d:/Python/2/homeassistant-brokkoli/DEVELOPMENT.md) file. This includes:

- Testing strategy and test organization
- Architecture overview
- Development best practices
- Quality metrics and troubleshooting tips

## 🆘 Troubleshooting

### Sensor Values Not Updating
If old sensor values persist after cannabis plant reconfiguration:
- Use the `replace_sensor` service instead of removing/re-adding plants

### Strain Not Found
- Ensure exact strain name matching Seedfinder PID format
- Check that Seedfinder integration is properly configured

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests, report issues, or suggest improvements.

## 📄 License

This project is licensed under the MIT License.

## ☕ Support

If you find this project helpful, consider supporting its development:

<a href="https://buymeacoffee.com/dingausmwald" target="_blank">
<img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 50px !important;">
</a>

---

**Part of the Brokkoli Suite** - Cannabis cultivation tracking for Home Assistant