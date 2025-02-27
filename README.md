## Overview
A general purpose framework that eliminates the need of writing server/client code from scratch for simple applications. It provides a set of classes, namely Server, Client, Connection and Message that hide the complexity related to asynchronous network programming.

## Server 
Server works by creating one or more worker processes, each running it's own asyncio loop. All workers share one listen socket on which they accept new connections, each worker maintains it's own set of connections and can't directly access connections from other workers. When worker accepts/loses a connection or receives a new message it calls corresponding user-supplied method. In order to provide those methods, user must create a class that implements the **ServerApp** protocol:

```
class ServerApp(Protocol):
    def __init__(self, context: ContextT):
        ...

    def on_client_connect(self, client: Connection) -> bool:
        return True

    def on_client_disconnect(self, client: Connection):
        ...

    def on_message(self, msg: OwnedMessage):
        ...
```

#### ServerApp methods:
- __init\_\_(context: ContextT):

Receives a **ContextT** argument - a dictionary (**dict[str, Any]**) that contains any user's data needed for his application(see **Server::\_\_init__**).
An instance of the user class that implements **ServerApp** protocol will be created once inside every worker process at **Server** startup.
- on_client_connect(client: Connection) -> bool:

Called when a new TCP connection is accepted, is used to filter out undesired connections. Must return a boolean value: **True** if connection is valid, otherwise - **False**. Setting to '**return True**' will just accept all connections. 
- on_client_disconnect(client: Connection):

Called when connection is lost, either by graceful TCP shutdown or network error. It's is not called when shutdown is initiated by server side - calling **Connection::shutdown()** or returning **False** from **on_client_connect()** will not trigger this callback.
- on_message(msg: OwnedMessage):

Called when worker receives a new message.

#### Server methods:
- __init\_\_(config: Config): \
Accepts a **Config** instanse - a dataclass, that contains server settings:
    - app - **type** of a class that implements **ServerApp** protocol. A separate instance of this type will be constructed in every worker process. Required arg.
    - context - **dict[str, Any]**, user data that will be used inside workers. This data is passed from the user's parent process to the child workers processes during the server startup, so it must be pickleable. Optional arg (default={}).
    - ip - address that server is going to bind to. Optional arg (default=54314).
    - port - port that server is going to bind to. Optional arg (default=socket.gethostbyname(socket.gethostname())).
    - workerNum - amount of worker processes. Optional arg (default=1).

- start():

Binds to the specified address and launches workers. Does not block calling process.

- stop(timeout: float | None=None):

If the optional argument timeout is **None**, the method blocks until worker processes are finished. If timeout is a positive number, it blocks at most timeout seconds, if processes has not finished by that time, it terminates the process.


## Client
Connects to the specified address, then creates a worker process that maintaines established connection(handles sends, recvs, shutdown).

- connect(ip: str, port: int):

Connects to the ip:port, then creates a worker process.

- send(msg: Message):

Sends msg to worker process to be scheduled for sending over connection. Throws **ConnectionResetError** if connection was lost.

- recv(timeout: float | None=None) -> Message:

If the optional argument timeout is **None**, the method blocks until new message is received. If timeout is a positive number, it blocks at most timeout seconds, if message has not arrived by that time, it throws **queue.Empty** exception. Throws **ConnectionResetError** if connection was lost.

- shutdown(timeout: float | None=None):

If the optional argument timeout is **None**, the method blocks until worker process is finished. If timeout is a positive number, it blocks at most timeout seconds, if process has not finished by that time, it terminates the process.


## Connection
Class that represets established TCP connection, accessible only inside **ServerApp** callbacks. Its two main methods - **send()** and **shutdown()** are used to send messages over the connection and to shut it down. The **Connection::recv()** method is not supposed to be called from any of the callbacks, messages are only received via the **on_message()** method. 

- send(msg: Message):

Sends msg.

- shutdown():

Closes the connection.

- addr() -> tuple[str, int]:

Returns the remote address with which the connection is established - ip, port.

## Message & OwnedMessage
Classes that represent messages sent over a **Connection**. **Message** is a dataclass that consists of 2 parts: header and payload. Header contains 2 fields - ID and size. ID may be used by the user to represent the type of the message according to the protocol used. This isn't necessary however, it's there mostly for convinience, since type of message and size are common fields among most network protocols. The size field contains the size of the payload and shouldn't be modified by user directly. The payload is the user's data, it is inserted using the **append()** method(which automaticly changes the size) and extracted using **pop()**. **OwnedMessage** holds both **Message** and the **Connection** it came from.

- append(data: bytes):

Append data to payload, modifies size field in header.

- pop(length: int):

Iterates through payload and returns next unextracted **length** bytes (doesn't change the size or payload).
