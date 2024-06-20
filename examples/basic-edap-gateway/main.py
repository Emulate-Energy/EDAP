"""Entrypoint of the application."""
import asyncio
import logging
import sys
import os
from src.utils import CustomJsonFormatter
from src.Mediator import Mediator

def main(event_loop: asyncio.AbstractEventLoop):
    """Runs the gateway application."""
    mediator = Mediator(event_loop)
    try:
        mediator.start()
        event_loop.run_forever()
    except KeyboardInterrupt:
        ...
    finally:
        event_loop.run_until_complete(mediator.stop())

def setup_logging():
    """Sets up the logging configuration."""
    logging.basicConfig(stream=sys.stdout, level=os.environ.get('LOG_LEVEL', 'INFO').upper())
    logger = logging.getLogger()
    logger.handlers.clear()
    log_handler = logging.StreamHandler()
    formatter = CustomJsonFormatter(service_name='edap-gateway')
    log_handler.setFormatter(formatter)
    logger.addHandler(log_handler)

if __name__ == '__main__':
    setup_logging()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    main(loop)
