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
channel partly measures the EC: lower the EC of your nutrient solution and the
moisture reading drops although the pot is just as wet. Professional probes run
at 70–100 MHz to separate water from ions; these do not.

Each plant has an **EC compensation factor** (a `number` entity, next to the
lux-to-PPFD factor). It removes the EC term from the reading:

```
moisture = raw − factor × (EC − 1000 µS/cm)
```

`0` disables it, which is the default — nothing changes until you set a factor.
A global starting value for new plants lives in the integration configuration.

| Probe | Sensing | Factor (points per 1000 µS/cm) | Basis |
|---|---|---|---|
| Xiaomi / MiFlora (HHCCJCY01) | capacitive, low excitation frequency | **0.015** (individual probes 0.011–0.046) | 8 probes, 3 days, R² up to 0.98 |
| anything else | unknown | 0 (off) | — |

**Determining your own factor.** Compare the reading at full saturation after
two waterings with clearly different EC, then `factor = Δmoisture / ΔEC`.

Two things will spoil that measurement:

- **A probe sitting near its 100 % ceiling.** Readings are compressed there, and
  they drag the factor down — in our data one probe measured 0.028 including
  those points and 0.046 without them. Exclude everything near the ceiling. A
  probe that often reads 100 should be repositioned anyway: at the stop it
  measures nothing at all.
- **Comparing at different water contents.** Bulk EC falls as the pot dries, so
  read both the moisture and the EC at the same point in the cycle — right after
  watering is the reproducible one.

The 0.015 comes from a single setup in coco. The spread between individual
probes is real, and a different substrate or a different make will need its own
value. If you determine one, please open an issue so this table can grow.

### Pore water EC (optional)

Bulk EC mixes water content and salt content, because dry pores do not conduct —
in our measurements it swung 25–59 % within a single irrigation cycle without
any nutrient being added. Switching a plant's **conductivity reading** to
`pore_water` divides that out:

```
EC_pore = EC_bulk / (moisture/100) ^ exponent
```

The exponent is medium dependent and has its own `number` entity per plant.
Archie/Rhoades suggest 1.3–2.0 for substrates; the default is 1.0. It cannot be
derived from the probe data alone, so tune it against a feed EC you know. Below
15 % moisture the bulk value is published unchanged.

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

