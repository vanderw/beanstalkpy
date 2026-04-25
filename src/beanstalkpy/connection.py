import asyncio
from typing import Optional, Tuple
from . import exceptions
from .protocol import CRLF

class Connection:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None

    async def connect(self):
        try:
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        except Exception as e:
            raise exceptions.ConnectionError(f"Failed to connect to {self.host}:{self.port}") from e

    async def close(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        self.reader = None
        self.writer = None

    async def send_command(self, command: str, body: Optional[bytes] = None):
        if not self.writer:
            await self.connect()
        
        line = command.encode("ascii") + CRLF
        self.writer.write(line)
        if body is not None:
            self.writer.write(body + CRLF)
        await self.writer.drain()

    async def read_response_line(self) -> str:
        if not self.reader:
            raise exceptions.ConnectionError("Not connected")
        
        line = await self.reader.readuntil(CRLF)
        return line[:-2].decode("ascii")

    async def read_data(self, size: int) -> bytes:
        if not self.reader:
            raise exceptions.ConnectionError("Not connected")
        
        data = await self.reader.readexactly(size)
        await self.reader.readexactly(2)  # Read trailing CRLF
        return data

    def _handle_error(self, line: str):
        if line == "OUT_OF_MEMORY":
            raise exceptions.OutOfMemoryError()
        elif line == "INTERNAL_ERROR":
            raise exceptions.InternalError()
        elif line == "BAD_FORMAT":
            raise exceptions.BadFormatError()
        elif line == "UNKNOWN_COMMAND":
            raise exceptions.UnknownCommandError()
        elif line == "EXPECTED_CRLF":
            raise exceptions.ExpectedCRLFError()
        elif line == "JOB_TOO_BIG":
            raise exceptions.JobTooBigError()
        elif line == "DRAINING":
            raise exceptions.DrainingError()
        elif line == "NOT_FOUND":
            raise exceptions.NotFoundError()
        elif line == "NOT_IGNORED":
            raise exceptions.NotIgnoredError()
        elif line == "TIMED_OUT":
            raise exceptions.TimedOutError()
        elif line == "DEADLINE_SOON":
            raise exceptions.DeadlineSoonError()
        # Other errors can be added here
