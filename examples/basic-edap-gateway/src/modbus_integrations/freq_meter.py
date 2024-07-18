"""Dummy backend device connection class, producing dummy data."""
import os
import asyncio
import logging
from random import random
from pymodbus.client import ModbusTcpClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder

from src.DeviceConnection import DeviceConnection
# IP address and port of the Modbus TCP device
DEVICE_IP = '192.168.10.20'  # Replace with the actual IP address
DEVICE_PORT = 502

# Addresses of the registers
REGISTER_FREQ_ADDRESS = 0x0001
REGISTER_STATE_ADDRESS = 0x0002

# Number of registers to read
NUM_REGISTERS = 1


class FrequencyMeterConnection(DeviceConnection):
    """Dummy device connection class that simulates a device connection."""

    frequency: float = 50.0

    def __init__(self, mediator, event_loop: asyncio.AbstractEventLoop):
        super().__init__(mediator, event_loop)

    def connect(self):
        logging.debug({"message": "Connecting to frequency meter"})

    def disconnect(self):
        logging.debug({"message": "Disconnecting from frequency meter"})

    def send(self, data):
        logging.debug({"message": "Sending data to frequency meter", "data": data})

    def _poll(self) -> dict:

        with ModbusTcpClient(DEVICE_IP, port=DEVICE_PORT) as client:
            # Read measured frequency (address 0x0001)
            freq_result = client.read_holding_registers(REGISTER_FREQ_ADDRESS, NUM_REGISTERS, unit=1)
            if freq_result.isError():
                freq_value = None
            else:
                freq_value = freq_result.registers[0]/1000

        self.frequency = freq_value
        return {
            "frequency": self.frequency,
        }
