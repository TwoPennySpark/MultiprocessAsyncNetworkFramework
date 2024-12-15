import os
import time
import socket

from netframe.client import Client
from netframe.message import Message

from multiprocessing import Process


def client():
    client = Client()
    addr = socket.gethostbyname(socket.gethostname())
    client.connect(ip=addr, port=54314)

    start = time.perf_counter()

    for _ in range(1):
        msgSent = Message()
        msgSent.append(b"hello")
        msgSent.append(os.getpid().to_bytes(4, 'little'))
        client.send(msgSent)

        msgRecv = client.recv()
        assert msgSent.payload == msgRecv.payload

    end = time.perf_counter()
    print(f"TIME:", end-start)

    client.shutdown()


if __name__ == "__main__":
    for _ in range(10):
        clientProcs: list[Process] = []
        for _ in range(10):
            proc = Process(target=client)
            proc.start()
            clientProcs.append(proc)

        for proc in clientProcs:
            proc.join()