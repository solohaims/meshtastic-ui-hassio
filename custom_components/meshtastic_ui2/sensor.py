"""Sensor platform for Meshtastic UI."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_NEW_MESSAGE
from .store import MeshtasticUiStore


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Meshtastic UI sensors."""
    store: MeshtasticUiStore = hass.data[DOMAIN]["store"]
    async_add_entities(
        [
            MeshMessagesTodaySensor(store),
            MeshActiveNodesSensor(store),
        ]
    )


class MeshMessagesTodaySensor(SensorEntity):
    """Sensor tracking total messages received today."""

    _attr_has_entity_name = True
    _attr_name = "Messages Today"
    _attr_unique_id = f"{DOMAIN}_messages_today"
    _attr_icon = "mdi:message-text"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "messages"

    def __init__(self, store: MeshtasticUiStore) -> None:
        """Initialize the sensor."""
        self._store = store

    @property
    def native_value(self) -> int:
        """Return today's message count."""
        return self._store.messages_today

    async def async_added_to_hass(self) -> None:
        """Subscribe to message updates."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_NEW_MESSAGE, self._handle_new_message
            )
        )

    @callback
    def _handle_new_message(self, _data: dict) -> None:
        """Update when a new message arrives."""
        self.async_write_ha_state()


class MeshActiveNodesSensor(SensorEntity):
    """Sensor tracking active nodes (seen within 1 hour)."""

    _attr_has_entity_name = True
    _attr_name = "Active Nodes"
    _attr_unique_id = f"{DOMAIN}_active_nodes"
    _attr_icon = "mdi:access-point-network"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "nodes"

    def __init__(self, store: MeshtasticUiStore) -> None:
        """Initialize the sensor."""
        self._store = store

    @property
    def native_value(self) -> int:
        """Return count of active nodes."""
        return self._store.active_nodes_count

    async def async_added_to_hass(self) -> None:
        """Subscribe to message updates to refresh node counts."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_NEW_MESSAGE, self._handle_update
            )
        )

    @callback
    def _handle_update(self, _data: dict) -> None:
        """Refresh when activity occurs."""
        self.async_write_ha_state()
