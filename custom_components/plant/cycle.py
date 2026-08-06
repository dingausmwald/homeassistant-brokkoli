"""Config-Entry-Plattform für die cycle.<name>-Entität.

Identisch zu plant.py, nur für Einträge mit device_type `cycle`. Beide Domains
brauchen ein eigenes Plattform-Modul, weil EntityComponent.async_setup_entry
das Modul anhand der Domain der Komponente auflöst (`plant` bzw. `cycle`).

Siehe plant.py für die ausführliche Begründung.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_PLANT, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Die Cycle-Entität dieses Config-Entries an ihre gebundene Plattform geben."""
    plant = hass.data[DOMAIN][entry.entry_id][ATTR_PLANT]
    async_add_entities([plant])
