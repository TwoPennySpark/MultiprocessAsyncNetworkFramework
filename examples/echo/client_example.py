import socket
import time

from netframe.message import Message
from netframe.client import Client

from multiprocessing import Process


def client():
    client = Client()
    client.connect(ip=socket.gethostbyname(socket.gethostname()), port=54321)
    start = time.perf_counter()

    for i in range(1000):
        msgSent = Message()
        msgSent.append(b"hello")
        msgSent.append(i.to_bytes(4, 'little'))
        client.send(msgSent)

        msgRecv = client.recv()
        assert msgSent.payload == msgRecv.payload

    end = time.perf_counter()
    print("TIME:", end-start)

    client.shutdown()


if __name__ == "__main__":
    clientProcs: list[Process] = []
    for _ in range(10):
        proc = Process(target=client)
        proc.start()
        clientProcs.append(proc)

    for proc in clientProcs:
        proc.join()