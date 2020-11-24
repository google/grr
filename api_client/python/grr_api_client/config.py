#!/usr/bin/env python
"""Functions and objects to access config-related GRR API methods."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_api_client import utils
from grr_response_proto.api import config_pb2


class GrrBinaryBase(object):
  """Base class for GrrBinary references and objects."""

  def __init__(self, binary_type=None, path=None, context=None):
    super(GrrBinaryBase, self).__init__()

    if not binary_type:
      raise ValueError("binary_type can't be empty")

    if not path:
      raise ValueError("path can't be empty")

    if not context:
      raise ValueError("context can't be empty")

    self.binary_type = binary_type
    self.path = path
    self._context = context

  def Get(self):
    args = config_pb2.ApiGetGrrBinaryArgs(type=self.binary_type, path=self.path)
    data = self._context.SendRequest("GetGrrBinary", args)
    return GrrBinary(data=data, context=self._context)

  def GetBlob(self):
    args = config_pb2.ApiGetGrrBinaryBlobArgs(
        type=self.binary_type, path=self.path)
    return self._context.SendStreamingRequest("GetGrrBinaryBlob", args)


class GrrBinaryRef(GrrBinaryBase):
  """GRR binary reference (points to one, but has no data)."""


class GrrBinary(GrrBinaryBase):
  """GRR binary object with fetched data."""

  def __init__(self, data=None, context=None):
    if data is None:
      raise ValueError("data can't be None")

    super(GrrBinary, self).__init__(
        binary_type=data.type, path=data.path, context=context)

    self.data = data


def ListGrrBinaries(context=None):
  """Lists all registered Grr binaries."""

  items = context.SendIteratorRequest("ListGrrBinaries", None)
  return utils.MapItemsIterator(
      lambda data: GrrBinary(data=data, context=context), items)
