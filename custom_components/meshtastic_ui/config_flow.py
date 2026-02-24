"""Config flow for Meshtastic UI."""

from homeassistant.config_entries import ConfigFlow

from .const import DOMAIN


class MeshtasticUiConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for Meshtastic UI integration."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        # Prevent duplicate entries
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        # Check that meshtastic integration is configured
        meshtastic_entries = self.hass.config_entries.async_entries("meshtastic")
        if not meshtastic_entries:
            return self.async_abort(reason="meshtastic_not_found")

        if user_input is not None:
            return self.async_create_entry(title="Meshtastic UI", data={})

        return self.async_show_form(step_id="user")
