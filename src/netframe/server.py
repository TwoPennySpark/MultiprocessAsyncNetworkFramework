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
        self.config = config
        self._stopEvent: EventClass = Event()
        self._workers: list[Process] = []


    def start(self):
        try:
            logger.info(f"Starting server on {self.config.ip}:{self.config.port}")
            self._listenSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._listenSock.bind((self.config.ip, self.config.port))
            self._listenSock.set_inheritable(True)
            self._listenSock.listen()
        except Exception as e:
            logger.error(f"Failed to create listen socket: {e}")
            raise

        for _ in range(self.config.workerNum):
            proc = Process(target=ServerWorker.run, daemon=True,
                           args=(self._listenSock, self.config, self._stopEvent))
            proc.start()
            self._workers.append(proc)


    def stop(self):
        self._stopEvent.set()
        for worker in self._workers:
            worker.join()