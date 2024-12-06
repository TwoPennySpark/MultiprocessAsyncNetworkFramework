from __future__ import annotations
from typing import TYPE_CHECKING

import asyncio
from multiprocessing import Queue

from netframe.config import Config
from netframe.message import Message, OwnedMessage

if TYPE_CHECKING:
    from netframe.worker import Worker


class Connection:
    class Owner:
        SERVER = 1
        CLIENT = 2

    def __init__(self, workerID: int, connID: int,
                 reader: asyncio.StreamReader, 
                 writer: asyncio.StreamWriter, 
                 inQueue: Queue[OwnedMessage],
                 serverConfig: Config | None = None,
                 worker: Worker | None = None):

        self._worker = worker
        self._id = connID
        self._reader = reader
        self._writer = writer
        self._config = serverConfig
        self._owner = Connection.Owner.SERVER if serverConfig else Connection.Owner.CLIENT

        self._inQueue = inQueue

        self._tasks: set[asyncio.Task] = set()


    async def recv(self):
        msg = OwnedMessage()
        
        try:
            hdrBytes = await self._reader.readexactly(Message.Header.HEADER_LEN)
            msg.msg.hdr.unpack(hdrBytes)

            msg.msg.payload = await self._reader.readexactly(msg.msg.hdr.size)

            if self._owner == Connection.Owner.SERVER:
                msg.owner = self
                self._config._on_message(msg)
            self._add_to_incoming_msg_queue(msg)
        except asyncio.CancelledError:
            return
        except asyncio.IncompleteReadError:
            await self.shutdown()
            return
        
        self.schedule_recv()


    async def send(self, msg: Message):
        try:
            self._writer.write(msg.pack())
            await self._writer.drain()
        except asyncio.CancelledError:
            return
        except Exception:
            await self.shutdown()


    def schedule_send(self, msg: Message):
        task = asyncio.create_task(self.send(msg))
        task.add_done_callback(self._tasks.discard)
        self._tasks.add(task)


    def schedule_recv(self):
        task = asyncio.create_task(self.recv())
        task.add_done_callback(self._tasks.discard)
        self._tasks.add(task)


    def _add_to_incoming_msg_queue(self, msg: OwnedMessage):
        if self._owner == Connection.Owner.SERVER: 
            if self._config.isExternalMsgProcess:
                msg.owner = None
            else:
                return

        self._inQueue.put(msg)

    
    async def shutdown(self):
        if self._owner == Connection.Owner.SERVER:
            self._config._on_client_disconnect(self)
            self._worker.del_conn(self._id)

        tasks = [t for t in self._tasks if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()

        self._writer.close()
        await self._writer.wait_closed()


    def addr(self) -> tuple[str, int]:
        return self._writer.get_extra_info('peername')