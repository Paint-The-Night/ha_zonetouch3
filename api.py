"""Low-level Zone Touch 3 client and protocol parsing."""

from __future__ import annotations

from dataclasses import dataclass
import re
import socket
import threading

from .const import (
    MAX_ZONES,
    SET_ZONE_COMMAND_TEMPLATE,
    SNAPSHOT_REQUEST_HEX,
    ZONE_BLOCK_BASE_OFFSET,
    ZONE_BLOCK_LENGTH,
    ZONE_INDEX_OFFSET_SHIFT_START,
)
from .exceptions import ZoneTouch3ConnectionError, ZoneTouch3ProtocolError

ASCII_SEGMENT_MIN_LENGTH = 3
DEVICE_ID_REGEX = re.compile(r"^[0-9A-F]{16}$")
FIRMWARE_REGEX = re.compile(r"^\d+\.\d+\.\d+\.\d+$")
PREFIXED_NAME_REGEX = re.compile(r"^\d+([A-Za-z][A-Za-z0-9 _-]+)$")


@dataclass(slots=True, frozen=True)
class ZoneTouch3Zone:
    """A single zone state from Zone Touch 3."""

    index: int
    name: str
    is_open: bool
    set_percentage: int
    actual_percentage: int


@dataclass(slots=True, frozen=True)
class ZoneTouch3Snapshot:
    """A full Zone Touch 3 state snapshot."""

    device_id: str
    controller_name: str
    firmware_version: str | None
    zones: tuple[ZoneTouch3Zone, ...]
    raw_size: int


class ZoneTouch3Client:
    """Synchronous Zone Touch 3 TCP client."""

    def __init__(self, host: str, port: int, socket_timeout: float) -> None:
        self._host = host
        self._port = port
        self._socket_timeout = socket_timeout
        self._io_lock = threading.Lock()

    def fetch_snapshot(self) -> ZoneTouch3Snapshot:
        """Fetch and parse a full zone state snapshot."""
        with self._io_lock:
            payload = self._send_frame(bytes.fromhex(SNAPSHOT_REQUEST_HEX))
        return self._parse_snapshot(payload)

    def set_zone_state(
        self,
        zone_index: int,
        turn_on: bool | None,
        percentage: int | None,
    ) -> None:
        """Set a zone state/percentage on the Zone Touch 3 controller."""
        if zone_index < 0 or zone_index >= MAX_ZONES:
            raise ZoneTouch3ProtocolError(
                f"Zone index {zone_index} is out of range 0..{MAX_ZONES - 1}"
            )

        if turn_on is None:
            state_code = 0x80  # set percentage only
        elif turn_on:
            state_code = 0x03  # turn on
        else:
            state_code = 0x02  # turn off

        target_percentage = _bound_percentage(percentage if percentage is not None else 0)

        payload = bytearray.fromhex(SET_ZONE_COMMAND_TEMPLATE)
        payload[18] = zone_index
        payload[19] = state_code
        payload[20] = target_percentage

        crc = _crc16_modbus(payload[4:22])
        payload[22] = (crc >> 8) & 0xFF
        payload[23] = crc & 0xFF

        with self._io_lock:
            self._send_frame(bytes(payload))

    def _send_frame(self, payload: bytes) -> bytes:
        try:
            with socket.create_connection(
                (self._host, self._port), timeout=self._socket_timeout
            ) as sock:
                sock.settimeout(self._socket_timeout)
                sock.sendall(payload)
                response = sock.recv(4096)
        except OSError as err:
            raise ZoneTouch3ConnectionError(
                f"Error communicating with {self._host}:{self._port}: {err}"
            ) from err

        if not response:
            raise ZoneTouch3ConnectionError(
                f"No response from {self._host}:{self._port}"
            )

        return response

    def _parse_snapshot(self, payload: bytes) -> ZoneTouch3Snapshot:
        if len(payload) < ZONE_BLOCK_BASE_OFFSET + ZONE_BLOCK_LENGTH:
            raise ZoneTouch3ProtocolError(
                f"Snapshot is too short to parse ({len(payload)} bytes)"
            )

        zones: list[ZoneTouch3Zone] = []
        for zone_index in range(MAX_ZONES):
            zone_offset = _zone_block_offset(zone_index)
            if zone_offset + ZONE_BLOCK_LENGTH > len(payload):
                break

            zone_mask = int.from_bytes(
                payload[zone_offset + 8 : zone_offset + 10], byteorder="little"
            )
            if zone_mask != (1 << zone_index):
                break

            state_byte = payload[zone_offset]
            if (state_byte & 0x0F) != (zone_index & 0x0F):
                break

            name = _parse_zone_name(payload[zone_offset + 10 : zone_offset + 22], zone_index)
            zones.append(
                ZoneTouch3Zone(
                    index=zone_index,
                    name=name,
                    is_open=(state_byte & 0xF0) == 0x40,
                    set_percentage=_bound_percentage(payload[zone_offset + 1]),
                    actual_percentage=_bound_percentage(payload[zone_offset + 3]),
                )
            )

        if not zones:
            raise ZoneTouch3ProtocolError("No zones could be parsed from snapshot")

        ascii_segments = _extract_ascii_segments(payload)
        device_id = _extract_device_id(ascii_segments, self._host)
        controller_name = _extract_controller_name(ascii_segments)
        firmware_version = _extract_firmware_version(ascii_segments)

        return ZoneTouch3Snapshot(
            device_id=device_id,
            controller_name=controller_name,
            firmware_version=firmware_version,
            zones=tuple(zones),
            raw_size=len(payload),
        )


