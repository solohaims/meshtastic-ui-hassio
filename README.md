# Meshtastic UI 2 for Home Assistant

**Meshtastic UI 2** is an enhanced fork of the [Meshtastic UI for Home Assistant](https://github.com/Daring-Designs/meshtastic-ui-ha) integration. It provides a full-featured dashboard for your [Meshtastic](https://meshtastic.org) mesh network directly within the Home Assistant sidebar.

## Key Features in this Fork

- **Multi-Node Support**: Connect multiple Meshtastic radios (TCP, Serial, or BLE) simultaneously to a single Home Assistant instance.
- **Packet Deduplication**: Automatically filters duplicate incoming messages when multiple gateways are active in the same mesh network.
- **Enhanced Identification**: Displays connection addresses (IP/Port, Serial path, or BLE MAC) on the Radio tab to easily distinguish between multiple hardware units.
- **Isolated Installation**: Renamed to `meshtastic_ui2` to allow side-by-side installation with the original integration.

## Built With

- **Backend** — Python, using the [meshtastic](https://pypi.org/project/meshtastic/) library.
- **Frontend** — Vanilla ES modules built with [Lit](https://lit.dev/) 4.x, [Leaflet](https://leafletjs.com/), and [D3](https://d3js.org/).

## Why Connect Multiple Radios?

Using multiple gateway nodes improves mesh coverage and redundancy. Meshtastic UI 2 consolidates all activity from your radios into a single, unified view, ensuring you never miss a message and always have the most up-to-date node positions on the map.

## Credits & Acknowledgements

This project is a fork of the original work by [Daring Designs](https://github.com/Daring-Designs). We want to thank the original authors for their outstanding contribution to the Meshtastic and Home Assistant communities.

Original Repository: [https://github.com/Daring-Designs/meshtastic-ui-ha](https://github.com/Daring-Designs/meshtastic-ui-ha)

## Installation

### Manual

1. Copy the `custom_components/meshtastic_ui2` folder into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.
3. Go to **Settings > Devices & Services > Add Integration** and search for **Meshtastic UI 2**.
4. Configure your connection(s). You can add multiple instances of this integration to connect additional nodes.

## Prerequisites

- Home Assistant 2024.1+
- One or more Meshtastic radios accessible via TCP, Serial, or BLE.

## License

MIT
