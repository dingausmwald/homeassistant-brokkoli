# Testing Documentation

This document provides detailed information about the testing strategy, structure, and implementation for the Brokkoli Plant Integration.

## Test Structure Overview

The test suite is organized into multiple categories to ensure comprehensive coverage:

```
tests/
├── integration/                 # Integration tests
│   ├── test_consumption_tracking.py
│   ├── test_data_persistence.py
│   ├── test_integration_scenarios.py
│   └── test_sensor_rounding_integration.py
├── unit/                       # Unit tests
│   ├── test_constant_validation.py
│   ├── test_consumption_constants.py
│   ├── test_consumption_sensors.py
│   ├── test_energy_cost.py
│   ├── test_energy_cost_constants.py
│   ├── test_sensor_compile_rounding.py
│   ├── test_sensor_configuration.py
│   ├── test_sensor_value_processing.py
│   ├── test_service_functionality.py
│   ├── test_service_schemas.py
│   └── test_total_consumption_sensors.py
├── tent_specific/              # Tent-specific tests
│   ├── test_tent_consumption_tracking.py
│   ├── test_tent_data_persistence.py
│   ├── test_tent_diagnostics.py
│   ├── test_tent_entity.py
│   ├── test_tent_integration.py
│   ├── test_tent_plant_assignment.py
│   ├── test_tent_sensor_aggregation.py
│   └── test_tent_services.py
├── verification/               # Verification tests
│   ├── test_aggregation_verification.py
│   ├── test_consumption_verification.py
│   ├── test_decimal_verification.py
│   ├── test_dli_verification.py
│   ├── test_entity_verification.py
│   ├── test_growth_phase_verification.py
│   ├── test_integration_verification.py
│   ├── test_light_integration_verification.py
│   ├── test_plant_attributes_verification.py
│   ├── test_plant_device_verification.py
│   ├── test_plant_dli_verification.py
│   ├── test_plant_entity_verification.py
│   ├── test_plant_sensor_verification.py
│   ├── test_sensor_aggregation_verification.py
│   ├── test_sensor_attributes_verification.py
│   ├── test_sensor_compilation_verification.py
│   ├── test_sensor_decimal_verification.py
│   ├── test_sensor_entity_verification.py
│   ├── test_sensor_rounding_verification.py
│   ├── test_sensor_unit_verification.py
│   ├── test_sensor_verification.py
│   ├── test_service_verification.py
│   ├── test_threshold_verification.py
│   └── test_unit_verification.py
├── run_tests.py               # Test runner script
├── test_config_entry_unloading.py
├── test_config_flow_decimals.py
├── test_constant_validation.py
├── test_device_removal.py
├── test_diagnostics.py
├── test_plant_device_dli.py
├── test_plant_entity.py
├── test_plant_tent_assignment.py
├── test_plant_tent_integration.py
├── test_repairs.py
├── test_rounding_applies_current_sensors.py
└── test_sensor_rounding_integration.py
```

## Test Categories

### Unit Tests

Unit tests focus on testing individual components and functions in isolation.

