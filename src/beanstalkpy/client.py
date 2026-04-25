import yaml
from dataclasses import dataclass
from typing import List, Optional, Union, Dict, Any

from .connection import Connection
from . import exceptions
from .protocol import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    PRIORITY_DEFAULT,
    DEFAULT_TTR,
)

@dataclass
class Job:
    id: int
    body: bytes

class Client:
    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self._conn = Connection(host, port)

    async def connect(self):
        await self._conn.connect()

    async def close(self):
        await self._conn.close()

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _request(self, command: str, body: Optional[bytes] = None) -> str:
        await self._conn.send_command(command, body)
        line = await self._conn.read_response_line()
        self._conn._handle_error(line)
        return line

    # Producer Commands

    async def put(
        self, body: bytes, priority: int = PRIORITY_DEFAULT, delay: int = 0, ttr: int = DEFAULT_TTR
    ) -> int:
        cmd = f"put {priority} {delay} {ttr} {len(body)}"
        line = await self._request(cmd, body)
        # INSERTED <id>
        parts = line.split()
        if parts[0] == "INSERTED":
            return int(parts[1])
        elif parts[0] == "BURIED":
            return int(parts[1])
        raise exceptions.ProtocolError(f"Unexpected response to put: {line}")

    async def use(self, tube: str) -> str:
        line = await self._request(f"use {tube}")
        # USING <tube>
        parts = line.split()
        if parts[0] == "USING":
            return parts[1]
        raise exceptions.ProtocolError(f"Unexpected response to use: {line}")

    # Worker Commands

    async def reserve(self, timeout: Optional[int] = None) -> Job:
        if timeout is not None:
            cmd = f"reserve-with-timeout {timeout}"
        else:
            cmd = "reserve"
        
        line = await self._request(cmd)
        # RESERVED <id> <bytes>
        parts = line.split()
        if parts[0] == "RESERVED":
            job_id = int(parts[1])
            size = int(parts[2])
            body = await self._conn.read_data(size)
            return Job(id=job_id, body=body)
        raise exceptions.ProtocolError(f"Unexpected response to reserve: {line}")

    async def reserve_job(self, job_id: int) -> Job:
        line = await self._request(f"reserve-job {job_id}")
        # RESERVED <id> <bytes>
        parts = line.split()
        if parts[0] == "RESERVED":
            job_id = int(parts[1])
            size = int(parts[2])
            body = await self._conn.read_data(size)
            return Job(id=job_id, body=body)
        raise exceptions.ProtocolError(f"Unexpected response to reserve-job: {line}")

    async def delete(self, job_id: int):
        line = await self._request(f"delete {job_id}")
        if line != "DELETED":
            raise exceptions.ProtocolError(f"Unexpected response to delete: {line}")

    async def release(self, job_id: int, priority: int = PRIORITY_DEFAULT, delay: int = 0):
        line = await self._request(f"release {job_id} {priority} {delay}")
        if line == "RELEASED":
            return
        elif line == "BURIED":
            raise exceptions.OutOfMemoryError("Server ran out of memory while releasing job")
        raise exceptions.ProtocolError(f"Unexpected response to release: {line}")

    async def bury(self, job_id: int, priority: int = PRIORITY_DEFAULT):
        line = await self._request(f"bury {job_id} {priority}")
        if line != "BURIED":
            raise exceptions.ProtocolError(f"Unexpected response to bury: {line}")

    async def touch(self, job_id: int):
        line = await self._request(f"touch {job_id}")
        if line != "TOUCHED":
            raise exceptions.ProtocolError(f"Unexpected response to touch: {line}")

    async def watch(self, tube: str) -> int:
        line = await self._request(f"watch {tube}")
        # WATCHING <count>
        parts = line.split()
        if parts[0] == "WATCHING":
            return int(parts[1])
        raise exceptions.ProtocolError(f"Unexpected response to watch: {line}")

    async def ignore(self, tube: str) -> int:
        line = await self._request(f"ignore {tube}")
        # WATCHING <count>
        parts = line.split()
        if parts[0] == "WATCHING":
            return int(parts[1])
        raise exceptions.ProtocolError(f"Unexpected response to ignore: {line}")

    # Other Commands

    async def peek(self, job_id: int) -> Job:
        return await self._peek_cmd(f"peek {job_id}")

    async def peek_ready(self) -> Job:
        return await self._peek_cmd("peek-ready")

    async def peek_delayed(self) -> Job:
        return await self._peek_cmd("peek-delayed")

    async def peek_buried(self) -> Job:
        return await self._peek_cmd("peek-buried")

    async def _peek_cmd(self, cmd: str) -> Job:
        line = await self._request(cmd)
        # FOUND <id> <bytes>
        parts = line.split()
        if parts[0] == "FOUND":
            job_id = int(parts[1])
            size = int(parts[2])
            body = await self._conn.read_data(size)
            return Job(id=job_id, body=body)
        raise exceptions.ProtocolError(f"Unexpected response to peek: {line}")

    async def kick(self, bound: int) -> int:
        line = await self._request(f"kick {bound}")
        # KICKED <count>
        parts = line.split()
        if parts[0] == "KICKED":
            return int(parts[1])
        raise exceptions.ProtocolError(f"Unexpected response to kick: {line}")

    async def kick_job(self, job_id: int):
        line = await self._request(f"kick-job {job_id}")
        if line != "KICKED":
            raise exceptions.ProtocolError(f"Unexpected response to kick-job: {line}")

    async def stats_job(self, job_id: int) -> Dict[str, Any]:
        return await self._stats_cmd(f"stats-job {job_id}")

    async def stats_tube(self, tube: str) -> Dict[str, Any]:
        return await self._stats_cmd(f"stats-tube {tube}")

    async def stats(self) -> Dict[str, Any]:
        return await self._stats_cmd("stats")

    async def _stats_cmd(self, cmd: str) -> Dict[str, Any]:
        line = await self._request(cmd)
        # OK <bytes>
        parts = line.split()
        if parts[0] == "OK":
            size = int(parts[1])
            data = await self._conn.read_data(size)
            return yaml.safe_load(data)
        raise exceptions.ProtocolError(f"Unexpected response to stats: {line}")

    async def list_tubes(self) -> List[str]:
        line = await self._request("list-tubes")
        # OK <bytes>
        parts = line.split()
        if parts[0] == "OK":
            size = int(parts[1])
            data = await self._conn.read_data(size)
            return yaml.safe_load(data)
        raise exceptions.ProtocolError(f"Unexpected response to list-tubes: {line}")

    async def list_tube_used(self) -> str:
        line = await self._request("list-tube-used")
        # USING <tube>
        parts = line.split()
        if parts[0] == "USING":
            return parts[1]
        raise exceptions.ProtocolError(f"Unexpected response to list-tube-used: {line}")

    async def list_tubes_watched(self) -> List[str]:
        line = await self._request("list-tubes-watched")
        # OK <bytes>
        parts = line.split()
        if parts[0] == "OK":
            size = int(parts[1])
            data = await self._conn.read_data(size)
            return yaml.safe_load(data)
        raise exceptions.ProtocolError(f"Unexpected response to list-tubes-watched: {line}")

    async def pause_tube(self, tube: str, delay: int):
        line = await self._request(f"pause-tube {tube} {delay}")
        if line != "PAUSED":
            raise exceptions.ProtocolError(f"Unexpected response to pause-tube: {line}")

    async def quit(self):
        await self._conn.send_command("quit")
        await self.close()
