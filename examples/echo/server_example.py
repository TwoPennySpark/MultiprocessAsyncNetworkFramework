from netframe import Server, Connection, OwnedMessage, Config, Message, ContextT

import os
import time


def on_client_connect(client: Connection, context: ContextT) -> bool:
    print(f"\n[{os.getpid()}]Client connected from {client.addr()}", flush=True)
    return True


def on_client_disconnect(client: Connection, context: ContextT):
    print(f"[{os.getpid()}]Client from {client.addr()} disconnected", flush=True)


def on_message(msg: OwnedMessage, context: ContextT):
    print(f"[{os.getpid()}]ON_MSG:", msg.msg)
    msg.owner.send(msg.msg)


if __name__ == "__main__":
    config = Config(on_client_connect, on_client_disconnect, on_message, workerNum=1)
    server = Server(config)
    server.start()

    # user app
    while True:
        time.sleep(1)
