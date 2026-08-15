import logging

from cbpi.api import ActorException, CBPiActor, Property, parameters

from .hardware import HardwareError, RelayBoard

logger = logging.getLogger(__name__)

BOARD_IDS = [0, 1, 2, 3, 4, 5, 6, 7]
RELAYS = [1, 2, 3, 4, 5, 6, 7, 8]


@parameters(
    [
        Property.Select(
            label="BoardID",
            options=BOARD_IDS,
            description="Stack/board ID of the Sequent 8-relay Industrial HAT (address jumpers, 0-7)",
        ),
        Property.Select(
            label="Relay",
            options=RELAYS,
            description="Relay channel on the board (1-8)",
        ),
    ]
)
class SequentRelay(CBPiActor):
    """CBPi actor driving one relay on a Sequent 8-relay Industrial HAT."""

    def __init__(self, cbpi, id, props):
        super().__init__(cbpi, id, props)
        self.board_id = int(self.props.get("BoardID", 0))
        self.relay = int(self.props.get("Relay", 1))

        if self.board_id not in BOARD_IDS:
            raise ActorException(f"Invalid Sequent relay board ID: {self.board_id}")
        if self.relay not in RELAYS:
            raise ActorException(f"Invalid Sequent relay channel: {self.relay}")

        self.board = RelayBoard(self.board_id)

    async def on_start(self):
        try:
            self.state = self.board.get(self.relay)
        except HardwareError as exc:
            logger.error(
                "SequentRelay %s (board %s, relay %s): %s",
                self.id, self.board_id, self.relay, exc,
            )
            self.state = False

    async def on(self, power=None):
        try:
            self.board.set(self.relay, True)
            self.state = True
            logger.info(
                "SequentRelay %s ON (board %s, relay %s)",
                self.id, self.board_id, self.relay,
            )
        except HardwareError as exc:
            logger.error(
                "SequentRelay %s (board %s, relay %s) failed to turn on: %s",
                self.id, self.board_id, self.relay, exc,
            )

    async def off(self):
        try:
            self.board.set(self.relay, False)
            self.state = False
            logger.info(
                "SequentRelay %s OFF (board %s, relay %s)",
                self.id, self.board_id, self.relay,
            )
        except HardwareError as exc:
            logger.error(
                "SequentRelay %s (board %s, relay %s) failed to turn off: %s",
                self.id, self.board_id, self.relay, exc,
            )

    def get_state(self):
        return dict(state=self.state)
