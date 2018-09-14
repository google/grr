#!/usr/bin/env python
"""Output plugins used by flows and hunts for results exports."""
from __future__ import unicode_literals

import abc
import logging
import threading


from future.utils import itervalues
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


class OutputPluginVerificationResult(rdf_structs.RDFProtoStruct):
  """Describes result of an output plugin's output verification."""
  protobuf = output_plugin_pb2.OutputPluginVerificationResult
  rdf_deps = [
      rdf_output_plugin.OutputPluginDescriptor,
      rdfvalue.RDFDatetime,
  ]


class OutputPluginVerificationResultsList(rdf_structs.RDFProtoStruct):
  """List of OutputPluginVerificationsResults."""
  protobuf = output_plugin_pb2.OutputPluginVerificationResultsList
  rdf_deps = [
      OutputPluginVerificationResult,
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

  def __init__(self, source_urn=None, args=None, token=None, state=None):
    """OutputPlugin constructor.

    Note that OutputPlugin constructor may run with security checks enabled
    (if they're enabled in the config). Therefore it's a bad idea to write
    anything to AFF4 in the constructor.

    Constructor should only be overriden if some non-self.state-stored
    class members should be initialized.

    Args:
      source_urn: URN of the data source to process the results from.
      args: This plugin's arguments.
      token: Security token.
      state: A dict representing the plugin's state. If this is passed, no
        initialization will be performed, only the state will be applied.

    Raises:
      ValueError: when state argument is passed together with args or token
                  arguments.
    """
    if state and (token or args):
      raise ValueError("'state' argument can't be passed together with 'args' "
                       "or 'token'.")

    if not state:
      self.state = rdf_protodict.AttributedDict()
      self.state.source_urn = source_urn
      self.state.args = args
      self.state.token = token

      self.InitializeState()
    else:
      self.state = state

    self.args = self.state["args"]
    self.token = self.state["token"]

    self.lock = threading.RLock()

  def InitializeState(self):
    """Initializes the state the output plugin can use later.

    InitializeState() is called only once per plugin's lifetime. It
    will be called when hunt or flow is created. It should be used to
    register state variables. It's called on the worker, so no
    security checks apply.
    """

  @abc.abstractmethod
  def ProcessResponses(self, responses):
    """Processes bunch of responses.

    When responses are processed, multiple ProcessResponses() calls can
    be done in a row. ProcessResponse() calls may be parallelized within the
    same worker to improve output performace, therefore ProcessResponses()
    implementation should be thread-safe. ProcessResponse() calls are
    *always* followed by a single Flush() call on the same worker.

    ProcessResponses() is called on the worker, so no security checks apply.

    Args:
      responses: GrrMessages from the hunt results collection.
    """

  def Flush(self):
    """Flushes the output plugin's state.

    Flush is *always* called after a series of ProcessResponses() calls.
    Flush() is called on the worker, so no security checks apply.

    NOTE: This method doesn't have to be thread-safe as it's called once
    after a series of ProcessResponses() calls is complete.
    """


class UnknownOutputPlugin(OutputPlugin):
  """Stub plugin used when original plugin class can't be found."""

  name = "unknown"
  description = "Original plugin class couldn't be found."
  args_type = rdfvalue.RDFBytes

  def ProcessResponses(self, responses):
    pass


class MultiVerifyHuntOutputError(Error):
  """Used when problem is detected when verifying hunts in bulk."""

  def __init__(self, message=None, errors=None):
    super(MultiVerifyHuntOutputError, self).__init__(message)
    self.errors = errors or []


class OutputPluginVerifier(with_metaclass(registry.MetaclassRegistry, object)):
  """Verifier object that check that output plugin's output is complete."""
  __abstract = True  # pylint: disable=g-bad-name

  plugin_name = ""

  @classmethod
  def VerifierClassesForPlugin(cls, plugin_name):
    if not plugin_name:
      return []
    return [c for c in itervalues(cls.classes) if c.plugin_name == plugin_name]

  def VerifyHuntOutput(self, plugin, hunt):
    """Verifies hunt output generated by this plugin.

    Checks implemented in this method are "defensive" checks that can be
    implemented in certain plugins to be more sure that they work as expected.
    A good example of such a plugin is a BigQueryOutputPlugin. We want to be
    sure that hunts results are uploaded correctly into the BigQuery service
    and that we can be sure that none are missing. Doing a "black-box" check
    (that VerifyHuntOutput is inteded to be) gives us more guarantees than
    relying on BigQueryOutputPlugin correct error reporting.

    Args:
      plugin: OutputPlugin object instance corresponding to a plugin that was
        used to process hunt results.
      hunt: Hunt object. Output of this hunt was fed into the output plugin of
        this class with the arguments specified by "args" argument.

    Returns:
      OutputPluginVerificationResult object.
    """
    raise NotImplementedError()

  def MultiVerifyHuntOutput(self, plugins_hunts_pairs):
    """Verfires hunts output generated by respective plugins.

    MultiVerifyHuntOutput is similar to VerifyHuntOutput except that it may be
    optimized for verifying multiple hunts at the same time. Default
    implementation just applies VerifyHuntOutput iteratively.

    Args:
      plugins_hunts_pairs: A list of (plugin, hunt) tuples where "plugin" is an
        OutputPlugin object instance corresponding to a plugin that was used to
        process hunt results, and "hunt" is a GRRHunt object.

    Yields:
      (RDFURN, OutputPluginVerificationResult) pairs, where urns
      correspond to hunts that were verified.

    Raises:
      MultiVerifyHuntOutputError: if an error was encountered while verifying
      any of the hunts. Note that the error will be thrown only after all the
      verification results are produced.
    """
    errors = []
    for plugin, hunt in plugins_hunts_pairs:
      try:
        yield hunt.urn, self.VerifyHuntOutput(plugin, hunt)
      except Exception as e:  # pylint: disable=broad-except
        logging.exception(e)
        errors.append((hunt.urn, e))

    if errors:
      error_messages = [
          "Error validating hunt %s: %s" % (hunt_urn, e)
          for hunt_urn, e in errors
      ]
      raise MultiVerifyHuntOutputError(
          "\n".join(error_messages), errors=[e for _, e in errors])

  def VerifyFlowOutput(self, plugin, flow):
    """Verifies flow output generated by this plugin.

    Checks implemented in this method are "defensive" checks that can be
    implemented in certain plugins to be more sure that they work as expected.
    A good example of such a plugin is a BigQueryOutputPlugin. We want to be
    sure that flows results are uploaded correctly into the BigQuery service
    and that we can be sure that none are missing. Doing a "black-box" check
    (that VerifyFlowOutput is inteded to be) gives us more guarantees than
    relying on BigQueryOutputPlugin correct error reporting.

    Args:
      plugin: OutputPlugin object instance corresponding to a plugin that was
        used to process flow results.
      flow: Flow object. Output of this flow was fed into the output plugin of
        this class with the arguments specified by "args" argument.

    Returns:
      OutputPluginVerificationResult object.
    """
    raise NotImplementedError()
