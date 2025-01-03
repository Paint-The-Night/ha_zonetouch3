"""Config flow for Zone Touch 3 integration."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN

@config_entries.HANDLERS.register(DOMAIN)
class ZoneTouch3ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Zone Touch 3."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            return self.async_create_entry(title="Zone Touch 3", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required("name"): str,
                vol.Required("ip_address"): str,
                vol.Required("port"): int,
                vol.Required("entities"): int,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )
