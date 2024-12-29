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
from netframe.util import loop_policy_setup, win_socket_share, setup_logging


class ClientWorker:
    def run(self,
             serverSock: socket.socket,
             inQueue:  Queue,
             outQueue: Queue,
             shouldStop: EventClass):
        self._serverSock = serverSock
        if sys.platform == "win32":
            self._serverSock = win_socket_share(self._serverSock)

        self._inQueue  = inQueue
        self._outQueue = outQueue
        self._shouldStop = shouldStop
        
        setup_logging()
        self._logger = logging.getLogger("netframe.error")
        
        loop_policy_setup(isMultiprocess=False)
        asyncio.run(self._start_client())


    async def _start_client(self):
        reader, writer = await asyncio.open_connection(sock=self._serverSock)
        self._connection = Connection(reader, writer, self)
        self._connection.recv()
        
        self._loop = asyncio.get_event_loop()
        self._outQueueConsumerThread = self._loop.run_in_executor(None, self._schedule_out_msgs)

        self._logger.info(f"Started client process({os.getpid()})")

        while not self._shouldStop.is_set():
            await asyncio.sleep(0.1)

        self._outQueue.put(None)
        await self._outQueueConsumerThread
        
        if self._connection.isActive:
            self._connection.shutdown()
            tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
            await asyncio.wait(tasks)

        self._logger.info(f"Finished client process({os.getpid()})")


    def process_msg(self, msg: OwnedMessage):
        self._inQueue.put(msg.msg)


    def process_disconnect(self, conn: Connection):
        self._inQueue.put(None)

        self._shouldStop.set()


    def _schedule_out_msgs(self):
        while True:
            msg = self._outQueue.get()
            if msg == None:
                break
            
            self._loop.call_soon_threadsafe(functools.partial(self._connection.send, msg=msg))