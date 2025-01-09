import socket
import logging

from multiprocessing import Process, Event
from multiprocessing.synchronize import Event as EventClass
from multiprocessing.context import SpawnProcess

from netframe.config import Config
from netframe.util import setup_logging
from netframe.server_worker import ServerWorker

setup_logging()
logger = logging.getLogger("netframe.error")


class Server:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._stopEvent: EventClass = Event()
        self._workers: list[Process] = []


    def start(self):
        try:
            logger.info(f"Starting server on {self._config.ip}:{self._config.port}")
            listenSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listenSock.bind((self._config.ip, self._config.port))
            listenSock.set_inheritable(True)
            listenSock.listen()
        except Exception as e:
            logger.error(f"Failed to create listen socket: {e}")
            raise

        for _ in range(self._config.workerNum):
            proc = Process(target=ServerWorker.run, daemon=True,
                           args=(listenSock, self._config, self._stopEvent))
            proc.start()
            self._workers.append(proc)

        listenSock.close()


    def stop(self):
        self._stopEvent.set()
        for worker in self._workers:
            worker.join()