#!/usr/bin/env python
"""VFS-related part of GRR API client library."""

from grr_api_client import utils
from grr.proto import api_pb2


class FileOperation(object):
  """Base wrapper class for file operations."""

  def __init__(self, client_id=None, operation_id=None, context=None):
    super(FileOperation, self).__init__()

    if not client_id:
      raise ValueError("client_id can't be empty")

    if not operation_id:
      raise ValueError("operation_id can't be empty")

    if not context:
      raise ValueError("context can't be empty")

    self.client_id = client_id
    self.operation_id = operation_id
    self._context = context

  def GetState(self):
    raise NotImplementedError()


class RefreshOperation(FileOperation):
  """Wrapper class for refresh operations."""

  STATE_RUNNING = api_pb2.ApiGetVfsRefreshOperationStateResult.RUNNING
  STATE_FINISHED = api_pb2.ApiGetVfsRefreshOperationStateResult.FINISHED

  def GetState(self):
    args = api_pb2.ApiGetVfsRefreshOperationStateArgs(
        client_id=self.client_id, operation_id=self.operation_id)
    return self._context.SendRequest("GetVfsRefreshOperationState", args).state


class CollectOperation(FileOperation):
  """Wrapper class for collect operations."""

  STATE_RUNNING = api_pb2.ApiGetVfsFileContentUpdateStateResult.RUNNING
  STATE_FINISHED = api_pb2.ApiGetVfsFileContentUpdateStateResult.FINISHED

  def GetState(self):
    args = api_pb2.ApiGetVfsFileContentUpdateStateArgs(
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
    args = api_pb2.ApiGetFileBlobArgs(
        client_id=self.client_id, file_path=self.path)
    if timestamp:
      args.timestamp = timestamp
    return self._context.SendStreamingRequest("GetFileBlob", args)

  def ListFiles(self):
    args = api_pb2.ApiListFilesArgs(
        client_id=self.client_id, file_path=self.path)
    items = self._context.SendIteratorRequest("ListFiles", args)

    def MapDataToFile(data):
      return File(client_id=self.client_id, data=data, context=self._context)

    return utils.MapItemsIterator(MapDataToFile, items)

  def GetFilesArchive(self):
    args = api_pb2.ApiGetVfsFilesArchiveArgs(
        client_id=self.client_id, file_path=self.path)
    return self._context.SendStreamingRequest("GetVfsFilesArchive", args)

  def GetVersionTimes(self):
    args = api_pb2.ApiGetFileVersionTimesArgs(
        client_id=self.client_id, file_path=self.path)
    return self._context.SendRequest("GetFileVersionTimes", args).times

  def Refresh(self):
    args = api_pb2.ApiCreateVfsRefreshOperationArgs(
        client_id=self.client_id, file_path=self.path)
    result = self._context.SendRequest("CreateVfsRefreshOperation", args)
    return RefreshOperation(
        client_id=self.client_id,
        operation_id=result.operation_id,
        context=self._context)

  def Collect(self):
    args = api_pb2.ApiUpdateVfsFileContentArgs(
        client_id=self.client_id, file_path=self.path)
    result = self._context.SendRequest("UpdateVfsFileContent", args)
    return CollectOperation(
        client_id=self.client_id,
        operation_id=result.operation_id,
        context=self._context)

  def GetTimeline(self):
    args = api_pb2.ApiGetVfsTimelineArgs(
        client_id=self.client_id, file_path=self.path)
    return self._context.SendRequest("GetVfsTimeline", args).items

  def GetTimelineAsCsv(self):
    args = api_pb2.ApiGetVfsTimelineAsCsvArgs(
        client_id=self.client_id, file_path=self.path)
    return self._context.SendStreamingRequest("GetVfsTimelineAsCsv", args)


class FileRef(FileBase):
  """Ref to a file."""

  def Get(self):
    """Fetch file's data and return proper File object."""

    args = api_pb2.ApiGetFileDetailsArgs(
        client_id=self.client_id, file_path=self.path)
    data = self._context.SendRequest("GetFileDetails", args).file
    return File(client_id=self.client_id, data=data, context=self._context)


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
