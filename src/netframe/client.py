import socket
from multiprocessing import Process, Queue

from netframe.message import Message
from netframe.client_worker import ClientWorker


class Client:
    def __init__(self) -> None:
        self._serverSock: socket.socket | None = None
        self._inQueue: Queue[Message] = Queue()
        self._outQueue: Queue[Message] = Queue()
        self._proc: Process | None = None


    def connect(self, ip: str, port: int):
        print(f"{ip}:{port}")

        self._serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._serverSock.set_inheritable(True)
        try:
            self._serverSock.connect((ip, port))
        except Exception as e:
            print("[-]connect failed", e)
            raise

        worker = ClientWorker()
        self._proc = Process(target=worker.run, daemon=True,
                             args=(self._serverSock, self._inQueue, self._outQueue))
        self._proc.start()


    def send(self, msg: Message):
        self._outQueue.put(msg)
        

    def recv(self) -> Message:
        return self._inQueue.get()


    def shutdown(self):
        self._proc.terminate()
        self._proc.join()
    