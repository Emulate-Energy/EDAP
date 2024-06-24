"""Central component that mediates between the device and the proxy."""
import asyncio
from typing import Any, Literal
import logging
from datetime import datetime, timezone

from src.ConnectionManager import ConnectionManager
from src.DeviceConnection import DeviceConnection
from src.dummy.DummyDeviceConnection import DummyDeviceConnection
from src.dummy.DummyEdapBattery import DummyEdapBattery

EventType = Literal["sample_received", "trigger_activated", "command_received"]
CommandType = Literal["set", "set_triggers", "ping"]

class Mediator:
    """Class that acts as a mediator between the device and the proxy."""
    _event_loop: asyncio.AbstractEventLoop
    connection_manager: ConnectionManager
    device_connection: DeviceConnection
    device: DummyEdapBattery

    def __init__(self, event_loop: asyncio.AbstractEventLoop):
        self._event_loop = event_loop
        self.connection_manager = ConnectionManager(self)
        self.device_connection = DummyDeviceConnection(self, event_loop)
        self.device = DummyEdapBattery(self)

    def notify(self, event: EventType, data: Any = None):
        """React to different kinds of events, triggered by one of the components."""
        self._event_loop.create_task(self.__inner_notify(event, data))

    async def __inner_notify(self, event: EventType, data: Any):
        match event:
            case "trigger_activated":
                await self.connection_manager.send_to_proxy(data)
                logging.debug({"message": "Trigger activated", "trigger": data})
            case "command_received":
                self.handle_commands(data)
            case "sample_received":
                self.device.update_from_sample(data)
            case _:
                logging.error({"message": "Unknown event", "event": event})
                return False
        return True

    def handle_commands(self, command: dict):
        """React to incoming command from the proxy."""
        command_time: datetime = None
        if "time" in command:
            # no need to account for timestamps that end with Z since python 3.11
            command_time = datetime.fromisoformat(command["time"])
            del command["time"]
        else:
            command_time = datetime.now(tz=timezone.utc)

        for command_name, command_data in command.items():
            match command_name:
                case "set":
                    try:
                        self.device_connection.send(command_data)
                        result = {"result": "success"}
                    except Exception as ex:
                        result = {"result": "error", "error": repr(ex)}
                case "set_triggers":
                    try:
                        self.device.set_triggers(command_data)
                        result = {"result": "success"}
                    except Exception as ex:
                        result = {"result": "error", "error": repr(ex)}
                case "ping":
                    result = {"result": "pong"}
                case _:
                    logging.error({"message": "Unknown command", "command": command_name})
                    return
            self._event_loop.create_task(
                self.send_command_response(command_name, command_time, result))

    async def send_command_response(self, command_name: str, command_time: datetime, result: dict):
        """Constructs and sends a response to a command."""
        if not result:
            return
        now = datetime.now(tz=timezone.utc)
        duration_ms = round((now - command_time).total_seconds() * 1000, 4)
        command_response = {
            "command": command_name,
            "duration": duration_ms,
            "time": command_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            "result": result,
        }
        await self.connection_manager.send_to_proxy(command_response)

    def start(self):
        """Start the different components of the mediator."""
        logging.info("Starting the Edap gateway...")
        self.connection_manager.start()
        self.device_connection.start()

    async def stop(self):
        """Stop the different components of the mediator."""
        logging.info("Shutting down the Edap gateway...")
        await self.connection_manager.stop()
        self.device_connection.stop()
