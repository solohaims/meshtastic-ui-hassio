# GEMINI.md

This file provides guidance for Gemini CLI and other AI assistants when working with code in this repository.

## Project Overview

**Meshtastic UI 2** — An enhanced fork of Meshtastic UI for Home Assistant. It adds a full dashboard for Meshtastic mesh networks with advanced features for power users.

## Key Enhancements (v2)

- **Multi-Node Support**: Connect multiple radios (TCP, Serial, BLE) to a single integration instance. All nodes share a common message and node database.
- **Packet Deduplication**: Uses a recent packet ID cache (last 200 IDs) to discard duplicate incoming messages when multiple nodes hear the same broadcast.
- **Gateway Identification**: The Radio tab displays connection addresses (IP/Port, Serial path, or BLE MAC) to identify different hardware units.
- **Isolated Domain**: Renamed to `meshtastic_ui2` to prevent conflicts with the original integration.

## Development

### Build

Vendor libraries (Lit, Leaflet, D3) are bundled into `ha_frontend/vendor/` via a build step. The app-level frontend files (`panel.js`, `views.js`, etc.) are vanilla ES modules served directly by Home Assistant.

```bash
npm install          # install deps
npm run build        # bundle vendor libraries
```

### Tests

Backend Python tests use `pytest`:

```bash
pip install -e ".[test]"
pytest
```

## Architecture

```
Frontend (Lit 4.x)                         Backend (Python, HA WebSocket API)
─────────────────────────────────          ────────────────────────────────────
ha_frontend/                               custom_components/meshtastic_ui2/
  panel.js   → shell, router, tabs,          __init__.py   → entry setup, packet
               WS subscriptions,                              dispatch, node sync
               gateways management            connection.py → radio I/O (meshtastic lib)
  views.js   → Multi-node Radio tab,          websocket_api.py → Multi-node WS commands
               Messages, Nodes, Map           store.py      → Shared store with
  settings.js → radio configuration                           deduplication logic
```

### Data Flow

1. **Radio → Backend**: `connection.py` wraps the `meshtastic` library. `__init__.py` handles multi-node packet dispatching.
2. **Persistence**: `store.py` implements a shared store for all nodes. Includes `is_duplicate()` check for incoming packets.
3. **Frontend → Backend**: `panel.js` calls WS commands (prefix `meshtastic_ui2/`). Commands like `gateways` return arrays of all active nodes.

### Key Conventions

- **Domain**: Always use `meshtastic_ui2`.
- **Node IDs**: `!xxxxxxxx` format.
- **Multi-Node**: Backend `hass.data[DOMAIN]["connections"]` is a dictionary of active radio instances.
- **Deduplication**: Message processing must check `store.is_duplicate(packet_id)`.

## Git Conventions

- Author: `Daring Designs <contact@daring-designs.com>` (inherited from original)
- Branch: `main`
