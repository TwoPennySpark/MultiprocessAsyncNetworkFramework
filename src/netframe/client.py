import socket
import logging

from multiprocessing import Process, Queue, Event
from multiprocessing.synchronize import Event as EventClass

from netframe.message import Message
from netframe.util import setup_logging
from netframe.client_worker import ClientWorker

setup_logging()


class Client:
    def __init__(self) -> None:
        self._inQueue: Queue[Message | None] = Queue()
        self._outQueue: Queue[Message | None] = Queue()
        self._workerProc: Process | None = None

        # Event that is set by ClientWorker to notify Client about the 
        # connection breakup. Used in send method to signal to the user
        # of Client that he can no longer send any msgs
        self._connLost: EventClass = Event()
        
        self._logger = logging.getLogger("netframe.error")


    def connect(self, ip: str, port: int):
        # connect to server
        serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serverSock.set_inheritable(True)
        try:
            serverSock.connect((ip, port))
        except Exception as e:
            self._logger.error(f"Connect failed: {e}")
            raise

        # launch client worker process, pass newly created socket
        self._workerProc = Process(target=ClientWorker.run, daemon=True,
                             args=(serverSock, self._inQueue, self._outQueue, self._connLost))
        self._workerProc.start()

        # don't need server socket in this process any more
        serverSock.close()


    def send(self, msg: Message, block: bool=True, timeout: int | None=None):
        if self._connLost.is_set():
            raise RuntimeError("Connection is closed for write")
        self._outQueue.put(msg, block, timeout)
        

    def recv(self, block: bool=True, timeout: int | None=None) -> Message:
        msg = self._inQueue.get(block, timeout)
        # msg == None means there won't be any more incoming msgs
        # we don't check self._connLost event here, since, even if
        # connection is lost, ClientWorker can still store msgs it 
        # read before connection breakup that were not yet requested 
        # by the Client
        if msg is None:
            self._inQueue.close()
            raise RuntimeError("No more incoming msgs")
        
        return msg


    def shutdown(self):
        if not self._workerProc:
            return

        self._inQueue.close()

        self._outQueue.put(None)
        self._outQueue.close()

        self._workerProc.join()
        self._workerProc = None