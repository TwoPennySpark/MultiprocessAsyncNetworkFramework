import socket
import logging

from multiprocessing import Process, Queue, Event
from multiprocessing.synchronize import Event as EventClass

from netframe.message import Message
from netframe.util import setup_logging
from netframe.client_worker import ClientWorker

setup_logging()
logger = logging.getLogger("netframe.error")


class Client:
    def __init__(self) -> None:
        self._inQueue: Queue[Message | None] = Queue()
        self._outQueue: Queue[Message | None] = Queue()
        self._proc: Process | None = None
        self._stopEvent: EventClass = Event()


    def connect(self, ip: str, port: int):
        serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serverSock.set_inheritable(True)
        try:
            serverSock.connect((ip, port))
        except Exception as e:
            logger.error(f"Connect failed: {e}")
            raise

        self._proc = Process(target=ClientWorker.run, daemon=True,
                             args=(serverSock, self._inQueue, self._outQueue, self._stopEvent))
        self._proc.start()

        serverSock.close()


    def send(self, msg: Message, block: bool=True, timeout: int | None=None):
        if self._stopEvent.is_set():
            raise RuntimeError("Connection is closed for write")
        self._outQueue.put(msg, block, timeout)
        

    def recv(self, block: bool=True, timeout: int | None=None) -> Message:
        msg = self._inQueue.get(block, timeout)
        if msg is None:
            self._inQueue.close()
            raise RuntimeError("No more incoming msgs")
        
        return msg


    def shutdown(self):
        if not self._proc:
            return

        self._inQueue.close()

        self._outQueue.put(None)
        self._outQueue.close()

        self._proc.join()
        self._proc = None