"""Handles the WebSocket connection to the Emulate Commander proxy."""
from typing import Optional
import asyncio
import logging
import json
import os
import traceback
from contextlib import suppress
import websockets.client as ws_client
import websockets.exceptions as ws_exceptions

from src.utils import json_serialize

class ConnectionManager:
    """Handles the WebSocket connection to the Emulate Commander proxy."""
    def __init__(self, mediator: Optional[None] = None) -> None:
        self.__proxy_connection: Optional[ws_client.WebSocketClientProtocol] = None

        self.__commander_proxy_base_url: Optional[str] = os.environ.get('COMMANDER_PROXY_BASE_URL')
        self.__device_id: Optional[str] = os.environ.get('DEVICE_ID')

        self.__connect_task: Optional[asyncio.Task] = None
        self.__poll_task: Optional[asyncio.Task] = None
        self.__close_proxy_connection_task: Optional[asyncio.Task] = None

        self.mediator = mediator

    async def __connect(self, retry_interval: int = 20):
        if self.is_connected():
            return
        url = f'{self.__commander_proxy_base_url}{self.__device_id}'
        while True:
            try:
                self.__proxy_connection = await ws_client.connect(uri=url, ping_interval=15)
                logging.info({"message": "Connected to proxy",
                              "url": url})
                return
            except (ws_exceptions.WebSocketException, OSError) as ex:
                logging.warning({"message": "Could not connect to proxy",
                                 "retry_interval": retry_interval,
                                 "url": url,
                                 "error": repr(ex),
                                 "traceback": traceback.format_exc()})
                await asyncio.sleep(retry_interval)

    async def __poll_proxy_connection(self):
        if not self.is_connected():
            logging.warning({"message": "Not connected, polling won't start"})
            return
        try:
            logging.info({"message": "Started to poll for proxy messages"})
            while True:
                received = await self.__proxy_connection.recv()
                try:
                    message = json.loads(received)
                    if self.mediator:
                        try:
                            await self.mediator.notify("command_received", message)
                        except Exception as ex:
                            logging.error({"message": "Error occurred while handling command",
                                           "error": repr(ex),
                                           "traceback": traceback.format_exc()})
                except json.JSONDecodeError as ex:
                    logging.error({"message": "Error occurred while decoding message",
                                   "received": received,
                                   "error": repr(ex),
                                   "traceback": traceback.format_exc()})
        except (ws_exceptions.ConnectionClosed,
                ws_exceptions.ConnectionClosedError) as ex:
            logging.warning({"message": "Connection to proxy closed",
                             "error": repr(ex),
                             "traceback": traceback.format_exc()})

    def __poll_task_done(self, _: asyncio.Task):
        logging.info({"message": "Poll task done"})
        self.__poll_task = None
        self.__close_proxy_connection_task = asyncio.get_event_loop().create_task(
            self.__close_proxy_connection())
        self.__close_proxy_connection_task.add_done_callback(
            self.__close_proxy_connection_task_done)

    async def send_to_proxy(self, payload: dict):
        """Sends a JSON payload to the proxy."""
        try:
            if self.is_connected():
                await self.__proxy_connection.send(json.dumps(payload, default=json_serialize))
                logging.debug({"message": "Payload to proxy sent",
                              "payload": payload})
            else:
                logging.warning({"message": "Could not send, not connected to proxy"})
        except ws_exceptions.WebSocketException as ex:
            logging.warning({"message": "Could not send payload",
                            "payload": payload,
                            "error": repr(ex),
                            "traceback": traceback.format_exc()})

    async def __close_proxy_connection(self):
        if self.__proxy_connection is not None and not self.__proxy_connection.closed:
            await self.__proxy_connection.close()
        logging.info({"message": "Proxy connection closed"})

    def __close_proxy_connection_task_done(self, _: asyncio.Task):
        self.__close_proxy_connection_task = None
        self.start()

    def is_connected(self) -> bool:
        """If the proxy connection is open."""
        return self.__proxy_connection is not None and self.__proxy_connection.open

    def __start_poll(self, _: asyncio.Task):
        self.__connect_task = None
        if self.__poll_task is not None:
            return
        self.__poll_task = asyncio.get_event_loop().create_task(self.__poll_proxy_connection())
        self.__poll_task.add_done_callback(self.__poll_task_done)

    def start(self):
        """Start polling for messages from the proxy."""
        if self.__connect_task is not None:
            return
        self.__connect_task = asyncio.get_event_loop().create_task(self.__connect())
        self.__connect_task.add_done_callback(self.__start_poll)

    async def stop(self):
        """Stop polling and disconnect from the proxy."""
        tasks = [self.__connect_task, self.__poll_task, self.__close_proxy_connection_task]
        for task in tasks:
            if task is not None and not task.done() and not task.cancelled():
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
        if self.is_connected():
            await self.__proxy_connection.close()
