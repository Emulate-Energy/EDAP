import os
import asyncio
from edap import EdapDevice, EdapSample, Trigger

from src.DeviceConnection import DeviceConnection
from src.device_integrations.pixii_battery import PixiiEdapBattery, PixiiBatteryConnection
from src.device_integrations.freq_meter import FrequencyMeterEdap, FrequencyMeterConnection
from src.dummy.DummyEdapBattery import DummyEdapBattery
from src.dummy.DummyDeviceConnection import DummyDeviceConnection


def get_edap_device(mediator, event_loop: asyncio.AbstractEventLoop) -> tuple[DeviceConnection, EdapDevice]:
    """Return an EDAP device instance, based on the environment variable."""
    device_model = os.environ.get("DEVICE_MODEL", "dummy")

    if device_model == "pixii_battery":
        return (
            PixiiBatteryConnection(mediator, event_loop),
            PixiiEdapBattery(mediator))
    if device_model == "frequency_meter":
        return (
            FrequencyMeterConnection(mediator, event_loop),
            FrequencyMeterEdap(mediator))
    if device_model == "dummy":
        return (
            DummyDeviceConnection(mediator, event_loop),
            DummyEdapBattery(mediator))

    raise ValueError(f"Unknown device model: {device_model}")


# we could add scanning logic here for automatically detecting the
# connected device. This would ultimately be ideal, probably?

# other way to do this would be by allowing the user to specify the
# device model, and then send it from the proxy to the gateway over WS as
# a command.