"""Meshtastic UI — companion dashboard integration."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    DOMAIN,
    EVENT_MESHTASTIC_EVENT,
    EVENT_MESHTASTIC_MESSAGE_LOG,
    SIGNAL_NEW_MESSAGE,
)
from .frontend import async_register_panel, async_unregister_panel
from .store import MeshtasticUiStore
from .websocket_api import async_register_websocket_api

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Meshtastic UI component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Meshtastic UI from a config entry."""
    store = MeshtasticUiStore(hass)
    await store.async_load()

    hass.data[DOMAIN] = {
        "store": store,
        "unsub_listeners": [],
    }

    # Register WebSocket API
    async_register_websocket_api(hass)

    # Register frontend panel
    await async_register_panel(hass)

    # Set up event listeners
    _setup_event_listeners(hass, store)

    # Initial node scan from device registry
    await _async_scan_nodes(hass, store)

    # Set up sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        data = hass.data.pop(DOMAIN, {})
        for unsub in data.get("unsub_listeners", []):
            unsub()
        async_unregister_panel(hass)

    return unload_ok


@callback
def _setup_event_listeners(hass: HomeAssistant, store: MeshtasticUiStore) -> None:
    """Subscribe to meshtastic events."""
    unsub_listeners = hass.data[DOMAIN]["unsub_listeners"]

    @callback
    def _handle_message_log(event: Event) -> None:
        """Handle meshtastic_message_log events."""
        data = event.data
        timestamp = datetime.now(timezone.utc).isoformat()

        message: dict[str, Any] = {
            "text": data.get("text", ""),
            "from": data.get("from", ""),
            "to": data.get("to", ""),
            "timestamp": timestamp,
            "channel": data.get("channel"),
            "gateway": data.get("gateway"),
        }

        pki = data.get("pki", False)
        if pki:
            # DM — key by partner entity_id or node id
            partner = data.get("from", "unknown")
            store.add_dm_message(partner, message)
            async_dispatcher_send(
                hass, SIGNAL_NEW_MESSAGE, {"type": "dm", "partner": partner, **message}
            )
        else:
            # Channel message — key by channel entity_id or channel name
            channel_id = data.get("channel", "default")
            store.add_channel_message(channel_id, message)
            async_dispatcher_send(
                hass,
                SIGNAL_NEW_MESSAGE,
                {"type": "channel", "channel": channel_id, **message},
            )

    @callback
    def _handle_meshtastic_event(event: Event) -> None:
        """Handle meshtastic_event for node activity tracking."""
        data = event.data
        node_id = data.get("node_id") or data.get("from")
        if not node_id:
            return

        update: dict[str, Any] = {"_last_seen": datetime.now(timezone.utc).isoformat()}
        event_type = data.get("type", "")
        if event_type:
            update["last_event_type"] = event_type

        store.update_node(str(node_id), update)

    @callback
    def _handle_state_changed(event: Event) -> None:
        """Capture telemetry updates from meshtastic sensors."""
        entity_id = event.data.get("entity_id", "")
        if not entity_id.startswith("sensor.meshtastic_"):
            return

        new_state = event.data.get("new_state")
        if new_state is None:
            return

        # Extract node id from entity_id
        # e.g. sensor.meshtastic_abcd1234_battery -> node id extraction
        node_id = _extract_node_id_from_entity(entity_id)
        if not node_id:
            return

        sensor_type = _extract_sensor_type(entity_id)
        if sensor_type:
            store.update_node(node_id, {sensor_type: new_state.state})

    unsub_listeners.append(
        hass.bus.async_listen(EVENT_MESHTASTIC_MESSAGE_LOG, _handle_message_log)
    )
    unsub_listeners.append(
        hass.bus.async_listen(EVENT_MESHTASTIC_EVENT, _handle_meshtastic_event)
    )
    unsub_listeners.append(
        hass.bus.async_listen("state_changed", _handle_state_changed)
    )


async def _async_scan_nodes(hass: HomeAssistant, store: MeshtasticUiStore) -> None:
    """Scan device registry for meshtastic nodes and read their sensor states."""
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)

    for device in dev_reg.devices.values():
        node_id = None
        for domain, identifier in device.identifiers:
            if domain == "meshtastic":
                node_id = identifier
                break

        if node_id is None:
            continue

        node_data: dict[str, Any] = {
            "name": device.name or node_id,
            "model": device.model or "",
        }

        # Read current sensor states for this device
        entity_entries = er.async_entries_for_device(ent_reg, device.id)
        for entity_entry in entity_entries:
            if not entity_entry.entity_id.startswith("sensor."):
                continue
            state = hass.states.get(entity_entry.entity_id)
            if state is None or state.state in ("unknown", "unavailable"):
                continue
            sensor_type = _extract_sensor_type(entity_entry.entity_id)
            if sensor_type:
                node_data[sensor_type] = state.state

        store.update_node(node_id, node_data)

    _LOGGER.debug("Initial node scan found %d meshtastic devices", store.total_nodes)


def _extract_node_id_from_entity(entity_id: str) -> str | None:
    """Extract node ID from a meshtastic sensor entity_id.

    Entity IDs follow the pattern: sensor.meshtastic_{node_id}_{sensor_type}
    """
    prefix = "sensor.meshtastic_"
    if not entity_id.startswith(prefix):
        return None

    remainder = entity_id[len(prefix):]
    # Node ID is everything up to the last underscore-separated sensor type
    # Common sensor types: battery, snr, hops, voltage, air_util_tx, channel_util
    known_suffixes = [
        "battery",
        "snr",
        "hops",
        "voltage",
        "air_util_tx",
        "channel_util",
        "uptime",
        "temperature",
        "humidity",
        "pressure",
        "latitude",
        "longitude",
        "altitude",
    ]
    for suffix in known_suffixes:
        if remainder.endswith(f"_{suffix}"):
            return remainder[: -(len(suffix) + 1)]

    return None


def _extract_sensor_type(entity_id: str) -> str | None:
    """Extract the sensor type suffix from a meshtastic sensor entity_id."""
    prefix = "sensor.meshtastic_"
    if not entity_id.startswith(prefix):
        return None

    remainder = entity_id[len(prefix):]
    known_suffixes = [
        "battery",
        "snr",
        "hops",
        "voltage",
        "air_util_tx",
        "channel_util",
        "uptime",
        "temperature",
        "humidity",
        "pressure",
        "latitude",
        "longitude",
        "altitude",
    ]
    for suffix in known_suffixes:
        if remainder.endswith(f"_{suffix}"):
            return suffix

    return None
