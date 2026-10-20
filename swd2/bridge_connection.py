"""The client's connection to the bridge"""
import asyncio
import json
import logging

from .bridge_protocol import PORT

logger = logging.getLogger("Client")

RETRY_SECONDS = 2
MAX_LINE = 1 << 22  # the longest message the client reads, in bytes (4 MiB)


class BridgeConnection:
    def __init__(self, on_message, on_disconnect):
        self.on_message = on_message  # awaited with each message (a dict) the bridge sends
        self.on_disconnect = on_disconnect  # called when the game closes the connection
        self.writer: asyncio.StreamWriter | None = None

    @property
    def connected(self) -> bool:
        return self.writer is not None

    def send(self, message: dict) -> None:
        if self.writer:
            self.writer.write(json.dumps(message).encode() + b"\n")

    async def run(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            try:
                reader, self.writer = await asyncio.open_connection("127.0.0.1", PORT, limit=MAX_LINE)
            except OSError:
                await asyncio.sleep(RETRY_SECONDS)
                continue

            try:
                while line := await reader.readline():
                    if line.strip():
                        await self.on_message(json.loads(line))
            except OSError as error:
                logger.debug(f"bridge connection lost: {error}")
            except Exception:
                # A message the client couldn't handle
                logger.exception("bridge message failed, reconnecting")
            finally:
                self.writer.close()
                self.writer = None
                self.on_disconnect()

            # Wait before trying again, so a bridge that turns the client away isn't asked again at once
            await asyncio.sleep(RETRY_SECONDS)
