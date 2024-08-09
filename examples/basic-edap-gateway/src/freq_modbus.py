import asyncio
from pymodbus.client import ModbusTcpClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder

import logging

SAMPLE_RATE = 5  # seconds

# IP address and port of the Modbus TCP device
DEVICE_IP = '192.168.10.20'  # Replace with the actual IP address
DEVICE_PORT = 502

# Addresses of the registers
REGISTER_FREQ_ADDRESS = 0x0001
REGISTER_STATE_ADDRESS = 0x0002

# Number of registers to read
NUM_REGISTERS = 1

def read_registers():
    """Function to read holding registers from the Modbus TCP device (frequency and state)."""
    with ModbusTcpClient(DEVICE_IP, port=DEVICE_PORT) as client:
        # Read measured frequency (address 0x0001)
        freq_result = client.read_holding_registers(REGISTER_FREQ_ADDRESS, NUM_REGISTERS, unit=1)
        if freq_result.isError():
            freq_result = None
        else:
            freq_value = freq_result.registers[0]/1000

        # Read state of the device (address 0x0002)
        state_result = client.read_holding_registers(REGISTER_STATE_ADDRESS, NUM_REGISTERS, unit=1)
        if state_result.isError():
            print("Error reading state:", state_result)
            state_result = None
        else:
            state_value = state_result.registers[0]

        return freq_value, state_value

async def read_frequency_loop():
    logging.info("Starting frequency reading loop")
    while True:
        freq, state = read_registers()
        logging.info({
            "message": "Logging frequency...",
            "frequency": freq,
            "device_state": state
        })
        await asyncio.sleep(SAMPLE_RATE)

if __name__ == '__main__':
    read_registers()
