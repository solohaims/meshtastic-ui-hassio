"""WebSocket API for Meshtastic UI."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.websocket_api import (
    ActiveConnection,
    async_register_command,
    async_response,
    websocket_command,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, SIGNAL_NEW_MESSAGE, WS_PREFIX


def async_register_websocket_api(hass: HomeAssistant) -> None:
    """Register all WebSocket commands."""
    async_register_command(hass, ws_gateways)
    async_register_command(hass, ws_messages)
    async_register_command(hass, ws_nodes)
    async_register_command(hass, ws_stats)
    async_register_command(hass, ws_subscribe)
    async_register_command(hass, ws_send_message)


def _get_store(hass: HomeAssistant) -> MeshtasticUiStore:
    """Get the store instance."""
    return hass.data[DOMAIN]["store"]


@websocket_command(
    {
        vol.Required("type"): f"{WS_PREFIX}/gateways",
    }
)
@async_response
async def ws_gateways(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Return discovered meshtastic gateways."""
    ent_reg = er.async_get(hass)
    gateways: list[dict[str, Any]] = []

    for entry in ent_reg.entities.values():
        if entry.platform != "meshtastic":
            continue
        # Look for gateway-type entities (typically the main device tracker or sensor)
        if entry.original_device_class == "gateway" or (
            entry.entity_id.startswith("sensor.meshtastic_")
            and "gateway" in entry.entity_id
        ):
            gateway_id = entry.entity_id.split(".")[-1]
            gateways.append(
                {
                    "entity_id": entry.entity_id,
                    "name": entry.name or entry.original_name or gateway_id,
                    "web_url": f"/meshtastic/web/{gateway_id}",
                }
            )

    # Fallback: if no gateway entities found, look for meshtastic config entries
    if not gateways:
        for config_entry in hass.config_entries.async_entries("meshtastic"):
            entry_id = config_entry.entry_id
            gateways.append(
                {
                    "entity_id": None,
                    "name": config_entry.title or "Meshtastic Gateway",
                    "web_url": f"/meshtastic/web/{entry_id}",
                }
            )

    connection.send_result(msg["id"], {"gateways": gateways})


@websocket_command(
    {
        vol.Required("type"): f"{WS_PREFIX}/messages",
        vol.Optional("entity_id"): str,
    }
)
@async_response
async def ws_messages(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Return stored messages, optionally filtered."""
    store = _get_store(hass)
    entity_id = msg.get("entity_id")

    if entity_id:
        # Check channels first, then DMs
        messages = store.get_channel_messages(entity_id)
        if not messages:
            messages = store.get_dm_messages(entity_id)
        connection.send_result(msg["id"], {"messages": messages})
    else:
        connection.send_result(
            msg["id"],
            {
                "messages": store.get_all_messages(),
                "channels": store.get_all_channel_ids(),
                "dms": store.get_all_dm_ids(),
            },
        )


@websocket_command(
    {
        vol.Required("type"): f"{WS_PREFIX}/nodes",
    }
)
@async_response
async def ws_nodes(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Return all tracked nodes."""
    store = _get_store(hass)
    connection.send_result(msg["id"], {"nodes": store.get_nodes()})


@websocket_command(
    {
        vol.Required("type"): f"{WS_PREFIX}/stats",
    }
)
@async_response
async def ws_stats(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Return summary statistics."""
    store = _get_store(hass)
    connection.send_result(
        msg["id"],
        {
            "messages_today": store.messages_today,
            "active_nodes": store.active_nodes_count,
            "total_nodes": store.total_nodes,
            "channel_count": store.channel_count,
        },
    )


@websocket_command(
    {
        vol.Required("type"): f"{WS_PREFIX}/subscribe",
    }
)
@callback
def ws_subscribe(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Subscribe to real-time message updates."""

    @callback
    def _forward_message(message_data: dict[str, Any]) -> None:
        """Forward new message to the subscriber."""
        connection.send_event(msg["id"], message_data)

    unsub = async_dispatcher_connect(hass, SIGNAL_NEW_MESSAGE, _forward_message)
    connection.subscriptions[msg["id"]] = unsub
    connection.send_result(msg["id"])


@websocket_command(
    {
        vol.Required("type"): f"{WS_PREFIX}/send_message",
        vol.Required("text"): str,
        vol.Optional("channel"): str,
        vol.Optional("to"): str,
    }
)
@async_response
async def ws_send_message(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Send a message via meshtastic services."""
    text = msg["text"]
    channel = msg.get("channel")
    to = msg.get("to")

    try:
        if to:
            # Direct message
            await hass.services.async_call(
                "meshtastic",
                "send_direct_message",
                {"text": text, "to": to},
                blocking=True,
            )
        else:
            # Channel broadcast
            service_data: dict[str, Any] = {"text": text}
            if channel:
                service_data["channel"] = channel
            await hass.services.async_call(
                "meshtastic",
                "broadcast_channel_message",
                service_data,
                blocking=True,
            )
        connection.send_result(msg["id"], {"success": True})
    except Exception as err:  # noqa: BLE001
        connection.send_error(msg["id"], "send_failed", str(err))
