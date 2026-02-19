"""Fan platform for Zone Touch 3 zones."""

from __future__ import annotations

from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ZoneTouch3DataUpdateCoordinator
from .models import ZoneTouch3RuntimeData


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Zone Touch 3 fan entities from a config entry."""
    runtime_data: ZoneTouch3RuntimeData = hass.data[DOMAIN][entry.entry_id]
    coordinator = runtime_data.coordinator

    entities: dict[int, ZoneTouch3ZoneFanEntity] = {}
    known_zone_indexes: set[int] = set()

    entity_registry = er.async_get(hass)
    known_prefix = f"{runtime_data.device_id}_zone_"
    for registry_entry in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
        if registry_entry.domain != "fan":
            continue
        if not registry_entry.unique_id.startswith(known_prefix):
            continue
        try:
            known_zone_indexes.add(int(registry_entry.unique_id.removeprefix(known_prefix)))
        except ValueError:
            continue

    @callback
    def _sync_entities() -> None:
        new_entities: list[ZoneTouch3ZoneFanEntity] = []

        for zone in coordinator.data.zones:
            known_zone_indexes.add(zone.index)

        for zone_index in sorted(known_zone_indexes):
            if zone_index in entities:
                continue

            entity = ZoneTouch3ZoneFanEntity(
                config_entry=entry,
                runtime_data=runtime_data,
                zone_index=zone_index,
            )
            entities[zone_index] = entity
            new_entities.append(entity)

        if new_entities:
            async_add_entities(new_entities)

    _sync_entities()
    entry.async_on_unload(coordinator.async_add_listener(_sync_entities))


class ZoneTouch3ZoneFanEntity(
    CoordinatorEntity[ZoneTouch3DataUpdateCoordinator],
    FanEntity,
):
    """Representation of a Zone Touch 3 zone damper."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:air-conditioner"
    _attr_percentage_step = 1
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )

    def __init__(
        self,
        config_entry: ConfigEntry,
        runtime_data: ZoneTouch3RuntimeData,
        zone_index: int,
    ) -> None:
        super().__init__(runtime_data.coordinator)
        self._config_entry = config_entry
        self._runtime_data = runtime_data
        self._zone_index = zone_index
        self._attr_unique_id = f"{runtime_data.device_id}_zone_{zone_index}"
        self._attr_name = self._fallback_zone_name

    @property
    def _fallback_zone_name(self) -> str:
        return f"Zone {self._zone_index + 1}"

    @property
    def _zone(self):
        return self.coordinator.get_zone(self._zone_index)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and self._zone is not None

    @property
    def is_on(self) -> bool | None:
        """Return true if the zone is open."""
        zone = self._zone
        if zone is None:
            return None
        return zone.is_open

    @property
    def percentage(self) -> int | None:
        """Return the configured zone opening percentage."""
        zone = self._zone
        if zone is None:
            return None
        return zone.set_percentage

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        zone = self._zone
        if zone is None:
            return None

        return {
            "actual_percentage": zone.actual_percentage,
            "zone_index": self._zone_index,
        }

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for this zone entity."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._runtime_data.device_id)},
            name=self._runtime_data.controller_name,
            manufacturer="Polyaire",
            model="Zone Touch 3",
            sw_version=self._runtime_data.firmware_version,
            configuration_url=f"http://{self._config_entry.data[CONF_HOST]}",
        )

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Open the zone damper."""
        del preset_mode
        del kwargs

        zone = self._zone
        target_percentage = percentage
        if target_percentage is None:
            target_percentage = zone.set_percentage if zone and zone.set_percentage > 0 else 100

        await self.coordinator.async_apply_zone_percentage(
            zone_index=self._zone_index,
            percentage=target_percentage,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Close the zone damper."""
        del kwargs

        await self.coordinator.async_apply_zone_change(
            zone_index=self._zone_index,
            turn_on=False,
            percentage=0,
        )

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the zone opening percentage."""
        if percentage <= 0:
            await self.async_turn_off()
            return

        await self.coordinator.async_apply_zone_percentage(
            zone_index=self._zone_index,
            percentage=percentage,
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        zone = self._zone
        if zone is not None and zone.name != self._attr_name:
            self._attr_name = zone.name
        super()._handle_coordinator_update()
