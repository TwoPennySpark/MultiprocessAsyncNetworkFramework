import os
import sys
import socket
import asyncio
import logging

from multiprocessing.synchronize import Event as EventClass

from netframe.config import Config
from netframe.message import OwnedMessage
from netframe.connection import Connection, ConnOwner
from netframe.util import loop_policy_setup, setup_logging
if sys.platform == "win32":
    from netframe.util import win_socket_share


class ServerWorker(ConnOwner):
    '''
    Represents a process running an asyncio event loop.
    Accepts and stores TCP connections.
    '''

    @staticmethod
    def run(listenSock: socket.socket, 
            config: Config,
            shouldStop: EventClass):
        setup_logging()

        if sys.platform == "win32":
            listenSock = win_socket_share(listenSock)

        worker = ServerWorker(listenSock, config, shouldStop)
        worker.serve()


    def __init__(self, listenSock: socket.socket, 
                       config: Config,
                       shouldStop: EventClass):
        '''
        Parameters:
            listenSock: shared listen socket that is used to accept new connections
            config:  configuration params
            shouldStop: event that is set by Server to signal ServerWorkers to quit
        '''
        self._listenSock = listenSock
        self._config = config
        self._app = self._config.app
        self._shouldStop = shouldStop

        self._connections = set[Connection]()  

        self._logger = logging.getLogger("netframe.error")


    def serve(self):
        loop_policy_setup(self._config.workerNum > 1)
        asyncio.run(self._serve())


    async def _serve(self):
        self._server = await asyncio.start_server(
            client_connected_cb=self._process_new_connection, sock=self._listenSock)

        self._logger.info(f"Started server process({os.getpid()})")

        while not self._shouldStop.is_set():
            await asyncio.sleep(0.1)

        await self._shutdown()

        self._logger.info(f"Finished server process({os.getpid()})")


    async def _process_new_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        allowConnection = False
        newConn = Connection(reader, writer, self)

        try:
            allowConnection = self._app.on_client_connect(newConn, self._config.context)
        except BaseException as e:
            self._logger.error(f"Exception occured during execution of "
                               f"user-supplied 'on_client_connect' callback: {e}")

        if allowConnection:
            self._connections.add(newConn)
            newConn.recv()
        else:
            newConn.shutdown()


    # ConnOwner protocol method
    def process_msg(self, msg: OwnedMessage):
        try:
            self._app.on_message(msg, self._config.context)
        except BaseException as e:
            self._logger.error(f"Exception occured during execution of "
                               f"user-supplied 'on_message' callback: {e}")


    # ConnOwner protocol method
    def process_disconnect(self, conn: Connection):
        self._connections.discard(conn)
        try:
            self._app.on_client_disconnect(conn, self._config.context)
        except BaseException as e:
            self._logger.error(f"Exception occured during execution of "
                               f"user-supplied 'on_client_disconnect' callback: {e}")


    async def _shutdown(self):
        self._logger.info(f"Server process({os.getpid()}) shutting down")

        self._server.close()
        self._listenSock.close()

        for conn in self._connections:
            conn.shutdown()

        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if len(tasks):
            await asyncio.wait(tasks, timeout=self._config.gracefulShutdownTimeout)