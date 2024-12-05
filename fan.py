"""Platform for light integration."""

from __future__ import annotations

import logging
from pprint import pformat
from typing import Any

import voluptuous as vol

from homeassistant.components.fan import PLATFORM_SCHEMA, FanEntity, FanEntityFeature
from homeassistant.const import CONF_IP_ADDRESS, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant

# Import the device class from the component that you want to support
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .zonetouch3 import zonetouch3_device

_LOGGER = logging.getLogger("zonetouch3")

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME): cv.string,
        vol.Required(CONF_IP_ADDRESS): cv.string,
        vol.Optional(CONF_PORT): cv.port,
    }
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the fan/s platform."""
    # Add devices
    _LOGGER.info(pformat(config))

    zone0 = {
        "name": config[CONF_NAME] + "_zone0",
        "address": config[CONF_IP_ADDRESS],
        "port": config[CONF_PORT],
        "zone": "0",
    }
    zone1 = {
        "name": config[CONF_NAME] + "_Zone1",
        "address": config[CONF_IP_ADDRESS],
        "port": config[CONF_PORT],
        "zone": "1",
    }
    zone2 = {
        "name": config[CONF_NAME] + "_Zone2",
        "address": config[CONF_IP_ADDRESS],
        "port": config[CONF_PORT],
        "zone": "2",
    }
    zone3 = {
        "name": config[CONF_NAME] + "_Zone3",
        "address": config[CONF_IP_ADDRESS],
        "port": config[CONF_PORT],
        "zone": "3",
    }
    zone4 = {
        "name": config[CONF_NAME] + "_Zone4",
        "address": config[CONF_IP_ADDRESS],
        "port": config[CONF_PORT],
        "zone": "4",
    }
    zone5 = {
        "name": config[CONF_NAME] + "_Zone5",
        "address": config[CONF_IP_ADDRESS],
        "port": config[CONF_PORT],
        "zone": "5",
    }
    zone6 = {
        "name": config[CONF_NAME] + "_Zone6",
        "address": config[CONF_IP_ADDRESS],
        "port": config[CONF_PORT],
        "zone": "6",
    }

    add_entities([zonetouch_3(zone0)])
    add_entities([zonetouch_3(zone1)])
    add_entities([zonetouch_3(zone2)])
    add_entities([zonetouch_3(zone3)])
    add_entities([zonetouch_3(zone4)])
    add_entities([zonetouch_3(zone5)])
    add_entities([zonetouch_3(zone6)])


class zonetouch_3(FanEntity):
    # Implement one of these methods.

    _attr_icon = "mdi:air-conditioner"
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.TURN_OFF
        | FanEntityFeature.TURN_ON
    )

    def __init__(self, fan) -> None:
        """Initialize an zonetouch 3 device."""
        _LOGGER.info(pformat(fan))
        self.fan = zonetouch3_device(fan["address"], fan["port"], fan["zone"])
        self._name = fan["name"]
        # Default state
        self._state = False
        self._attr_percentage = 0

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

    def turn_on(
        self,
        percentage: int | None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        self.fan.state = {"state": True, "percentage": percentage}

    def set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        self.fan.state = {"state": None, "percentage": percentage}

    def turn_off(self, **kwargs: Any) -> None:
        """Turn the fan off."""
        self.fan.state = {"state": False, "percentage": 0}

    def update(self) -> None:
        """Get live state of individual fan."""
        self.fan.get_state()
        self._state = self.fan.state["state"]
        self._attr_percentage = self.fan.state["percentage"]
