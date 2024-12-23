from netframe import Server, Connection, OwnedMessage, Config, ContextT

import os
import time

config = Config(workerNum=4)

@config.on_client_connect
def on_client_connect(client: Connection, context: ContextT) -> bool:
    print(f"\n[{os.getpid()}]Client connected from {client.addr()}", flush=True)
    return True


@config.on_client_disconnect
def on_client_disconnect(client: Connection, context: ContextT):
    print(f"[{os.getpid()}]Client from {client.addr()} disconnected", flush=True)


@config.on_message
def on_message(msg: OwnedMessage, context: ContextT):
    print(f"[{os.getpid()}]ON_MSG:", msg.msg)
    msg.owner.send(msg.msg)


if __name__ == "__main__":
    server = Server(config)
    server.start()

    # user app
    while True:
        time.sleep(1)
