import asyncio
from typing import Optional, List
from .client import Client
from .protocol import DEFAULT_HOST, DEFAULT_PORT

class Pool:
    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        minsize: int = 1,
        maxsize: int = 10,
    ):
        self.host = host
        self.port = port
        self.minsize = minsize
        self.maxsize = maxsize
        self._pool: asyncio.Queue[Client] = asyncio.Queue(maxsize)
        self._all_clients: List[Client] = []
        self._count = 0
        self._lock = asyncio.Lock()

    async def _create_client(self) -> Client:
        client = Client(self.host, self.port)
        await client.connect()
        self._all_clients.append(client)
        self._count += 1
        return client

    async def acquire(self) -> Client:
        async with self._lock:
            if self._pool.empty() and self._count < self.maxsize:
                return await self._create_client()
        
        return await self._pool.get()

    async def release(self, client: Client):
        await self._pool.put(client)

    async def close(self):
        for client in self._all_clients:
            await client.close()
        self._all_clients = []
        self._count = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
