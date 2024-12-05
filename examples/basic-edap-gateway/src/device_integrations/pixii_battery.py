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
# IP address and port of the Modbus TCP device
DEVICE_IP = os.environ.get("DEVICE_IP", "192.168.10.20")
DEVICE_PORT = 502

# Addresses of the registers
REGISTER_POWER_ADDRESS = 0x0001
REGISTER_SOC_ADDRESS = 0x0002
REGISTER_POWER_SP_ADDRESS = 0x0002

# Number of registers to read
NUM_REGISTERS = 1


class PixiiBatteryConnection(DeviceConnection):
    """Read and write values from a Pixii battery (dummy code for now)."""
    power: float = 0.0
    soc: float = 0.50
    power_setpoint: float = 0.0

    def __init__(self, mediator, event_loop: asyncio.AbstractEventLoop):
        super().__init__(mediator, event_loop)
        logging.info({
            "message": "Pixii Battery Connection initialized",
            "device_ip": DEVICE_IP,
            "device_port": DEVICE_PORT})


    def connect(self):
        logging.debug({"message": "Connecting to pixii batter"})

    def disconnect(self):
        logging.debug({"message": "Disconnecting from pixii battery"})

    def send(self, data):
        logging.debug({"message": "Sending data to battery", "data": data})
        if "power" in data:
            self.write_power_setpoint(data["power"])

    def write_power_setpoint(self, power: float):
        """Write the power setpoint to the battery."""
        with ModbusTcpClient(DEVICE_IP, port=DEVICE_PORT) as client:
            # This might not be correct at all?
            client.write_register(REGISTER_POWER_SP_ADDRESS, int(power*1000), unit=1)

    def _poll(self) -> dict:

        with ModbusTcpClient(DEVICE_IP, port=DEVICE_PORT) as client:
            # Read measured power (address 0x0001)
            power_result = client.read_holding_registers(REGISTER_POWER_ADDRESS, NUM_REGISTERS, unit=1)
            if power_result.isError():
                power = None
            else:
                power = power_result.registers[0]/1000 # not sure about units of course

            soc_result = client.read_holding_registers(REGISTER_SOC_ADDRESS, NUM_REGISTERS, unit=1)
            if power_result.isError():
                soc = None
            else:
                soc = power_result.registers[0]/100

        self.power = power
        self.soc = soc
        return {
            "power": self.power,
            "soc": self.soc
        }


class PixiiEdapBattery(EdapDevice):
    """Dummy implementation of a pixii battery device"""
    power_kw: float = 0.0
    soc: float = 0.50
    energy_capacity = 100.0 # kWh
    energy: float = 0.0
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
        self.power_kw = data["power"]
        self.soc = data["soc"]

        now = datetime.now(tz=timezone.utc)
        if self.last_sample_time:
            since_last_sample = now - self.last_sample_time
            self.energy += self.power_kw * since_last_sample.total_seconds() / 3600

        self.last_sample_time = now

        sample = EdapSample(
            time = now,
            power = self.power_kw,
            energy = self.energy,
            sensors = {"soc": self.soc, "remaining_energy": self.soc * self.energy_capacity},
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
