# Supported Devices

This document describes known supported and unsupported devices for the Brokkoli Plant Manager integration.

## Supported Sensor Types

### Temperature Sensors
- **Generic Temperature Sensors**: Any Home Assistant compatible temperature sensor
- **MiFlora Sensors**: Xiaomi MiFlora plant sensors
- **ESPHome Temperature Sensors**: Custom ESPHome-based temperature sensors
- **Zigbee Temperature Sensors**: Zigbee-based temperature sensors (Aqara, etc.)
- **Z-Wave Temperature Sensors**: Z-Wave temperature sensors

### Soil Moisture Sensors
- **Generic Moisture Sensors**: Any Home Assistant compatible moisture sensor
- **MiFlora Sensors**: Xiaomi MiFlora plant sensors (moisture channel)
- **ESPHome Moisture Sensors**: Custom ESPHome-based moisture sensors
- **Analog Soil Moisture Sensors**: Basic analog moisture sensors with ADC conversion
- **Capacitive Moisture Sensors**: More accurate capacitive soil moisture sensors

### Soil Conductivity Sensors
- **Generic Conductivity Sensors**: Any Home Assistant compatible conductivity sensor
- **MiFlora Sensors**: Xiaomi MiFlora plant sensors (conductivity channel)
- **ESPHome Conductivity Sensors**: Custom ESPHome-based conductivity sensors
- **Atlas Scientific Conductivity Sensors**: Professional-grade conductivity sensors

### Light Sensors (Illuminance)
- **Generic Light Sensors**: Any Home Assistant compatible illuminance sensor
- **MiFlora Sensors**: Xiaomi MiFlora plant sensors (light channel)
- **ESPHome Light Sensors**: Custom ESPHome-based light sensors
- **Lux Sensors**: Dedicated lux measurement sensors
- **PAR Sensors**: Photosynthetically Active Radiation sensors (with conversion)

### Humidity Sensors
- **Generic Humidity Sensors**: Any Home Assistant compatible humidity sensor
- **DHT Sensors**: DHT11, DHT22, and similar temperature/humidity sensors
- **BME280 Sensors**: Combined temperature/humidity/pressure sensors
- **ESPHome Humidity Sensors**: Custom ESPHome-based humidity sensors
- **Zigbee Humidity Sensors**: Zigbee-based humidity sensors

### CO2 Sensors
- **Generic CO2 Sensors**: Any Home Assistant compatible CO2 sensor
- **MH-Z19 Sensors**: Popular infrared CO2 sensors
- **SenseAir S8 Sensors**: Another common infrared CO2 sensor
- **ESPHome CO2 Sensors**: Custom ESPHome-based CO2 sensors
- **Zigbee CO2 Sensors**: Zigbee-based CO2 sensors

### Power Consumption Sensors
- **Generic Power Sensors**: Any Home Assistant compatible power consumption sensor
- **Shelly EM/3EM**: Shelly energy meters
- **TP-Link Smart Plugs**: Kasa smart plugs with energy monitoring
- **Zigbee Power Meters**: Zigbee-based power consumption sensors
- **ESPHome Power Sensors**: Custom ESPHome-based power sensors

### pH Sensors
- **Generic pH Sensors**: Any Home Assistant compatible pH sensor
- **Atlas Scientific pH Sensors**: Professional-grade pH sensors
- **ESPHome pH Sensors**: Custom ESPHome-based pH sensors
- **Analog pH Sensors**: Basic analog pH sensors with ADC conversion

## Supported Actuators

### Watering Systems
- **Generic Switches**: Any Home Assistant compatible switch
- **Shelly Switches**: Shelly 1, 2.5, etc.
- **Sonoff Switches**: Sonoff Basic, RF, etc.
- **Zigbee Switches**: Zigbee-based smart switches
- **Relay Modules**: ESPHome-based relay modules

### Environmental Controls
- **Fans**: Any smart fan or switch-controlled fan
- **Heaters**: Any smart heater or switch-controlled heater
- **Humidifiers**: Any Home Assistant compatible humidifier
- **Dehumidifiers**: Any Home Assistant compatible dehumidifier
- **Grow Lights**: Any smart light or switch-controlled grow light

## Supported Communication Protocols

### Wired Protocols
- **Wi-Fi**: Most common wireless protocol
- **Ethernet**: Wired network connections
- **RS485**: Industrial communication protocol
- **Modbus**: Industrial communication protocol

