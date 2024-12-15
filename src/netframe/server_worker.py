from __future__ import annotations

import os
import sys
import socket
import asyncio

from multiprocessing.synchronize import Event

from netframe.config import Config
from netframe.connection import Connection, ConnOwner
from netframe.message import OwnedMessage


class ServerWorker:
    def run(self, listenSock: socket.socket, 
                  config: Config,
                  shouldStop: Event):
        
        self._shouldStop = shouldStop
        self._listenSock = listenSock

        self._config = config

        self._connections = set[Connection]()  

        if sys.platform == "win32":
            sockData = self._listenSock.share(os.getpid())
            self._listenSock = socket.fromshare(sockData)

        self._loop_setup(self._config.workerNum == 1)
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        asyncio.run(self._serve())


    async def _serve(self):
        self._server = await asyncio.start_server(
            client_connected_cb=self._process_new_connection, sock=self._listenSock)

        while not self._shouldStop.is_set():
            await asyncio.sleep(1)

        await self._shutdown()


    async def _process_new_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        newConn = Connection(reader, writer, self)
        if self._config._on_client_connect(newConn, self._config.context):
            self._connections.add(newConn)
            newConn.recv()
        else:
            newConn.shutdown(notifyOwner=False)


    def process_msg(self, msg: OwnedMessage):
        self._config._on_message(msg, self._config.context)


    def process_disconnect(self, conn: Connection):
        self._config._on_client_disconnect(conn, self._config.context)
        self._connections.discard(conn)


    async def _shutdown(self):
        self._server.close()
        self._listenSock.close()

        tasks = [conn.shutdown() for conn in self._connections]
        if len(tasks):
            await asyncio.wait(tasks, timeout=self._config.gracefulShutdownTimeout)
            
        self.loop.stop()

    
    def _loop_setup(self, isSolo):
        if sys.platform == "win32":
            if not isSolo:
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        else:
            try:
                import uvloop
                asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
            except ImportError:
                pass