#!/usr/bin/env python
"""VFS-related part of GRR API client library."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_api_client import utils
from grr_response_proto.api import vfs_pb2


class FileOperation(object):
  """Base wrapper class for file operations."""

  # States have to be defined by child classes.
  STATE_RUNNING = None
  STATE_FINISHED = None

  def __init__(self,
               client_id=None,
               operation_id=None,
               target_file=None,
               context=None):
    super(FileOperation, self).__init__()

    if not client_id:
      raise ValueError("client_id can't be empty")

    if not operation_id:
      raise ValueError("operation_id can't be empty")

    if not target_file:
      raise ValueError("target_file can't be empty")

    if not context:
      raise ValueError("context can't be empty")

    self.client_id = client_id
    self.operation_id = operation_id
    self.target_file = target_file
    self._context = context

  def GetState(self):
    raise NotImplementedError()

  def WaitUntilDone(self, timeout=None):
    """Wait until the operation is done.

    Args:
      timeout: timeout in seconds. None means default timeout (1 hour).
               0 means no timeout (wait forever).
    Returns:
      Operation object with refreshed target_file.
    Raises:
      PollTimeoutError: if timeout is reached.
    """

    utils.Poll(
        generator=self.GetState,
        condition=lambda s: s != self.__class__.STATE_RUNNING,
        timeout=timeout)
    self.target_file = self.target_file.Get()
    return self


class RefreshOperation(FileOperation):
  """Wrapper class for refresh operations."""

  STATE_RUNNING = vfs_pb2.ApiGetVfsRefreshOperationStateResult.RUNNING
  STATE_FINISHED = vfs_pb2.ApiGetVfsRefreshOperationStateResult.FINISHED

  def GetState(self):
    args = vfs_pb2.ApiGetVfsRefreshOperationStateArgs(
        client_id=self.client_id, operation_id=self.operation_id)
    return self._context.SendRequest("GetVfsRefreshOperationState", args).state


class CollectOperation(FileOperation):
  """Wrapper class for collect operations."""

  STATE_RUNNING = vfs_pb2.ApiGetVfsFileContentUpdateStateResult.RUNNING
  STATE_FINISHED = vfs_pb2.ApiGetVfsFileContentUpdateStateResult.FINISHED

  def GetState(self):
    args = vfs_pb2.ApiGetVfsFileContentUpdateStateArgs(
        client_id=self.client_id, operation_id=self.operation_id)
    return self._context.SendRequest("GetVfsFileContentUpdateState", args).state


class FileBase(object):
  """Base class for FlowRef and Flow."""

  def __init__(self, client_id=None, path=None, context=None):
    super(FileBase, self).__init__()

    if not client_id:
      raise ValueError("client_id can't be empty")

    if not path:
      raise ValueError("path can't be empty")

    if not context:
      raise ValueError("context can't be empty")

    self.client_id = client_id
    self.path = path
    self._context = context

  def GetBlob(self, timestamp=None):
    args = vfs_pb2.ApiGetFileBlobArgs(
        client_id=self.client_id, file_path=self.path)
    if timestamp:
      args.timestamp = timestamp
    return self._context.SendStreamingRequest("GetFileBlob", args)

  def ListFiles(self):
    args = vfs_pb2.ApiListFilesArgs(
        client_id=self.client_id, file_path=self.path)
    items = self._context.SendIteratorRequest("ListFiles", args)

    def MapDataToFile(data):
      return File(client_id=self.client_id, data=data, context=self._context)

    return utils.MapItemsIterator(MapDataToFile, items)

  def GetFilesArchive(self):
    args = vfs_pb2.ApiGetVfsFilesArchiveArgs(
        client_id=self.client_id, file_path=self.path)
    return self._context.SendStreamingRequest("GetVfsFilesArchive", args)

  def GetVersionTimes(self):
    args = vfs_pb2.ApiGetFileVersionTimesArgs(
        client_id=self.client_id, file_path=self.path)
    return self._context.SendRequest("GetFileVersionTimes", args).times

  def Refresh(self):
    args = vfs_pb2.ApiCreateVfsRefreshOperationArgs(
        client_id=self.client_id, file_path=self.path)
    result = self._context.SendRequest("CreateVfsRefreshOperation", args)
    return RefreshOperation(
        client_id=self.client_id,
        operation_id=result.operation_id,
        target_file=self,
        context=self._context)

  def Collect(self):
    args = vfs_pb2.ApiUpdateVfsFileContentArgs(
        client_id=self.client_id, file_path=self.path)
    result = self._context.SendRequest("UpdateVfsFileContent", args)
    return CollectOperation(
        client_id=self.client_id,
        operation_id=result.operation_id,
        target_file=self,
        context=self._context)

  def GetTimeline(self):
    args = vfs_pb2.ApiGetVfsTimelineArgs(
        client_id=self.client_id, file_path=self.path)
    return self._context.SendRequest("GetVfsTimeline", args).items

  def GetTimelineAsCsv(self):
    args = vfs_pb2.ApiGetVfsTimelineAsCsvArgs(
        client_id=self.client_id, file_path=self.path)
    return self._context.SendStreamingRequest("GetVfsTimelineAsCsv", args)

  def Get(self):
    """Fetch file's data and return proper File object."""

    args = vfs_pb2.ApiGetFileDetailsArgs(
        client_id=self.client_id, file_path=self.path)
    data = self._context.SendRequest("GetFileDetails", args).file
    return File(client_id=self.client_id, data=data, context=self._context)


class FileRef(FileBase):
  """File reference (points to a file, but has no data)."""


class File(FileBase):
  """File object with fetched data."""

  def __init__(self, client_id=None, data=None, context=None):
    if data is None:
      raise ValueError("data can't be None")

    super(File, self).__init__(
        client_id=client_id, path=data.path, context=context)

    self.data = data

  @property
  def is_directory(self):
    return self.data.is_directory
