import asyncio
import logging

from cbpi.api import CBPiSensor, Property, SensorException, parameters

from .hardware import HardwareError, RtdBoard

logger = logging.getLogger(__name__)

BOARD_IDS = [0, 1, 2, 3, 4, 5, 6, 7]
CHANNELS = [1, 2, 3, 4, 5, 6, 7, 8]


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

        self.board = RtdBoard(self.board_id)

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
            self.value = round(temp_c if unit == "C" else (temp_c * 9.0 / 5.0 + 32), 2)

            self.push_update(self.value)
            self.log_data(self.value)

            await asyncio.sleep(self.interval)
