from __future__ import annotations
from typing import Protocol, Coroutine

import asyncio
from contextlib import suppress

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


    async def _recv(self):
        msg = OwnedMessage(owner=self)

        try:
            hdrBytes = await self._reader.readexactly(Message.Header.HEADER_LEN)
            msg.msg.hdr.unpack(hdrBytes)

            msg.msg.payload = await self._reader.readexactly(msg.msg.hdr.size)            
        except asyncio.CancelledError:
            return
        except (asyncio.IncompleteReadError, ConnectionResetError) as e:
            self.shutdown()
            return
        
        self.recv()
        self._owner.process_msg(msg)

    
    async def _send(self, msg: Message):
        try:
            self._writer.write(msg.pack())
            await self._writer.drain()
        except asyncio.CancelledError:
            return
        except ConnectionResetError as e:
            self.shutdown()

    
    async def _shutdown(self, notifyOwner:bool=True):
        if notifyOwner:
            self._owner.process_disconnect(self)

        tasks = [t for t in self._tasks if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()

        if len(tasks):
            await asyncio.wait(tasks, timeout=1)

        self._writer.close()
        with suppress(ConnectionResetError):
            await self._writer.wait_closed()

    
    def _schedule(self, coro: Coroutine) -> asyncio.Task:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task


    def send(self, msg: Message) -> asyncio.Task:
        return self._schedule(self._send(msg))


    def recv(self) -> asyncio.Task:
        return self._schedule(self._recv())


    def shutdown(self, notifyOwner=True) -> asyncio.Task:
        return self._schedule(self._shutdown(notifyOwner))


    def addr(self) -> tuple[str, int]:
        return self._writer.get_extra_info('peername')