#!/usr/bin/env python
"""Communication protocol with unprivileged servers."""

import abc
import socket
import struct
import subprocess
from typing import NamedTuple, Callable, Optional, List


class Transport(abc.ABC):
  """Low-level transport protocol."""

  @abc.abstractmethod
  def SendBytes(self, data: bytes) -> None:
    """Sends bytes atomically."""
    pass

  @abc.abstractmethod
  def RecvBytes(self, size: int) -> bytes:
    """Receives a fixed amount of bytes atomically."""
    pass


class Message(NamedTuple):
  """A message sent using a connection."""

  data: bytes
  """The main data contained in a message, usually a protobuf message."""

  attachment: bytes
  """Additional data contained in a message, usually just raw bytes."""


_HEADER_STRUCT = struct.Struct('<LL')


class Connection:
  """Connection between a client and a server.

  The connection:

  * is bi-directional.
  * makes it possible to send a message (bytes) and an attachment (bytes)
  * is implemented on top of a low-level `Transport`
  """

  def __init__(self, transport: Transport):
    self._transport = transport

  def Send(self, message: Message) -> None:
    """Sends a data message and an attachment."""
    header = _HEADER_STRUCT.pack(len(message.data), len(message.attachment))
    self._transport.SendBytes(header)
    if message.data:
      self._transport.SendBytes(message.data)
    if message.attachment:
      self._transport.SendBytes(message.attachment)

  def Recv(self) -> Message:
    """Receives a data message and an attachment."""
    header = self._transport.RecvBytes(_HEADER_STRUCT.size)
    data_len, attachment_len = _HEADER_STRUCT.unpack(header)
    if data_len > 0:
      data = self._transport.RecvBytes(data_len)
    else:
      data = b''
    if attachment_len > 0:
      attachment = self._transport.RecvBytes(attachment_len)
    else:
      attachment = b''
    return Message(data=data, attachment=attachment)


class Server(abc.ABC):
  """An unprivileged server."""

  @abc.abstractmethod
  def Start(self) -> None:
    """Starts the server."""
    pass

  @abc.abstractmethod
  def Stop(self) -> None:
    """Stops the server."""
    pass

  @abc.abstractmethod
  def Connect(self) -> Connection:
    """Returns a connection to the server."""
    pass


class SocketTransport(Transport):
  """A low-level transport protocol based on a socket."""

  def __init__(self, sock: socket.socket):
    self._socket = sock

  def SendBytes(self, data: bytes) -> None:
    self._socket.sendall(data)

  def RecvBytes(self, size: int) -> bytes:
    return self._socket.recv(size, socket.MSG_WAITALL)


ConnectionHandler = Callable[[Connection], None]

ArgsFactory = Callable[[int], List[str]]


class SubprocessServer(Server):
  """A server running as a subprocess.

  A socketpair is created and shared with the subprocess as communication
  channel.
  """

  def __init__(self, args_factory: ArgsFactory):
    """Constructor.

    Args:
      args_factory: Function which takes a socket file descriptor and returns
        the args to run the server subprocess (as required by subprocess.Popen).
    """
    self._args_factory = args_factory
    self._process = None  # type: Optional[subprocess.Popen]
    self._socket = None  # type: Optional[socket.socket]
    self._remote_socket = None  # type: Optional[socket.socket]

  def Start(self) -> None:
    self._socket, self._remote_socket = socket.socketpair()
    args = self._args_factory(self._remote_socket.fileno())
    self._process = subprocess.Popen(
        args,
        close_fds=True,
        pass_fds=[self._remote_socket.fileno()],
    )
    self._remote_socket.close()

  def Stop(self) -> None:
    self._process.kill()
    self._process.wait()
    self._socket.close()

  def Connect(self) -> Connection:
    transport = SocketTransport(self._socket)
    return Connection(transport)


def Main(socket_fd: int, connection_handler: ConnectionHandler) -> None:
  """The entry point of the server process.

  Args:
    socket_fd: Socket file descriptor connected to the client.
    connection_handler: Connection handler for processing the connection.
  """
  sock = socket.socket(fileno=socket_fd)
  transport = SocketTransport(sock)
  connection = Connection(transport)
  connection_handler(connection)
