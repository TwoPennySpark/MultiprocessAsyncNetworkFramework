import os
import sys
import socket
import asyncio
import functools

from threading import Thread
from multiprocessing import Queue
from multiprocessing.synchronize import Event as EventClass

from netframe.message import OwnedMessage
from netframe.connection import Connection, ConnOwner


class ClientWorker:
    def run(self,
             serverSock: socket.socket,
             inQueue:  Queue,
             outQueue: Queue,
             shouldStop: EventClass):
        self._serverSock = serverSock
        self._inQueue  = inQueue
        self._outQueue = outQueue

        self._shouldStop = shouldStop
        self._outQueueConsumerThread = Thread(target=self._schedule_out_msg, daemon=True)

        if sys.platform == "win32":
            sockData = self._serverSock.share(os.getpid())
            self._serverSock = socket.fromshare(sockData)
        
        self._loop = asyncio.get_event_loop()
        self._loop.create_task(self._start_client())
        self._loop.run_until_complete(self._waiter())

        self._outQueueConsumerThread.join()


    async def _start_client(self):
        reader, writer = await asyncio.open_connection(sock=self._serverSock)
        self._connection = Connection(reader, writer, self)
        self._connection.recv()
        
        self._outQueueConsumerThread.start()


    async def _waiter(self):
        while not self._shouldStop.is_set():
            await asyncio.sleep(1)

        self._connection.shutdown()
        self._outQueue.put(None)
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        await asyncio.wait(tasks)


    def process_msg(self, msg: OwnedMessage):
        self._inQueue.put(msg.msg)


    def process_disconnect(self, conn: Connection):
        self._inQueue.put(None)
        self._outQueue.put(None)

        self._shouldStop.set()


    def _schedule_out_msg(self):
        while True:
            msg = self._outQueue.get()
            if msg == None:
                break
            
            self._loop.call_soon_threadsafe(functools.partial(self._connection.send, msg=msg))