#!/usr/bin/env python
"""Flows-related part of GRR API client library."""

from grr_api_client import utils
from grr.proto import api_pb2


class FlowResult(object):
  """Wrapper class for flow results."""

  def __init__(self, data=None):
    super(FlowResult, self).__init__()
    self.data = data

    self.timestamp = data.timestamp

  @property
  def payload(self):
    return utils.UnpackAny(self.data.payload)


class FlowBase(object):
  """Base class for FlowRef and Flow."""

  def __init__(self, client_id=None, flow_id=None, context=None):
    super(FlowBase, self).__init__()

    if not client_id:
      raise ValueError("client_id can't be empty.")

    if not flow_id:
      raise ValueError("flow_id can't be empty.")

    if not context:
      raise ValueError("context can't be empty")

    self.client_id = client_id
    self.flow_id = flow_id
    self._context = context

  def Cancel(self):
    args = api_pb2.ApiCancelFlowArgs(
        client_id=self.client_id, flow_id=self.flow_id)
    self._context.SendRequest("CancelFlow", args)

  def ListResults(self):
    args = api_pb2.ApiListFlowResultsArgs(
        client_id=self.client_id, flow_id=self.flow_id)
    items = self._context.SendIteratorRequest("ListFlowResults", args)
    return utils.MapItemsIterator(lambda data: FlowResult(data=data), items)

  def GetFilesArchive(self):
    args = api_pb2.ApiGetFlowFilesArchiveArgs(
        client_id=self.client_id, flow_id=self.flow_id)
    return self._context.SendStreamingRequest("GetFlowFilesArchive", args)


class FlowRef(FlowBase):
  """Ref to a flow."""

  def Get(self):
    """Fetch flow's data and return proper Flow object."""

    args = api_pb2.ApiGetFlowArgs(
        client_id=self.client_id, flow_id=self.flow_id)
    data = self._context.SendRequest("GetFlow", args)
    return Flow(data=data, context=self._context)


class Flow(FlowBase):
  """Flow object with fetched data."""

  def __init__(self, data=None, context=None):
    if data is None:
      raise ValueError("data can't be None")

    client_id = utils.UrnStringToClientId(data.urn)
    flow_id = data.flow_id

    super(Flow, self).__init__(
        client_id=client_id, flow_id=flow_id, context=context)

    self.data = data
