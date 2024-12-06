import os
import socket
import asyncio
import functools
from multiprocessing import Process, Queue

from netframe.message import Message, OwnedMessage
from netframe.connection import Connection


class Client:
    def __init__(self) -> None:
        self.serverSock: socket.socket | None = None

        self.worker: Process | None = None
        self.loop: asyncio.BaseEventLoop | None = None

        self.connection: Connection | None = None
        self.inQueue: Queue[OwnedMessage] = Queue()
        self.outQueue: Queue[Message] = Queue()


    def connect(self, ip: str, port: int):
        self.serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSock.set_inheritable(True)
        try:
            self.serverSock.connect((ip, port))
        except Exception as e:
            print("[-]connect failed", e)
            raise

        self.worker = Process(target=self._run, daemon=True)
        self.worker.start()

    
    def _run(self):
        sockData = self.serverSock.share(os.getpid())
        self.serverSock = socket.fromshare(sockData)
        
        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self._start_client())
        self.loop.run_forever()


    async def _start_client(self):
        reader, writer = await asyncio.open_connection(sock=self.serverSock)
        self.connection = Connection(0, 0, reader, writer, self.inQueue)
        self.loop.create_task(asyncio.to_thread(self._dequeue))
        self.loop.create_task(self.connection.recv())


    def _dequeue(self):
        while True:
            msg = self.outQueue.get()
            self.loop.call_soon_threadsafe(functools.partial(self.connection.schedule_send, msg=msg))


    def send(self, msg: Message):
        self.outQueue.put(msg)
        

    def recv(self) -> Message:
        return self.inQueue.get().msg


    def shutdown(self):
        self.worker.terminate()
        self.worker.join()