import logging

from cbpi.api import ActorException, CBPiActor, Property, parameters

from .hardware import HardwareError, RelayBoard

logger = logging.getLogger(__name__)

BOARD_IDS = [0, 1, 2, 3, 4, 5, 6, 7]
RELAYS = [1, 2, 3, 4, 5, 6, 7, 8]
STARTUP_STATES = ["Off", "On"]


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
        Property.Select(
            label="StartupState",
            options=STARTUP_STATES,
            description="Relay state when CBPi starts (default: Off). Use On to energize "
            "e.g. an NC-wired error lamp relay so the lamp goes out once CBPi is up.",
        ),
    ]
)
class SequentRelay(CBPiActor):
    """CBPi actor driving one relay on a Sequent 8-relay Industrial HAT."""

    def __init__(self, cbpi, id, props):
        super().__init__(cbpi, id, props)
        self.board_id = int(self.props.get("BoardID", 0))
        self.relay = int(self.props.get("Relay", 1))
        # Actors configured before this property existed have no value: treat as Off.
        self.startup_state = self.props.get("StartupState") or "Off"

        if self.board_id not in BOARD_IDS:
            raise ActorException(f"Invalid Sequent relay board ID: {self.board_id}")
        if self.relay not in RELAYS:
            raise ActorException(f"Invalid Sequent relay channel: {self.relay}")
        if self.startup_state not in STARTUP_STATES:
            raise ActorException(f"Invalid Sequent relay startup state: {self.startup_state}")

        self.board = RelayBoard(self.board_id)

    async def on_start(self):
        # Always drive the relay to its configured startup state rather than
        # adopting whatever it happened to be left at. Report OFF unless the
        # hardware write succeeds.
        startup_on = self.startup_state == "On"
        self.state = False
        try:
            self.board.set(self.relay, startup_on)
            self.state = startup_on
            logger.info(
                "SequentRelay %s startup %s (board %s, relay %s)",
                self.id, self.startup_state.upper(), self.board_id, self.relay,
            )
        except HardwareError as exc:
            logger.error(
                "SequentRelay %s (board %s, relay %s) failed to set startup state %s: %s",
                self.id, self.board_id, self.relay, self.startup_state, exc,
            )

    async def on(self, power=None, output=None):
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
        # Actor.to_dict() sends this value as the UI's "state" field, which the
        # UI tests for truthiness, so it must be a plain bool. A dict like
        # {"state": False} is truthy in JS and renders as ON.
        return self.state
