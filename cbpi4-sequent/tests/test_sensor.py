import asyncio
from unittest.mock import MagicMock

import pytest

from cbpi4_sequent.hardware import HardwareError
from cbpi4_sequent.sensor import SequentRTD


def make_sensor(monkeypatch, board_id=0, channel=1, interval=1, read_values=None, **extra_props):
    cbpi = MagicMock()
    cbpi.config.get.return_value = "C"
    props = {"BoardID": board_id, "Channel": channel, "Interval": interval, **extra_props}

    sensor = SequentRTD(cbpi, "sensor-1", props)

    if read_values is not None:
        iterator = iter(read_values)
        monkeypatch.setattr(sensor.board, "read_temperature", lambda ch: next(iterator))

    return sensor


def run_once(monkeypatch, sensor, temp_unit="C"):
    """Run one read/publish iteration and return the published value."""
    sensor.cbpi.config.get.return_value = temp_unit
    sensor.push_update = MagicMock()
    sensor.log_data = MagicMock()

    async def stop_after_one_iteration(*args, **kwargs):
        sensor.running = False

    monkeypatch.setattr(asyncio, "sleep", stop_after_one_iteration)

    sensor.running = True
    asyncio.run(sensor.run())

    sensor.push_update.assert_called_once_with(sensor.value)
    sensor.log_data.assert_called_once_with(sensor.value)
    return sensor.value


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


class TestSequentRTDCalibration:
    def test_legacy_config_without_calibration_is_unchanged(self, monkeypatch):
        sensor = make_sensor(monkeypatch, read_values=[20.0])

        assert sensor.offset == 0.0
        assert sensor.offset_unit is None
        assert run_once(monkeypatch, sensor, "F") == 68.0

    def test_zero_offset_without_unit_is_allowed(self, monkeypatch):
        sensor = make_sensor(monkeypatch, read_values=[20.0], CalibrationOffset=0)

        assert run_once(monkeypatch, sensor, "C") == 20.0

    def test_empty_offset_field_means_zero(self, monkeypatch):
        sensor = make_sensor(monkeypatch, read_values=[20.0], CalibrationOffset="", CalibrationUnit="")

        assert run_once(monkeypatch, sensor, "C") == 20.0

    def test_positive_fahrenheit_offset_in_fahrenheit(self, monkeypatch):
        sensor = make_sensor(monkeypatch, read_values=[20.0], CalibrationOffset=1.2, CalibrationUnit="F")

        assert run_once(monkeypatch, sensor, "F") == 69.2

    def test_negative_fractional_offset(self, monkeypatch):
        sensor = make_sensor(monkeypatch, read_values=[20.0], CalibrationOffset=-0.75, CalibrationUnit="F")

        assert run_once(monkeypatch, sensor, "F") == 67.25

    def test_offset_given_as_string_from_ui(self, monkeypatch):
        sensor = make_sensor(monkeypatch, read_values=[20.0], CalibrationOffset="-0.4", CalibrationUnit="C")

        assert run_once(monkeypatch, sensor, "C") == 19.6

    def test_fahrenheit_offset_converted_for_celsius_display(self, monkeypatch):
        # 1.8 F difference == 1.0 C difference (no +32 for differences)
        sensor = make_sensor(monkeypatch, read_values=[20.0], CalibrationOffset=1.8, CalibrationUnit="F")

        assert run_once(monkeypatch, sensor, "C") == 21.0

    def test_celsius_offset_converted_for_fahrenheit_display(self, monkeypatch):
        # 0.5 C difference == 0.9 F difference
        sensor = make_sensor(monkeypatch, read_values=[20.0], CalibrationOffset=0.5, CalibrationUnit="C")

        assert run_once(monkeypatch, sensor, "F") == 68.9

    def test_offset_applied_once_per_reading(self, monkeypatch):
        sensor = make_sensor(monkeypatch, read_values=[20.0, 20.0], CalibrationOffset=1.0, CalibrationUnit="C")

        assert run_once(monkeypatch, sensor, "C") == 21.0
        assert run_once(monkeypatch, sensor, "C") == 21.0

    def test_nonzero_offset_without_unit_raises(self, monkeypatch):
        from cbpi.api import SensorException

        with pytest.raises(SensorException):
            make_sensor(monkeypatch, CalibrationOffset=1.2)

    def test_invalid_unit_raises(self, monkeypatch):
        from cbpi.api import SensorException

        with pytest.raises(SensorException):
            make_sensor(monkeypatch, CalibrationOffset=1.2, CalibrationUnit="K")

    def test_non_numeric_offset_raises(self, monkeypatch):
        from cbpi.api import SensorException

        with pytest.raises(SensorException):
            make_sensor(monkeypatch, CalibrationOffset="abc", CalibrationUnit="F")

    def test_non_finite_offset_raises(self, monkeypatch):
        from cbpi.api import SensorException

        with pytest.raises(SensorException):
            make_sensor(monkeypatch, CalibrationOffset="nan", CalibrationUnit="F")

    def test_failed_reading_is_not_published_with_offset(self, monkeypatch):
        sensor = make_sensor(monkeypatch, CalibrationOffset=5.0, CalibrationUnit="F")

        def raise_error(channel):
            sensor.running = False
            raise HardwareError("RTD board 0 channel 1 appears open or disconnected")

        monkeypatch.setattr(sensor.board, "read_temperature", raise_error)
        sensor.push_update = MagicMock()
        sensor.log_data = MagicMock()

        async def fast_sleep(*args, **kwargs):
            return None

        monkeypatch.setattr(asyncio, "sleep", fast_sleep)

        sensor.running = True
        asyncio.run(sensor.run())

        sensor.push_update.assert_not_called()
        sensor.log_data.assert_not_called()
        assert sensor.value == 0
