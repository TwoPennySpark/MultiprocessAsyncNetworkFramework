import os
import time
import socket

from multiprocessing import Process

from netframe import Client, Message


def client(id):
    client = Client()
    addr = socket.gethostbyname(socket.gethostname())
    client.connect(ip=addr, port=54314)

    start = time.perf_counter()
    for i in range(1024):
        msgSent = Message()
        msgSent.hdr.id = i
        msgSent.append(b"hello")
        msgSent.append(os.getpid().to_bytes(4, 'little'))
        client.send(msgSent)
        
        msgRecv = client.recv()
        assert msgSent.payload == msgRecv.payload

    end = time.perf_counter()
    print(f"[{id}]TIME:", end-start)

    client.shutdown()


if __name__ == "__main__":
    i = 0
    for _ in range(10):
        clientProcs: list[Process] = []
        for _ in range(10):
            proc = Process(target=client, args=(i,))
            proc.start()
            clientProcs.append(proc)
            i+=1

        for proc in clientProcs:
            proc.join()