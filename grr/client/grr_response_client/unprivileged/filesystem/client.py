#!/usr/bin/env python
"""Unprivileged filesystem RPC client code."""

import abc
from typing import TypeVar, Generic, Optional, Sequence, BinaryIO, Tuple

from grr_response_client.unprivileged import communication
from grr_response_client.unprivileged.proto import filesystem_pb2

RequestType = TypeVar('RequestType')
ResponseType = TypeVar('ResponseType')


class Error(Exception):
  """Base class for exceptions in this module."""
  pass


class OperationError(Exception):
  """Error while executing the operation."""

  def __init__(self, message: str, formatted_exception: str):
    """Constructor.

    Args:
      message: the exception message
      formatted_exception: the remote exception formatted using
        traceback.format_exc()
    """
    super().__init__(message)
    self.formatted_exception = formatted_exception


class ConnectionWrapper:
  """Wraps a connection, adding protobuf serialization of messages."""

  def __init__(self, connection: communication.Connection):
    self._connection = connection

  def Send(self, request: filesystem_pb2.Request, attachment: bytes) -> None:
    self._connection.Send(
        communication.Message(request.SerializeToString(), attachment))

  def Recv(self) -> Tuple[filesystem_pb2.Response, bytes]:
    raw_response, attachment = self._connection.Recv()
    response = filesystem_pb2.Response()
    response.ParseFromString(raw_response)
    return response, attachment


class Device(abc.ABC):
  """A device underlying a filesystem."""

  @abc.abstractmethod
  def Read(self, offset: int, size: int) -> bytes:
    """Reads from the device."""
    pass

  @property
  @abc.abstractmethod
  def file_descriptor(self) -> Optional[int]:
    """Returns the file descriptor for the device.

    Returns None, if this device is not backed by a regular file.
    """
    pass


class FileDevice(Device):
  """A device implementation backed by a python file."""

  def __init__(self, file_obj: BinaryIO):
    super().__init__()
    self._file = file_obj

  def Read(self, offset: int, size: int) -> bytes:
    self._file.seek(offset)
    return self._file.read(size)

  @property
  def file_descriptor(self) -> Optional[int]:
    return self._file.fileno()


class OperationHandler(abc.ABC, Generic[RequestType, ResponseType]):
  """Base class for RPC handlers.

  The purpose is to handle the DeviceDataRequest/DeviceData messages
  common to most RPCs.
  """

  def __init__(self, connection: ConnectionWrapper, device: Device):
    self._connection = connection
    self._device = device

  def Run(self, request: RequestType) -> ResponseType:
    self._connection.Send(self.PackRequest(request), b'')

    while True:
      packed_response, attachment = self._connection.Recv()
      if packed_response.HasField('device_data_request'):
        device_data_request = packed_response.device_data_request
        data = self._device.Read(device_data_request.offset,
                                 device_data_request.size)
        device_data = filesystem_pb2.DeviceData()
        request = filesystem_pb2.Request(device_data=device_data)
        self._connection.Send(request, data)
      elif packed_response.HasField('exception'):
        raise OperationError(packed_response.exception.message,
                             packed_response.exception.formatted_exception)
      else:
        response = self.UnpackResponse(packed_response)
        self.MergeResponseAttachment(response, attachment)
        return response

  def MergeResponseAttachment(self, response: ResponseType,
                              attachment: bytes) -> None:
    """Merges an attachment back into the response."""
    pass

  @abc.abstractmethod
  def UnpackResponse(self, response: filesystem_pb2.Response) -> ResponseType:
    """Extracts an inner Response message from a response message."""
    pass

  @abc.abstractmethod
  def PackRequest(self, request: RequestType) -> filesystem_pb2.Request:
    """Packs an inner Request message into a request message."""
    pass


class InitHandler(OperationHandler[filesystem_pb2.InitRequest,
                                   filesystem_pb2.InitResponse]):
  """Implements the Init RPC."""

  def UnpackResponse(
      self, response: filesystem_pb2.Response) -> filesystem_pb2.InitResponse:
    return response.init_response

  def PackRequest(
      self, request: filesystem_pb2.InitRequest) -> filesystem_pb2.Request:
    return filesystem_pb2.Request(init_request=request)


