# Tent Class Design Principles

## Overview

This document outlines the design principles for the Tent class in the Home Assistant Brokkoli integration, specifically addressing the separation of concerns between Tent entities and Plant entities.

## Design Principle: Separation of Concerns

The Tent class is designed to focus exclusively on environmental monitoring and maintenance operations, without any plant-specific growth metrics. This clear separation ensures that:

1. **Tents** manage the growing environment (sensors, maintenance, journaling)
2. **Plants** manage growth metrics (flowering duration, pot size, water capacity)

## Tent Class Responsibilities

The Tent class is responsible for:

### 1. Sensor Management
- Storing and managing a list of environmental sensors
- Providing sensor mapping capabilities for plant assignment
- Supporting addition and removal of sensors

### 2. Maintenance Operations
- Recording maintenance activities with timestamps and descriptions
- Tracking maintenance costs
- Providing maintenance history

### 3. Documentation
- Maintaining a journal of events and observations
- Supporting text-based documentation entries

### 4. Device Integration
- Proper Home Assistant device registration
- Entity management and state reporting

## Plant-Specific Attributes (Excluded from Tent)

The following plant-specific attributes are intentionally **NOT** included in the Tent class:

### Growth Metrics
- `flowering_duration` - Duration of flowering phase (plant-specific)
- `pot_size` - Size of the planting container (plant-specific)
- `water_capacity` - Water holding capacity of the growing medium (plant-specific)

### Growth Aggregations
- `flowering_duration_aggregation` - Method for aggregating flowering duration data
- `pot_size_aggregation` - Method for aggregating pot size data
- `water_capacity_aggregation` - Method for aggregating water capacity data

## Rationale

This design follows the project specification that "The Tent class should only focus on maintenance and sensor management rather than growth metrics. It should not contain plant-specific methods such as add_pot_size, add_water_capacity, add_flowering_duration, etc."

### Benefits
1. **Clear Separation**: Each entity type has distinct responsibilities
2. **Maintainability**: Changes to plant growth metrics don't affect tent implementations
3. **Scalability**: Tents can be shared among multiple plants without conflicts
4. **Logical Consistency**: Environmental monitoring is separate from biological growth tracking

## Implementation Verification

Code analysis confirms that:
- The Tent class in `tent.py` contains only environment-related attributes and methods
- Plant-specific attributes are exclusively in the PlantDevice class in `__init__.py`
- No plant growth metrics are present in the Tent class

## Conclusion

The current implementation correctly separates Tent responsibilities from Plant responsibilities, ensuring that Tents focus solely on environmental monitoring and maintenance without any plant-specific growth metrics.