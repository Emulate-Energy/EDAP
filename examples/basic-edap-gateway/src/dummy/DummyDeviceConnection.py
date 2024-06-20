"""Dummy backend device connection class, producing dummy data."""
import os
import asyncio
import logging
from random import random

from src.DeviceConnection import DeviceConnection


class DummyDeviceConnection(DeviceConnection):
    """Dummy device connection class that simulates a device connection."""

    power: float = 0.0
    soc: float = 0.50
    random_data: bool

    def __init__(self, mediator, event_loop: asyncio.AbstractEventLoop):
        super().__init__(mediator, event_loop)
        random_data = os.environ.get("RANDOM_DUMMY_DATA", 'false')
        self.random_data = random_data.lower() == 'true'

    def connect(self):
        logging.debug({"message": "Connecting to dummy device"})

    def disconnect(self):
        logging.debug({"message": "Disconnecting from dummy device"})

    def send(self, data):
        logging.debug({"message": "Sending data to dummy device", "data": data})
        if "power" in data:
            self.power = data["power"]

    def _poll(self) -> dict:
        if self.random_data:
            self.power = random() * 100
            self.soc = random()
        return {
            "power": self.power,
            "soc": self.soc
        }