def _zone_block_offset(zone_index: int) -> int:
    zone_offset = ZONE_BLOCK_BASE_OFFSET + (zone_index * ZONE_BLOCK_LENGTH)
    if zone_index >= ZONE_INDEX_OFFSET_SHIFT_START:
        zone_offset += 1
    return zone_offset


def _parse_zone_name(block: bytes, zone_index: int) -> str:
    raw_name = block.split(b"\x00", maxsplit=1)[0]
    name = raw_name.decode("ascii", errors="ignore").strip()
    if not name:
        return f"Zone {zone_index + 1}"
    return name


def _extract_ascii_segments(payload: bytes) -> list[str]:
    segments: list[str] = []
    start_index: int | None = None

    for index, value in enumerate(payload + b"\x00"):
        if 32 <= value <= 126:
            if start_index is None:
                start_index = index
            continue

        if start_index is None:
            continue

        if index - start_index >= ASCII_SEGMENT_MIN_LENGTH:
            segments.append(payload[start_index:index].decode("ascii", errors="ignore"))
        start_index = None

    return segments


def _extract_device_id(segments: list[str], fallback_host: str) -> str:
    for segment in segments:
        if DEVICE_ID_REGEX.fullmatch(segment):
            return segment.lower()
    return fallback_host.replace(".", "_")


def _extract_controller_name(segments: list[str]) -> str:
    for segment in segments:
        match = PREFIXED_NAME_REGEX.fullmatch(segment)
        if match:
            return match.group(1).strip()

    for segment in segments:
        if segment.startswith("Program"):
            continue
        if FIRMWARE_REGEX.fullmatch(segment):
            continue
        if segment.isdigit():
            continue
        if len(segment) <= 2:
            continue
        return segment

    return "Zone Touch 3"


def _extract_firmware_version(segments: list[str]) -> str | None:
    for segment in segments:
        if FIRMWARE_REGEX.fullmatch(segment):
            return segment
    return None


def _bound_percentage(value: int) -> int:
    return max(0, min(100, int(value)))


def _crc16_modbus(payload: bytes) -> int:
    crc = 0xFFFF
    for byte in payload:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc
