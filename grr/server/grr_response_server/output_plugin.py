#!/usr/bin/env python
"""Output plugins used by flows and hunts for results exports."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc
import threading

from future.utils import with_metaclass

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import output_plugin_pb2
from grr_response_server.rdfvalues import output_plugin as rdf_output_plugin


class OutputPluginBatchProcessingStatus(rdf_structs.RDFProtoStruct):
  """Describes processing status of a single batch by a hunt output plugin."""
  protobuf = output_plugin_pb2.OutputPluginBatchProcessingStatus
  rdf_deps = [
      rdf_output_plugin.OutputPluginDescriptor,
  ]


class Error(Exception):
  """Output plugins-related exception."""


class PluginDoesNotProduceOutputStreams(Error):
  """Raised when output streams API is used on plugins not supporting them."""


class OutputPlugin(with_metaclass(registry.OutputPluginRegistry, object)):
  """The base class for output plugins.

  Plugins process responses incrementally in small batches.

  Every batch is processed via ProcessResponses() calls, which may be issued
  in parallel for better performance. Then a single Flush() call is made.
  Next batch of results may potentially be processed on a different worker,
  therefore plugin's permanent state is stored in "state" attribute.
  """

  __abstract = True  # pylint: disable=g-bad-name

  name = ""
  description = ""
  args_type = None

  @classmethod
  def CreatePluginAndDefaultState(cls, source_urn=None, args=None, token=None):
    state = rdf_protodict.AttributedDict()
    state["source_urn"] = source_urn
    state["args"] = args
    state["token"] = token
    plugin = cls(source_urn=source_urn, args=args, token=token)
    plugin.InitializeState(state)
    return plugin, state

  def __init__(self, source_urn=None, args=None, token=None):
    """OutputPlugin constructor.

    Constructor should be overridden to maintain instance-local state - i.e.
    state that gets accumulated during the single output plugin run and that
    should be used to update the global state via UpdateState method.

    Args:
      source_urn: URN of the data source to process the results from.
      args: This plugin's arguments.
      token: Security token.
    """
    self.source_urn = source_urn
    self.args = args
    self.token = token
    self.lock = threading.RLock()

  def InitializeState(self, state):
    """Initializes the state the output plugin can use later.

    InitializeState() is called only once per plugin's lifetime. It
    will be called when hunt or flow is created. It should be used to
    register state variables. It's called on the worker, so no
    security checks apply.

    Args:
      state: rdf_protodict.AttributedDict to be filled with default values.
    """

  @abc.abstractmethod
  def ProcessResponses(self, state, responses):
    """Processes bunch of responses.

    When responses are processed, multiple ProcessResponses() calls can
    be done in a row. ProcessResponse() calls may be parallelized within the
    same worker to improve output performace, therefore ProcessResponses()
    implementation should be thread-safe. ProcessResponse() calls are
    *always* followed by a single Flush() call on the same worker.

    ProcessResponses() is called on the worker, so no security checks apply.

    Args:
      state: rdf_protodict.AttributedDict with plugin's state. NOTE:
        ProcessResponses should not change state object. All such changes should
        take place in the UpdateState method (see below).
      responses: GrrMessages from the hunt results collection.
    """

  def Flush(self, state):
    """Flushes the output plugin's state.

    Flush is *always* called after a series of ProcessResponses() calls.
    Flush() is called on the worker, so no security checks apply.

    NOTE: This method doesn't have to be thread-safe as it's called once
    after a series of ProcessResponses() calls is complete.

    Args:
      state: rdf_protodict.AttributedDict with plugin's state. NOTE:
        ProcessResponses should not change state object. All such changes should
        take place in the UpdateState method (see below).
    """

  def UpdateState(self, state):
    """Updates state of the output plugin.

    UpdateState is called after a series of ProcessResponses() calls and
    after a Flush() call. The implementation of this method should be
    lightweight, since its will be guaranteed to be called atomically
    in a middle of database transaction.

    Args:
      state: rdf_protodict.AttributedDict with plugin's state to be updated.
    """


class UnknownOutputPlugin(OutputPlugin):
  """Stub plugin used when original plugin class can't be found."""

  name = "unknown"
  description = "Original plugin class couldn't be found."
  args_type = rdfvalue.RDFBytes

  def ProcessResponses(self, responses):
    pass
