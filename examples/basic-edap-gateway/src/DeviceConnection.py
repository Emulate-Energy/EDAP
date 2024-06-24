"""Abstract class that is responsible for managing the connection to the device/backend."""
import os
import asyncio
import logging
from contextlib import suppress
from typing import Optional
from datetime import timedelta
from abc import ABC, abstractmethod

DEFAULT_POLLING_INTERVAL = timedelta(seconds=1)

class DeviceConnection(ABC):
    """Class that is responsible for managing the connection to the device.
    This involves sampling the device at regular intervals and passing the data onto the mediator,
    and also handling incoming commands (like setting power) to the device.
    Implementation will differ depending on specific hardware."""
    def __init__(self, mediator, event_loop: asyncio.AbstractEventLoop):
        self.mediator = mediator
        self._event_loop = event_loop

        polling_interval_s = int(os.environ.get('DEVICE_POLLING_INTERVAL',
                                 DEFAULT_POLLING_INTERVAL.total_seconds()))
        self.polling_interval = timedelta(seconds=polling_interval_s)

        self._polling_loop_task: Optional[asyncio.Task] = None

    @abstractmethod
    def connect(self):
        """Should handle connect to the device backend, if needed. Could be used for things like
        opening a socket connection or setting up an authenticated session etc."""

    @abstractmethod
    def disconnect(self):
        """Should handle disconnecting from the device backend, if needed."""

    @abstractmethod
    def send(self, data: dict):
        """Should handle passing commands to the device."""

    @abstractmethod
    def _poll(self) -> dict:
        return {}

    def start(self):
        """Connect if needed, and start the polling loop."""
        self.connect()
        logging.info({
            "message": "Starting device polling loop",
            "polling_interval": self.polling_interval.total_seconds()
        })
        self._polling_loop_task = self._event_loop.create_task(self._polling_loop())

    async def _polling_loop(self):
        # The following generator keeps a counter tracking when the next tick
        # should happen, and yields the number of seconds we need to sleep to
        # reach it. It should account for drift.
        def g_tick():
            next_tick_time = self._event_loop.time()
            while True:
                next_tick_time += self.polling_interval.total_seconds()
                yield max(next_tick_time - self._event_loop.time(), 0)

        g = g_tick()
        with suppress(asyncio.CancelledError):
            while True:
                data = self._poll()
                self.mediator.notify("sample_received", data)
                await asyncio.sleep(next(g))


    def stop(self):
        """Disconnect if needed, and stop the polling loop."""
        self.disconnect()
        if self._polling_loop_task:
            self._polling_loop_task.cancel()
