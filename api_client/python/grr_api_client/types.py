#!/usr/bin/env python
"""Types-related part of GRR API client library."""

from grr_api_client import utils

from grr.proto import api_pb2
from grr.proto import flows_pb2


class Error(Exception):
  pass


class UnknownFlowName(Error):
  pass


class Types(object):
  """Object that helps users to deal with GRR type system."""

  def __init__(self, context=None):
    super(Types, self).__init__()

    if not context:
      raise ValueError("context can't be empty")
    self._context = context

    self._flow_descriptors = None

  def CreateFlowRunnerArgs(self):
    """Creates flow runner args object."""
    return flows_pb2.FlowRunnerArgs()

  def CreateHuntRunnerArgs(self):
    """Creates hunt runner args object."""
    return flows_pb2.HuntRunnerArgs()

  def CreateFlowArgs(self, flow_name=None):
    """Creates flow arguments object for a flow with a given name."""
    if not self._flow_descriptors:
      self._flow_descriptors = {}

      args = api_pb2.ApiListFlowDescriptorsArgs()
      result = self._context.SendRequest("ListFlowDescriptors", args)
      for item in result.items:
        self._flow_descriptors[item.name] = item

    try:
      flow_descriptor = self._flow_descriptors[flow_name]
    except KeyError:
      raise UnknownFlowName(flow_name)

    return utils.CopyProto(utils.UnpackAny(flow_descriptor.default_args))

  def UnpackAny(self, proto_any):
    """Resolves the type and unpacks the given protobuf Any object."""
    return utils.UnpackAny(proto_any)
