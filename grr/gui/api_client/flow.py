#!/usr/bin/env python
"""Flows-related part of GRR API client library."""

from grr.gui.api_client import utils
from grr.proto import api_pb2


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
    self._context.SendRequest("CancelFlow")


class FlowRef(FlowBase):
  """Ref to a flow."""

  def Get(self):
    """Fetch flow's data and return proper Flow object."""

    args = api_pb2.ApiGetFlowArgs(client_id=self.client_id,
                                  flow_id=self.flow_id)
    data = self._context.SendRequest("GetFlow", args)
    return Flow(data=data, context=self._context)


class Flow(FlowBase):
  """Flow object with fetched data."""

  def __init__(self, data=None, context=None):
    if data is None:
      raise ValueError("data can't be None")

    urn = context.GetDataAttribute(data, "urn")
    client_id = utils.UrnToClientId(urn)
    flow_id = utils.UrnToFlowId(urn)

    super(Flow, self).__init__(client_id=client_id,
                               flow_id=flow_id,
                               context=context)

    self.data = data
