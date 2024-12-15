import os
import sys
import socket
import asyncio
import functools
from multiprocessing import Queue

from netframe.message import Message, OwnedMessage
from netframe.connection import Connection, ConnOwner


class ClientWorker:
    def run(self,
             serverSock: socket.socket,
             inQueue:  Queue,
             outQueue: Queue):

        self._serverSock = serverSock

        self._inQueue  = inQueue
        self._outQueue = outQueue

        if sys.platform == "win32":
            sockData = self._serverSock.share(os.getpid())
            self._serverSock = socket.fromshare(sockData)
        
        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self._start_client())
        self.loop.run_forever()


    async def _start_client(self):
        reader, writer = await asyncio.open_connection(sock=self._serverSock)
        self.connection = Connection(reader, writer, self)
        self.loop.create_task(asyncio.to_thread(self._dequeue))
        self.connection.recv()


    def process_msg(self, msg: OwnedMessage):
        self._inQueue.put(msg.msg)


    def process_disconnect(self, conn: Connection):
        pass


    def _dequeue(self):
        while True:
            msg = self._outQueue.get()
            self.loop.call_soon_threadsafe(functools.partial(self.connection.send, msg=msg))