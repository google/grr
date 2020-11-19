#!/usr/bin/env python
"""Flows-related part of GRR API client library."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from typing import Union

from google.protobuf import message
from grr_api_client import context as api_context
from grr_api_client import errors
from grr_api_client import utils
from grr_response_proto.api import flow_pb2
from grr_response_proto.api import timeline_pb2


class FlowResult(object):
  """Wrapper class for flow results."""

  def __init__(
      self,
      data: flow_pb2.ApiFlowResult,
  ):
    super(FlowResult, self).__init__()
    self.data = data  # type: flow_pb2.ApiFlowResult
    self.timestamp = data.timestamp  # type: int

  @property
  def payload(self) -> Union[message.Message, utils.UnknownProtobuf]:
    return utils.UnpackAny(self.data.payload)

  def __repr__(self) -> str:
    return "<FlowResult payload={!r}>".format(self.payload)


class FlowLog(object):
  """Wrapper class for flow logs."""

  def __init__(
      self,
      data: flow_pb2.ApiFlowLog,
  ):
    super(FlowLog, self).__init__()

    self.data = data  # type: flow_pb2.ApiFlowLog
    self.log_message = self.data.log_message  # type: str


class FlowBase(object):
  """Base class for FlowRef and Flow."""

  def __init__(
      self,
      client_id: str,
      flow_id: str,
      context: api_context.GrrApiContext,
  ):
    super(FlowBase, self).__init__()

    if not client_id:
      raise ValueError("client_id can't be empty.")

    if not flow_id:
      raise ValueError("flow_id can't be empty.")

    if not context:
      raise ValueError("context can't be empty")

    self.client_id = client_id  # type: str
    self.flow_id = flow_id  # type: str
    self._context = context  # type: api_context.GrrApiContext

  def Cancel(self):
    args = flow_pb2.ApiCancelFlowArgs(
        client_id=self.client_id, flow_id=self.flow_id)
    self._context.SendRequest("CancelFlow", args)

  def ListResults(self) -> utils.ItemsIterator[FlowResult]:
    args = flow_pb2.ApiListFlowResultsArgs(
        client_id=self.client_id, flow_id=self.flow_id)
    items = self._context.SendIteratorRequest("ListFlowResults", args)
    return utils.MapItemsIterator(lambda data: FlowResult(data=data), items)

  def GetExportedResultsArchive(self, plugin_name) -> utils.BinaryChunkIterator:
    args = flow_pb2.ApiGetExportedFlowResultsArgs(
        client_id=self.client_id, flow_id=self.flow_id, plugin_name=plugin_name)
    return self._context.SendStreamingRequest("GetExportedFlowResults", args)

  def ListLogs(self) -> utils.ItemsIterator[FlowLog]:
    args = flow_pb2.ApiListFlowLogsArgs(
        client_id=self.client_id, flow_id=self.flow_id)
    items = self._context.SendIteratorRequest("ListFlowLogs", args)
    return utils.MapItemsIterator(lambda data: FlowLog(data=data), items)

  def GetFilesArchive(self) -> utils.BinaryChunkIterator:
    args = flow_pb2.ApiGetFlowFilesArchiveArgs(
        client_id=self.client_id, flow_id=self.flow_id)
    return self._context.SendStreamingRequest("GetFlowFilesArchive", args)

  def GetCollectedTimeline(
      self,
      fmt: timeline_pb2.ApiGetCollectedTimelineArgs.Format,
  ) -> utils.BinaryChunkIterator:
    args = timeline_pb2.ApiGetCollectedTimelineArgs(
        client_id=self.client_id, flow_id=self.flow_id, format=fmt)
    return self._context.SendStreamingRequest("GetCollectedTimeline", args)

  def Get(self) -> "Flow":
    """Fetch flow's data and return proper Flow object."""

    args = flow_pb2.ApiGetFlowArgs(
        client_id=self.client_id, flow_id=self.flow_id)
    data = self._context.SendRequest("GetFlow", args)

    if not isinstance(data, flow_pb2.ApiFlow):
      raise TypeError(f"Unexpected response type: {type(data)}")

    return Flow(data=data, context=self._context)

  def WaitUntilDone(
      self,
      timeout: int = utils.DEFAULT_POLL_TIMEOUT,
  ) -> "Flow":
    """Wait until the flow completes.

    Args:
      timeout: timeout in seconds. None means default timeout (1 hour). 0 means
        no timeout (wait forever).

    Returns:
      Fresh flow object.
    Raises:
      PollTimeoutError: if timeout is reached.
      FlowFailedError: if the flow is not successful.
    """

    f = utils.Poll(
        generator=self.Get,
        condition=lambda f: f.data.state != flow_pb2.ApiFlow.State.RUNNING,
        timeout=timeout)
    if f.data.state != flow_pb2.ApiFlow.State.TERMINATED:
      raise errors.FlowFailedError(
          "Flow %s (%s) failed: %s" %
          (self.flow_id, self.client_id, f.data.context.current_state))
    return f


class FlowRef(FlowBase):
  """Flow reference (points to the flow, but has no data)."""

  def __repr__(self) -> str:
    return "FlowRef(client_id={!r}, flow_id={!r})".format(
        self.client_id, self.flow_id)


class Flow(FlowBase):
  """Flow object with fetched data."""

  def __init__(
      self,
      data: flow_pb2.ApiFlow,
      context: api_context.GrrApiContext,
  ):
    client_id = utils.UrnStringToClientId(data.urn)
    flow_id = data.flow_id

    super(Flow, self).__init__(
        client_id=client_id, flow_id=flow_id, context=context)

    self.data = data  # type: flow_pb2.ApiFlow

  @property
  def args(self) -> Union[message.Message, utils.UnknownProtobuf]:
    return utils.UnpackAny(self.data.args)

  def __repr__(self) -> str:
    return ("Flow(data=<{} client_id={!r}, flow_id={!r}, name={!r}, "
            "state={}, ...>)").format(
                type(self.data).__name__, self.data.client_id,
                self.data.flow_id, self.data.name,
                flow_pb2.ApiFlow.State.Name(self.data.state))
