#!/usr/bin/env python
"""Types-related part of GRR API client library."""

from typing import Any, Union

from google.protobuf import any_pb2
from google.protobuf import message
from grr_api_client import context as api_context
from grr_api_client import errors
from grr_api_client import utils
from grr_response_proto import flows_pb2
from grr_response_proto.api import flow_pb2


class UnknownFlowName(errors.Error):
  pass


class Types(object):
  """Object that helps users to deal with GRR type system."""

  def __init__(
      self,
      context: api_context.GrrApiContext,
  ):
    super().__init__()

    self._context: api_context.GrrApiContext = context
    self._flow_descriptors = None

  def CreateFlowRunnerArgs(self) -> flows_pb2.FlowRunnerArgs:
    """Creates flow runner args object."""
    return flows_pb2.FlowRunnerArgs()

  def CreateHuntRunnerArgs(self) -> flows_pb2.HuntRunnerArgs:
    """Creates hunt runner args object."""
    return flows_pb2.HuntRunnerArgs()

  # TODO: Delete this method as it is not really type-safe.
  def CreateFlowArgs(
      self,
      flow_name: str,
  ) -> Any:
    """Creates flow arguments object for a flow with a given name."""
    if not self._flow_descriptors:
      self._flow_descriptors = {}

      result = self._context.SendRequest("ListFlowDescriptors", None)
      if not isinstance(result, flow_pb2.ApiListFlowDescriptorsResult):
        raise TypeError(f"Unexpected response type: {type(result)}")

      for item in result.items:
        self._flow_descriptors[item.name] = item

    try:
      flow_descriptor = self._flow_descriptors[flow_name]
    except KeyError:
      raise UnknownFlowName(flow_name)

    return utils.CopyProto(utils.UnpackAny(flow_descriptor.default_args))

  def UnpackAny(
      self,
      proto_any: any_pb2.Any,
  ) -> Union[message.Message, utils.UnknownProtobuf]:
    """Resolves the type and unpacks the given protobuf Any object."""
    return utils.UnpackAny(proto_any)
