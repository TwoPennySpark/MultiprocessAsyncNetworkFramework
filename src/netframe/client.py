import queue
import socket
import logging

from multiprocessing import Process, Pipe

from netframe.message import Message
from netframe.util import setup_logging
from netframe.client_worker import ClientWorker


class Client:
    def __init__(self):
        self._inQueueRead,  self._inQueueWrite  = Pipe()
        self._outQueueRead, self._outQueueWrite = Pipe()
        self._worker: Process | None = None

        setup_logging()
        self._logger = logging.getLogger("netframe.error")


    def __del__(self):
        if self._worker:
            self.shutdown()


    def connect(self, ip: str, port: int):
        if self._worker:
            raise RuntimeError("Client already connected")
        
        # connect to server
        serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serverSock.set_inheritable(True)
        try:
            serverSock.connect((ip, port))
        except Exception as e:
            self._logger.error(f"Connect failed: {e}")
            raise

        # launch client worker process, pass newly created socket
        self._worker = Process(target=ClientWorker.run, daemon=True,
                             args=(serverSock, self._inQueueWrite, self._outQueueRead))
        self._worker.start()

        # close resources not needed in this proc
        self._inQueueWrite.close()
        self._outQueueRead.close()
        serverSock.close()


    def send(self, msg: Message):
        if not self._worker:
            raise RuntimeError("Client is not connected")
        
        try:
            self._outQueueWrite.send(msg)
        except (BrokenPipeError, OSError):
            raise ConnectionResetError("Connection lost")
        

    def recv(self, timeout: float | None=None) -> Message:
        if not self._worker:
            raise RuntimeError("Client is not connected")

        try:
            if timeout != None and self._inQueueRead.poll(timeout) == False:
                raise queue.Empty
            msg = self._inQueueRead.recv()
        except (EOFError, OSError):
            raise ConnectionResetError("Connection lost")
        
        return msg


    def shutdown(self, timeout: float | None=None):
        ''' 
        Stop client worker process in timeout seconds
        If timeout is reached and worker still active -
        force shutdown it
        '''
        if not self._worker:
            raise RuntimeError("Client is not connected")
        
        self._inQueueRead.close()
        self._outQueueWrite.close()

        self._worker.join(timeout)
        if self._worker.is_alive():
            self._worker.kill()
        self._worker = None