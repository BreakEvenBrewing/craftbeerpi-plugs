from .actor import SequentRelay
from .sensor import SequentRTD

__version__ = "0.1.0"


def setup(cbpi):
    """Called by CraftBeerPi during startup to register plugin components."""
    cbpi.plugin.register("SequentRTD", SequentRTD)
    cbpi.plugin.register("SequentRelay", SequentRelay)
