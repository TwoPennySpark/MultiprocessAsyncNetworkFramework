from __future__ import annotations
from typing import Protocol, Coroutine
from contextlib import suppress
from enum import Enum, auto

import socket
import asyncio

from netframe.message import Message, OwnedMessage


class ConnOwner(Protocol):
    '''Connection owner - ServerWorker or ClientWorker'''

    # called when a new message is received
    def process_msg(self, msg: OwnedMessage):
        pass

    # called when connection is lost either due to a network 
    # error or graceful TCP shutdown initiated by other party
    # isn't called when shutdown is initiated by owner 
    def process_disconnect(self, conn: Connection):
        pass


class Connection:
    '''
    Represents TCP connection. Provides means for sending, 
    receiving data and closing the connection.
    '''

    def __init__(self,
                 reader: asyncio.StreamReader, 
                 writer: asyncio.StreamWriter, 
                 owner: ConnOwner):
        self._reader = reader
        self._writer = writer
        self._owner = owner
        
        self.isActive = True

        self._tasks: set[asyncio.Task] = set()


    async def _recv(self):
        msg = OwnedMessage(owner=self)

        try:
            hdrBytes = await self._reader.readexactly(Message.Header.HEADER_LEN)
            msg.msg.hdr.unpack(hdrBytes)

            msg.msg.payload = bytearray(await self._reader.readexactly(msg.msg.hdr.size))            
        except asyncio.CancelledError:
            return
        except (asyncio.IncompleteReadError, ConnectionResetError, ConnectionAbortedError):
            self._shutdown(self.SHUTDOWN_REASON.CONNECTION_BREAKUP)
            return

        self.recv()
        self._owner.process_msg(msg)

    
    async def _send(self, msg: Message):
        try:
            self._writer.write(msg.pack())
            await self._writer.drain()
        except asyncio.CancelledError:
            return
        except (ConnectionResetError, ConnectionAbortedError):
            self._shutdown(self.SHUTDOWN_REASON.CONNECTION_BREAKUP)

    
    class SHUTDOWN_REASON(Enum):
        # owner initiated shutdown
        MANUAL = auto() 
        # a network error occured or peer has closed the connection
        CONNECTION_BREAKUP = auto()


    def _shutdown(self, reason: SHUTDOWN_REASON):
        tasksToCancel = [t for t in self._tasks 
                        if t is not asyncio.current_task()]
        # do not cancel scheduled send tasks in case of manual shutdown
        if reason == self.SHUTDOWN_REASON.MANUAL:
            tasksToCancel = [t for t in tasksToCancel
                            if t.get_name() != self._send.__name__]
        for task in tasksToCancel:
            task.cancel()

        self._schedule(self._ashutdown(reason))
        self.isActive = False
        

    async def _ashutdown(self, reason: SHUTDOWN_REASON):
        allTasks = [t for t in self._tasks if t is not asyncio.current_task()]
        if len(allTasks):
            await asyncio.wait(allTasks)
        
        # when using TCP, if we schedule some msgs to be sent and then close the
        # connection immediately, those scheduled msgs may not be fully delivered if 
        # there is some pending readable data left on the socket
        # to prevent this, we issue a shutdown and drain the recv buffer
        # https://blog.netherlabs.nl/articles/2009/01/18/the-ultimate-so_linger-page-or-why-is-my-tcp-not-reliable  
        if reason == self.SHUTDOWN_REASON.MANUAL:
            sock = self._writer.get_extra_info('socket')
            sock.shutdown(socket.SHUT_WR)
            while True:
                try:
                    msg = await self._reader.read(1024)
                    if msg == b'':
                        break
                except:
                    break

        self._writer.close()
        with suppress(ConnectionResetError, ConnectionAbortedError):
            await self._writer.wait_closed()

        if reason == self.SHUTDOWN_REASON.CONNECTION_BREAKUP:
            self._owner.process_disconnect(self)

    
    def _schedule(self, coro: Coroutine):
        if not self.isActive:
            return

        task = asyncio.create_task(coro, name=coro.__name__)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)


    def send(self, msg: Message):
        self._schedule(self._send(msg))


    def recv(self):
        self._schedule(self._recv())


    def shutdown(self):
        self._shutdown(self.SHUTDOWN_REASON.MANUAL)


    def addr(self) -> tuple[str, int]:
        return self._writer.get_extra_info('peername')