"""Test fixtures.

The real ``cbpi4`` package pulls in heavyweight, Raspberry-Pi/Linux-specific
dependencies (systemd-python, aiohttp stack, etc.) that aren't needed to
unit-test this plugin's own logic. Instead we install a minimal stub of the
``cbpi.api`` surface this plugin actually uses, so tests can run anywhere.
"""

import sys
import types


def _install_cbpi_stub():
    if "cbpi.api" in sys.modules:
        return

    cbpi_pkg = types.ModuleType("cbpi")
    cbpi_api = types.ModuleType("cbpi.api")

    class CBPiException(Exception):
        pass

    class SensorException(CBPiException):
        pass

    class ActorException(CBPiException):
        pass

    class PropertyType:
        pass

    class _Select(PropertyType):
        def __init__(self, label, options, default_value=None, description=""):
            self.label = label
            self.options = options
            self.default_value = default_value
            self.description = description

    class _Number(PropertyType):
        def __init__(self, label, configurable=False, default_value=None, unit="", description=""):
            self.label = label
            self.configurable = configurable
            self.default_value = default_value
            self.description = description

    class Property:
        Select = _Select
        Number = _Number

    def parameters(param_list):
        def decorator(cls):
            cls.cbpi_p = True
            cls.cbpi_parameters = param_list
            return cls

        return decorator

    class CBPiSensor:
        def __init__(self, cbpi, id, props):
            self.cbpi = cbpi
            self.id = id
            self.props = props
            self.running = False
            self.state = False

        def push_update(self, value, mqtt=True):
            pass

        def log_data(self, value):
            pass

        def get_config_value(self, name, default):
            return self.cbpi.config.get(name, default=default)

        def get_state(self):
            pass

    class CBPiActor:
        def __init__(self, cbpi, id, props):
            self.cbpi = cbpi
            self.id = id
            self.props = props
            self.state = False
            self.power = 100

        async def on_start(self):
            pass

        async def on(self, power=None):
            pass

        async def off(self):
            pass

        def get_state(self):
            return dict(state=self.state)

    cbpi_api.CBPiSensor = CBPiSensor
    cbpi_api.CBPiActor = CBPiActor
    cbpi_api.Property = Property
    cbpi_api.parameters = parameters
    cbpi_api.SensorException = SensorException
    cbpi_api.ActorException = ActorException
    cbpi_api.CBPiException = CBPiException

    cbpi_pkg.api = cbpi_api

    sys.modules["cbpi"] = cbpi_pkg
    sys.modules["cbpi.api"] = cbpi_api


_install_cbpi_stub()
