import socket
from multiprocessing import Queue, cpu_count
from netframe.worker import Worker

from netframe.message import OwnedMessage
from netframe.connection import Connection


class Server:
    def __init__(self) -> None:
        self.inQueue: Queue[OwnedMessage] = Queue()
        self.workerQueues: dict[int, Queue] = {}


    def start(self, port, addr=socket.gethostbyname(socket.gethostname()), workerNum=cpu_count()):
        try:
            self.listenSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.listenSock.bind((addr, port))
            self.listenSock.listen()
        except Exception as e:
            print("[-]Failed to create listen socket:", e)
            raise

        for _ in range(workerNum):
            outQueue = Queue()

            worker = Worker(self.listenSock, self.inQueue, outQueue, self)
            workerProc = worker.start()
            self.workerQueues[workerProc.pid] = outQueue
            
    
    def stop(self):
        pass
        # for worker in self.workers:
        #     worker.terminate()
        # for worker in self.workers:
            # worker.join()


    def update(self):
        while True:
            msg = self.inQueue.get()
            self.on_message(msg)


    def on_client_connect(self, client: Connection) -> bool:
        return True
    

    def on_client_disconnect(self, client: Connection):
        pass


    def on_message(self, msg: OwnedMessage):
        pass