# Automation Examples

This document provides automation examples that users can use with the Brokkoli Plant Manager integration.

## Basic Plant Monitoring

### Send Notification When Plant Has Problems
```yaml
alias: "Plant Problem Alert"
description: "Send notification when any plant has problems"
mode: single
trigger:
  - platform: state
    entity_id: plant.*
    attribute: problem
    from: "ok"
    to: "low"
  - platform: state
    entity_id: plant.*
    attribute: problem
    from: "ok"
    to: "high"
condition: []
action:
  - service: notify.mobile_app_your_phone
    data:
      message: "Plant {{ trigger.entity_id }} has a problem: {{ states(trigger.entity_id) }}"
      title: "Plant Problem Detected"
```

### Adjust Lighting Based on DLI
```yaml
alias: "Adjust Lighting for Optimal DLI"
description: "Adjust grow light intensity based on DLI progress"
mode: single
trigger:
  - platform: time_pattern
    minutes: "/30"
condition:
  - condition: time
    after: "06:00:00"
    before: "22:00:00"
action:
  - service: light.turn_on
    data:
      entity_id: light.grow_light
      brightness_pct: >
        {% set dli = states('sensor.plant_dli') | float(0) %}
        {% set target_dli = 25 %}
        {% set progress = dli / target_dli * 100 %}
        {% if progress < 50 %}80
        {% elif progress < 75 %}60
        {% elif progress < 90 %}40
        {% else %}20
        {% endif %}
```

## Watering Automation

### Automated Watering Based on Soil Moisture
```yaml
alias: "Automated Plant Watering"
description: "Water plant when soil moisture drops below threshold"
mode: single
trigger:
  - platform: numeric_state
    entity_id: sensor.plant_soil_moisture
    below: 30
condition:
  - condition: time
    after: "08:00:00"
    before: "20:00:00"
action:
  - service: switch.turn_on
    data:
      entity_id: switch.water_pump
  - delay: "00:00:30"
  - service: switch.turn_off
    data:
      entity_id: switch.water_pump
  - service: plant.add_watering
    data:
      entity_id: plant.my_plant
      amount_liters: 0.5
```

### Watering Schedule
```yaml
alias: "Scheduled Plant Watering"
description: "Water plants on a schedule"
mode: single
trigger:
  - platform: time
    at: "08:00:00"
condition:
  - condition: state
    entity_id: binary_sensor.weekday
    state: "on"
action:
  - service: switch.turn_on
    data:
      entity_id: switch.water_pump
  - delay: "00:00:45"
  - service: switch.turn_off
    data:
      entity_id: switch.water_pump
  - service: plant.add_watering
    data:
      entity_id: plant.my_plant
      amount_liters: 0.75
```

## Environmental Control

### Temperature Control
```yaml
alias: "Plant Temperature Control"
description: "Control environment based on plant temperature"
mode: single
trigger:
  - platform: numeric_state
    entity_id: sensor.plant_temperature
    above: 28
  - platform: numeric_state
    entity_id: sensor.plant_temperature
    below: 20
condition: []
action:
  - choose:
      - conditions:
          - condition: numeric_state
            entity_id: sensor.plant_temperature
            above: 28
        sequence:
          - service: switch.turn_on
            data:
              entity_id: switch.fan
          - service: notify.mobile_app_your_phone
            data:
              message: "Plant temperature is high: {{ states('sensor.plant_temperature') }}°C"
              title: "Temperature Alert"
      - conditions:
          - condition: numeric_state
            entity_id: sensor.plant_temperature
            below: 20
        sequence:
          - service: switch.turn_on
            data:
              entity_id: switch.heater
          - service: notify.mobile_app_your_phone
            data:
              message: "Plant temperature is low: {{ states('sensor.plant_temperature') }}°C"
              title: "Temperature Alert"
```

### Humidity Control
```yaml
alias: "Plant Humidity Control"
description: "Control humidity based on plant needs"
mode: single
trigger:
  - platform: numeric_state
    entity_id: sensor.plant_air_humidity
    above: 65
  - platform: numeric_state
    entity_id: sensor.plant_air_humidity
    below: 45
condition: []
action:
  - choose:
      - conditions:
          - condition: numeric_state
            entity_id: sensor.plant_air_humidity
            above: 65
        sequence:
          - service: switch.turn_on
            data:
              entity_id: switch.dehumidifier
      - conditions:
          - condition: numeric_state
            entity_id: sensor.plant_air_humidity
            below: 45
        sequence:
          - service: switch.turn_on
            data:
              entity_id: switch.humidifier
```

