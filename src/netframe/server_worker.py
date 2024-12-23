from __future__ import annotations
from multiprocessing.synchronize import Event as EventClass

import sys
import socket
import asyncio

from netframe.config import Config
from netframe.message import OwnedMessage
from netframe.connection import Connection, ConnOwner
from netframe.util import loop_policy_setup, win_socket_share


class ServerWorker:
    def run(self, listenSock: socket.socket, 
                  config: Config,
                  shouldStop: EventClass):
        self._listenSock = listenSock
        if sys.platform == "win32":
            self._listenSock = win_socket_share(self._listenSock)
        
        self._config = config
        self._shouldStop = shouldStop

        self._connections = set[Connection]()  

        loop_policy_setup(self._config.workerNum > 1)
        asyncio.run(self._serve())


    async def _serve(self):
        self._server = await asyncio.start_server(
            client_connected_cb=self._process_new_connection, sock=self._listenSock)

        while not self._shouldStop.is_set():
            await asyncio.sleep(0.1)

        await self._shutdown()


    async def _process_new_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        allowConnection = False
        newConn = Connection(reader, writer, self)

        try:
            allowConnection = self._config._on_client_connect(newConn, self._config.context)
        except BaseException:
            pass

        if allowConnection:
            self._connections.add(newConn)
            newConn.recv()
        else:
            newConn.shutdown()


    def process_msg(self, msg: OwnedMessage):
        try:
            self._config._on_message(msg, self._config.context)
        except BaseException:
            pass


    def process_disconnect(self, conn: Connection):
        self._connections.discard(conn)
        try:
            self._config._on_client_disconnect(conn, self._config.context)
        except BaseException:
            pass


    async def _shutdown(self):
        self._server.close()
        self._listenSock.close()

        tasks = [conn.shutdown() for conn in self._connections]
        if len(tasks):
            await asyncio.wait(tasks, timeout=self._config.gracefulShutdownTimeout)