class OpenHandler(OperationHandler[filesystem_pb2.OpenRequest,
                                   filesystem_pb2.OpenResponse]):
  """Implements the Open RPC."""

  def UnpackResponse(
      self, response: filesystem_pb2.Response) -> filesystem_pb2.OpenResponse:
    return response.open_response

  def PackRequest(
      self, request: filesystem_pb2.OpenRequest) -> filesystem_pb2.Request:
    return filesystem_pb2.Request(open_request=request)


class ReadHandler(OperationHandler[filesystem_pb2.ReadRequest,
                                   filesystem_pb2.ReadResponse]):
  """Implements the Read RPC."""

  def UnpackResponse(
      self, response: filesystem_pb2.Response) -> filesystem_pb2.ReadResponse:
    return response.read_response

  def PackRequest(
      self, request: filesystem_pb2.ReadRequest) -> filesystem_pb2.Request:
    return filesystem_pb2.Request(read_request=request)

  def MergeResponseAttachment(self, response: filesystem_pb2.ReadResponse,
                              attachment: bytes) -> None:
    response.data = attachment


class StatHandler(OperationHandler[filesystem_pb2.StatRequest,
                                   filesystem_pb2.StatResponse]):
  """Implements the Stat RPC."""

  def UnpackResponse(
      self, response: filesystem_pb2.Response) -> filesystem_pb2.StatResponse:
    return response.stat_response

  def PackRequest(
      self, request: filesystem_pb2.StatRequest) -> filesystem_pb2.Request:
    return filesystem_pb2.Request(stat_request=request)


class ListFilesHandler(OperationHandler[filesystem_pb2.ListFilesRequest,
                                        filesystem_pb2.ListFilesResponse]):
  """Implements the ListFiles RPC."""

  def UnpackResponse(
      self,
      response: filesystem_pb2.Response) -> filesystem_pb2.ListFilesResponse:
    return response.list_files_response

  def PackRequest(
      self, request: filesystem_pb2.ListFilesRequest) -> filesystem_pb2.Request:
    return filesystem_pb2.Request(list_files_request=request)


class ListNamesHandler(OperationHandler[filesystem_pb2.ListNamesRequest,
                                        filesystem_pb2.ListNamesResponse]):
  """Implements the ListNames RPC."""

  def UnpackResponse(
      self,
      response: filesystem_pb2.Response) -> filesystem_pb2.ListNamesResponse:
    return response.list_names_response

  def PackRequest(
      self, request: filesystem_pb2.ListNamesRequest) -> filesystem_pb2.Request:
    return filesystem_pb2.Request(list_names_request=request)


class CloseHandler(OperationHandler[filesystem_pb2.CloseRequest,
                                    filesystem_pb2.CloseResponse]):
  """Implements the Close RPC."""

  def UnpackResponse(
      self, response: filesystem_pb2.Response) -> filesystem_pb2.CloseResponse:
    return response.close_response

  def PackRequest(
      self, request: filesystem_pb2.CloseRequest) -> filesystem_pb2.Request:
    return filesystem_pb2.Request(close_request=request)


class LookupCaseInsensitiveHandler(
    OperationHandler[filesystem_pb2.LookupCaseInsensitiveRequest,
                     filesystem_pb2.LookupCaseInsensitiveResponse]):
  """Implements the LookupCaseInsensitive RPC."""

  def UnpackResponse(
      self, response: filesystem_pb2.Response
  ) -> filesystem_pb2.LookupCaseInsensitiveResponse:
    return response.lookup_case_insensitive_response

  def PackRequest(
      self, request: filesystem_pb2.LookupCaseInsensitiveRequest
  ) -> filesystem_pb2.Request:
    return filesystem_pb2.Request(lookup_case_insensitive_request=request)


