"""Dummy backend device connection class, producing dummy data."""
import os
import asyncio
import logging
from random import random
from datetime import datetime, timezone
from pymodbus.client import ModbusTcpClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
from edap import EdapDevice, EdapSample, Trigger

from src.DeviceConnection import DeviceConnection
import subprocess
import re

def get_device_ip(interface='eth0'):
    try:
        # Run the arp-scan command
        result = subprocess.run(['sudo', 'arp-scan', '--interface', interface, '--localnet'],
                                capture_output=True, text=True, check=True)
        # Get the output
        output = result.stdout
        output_lines = output.split('\n') # split into rows
        scan_result_lines = output_lines[2:-4] # might be slightly wrong, try it
        results = [line.split() for line in scan_result_lines]
        ips = [r[0] for r in results]
        mac_addressess = [r[1] for r in results]
        companies = [r[2] for r in results]
        # Extract IP addresses using regex
        return ips, mac_addressess, companies
    except subprocess.CalledProcessError as e:
        print(f"Error occurred: {e}")
        return []

# IP address and port of the Modbus TCP device
DEVICE_IP = get_device_ip('eth0')[0][0]
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


class FrequencyMeterEdap(EdapDevice):
    """Dummy implementation of a pixii battery device"""
    frequency: float = 50.0
    last_sample_time: datetime # when the last device sample received
    last_triggered: datetime  # when the last trigger was activated

    def __init__(self, mediator):
        self.mediator = mediator
        self.last_sample_time = None
        self.last_triggered = None

        # add a default time trigger just for testing
        default_time_trigger: Trigger = Trigger(
            id="time",
            property="time",
            delta=10
        )
        super().__init__([default_time_trigger])

    def update_from_sample(self, data: dict):
        """Update the device state from a polling sample, and check if any triggers are activated,
        notifying the mediator if so."""
        logging.debug({"message": "Updating device from sample", "data": data})
        self.frequency = data["frequency"]

        now = datetime.now(tz=timezone.utc)
        self.last_sample_time = now

        sample = EdapSample(
            time = now,
            power = 0,
            energy = 0,
            sensors = {"frequency": self.frequency},
        )

        maybe_sample = self.trigger(sample)
        if maybe_sample is not None:
            self.last_triggered = now
            self.mediator.notify("trigger_activated", maybe_sample)

    def generate_sample(self, sample: EdapSample) -> dict:
        sample["duration"] = (sample["time"] - self._last_sample["time"]).total_seconds()
        sample["sample_energy"] = sample["energy"] - self._last_sample["energy"]
        sample["triggers"] = []
        return sample
