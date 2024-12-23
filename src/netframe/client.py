import socket
from multiprocessing import Process, Queue, Event
from multiprocessing.synchronize import Event as EventClass


from netframe.message import Message
from netframe.client_worker import ClientWorker


class Client:
    def __init__(self) -> None:
        self._serverSock: socket.socket | None = None
        self._inQueue: Queue[Message] = Queue()
        self._outQueue: Queue[Message] = Queue()
        self._proc: Process | None = None
        self._stopEvent: EventClass = Event()


    def connect(self, ip: str, port: int):
        self._serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._serverSock.set_inheritable(True)
        try:
            self._serverSock.connect((ip, port))
        except Exception as e:
            print("[-]connect failed", e)
            raise

        worker = ClientWorker()
        self._proc = Process(target=worker.run, daemon=True,
                             args=(self._serverSock, self._inQueue, self._outQueue, self._stopEvent))
        self._proc.start()


    def send(self, msg: Message, block: bool=True, timeout: int | None=None):
        self._outQueue.put(msg, block, timeout)
        

    def recv(self, block: bool=True, timeout: int | None=None) -> Message:
        msg = self._inQueue.get(block, timeout)
        if msg is None:
            raise ValueError("No more incoming msgs")
        
        return msg


    def shutdown(self):
        if not self._stopEvent.is_set():
            self._stopEvent.set()
            self._inQueue.close()
            self._outQueue.close()
            
        self._proc.join()