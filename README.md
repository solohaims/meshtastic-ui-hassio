# Meshtastic UI for Home Assistant

A companion integration that adds a unified dashboard for your [Meshtastic](https://meshtastic.org) mesh network in Home Assistant. Works alongside the existing [Meshtastic integration](https://github.com/meshtastic/home-assistant) — no configuration overlap, no direct code dependency.

## What It Does

**Meshtastic UI** adds a sidebar panel ("Mesh UI") with four tabs:

- **Radio** — Embeds the Meshtastic web client directly in your HA dashboard (no more opening a separate tab)
- **Messages** — View channel and direct message history with a chat-style interface. Send messages right from HA. Messages persist across restarts.
- **Nodes** — Sortable table of all mesh nodes showing name, SNR, hops, battery, and last seen time
- **Stats** — At-a-glance summary cards: messages today, active nodes, total nodes, and channel count

It also creates two sensor entities:
- `sensor.meshtastic_ui_messages_today` — Total messages received today
- `sensor.meshtastic_ui_active_nodes` — Nodes seen in the last hour

## Prerequisites

The [Meshtastic integration](https://github.com/meshtastic/home-assistant) (v0.6.1+) must be installed and have at least one gateway configured.

## Installation

### HACS (Recommended)

1. Open **HACS** in Home Assistant
2. Click the three-dot menu → **Custom repositories**
3. Add `https://github.com/Daring-Designs/meshtastic-ui-ha` with category **Integration**
4. Find **Meshtastic UI** and click **Download**
5. Restart Home Assistant
6. Go to **Settings → Devices & Services → Add Integration** and search for **Meshtastic UI**

### Manual

Copy the `custom_components/meshtastic_ui` folder into your Home Assistant `config/custom_components/` directory, restart, and add the integration.

## How It Works

This integration communicates with the existing Meshtastic integration entirely through Home Assistant's public APIs:

- **Event bus** — Listens to `meshtastic_message_log` and `meshtastic_event` for real-time messages and node activity
- **Device/Entity registry** — Discovers gateways and nodes automatically
- **State machine** — Reads sensor values (SNR, battery, hops, etc.) from existing Meshtastic entities
- **Services** — Sends messages by calling `meshtastic.broadcast_channel_message` and `meshtastic.send_direct_message`

Message history and node data are stored locally and persist across HA restarts.

## License

MIT
