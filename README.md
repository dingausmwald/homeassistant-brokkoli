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

### Moisture normalisation

A capacitive probe's raw number is not a water content. The integration
scales it against the pot's own full-and-drained state: the percentile of
the raw readings over a rolling window, which is the reading after an
irrigation has run to drain. The published value is that ratio, so a
saturated pot reads 100 % and the number below it is the dryback.

```
moisture = raw / percentile(field capacity readings) × 100
```

The readings it takes that percentile over are the ones where the pot stood at
field capacity. Every shot that runs to drain leaves the same signature: a rise
within a few minutes, a peak while the solution still flows past the probe, and
a fall back as the excess drains. Over 356 waterings on eight probes that peak
sat 0.6 to 1.4 minutes from the valve closing. The pot is at field capacity once
it has settled, 80 to 120 minutes later. The percentile is taken over that one
watering: the most recent whose settling window has passed and holds enough
readings.

There is no second path. A fallback to the percentile over the whole window
would be invisible from the outside and could quietly become the only path if
detection stopped working. A plant whose window holds no watering — freshly
potted into moist medium and not yet watered — publishes no moisture until it
has been watered once. A restart is not such a case: the reference is rebuilt
from the recorder, which holds far more than the window.

Three `number` entities per plant set it: the window in days, the
percentile, and whether to normalise at all. Steering on the dryback from
field capacity is the usual practice in coco, and it needs no absolute
calibration of the probe.

Two limits worth knowing. A probe that sits at its 100 % ceiling in a wet
pot cannot be scaled at all, because the reading is cut off and the pot
never shows a full state — position probes so they read below about 95 when
saturated. And after a step change in the feed EC the percentile carries the
old readings for the length of the window, so the published value reads low
until the window has turned over. An irrigation automation driven by this
value needs its own cap on waterings per day; without one, a low reading
and an automatic refill reinforce each other.

Earlier versions also subtracted an EC term from the reading, on the grounds
that the moisture channel partly measures salinity. It was removed in
2026.11.6: the subtraction moved the scale's zero point to an arbitrary
place, which put a healthy plant at 0 % while its probe still read 31 of 71.
The cross-sensitivity is real, but it cannot be separated from the drying in
a pot, where EC and water content always move together.

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
- **Moisture** is the normalised reading. Keep normalisation on: the division
  assumes a saturated pot reads 100 %.
- The published value is a **trailing 30 min median**, fixed, no setting. The
  water reaches the probe before the dissolved salts do: after a shot the
  moisture channel is up within three minutes while the EC channel sits still
  for another four and then jumps. Dividing one by the other in that window
  throws the estimate off by 15 % upwards, median over eight probes; the median
  leaves 3 %, and costs nothing in the settled part of a cycle.
- The estimate gets noisier the drier the pot, because the divisor shrinks
  faster than the probe EC falls, and a single exponent over-corrects at the
  dry end. It is published anyway; only a moisture of zero leaves nothing to
  divide by. Earlier versions suppressed everything below 50 % moisture, which
  blanked the series for hours on a pot that dries deep.

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

