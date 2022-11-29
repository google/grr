#!/usr/bin/env python
"""Flows-related part of GRR API client library."""

from typing import Union

from google.protobuf import wrappers_pb2
from google.protobuf import message
from grr_api_client import context as api_context
from grr_api_client import errors
from grr_api_client import utils
from grr_response_proto.api import flow_pb2
from grr_response_proto.api import osquery_pb2
from grr_response_proto.api import timeline_pb2


class FlowResult(object):
  """Wrapper class for flow results."""

  def __init__(
      self,
      data: flow_pb2.ApiFlowResult,
  ):
    super().__init__()
    self.data: flow_pb2.ApiFlowResult = data
    self.timestamp: int = data.timestamp

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
    super().__init__()

    self.data: flow_pb2.ApiFlowLog = data
    self.log_message: str = self.data.log_message


class FlowBase(object):
  """Base class for FlowRef and Flow."""

  def __init__(
      self,
      client_id: str,
      flow_id: str,
      context: api_context.GrrApiContext,
  ):
    super().__init__()

    if not client_id:
      raise ValueError("client_id can't be empty.")

    if not flow_id:
      raise ValueError("flow_id can't be empty.")

    if not context:
      raise ValueError("context can't be empty")

    self.client_id: str = client_id
    self.flow_id: str = flow_id
    self._context: api_context.GrrApiContext = context

  def Cancel(self):
    args = flow_pb2.ApiCancelFlowArgs(
        client_id=self.client_id, flow_id=self.flow_id)
    self._context.SendRequest("CancelFlow", args)

  def ListResults(self) -> utils.ItemsIterator[FlowResult]:
    args = flow_pb2.ApiListFlowResultsArgs(
        client_id=self.client_id, flow_id=self.flow_id)
    items = self._context.SendIteratorRequest("ListFlowResults", args)
    return utils.MapItemsIterator(lambda data: FlowResult(data=data), items)

  def ListParsedResults(self) -> utils.ItemsIterator[FlowResult]:
    args = flow_pb2.ApiListParsedFlowResultsArgs(
        client_id=self.client_id, flow_id=self.flow_id)
    items = self._context.SendIteratorRequest("ListParsedFlowResults", args)
    return utils.MapItemsIterator(lambda data: FlowResult(data=data), items)

  def ListApplicableParsers(
      self) -> flow_pb2.ApiListFlowApplicableParsersResult:
    """Lists parsers that are applicable to results of the flow."""
    args = flow_pb2.ApiListFlowApplicableParsersArgs(
        client_id=self.client_id, flow_id=self.flow_id)

    result = self._context.SendRequest("ListFlowApplicableParsers", args)
    if not isinstance(result, flow_pb2.ApiListFlowApplicableParsersResult):
      raise TypeError(f"Unexpected type: '{type(result)}'")

    return result

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

  def GetCollectedTimelineBody(
      self,
      timestamp_subsecond_precision: bool = True,
      inode_ntfs_file_reference_format: bool = False,
      backslash_escape: bool = True,
      carriage_return_escape: bool = False,
      non_printable_escape: bool = False,
  ) -> utils.BinaryChunkIterator:
    """Fetches timeline content in the body format."""
    args = timeline_pb2.ApiGetCollectedTimelineArgs()
    args.client_id = self.client_id
    args.flow_id = self.flow_id
    args.format = timeline_pb2.ApiGetCollectedTimelineArgs.BODY

    opts = args.body_opts
    opts.timestamp_subsecond_precision = timestamp_subsecond_precision
    opts.inode_ntfs_file_reference_format = inode_ntfs_file_reference_format
    opts.backslash_escape = backslash_escape
    opts.carriage_return_escape = carriage_return_escape
    opts.non_printable_escape = non_printable_escape

    return self._context.SendStreamingRequest("GetCollectedTimeline", args)

  def GetOsqueryResults(
      self,
      fmt: osquery_pb2.ApiGetOsqueryResultsArgs.Format,
  ) -> utils.BinaryChunkIterator:
    args = osquery_pb2.ApiGetOsqueryResultsArgs(
        client_id=self.client_id, flow_id=self.flow_id, format=fmt)
    return self._context.SendStreamingRequest("GetOsqueryResults", args)

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

    super().__init__(client_id=client_id, flow_id=flow_id, context=context)

    self.data: flow_pb2.ApiFlow = data

  @property
  def args(self) -> Union[message.Message, utils.UnknownProtobuf]:
    return utils.UnpackAny(self.data.args)

  def __repr__(self) -> str:
    return ("Flow(data=<{} client_id={!r}, flow_id={!r}, name={!r}, "
            "state={}, ...>)").format(
                type(self.data).__name__, self.data.client_id,
                self.data.flow_id, self.data.name,
                flow_pb2.ApiFlow.State.Name(self.data.state))

  def GetLargeFileEncryptionKey(self) -> bytes:
    """Retrieves the encryption key of the large file collection flow."""
    if self.data.name != "CollectLargeFileFlow":
      raise ValueError(f"Incorrect flow type: '{self.data.name}'")

    encryption_key_wrapper = wrappers_pb2.BytesValue()

    state = {item.key: item.value for item in self.data.state_data.items}
    state["encryption_key"].Unpack(encryption_key_wrapper)

    return encryption_key_wrapper.value
