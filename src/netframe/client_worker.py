import os
import sys
import socket
import asyncio
import logging
import functools

from multiprocessing import Queue
from multiprocessing.synchronize import Event as EventClass

from netframe.message import OwnedMessage
from netframe.connection import Connection, ConnOwner
from netframe.util import loop_policy_setup, setup_logging
if sys.platform == "win32":
    from netframe.util import win_socket_share


class ClientWorker:
    '''
    Represents a process running an asyncio event loop.
    Manages TCP connection between server and client.
    '''

    @staticmethod
    def run(serverSock: socket.socket,
            inQueue:  Queue,
            outQueue: Queue,
            connLost: EventClass):
        setup_logging()

        if sys.platform == "win32":
            serverSock = win_socket_share(serverSock)

        worker = ClientWorker(serverSock, inQueue, outQueue, connLost)
        worker.start_client()


    def __init__(self, serverSock: socket.socket,
                       inQueue:  Queue,
                       outQueue: Queue,
                       connLost: EventClass):
        '''
        Parameters:
            serverSock: socket that respresents already established connection between client and server
            inQueue:  queue for incoming msgs. Filled by ClientWorker, consumed by Client
            outQueue: queue for outgoing msgs. Filled by Client, consumed by ClientWorker
            connLost: event that is set by ClientWorker to notify Client about the connection breakup
        '''
        self._serverSock = serverSock
        self._inQueue  = inQueue
        self._outQueue = outQueue
        self._connLost = connLost
        
        self._logger = logging.getLogger("netframe.error")
        

    def start_client(self):
        loop_policy_setup(isMultiprocess=False)
        asyncio.run(self._start_client())


    async def _start_client(self):
        reader, writer = await asyncio.open_connection(sock=self._serverSock)
        self._connection = Connection(reader, writer, self)
        self._connection.recv()
        
        self._logger.info(f"Started client process({os.getpid()})")
        
        self._loop = asyncio.get_event_loop()

        # launch outQueue consumer thread, it will run until Client calls shutdown()
        await self._loop.run_in_executor(None, self._schedule_out_msgs)

        if self._connection.isActive:
            self._connection.shutdown()
            tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
            await asyncio.wait(tasks)

        # at this point there might be some msgs left in inQueue which
        # will prevent us from exiting worker process. Since we get to
        # this part after shutdown() is called, it means that the client is
        # no longer interested in received msgs and we can safely discard
        # them by canceling queue thread
        self._inQueue.cancel_join_thread()
        
        self._logger.info(f"Finished client process({os.getpid()})")


    # ConnOwner protocol method
    def process_msg(self, msg: OwnedMessage):
        self._inQueue.put(msg.msg)


    # ConnOwner protocol method
    def process_disconnect(self, conn: Connection):
        self._inQueue.put(None)

        self._connLost.set()


    def _schedule_out_msgs(self):
        while True:
            msg = self._outQueue.get()
            if msg == None:
                break
            
            self._loop.call_soon_threadsafe(functools.partial(self._connection.send, msg=msg))