"""Platform for light integration."""

from __future__ import annotations

import logging
from pprint import pformat
import time
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.const import CONF_ENTITIES, CONF_IP_ADDRESS, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant

# Import the device class from the component that you want to support
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .zonetouch3 import zonetouch3_device

_LOGGER = logging.getLogger("zonetouch3")


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the fan platform from a config entry."""
    config = config_entry.data
    _LOGGER.info(pformat(config))

    # loop though zone amount, create/entities objects per zone
    for zone_no in range(0, config[CONF_ENTITIES]):
        async_add_entities(
            [
                zonetouch_3(
                    {
                        "name": config[CONF_NAME] + "_Zone" + str(zone_no),
                        "address": config[CONF_IP_ADDRESS],
                        "port": config[CONF_PORT],
                        "zone": str(zone_no),
                    }
                )
            ]
        )


class zonetouch_3(FanEntity):
    """Zone Touch entity."""

    _attr_icon = "mdi:air-conditioner"
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.TURN_OFF
        | FanEntityFeature.TURN_ON
    )

    def __init__(self, fan) -> None:
        """Initialize an zonetouch 3 entity/object."""
        _LOGGER.info(pformat(fan))
        # Object
        self.fan = zonetouch3_device(fan["address"], fan["port"], fan["zone"])
        self._name = fan["name"]
        self._attr_unique_id = self._name
        # Default state
        self._state = False
        self._attr_percentage = 0

    # Getters
    @property
    def name(self) -> str:
        """Return the display name of this fan."""
        return self._name

    @property
    def is_on(self) -> bool | None:
        """Return true if the entity is on."""
        return self._state

    @property
    def percentage(self) -> int | None:
        """Return the current percentage."""
        return self._attr_percentage

    # Setters
    def turn_on(
        self,
        percentage: int | None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        self.fan.state = {"state": True, "percentage": percentage}
        self.update()

    def set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        self.fan.state = {"state": None, "percentage": percentage}
        self.update()  # Check current status

    def turn_off(self, **kwargs: Any) -> None:
        """Turn the fan off."""
        self.fan.state = {"state": False, "percentage": 0}
        self.update()  # Check current status

    def update(self) -> None:
        """Get live state of individual fan."""
        self.fan.get_state()
        self._state = self.fan.state["state"]
        self._attr_percentage = self.fan.state["percentage"]
