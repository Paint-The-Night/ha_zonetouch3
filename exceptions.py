"""Zone Touch 3 integration exceptions."""

from __future__ import annotations


class ZoneTouch3Error(Exception):
    """Base error raised by the Zone Touch 3 integration."""


class ZoneTouch3ConnectionError(ZoneTouch3Error):
    """Raised when Zone Touch 3 cannot be reached."""


class ZoneTouch3ProtocolError(ZoneTouch3Error):
    """Raised when Zone Touch 3 data cannot be parsed."""
