#!/usr/bin/env python
"""VFS-related part of GRR API client library."""

import abc
from collections.abc import Sequence
from typing import Optional

from google.protobuf import message
from grr_api_client import context as api_context
from grr_api_client import utils
from grr_response_proto.api import vfs_pb2


class FileOperation(metaclass=abc.ABCMeta):
  """Base wrapper class for file operations."""

  # TODO(hanuszczak): This should be typed with a generic type parameter for a
  # state enum type. However, in the generated code, proto enums types are not
  # Python types and cannot be applied to types like `Generic` or `Optional`.
  @classmethod
  @abc.abstractmethod
  def RunningState(cls) -> int:
    raise NotImplementedError()

  # TODO(hanuszczak): See comment for `RunningState`.
  @classmethod
  @abc.abstractmethod
  def FinishedState(cls) -> int:
    raise NotImplementedError()

  def __init__(
      self,
      client_id: str,
      operation_id: str,
      target_file: "FileBase",
      context: api_context.GrrApiContext,
  ):
    super().__init__()

    if not client_id:
      raise ValueError("client_id can't be empty")

    if not operation_id:
      raise ValueError("operation_id can't be empty")

    if not target_file:
      raise ValueError("target_file can't be empty")

    self.client_id: str = client_id
    self.operation_id: str = operation_id
    self.target_file: FileBase = target_file
    self._context: api_context.GrrApiContext = context

  @abc.abstractmethod
  def GetState(self) -> int:
    raise NotImplementedError()

  def WaitUntilDone(
      self,
      timeout: Optional[int] = None,
  ) -> "FileOperation":
    """Wait until the operation is done.

    Args:
      timeout: timeout in seconds. None means default timeout (1 hour). 0 means
        no timeout (wait forever).

    Returns:
      Operation object with refreshed target_file.
    Raises:
      PollTimeoutError: if timeout is reached.
    """

    utils.Poll(
        generator=self.GetState,
        condition=lambda s: s != self.__class__.RunningState(),
        timeout=timeout,
    )
    self.target_file = self.target_file.Get()
    return self


class RefreshOperation(FileOperation):
  """Wrapper class for refresh operations."""

  # TODO(hanuszczak): These definitions are kept for backward compatibility and
  # should be removed after some grace period.
  STATE_RUNNING = vfs_pb2.ApiGetVfsRefreshOperationStateResult.RUNNING
  STATE_FINISHED = vfs_pb2.ApiGetVfsRefreshOperationStateResult.FINISHED

  @classmethod
  def RunningState(cls) -> vfs_pb2.ApiGetVfsRefreshOperationStateResult.State:
    return vfs_pb2.ApiGetVfsRefreshOperationStateResult.RUNNING

  @classmethod
  def FinishedState(cls) -> vfs_pb2.ApiGetVfsRefreshOperationStateResult.State:
    return vfs_pb2.ApiGetVfsRefreshOperationStateResult.FINISHED

  def GetState(self) -> vfs_pb2.ApiGetVfsRefreshOperationStateResult.State:
    args = vfs_pb2.ApiGetVfsRefreshOperationStateArgs(
        client_id=self.client_id, operation_id=self.operation_id
    )

    response = self._context.SendRequest("GetVfsRefreshOperationState", args)
    if not isinstance(response, vfs_pb2.ApiGetVfsRefreshOperationStateResult):
      raise TypeError(f"Unexpected response type: {type(response)}")

    return response.state


class CollectOperation(FileOperation):
  """Wrapper class for collect operations."""

  # TODO(hanuszczak): These definitions are kept for backward compatibility and
  # should be removed after some grace period.
  STATE_RUNNING = vfs_pb2.ApiGetVfsFileContentUpdateStateResult.RUNNING
  STATE_FINISHED = vfs_pb2.ApiGetVfsFileContentUpdateStateResult.FINISHED

  @classmethod
  def RunningState(cls) -> vfs_pb2.ApiGetVfsFileContentUpdateStateResult.State:
    return vfs_pb2.ApiGetVfsFileContentUpdateStateResult.RUNNING

  @classmethod
  def FinishedState(cls) -> vfs_pb2.ApiGetVfsFileContentUpdateStateResult.State:
    return vfs_pb2.ApiGetVfsFileContentUpdateStateResult.FINISHED

  def GetState(self) -> vfs_pb2.ApiGetVfsFileContentUpdateStateResult.State:
    args = vfs_pb2.ApiGetVfsFileContentUpdateStateArgs(
        client_id=self.client_id, operation_id=self.operation_id
    )

    response = self._context.SendRequest("GetVfsFileContentUpdateState", args)
    if not isinstance(response, vfs_pb2.ApiGetVfsFileContentUpdateStateResult):
      raise TypeError(f"Unexpected response type: {type(response)}")

    return response.state


