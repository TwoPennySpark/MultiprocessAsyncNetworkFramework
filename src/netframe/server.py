import socket
import logging

from multiprocessing import Process, Event
from multiprocessing.synchronize import Event as EventClass
from multiprocessing.context import SpawnProcess

from netframe.config import Config
from netframe.util import setup_logging
from netframe.server_worker import ServerWorker

setup_logging()


class Server:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._stopEvent: EventClass = Event()
        self._workers: list[Process] = []

        self._logger = logging.getLogger("netframe.error")


    def start(self):
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


    def stop(self):
        if not self._workers:
            return

        # signals workers to stop
        self._stopEvent.set()

        # wait for workers to finish
        for worker in self._workers:
            worker.join()