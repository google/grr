#!/usr/bin/env python
"""Output plugins used by flows and hunts for results exports."""

import abc
import threading
from typing import Generic, Iterable, NamedTuple, Optional, Type, TypeVar

from google.protobuf import message as pb_message
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.registry import OutputPluginRegistry
from grr_response_proto import flows_pb2
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


class OutputPlugin(metaclass=OutputPluginRegistry):
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
  args_type: Optional[Type[rdf_structs.RDFProtoStruct]] = None
  proto_args_type = None

  @classmethod
  def CreatePluginAndDefaultState(cls, source_urn=None, args=None):
    """Creates a plugin and returns its initial state."""
    state = rdf_protodict.AttributedDict()
    if args is not None:
      args.Validate()
    state["args"] = args
    plugin = cls(source_urn=source_urn, args=args)
    plugin.InitializeState(state)
    return plugin, state

  def __init__(self, source_urn=None, args=None):
    """OutputPlugin constructor.

    Constructor should be overridden to maintain instance-local state - i.e.
    state that gets accumulated during the single output plugin run and that
    should be used to update the global state via UpdateState method.

    Args:
      source_urn: URN of the data source to process the results from.
      args: This plugin's arguments.
    """
    self.source_urn = source_urn
    self.args = args
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
    same worker to improve output performance, therefore ProcessResponses()
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
  proto_args_type = None

  def ProcessResponses(self, responses):
    pass


LogEntry = NamedTuple(
    "LogEntry",
    [
        ("level", "flows_pb2.FlowOutputPluginLogEntry.LogEntryType"),
        ("message", str),
    ],
)


_ProtoArgsT = TypeVar("_ProtoArgsT", bound=pb_message.Message)


class OutputPluginProto(Generic[_ProtoArgsT]):
  """The base class for proto-based output plugins.

  Plugins process responses from a flow after they're queued to be processed.

  ProcessResults() processes "current" flow results processed in the worker,
  and Flush() is called after. Finally GetLogs() is called to retrieve anything
  that is interesting to the flow.There is no mechanism for keeping track of
  the plugin's state between calls.
  """

  friendly_name = ""
  description = ""
  args_type: Optional[type[_ProtoArgsT]] = None

  LOG_INFO = flows_pb2.FlowOutputPluginLogEntry.LogEntryType.LOG
  LOG_ERROR = flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ERROR

  def __init__(
      self,
      source_urn: Optional[rdfvalue.RDFURN] = None,
      args: Optional[_ProtoArgsT] = None,
  ):
    """OutputPlugin constructor.

    Constructor should be overridden to maintain instance-local state - i.e.
    state that gets accumulated during the single output plugin run.

    Args:
      source_urn: URN of the data source to process the results from.
      args: This plugin's arguments.
    """
    self.source_urn = source_urn
    self.args: _ProtoArgsT = args
    # List of log messages to be returned by GetLogs() method.
    self._logs: list[LogEntry] = []

  @abc.abstractmethod
  def ProcessResults(self, responses: Iterable[flows_pb2.FlowResult]):
    """Processes bunch of responses.

    When responses are processed, multiple ProcessResults() calls can
    be done in a row. ProcessResults() calls may be parallelized within the
    same worker to improve output performance, therefore ProcessResults()
    implementation should be thread-safe. ProcessResults() calls are
    *always* followed by a single Flush() call on the same worker.

    ProcessResults() is called on the worker, so no security checks apply.

    Args:
      responses: FlowResults to be processed.
    """

  @abc.abstractmethod
  def Flush(self):
    """Flushes the output plugin's state.

    Flush is *always* called after ProcessResponses() calls.
    Flush() is called on the worker, so no security checks apply.
    """

  def Log(
      self,
      msg: str,
      level: "flows_pb2.FlowOutputPluginLogEntry.LogEntryType" = LOG_INFO,
  ):
    """Logs a message to the output plugin's log."""
    self._logs.append((level, msg))

  def GetLogs(
      self,
  ) -> list[LogEntry]:
    """Returns the output plugin's logs."""
    return self._logs
