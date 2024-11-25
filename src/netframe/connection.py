from __future__ import annotations
from typing import TYPE_CHECKING

import asyncio
from multiprocessing import Queue

from netframe.message import Message, OwnedMessage

if TYPE_CHECKING:
    from netframe.server import Server


class Connection:
    def __init__(self, workerID: int, connID: int,
                 reader: asyncio.StreamReader, 
                 writer: asyncio.StreamWriter, 
                 inQueue: Queue[OwnedMessage],
                 server: Server | None = None):
        self._workerID = workerID
        self._id = connID
        self._reader = reader
        self._writer = writer
        self._server = server

        self._inQueue = inQueue


    async def recv(self):
        msg = OwnedMessage()

        try:
            hdrBytes = await self._reader.readexactly(Message.Header.HEADER_LEN)
            msg.msg.hdr.unpack(hdrBytes)

            msg.msg.payload = await self._reader.readexactly(msg.msg.hdr.size)
            self._add_to_incoming_msg_queue(msg)
        except Exception as e:
            if self._server:
                self._server.on_client_disconnect(self)
            return
        
        asyncio.create_task(self.recv())


    async def send(self, msg: Message):
        try:
            self._writer.write(msg.pack())
            await self._writer.drain()
        except Exception as e:
            if self._server:
                self._server.on_client_disconnect(self)
            return


    def _add_to_incoming_msg_queue(self, msg: OwnedMessage):
        if self._server:
            msg.workerId = self._workerID
            msg.connId = self._id
        self._inQueue.put(msg)