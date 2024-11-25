from netframe import Server, Connection, OwnedMessage
import os


class EchoServer(Server):
    def __init__(self):
        super().__init__()

    
    def on_client_connect(self, client: Connection) -> bool:
        print(f"[{os.getpid()}]Client connected")
        return True
    
    
    def on_client_disconnect(self, client: Connection):
        print(f"[{os.getpid()}]Client disconnected")

        
    def on_message(self, msg: OwnedMessage):
        self.workerQueues[msg.workerId].put(msg)


if __name__ == "__main__":
    server = EchoServer()
    server.start(54321, workerNum=10)
    server.update()