## Tent Management

### Assign Plants to Tent
```yaml
alias: "Assign Plants to Tent"
description: "Automatically assign new plants to a tent"
mode: single
trigger:
  - platform: event
    event_type: call_service
    event_data:
      domain: plant
      service: create_plant
condition: []
action:
  - service: plant.change_tent
    data:
      entity_id: "{{ trigger.event.data.entity_id }}"
      tent_name: "My Grow Tent"
```

### Tent Environment Monitoring
```yaml
alias: "Tent Environment Monitoring"
description: "Monitor and control tent environment"
mode: single
trigger:
  - platform: time_pattern
    minutes: "/15"
condition: []
action:
  - service: plant.list_tents
    data: {}
  - service: notify.mobile_app_your_phone
    data:
      message: >
        Tent Status:
        Temperature: {{ states('sensor.tent_temperature') }}°C
        Humidity: {{ states('sensor.tent_humidity') }}%
        CO2: {{ states('sensor.tent_co2') }}ppm
      title: "Tent Environment Report"
```

## Data Management

### Export Plants Weekly
```yaml
alias: "Weekly Plant Export"
description: "Export plant data weekly for backup"
mode: single
trigger:
  - platform: time
    at: "02:00:00"
    weekdays:
      - sun
condition: []
action:
  - service: plant.export_plants
    data:
      plant_entities:
        - plant.my_plant
        - plant.my_other_plant
      file_path: "/config/backups/plants_{{ now().strftime('%Y%m%d') }}.zip"
      include_images: true
      include_sensor_data: true
      sensor_data_days: 30
```

### Import Plants on Startup
```yaml
alias: "Import Plants on Startup"
description: "Import plant data on Home Assistant startup"
mode: single
trigger:
  - platform: homeassistant
    event: start
condition: []
action:
  - service: plant.import_plants
    data:
      file_path: "/config/backups/latest_plants.zip"
      include_images: true
      overwrite_existing: false
```

## Advanced Automations

### Growth Phase Transition
```yaml
alias: "Plant Growth Phase Transition"
description: "Automatically transition plant growth phases"
mode: single
trigger:
  - platform: numeric_state
    entity_id: sensor.plant_flowering_duration
    above: 49
condition:
  - condition: state
    entity_id: plant.my_plant
    attribute: growth_phase
    state: "growing"
action:
  - service: plant.update_plant_attributes
    data:
      entity_id: plant.my_plant
      growth_phase: "flowering"
```

### Health Monitoring
```yaml
alias: "Plant Health Monitoring"
description: "Monitor plant health and send alerts"
mode: single
trigger:
  - platform: numeric_state
    entity_id: sensor.plant_health
    below: 3
condition: []
action:
  - service: notify.mobile_app_your_phone
    data:
      message: "Plant health is declining: {{ states('sensor.plant_health') }}/5"
      title: "Plant Health Alert"
```

### Consumption Tracking
```yaml
alias: "Track Water Consumption"
description: "Track and report water consumption"
mode: single
trigger:
  - platform: time
    at: "20:00:00"
condition: []
action:
  - service: notify.mobile_app_your_phone
    data:
      message: >
        Daily Water Consumption:
        {{ states('sensor.plant_total_water_consumption') }}L
        Cost: €{{ (states('sensor.plant_total_water_consumption') | float * 0.002) | round(2) }}
      title: "Daily Water Report"
```

### Light Scheduling
```yaml
alias: "Plant Light Schedule"
description: "Control plant lighting schedule"
mode: single
trigger:
  - platform: time
    at: "06:00:00"
  - platform: time
    at: "22:00:00"
condition: []
action:
  - choose:
      - conditions:
          - condition: time
            after: "06:00:00"
            before: "22:00:00"
        sequence:
          - service: light.turn_on
            data:
              entity_id: light.grow_light
              brightness_pct: 100
      - conditions:
          - condition: or
            conditions:
              - condition: time
                after: "22:00:00"
              - condition: time
                before: "06:00:00"
        sequence:
          - service: light.turn_off
            data:
              entity_id: light.grow_light
```

These automation examples can be customized to fit your specific setup and requirements. Remember to replace entity IDs with your actual entity IDs and adjust values according to your plants' needs.