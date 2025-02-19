import queue
import socket
import logging

from multiprocessing import Pipe

from netframe.message import Message
from netframe.util import setup_logging
from netframe.worker_pool import WorkerPool
from netframe.client_worker import ClientWorker


class Client:
    def __init__(self):
        self._inQueueRead,  self._inQueueWrite  = Pipe()
        self._outQueueRead, self._outQueueWrite = Pipe()
        self._worker = WorkerPool(workerNum=1)

        setup_logging()
        self._logger = logging.getLogger("netframe.error")


    def __del__(self):
        if self._worker.is_started():
            self.shutdown()


    def connect(self, ip: str, port: int):
        if self._worker.is_started():
            raise RuntimeError("Client already connected")
        
        # connect to server
        serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serverSock.set_inheritable(True)
        try:
            serverSock.connect((ip, port))
        except Exception as e:
            self._logger.error(f"Connect failed: {e}")
            raise

        # launch client worker process
        self._worker.start(target=ClientWorker.run, 
                           args=(serverSock, self._inQueueWrite, self._outQueueRead))

        # close resources not needed in this proc
        self._inQueueWrite.close()
        self._outQueueRead.close()
        serverSock.close()


    def send(self, msg: Message):
        if not self._worker.is_started():
            raise RuntimeError("Client is not connected")
        
        try:
            self._outQueueWrite.send(msg)
        except (BrokenPipeError, OSError):
            raise ConnectionResetError("Connection lost")
        

    def recv(self, timeout: float | None=None) -> Message:
        if not self._worker.is_started():
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
        Waits for client worker process to finish within timeout, 
        shuts it down forcefully after timeout expires
        '''
        if not self._worker.is_started():
            raise RuntimeError("Client is not connected")
        
        self._inQueueRead.close()
        self._outQueueWrite.close()

        self._worker.stop(timeout)