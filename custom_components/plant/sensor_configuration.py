"""Central sensor configuration for the Plant integration.

This module centralizes per-sensor defaults and formatting behaviors
such as decimal places for rounding and display.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class SensorDecimalConfig:
    """Configuration for decimal places per sensor type."""

    decimals: int


# Default decimal settings per logical sensor key used in this integration
DEFAULT_DECIMALS: Dict[str, SensorDecimalConfig] = {
    # Base sensors
    "temperature": SensorDecimalConfig(decimals=1),
    "moisture": SensorDecimalConfig(decimals=1),
    "conductivity": SensorDecimalConfig(decimals=0),
    "illuminance": SensorDecimalConfig(decimals=0),
    "humidity": SensorDecimalConfig(decimals=1),
    "CO2": SensorDecimalConfig(decimals=0),
    "ph": SensorDecimalConfig(decimals=2),
    # Calculated sensors
    "ppfd": SensorDecimalConfig(decimals=0),
    "dli": SensorDecimalConfig(decimals=2),
    "total_integral": SensorDecimalConfig(decimals=0),
    # Consumption sensors
    "moisture_consumption": SensorDecimalConfig(decimals=3),
    "total_water_consumption": SensorDecimalConfig(decimals=2),
    "fertilizer_consumption": SensorDecimalConfig(decimals=3),
    "total_fertilizer_consumption": SensorDecimalConfig(decimals=2),
    "power_consumption": SensorDecimalConfig(decimals=0),
    "total_power_consumption": SensorDecimalConfig(decimals=0),
    # Costs
    "energy_cost": SensorDecimalConfig(decimals=2),
}


def get_decimals_for(sensor_type: str, overrides: Dict[str, int] | None = None) -> int:
    """Return decimals for sensor type, with optional overrides.

    overrides: mapping from sensor_type to decimals
    """
    if overrides and sensor_type in overrides:
        override_value = overrides.get(sensor_type)
        try:
            if override_value is None:
                raise TypeError("override is None")
            coerced = int(override_value)
            return max(0, coerced)
        except (TypeError, ValueError):
            # Fall back to defaults on invalid override values
            pass
    config = DEFAULT_DECIMALS.get(sensor_type)
    return config.decimals if config else 2