class File:
  """Wraps a remote file_id."""

  def __init__(self, connection: ConnectionWrapper, device: Device,
               file_id: int, inode: int):
    self._connection = connection
    self._device = device
    self._file_id = file_id
    self._inode = inode

  def Read(self, offset: int, size: int) -> bytes:
    request = filesystem_pb2.ReadRequest(
        file_id=self._file_id, offset=offset, size=size)
    response = ReadHandler(self._connection, self._device).Run(request)
    return response.data

  def Close(self) -> None:
    request = filesystem_pb2.CloseRequest(file_id=self._file_id)
    CloseHandler(self._connection, self._device).Run(request)

  def Stat(self) -> filesystem_pb2.StatEntry:
    request = filesystem_pb2.StatRequest(file_id=self._file_id)
    response = StatHandler(self._connection, self._device).Run(request)
    return response.entry

  def ListFiles(self) -> Sequence[filesystem_pb2.StatEntry]:
    request = filesystem_pb2.ListFilesRequest(file_id=self._file_id)
    response = ListFilesHandler(self._connection, self._device).Run(request)
    return list(response.entries)

  def ListNames(self) -> Sequence[str]:
    request = filesystem_pb2.ListNamesRequest(file_id=self._file_id)
    response = ListNamesHandler(self._connection, self._device).Run(request)
    return list(response.names)

  @property
  def inode(self) -> int:
    return self._inode

  def LookupCaseInsensitive(self, name: str) -> Optional[str]:
    request = filesystem_pb2.LookupCaseInsensitiveRequest(
        file_id=self._file_id, name=name)
    response = LookupCaseInsensitiveHandler(self._connection,
                                            self._device).Run(request)
    if response.HasField('name'):
      return response.name
    return None

  def __enter__(self) -> 'File':
    return self

  def __exit__(self, exc_type, exc_value, traceback) -> None:
    self.Close()


class StaleInodeError(Error):
  """The inode provided to open a file is stale / outdated."""
  pass


class Client:
  """Client for the RPC filesystem service."""

  def __init__(self, connection: communication.Connection,
               implementation_type: filesystem_pb2.ImplementationType,
               device: Device):
    self._connection = ConnectionWrapper(connection)
    self._device = device
    device_file_descriptor = device.file_descriptor
    if device_file_descriptor is None:
      serialized_device_file_descriptor = None
    else:
      serialized_device_file_descriptor = communication.FileDescriptor.FromFileDescriptor(
          device_file_descriptor).Serialize()
    request = filesystem_pb2.InitRequest(
        implementation_type=implementation_type,
        serialized_device_file_descriptor=serialized_device_file_descriptor)
    InitHandler(self._connection, self._device).Run(request)

  def __enter__(self) -> 'Client':
    return self

  def __exit__(self, exc_type, exc_value, traceback) -> None:
    self.Close()

  def Close(self):
    pass

  def Open(self,
           path: str,
           stream_name: Optional[str] = None) -> File:
    """Opens a file."""
    request = filesystem_pb2.OpenRequest(path=path, stream_name=stream_name)
    return self._Open(request)

  def OpenByInode(self,
                  inode: int,
                  stream_name: Optional[str] = None) -> File:
    """Opens a file by inode."""
    request = filesystem_pb2.OpenRequest(inode=inode, stream_name=stream_name)
    return self._Open(request)

  def _Open(self, request: filesystem_pb2.OpenRequest) -> File:
    response = OpenHandler(self._connection, self._device).Run(request)
    if response.status == filesystem_pb2.OpenResponse.Status.STALE_INODE:
      raise StaleInodeError()
    elif response.status != filesystem_pb2.OpenResponse.Status.NO_ERROR:
      raise IOError(f'Open RPC returned status {response.status}.')
    return File(self._connection, self._device, response.file_id,
                response.inode)


def CreateFilesystemClient(
    connection: communication.Connection,
    implementation_type: filesystem_pb2.ImplementationType,
    device: Device) -> Client:
  """Creates a filesystem client."""
  return Client(connection, implementation_type, device)
