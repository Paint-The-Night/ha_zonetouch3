"""The Zone Touch 3 integration."""

from __future__ import annotations

import asyncio

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .api import ZoneTouch3Client
from .const import (
    ATTR_BYPASS_MIN_OPEN_GUARD,
    ATTR_ENTRY_ID,
    ATTR_PERCENTAGE,
    CONF_SOCKET_TIMEOUT,
    DEFAULT_PORT,
    DEFAULT_SOCKET_TIMEOUT,
    DOMAIN,
    PLATFORMS,
    SERVICE_SET_ALL_ZONES,
)
from .coordinator import ZoneTouch3DataUpdateCoordinator
from .models import ZoneTouch3RuntimeData

SERVICE_SET_ALL_ZONES_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTRY_ID): cv.string,
        vol.Optional(ATTR_PERCENTAGE, default=0): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=100)
        ),
        vol.Optional(ATTR_BYPASS_MIN_OPEN_GUARD, default=True): cv.boolean,
    }
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up Zone Touch 3 from YAML (not used)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Zone Touch 3 from a config entry."""
    host = entry.data[CONF_HOST]
    port = int(entry.data.get(CONF_PORT, DEFAULT_PORT))
    socket_timeout = float(
        entry.options.get(
            CONF_SOCKET_TIMEOUT,
            entry.data.get(CONF_SOCKET_TIMEOUT, DEFAULT_SOCKET_TIMEOUT),
        )
    )

    client = ZoneTouch3Client(host, port, socket_timeout)
    coordinator = ZoneTouch3DataUpdateCoordinator(hass, entry, client)

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        raise ConfigEntryNotReady(
            f"Unable to connect to Zone Touch 3 at {host}:{port}: {err}"
        ) from err

    snapshot = coordinator.data
    runtime_data = ZoneTouch3RuntimeData(
        client=client,
        coordinator=coordinator,
        device_id=snapshot.device_id,
        controller_name=snapshot.controller_name,
        firmware_version=snapshot.firmware_version,
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime_data
    _async_register_services(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    runtime_data: ZoneTouch3RuntimeData | None = hass.data.get(DOMAIN, {}).get(
        entry.entry_id
    )
    if runtime_data is not None:
        await runtime_data.coordinator.async_shutdown()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            _async_unregister_services(hass)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration services once."""
    if hass.services.has_service(DOMAIN, SERVICE_SET_ALL_ZONES):
        return

    async def _async_handle_set_all_zones(call: ServiceCall) -> None:
        entry_id = call.data.get(ATTR_ENTRY_ID)
        percentage = int(call.data[ATTR_PERCENTAGE])
        bypass_guard = bool(call.data[ATTR_BYPASS_MIN_OPEN_GUARD])

        runtime_entries: dict[str, ZoneTouch3RuntimeData] = hass.data.get(DOMAIN, {})
        if not runtime_entries:
            raise HomeAssistantError("No Zone Touch 3 entries are currently loaded")

        if entry_id is not None and entry_id not in runtime_entries:
            raise HomeAssistantError(f"Zone Touch 3 entry '{entry_id}' is not loaded")

        coordinators = (
            [runtime_entries[entry_id].coordinator]
            if entry_id is not None
            else [runtime_data.coordinator for runtime_data in runtime_entries.values()]
        )

        await asyncio.gather(
            *[
                coordinator.async_apply_all_zones(
                    percentage=percentage,
                    bypass_min_open_guard=bypass_guard,
                )
                for coordinator in coordinators
            ]
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_ALL_ZONES,
        _async_handle_set_all_zones,
        schema=SERVICE_SET_ALL_ZONES_SCHEMA,
    )


def _async_unregister_services(hass: HomeAssistant) -> None:
    """Unregister integration services if no entries remain."""
    if hass.services.has_service(DOMAIN, SERVICE_SET_ALL_ZONES):
        hass.services.async_remove(DOMAIN, SERVICE_SET_ALL_ZONES)
