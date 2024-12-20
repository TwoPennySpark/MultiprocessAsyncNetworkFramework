from __future__ import annotations
from typing import Protocol, Coroutine
from contextlib import suppress

import asyncio

from netframe.message import Message, OwnedMessage


class ConnOwner(Protocol):
    def process_msg(self, msg: OwnedMessage):
        pass

    def process_disconnect(self, conn: Connection):
        pass


class Connection:
    def __init__(self,
                 reader: asyncio.StreamReader, 
                 writer: asyncio.StreamWriter, 
                 owner: ConnOwner):
        self._reader = reader
        self._writer = writer
        self._owner = owner
        
        self._tasks: set[asyncio.Task] = set()
        self._isActive = True


    async def _recv(self):
        msg = OwnedMessage(owner=self)

        try:
            hdrBytes = await self._reader.readexactly(Message.Header.HEADER_LEN)
            msg.msg.hdr.unpack(hdrBytes)

            msg.msg.payload = await self._reader.readexactly(msg.msg.hdr.size)            
        except asyncio.CancelledError:
            return
        except (asyncio.IncompleteReadError, ConnectionResetError, ConnectionAbortedError):
            await self._shutdown()
            self._owner.process_disconnect(self)
            return

        self.recv()
        self._owner.process_msg(msg)

    
    async def _send(self, msg: Message):
        try:
            self._writer.write(msg.pack())
            await self._writer.drain()
        except asyncio.CancelledError:
            return
        except (ConnectionResetError, ConnectionAbortedError):
            await self._shutdown()
            self._owner.process_disconnect(self)

    
    async def _shutdown(self):
        self._isActive = False

        tasks = [t for t in self._tasks if t is not asyncio.current_task()]
        if len(tasks):
            for task in tasks:
                task.cancel()
            await asyncio.wait(tasks, timeout=1)

        self._writer.close()
        with suppress(ConnectionResetError, ConnectionAbortedError):
            await self._writer.wait_closed()

    
    def _schedule(self, coro: Coroutine):
        if not self._isActive:
            return

        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)


    def send(self, msg: Message):
        self._schedule(self._send(msg))


    def recv(self):
        self._schedule(self._recv())


    def shutdown(self):
        self._schedule(self._shutdown())


    def addr(self) -> tuple[str, int]:
        return self._writer.get_extra_info('peername')