#!/usr/bin/env python
"""Communication protocol with unprivileged servers."""

import abc
import contextlib
import enum
import os
import platform
import struct
import subprocess
from typing import NamedTuple, Callable, Optional, List, BinaryIO, Set
import psutil

from grr_response_client.unprivileged import sandbox


class Error(Exception):
  """Base class for exceptions in this module."""


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

  def __enter__(self) -> "Server":
    self.Start()
    return self

  def __exit__(self, exc_type, exc_value, traceback) -> None:
    self.Stop()


ConnectionHandler = Callable[[Connection], None]


class PipeTransport(Transport):
  """A low-level transport protocol based on a pair of pipes."""

  def __init__(self, read_pipe: BinaryIO, write_pipe: BinaryIO):
    self._read_pipe = read_pipe
    self._write_pipe = write_pipe

  def SendBytes(self, data: bytes) -> None:
    # A write to a pipe could write less data than requested.
    # It might be necessary to write multiple times to write all the data.
    while data:
      written = self._write_pipe.write(data)
      if written == 0:
        raise Error("Write to pipe returned 0 bytes.")
      data = data[written:]

  def RecvBytes(self, size: int) -> bytes:
    # A read from a pipe can return less data than requested.
    # It might be necessary to read multiple times to read the exact amount
    # of data requested.
    parts = []
    remaining = size
    while remaining > 0:
      part = self._read_pipe.read(remaining)
      if not part:
        raise Error("Read from pipe returned 0 bytes.")
      remaining -= len(part)
      parts.append(part)
    return b"".join(parts)


class Mode(enum.Enum):
  READ = 1
  WRITE = 2


class FileDescriptor:
  """Wraps a file descriptor or handle which can be passed to a process."""

  # For some reason the typechecker doesn't see the attributes being set
  # in __init__.
  _file_descriptor: Optional[int] = None
  _handle: Optional[int] = None
  _mode: Optional[Mode] = None

  def __init__(self,
               file_descriptor: Optional[int] = None,
               handle: Optional[int] = None,
               mode: Optional[Mode] = None):
    self._file_descriptor = file_descriptor
    self._handle = handle
    self._mode = mode

  def Serialize(self) -> int:
    """Serializes the file descriptor for passing to adifferent process."""
    if platform.system() == "Windows":
      return self.ToHandle()
    else:
      return self.ToFileDescriptor()

  def ToFileDescriptor(self) -> int:
    """Converts the value to a file descriptor."""
    if self._file_descriptor is not None:
      return self._file_descriptor

    if platform.system() == "Windows":
      import msvcrt  # pylint: disable=g-import-not-at-top
      if self._mode == Mode.READ:
        mode = os.O_RDONLY
      elif self._mode == Mode.WRITE:
        mode = os.O_APPEND
      else:
        raise ValueError(f"Invalid mode {self._mode}")
      if self._handle is None:
        raise ValueError("Handle is required.")
      # pytype doesn't see the functions in msvcrt
      self._file_descriptor = msvcrt.open_osfhandle(self._handle, mode)  # pytype: disable=module-attr
      # The file descriptor takes ownership of the handle.
      self._handle = None
      return self._file_descriptor
    else:
      raise ValueError("File descriptor is required.")

  def ToHandle(self) -> int:
    """Converts the value to a handle."""
    if self._handle is not None:
      return self._handle

    if platform.system() == "Windows":
      if self._file_descriptor is None:
        raise ValueError("File descriptor is required.")
      import msvcrt  # pylint: disable=g-import-not-at-top
      # pytype doesn't see the functions in msvcrt
      return msvcrt.get_osfhandle(self._file_descriptor)  # pytype: disable=module-attr
    else:
      raise ValueError("Handle is required.")

  @classmethod
  def FromFileDescriptor(cls, file_descriptor: int) -> "FileDescriptor":
    """Creates a value from a file descritor."""
    return FileDescriptor(file_descriptor=file_descriptor)

  @classmethod
  def FromHandle(cls, handle: int, mode: Mode) -> "FileDescriptor":
    """Creates a value from a handle."""
    return FileDescriptor(handle=handle, mode=mode)

  @classmethod
  def FromSerialized(cls, serialized: int, mode: Mode) -> "FileDescriptor":
    """Creates a value from a serialized value."""
    if platform.system() == "Windows":
      return cls.FromHandle(serialized, mode)
    else:
      return cls.FromFileDescriptor(serialized)


class Channel(NamedTuple):
  """File descriptors / handles used for communication."""

  pipe_input: Optional[FileDescriptor] = None
  """Pipe used for input (client to server).

  This is a file descriptor on UNIX, a handle on Windows.
  """

  pipe_output: Optional[FileDescriptor] = None
  """Pipe used for output (server to client).

  This is a file descriptor on UNIX, a handle on Windows.
  """

  @classmethod
  def FromSerialized(cls, pipe_input: int, pipe_output: int) -> "Channel":
    """Creates a channel from serialized pipe file descriptors."""
    return Channel(
        FileDescriptor.FromSerialized(pipe_input, Mode.READ),
        FileDescriptor.FromSerialized(pipe_output, Mode.WRITE))


