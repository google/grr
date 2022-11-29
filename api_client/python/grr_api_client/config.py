#!/usr/bin/env python
"""Functions and objects to access config-related GRR API methods."""

from grr_api_client import context as api_context
from grr_api_client import utils
from grr_response_proto.api import config_pb2


class GrrBinaryBase(object):
  """Base class for GrrBinary references and objects."""

  def __init__(
      self,
      binary_type: config_pb2.ApiGrrBinary.Type,
      path: str,
      context: api_context.GrrApiContext,
  ):
    super().__init__()

    self.binary_type = binary_type
    self.path = path
    self._context = context

  def Get(self) -> "GrrBinary":
    args = config_pb2.ApiGetGrrBinaryArgs(type=self.binary_type, path=self.path)

    data = self._context.SendRequest("GetGrrBinary", args)
    if not isinstance(data, config_pb2.ApiGrrBinary):
      raise TypeError(f"Unexpected response type: {type(data)}")

    return GrrBinary(data=data, context=self._context)

  def GetBlob(self) -> utils.BinaryChunkIterator:
    args = config_pb2.ApiGetGrrBinaryBlobArgs(
        type=self.binary_type, path=self.path)
    return self._context.SendStreamingRequest("GetGrrBinaryBlob", args)


class GrrBinaryRef(GrrBinaryBase):
  """GRR binary reference (points to one, but has no data)."""


class GrrBinary(GrrBinaryBase):
  """GRR binary object with fetched data."""

  def __init__(
      self,
      data: config_pb2.ApiGrrBinary,
      context: api_context.GrrApiContext,
  ):
    super().__init__(binary_type=data.type, path=data.path, context=context)

    self.data: config_pb2.ApiGrrBinary = data


def ListGrrBinaries(
    context: api_context.GrrApiContext) -> utils.ItemsIterator[GrrBinary]:
  """Lists all registered Grr binaries."""

  items = context.SendIteratorRequest("ListGrrBinaries", None)
  return utils.MapItemsIterator(
      lambda data: GrrBinary(data=data, context=context), items)
