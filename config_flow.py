"""Config flow for Zone Touch 3."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError

from .api import ZoneTouch3Client
from .const import (
    CONF_COMMAND_GAP,
    CONF_ENFORCE_MIN_OPEN_ZONE,
    CONF_POST_COMMAND_SETTLE,
    CONF_SCAN_INTERVAL,
    CONF_SOCKET_TIMEOUT,
    DEFAULT_COMMAND_GAP,
    DEFAULT_ENFORCE_MIN_OPEN_ZONE,
    DEFAULT_PORT,
    DEFAULT_POST_COMMAND_SETTLE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SOCKET_TIMEOUT,
    DOMAIN,
    MAX_COMMAND_GAP,
    MAX_POST_COMMAND_SETTLE,
    MAX_SCAN_INTERVAL,
    MAX_SOCKET_TIMEOUT,
    MIN_COMMAND_GAP,
    MIN_POST_COMMAND_SETTLE,
    MIN_SCAN_INTERVAL,
    MIN_SOCKET_TIMEOUT,
)
from .exceptions import ZoneTouch3ConnectionError, ZoneTouch3ProtocolError

_LOGGER = logging.getLogger(__name__)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidResponse(HomeAssistantError):
    """Error to indicate response does not match expected protocol."""


class ZoneTouch3ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Zone Touch 3."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            normalized_input = _normalize_input(user_input)

            try:
                info = await _async_validate_input(self.hass, normalized_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidResponse:
                errors["base"] = "invalid_response"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected exception while validating Zone Touch 3 setup")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(info["device_id"])
                self._abort_if_unique_id_configured(
                    updates={
                        CONF_HOST: normalized_input[CONF_HOST],
                        CONF_PORT: normalized_input[CONF_PORT],
                    }
                )

                return self.async_create_entry(
                    title=normalized_input[CONF_NAME] or info["controller_name"],
                    data={
                        CONF_HOST: normalized_input[CONF_HOST],
                        CONF_PORT: normalized_input[CONF_PORT],
                        CONF_NAME: normalized_input[CONF_NAME],
                        CONF_SCAN_INTERVAL: normalized_input[CONF_SCAN_INTERVAL],
                        CONF_SOCKET_TIMEOUT: normalized_input[CONF_SOCKET_TIMEOUT],
                        CONF_ENFORCE_MIN_OPEN_ZONE: normalized_input[
                            CONF_ENFORCE_MIN_OPEN_ZONE
                        ],
                        CONF_COMMAND_GAP: normalized_input[CONF_COMMAND_GAP],
                        CONF_POST_COMMAND_SETTLE: normalized_input[
                            CONF_POST_COMMAND_SETTLE
                        ],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_config_schema(user_input),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> ZoneTouch3OptionsFlowHandler:
        """Get options flow."""
        return ZoneTouch3OptionsFlowHandler(config_entry)


class ZoneTouch3OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for Zone Touch 3."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Manage options."""
        if user_input is not None:
            normalized_input = _normalize_input(
                {
                    CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                    CONF_SOCKET_TIMEOUT: user_input[CONF_SOCKET_TIMEOUT],
                    CONF_ENFORCE_MIN_OPEN_ZONE: user_input[
                        CONF_ENFORCE_MIN_OPEN_ZONE
                    ],
                    CONF_COMMAND_GAP: user_input[CONF_COMMAND_GAP],
                    CONF_POST_COMMAND_SETTLE: user_input[CONF_POST_COMMAND_SETTLE],
                },
                include_connection_fields=False,
            )
            return self.async_create_entry(title="", data=normalized_input)

        defaults: dict[str, Any] = {
            CONF_SCAN_INTERVAL: self._entry.options.get(
                CONF_SCAN_INTERVAL,
                self._entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ),
            CONF_SOCKET_TIMEOUT: self._entry.options.get(
                CONF_SOCKET_TIMEOUT,
                self._entry.data.get(CONF_SOCKET_TIMEOUT, DEFAULT_SOCKET_TIMEOUT),
            ),
            CONF_ENFORCE_MIN_OPEN_ZONE: self._entry.options.get(
                CONF_ENFORCE_MIN_OPEN_ZONE,
                self._entry.data.get(
                    CONF_ENFORCE_MIN_OPEN_ZONE, DEFAULT_ENFORCE_MIN_OPEN_ZONE
                ),
            ),
            CONF_COMMAND_GAP: self._entry.options.get(
                CONF_COMMAND_GAP,
                self._entry.data.get(CONF_COMMAND_GAP, DEFAULT_COMMAND_GAP),
            ),
            CONF_POST_COMMAND_SETTLE: self._entry.options.get(
                CONF_POST_COMMAND_SETTLE,
                self._entry.data.get(
                    CONF_POST_COMMAND_SETTLE, DEFAULT_POST_COMMAND_SETTLE
                ),
            ),
        }

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(defaults),
        )


