#!/usr/bin/env python
"""Unprivileged filesystem RPC server."""

import abc
import os
import sys
import traceback
from typing import TypeVar, Generic, Optional, Tuple
from grr_response_client.unprivileged import communication
from grr_response_client.unprivileged.filesystem import filesystem
from grr_response_client.unprivileged.filesystem import ntfs
from grr_response_client.unprivileged.filesystem import tsk
from grr_response_client.unprivileged.proto import filesystem_pb2


class Error(Exception):
  """Base class for exceptions in this module."""
  pass


class DispatchError(Error):
  """Error while dispatching a request."""
  pass


class State:
  """State of the filesystem RPC server.

  Contains open files and filesystems.
  """

  def __init__(self):
    self.filesystem = None  # type: Optional[filesystem.Filesystem]
    self.files = filesystem.Files()


class ConnectionWrapper:
  """Wraps a connection, adding protobuf serialization."""

  def __init__(self, connection: communication.Connection):
    self._connection = connection

  def Send(self, response: filesystem_pb2.Response, attachment: bytes) -> None:
    self._connection.Send(
        communication.Message(response.SerializeToString(), attachment))

  def Recv(self) -> Tuple[filesystem_pb2.Request, bytes]:
    raw_request, attachment = self._connection.Recv()
    request = filesystem_pb2.Request()
    request.ParseFromString(raw_request)
    return request, attachment


class RpcDevice(filesystem.Device):
  """A device implementation which reads data blocks via a connection."""

  def __init__(self, connection: ConnectionWrapper):
    self._connection = connection

  def Read(self, offset: int, size: int) -> bytes:
    device_data_request = filesystem_pb2.DeviceDataRequest(
        offset=offset, size=size)
    self._connection.Send(
        filesystem_pb2.Response(device_data_request=device_data_request), b'')
    _, attachment = self._connection.Recv()
    return attachment


class FileDevice(filesystem.Device):
  """A device implementation backed by a file identified by file descriptor."""

  def __init__(self, file_descriptor: int):
    self._file = os.fdopen(file_descriptor, 'rb')

  def Read(self, offset: int, size: int) -> bytes:
    self._file.seek(offset)
    return self._file.read(size)


RequestType = TypeVar('RequestType')
ResponseType = TypeVar('ResponseType')


class OperationHandler(abc.ABC, Generic[RequestType, ResponseType]):
  """Base class for RPC handlers.

  The purpose is to handles the DeviceDataRequest/DeviceData messages
  common to most RPCs.
  """

  def __init__(self, state: State, request: filesystem_pb2.Request,
               connection: ConnectionWrapper):
    self._state = state
    self._request = request
    self._connection = connection

  def Run(self) -> None:
    request = self.UnpackRequest(self._request)
    response = self.HandleOperation(self._state, request)
    attachment = self.ExtractResponseAttachment(response)
    self._connection.Send(self.PackResponse(response), attachment)

  def CreateDevice(self) -> filesystem.Device:
    return RpcDevice(self._connection)

  @abc.abstractmethod
  def HandleOperation(self, state: State, request: RequestType) -> ResponseType:
    """The actual implementation of the RPC."""
    pass

  @abc.abstractmethod
  def PackResponse(self, response: ResponseType) -> filesystem_pb2.Response:
    """Packs an inner Response message into a response RPC message."""
    pass

  @abc.abstractmethod
  def UnpackRequest(self, request: filesystem_pb2.Request) -> RequestType:
    """Extracts an inner Request message from a Request RPC message."""
    pass

  def ExtractResponseAttachment(self, response: ResponseType) -> bytes:
    """Extracts and clears an attachment from the response."""
    return b''


class InitHandler(OperationHandler[filesystem_pb2.InitRequest,
                                   filesystem_pb2.InitResponse]):
  """Implements the Init operation."""

  def HandleOperation(
      self, state: State,
      request: filesystem_pb2.InitRequest) -> filesystem_pb2.InitResponse:
    if request.HasField('serialized_device_file_descriptor'):
      device = FileDevice(
          communication.FileDescriptor.FromSerialized(
              request.serialized_device_file_descriptor,
              communication.Mode.READ).ToFileDescriptor())
    else:
      device = self.CreateDevice()

    if request.implementation_type == filesystem_pb2.NTFS:
      state.filesystem = ntfs.NtfsFilesystem(device)
    elif request.implementation_type == filesystem_pb2.TSK:
      state.filesystem = tsk.TskFilesystem(device)
    else:
      raise DispatchError(
          f'Bad implementation type: {request.implementation_type}')

    return filesystem_pb2.InitResponse()

  def PackResponse(
      self, response: filesystem_pb2.InitResponse) -> filesystem_pb2.Response:
    return filesystem_pb2.Response(init_response=response)

  def UnpackRequest(
      self, request: filesystem_pb2.Request) -> filesystem_pb2.InitRequest:
    return request.init_request


