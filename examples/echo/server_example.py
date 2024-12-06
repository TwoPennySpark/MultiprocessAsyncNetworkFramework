import os
import time

from netframe import Server, Connection, OwnedMessage

server = Server()

@server.config.on_client_connect
def on_client_connect(client: Connection) -> bool:
    print(f"[{os.getpid()}][{client._id}]Client connected from {client.addr()}", flush=True)
    return True


@server.config.on_client_disconnect
def on_client_disconnect(client: Connection):
    print(f"[{os.getpid()}]Client from {client.addr()} disconnected", flush=True)


@server.config.on_message
def on_message(msg: OwnedMessage):
    print(f"[{os.getpid()}][{msg.owner._id}]ON_MSG:", msg.msg)
    msg.owner.schedule_send(msg.msg)


if __name__ == "__main__":
    server.start(port=54314, workerNum=2)

    # user app
    while True:
        time.sleep(0.1)