### Wireless Protocols
- **Zigbee**: Supported through Zigbee2MQTT or ZHA
- **Z-Wave**: Supported through the Z-Wave integration
- **Bluetooth**: Limited support through Bluetooth integration
- **LoRa**: Custom implementations through ESPHome
- **RF433**: Simple radio frequency communication

### Home Automation Hubs
- **Home Assistant**: Native support
- **ESPHome**: Direct integration through ESPHome
- **Zigbee2MQTT**: MQTT-based Zigbee integration
- **ZHA**: Native Zigbee integration
- **OpenHAB**: Through MQTT or other protocols

## Supported Platforms

### Single Board Computers
- **Raspberry Pi**: All models with sufficient performance
- **ODROID**: Various models
- **ASUS Tinker Board**: Supported platforms
- **Libre Computer**: ROC-RK3328-CC and similar

### x86 Systems
- **Intel NUC**: Various models
- **Mini PCs**: Generic x86 mini computers
- **Desktop Systems**: Standard desktop computers
- **Server Systems**: Dedicated server hardware

### Virtualization
- **Docker**: Containerized deployment
- **Virtual Machines**: VM-based deployments
- **Proxmox**: Virtualization platform support
- **VMware**: Enterprise virtualization support

## Known Unsupported Devices

### Proprietary Systems
- **Proprietary Plant Monitors**: Devices that don't expose data through standard protocols
- **Closed Ecosystem Devices**: Devices that only work within their own ecosystem
- **Cloud-Only Devices**: Devices that require cloud connectivity for operation

### Incompatible Sensors
- **Sensors without Standard Interfaces**: Devices that don't support common communication protocols
- **Sensors with Proprietary Software**: Devices that require specific software to operate
- **Sensors with Limited Integration**: Devices that don't integrate well with Home Assistant

### Hardware Limitations
- **Devices Requiring Specialized Hardware**: Equipment that needs specific hardware interfaces
- **Industrial Equipment without Connectivity**: Professional equipment without network connectivity
- **Legacy Equipment**: Older equipment without modern communication capabilities

## Device Compatibility Notes

### MiFlora Sensors
- **Advantages**: All-in-one solution for basic plant monitoring
- **Limitations**: Limited update frequency, battery life concerns
- **Recommendations**: Good for basic monitoring but consider more frequent updates needed

### ESPHome-Based Sensors
- **Advantages**: Highly customizable, good update frequency, low cost
- **Limitations**: Requires development knowledge for custom implementations
- **Recommendations**: Best for users comfortable with DIY electronics

### Zigbee/Z-Wave Sensors
- **Advantages**: Reliable mesh networking, good battery life
- **Limitations**: Requires compatible hub, may have vendor lock-in
- **Recommendations**: Good for larger installations with existing hubs

### Professional Sensors
- **Advantages**: High accuracy, reliability, professional features
- **Limitations**: Higher cost, may require specialized integration
- **Recommendations**: Best for commercial or serious hobbyist applications

## Integration Recommendations

### For Beginners
1. Start with MiFlora sensors for basic monitoring
2. Use simple switch-controlled watering systems
3. Consider Zigbee-based sensors if you have a Zigbee hub
4. Begin with a small number of plants

### For Intermediate Users
1. Implement ESPHome-based custom sensors for better control
2. Use more sophisticated watering systems with flow meters
3. Add environmental controls for temperature and humidity
4. Implement basic automations for plant care

### For Advanced Users
1. Use professional-grade sensors for maximum accuracy
2. Implement custom control algorithms
3. Add advanced data analysis and visualization
4. Integrate with other systems for comprehensive monitoring

## Troubleshooting Device Issues

### Common Compatibility Problems
1. **Update Frequency**: Some sensors update infrequently; check sensor specifications
2. **Data Accuracy**: Calibrate sensors according to manufacturer instructions
3. **Communication Issues**: Ensure proper network connectivity and protocol support
4. **Power Requirements**: Verify adequate power supply for all devices

### Device Selection Guidelines
1. **Check Home Assistant Compatibility**: Ensure devices are compatible with Home Assistant
2. **Consider Update Frequency**: Select sensors with appropriate update intervals
3. **Evaluate Accuracy Requirements**: Choose sensors that meet your accuracy needs
4. **Assess Power Requirements**: Consider battery life and power consumption
5. **Plan for Scalability**: Choose devices that can scale with your installation

This list of supported devices is not exhaustive but represents the most commonly used and tested devices with the Brokkoli Plant Manager integration. New devices are continuously being tested and added to the supported list.