class OpenHandler(OperationHandler[filesystem_pb2.OpenRequest,
                                   filesystem_pb2.OpenResponse]):
  """Implements the Open operation."""

  def HandleOperation(
      self, state: State,
      request: filesystem_pb2.OpenRequest) -> filesystem_pb2.OpenResponse:
    path = request.path if request.HasField('path') else None
    inode = request.inode if request.HasField('inode') else None
    stream_name = request.stream_name if request.HasField(
        'stream_name') else None
    if inode is None:
      file_obj = state.filesystem.Open(path, stream_name)
    else:
      try:
        file_obj = state.filesystem.OpenByInode(inode, stream_name)
      except filesystem.StaleInodeError:
        return filesystem_pb2.OpenResponse(
            status=filesystem_pb2.OpenResponse.Status.STALE_INODE)
    file_id = state.files.Add(file_obj)
    return filesystem_pb2.OpenResponse(
        status=filesystem_pb2.OpenResponse.Status.NO_ERROR,
        file_id=file_id,
        inode=file_obj.Inode())

  def PackResponse(
      self, response: filesystem_pb2.OpenResponse) -> filesystem_pb2.Response:
    return filesystem_pb2.Response(open_response=response)

  def UnpackRequest(
      self, request: filesystem_pb2.Request) -> filesystem_pb2.OpenRequest:
    return request.open_request


class ReadHandler(OperationHandler[filesystem_pb2.ReadRequest,
                                   filesystem_pb2.ReadResponse]):
  """Implements the Read operation."""

  def HandleOperation(
      self, state: State,
      request: filesystem_pb2.ReadRequest) -> filesystem_pb2.ReadResponse:
    file = state.files.Get(request.file_id)
    data = file.Read(offset=request.offset, size=request.size)
    return filesystem_pb2.ReadResponse(data=data)

  def PackResponse(
      self, response: filesystem_pb2.ReadResponse) -> filesystem_pb2.Response:
    return filesystem_pb2.Response(read_response=response)

  def ExtractResponseAttachment(self,
                                response: filesystem_pb2.ReadResponse) -> bytes:
    attachment = response.data
    response.ClearField('data')
    return attachment

  def UnpackRequest(
      self, request: filesystem_pb2.Request) -> filesystem_pb2.ReadRequest:
    return request.read_request


class StatHandler(OperationHandler[filesystem_pb2.StatRequest,
                                   filesystem_pb2.StatResponse]):
  """Implements the Stat operation."""

  def HandleOperation(
      self, state: State,
      request: filesystem_pb2.StatRequest) -> filesystem_pb2.StatResponse:
    file_obj = state.files.Get(request.file_id)
    return filesystem_pb2.StatResponse(entry=file_obj.Stat())

  def PackResponse(
      self, response: filesystem_pb2.StatResponse) -> filesystem_pb2.Response:
    return filesystem_pb2.Response(stat_response=response)

  def UnpackRequest(
      self, request: filesystem_pb2.Request) -> filesystem_pb2.StatRequest:
    return request.stat_request


class ListFilesHandler(OperationHandler[filesystem_pb2.ListFilesRequest,
                                        filesystem_pb2.ListFilesResponse]):
  """Implements the ListFiles operation."""

  def HandleOperation(
      self, state: State, request: filesystem_pb2.ListFilesRequest
  ) -> filesystem_pb2.ListFilesResponse:
    file_obj = state.files.Get(request.file_id)
    return filesystem_pb2.ListFilesResponse(entries=file_obj.ListFiles())

  def PackResponse(
      self,
      response: filesystem_pb2.ListFilesResponse) -> filesystem_pb2.Response:
    return filesystem_pb2.Response(list_files_response=response)

  def UnpackRequest(
      self, request: filesystem_pb2.Request) -> filesystem_pb2.ListFilesRequest:
    return request.list_files_request


