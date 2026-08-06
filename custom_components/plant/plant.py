"""Config-Entry-Plattform für die plant.<name>-Entität.

Die Haupt-Entität lebt auf der Domain `plant`, die diese Integration selbst
besitzt. Sie über eine echte Config-Entry-Plattform hinzuzufügen statt über
eine frei erzeugte EntityComponent gibt ihrer EntityPlatform einen
`config_entry`. Home Assistant hängt das Gerät dann selbst an und trägt die
Entität nativ in die Registry ein - die manuelle Nachbesserung über
`erreg.async_update_entity(...)` entfällt, und HA Core 2026.8 beschwert sich
nicht mehr darüber, dass ein Gerät an einer Entität ohne Config-Entry hängt.

Die PlantDevice-Instanz wird in `__init__.async_setup_entry` erzeugt (dort wird
sie für die Utility-Sensoren gebraucht) und unter den Daten des Eintrags
abgelegt. Diese Plattform reicht genau dieselbe Instanz an das an den
Config-Entry gebundene `async_add_entities` weiter.

Gegenstück für Cycles: cycle.py
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
    """Die PlantDevice dieses Config-Entries an ihre gebundene Plattform geben."""
    plant = hass.data[DOMAIN][entry.entry_id][ATTR_PLANT]
    async_add_entities([plant])
