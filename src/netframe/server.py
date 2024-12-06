import os
import signal
import socket
from multiprocessing import Queue, cpu_count, Process, allow_connection_pickling, get_context

from netframe.config import Config
from netframe.worker import Worker
from netframe.message import OwnedMessage

allow_connection_pickling()
spawn = get_context("spawn")

class Server:
    def __init__(self) -> None:
        self.config: Config = Config()
        self.inQueue: Queue[OwnedMessage] = Queue()
        self.workers: list[Process] = []
        self.workerQueues: dict[int, Queue] = {}


    def start(self, port, addr=socket.gethostbyname(socket.gethostname()), workerNum=cpu_count()):
        try:
            print(f"{addr}:{port}")
            self.listenSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.listenSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.listenSock.bind((addr, port))
            self.listenSock.set_inheritable(True)
            self.listenSock.listen()
        except Exception as e:
            print("[-]Failed to create listen socket:", e)
            raise

        for _ in range(workerNum):
            worker = Worker()
            outQueue = Queue()

            workerProc = spawn.Process(target=worker.run, args=(self.listenSock, self.inQueue, outQueue, self.config))
            workerProc.start()

            self.workerQueues[workerProc.pid] = outQueue

            self.workers.append(workerProc)
            
    
    def stop(self):
        for worker in self.workers:
            os.kill(worker.pid, signal.CTRL_BREAK_EVENT)
        for worker in self.workers:
            worker.join()