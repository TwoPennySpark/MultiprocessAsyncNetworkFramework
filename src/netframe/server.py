import socket
import logging

from multiprocessing import Event

from netframe.config import Config
from netframe.util import setup_logging
from netframe.worker_pool import WorkerPool
from netframe.server_worker import ServerWorker


class Server:
    def __init__(self, config: Config):
        self._config = config
        self._stopEvent = Event()
        self._workers = WorkerPool(config.workerNum)

        setup_logging()
        self._logger = logging.getLogger("netframe.error")


    def start(self):
        '''Creates listen socket, launches server workers'''
        if self._workers.is_started():
            raise RuntimeError("Server already running")

        self._logger.info(f"Starting server on {self._config.ip}:{self._config.port}")

        # create listen socket
        listenSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            listenSock.bind((self._config.ip, self._config.port))
        except Exception as e:
            self._logger.error(f"Failed to create listen socket: {e}")
            raise
        listenSock.set_inheritable(True)

        # launch server worker processes
        self._workers.start(target=ServerWorker.run, 
                            args=(listenSock, self._config, self._stopEvent))

        # don't need listen socket in this proc any more
        listenSock.close()


    def stop(self, timeout: float | None=None):
        ''' 
        Waits for server worker processes to finish within timeout, 
        shuts them down forcefully after timeout expires
        '''
        if not self._workers.is_started():
            raise RuntimeError("Server is not running")

        # signals workers to stop
        self._stopEvent.set()

        self._workers.stop(timeout)