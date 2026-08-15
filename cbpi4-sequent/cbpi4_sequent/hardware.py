"""Thin adapters around Sequent Microsystems' Python libraries.

These wrap ``librtd`` (SMrtd) and ``lib8relind`` (SM8relind) so the rest of
the plugin never imports the vendor libraries directly. That keeps hardware
access in one place and lets tests substitute a fake board instead of
talking to real I2C hardware.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class HardwareError(Exception):
    """Raised when a Sequent board can't be reached or returns bad data."""


class RtdBoard:
    """Adapter around the Sequent RTD Data Acquisition HAT (``librtd``)."""

    MIN_CHANNEL = 1
    MAX_CHANNEL = 8

    def __init__(self, board_id: int):
        self.board_id = board_id

    def read_temperature(self, channel: int) -> float:
        """Return the temperature in Celsius read from ``channel``.

        Raises ``HardwareError`` if the board is missing, the channel is out
        of range, or the RTD channel is open/disconnected.
        """
        if not (self.MIN_CHANNEL <= channel <= self.MAX_CHANNEL):
            raise HardwareError(
                f"Invalid RTD channel {channel}: must be between "
                f"{self.MIN_CHANNEL} and {self.MAX_CHANNEL}"
            )

        import librtd

        try:
            value = librtd.get(self.board_id, channel)
        except Exception as exc:
            raise HardwareError(
                f"Failed to read RTD board {self.board_id} channel {channel}: {exc}"
            ) from exc

        # An open/disconnected PT100 channel reads as (or very near) the
        # board's initialization sentinel of absolute zero.
        if value <= -273.0:
            raise HardwareError(
                f"RTD board {self.board_id} channel {channel} appears open "
                f"or disconnected (reading {value}°C)"
            )

        return value


class RelayBoard:
    """Adapter around the Sequent 8-relay Industrial HAT (``lib8relind``)."""

    MIN_RELAY = 1
    MAX_RELAY = 8

    def __init__(self, board_id: int):
        self.board_id = board_id

    def set(self, relay: int, state: bool) -> None:
        """Turn ``relay`` on (``state=True``) or off (``state=False``)."""
        self._validate(relay)

        import lib8relind

        try:
            lib8relind.set(self.board_id, relay, 1 if state else 0)
        except Exception as exc:
            raise HardwareError(
                f"Failed to set relay board {self.board_id} relay {relay}: {exc}"
            ) from exc

    def get(self, relay: int) -> bool:
        """Return whether ``relay`` is currently on."""
        self._validate(relay)

        import lib8relind

        try:
            return bool(lib8relind.get(self.board_id, relay))
        except Exception as exc:
            raise HardwareError(
                f"Failed to read relay board {self.board_id} relay {relay}: {exc}"
            ) from exc

    def _validate(self, relay: int) -> None:
        if not (self.MIN_RELAY <= relay <= self.MAX_RELAY):
            raise HardwareError(
                f"Invalid relay {relay}: must be between "
                f"{self.MIN_RELAY} and {self.MAX_RELAY}"
            )
