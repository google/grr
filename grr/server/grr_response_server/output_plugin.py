#!/usr/bin/env python
"""Output plugins used by flows and hunts for results exports."""

import abc
from typing import Generic, Iterable, NamedTuple, Optional, TypeVar

from google.protobuf import message as pb_message
from grr_response_core.lib import rdfvalue
from grr_response_proto import flows_pb2


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
