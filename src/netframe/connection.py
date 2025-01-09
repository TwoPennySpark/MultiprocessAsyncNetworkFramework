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
        
        self.isActive = True

        self._tasks: set[asyncio.Task] = set()


    async def _recv(self):
        msg = OwnedMessage(owner=self)

        try:
            hdrBytes = await self._reader.readexactly(Message.Header.HEADER_LEN)
            msg.msg.hdr.unpack(hdrBytes)

            msg.msg.payload = bytearray(await self._reader.readexactly(msg.msg.hdr.size))            
        except asyncio.CancelledError:
            return
        except (asyncio.IncompleteReadError, ConnectionResetError, ConnectionAbortedError):
            self.shutdown(waitForSendTasks=False)
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
        except (ConnectionResetError, ConnectionAbortedError) as e:
            self.shutdown(waitForSendTasks=False)
            self._owner.process_disconnect(self)

    
    async def _shutdown(self):
        allTasks = [t for t in self._tasks if t is not asyncio.current_task()]
        if len(allTasks):
            await asyncio.wait(allTasks)

        self._writer.close()
        with suppress(ConnectionResetError, ConnectionAbortedError):
            await self._writer.wait_closed()

    
    def _schedule(self, coro: Coroutine):
        if not self.isActive:
            return

        task = asyncio.create_task(coro, name=coro.__name__)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)


    def send(self, msg: Message):
        self._schedule(self._send(msg))


    def recv(self):
        self._schedule(self._recv())


    def shutdown(self, waitForSendTasks: bool=True):
        tasksToCancel = [t for t in self._tasks 
                        if  t is not asyncio.current_task()]
        if waitForSendTasks:
            tasksToCancel = [t for t in tasksToCancel
                            if t.get_name() != self._send.__name__]
        for task in tasksToCancel:
            task.cancel()

        self._schedule(self._shutdown())
        self.isActive = False


    def addr(self) -> tuple[str, int]:
        return self._writer.get_extra_info('peername')