ArgsFactory = Callable[[Channel], List[str]]


class SubprocessServer(Server):
  """A server running as a subprocess.

  A pair of pipes is created and shared with the subprocess as communication
  channel.
  """

  _past_instances_total_cpu_time = 0.0
  _past_instances_total_sys_time = 0.0

  _started_instances: Set["SubprocessServer"] = set()

  def __init__(self,
               args_factory: ArgsFactory,
               extra_file_descriptors: Optional[List[FileDescriptor]] = None):
    """Constructor.

    Args:
      args_factory: Function which takes a channel and returns the args to run
        the server subprocess (as required by subprocess.Popen).
      extra_file_descriptors: Extra file desctiptors to map to the subprocess.
    """
    self._args_factory = args_factory
    self._process = None  # type: Optional[subprocess.Popen]
    # Omitting type, since the type is conditionally imported on Windows.
    self._process_win = None
    self._output_r = None  # type: Optional[BinaryIO]
    self._input_w = None  # type: Optional[BinaryIO]
    if extra_file_descriptors is None:
      extra_file_descriptors = []
    self._extra_file_descriptors = extra_file_descriptors

  def Start(self) -> None:
    with contextlib.ExitStack() as stack:
      input_r_fd, input_w_fd = os.pipe()
      stack.callback(os.close, input_r_fd)
      self._input_w = os.fdopen(input_w_fd, "wb", buffering=0)

      output_r_fd, output_w_fd = os.pipe()
      stack.callback(os.close, output_w_fd)
      self._output_r = os.fdopen(output_r_fd, "rb", buffering=0)

      input_r_fd_obj = FileDescriptor.FromFileDescriptor(input_r_fd)
      output_w_fd_obj = FileDescriptor.FromFileDescriptor(output_w_fd)

      if platform.system() == "Windows":
        # pylint: disable=g-import-not-at-top
        from grr_response_client.unprivileged.windows import process  # pytype: disable=import-error
        # pylint: enable=g-import-not-at-top
        args = self._args_factory(
            Channel(pipe_input=input_r_fd_obj, pipe_output=output_w_fd_obj))
        extra_handles = [fd.ToHandle() for fd in self._extra_file_descriptors]
        self._process_win = process.Process(
            args, [input_r_fd_obj.ToHandle(),
                   output_w_fd_obj.ToHandle()] + extra_handles)
      else:
        args = self._args_factory(
            Channel(pipe_input=input_r_fd_obj, pipe_output=output_w_fd_obj))
        extra_fds = [
            fd.ToFileDescriptor() for fd in self._extra_file_descriptors
        ]
        self._process = subprocess.Popen(
            args,
            close_fds=True,
            pass_fds=[input_r_fd, output_w_fd] + extra_fds,
        )

    SubprocessServer._started_instances.add(self)

  def Stop(self) -> None:

    if self in self._started_instances:
      SubprocessServer._started_instances.remove(self)
      SubprocessServer._past_instances_total_cpu_time += self.cpu_time
      SubprocessServer._past_instances_total_sys_time += self.sys_time

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

  @classmethod
  def TotalCpuTime(cls) -> float:
    return SubprocessServer._past_instances_total_cpu_time + sum(
        [instance.cpu_time for instance in cls._started_instances])

  @classmethod
  def TotalSysTime(cls) -> float:
    return SubprocessServer._past_instances_total_sys_time + sum(
        [instance.sys_time for instance in cls._started_instances])

  @property
  def cpu_time(self) -> float:
    if self._process_win is not None:
      return self._process_win.GetCpuTimes().cpu_time
    return self._psutil_process.cpu_times().user  # pytype: disable=wrong-arg-count  # bind-properties

  @property
  def sys_time(self) -> float:
    if self._process_win is not None:
      return self._process_win.GetCpuTimes().sys_time
    return self._psutil_process.cpu_times().system  # pytype: disable=wrong-arg-count  # bind-properties

  @property
  def _psutil_process(self) -> psutil.Process:
    if self._process_win is not None:
      return psutil.Process(pid=self._process_win.pid)
    elif self._process is not None:
      return psutil.Process(pid=self._process.pid)
    else:
      raise ValueError("Can't determine process.")


def Main(channel: Channel, connection_handler: ConnectionHandler, user: str,
         group: str) -> None:
  """The entry point of the server process.

  Args:
    channel: Channel connected to the client.
    connection_handler: Connection handler for processing the connection.
    user: Unprivileged (UNIX) user to run as. If `""`, don't change user.
    group: Unprivileged (UNIX) group to run as. If `""`, don't change group.
  """
  sandbox.EnterSandbox(user, group)
  with os.fdopen(
      channel.pipe_input.ToFileDescriptor(), "rb",
      buffering=False) as pipe_input:
    with os.fdopen(
        channel.pipe_output.ToFileDescriptor(), "wb",
        buffering=False) as pipe_output:
      transport = PipeTransport(pipe_input, pipe_output)
      connection = Connection(transport)
      connection_handler(connection)


def TotalServerCpuTime() -> float:
  return SubprocessServer.TotalCpuTime()


def TotalServerSysTime() -> float:
  return SubprocessServer.TotalSysTime()