class FileBase(object):
  """Base class for FlowRef and Flow."""

  def __init__(
      self,
      client_id: str,
      path: str,
      context: api_context.GrrApiContext,
  ):
    super().__init__()

    if not client_id:
      raise ValueError("client_id can't be empty")

    if not path:
      raise ValueError("path can't be empty")

    self.client_id: str = client_id
    self.path: str = path
    self._context: api_context.GrrApiContext = context

  def GetBlob(
      self,
      timestamp: Optional[int] = None,
  ) -> utils.BinaryChunkIterator:
    args = vfs_pb2.ApiGetFileBlobArgs(
        client_id=self.client_id, file_path=self.path
    )
    if timestamp is not None:
      args.timestamp = timestamp
    return self._context.SendStreamingRequest("GetFileBlob", args)

  def GetBlobWithOffset(
      self,
      offset: int,
      timestamp: Optional[int] = None,
  ) -> utils.BinaryChunkIterator:
    args = vfs_pb2.ApiGetFileBlobArgs(
        client_id=self.client_id, file_path=self.path, offset=offset
    )
    if timestamp is not None:
      args.timestamp = timestamp
    return self._context.SendStreamingRequest("GetFileBlob", args)

  def ListFiles(self) -> utils.ItemsIterator["File"]:
    """Lists files under the directory."""
    args = vfs_pb2.ApiListFilesArgs(
        client_id=self.client_id, file_path=self.path
    )
    items = self._context.SendIteratorRequest("ListFiles", args)

    def MapDataToFile(data: message.Message) -> "File":
      if not isinstance(data, vfs_pb2.ApiFile):
        raise TypeError(f"Unexpected response type: {type(data)}")

      return File(client_id=self.client_id, data=data, context=self._context)

    return utils.MapItemsIterator(MapDataToFile, items)

  def GetFilesArchive(self) -> utils.BinaryChunkIterator:
    args = vfs_pb2.ApiGetVfsFilesArchiveArgs(
        client_id=self.client_id, file_path=self.path
    )
    return self._context.SendStreamingRequest("GetVfsFilesArchive", args)

  def GetVersionTimes(self) -> Sequence[int]:
    args = vfs_pb2.ApiGetFileVersionTimesArgs(
        client_id=self.client_id, file_path=self.path
    )

    result = self._context.SendRequest("GetFileVersionTimes", args)
    if not isinstance(result, vfs_pb2.ApiGetFileVersionTimesResult):
      raise TypeError(f"Unexpected result type: {type(result)}")

    return result.times

  def Refresh(self) -> RefreshOperation:
    args = vfs_pb2.ApiCreateVfsRefreshOperationArgs(
        client_id=self.client_id, file_path=self.path
    )

    result = self._context.SendRequest("CreateVfsRefreshOperation", args)
    if not isinstance(result, vfs_pb2.ApiCreateVfsRefreshOperationResult):
      raise TypeError(f"Unexpected result type: {type(result)}")

    return RefreshOperation(
        client_id=self.client_id,
        operation_id=result.operation_id,
        target_file=self,
        context=self._context,
    )

  def RefreshRecursively(self, max_depth: int = 5) -> RefreshOperation:
    args = vfs_pb2.ApiCreateVfsRefreshOperationArgs(
        client_id=self.client_id, file_path=self.path, max_depth=max_depth
    )

    result = self._context.SendRequest("CreateVfsRefreshOperation", args)
    if not isinstance(result, vfs_pb2.ApiCreateVfsRefreshOperationResult):
      raise TypeError(f"Unexpected result type: {type(result)}")

    return RefreshOperation(
        client_id=self.client_id,
        operation_id=result.operation_id,
        target_file=self,
        context=self._context,
    )

  def Collect(self) -> "CollectOperation":
    args = vfs_pb2.ApiUpdateVfsFileContentArgs(
        client_id=self.client_id, file_path=self.path
    )

    result = self._context.SendRequest("UpdateVfsFileContent", args)
    if not isinstance(result, vfs_pb2.ApiUpdateVfsFileContentResult):
      raise TypeError(f"Unexpected result type: {type(result)}")

    return CollectOperation(
        client_id=self.client_id,
        operation_id=result.operation_id,
        target_file=self,
        context=self._context,
    )

  def GetTimeline(self) -> Sequence[vfs_pb2.ApiVfsTimelineItem]:
    args = vfs_pb2.ApiGetVfsTimelineArgs(
        client_id=self.client_id, file_path=self.path
    )

    result = self._context.SendRequest("GetVfsTimeline", args)
    if not isinstance(result, vfs_pb2.ApiGetVfsTimelineResult):
      raise TypeError(f"Unexpected result type: {type(result)}")

    return result.items

  def GetTimelineAsCsv(self) -> utils.BinaryChunkIterator:
    args = vfs_pb2.ApiGetVfsTimelineAsCsvArgs(
        client_id=self.client_id, file_path=self.path
    )
    return self._context.SendStreamingRequest("GetVfsTimelineAsCsv", args)

  def Get(self) -> "File":
    """Fetch file's data and return proper File object."""

    args = vfs_pb2.ApiGetFileDetailsArgs(
        client_id=self.client_id, file_path=self.path
    )

    data = self._context.SendRequest("GetFileDetails", args)
    if not isinstance(data, vfs_pb2.ApiGetFileDetailsResult):
      raise TypeError(f"Unexpected result type: {type(data)}")

    return File(client_id=self.client_id, data=data.file, context=self._context)


class FileRef(FileBase):
  """File reference (points to a file, but has no data)."""


class File(FileBase):
  """File object with fetched data."""

  def __init__(
      self,
      client_id: str,
      data: vfs_pb2.ApiFile,
      context: api_context.GrrApiContext,
  ):
    super().__init__(client_id=client_id, path=data.path, context=context)

    self.data: vfs_pb2.ApiFile = data

  @property
  def is_directory(self) -> bool:
    return self.data.is_directory
