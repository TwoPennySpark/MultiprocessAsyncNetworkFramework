import os
import sys
import socket
import asyncio
import logging
import functools

import multiprocessing.connection
from multiprocessing import Pipe
from multiprocessing.connection import wait, Connection as PipeHndl
from contextlib import suppress

from netframe.message import OwnedMessage
from netframe.connection import Connection, ConnOwner
from netframe.util import loop_policy_setup, setup_logging
if sys.platform == "win32":
    from netframe.util import win_socket_share


class ClientWorker(ConnOwner):
    '''
    Represents a process running an asyncio event loop.
    Manages TCP connection between server and client.
    '''
    
    @staticmethod
    def run(serverSock: socket.socket,
            inQueue:  PipeHndl,
            outQueue: PipeHndl):
        setup_logging()

        if sys.platform == "win32":
            serverSock = win_socket_share(serverSock)

        worker = ClientWorker(serverSock, inQueue, outQueue)
        worker.start_client()


    def __init__(self, serverSock: socket.socket,
                       inQueue:  PipeHndl,
                       outQueue: PipeHndl):
        '''
        Parameters:
            serverSock: socket that respresents already established connection between client and server
            inQueue:  queue for incoming msgs. Filled by ClientWorker, consumed by Client
            outQueue: queue for outgoing msgs. Filled by Client, consumed by ClientWorker
        '''
        self._serverSock = serverSock
        self._inQueue  = inQueue
        self._outQueue = outQueue
        
        self._logger = logging.getLogger("netframe.error")
        

    def start_client(self):
        loop_policy_setup(isMultiprocess=False)
        asyncio.run(self._start_client())


    async def _start_client(self):
        reader, writer = await asyncio.open_connection(sock=self._serverSock)
        self._connection = Connection(reader, writer, self)
        self._connection.recv()
        
        self._logger.info(f"Started client process({os.getpid()})")
        
        # launch outQ consumer thread, it will run until Client 
        # calls shutdown() or we lose connection with server
        self._loop = asyncio.get_event_loop()
        # this pipe is used to gracefully stop the thread
        self._outThreadStopSignalSender, self._outThreadStopSignalRecver = Pipe()
        await self._loop.run_in_executor(None, self._schedule_out_msgs)

        if self._connection.isActive:
            self._connection.shutdown()
            tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
            await asyncio.wait(tasks)

        self._logger.info(f"Finished client process({os.getpid()})")


    # ConnOwner protocol method
    def process_msg(self, msg: OwnedMessage):
        with suppress(BrokenPipeError):
            self._inQueue.send(msg.msg)


    # ConnOwner protocol method
    def process_disconnect(self, conn: Connection):
        # signal Client that connection is lost
        self._inQueue.close()

        # signal outQ consumer thread to stop
        self._outThreadStopSignalSender.close()


    def _schedule_out_msgs(self):
        while True:
            ready = wait([self._outQueue, self._outThreadStopSignalRecver])
            if self._outThreadStopSignalRecver in ready:
                # lost connection with server
                break

            try:
                msg = self._outQueue.recv()
            except EOFError:
                # Client called shutdown()
                break

            self._loop.call_soon_threadsafe(functools.partial(self._connection.send, msg=msg))