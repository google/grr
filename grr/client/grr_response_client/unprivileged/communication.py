#!/usr/bin/env python
"""Communication protocol with unprivileged servers."""

import abc
import contextlib
import os
import platform
import struct
import subprocess
from typing import NamedTuple, Callable, Optional, List, BinaryIO


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


_HEADER_STRUCT = struct.Struct("<LL")


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
      data = b""
    if attachment_len > 0:
      attachment = self._transport.RecvBytes(attachment_len)
    else:
      attachment = b""
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


ConnectionHandler = Callable[[Connection], None]


class Channel(NamedTuple):
  """File descriptors / handle sused for communication."""

  pipe_input: Optional[int] = None
  """Pipe used for input (client to server).

  This is a file descriptor on UNIX, a handle on Windows.
  """

  pipe_output: Optional[int] = None
  """Pipe used for output (server to client).

  This is a file descriptor on UNIX, a handle on Windows.
  """


ArgsFactory = Callable[[Channel], List[str]]


class PipeTransport(Transport):
  """A low-level transport protocol based on a pair of pipes."""

  def __init__(self, read_pipe: BinaryIO, write_pipe: BinaryIO):
    self._read_pipe = read_pipe
    self._write_pipe = write_pipe

  def SendBytes(self, data: bytes) -> None:
    self._write_pipe.write(data)

  def RecvBytes(self, size: int) -> bytes:
    return self._read_pipe.read(size)


class SubprocessServer(Server):
  """A server running as a subprocess.

  A pair of pipes is created and shared with the subprocess as communication
  channel.
  """

  def __init__(self, args_factory: ArgsFactory):
    """Constructor.

    Args:
      args_factory: Function which takes a channel and returns
        the args to run the server subprocess (as required by subprocess.Popen).
    """
    self._args_factory = args_factory
    self._process = None  # type: Optional[subprocess.Popen]
    # Omiting type, since the type is conditionally imported on Windows.
    self._process_win = None
    self._output_r = None  # type: Optional[BinaryIO]
    self._input_w = None  # type: Optional[BinaryIO]

  def Start(self) -> None:
    with contextlib.ExitStack() as stack:
      input_r_fd, input_w_fd = os.pipe()
      stack.callback(os.close, input_r_fd)
      self._input_w = os.fdopen(input_w_fd, "wb", buffering=0)

      output_r_fd, output_w_fd = os.pipe()
      stack.callback(os.close, output_w_fd)
      self._output_r = os.fdopen(output_r_fd, "rb", buffering=0)

      if platform.system() == "Windows":
        # pylint: disable=g-import-not-at-top
        import msvcrt
        from grr_response_client.unprivileged.windows import process  # pytype: disable=import-error
        # pylint: enable=g-import-not-at-top
        # pytype doesn't see the functions in msvcrt
        # pytype: disable=module-attr
        input_r_handle = msvcrt.get_osfhandle(input_r_fd)
        output_w_handle = msvcrt.get_osfhandle(output_w_fd)
        # pytype: enable=module-attr
        args = self._args_factory(
            Channel(pipe_input=input_r_handle, pipe_output=output_w_handle))
        self._process_win = process.Process(args, [input_r_fd, output_w_fd])
      else:
        args = self._args_factory(
            Channel(pipe_input=input_r_fd, pipe_output=output_w_fd))
        self._process = subprocess.Popen(
            args,
            close_fds=True,
            pass_fds=[input_r_fd, output_w_fd],
        )

  def Stop(self) -> None:
    if self._process is not None:
      self._process.kill()
      self._process.wait()
    if self._process_win is not None:
      self._process_win.Stop()
    if self._input_w is not None:
      self._input_w.close()
    if self._output_r is not None:
      self._output_r.close()

  def Connect(self) -> Connection:
    transport = PipeTransport(self._output_r, self._input_w)
    return Connection(transport)


def Main(channel: Channel, connection_handler: ConnectionHandler) -> None:
  """The entry point of the server process.

  Args:
    channel: Channel connected to the client.
    connection_handler: Connection handler for processing the connection.
  """
  if platform.system() == "Windows":
    import msvcrt  # pylint: disable=g-import-not-at-top
    # pytype doesn't see the functions in mscvcrt
    # pytype: disable=module-attr
    channel = Channel(
        pipe_input=msvcrt.open_osfhandle(channel.pipe_input, os.O_RDONLY),
        pipe_output=msvcrt.open_osfhandle(channel.pipe_output, os.O_APPEND))
    # pytype: enable=module-attr
  with os.fdopen(channel.pipe_input, "rb", buffering=False) as pipe_input:
    with os.fdopen(channel.pipe_output, "wb", buffering=False) as pipe_output:
      transport = PipeTransport(pipe_input, pipe_output)
      connection = Connection(transport)
      connection_handler(connection)
