"""Diagnostics support for Zone Touch 3."""

from __future__ import annotations

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .models import ZoneTouch3RuntimeData

TO_REDACT = {CONF_HOST}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> dict:
    """Return diagnostics for a config entry."""
    runtime_data: ZoneTouch3RuntimeData = hass.data[DOMAIN][config_entry.entry_id]
    snapshot = runtime_data.coordinator.data

    payload = {
        "entry": {
            "title": config_entry.title,
            "data": dict(config_entry.data),
            "options": dict(config_entry.options),
            "unique_id": config_entry.unique_id,
        },
        "controller": {
            "device_id": runtime_data.device_id,
            "controller_name": runtime_data.controller_name,
            "firmware_version": runtime_data.firmware_version,
            "raw_snapshot_size": snapshot.raw_size,
        },
        "zones": [
            {
                "index": zone.index,
                "name": zone.name,
                "is_open": zone.is_open,
                "set_percentage": zone.set_percentage,
                "actual_percentage": zone.actual_percentage,
            }
            for zone in snapshot.zones
        ],
    }

    return async_redact_data(payload, TO_REDACT)
