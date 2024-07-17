import asyncio
import logging


SAMPLE_RATE = 5  # seconds

def read_modbus_values() -> tuple:
    """Fill in code to read the Modbus values from the device here."""
    return (0, 0)

def publish_values_to_mqtt(values: tuple):
    """Fill in code to publish the values to MQTT here."""
    pass

async def mqtt_publish_loop():
    logging.info("Starting MQTT publish loop")

    while True:
        values = read_modbus_values()
        publish_values_to_mqtt(values)
        logging.info({
            "message": "Published values to MQTT",
            "values": values
        })
        await asyncio.sleep(SAMPLE_RATE)
