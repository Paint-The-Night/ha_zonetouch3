"""Config flow for Zone Touch 3."""

from __future__ import annotations

import logging
import ipaddress
from urllib.parse import urlparse
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError

from .api import (
    ZoneTouch3Client,
    ZoneTouch3DiscoveredController,
    discover_zone_touch3_controllers,
)
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
CONF_DISCOVERED_DEVICE = "discovered_device"


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidResponse(HomeAssistantError):
    """Error to indicate response does not match expected protocol."""


class ZoneTouch3ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Zone Touch 3."""

    VERSION = 1
    _pending_input: dict[str, Any] | None
    _discovered_controllers: tuple[ZoneTouch3DiscoveredController, ...]

    def __init__(self) -> None:
        """Initialize the Zone Touch 3 config flow."""
        self._pending_input = None
        self._discovered_controllers = ()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            normalized_input = _normalize_input(user_input)
            if not normalized_input[CONF_HOST]:
                discovered = await _async_discover_controllers(self.hass, timeout=2.0)
                if len(discovered) == 1:
                    normalized_input[CONF_HOST] = discovered[0].ip
                elif len(discovered) > 1:
                    self._pending_input = normalized_input
                    self._discovered_controllers = discovered
                    return await self.async_step_pick_discovered()
                else:
                    errors["base"] = "cannot_discover"

            if not errors:
                return await self._async_validate_and_create_entry(
                    normalized_input, errors
                )
        else:
            discovered = await _async_discover_controllers(self.hass, timeout=1.5)
            self._discovered_controllers = discovered
            if len(discovered) == 1:
                user_input = {CONF_HOST: discovered[0].ip}

        return self.async_show_form(
            step_id="user",
            data_schema=_config_schema(user_input),
            errors=errors,
        )

    async def async_step_pick_discovered(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle selecting one controller from discovered candidates."""
        if self._pending_input is None or not self._discovered_controllers:
            return await self.async_step_user()

        if user_input is not None:
            selected_ip = str(user_input[CONF_DISCOVERED_DEVICE]).strip()
            self._pending_input[CONF_HOST] = selected_ip
            normalized_input = self._pending_input
            self._pending_input = None
            self._discovered_controllers = ()
            errors: dict[str, str] = {}
            return await self._async_validate_and_create_entry(normalized_input, errors)

        options = {
            controller.ip: f"{controller.name} ({controller.ip})"
            for controller in self._discovered_controllers
        }
        return self.async_show_form(
            step_id="pick_discovered",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DISCOVERED_DEVICE): vol.In(options),
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> ZoneTouch3OptionsFlowHandler:
        """Get options flow."""
        return ZoneTouch3OptionsFlowHandler(config_entry)

    async def _async_validate_and_create_entry(
        self,
        normalized_input: dict[str, Any],
        errors: dict[str, str],
    ) -> config_entries.FlowResult:
        """Validate controller connection and create a config entry."""
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
            data_schema=_config_schema(normalized_input),
            errors=errors,
        )


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


async def _async_discover_controllers(
    hass: HomeAssistant,
    *,
    timeout: float,
) -> tuple[ZoneTouch3DiscoveredController, ...]:
    """Discover Zone Touch 3 controllers on the local network."""
    seed_ip = _guess_local_ipv4(hass)
    return await hass.async_add_executor_job(
        discover_zone_touch3_controllers,
        timeout,
        seed_ip,
    )


def _guess_local_ipv4(hass: HomeAssistant) -> str | None:
    """Guess the LAN IPv4 used by Home Assistant for subnet-scan fallback."""
    candidates: list[str] = []

    api_obj = getattr(hass.config, "api", None)
    if api_obj is not None:
        local_ip = getattr(api_obj, "local_ip", None)
        if isinstance(local_ip, str):
            candidates.append(local_ip)

    for url in (hass.config.internal_url, hass.config.external_url):
        if not url:
            continue
        host = urlparse(url).hostname
        if host:
            candidates.append(host)

    for candidate in candidates:
        try:
            ipaddress.IPv4Address(candidate)
        except ipaddress.AddressValueError:
            continue
        return candidate

    return None