#### Constant Validation Tests
Files: 
- [test_constant_validation.py](file:///d:/Python/2/homeassistant-brokkoli/tests/test_constant_validation.py)
- [unit/test_consumption_constants.py](file:///d:/Python/2/homeassistant-brokkoli/tests/unit/test_consumption_constants.py)
- [unit/test_energy_cost_constants.py](file:///d:/Python/2/homeassistant-brokkoli/tests/unit/test_energy_cost_constants.py)

These tests validate that all required constants are properly defined:
- Basic constants (DOMAIN, sensor attributes, readings, units, icons)
- Device types and service constants
- Aggregation methods
- Consumption-related constants
- Energy cost constants

#### Sensor Tests
Files:
- [unit/test_consumption_sensors.py](file:///d:/Python/2/homeassistant-brokkoli/tests/unit/test_consumption_sensors.py)
- [unit/test_total_consumption_sensors.py](file:///d:/Python/2/homeassistant-brokkoli/tests/unit/test_total_consumption_sensors.py)
- [unit/test_energy_cost.py](file:///d:/Python/2/homeassistant-brokkoli/tests/unit/test_energy_cost.py)

These tests validate sensor functionality:
- Consumption sensor constants and configuration
- Total consumption sensor integration
- Energy cost calculation logic
- Sensor properties and behavior

#### Configuration Tests
Files:
- [unit/test_sensor_configuration.py](file:///d:/Python/2/homeassistant-brokkoli/tests/unit/test_sensor_configuration.py)
- [test_config_flow_decimals.py](file:///d:/Python/2/homeassistant-brokkoli/tests/test_config_flow_decimals.py)

These tests validate configuration handling:
- Sensor decimal configuration
- Config flow decimal handling

#### Value Processing Tests
Files:
- [unit/test_sensor_value_processing.py](file:///d:/Python/2/homeassistant-brokkoli/tests/unit/test_sensor_value_processing.py)
- [test_rounding_applies_current_sensors.py](file:///d:/Python/2/homeassistant-brokkoli/tests/test_rounding_applies_current_sensors.py)

These tests validate value processing:
- Numeric conversion (int/float)
- Edge cases (negative values, decimals, scientific notation)
- Invalid value handling
- Rounding behavior

#### Service Tests
Files:
- [unit/test_service_functionality.py](file:///d:/Python/2/homeassistant-brokkoli/tests/unit/test_service_functionality.py)
- [unit/test_service_schemas.py](file:///d:/Python/2/homeassistant-brokkoli/tests/unit/test_service_schemas.py)

These tests validate service functionality:
- Service constants validation
- Service schema existence

### Integration Tests

Integration tests validate that multiple components work together correctly.

#### Consumption Tracking Tests
File: [integration/test_consumption_tracking.py](file:///d:/Python/2/homeassistant-brokkoli/tests/integration/test_consumption_tracking.py)

Validates consumption tracking functionality:
- Water, fertilizer, and power consumption calculations
- Default consumption values
- Service parameter validation
- Total consumption aggregation

#### Data Persistence Tests
File: [integration/test_data_persistence.py](file:///d:/Python/2/homeassistant-brokkoli/tests/integration/test_data_persistence.py)

Validates data persistence:
- Export/import functionality
- Plant creation persistence
- Configuration persistence
- Sensor and consumption data persistence

#### Integration Scenario Tests
File: [integration/test_integration_scenarios.py](file:///d:/Python/2/homeassistant-brokkoli/tests/integration/test_integration_scenarios.py)

Validates integration scenarios:
- Module imports
- Config flow integration
- Sensor integration
- Service integration
- Data persistence integration
- Consumption integration

#### Sensor Rounding Integration Tests
File: [integration/test_sensor_rounding_integration.py](file:///d:/Python/2/homeassistant-brokkoli/tests/integration/test_sensor_rounding_integration.py)

Validates sensor rounding integration:
- Sensor compilation rounding
- Sensor value processing with rounding

### Tent-Specific Tests

Tent-specific tests validate functionality related to tent entities.

#### Tent Consumption Tracking Tests
File: [tent_specific/test_tent_consumption_tracking.py](file:///d:/Python/2/homeassistant-brokkoli/tests/tent_specific/test_tent_consumption_tracking.py)

Validates tent consumption tracking:
- Tent-level consumption calculations
- Aggregation of plant consumption data

#### Tent Data Persistence Tests
File: [tent_specific/test_tent_data_persistence.py](file:///d:/Python/2/homeassistant-brokkoli/tests/tent_specific/test_tent_data_persistence.py)

Validates tent data persistence:
- Tent configuration persistence
- Tent plant assignment persistence

#### Tent Entity Tests
File: [tent_specific/test_tent_entity.py](file:///d:/Python/2/homeassistant-brokkoli/tests/tent_specific/test_tent_entity.py)

Validates tent entity functionality:
- Tent attributes
- Tent sensor aggregation
- Tent plant management

## Test Implementation Details

### Test Runner

The custom test runner ([run_tests.py](file:///d:/Python/2/homeassistant-brokkoli/tests/run_tests.py)) executes all tests in isolation without requiring a full Home Assistant installation.

### Module Loading

Tests use `importlib` to load modules without importing full HA dependencies:

```python
def _load_module(module_name, file_path):
    """Load a module from a file path."""
    path = Path(file_path).resolve()
    loader = importlib.machinery.SourceFileLoader(module_name, str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    loader.exec_module(module)
    return module
```

### Mocking

Tests create minimal mock objects for Home Assistant components:

```python
def _setup_ha_modules():
    """Set up minimal HA modules for testing."""
    # Only set up modules if they don't already exist
    if "homeassistant.const" not in sys.modules:
        # Inject minimal dummy module for homeassistant.const
        dummy_ha_const = type(sys)("homeassistant.const")
        setattr(dummy_ha_const, "STATE_UNKNOWN", "unknown")
        setattr(dummy_ha_const, "STATE_UNAVAILABLE", "unavailable")
        sys.modules["homeassistant.const"] = dummy_ha_const
```

## New Test Files

### Consumption Constants Tests
File: [unit/test_consumption_constants.py](file:///d:/Python/2/homeassistant-brokkoli/tests/unit/test_consumption_constants.py)

This test file validates all consumption-related constants and configuration:
- Consumption attributes, readings, icons, and units
- Default values for water, fertilizer, and power consumption
- Configuration constants for consumption sensors
- Aggregation methods for different consumption sensor types
- Total consumption constants and aggregation methods
- Aggregation method constants (ORIGINAL, MEAN, MEDIAN, etc.)

### Energy Cost Constants Tests
File: [unit/test_energy_cost_constants.py](file:///d:/Python/2/homeassistant-brokkoli/tests/unit/test_energy_cost_constants.py)

This test file validates energy cost constants and calculation logic:
- Energy cost constants (reading name, icon, kWh price)
- Energy cost configuration constants
- Energy cost calculation logic with various scenarios
- Rounding behavior for currency values
- Edge cases (zero consumption, high consumption)
- Custom price configurations
- Negative consumption values (for energy returned to grid)
- Decimal configuration for energy cost sensors

## Running Tests

### Using the Custom Test Runner

The simplest way to run all tests is using the custom test runner:

```bash
cd homeassistant-brokkoli
python tests/run_tests.py
```

### Running Tests by Category

To run tests within a specific category:

```bash
# Run unit tests
cd homeassistant-brokkoli
python -m pytest tests/unit -v

# Run integration tests
cd homeassistant-brokkoli
python -m pytest tests/integration -v

# Run tent-specific tests
cd homeassistant-brokkoli
python -m pytest tests/tent_specific -v
```

### Running Individual Test Files

Each test file can be executed independently:

```bash
cd homeassistant-brokkoli
python -m pytest tests/unit/test_consumption_constants.py -v
python -m pytest tests/unit/test_energy_cost_constants.py -v
```

## Test Coverage

The test suite aims for comprehensive coverage of all functionality:

- Unit tests: Validate individual functions and components
- Integration tests: Validate component interactions
- Constant validation: Ensure all constants are properly defined
- Edge case testing: Handle boundary conditions and error scenarios
- Configuration testing: Validate all configuration options
- Data persistence: Ensure data is properly stored and retrieved

## Best Practices

### Isolated Testing

Tests should not require a full Home Assistant instance:
- Use module loading instead of direct imports
- Mock external dependencies
- Focus on specific functionality

### Constant Validation

Ensure all constants required by the integration are properly defined:
- Check that [const.py](file:///d:/Python/2/homeassistant-brokkoli/custom_components/plant/const.py) contains all required constants
- Validate that constants are accessible to all modules that import them
- Verify that AGGREGATION_METHODS and AGGREGATION_METHODS_EXTENDED are properly defined

### Comprehensive Coverage

Tests should cover:
- Happy path scenarios
- Error conditions
- Edge cases
- Boundary conditions
- Configuration variations