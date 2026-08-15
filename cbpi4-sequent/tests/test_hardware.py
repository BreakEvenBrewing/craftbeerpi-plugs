import sys
import types

import pytest

from cbpi4_sequent.hardware import HardwareError, RelayBoard, RtdBoard


def _install_fake_module(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


@pytest.fixture(autouse=True)
def _clear_fake_modules():
    yield
    sys.modules.pop("librtd", None)
    sys.modules.pop("lib8relind", None)


class TestRtdBoard:
    def test_read_temperature_returns_value(self):
        _install_fake_module("librtd", get=lambda stack, channel: 21.5)

        board = RtdBoard(board_id=0)
        assert board.read_temperature(1) == 21.5

    def test_read_temperature_passes_board_and_channel(self):
        seen = {}

        def fake_get(stack, channel):
            seen["stack"] = stack
            seen["channel"] = channel
            return 20.0

        _install_fake_module("librtd", get=fake_get)

        board = RtdBoard(board_id=3)
        board.read_temperature(5)
        assert seen == {"stack": 3, "channel": 5}

    def test_invalid_channel_raises_without_touching_hardware(self):
        _install_fake_module("librtd", get=lambda stack, channel: 21.5)

        board = RtdBoard(board_id=0)
        with pytest.raises(HardwareError):
            board.read_temperature(9)

    def test_missing_board_raises_hardware_error(self):
        def fake_get(stack, channel):
            raise ValueError("Fail to communicate with the RTD card")

        _install_fake_module("librtd", get=fake_get)

        board = RtdBoard(board_id=0)
        with pytest.raises(HardwareError):
            board.read_temperature(1)

    def test_open_channel_raises_hardware_error(self):
        _install_fake_module("librtd", get=lambda stack, channel: -273.15)

        board = RtdBoard(board_id=0)
        with pytest.raises(HardwareError):
            board.read_temperature(1)


class TestRelayBoard:
    def test_set_on_calls_vendor_lib_with_1(self):
        seen = {}

        def fake_set(stack, relay, value):
            seen["args"] = (stack, relay, value)

        _install_fake_module("lib8relind", set=fake_set, get=lambda stack, relay: 0)

        board = RelayBoard(board_id=0)
        board.set(1, True)
        assert seen["args"] == (0, 1, 1)

    def test_set_off_calls_vendor_lib_with_0(self):
        seen = {}

        def fake_set(stack, relay, value):
            seen["args"] = (stack, relay, value)

        _install_fake_module("lib8relind", set=fake_set, get=lambda stack, relay: 0)

        board = RelayBoard(board_id=2)
        board.set(3, False)
        assert seen["args"] == (2, 3, 0)

    def test_get_returns_bool(self):
        _install_fake_module("lib8relind", get=lambda stack, relay: 1, set=lambda *a: None)

        board = RelayBoard(board_id=0)
        assert board.get(1) is True

    def test_invalid_relay_raises_without_touching_hardware(self):
        _install_fake_module("lib8relind", get=lambda *a: 0, set=lambda *a: None)

        board = RelayBoard(board_id=0)
        with pytest.raises(HardwareError):
            board.set(9, True)

    def test_missing_board_raises_hardware_error(self):
        def fake_set(stack, relay, value):
            raise ValueError("8-relay card not detected!")

        _install_fake_module("lib8relind", set=fake_set, get=lambda *a: 0)

        board = RelayBoard(board_id=0)
        with pytest.raises(HardwareError):
            board.set(1, True)
