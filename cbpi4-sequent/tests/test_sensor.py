import asyncio
from unittest.mock import MagicMock

import pytest

from cbpi4_sequent.hardware import HardwareError
from cbpi4_sequent.sensor import SequentRTD


def make_sensor(monkeypatch, board_id=0, channel=1, interval=1, read_values=None):
    cbpi = MagicMock()
    cbpi.config.get.return_value = "C"
    props = {"BoardID": board_id, "Channel": channel, "Interval": interval}

    sensor = SequentRTD(cbpi, "sensor-1", props)

    if read_values is not None:
        iterator = iter(read_values)
        monkeypatch.setattr(sensor.board, "read_temperature", lambda ch: next(iterator))

    return sensor


class TestSequentRTD:
    def test_invalid_board_id_raises(self, monkeypatch):
        from cbpi.api import SensorException

        cbpi = MagicMock()
        with pytest.raises(SensorException):
            SequentRTD(cbpi, "sensor-1", {"BoardID": 99, "Channel": 1})

    def test_invalid_channel_raises(self, monkeypatch):
        from cbpi.api import SensorException

        cbpi = MagicMock()
        with pytest.raises(SensorException):
            SequentRTD(cbpi, "sensor-1", {"BoardID": 0, "Channel": 99})

    def test_run_pushes_and_logs_reading(self, monkeypatch):
        sensor = make_sensor(monkeypatch, read_values=[21.23])
        sensor.push_update = MagicMock()
        sensor.log_data = MagicMock()

        async def stop_after_one_iteration(*args, **kwargs):
            sensor.running = False

        monkeypatch.setattr(asyncio, "sleep", stop_after_one_iteration)

        sensor.running = True
        asyncio.run(sensor.run())

        assert sensor.value == 21.23
        sensor.push_update.assert_called_once_with(21.23)
        sensor.log_data.assert_called_once_with(21.23)

    def test_run_converts_to_fahrenheit_when_configured(self, monkeypatch):
        sensor = make_sensor(monkeypatch, read_values=[20.0])
        sensor.cbpi.config.get.return_value = "F"
        sensor.push_update = MagicMock()
        sensor.log_data = MagicMock()

        async def stop_after_one_iteration(*args, **kwargs):
            sensor.running = False

        monkeypatch.setattr(asyncio, "sleep", stop_after_one_iteration)

        sensor.running = True
        asyncio.run(sensor.run())

        assert sensor.value == 68.0

    def test_run_survives_hardware_error_and_keeps_polling(self, monkeypatch):
        sensor = make_sensor(monkeypatch)
        calls = {"count": 0}

        def flaky_read(channel):
            calls["count"] += 1
            if calls["count"] == 1:
                raise HardwareError("board not detected")
            sensor.running = False
            return 19.5

        monkeypatch.setattr(sensor.board, "read_temperature", flaky_read)
        sensor.push_update = MagicMock()
        sensor.log_data = MagicMock()

        async def fast_sleep(*args, **kwargs):
            return None

        monkeypatch.setattr(asyncio, "sleep", fast_sleep)

        sensor.running = True
        asyncio.run(sensor.run())

        assert sensor.value == 19.5
        assert calls["count"] == 2
