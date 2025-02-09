import time
import socket
import logging

from multiprocessing import Process, Event

from netframe.config import Config
from netframe.util import setup_logging
from netframe.server_worker import ServerWorker


class Server:
    def __init__(self, config: Config):
        self._config = config
        self._stopEvent = Event()
        self._workers: list[Process] = []

        setup_logging()
        self._logger = logging.getLogger("netframe.error")


    def start(self):
        if self._workers:
            raise RuntimeError("Server already running")

        self._logger.info(f"Starting server on {self._config.ip}:{self._config.port}")

        # create listen socket
        try:
            listenSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listenSock.bind((self._config.ip, self._config.port))
            listenSock.set_inheritable(True)
            listenSock.listen()
        except Exception as e:
            self._logger.error(f"Failed to create listen socket: {e}")
            raise

        # launch server worker processes, pass newly created socket
        for _ in range(self._config.workerNum):
            proc = Process(target=ServerWorker.run, daemon=True,
                           args=(listenSock, self._config, self._stopEvent))
            proc.start()
            self._workers.append(proc)

        # don't need listen socket in this process any more
        listenSock.close()


    def stop(self, timeout: float | None=None):
        ''' 
        Stop server worker processes in timeout seconds
        If timeout is reached and workers still active -
        force shutdown them
        '''
        if not self._workers:
            raise RuntimeError("Server is not running")

        # signals workers to stop
        self._stopEvent.set()

        if timeout is None:
            for worker in self._workers:
                worker.join(timeout)
        else:
            for worker in self._workers:
                start = time.perf_counter()
                worker.join(timeout)
                end   = time.perf_counter()
                
                timeout -= end-start
                if timeout < 0: 
                    timeout = 0

            for worker in self._workers:
                if worker.is_alive():
                    worker.kill()

        self._workers.clear()