class ListNamesHandler(OperationHandler[filesystem_pb2.ListNamesRequest,
                                        filesystem_pb2.ListNamesResponse]):
  """Implements the ListNames operation."""

  def HandleOperation(
      self, state: State, request: filesystem_pb2.ListNamesRequest
  ) -> filesystem_pb2.ListNamesResponse:
    file_obj = state.files.Get(request.file_id)
    return filesystem_pb2.ListNamesResponse(names=file_obj.ListNames())

  def PackResponse(
      self,
      response: filesystem_pb2.ListNamesResponse) -> filesystem_pb2.Response:
    return filesystem_pb2.Response(list_names_response=response)

  def UnpackRequest(
      self, request: filesystem_pb2.Request) -> filesystem_pb2.ListNamesRequest:
    return request.list_names_request


class CloseHandler(OperationHandler[filesystem_pb2.CloseRequest,
                                    filesystem_pb2.CloseResponse]):
  """Implements the Close operation."""

  def HandleOperation(
      self, state: State,
      request: filesystem_pb2.CloseRequest) -> filesystem_pb2.CloseResponse:
    file_obj = state.files.Get(request.file_id)
    file_obj.Close()
    state.files.Remove(request.file_id)
    return filesystem_pb2.CloseResponse()

  def PackResponse(
      self, response: filesystem_pb2.CloseResponse) -> filesystem_pb2.Response:
    return filesystem_pb2.Response(close_response=response)

  def UnpackRequest(
      self, request: filesystem_pb2.Request) -> filesystem_pb2.CloseRequest:
    return request.close_request


class LookupCaseInsensitiveHandler(
    OperationHandler[filesystem_pb2.LookupCaseInsensitiveRequest,
                     filesystem_pb2.LookupCaseInsensitiveResponse]):
  """Implements the LookupCaseInsensitive operation."""

  def HandleOperation(
      self, state: State, request: filesystem_pb2.LookupCaseInsensitiveRequest
  ) -> filesystem_pb2.LookupCaseInsensitiveResponse:
    file_obj = state.files.Get(request.file_id)
    result = file_obj.LookupCaseInsensitive(request.name)
    return filesystem_pb2.LookupCaseInsensitiveResponse(name=result)

  def PackResponse(
      self, response: filesystem_pb2.LookupCaseInsensitiveResponse
  ) -> filesystem_pb2.Response:
    return filesystem_pb2.Response(lookup_case_insensitive_response=response)

  def UnpackRequest(
      self, request: filesystem_pb2.Request
  ) -> filesystem_pb2.LookupCaseInsensitiveRequest:
    return request.lookup_case_insensitive_request


def DispatchWrapped(connection: ConnectionWrapper) -> None:
  """Dispatches a request to the proper OperationHandler."""
  state = State()
  while True:
    try:
      request, att = connection.Recv()

      if state.filesystem is None and not request.HasField('init_request'):
        raise DispatchError('The first request must be Init')

      if state.filesystem is not None and request.HasField('init_request'):
        raise DispatchError('Init can be called only once on a connection')

      if request.HasField('init_request'):
        handler_class = InitHandler
      elif request.HasField('open_request'):
        handler_class = OpenHandler
      elif request.HasField('read_request'):
        handler_class = ReadHandler
      elif request.HasField('close_request'):
        handler_class = CloseHandler
      elif request.HasField('stat_request'):
        handler_class = StatHandler
      elif request.HasField('list_files_request'):
        handler_class = ListFilesHandler
      elif request.HasField('lookup_case_insensitive_request'):
        handler_class = LookupCaseInsensitiveHandler
      elif request.HasField('list_names_request'):
        handler_class = ListNamesHandler
      else:
        raise DispatchError('No request set.')

      handler = handler_class(state, request, connection)
      handler.Run()
    except:  # pylint: disable=bare-except
      exception = filesystem_pb2.Exception(
          message=str(sys.exc_info()[1]),
          formatted_exception=traceback.format_exc())
      connection.Send(filesystem_pb2.Response(exception=exception), b'')


def Dispatch(connection: communication.Connection):
  DispatchWrapped(ConnectionWrapper(connection))
