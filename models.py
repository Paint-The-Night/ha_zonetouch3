"""Runtime models for Zone Touch 3."""

from __future__ import annotations

from dataclasses import dataclass

from .api import ZoneTouch3Client
from .coordinator import ZoneTouch3DataUpdateCoordinator


@dataclass(slots=True)
class ZoneTouch3RuntimeData:
    """Runtime data kept for an active Zone Touch 3 config entry."""

    client: ZoneTouch3Client
    coordinator: ZoneTouch3DataUpdateCoordinator
    device_id: str
    controller_name: str
    firmware_version: str | None
