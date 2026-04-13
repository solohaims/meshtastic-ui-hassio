"""Tests for Meshtastic UI config flow."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.meshtastic_ui2.const import (
    CONF_BLE_ADDRESS,
    CONF_CONNECTION_TYPE,
    CONF_SERIAL_DEV_PATH,
    CONF_TCP_HOSTNAME,
    CONF_TCP_PORT,
    DEFAULT_TCP_PORT,
    DOMAIN,
    MESHTASTIC_BLE_SERVICE_UUID,
)


def _make_bluetooth_service_info(
    name: str = "Meshtastic_abcd",
    address: str = "AA:BB:CC:DD:EE:FF",
):
    """Create a mock BluetoothServiceInfoBleak for testing."""
    from unittest.mock import MagicMock

    info = MagicMock()
    info.name = name
    info.address = address
    info.service_uuids = [MESHTASTIC_BLE_SERVICE_UUID]
    info.manufacturer_data = {}
    info.service_data = {}
    info.rssi = -60
    info.source = "local"
    info.device = MagicMock()
    info.device.address = address
    info.advertisement = MagicMock()
    info.connectable = True
    info.time = 0
    return info


async def test_user_step_shows_form(hass: HomeAssistant):
    """Test the initial user step shows connection type selector."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_tcp_step_success(hass: HomeAssistant):
    """Test TCP step with valid input creates config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.meshtastic_ui2.config_flow.MeshtasticUiConfigFlow._test_tcp_connection"
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_CONNECTION_TYPE: "tcp"},
        )
        assert result["step_id"] == "tcp"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_TCP_HOSTNAME: "192.168.1.100", CONF_TCP_PORT: DEFAULT_TCP_PORT},
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_CONNECTION_TYPE] == "tcp"
        assert result["data"][CONF_TCP_HOSTNAME] == "192.168.1.100"
        assert result["data"][CONF_TCP_PORT] == DEFAULT_TCP_PORT


async def test_tcp_step_failure(hass: HomeAssistant):
    """Test TCP step shows error on connection failure."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.meshtastic_ui2.config_flow.MeshtasticUiConfigFlow._test_tcp_connection",
        side_effect=Exception("Connection refused"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_CONNECTION_TYPE: "tcp"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_TCP_HOSTNAME: "192.168.1.100", CONF_TCP_PORT: DEFAULT_TCP_PORT},
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"]["base"] == "cannot_connect"


async def test_serial_step_success(hass: HomeAssistant):
    """Test serial step with valid input creates config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with (
        patch(
            "custom_components.meshtastic_ui2.config_flow.MeshtasticUiConfigFlow._test_serial_connection"
        ),
        patch(
            "custom_components.meshtastic_ui2.config_flow.MeshtasticUiConfigFlow._find_serial_ports",
            return_value=["/dev/ttyUSB0"],
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_CONNECTION_TYPE: "serial"},
        )
        assert result["step_id"] == "serial"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_SERIAL_DEV_PATH: "/dev/ttyUSB0"},
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_CONNECTION_TYPE] == "serial"
        assert result["data"][CONF_SERIAL_DEV_PATH] == "/dev/ttyUSB0"


async def test_serial_step_failure(hass: HomeAssistant):
    """Test serial step shows error on connection failure."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with (
        patch(
            "custom_components.meshtastic_ui2.config_flow.MeshtasticUiConfigFlow._test_serial_connection",
            side_effect=Exception("Device not found"),
        ),
        patch(
            "custom_components.meshtastic_ui2.config_flow.MeshtasticUiConfigFlow._find_serial_ports",
            return_value=[],
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_CONNECTION_TYPE: "serial"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_SERIAL_DEV_PATH: "/dev/ttyUSB0"},
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"]["base"] == "cannot_connect"


async def test_ble_step_success(hass: HomeAssistant):
    """Test BLE step with valid input creates config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with (
        patch(
            "custom_components.meshtastic_ui2.config_flow.MeshtasticUiConfigFlow._test_ble_connection"
        ),
        patch(
            "custom_components.meshtastic_ui2.config_flow.async_discovered_service_info",
            return_value=[],
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_CONNECTION_TYPE: "ble"},
        )
        # No discovered devices → falls through to ble_manual step.
        assert result["step_id"] == "ble_manual"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_BLE_ADDRESS: "AA:BB:CC:DD:EE:FF"},
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_CONNECTION_TYPE] == "ble"
        assert result["data"][CONF_BLE_ADDRESS] == "AA:BB:CC:DD:EE:FF"


async def test_ble_step_failure(hass: HomeAssistant):
    """Test BLE step shows error on connection failure."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with (
        patch(
            "custom_components.meshtastic_ui2.config_flow.MeshtasticUiConfigFlow._test_ble_connection",
            side_effect=Exception("BLE error"),
        ),
        patch(
            "custom_components.meshtastic_ui2.config_flow.async_discovered_service_info",
            return_value=[],
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_CONNECTION_TYPE: "ble"},
        )
        # No discovered devices → ble_manual.
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_BLE_ADDRESS: "AA:BB:CC:DD:EE:FF"},
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"]["base"] == "cannot_connect"


async def test_ble_step_with_discovered_devices(hass: HomeAssistant):
    """Test BLE step shows picker when devices are discovered."""
    info = _make_bluetooth_service_info()

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with (
        patch(
            "custom_components.meshtastic_ui2.config_flow.MeshtasticUiConfigFlow._test_ble_connection"
        ),
        patch(
            "custom_components.meshtastic_ui2.config_flow.async_discovered_service_info",
            return_value=[info],
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_CONNECTION_TYPE: "ble"},
        )
        # Should show the BLE picker (not ble_manual).
        assert result["step_id"] == "ble"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_BLE_ADDRESS: "AA:BB:CC:DD:EE:FF"},
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_BLE_ADDRESS] == "AA:BB:CC:DD:EE:FF"


async def test_bluetooth_discovery(hass: HomeAssistant):
    """Test that HA Bluetooth discovery triggers the config flow."""
    info = _make_bluetooth_service_info()

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=info,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "bluetooth_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_CONNECTION_TYPE] == "ble"
    assert result["data"][CONF_BLE_ADDRESS] == "AA:BB:CC:DD:EE:FF"


async def test_bluetooth_discovery_already_configured(hass: HomeAssistant):
    """Test that Bluetooth discovery aborts if already configured."""
    info = _make_bluetooth_service_info()

    # First: set up via Bluetooth discovery.
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=info,
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY

    # Second discovery should abort.
    result2 = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=info,
    )
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


async def test_already_configured(hass: HomeAssistant):
    """Test abort if integration is already configured."""
    # Create a first entry
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.meshtastic_ui2.config_flow.MeshtasticUiConfigFlow._test_tcp_connection"
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_CONNECTION_TYPE: "tcp"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_TCP_HOSTNAME: "192.168.1.100", CONF_TCP_PORT: DEFAULT_TCP_PORT},
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY

    # Try to create a second entry — should abort
    result2 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"
