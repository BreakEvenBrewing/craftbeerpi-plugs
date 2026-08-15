import asyncio
from unittest.mock import MagicMock

import pytest

from cbpi4_sequent.hardware import HardwareError
from cbpi4_sequent.actor import SequentRelay


def make_actor(board_id=0, relay=1):
    cbpi = MagicMock()
    props = {"BoardID": board_id, "Relay": relay}
    return SequentRelay(cbpi, "actor-1", props)


class TestSequentRelay:
    def test_invalid_board_id_raises(self):
        from cbpi.api import ActorException

        with pytest.raises(ActorException):
            SequentRelay(MagicMock(), "actor-1", {"BoardID": 99, "Relay": 1})

    def test_invalid_relay_raises(self):
        from cbpi.api import ActorException

        with pytest.raises(ActorException):
            SequentRelay(MagicMock(), "actor-1", {"BoardID": 0, "Relay": 99})

    def test_on_sets_relay_and_state(self, monkeypatch):
        actor = make_actor(board_id=1, relay=3)
        calls = []
        monkeypatch.setattr(actor.board, "set", lambda relay, state: calls.append((relay, state)))

        asyncio.run(actor.on())

        assert calls == [(3, True)]
        assert actor.state is True

    def test_off_sets_relay_and_state(self, monkeypatch):
        actor = make_actor(board_id=1, relay=3)
        actor.state = True
        calls = []
        monkeypatch.setattr(actor.board, "set", lambda relay, state: calls.append((relay, state)))

        asyncio.run(actor.off())

        assert calls == [(3, False)]
        assert actor.state is False

    def test_on_start_reads_current_relay_state(self, monkeypatch):
        actor = make_actor()
        monkeypatch.setattr(actor.board, "get", lambda relay: True)

        asyncio.run(actor.on_start())

        assert actor.state is True

    def test_on_start_defaults_to_off_on_hardware_error(self, monkeypatch):
        actor = make_actor()

        def raise_error(relay):
            raise HardwareError("relay board not detected")

        monkeypatch.setattr(actor.board, "get", raise_error)

        asyncio.run(actor.on_start())

        assert actor.state is False

    def test_on_swallows_hardware_error_and_leaves_state_unchanged(self, monkeypatch):
        actor = make_actor()
        actor.state = False

        def raise_error(relay, state):
            raise HardwareError("relay board not detected")

        monkeypatch.setattr(actor.board, "set", raise_error)

        asyncio.run(actor.on())

        assert actor.state is False

    def test_get_state_reports_current_state(self):
        actor = make_actor()
        actor.state = True
        assert actor.get_state() == {"state": True}
