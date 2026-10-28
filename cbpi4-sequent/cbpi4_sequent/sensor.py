import asyncio
import logging
import math

from cbpi.api import CBPiSensor, Property, SensorException, parameters

from .hardware import HardwareError, RtdBoard

logger = logging.getLogger(__name__)

BOARD_IDS = [0, 1, 2, 3, 4, 5, 6, 7]
CHANNELS = [1, 2, 3, 4, 5, 6, 7, 8]
CALIBRATION_UNITS = ["C", "F"]


@parameters(
    [
        Property.Select(
            label="BoardID",
            options=BOARD_IDS,
            description="Stack/board ID of the Sequent RTD HAT (address jumpers, 0-7)",
        ),
        Property.Select(
            label="Channel",
            options=CHANNELS,
            description="RTD input channel on the board (1-8)",
        ),
        Property.Select(
            label="Interval",
            options=[1, 5, 10, 30, 60],
            default_value=5,
            description="Read interval in seconds",
        ),
        Property.Number(
            label="CalibrationOffset",
            configurable=True,
            default_value=0,
            unit="degree",
            description="Temperature correction added to the measured value. Positive or "
            "negative decimal degrees; specify °C or °F using CalibrationUnit.",
        ),
        Property.Select(
            label="CalibrationUnit",
            options=CALIBRATION_UNITS,
            description="Unit of CalibrationOffset (C or F). Required when the offset "
            "is not 0; converted automatically if the display unit differs.",
        ),
    ]
)
class SequentRTD(CBPiSensor):
    """CBPi sensor reading a PT100 probe from a Sequent RTD HAT."""

    def __init__(self, cbpi, id, props):
        super().__init__(cbpi, id, props)
        self.value = 0
        self.board_id = int(self.props.get("BoardID", 0))
        self.channel = int(self.props.get("Channel", 1))
        self.interval = int(self.props.get("Interval", 5))

        if self.board_id not in BOARD_IDS:
            raise SensorException(f"Invalid Sequent RTD board ID: {self.board_id}")
        if self.channel not in CHANNELS:
            raise SensorException(f"Invalid Sequent RTD channel: {self.channel}")

        self.offset, self.offset_unit = self._parse_calibration()

        self.board = RtdBoard(self.board_id)

    def _parse_calibration(self):
        # Sensors configured before calibration existed have neither property;
        # the UI may also send an empty string for a cleared number field.
        raw = self.props.get("CalibrationOffset")
        if raw is None or raw == "":
            raw = 0
        try:
            offset = float(raw)
        except (TypeError, ValueError):
            raise SensorException(f"Invalid Sequent RTD calibration offset: {raw!r}")
        if not math.isfinite(offset):
            raise SensorException(f"Invalid Sequent RTD calibration offset: {raw!r}")

        unit = self.props.get("CalibrationUnit") or None
        if unit is not None and unit not in CALIBRATION_UNITS:
            raise SensorException(f"Invalid Sequent RTD calibration unit: {unit!r}")
        if offset != 0 and unit is None:
            # Guessing would silently apply e.g. a Fahrenheit offset to Celsius.
            raise SensorException(
                "Sequent RTD calibration offset is set but CalibrationUnit is not (choose C or F)"
            )
        return offset, unit

    def offset_in(self, unit):
        """Return the calibration offset expressed as a difference in ``unit``."""
        if self.offset == 0 or self.offset_unit == unit:
            return self.offset
        # Temperature differences scale by 9/5 with no +32 shift.
        return self.offset * 9.0 / 5.0 if unit == "F" else self.offset * 5.0 / 9.0

    def get_state(self):
        return dict(value=self.value)

    async def run(self):
        while self.running:
            try:
                temp_c = self.board.read_temperature(self.channel)
            except HardwareError as exc:
                logger.error(
                    "SequentRTD %s (board %s, channel %s): %s",
                    self.id, self.board_id, self.channel, exc,
                )
                await asyncio.sleep(self.interval)
                continue

            unit = self.get_config_value("TEMP_UNIT", "C")
            temp = temp_c if unit == "C" else (temp_c * 9.0 / 5.0 + 32)
            self.value = round(temp + self.offset_in(unit), 2)

            self.push_update(self.value)
            self.log_data(self.value)

            await asyncio.sleep(self.interval)
