"""Test for plant status management."""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from datetime import timedelta

from homeassistant.const import STATE_OK, STATE_PROBLEM, STATE_UNKNOWN, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from custom_components.plant import PlantDevice
from custom_components.plant.const import (
    FLOW_PLANT_INFO,
    ATTR_NAME,
    ATTR_DEVICE_TYPE,
    DEVICE_TYPE_PLANT,
    STATE_LOW,
    STATE_HIGH,
)

_LOGGER = logging.getLogger(__name__)


class TestPlantStatus:
    """Test plant status management."""

    @pytest.fixture
    def hass(self):
        """Fixture for Home Assistant instance."""
        return Mock(spec=HomeAssistant)

    @pytest.fixture
    def config_entry(self):
        """Fixture for config entry."""
        config = Mock(spec=ConfigEntry)
        config.data = {
            FLOW_PLANT_INFO: {
                ATTR_NAME: "Test Plant",
                ATTR_DEVICE_TYPE: DEVICE_TYPE_PLANT,
            }
        }
        config.options = {}
        config.entry_id = "test_entry_id"
        return config

    @pytest.fixture
    def plant_device(self, hass, config_entry):
        """Fixture for plant device."""
        with patch("custom_components.plant.PlantDevice._schedule_regular_updates"):
            plant = PlantDevice(hass, config_entry)
        return plant

    def test_initial_state_unknown(self, plant_device):
        """Test that plant starts with UNKNOWN state."""
        assert plant_device.state == STATE_UNKNOWN

    def test_update_with_no_sensors(self, plant_device):
        """Test update with no sensors configured."""
        plant_device.update()
        assert plant_device.state == STATE_UNKNOWN

    def test_update_with_valid_temperature_sensor(self, plant_device):
        """Test update with valid temperature sensor within range."""
        # Setup mock temperature sensor
        temp_sensor = Mock()
        temp_sensor.state = "25.0"
        plant_device.sensor_temperature = temp_sensor

        # Setup temperature thresholds
        min_temp = Mock()
        min_temp.native_value = "10.0"
        plant_device.min_temperature = min_temp

        max_temp = Mock()
        max_temp.native_value = "30.0"
        plant_device.max_temperature = max_temp

        # Update plant status
        plant_device.update()

        # Verify results
        assert plant_device.state == STATE_OK
        assert plant_device.temperature_status == STATE_OK

    def test_update_with_low_temperature_sensor(self, plant_device):
        """Test update with temperature sensor below minimum."""
        # Setup mock temperature sensor
        temp_sensor = Mock()
        temp_sensor.state = "5.0"  # Below minimum
        plant_device.sensor_temperature = temp_sensor

        # Setup temperature thresholds
        min_temp = Mock()
        min_temp.native_value = "10.0"
        plant_device.min_temperature = min_temp

        max_temp = Mock()
        max_temp.native_value = "30.0"
        plant_device.max_temperature = max_temp

        # Update plant status
        plant_device.update()

        # Verify results
        assert plant_device.state == STATE_PROBLEM
        assert plant_device.temperature_status == STATE_LOW

    def test_update_with_high_temperature_sensor(self, plant_device):
        """Test update with temperature sensor above maximum."""
        # Setup mock temperature sensor
        temp_sensor = Mock()
        temp_sensor.state = "35.0"  # Above maximum
        plant_device.sensor_temperature = temp_sensor

        # Setup temperature thresholds
        min_temp = Mock()
        min_temp.native_value = "10.0"
        plant_device.min_temperature = min_temp

        max_temp = Mock()
        max_temp.native_value = "30.0"
        plant_device.max_temperature = max_temp

        # Update plant status
        plant_device.update()

        # Verify results
        assert plant_device.state == STATE_PROBLEM
        assert plant_device.temperature_status == STATE_HIGH

    def test_update_with_unavailable_temperature_sensor(self, plant_device):
        """Test update with unavailable temperature sensor."""
        # Setup mock temperature sensor
        temp_sensor = Mock()
        temp_sensor.state = STATE_UNAVAILABLE
        plant_device.sensor_temperature = temp_sensor

        # Setup temperature thresholds
        min_temp = Mock()
        min_temp.native_value = "10.0"
        plant_device.min_temperature = min_temp

        max_temp = Mock()
        max_temp.native_value = "30.0"
        plant_device.max_temperature = max_temp

        # Update plant status
        plant_device.update()

        # Verify results
        assert plant_device.state == STATE_UNKNOWN

    def test_update_with_invalid_temperature_value(self, plant_device):
        """Test update with invalid temperature value."""
        # Setup mock temperature sensor
        temp_sensor = Mock()
        temp_sensor.state = "invalid"
        plant_device.sensor_temperature = temp_sensor

        # Setup temperature thresholds
        min_temp = Mock()
        min_temp.native_value = "10.0"
        plant_device.min_temperature = min_temp

        max_temp = Mock()
        max_temp.native_value = "30.0"
        plant_device.max_temperature = max_temp

        # Update plant status
        plant_device.update()

        # Verify results (should remain UNKNOWN due to invalid value)
        assert plant_device.state == STATE_UNKNOWN

    def test_update_with_multiple_sensors_all_ok(self, plant_device):
        """Test update with multiple sensors all within range."""
        # Setup mock temperature sensor
        temp_sensor = Mock()
        temp_sensor.state = "25.0"
        plant_device.sensor_temperature = temp_sensor

        # Setup temperature thresholds
        min_temp = Mock()
        min_temp.native_value = "10.0"
        plant_device.min_temperature = min_temp

        max_temp = Mock()
        max_temp.native_value = "30.0"
        plant_device.max_temperature = max_temp

        # Setup mock humidity sensor
        humidity_sensor = Mock()
        humidity_sensor.state = "50.0"
        plant_device.sensor_humidity = humidity_sensor

        # Setup humidity thresholds
        min_humidity = Mock()
        min_humidity.native_value = "40.0"
        plant_device.min_humidity = min_humidity

        max_humidity = Mock()
        max_humidity.native_value = "60.0"
        plant_device.max_humidity = max_humidity

        # Update plant status
        plant_device.update()

        # Verify results
        assert plant_device.state == STATE_OK
        assert plant_device.temperature_status == STATE_OK
        assert plant_device.humidity_status == STATE_OK

    def test_update_with_multiple_sensors_one_problem(self, plant_device):
        """Test update with multiple sensors where one is problematic."""
        # Setup mock temperature sensor (OK)
        temp_sensor = Mock()
        temp_sensor.state = "25.0"
        plant_device.sensor_temperature = temp_sensor

        # Setup temperature thresholds
        min_temp = Mock()
        min_temp.native_value = "10.0"
        plant_device.min_temperature = min_temp

        max_temp = Mock()
        max_temp.native_value = "30.0"
        plant_device.max_temperature = max_temp

        # Setup mock humidity sensor (Problem - too high)
        humidity_sensor = Mock()
        humidity_sensor.state = "70.0"
        plant_device.sensor_humidity = humidity_sensor

        # Setup humidity thresholds
        min_humidity = Mock()
        min_humidity.native_value = "40.0"
        plant_device.min_humidity = min_humidity

        max_humidity = Mock()
        max_humidity.native_value = "60.0"
        plant_device.max_humidity = max_humidity

        # Update plant status
        plant_device.update()

        # Verify results
        assert plant_device.state == STATE_PROBLEM
        assert plant_device.temperature_status == STATE_OK
        assert plant_device.humidity_status == STATE_HIGH

    def test_update_with_disabled_temperature_trigger(self, plant_device):
        """Test update with temperature trigger disabled."""
        # Setup config to disable temperature trigger
        plant_device._config.options = {"temperature_trigger": False}

        # Setup mock temperature sensor (Problematic value)
        temp_sensor = Mock()
        temp_sensor.state = "5.0"  # Below minimum
        plant_device.sensor_temperature = temp_sensor

        # Setup temperature thresholds
        min_temp = Mock()
        min_temp.native_value = "10.0"
        plant_device.min_temperature = min_temp

        max_temp = Mock()
        max_temp.native_value = "30.0"
        plant_device.max_temperature = max_temp

        # Update plant status
        plant_device.update()

        # Verify results - should be OK because trigger is disabled
        assert plant_device.state == STATE_OK
        assert plant_device.temperature_status == STATE_LOW  # Status still set, but doesn't affect overall state

    def test_update_with_ph_sensor(self, plant_device):
        """Test update with pH sensor."""
        # Setup mock pH sensor
        ph_sensor = Mock()
        ph_sensor.state = "6.5"
        plant_device.sensor_ph = ph_sensor

        # Setup pH thresholds
        min_ph = Mock()
        min_ph.native_value = "5.5"
        plant_device.min_ph = min_ph

        max_ph = Mock()
        max_ph.native_value = "7.5"
        plant_device.max_ph = max_ph

        # Update plant status
        plant_device.update()

        # Verify results
        assert plant_device.state == STATE_OK
        assert plant_device.ph_status == STATE_OK

    def test_update_with_low_ph_sensor(self, plant_device):
        """Test update with pH sensor below minimum."""
        # Setup mock pH sensor
        ph_sensor = Mock()
        ph_sensor.state = "5.0"  # Below minimum
        plant_device.sensor_ph = ph_sensor

        # Setup pH thresholds
        min_ph = Mock()
        min_ph.native_value = "5.5"
        plant_device.min_ph = min_ph

        max_ph = Mock()
        max_ph.native_value = "7.5"
        plant_device.max_ph = max_ph

        # Update plant status
        plant_device.update()

        # Verify results
        assert plant_device.state == STATE_PROBLEM
        assert plant_device.ph_status == STATE_LOW

    def test_update_with_high_ph_sensor(self, plant_device):
        """Test update with pH sensor above maximum."""
        # Setup mock pH sensor
        ph_sensor = Mock()
        ph_sensor.state = "8.0"  # Above maximum
        plant_device.sensor_ph = ph_sensor

        # Setup pH thresholds
        min_ph = Mock()
        min_ph.native_value = "5.5"
        plant_device.min_ph = min_ph

        max_ph = Mock()
        max_ph.native_value = "7.5"
        plant_device.max_ph = max_ph

        # Update plant status
        plant_device.update()

        # Verify results
        assert plant_device.state == STATE_PROBLEM
        assert plant_device.ph_status == STATE_HIGH

    def test_update_with_disabled_ph_trigger(self, plant_device):
        """Test update with pH trigger disabled."""
        # Setup config to disable pH trigger
        plant_device._config.options = {"ph_trigger": False}

        # Setup mock pH sensor (Problematic value)
        ph_sensor = Mock()
        ph_sensor.state = "5.0"  # Below minimum
        plant_device.sensor_ph = ph_sensor

        # Setup pH thresholds
        min_ph = Mock()
        min_ph.native_value = "5.5"
        plant_device.min_ph = min_ph

        max_ph = Mock()
        max_ph.native_value = "7.5"
        plant_device.max_ph = max_ph

        # Update plant status
        plant_device.update()

        # Verify results - should be OK because trigger is disabled
        assert plant_device.state == STATE_OK
        assert plant_device.ph_status == STATE_LOW  # Status still set, but doesn't affect overall state

    def test_schedule_regular_updates(self, plant_device, hass):
        """Test that regular updates are scheduled."""
        with patch("custom_components.plant.async_track_time_interval") as mock_track:
            plant_device._schedule_regular_updates()
            
            # Verify that async_track_time_interval was called
            mock_track.assert_called_once()
            
            # Verify the interval is 30 seconds
            args = mock_track.call_args
            assert args[0][2] == timedelta(seconds=30)

    def test_debounce_no_change_without_time_passing(self, plant_device):
        """Test that debounce prevents state changes when time hasn't passed."""
        # Setup config with debounce time
        plant_device._config.options = {"status_debounce_time": 5}
        plant_device._status_debounce_time = 5
        plant_device._pending_status = None
        plant_device._last_status_change = None
        
        # Setup mock temperature sensor (Problematic value)
        temp_sensor = Mock()
        temp_sensor.state = "5.0"  # Below minimum
        plant_device.sensor_temperature = temp_sensor

        # Setup temperature thresholds
        min_temp = Mock()
        min_temp.native_value = "10.0"
        plant_device.min_temperature = min_temp

        max_temp = Mock()
        max_temp.native_value = "30.0"
        plant_device.max_temperature = max_temp

        # Initial state should be UNKNOWN
        assert plant_device.state == STATE_UNKNOWN

        # Update plant status - should set pending status but not change actual state
        plant_device.update()
        
        # Should have pending status but actual state should remain UNKNOWN
        assert plant_device._pending_status == STATE_PROBLEM
        assert plant_device.state == STATE_UNKNOWN

    def test_debounce_change_after_time_passing(self, plant_device):
        """Test that debounce allows state changes after time has passed."""
        import datetime
        from unittest.mock import patch
        
        # Setup config with debounce time
        plant_device._config.options = {"status_debounce_time": 5}
        plant_device._status_debounce_time = 5
        plant_device._pending_status = STATE_PROBLEM
        
        # Mock datetime to simulate time passing
        mock_now = datetime.datetime.now()
        plant_device._last_status_change = mock_now - datetime.timedelta(seconds=6)  # 6 seconds ago
        
        # Setup mock temperature sensor (Problematic value)
        temp_sensor = Mock()
        temp_sensor.state = "5.0"  # Below minimum
        plant_device.sensor_temperature = temp_sensor

        # Setup temperature thresholds
        min_temp = Mock()
        min_temp.native_value = "10.0"
        plant_device.min_temperature = min_temp

        max_temp = Mock()
        max_temp.native_value = "30.0"
        plant_device.max_temperature = max_temp

        # Initial state should be UNKNOWN
        assert plant_device.state == STATE_UNKNOWN

        # Update plant status - should apply pending status since debounce time has passed
        plant_device.update()
        
        # Should have applied the pending status
        assert plant_device.state == STATE_PROBLEM
        assert plant_device._pending_status is None

    def test_hysteresis_no_change_near_threshold(self, plant_device):
        """Test that hysteresis prevents state changes when values are near thresholds."""
        # Setup config with hysteresis
        plant_device._config.options = {"hysteresis_percentage": 10.0}
        plant_device._hysteresis_percentage = 10.0
        plant_device.temperature_status = STATE_LOW  # Previously low
        
        # Setup mock temperature sensor (near minimum threshold)
        temp_sensor = Mock()
        temp_sensor.state = "11.0"  # Just above minimum with hysteresis
        plant_device.sensor_temperature = temp_sensor

        # Setup temperature thresholds
        min_temp = Mock()
        min_temp.native_value = "10.0"
        plant_device.min_temperature = min_temp

        max_temp = Mock()
        max_temp.native_value = "30.0"
        plant_device.max_temperature = max_temp

        # Test hysteresis checking
        result = plant_device._check_sensor_with_hysteresis(11.0, 10.0, 30.0, STATE_LOW, STATE_LOW, STATE_HIGH, STATE_OK)
        
        # Should remain LOW due to hysteresis
        assert result == STATE_LOW

    def test_hysteresis_change_when_clearly_out_of_range(self, plant_device):
        """Test that hysteresis allows state changes when values are clearly out of range."""
        # Setup config with hysteresis
        plant_device._config.options = {"hysteresis_percentage": 10.0}
        plant_device._hysteresis_percentage = 10.0
        plant_device.temperature_status = STATE_LOW  # Previously low
        
        # Setup mock temperature sensor (well above minimum threshold)
        temp_sensor = Mock()
        temp_sensor.state = "15.0"  # Well above minimum with hysteresis
        plant_device.sensor_temperature = temp_sensor

        # Setup temperature thresholds
        min_temp = Mock()
        min_temp.native_value = "10.0"
        plant_device.min_temperature = min_temp

        max_temp = Mock()
        max_temp.native_value = "30.0"
        plant_device.max_temperature = max_temp

        # Test hysteresis checking
        result = plant_device._check_sensor_with_hysteresis(15.0, 10.0, 30.0, STATE_LOW, STATE_LOW, STATE_HIGH, STATE_OK)
        
        # Should change to OK since it's clearly in range
        assert result == STATE_OK

    def test_stabilization_window_no_trigger_immediately(self, plant_device):
        """Test that stabilization window prevents immediate problem triggering."""
        # Setup config with stabilization window
        plant_device._config.options = {"stabilization_window": 10}
        plant_device._stabilization_window = 10
        
        # Test stabilization checking - first time seeing issue
        is_stabilized = plant_device._check_sensor_stabilization("temperature", True)
        
        # Should not be stabilized yet (first occurrence)
        assert is_stabilized == False

    def test_stabilization_window_trigger_after_time(self, plant_device):
        """Test that stabilization window allows triggering after sufficient time."""
        import datetime
        
        # Setup config with stabilization window
        plant_device._config.options = {"stabilization_window": 10}
        plant_device._stabilization_window = 10
        
        # Record first occurrence
        plant_device._check_sensor_stabilization("temperature", True)
        
        # Simulate time passing by manually setting the recorded time
        import datetime
        mock_now = datetime.datetime.now()
        plant_device._sensor_issue_times["temperature"] = mock_now - datetime.timedelta(seconds=15)  # 15 seconds ago
        
        # Test stabilization checking again
        is_stabilized = plant_device._check_sensor_stabilization("temperature", True)
        
        # Should be stabilized now (time has passed)
        assert is_stabilized == True

if __name__ == "__main__":
    pytest.main([__file__])