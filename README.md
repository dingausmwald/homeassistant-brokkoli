# Brokkoli Cannabis Management for Home Assistant

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
- **Power**: Power consumption monitoring
- **Daily Light Integral (DLI)**: Calculated from light sensors

### EC compensation for capacitive soil probes

Cheap capacitive probes measure the impedance of the medium. At their low
excitation frequency ionic conduction contributes heavily, so the moisture
channel partly measures the EC: flush a pot or lower the EC of the nutrient
solution and the moisture reading drops although the pot is just as wet.

The integration takes the probe's own EC out of the moisture reading:

```
moisture = raw − factor × ln(EC / 180 µS/cm)
```

Each plant has an **EC compensation factor** (a `number` entity); new plants
start from the default in the integration configuration. `0` disables it. For
Xiaomi/MiFlora probes in coco use **19.7** — the same value for every plant.
With normalisation on, the maximum is taken over the corrected readings, so a
saturated pot still reads 100 %.

**Where the numbers come from.** Eight Xiaomi/MiFlora (HHCCJCY01) probes in
coco, evaluated per irrigation event over two weeks that included lowering the
nutrient EC and a three-day flush that halved the EC in the pots:

- The reading follows the EC the probe itself measures, not the EC of the feed.
- With one factor for all probes the relation is logarithmic, not linear: each
  doubling of the probe EC adds about 13.7 moisture points.
- The effect shows down to the lowest EC measured, 180 µS/cm, without a
  threshold. A logarithm has no zero point, so the reference is that lowest
  measured EC: everything the data show is removed, nothing below it is
  extrapolated. With normalisation the reference only moves the driest values.
- Fitted on the days before the EC change, the correction held the field
  capacity through the flush to within 4.9 points on average (uncorrected 12.3,
  linear 6.8).

A probe that sits at its 100 % ceiling in a wet pot cannot be corrected — the
reading is cut off. Position probes so they read below about 95 when saturated.

### Pore water EC (optional)

The probe reads the EC of the pot as a whole — water, coco and air. Even a pot
flushed with 1640 µS/cm reads about 600, and the reading falls as the pot dries
although no salt leaves. Switching a plant's **conductivity reading** to
`pore_water` converts it to the EC of the solution around the roots:

```
EC_pore = 2.7 × EC_probe / (moisture/100) ^ exponent
```

- **Scale 2.7.** After three days of flushing with 1640 µS/cm, three probes in
  different pots agreed within 3 % at about 600 right after watering.
- **Exponent 2.0**, a `number` entity per plant. Over 176 drying cycles the
  probe EC followed the moisture with an exponent of 2.1. With it the pore value
  stays flat through a cycle — unless the plant concentrates the solution while
  drinking (it rises) or takes up more nutrient than water (it falls), which is
  what the value is there to show. Change it only for a different medium.
- **Moisture** is the normalised reading without the EC correction. Keep
  normalisation on: the division assumes a saturated pot reads 100 %.
- Below 50 % moisture nothing is published; with exponent 2 the division would
  blow the value up.

In this mode the conductivity thresholds are in µS/cm of the solution.

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

### Strain Management
Update cannabis strain and refresh data from Seedfinder:

1. Go to cannabis plant device configuration
2. Enter the exact strain name (Seedfinder PID format)
3. Enable "Force refresh" to update all data including images
4. Strain changes take effect immediately

## 📱 Available Services

The integration provides various services to interact with your cannabis plants:

- `plant.replace_sensor` - Replace sensors for a plant
- `plant.create_plant` - Create a new plant
- `plant.remove_plant` - Remove a plant and all its entities
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

