"""Integration tests for end-to-end tent-plant workflow."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from custom_components.plant import PlantDevice
from custom_components.plant.tent import Tent, JournalEntry, MaintenanceEntry


class TestTentPlantIntegrationWorkflow:
    """Test end-to-end tent-plant integration workflow."""

    @pytest.fixture
    def hass(self):
        """Mock Home Assistant instance."""
        hass = Mock(spec=HomeAssistant)
        hass.data = {}
        hass.config_entries = Mock()
        hass.config_entries.async_update_entry = Mock()
        return hass

    @pytest.fixture
    def tent_config_entry(self):
        """Mock tent config entry."""
        entry = Mock(spec=ConfigEntry)
        entry.data = {
            "plant_info": {
                "tent_id": "tent_0001",
                "name": "Test Tent",
                "device_type": "tent",
                "sensors": [],
                "journal": {"entries": []},
                "maintenance_entries": [],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
        }
        entry.entry_id = "tent_entry_id"
        entry.options = {}
        return entry

    @pytest.fixture
    def plant_config_entry(self):
        """Mock plant config entry."""
        entry = Mock(spec=ConfigEntry)
        entry.data = {
            "plant_info": {
                "plant_id": "plant_0001",
                "name": "Test Plant",
                "device_type": "plant",
                "sensors": [],
            }
        }
        entry.entry_id = "plant_entry_id"
        entry.options = {}
        return entry

    def test_end_to_end_tent_creation_and_plant_assignment(self, hass, tent_config_entry, plant_config_entry):
        """Test complete workflow: create tent, create plant, assign plant to tent."""
        # Create tent
        tent = Tent(hass, tent_config_entry)
        assert tent.tent_id == "tent_0001"
        assert tent.name == "Test Tent"
        assert len(tent.get_sensors()) == 0

        # Add sensors to tent
        tent.add_sensor("sensor.temperature")
        tent.add_sensor("sensor.humidity")
        tent.add_sensor("sensor.illuminance")
        
        assert len(tent.get_sensors()) == 3
        assert "sensor.temperature" in tent.get_sensors()
        assert "sensor.humidity" in tent.get_sensors()
        assert "sensor.illuminance" in tent.get_sensors()

        # Create plant
        with patch('custom_components.plant.PlantDevice._get_next_id'):
            plant = PlantDevice(hass, plant_config_entry)
        
        assert plant.name == "Test Plant"
        assert plant._assigned_tent is None

        # Mock plant sensor methods
        plant.replace_sensors = Mock()
        
        # Assign tent to plant
        plant.change_tent(tent)
        
        # Verify tent assignment
        assert plant._assigned_tent == tent
        assert plant._tent_id == "tent_0001"
        
        # Verify sensors were assigned
        tent.get_sensors.assert_called_once()
        plant.replace_sensors.assert_called_once_with([
            "sensor.temperature", 
            "sensor.humidity", 
            "sensor.illuminance"
        ])

    def test_tent_sensor_modification_and_plant_update(self, hass, tent_config_entry, plant_config_entry):
        """Test workflow: modify tent sensors, verify plant updates."""
        # Create tent with initial sensors
        tent = Tent(hass, tent_config_entry)
        tent.add_sensor("sensor.temperature")
        tent.add_sensor("sensor.humidity")
        
        # Create plant
        with patch('custom_components.plant.PlantDevice._get_next_id'):
            plant = PlantDevice(hass, plant_config_entry)
        
        # Mock plant sensor methods
        plant.replace_sensors = Mock()
        
        # Assign tent to plant
        plant.change_tent(tent)
        plant.replace_sensors.reset_mock()
        
        # Add new sensor to tent
        tent.add_sensor("sensor.illuminance")
        
        # Verify config was updated
        hass.config_entries.async_update_entry.assert_called()
        
        # Change tent again to trigger sensor update
        plant.change_tent(tent)
        
        # Verify plant received updated sensor list
        plant.replace_sensors.assert_called_once_with([
            "sensor.temperature", 
            "sensor.humidity", 
            "sensor.illuminance"
        ])

    def test_tent_journal_and_maintenance_functionality(self, hass, tent_config_entry):
        """Test tent journal and maintenance functionality."""
        # Create tent
        tent = Tent(hass, tent_config_entry)
        
        # Test journal functionality
        journal_entry = JournalEntry("Test journal entry", "Test User")
        tent.add_journal_entry(journal_entry)
        
        journal_entries = tent.get_journal().get_entries()
        assert len(journal_entries) == 1
        assert journal_entries[0].content == "Test journal entry"
        assert journal_entries[0].author == "Test User"
        
        # Test maintenance functionality
        maintenance_entry = MaintenanceEntry("Test maintenance", "Test Technician", 100.50)
        tent.add_maintenance_entry(maintenance_entry)
        
        maintenance_entries = tent.get_maintenance_entries()
        assert len(maintenance_entries) == 1
        assert maintenance_entries[0].description == "Test maintenance"
        assert maintenance_entries[0].performed_by == "Test Technician"
        assert maintenance_entries[0].cost == 100.50
        
        # Verify config was updated
        hass.config_entries.async_update_entry.assert_called()

    def test_plant_reassignment_between_tents(self, hass, tent_config_entry, plant_config_entry):
        """Test workflow: reassign plant between different tents."""
        # Create first tent
        tent1_config = Mock(spec=ConfigEntry)
        tent1_config.data = {
            "plant_info": {
                "tent_id": "tent_0001",
                "name": "Test Tent 1",
                "device_type": "tent",
                "sensors": ["sensor.temperature_1", "sensor.humidity_1"],
                "journal": {"entries": []},
                "maintenance_entries": [],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
        }
        tent1_config.entry_id = "tent1_entry_id"
        tent1_config.options = {}
        tent1 = Tent(hass, tent1_config)
        
        # Create second tent
        tent2_config = Mock(spec=ConfigEntry)
        tent2_config.data = {
            "plant_info": {
                "tent_id": "tent_0002",
                "name": "Test Tent 2",
                "device_type": "tent",
                "sensors": ["sensor.temperature_2", "sensor.illuminance_2"],
                "journal": {"entries": []},
                "maintenance_entries": [],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
        }
        tent2_config.entry_id = "tent2_entry_id"
        tent2_config.options = {}
        tent2 = Tent(hass, tent2_config)
        
        # Create plant
        with patch('custom_components.plant.PlantDevice._get_next_id'):
            plant = PlantDevice(hass, plant_config_entry)
        
        # Mock plant sensor methods
        plant.replace_sensors = Mock()
        
        # Assign first tent to plant
        plant.change_tent(tent1)
        assert plant._assigned_tent == tent1
        plant.replace_sensors.assert_called_once_with(["sensor.temperature_1", "sensor.humidity_1"])
        
        # Reset mock
        plant.replace_sensors.reset_mock()
        
        # Reassign to second tent
        plant.change_tent(tent2)
        assert plant._assigned_tent == tent2
        plant.replace_sensors.assert_called_once_with(["sensor.temperature_2", "sensor.illuminance_2"])

    def test_tent_data_persistence(self, hass, tent_config_entry):
        """Test that tent data is properly persisted."""
        # Create tent
        tent = Tent(hass, tent_config_entry)
        
        # Add sensors
        tent.add_sensor("sensor.temperature")
        tent.add_sensor("sensor.humidity")
        
        # Add journal entry
        journal_entry = JournalEntry("Persistence test entry", "Tester")
        tent.add_journal_entry(journal_entry)
        
        # Add maintenance entry
        maintenance_entry = MaintenanceEntry("Persistence test maintenance", "Tester", 75.0)
        tent.add_maintenance_entry(maintenance_entry)
        
        # Verify config update was called
        hass.config_entries.async_update_entry.assert_called()
        
        # Check that the config data contains the expected information
        call_args = hass.config_entries.async_update_entry.call_args
        assert call_args is not None
        
        updated_config = call_args[1]['data']
        plant_info = updated_config['plant_info']
        
        # Verify sensors are persisted
        assert "sensor.temperature" in plant_info['sensors']
        assert "sensor.humidity" in plant_info['sensors']
        
        # Verify journal entries are persisted
        assert len(plant_info['journal']['entries']) == 1
        assert plant_info['journal']['entries'][0]['content'] == "Persistence test entry"
        
        # Verify maintenance entries are persisted
        assert len(plant_info['maintenance_entries']) == 1
        assert plant_info['maintenance_entries'][0]['description'] == "Persistence test maintenance"
        assert plant_info['maintenance_entries'][0]['cost'] == 75.0