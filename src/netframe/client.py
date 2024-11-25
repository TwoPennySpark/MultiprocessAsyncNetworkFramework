import socket
import asyncio
from multiprocessing import Process, Queue

from netframe.message import Message, OwnedMessage
from netframe.connection import Connection


class Client:
    def __init__(self) -> None:
        self.worker: Process | None = None
        self.loop: asyncio.BaseEventLoop | None = None

        self.connection: Connection | None = None
        self.inQueue: Queue[OwnedMessage] = Queue()
        self.outQueue: Queue[Message] = Queue()

        self.serverSock: socket.socket | None = None


    def connect(self, ip: str, port: int):
        self.serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.serverSock.connect((ip, port))
        except Exception as e:
            print("[-]connect failed", e)
            raise

        self.worker = Process(target=self._work, daemon=True)
        self.worker.start()


    def _work(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.create_task(self._start_client())
        self.loop.run_forever()


    async def _start_client(self):
        reader, writer = await asyncio.open_connection(sock=self.serverSock)
        self.connection = Connection(0, 0, reader, writer, self.inQueue)
        self.loop.create_task(asyncio.to_thread(self._dequeue))
        self.loop.create_task(self.connection.recv())


    def _dequeue(self):
        asyncio.set_event_loop(self.loop)
        while True:
            msg = self.outQueue.get()
            asyncio.run_coroutine_threadsafe(self.connection.send(msg), self.loop)


    def send(self, msg: Message):
        self.outQueue.put(msg)
        

    def recv(self) -> Message:
        return self.inQueue.get().msg


    def shutdown(self):
        self.worker.terminate()