def _config_schema(user_input: dict[str, Any] | None) -> vol.Schema:
    data = _normalize_input(user_input or {})

    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=data[CONF_HOST]): str,
            vol.Required(CONF_PORT, default=data[CONF_PORT]): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=65535)
            ),
            vol.Optional(CONF_NAME, default=data[CONF_NAME]): str,
            vol.Required(
                CONF_SCAN_INTERVAL, default=data[CONF_SCAN_INTERVAL]
            ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)),
            vol.Required(
                CONF_SOCKET_TIMEOUT, default=data[CONF_SOCKET_TIMEOUT]
            ): vol.All(
                vol.Coerce(float),
                vol.Range(min=MIN_SOCKET_TIMEOUT, max=MAX_SOCKET_TIMEOUT),
            ),
            vol.Required(
                CONF_ENFORCE_MIN_OPEN_ZONE,
                default=data[CONF_ENFORCE_MIN_OPEN_ZONE],
            ): bool,
            vol.Required(CONF_COMMAND_GAP, default=data[CONF_COMMAND_GAP]): vol.All(
                vol.Coerce(float), vol.Range(min=MIN_COMMAND_GAP, max=MAX_COMMAND_GAP)
            ),
            vol.Required(
                CONF_POST_COMMAND_SETTLE, default=data[CONF_POST_COMMAND_SETTLE]
            ): vol.All(
                vol.Coerce(float),
                vol.Range(
                    min=MIN_POST_COMMAND_SETTLE, max=MAX_POST_COMMAND_SETTLE
                ),
            ),
        }
    )


def _options_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_SCAN_INTERVAL, default=defaults[CONF_SCAN_INTERVAL]
            ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)),
            vol.Required(
                CONF_SOCKET_TIMEOUT, default=defaults[CONF_SOCKET_TIMEOUT]
            ): vol.All(
                vol.Coerce(float),
                vol.Range(min=MIN_SOCKET_TIMEOUT, max=MAX_SOCKET_TIMEOUT),
            ),
            vol.Required(
                CONF_ENFORCE_MIN_OPEN_ZONE,
                default=defaults[CONF_ENFORCE_MIN_OPEN_ZONE],
            ): bool,
            vol.Required(
                CONF_COMMAND_GAP, default=defaults[CONF_COMMAND_GAP]
            ): vol.All(
                vol.Coerce(float), vol.Range(min=MIN_COMMAND_GAP, max=MAX_COMMAND_GAP)
            ),
            vol.Required(
                CONF_POST_COMMAND_SETTLE, default=defaults[CONF_POST_COMMAND_SETTLE]
            ): vol.All(
                vol.Coerce(float),
                vol.Range(
                    min=MIN_POST_COMMAND_SETTLE, max=MAX_POST_COMMAND_SETTLE
                ),
            ),
        }
    )


def _normalize_input(
    user_input: dict[str, Any],
    *,
    include_connection_fields: bool = True,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        CONF_SCAN_INTERVAL: int(user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)),
        CONF_SOCKET_TIMEOUT: float(
            user_input.get(CONF_SOCKET_TIMEOUT, DEFAULT_SOCKET_TIMEOUT)
        ),
        CONF_ENFORCE_MIN_OPEN_ZONE: bool(
            user_input.get(CONF_ENFORCE_MIN_OPEN_ZONE, DEFAULT_ENFORCE_MIN_OPEN_ZONE)
        ),
        CONF_COMMAND_GAP: float(user_input.get(CONF_COMMAND_GAP, DEFAULT_COMMAND_GAP)),
        CONF_POST_COMMAND_SETTLE: float(
            user_input.get(CONF_POST_COMMAND_SETTLE, DEFAULT_POST_COMMAND_SETTLE)
        ),
    }

    if include_connection_fields:
        host = str(user_input.get(CONF_HOST, "")).strip()
        name = str(user_input.get(CONF_NAME, "")).strip()

        data[CONF_HOST] = host
        data[CONF_PORT] = int(user_input.get(CONF_PORT, DEFAULT_PORT))
        data[CONF_NAME] = name or "Zone Touch 3"

    return data


async def _async_validate_input(
    hass: HomeAssistant,
    data: dict[str, Any],
) -> dict[str, str]:
    """Validate the user input allows us to connect."""
    client = ZoneTouch3Client(
        host=data[CONF_HOST],
        port=data[CONF_PORT],
        socket_timeout=data[CONF_SOCKET_TIMEOUT],
    )

    try:
        snapshot = await hass.async_add_executor_job(client.fetch_snapshot)
    except ZoneTouch3ConnectionError as err:
        raise CannotConnect from err
    except ZoneTouch3ProtocolError as err:
        raise InvalidResponse from err

    return {
        "device_id": snapshot.device_id,
        "controller_name": snapshot.controller_name,
    }
