"""Test for the Tent entity."""

import pytest
from datetime import datetime
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from custom_components.plant.tent import Tent, JournalEntry, Journal, MaintenanceEntry


def test_journal_entry_creation():
    """Test creating a journal entry."""
    entry = JournalEntry("Test entry", "Test Author")
    assert entry.content == "Test entry"
    assert entry.author == "Test Author"
    assert isinstance(entry.timestamp, datetime)


def test_journal_entry_to_dict():
    """Test converting journal entry to dict."""
    entry = JournalEntry("Test entry", "Test Author")
    data = entry.to_dict()
    assert "timestamp" in data
    assert data["content"] == "Test entry"
    assert data["author"] == "Test Author"


def test_journal_entry_from_dict():
    """Test creating journal entry from dict."""
    timestamp = datetime.now()
    data = {
        "timestamp": timestamp.isoformat(),
        "content": "Test entry",
        "author": "Test Author"
    }
    entry = JournalEntry.from_dict(data)
    assert entry.content == "Test entry"
    assert entry.author == "Test Author"
    assert entry.timestamp == timestamp


def test_journal_creation():
    """Test creating a journal."""
    journal = Journal()
    assert len(journal.entries) == 0


def test_journal_add_entry():
    """Test adding entries to journal."""
    journal = Journal()
    entry = JournalEntry("Test entry")
    journal.add_entry(entry)
    assert len(journal.entries) == 1
    assert journal.entries[0] == entry


def test_journal_get_entries():
    """Test getting entries from journal."""
    journal = Journal()
    entry1 = JournalEntry("Test entry 1")
    entry2 = JournalEntry("Test entry 2")
    journal.add_entry(entry1)
    journal.add_entry(entry2)
    
    entries = journal.get_entries()
    assert len(entries) == 2
    assert entries[0] == entry1
    assert entries[1] == entry2
    # Test that it returns a copy
    assert entries is not journal.entries


def test_journal_to_dict():
    """Test converting journal to dict."""
    journal = Journal()
    entry = JournalEntry("Test entry", "Test Author")
    journal.add_entry(entry)
    
    data = journal.to_dict()
    assert "entries" in data
    assert len(data["entries"]) == 1


def test_journal_from_dict():
    """Test creating journal from dict."""
    timestamp = datetime.now()
    data = {
        "entries": [
            {
                "timestamp": timestamp.isoformat(),
                "content": "Test entry",
                "author": "Test Author"
            }
        ]
    }
    journal = Journal.from_dict(data)
    assert len(journal.entries) == 1
    assert journal.entries[0].content == "Test entry"


def test_maintenance_entry_creation():
    """Test creating a maintenance entry."""
    entry = MaintenanceEntry("Test maintenance", "Test Technician", 100.50)
    assert entry.description == "Test maintenance"
    assert entry.performed_by == "Test Technician"
    assert entry.cost == 100.50
    assert isinstance(entry.timestamp, datetime)


def test_maintenance_entry_to_dict():
    """Test converting maintenance entry to dict."""
    entry = MaintenanceEntry("Test maintenance", "Test Technician", 100.50)
    data = entry.to_dict()
    assert "timestamp" in data
    assert data["description"] == "Test maintenance"
    assert data["performed_by"] == "Test Technician"
    assert data["cost"] == 100.50


def test_maintenance_entry_from_dict():
    """Test creating maintenance entry from dict."""
    timestamp = datetime.now()
    data = {
        "timestamp": timestamp.isoformat(),
        "description": "Test maintenance",
        "performed_by": "Test Technician",
        "cost": 100.50
    }
    entry = MaintenanceEntry.from_dict(data)
    assert entry.description == "Test maintenance"
    assert entry.performed_by == "Test Technician"
    assert entry.cost == 100.50
    assert entry.timestamp == timestamp


def test_tent_creation():
    """Test creating a tent."""
    # This is a basic test - in a real scenario we would need to mock HomeAssistant and ConfigEntry
    pass


if __name__ == "__main__":
    pytest.main([__file__])