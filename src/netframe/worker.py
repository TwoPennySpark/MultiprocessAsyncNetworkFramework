from __future__ import annotations
from typing import TYPE_CHECKING

import os
import sys
import socket
import asyncio
from multiprocessing import Process, Queue

from netframe.connection import Connection
from netframe.message import OwnedMessage

if TYPE_CHECKING:
    from netframe.server import Server


class Worker:
    def __init__(self, listenSock: socket.socket, 
                 inQueue:  Queue[OwnedMessage], 
                 outQueue: Queue[OwnedMessage], 
                 server:   Server):
        self._listenSock = listenSock

        self._inQueue  = inQueue
        self._outQueue = outQueue

        self._server = server


    def start(self):
        proc = Process(target=self._work, daemon=True)
        proc.start()

        return proc

        
    def _work(self):
        self._id = os.getpid()
        self._lastConnID = 0
        self._connections: dict[int, Connection] = {}

        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.create_task(self._start_server())
        self.loop.create_task(asyncio.to_thread(self._dequeue))
        self.loop.run_forever()


    async def _start_server(self):
        server = await asyncio.start_server(client_connected_cb=self._process_new_connection, sock=self._listenSock)
        await server.serve_forever()


    async def _process_new_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        newConn = Connection(self._id, self._lastConnID, reader, writer, self._inQueue, self._server)
        if self._server.on_client_connect(newConn):
            self._connections[self._lastConnID] = newConn
            self._lastConnID += 1
            asyncio.create_task(newConn.recv())


    def _dequeue(self):
        asyncio.set_event_loop(self.loop)
        while True:
            msg = self._outQueue.get()
            asyncio.run_coroutine_threadsafe(self._connections[msg.connId].send(msg.msg), self.loop)