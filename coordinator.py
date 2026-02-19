"""Coordinator for Zone Touch 3 state updates."""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from datetime import timedelta
import logging
import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ZoneTouch3Client, ZoneTouch3Snapshot, ZoneTouch3Zone
from .const import (
    CONF_COMMAND_GAP,
    CONF_ENFORCE_MIN_OPEN_ZONE,
    CONF_POST_COMMAND_SETTLE,
    CONF_SCAN_INTERVAL,
    DEFAULT_COMMAND_GAP,
    DEFAULT_ENFORCE_MIN_OPEN_ZONE,
    DEFAULT_POST_COMMAND_SETTLE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .exceptions import ZoneTouch3ConnectionError, ZoneTouch3ProtocolError

_LOGGER = logging.getLogger(__name__)
COMMAND_BATCH_WINDOW_SECONDS = 0.1
TURN_ON_SETTLE_SECONDS = 1.0


@dataclass(slots=True)
class _PendingZoneCommand:
    """A queued zone change that may be superseded by newer commands."""

    turn_on: bool | None
    percentage: int | None
    generation: int
    future: asyncio.Future[None]


class ZoneTouch3DataUpdateCoordinator(DataUpdateCoordinator[ZoneTouch3Snapshot]):
    """Manage fetching data and sending commands to Zone Touch 3."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: ZoneTouch3Client,
    ) -> None:
        self.config_entry = config_entry
        self.client = client

        self._pending_lock = asyncio.Lock()
        self._pending_zone_commands: dict[int, _PendingZoneCommand] = {}
        self._latest_zone_generation: dict[int, int] = {}
        self._dispatch_task: asyncio.Task[None] | None = None

        self._command_lock = asyncio.Lock()
        self._command_generation = 0
        self._last_command_ts: float | None = None

        self._refresh_generation = 0
        self._refresh_task: asyncio.Task[None] | None = None

        scan_interval = int(
            config_entry.options.get(
                CONF_SCAN_INTERVAL,
                config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            )
        )
        self._command_gap = float(
            config_entry.options.get(
                CONF_COMMAND_GAP,
                config_entry.data.get(CONF_COMMAND_GAP, DEFAULT_COMMAND_GAP),
            )
        )
        self._post_command_settle = float(
            config_entry.options.get(
                CONF_POST_COMMAND_SETTLE,
                config_entry.data.get(
                    CONF_POST_COMMAND_SETTLE, DEFAULT_POST_COMMAND_SETTLE
                ),
            )
        )

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{config_entry.entry_id}",
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> ZoneTouch3Snapshot:
        """Fetch data from Zone Touch 3."""
        try:
            return await self.hass.async_add_executor_job(self.client.fetch_snapshot)
        except ZoneTouch3ConnectionError as err:
            raise UpdateFailed(str(err)) from err
        except ZoneTouch3ProtocolError as err:
            raise UpdateFailed(f"Invalid protocol data: {err}") from err

    async def async_apply_zone_change(
        self,
        zone_index: int,
        turn_on: bool | None,
        percentage: int | None,
        bypass_min_open_guard: bool = False,
    ) -> None:
        """Apply a zone change command and refresh state."""
        zone = self.get_zone(zone_index)
        if zone is None:
            raise HomeAssistantError(f"Zone {zone_index + 1} is not currently available")

        if turn_on is False and self._enforce_min_open_zone and not bypass_min_open_guard:
            open_count = sum(1 for zone_state in self.data.zones if zone_state.is_open)
            if zone.is_open and open_count <= 1:
                raise HomeAssistantError(
                    "Safety guard blocked this change because it would close the last open zone"
                )

        command_future = await self._async_enqueue_zone_command(
            zone_index=zone_index,
            turn_on=turn_on,
            percentage=percentage,
        )
        await command_future

    async def async_apply_all_zones(
        self,
        percentage: int,
        *,
        bypass_min_open_guard: bool = True,
    ) -> None:
        """Apply one percentage target to all known zones."""
        if self.data is None:
            raise HomeAssistantError("Zone data is not available yet")

        target = max(0, min(100, int(percentage)))
        if target <= 0:
            tasks = [
                self.async_apply_zone_change(
                    zone_index=zone.index,
                    turn_on=False,
                    percentage=0,
                    bypass_min_open_guard=bypass_min_open_guard,
                )
                for zone in self.data.zones
            ]
        else:
            tasks = [
                self.async_apply_zone_percentage(zone.index, target)
                for zone in self.data.zones
            ]

        await asyncio.gather(*tasks)

    async def async_apply_zone_percentage(
        self,
        zone_index: int,
        percentage: int,
    ) -> None:
        """Apply a percentage reliably, including for currently closed zones."""
        zone = self.get_zone(zone_index)
        if zone is not None and zone.is_open:
            await self.async_apply_zone_change(
                zone_index=zone_index,
                turn_on=None,
                percentage=percentage,
            )
            return

        await self.async_apply_zone_change(
            zone_index=zone_index,
            turn_on=True,
            percentage=percentage,
        )
        await asyncio.sleep(TURN_ON_SETTLE_SECONDS)
        await self.async_apply_zone_change(
            zone_index=zone_index,
            turn_on=None,
            percentage=percentage,
        )

    async def async_shutdown(self) -> None:
        """Cancel outstanding tasks when unloading the integration."""
        if self._dispatch_task is not None:
            self._dispatch_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._dispatch_task
            self._dispatch_task = None

        async with self._pending_lock:
            for command in self._pending_zone_commands.values():
                if not command.future.done():
                    command.future.cancel()
            self._pending_zone_commands.clear()

        if self._refresh_task is None:
            return

        self._refresh_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._refresh_task
        self._refresh_task = None

    def get_zone(self, zone_index: int) -> ZoneTouch3Zone | None:
        """Return a zone by its index."""
        if self.data is None:
            return None

        return next((zone for zone in self.data.zones if zone.index == zone_index), None)

    @property
    def _enforce_min_open_zone(self) -> bool:
        return bool(
            self.config_entry.options.get(
                CONF_ENFORCE_MIN_OPEN_ZONE,
                self.config_entry.data.get(
                    CONF_ENFORCE_MIN_OPEN_ZONE, DEFAULT_ENFORCE_MIN_OPEN_ZONE
                ),
            )
        )

    async def _async_respect_command_gap_locked(self) -> None:
        """Throttle command writes so Zone Touch 3 is not flooded by bursts."""
        if self._command_gap <= 0 or self._last_command_ts is None:
            return

        elapsed = time.monotonic() - self._last_command_ts
        wait_time = self._command_gap - elapsed
        if wait_time > 0:
            await asyncio.sleep(wait_time)

    async def _async_enqueue_zone_command(
        self,
        zone_index: int,
        turn_on: bool | None,
        percentage: int | None,
    ) -> asyncio.Future[None]:
        """Queue a zone command, replacing any older pending command for the same zone."""
        loop = asyncio.get_running_loop()
        command_future: asyncio.Future[None] = loop.create_future()

        async with self._pending_lock:
            self._command_generation += 1
            command_generation = self._command_generation
            self._latest_zone_generation[zone_index] = command_generation

            previous = self._pending_zone_commands.get(zone_index)
            if previous is not None and not previous.future.done():
                previous.future.set_result(None)

            self._pending_zone_commands[zone_index] = _PendingZoneCommand(
                turn_on=turn_on,
                percentage=percentage,
                generation=command_generation,
                future=command_future,
            )

            if self._dispatch_task is None or self._dispatch_task.done():
                self._dispatch_task = self.hass.async_create_task(
                    self._async_dispatch_pending_commands()
                )

        return command_future

    async def _async_dispatch_pending_commands(self) -> None:
        """Drain pending zone commands, coalescing rapid updates by zone."""
        try:
            while True:
                await asyncio.sleep(COMMAND_BATCH_WINDOW_SECONDS)

                async with self._pending_lock:
                    if not self._pending_zone_commands:
                        self._dispatch_task = None
                        return

                    batch = list(self._pending_zone_commands.items())
                    self._pending_zone_commands.clear()

                sent_any = False
                for zone_index, command in sorted(batch, key=lambda item: item[0]):
                    if command.generation != self._latest_zone_generation.get(zone_index):
                        if not command.future.done():
                            command.future.set_result(None)
                        continue

                    try:
                        sent = await self._async_send_zone_command(
                            zone_index,
                            command.turn_on,
                            command.percentage,
                            command.generation,
                        )
                    except HomeAssistantError as err:
                        if not command.future.done():
                            command.future.set_exception(err)
                    else:
                        if sent:
                            sent_any = True
                        if not command.future.done():
                            command.future.set_result(None)

                if sent_any:
                    self._refresh_generation += 1
                    self._schedule_refresh(self._refresh_generation)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Unhandled error while dispatching queued zone commands")
            async with self._pending_lock:
                for command in self._pending_zone_commands.values():
                    if not command.future.done():
                        command.future.set_exception(
                            HomeAssistantError("Zone command queue failed unexpectedly")
                        )
                self._pending_zone_commands.clear()
        finally:
            self._dispatch_task = None

    async def _async_send_zone_command(
        self,
        zone_index: int,
        turn_on: bool | None,
        percentage: int | None,
        generation: int,
    ) -> bool:
        """Send a single zone command to the controller with pacing safeguards."""
        async with self._command_lock:
            await self._async_respect_command_gap_locked()
            async with self._pending_lock:
                if generation != self._latest_zone_generation.get(zone_index):
                    return False

            try:
                await self.hass.async_add_executor_job(
                    self.client.set_zone_state,
                    zone_index,
                    turn_on,
                    percentage,
                )
            except ZoneTouch3ConnectionError as err:
                raise HomeAssistantError(f"Unable to send zone command: {err}") from err
            except ZoneTouch3ProtocolError as err:
                raise HomeAssistantError(f"Unable to build zone command: {err}") from err

            self._last_command_ts = time.monotonic()
            return True

    def _schedule_refresh(self, generation: int) -> None:
        """Debounce refreshes so command bursts trigger a single state poll."""
        if self._refresh_task is not None and not self._refresh_task.done():
            self._refresh_task.cancel()

        self._refresh_task = self.hass.async_create_task(
            self._async_debounced_refresh(generation)
        )

    async def _async_debounced_refresh(self, generation: int) -> None:
        """Refresh state after commands settle, unless superseded by newer commands."""
        try:
            if self._post_command_settle > 0:
                await asyncio.sleep(self._post_command_settle)

            if generation != self._refresh_generation:
                return

            async with self._command_lock:
                if generation != self._refresh_generation:
                    return
                await self.async_refresh()
        except asyncio.CancelledError:
            return
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Failed to refresh state after zone command burst")
