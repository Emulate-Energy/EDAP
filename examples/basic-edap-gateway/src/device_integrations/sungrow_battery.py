"""Sungrow Modbus Integration"""
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
device_ip = os.environ.get("DEVICE_IP", "192.168.10.24")
device_port = 502
slave_id = 1

# Addresses of the read only registers
power_address = 13033 # (w)
power_sign_address = 13034 # 0 if inverter is producing power, 65535 if consuming. 
soc_address = 13022 # x 10
pv_power_address = 5016 # (w)
battery_power_address = 13021 # (w)

# Addresses of the holding registers
EMS_mode_address = 13049 # 0: Self Consumption, 2: Control mode
chargeORdischarge_address = 13050 # 0xAA:Charge； 0xBB:Discharge; 0xCC:Stop
power_sp_address = 13051 # (w)

battery_capacity_address = 13038 # x 10 kWh
grid_frequency_Address = 5241 # x 100
BDC_rated_power_Address = 5627


class SungrowBatteryConnection(DeviceConnection):
    power: float = 0.0
    soc: float = 0.50
    power_setpoint: float = 0.0

    def __init__(self, mediator, event_loop: asyncio.AbstractEventLoop):
        super().__init__(mediator, event_loop)

    def connect(self):
        logging.debug({"message": "Connecting to battery"})

    def disconnect(self):
        logging.debug({"message": "Disconnecting from battery"})

    def send(self, data):
        logging.debug({"message": "Sending data to battery", "data": data})
        if "power" in data:
            self.write_power_setpoint(data["power"])

    def write_power_setpoint(self, power: float):
        """Write the power setpoint to the battery."""
        with ModbusTcpClient(host=device_ip, port=device_port, slave=slave_id) as client:
            client.write_register(EMS_mode_address, 2, slave_id) # change to control mode
            if power > 0:
                client.write_register(chargeORdischarge_address, 187, slave_id) # 0xBB for Discharging
            elif power < 0:
                client.write_register(chargeORdischarge_address, 170, slave_id) # 0xAA for Charging
            else:
                client.write_register(chargeORdischarge_address, 204, slave_id) # 0xCC for stop
                client.write_register(chargeORdischarge_address, 204, slave_id) # 0xCC for stop
            
            client.write_register(power_sp_address, int(abs(power)*1000), slave_id)

    def _poll(self) -> dict:

        with ModbusTcpClient(host=device_ip, port=device_port, slave=slave_id) as client:
            # Read measured power
            power_result = client.read_input_registers(power_address, 1, slave_id)
            power_sign_result = client.read_input_registers(power_sign_address, 1, slave_id)
            if power_result.isError():
                power = None
            else:
                power = (power_result.registers[0]-power_sign_result.registers[0])/1000 # convert to kW
            # Read measured soc
            soc_result = client.read_input_registers(soc_address, 1, slave_id)
            if soc_result.isError():
                soc = None
            else:
                soc = soc_result.registers[0]/1000 # convert to 0-1 range
            # Read measured freq
            freq_result = client.read_input_registers(grid_frequency_Address, 1, slave_id)
            if freq_result.isError():
                soc = None
            else:
                freq = freq_result.registers[0]/100 # convert to Hz
            

        self.power = power
        self.soc = soc
        self.freq = freq
        return {
            "power": self.power,
            "soc": self.soc,
            "freq": self.freq
        }


class SungrowEdapBattery(EdapDevice):
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
