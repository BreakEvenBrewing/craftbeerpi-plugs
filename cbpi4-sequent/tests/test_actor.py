import asyncio
from unittest.mock import MagicMock

import pytest

from cbpi4_sequent.hardware import HardwareError
from cbpi4_sequent.actor import SequentRelay


def make_actor(board_id=0, relay=1, startup_state=None):
    cbpi = MagicMock()
    props = {"BoardID": board_id, "Relay": relay}
    if startup_state is not None:
        props["StartupState"] = startup_state
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

    def test_on_start_forces_relay_off(self, monkeypatch):
        actor = make_actor(board_id=1, relay=3)
        actor.state = True
        calls = []
        monkeypatch.setattr(actor.board, "set", lambda relay, state: calls.append((relay, state)))

        asyncio.run(actor.on_start())

        assert calls == [(3, False)]
        assert actor.state is False

    def test_on_start_startup_state_off_forces_relay_off(self, monkeypatch):
        actor = make_actor(relay=3, startup_state="Off")
        actor.state = True
        calls = []
        monkeypatch.setattr(actor.board, "set", lambda relay, state: calls.append((relay, state)))

        asyncio.run(actor.on_start())

        assert calls == [(3, False)]
        assert actor.state is False

    def test_on_start_startup_state_on_energizes_relay(self, monkeypatch):
        actor = make_actor(relay=8, startup_state="On")
        calls = []
        monkeypatch.setattr(actor.board, "set", lambda relay, state: calls.append((relay, state)))

        asyncio.run(actor.on_start())

        assert calls == [(8, True)]
        assert actor.state is True

    def test_on_start_startup_state_on_reports_off_on_hardware_error(self, monkeypatch):
        actor = make_actor(startup_state="On")

        def raise_error(relay, state):
            raise HardwareError("relay board not detected")

        monkeypatch.setattr(actor.board, "set", raise_error)

        asyncio.run(actor.on_start())

        assert actor.state is False

    def test_empty_startup_state_defaults_to_off(self):
        assert make_actor(startup_state="").startup_state == "Off"

    def test_invalid_startup_state_raises(self):
        from cbpi.api import ActorException

        with pytest.raises(ActorException):
            make_actor(startup_state="Maybe")

    def test_on_start_reports_off_on_hardware_error(self, monkeypatch):
        actor = make_actor()
        actor.state = True

        def raise_error(relay, state):
            raise HardwareError("relay board not detected")

        monkeypatch.setattr(actor.board, "set", raise_error)

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

    def test_on_accepts_power_and_output(self, monkeypatch):
        # cbpi 4.7.4's ActorController calls instance.on(power, output).
        actor = make_actor()
        monkeypatch.setattr(actor.board, "set", lambda relay, state: None)

        asyncio.run(actor.on(100, 100))

        assert actor.state is True

    def test_get_state_returns_plain_bool(self):
        actor = make_actor()
        assert actor.get_state() is False
        actor.state = True
        assert actor.get_state() is True

    def test_instances_do_not_share_state(self, monkeypatch):
        a = make_actor(relay=1)
        b = make_actor(relay=2)
        monkeypatch.setattr(a.board, "set", lambda relay, state: None)

        asyncio.run(a.on())

        assert a.get_state() is True
        assert b.get_state() is False
