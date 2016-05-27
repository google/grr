#!/usr/bin/env python
"""Output plugins used by flows and hunts for results exports."""



import abc
import threading
import zipfile

import logging

from grr.lib import aff4
from grr.lib import registry
from grr.lib import utils
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import output_plugin_pb2


class OutputPluginBatchProcessingStatus(rdf_structs.RDFProtoStruct):
  """Describes processing status of a single batch by a hunt output plugin."""
  protobuf = output_plugin_pb2.OutputPluginBatchProcessingStatus


class OutputPluginVerificationResult(rdf_structs.RDFProtoStruct):
  """Describes result of an output plugin's output verification."""
  protobuf = output_plugin_pb2.OutputPluginVerificationResult


class OutputPluginVerificationResultsList(rdf_structs.RDFProtoStruct):
  """List of OutputPluginVerificationsResults."""
  protobuf = output_plugin_pb2.OutputPluginVerificationResultsList


class Error(Exception):
  """Output plugins-related exception."""


class PluginDoesNotProduceOutputStreams(Error):
  """Raised when output streams API is used on plugins not supporting them."""


class OutputPlugin(object):
  """The base class for output plugins.

  Plugins process responses incrementally in small batches.

  Every batch is processed via ProcessResponses() calls, which may be issued
  in parallel for better performance. Then a single Flush() call is made.
  Next batch of results may potentially be processed on a different worker,
  therefore plugin's permanent state is stored in "state" attribute.
  """

  __metaclass__ = registry.MetaclassRegistry
  __abstract = True  # pylint: disable=g-bad-name

  name = ""
  description = ""
  args_type = None

  def __init__(self,
               source_urn=None,
               output_base_urn=None,
               args=None,
               token=None,
               state=None):
    """OutputPlugin constructor.

    Note that OutputPlugin constructor may run with security checks enabled
    (if they're enabled in the config). Therefore it's a bad idea to write
    anything to AFF4 in the constructor.

    Constructor should only be overriden if some non-self.state-stored
    class members should be initialized.

    Args:
      source_urn: URN of the data source to process the results from.
      output_base_urn: URN of the AFF4 volume where plugin will write output
                       data (if needed).
      args: This plugin's arguments.
      token: Security token.
      state: Instance of rdf_flows.FlowState. Represents plugin's state. If this
             is passed, no initialization will be performed, only the state will
             be applied.
    Raises:
      ValueError: when state argument is passed together with args or token
                  arguments.
    """
    if state and (token or args):
      raise ValueError("'state' argument can't be passed together with 'args' "
                       "or 'token'.")

    if not state:
      self.state = state or rdf_flows.FlowState()
      self.state.Register("source_urn", source_urn)
      self.state.Register("output_base_urn", output_base_urn)
      self.state.Register("args", args)
      self.state.Register("token", token)

      self.Initialize()
    else:
      self.state = state

    self.args = self.state.args
    self.token = self.state.token

    self.lock = threading.RLock()

  def Initialize(self):
    """Initializes the output plugin.

    Initialize() is called only once per plugin's lifetime. It will be called
    when hunt or flow is created.

    Initialize() can be used to register state variables. It's called on the
    worker, so no security checks apply.
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


class MultiVerifyHuntOutputError(Error):
  """Used when problem is detected when verifying hunts in bulk."""

  def __init__(self, message=None, errors=None):
    super(MultiVerifyHuntOutputError, self).__init__(message)
    self.errors = errors or []


class OutputPluginVerifier(object):
  """Verifier object that check that output plugin's output is complete."""

  __metaclass__ = registry.MetaclassRegistry
  __abstract = True  # pylint: disable=g-bad-name

  plugin_name = ""

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
      plugin: OutputPlugin object instance corresponding to a plugin that
              was used to process hunt results.
      hunt: Hunt object. Output of this hunt was fed into the output
            plugin of this class with the arguments specified by
            "args" argument.

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
      plugins_hunts_pairs: A list of (plugin, hunt) tuples where "plugin"
          is an OutputPlugin object instance corresponding to a plugin
          that was used to process hunt results, and "hunt" is a GRRHunt
          object.

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
      error_messages = ["Error validating hunt %s: %s" % (hunt_urn, e)
                        for hunt_urn, e in errors]
      raise MultiVerifyHuntOutputError("\n".join(error_messages),
                                       errors=[e for _, e in errors])

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
      plugin: OutputPlugin object instance corresponding to a plugin that
              was used to process flow results.
      flow: Flow object. Output of this flow was fed into the output
            plugin of this class with the arguments specified by
            "args" argument.

    Returns:
      OutputPluginVerificationResult object.
    """
    raise NotImplementedError()


class OutputPluginWithOutputStreams(OutputPlugin):
  """OutputPlugin that writes results to output streams on AFF4."""

  __abstract = True  # pylint: disable=g-bad-name

  def Initialize(self):
    super(OutputPluginWithOutputStreams, self).Initialize()
    self.state.Register("output_streams", {})

  def Flush(self):
    super(OutputPluginWithOutputStreams, self).Flush()

    for stream in self.state.output_streams.values():
      stream.Flush()

  def _GetOutputStream(self, name):
    """Gets output stream with a given name."""
    return self.state.output_streams[name]

  def _CreateOutputStream(self, name):
    """Creates new output stream with a given name."""
    try:
      return self.state.output_streams[name]
    except KeyError:
      output_stream = aff4.FACTORY.Create(
          self.state.output_base_urn.Add(name),
          aff4.AFF4UnversionedImage,
          mode="w",
          token=self.token)
      self.state.output_streams[name] = output_stream
      return output_stream

  @property
  def output_streams_map(self):
    """Mapping of output streams names into URNs.

    Returns:
      Dictionary with "stream name" -> "stream urn" key value pairs.
    """
    return dict((k, v.urn) for k, v in self.state.output_streams.items())

  @property
  def reverse_output_streams_map(self):
    """Mapping of output streams urns into names."""
    return dict((v.urn, k) for k, v in self.state.output_streams.items())

  def OpenOutputStreams(self):
    """Opens all the used output streams.

    Returns:
      Dictionary with "stream name" -> "stream object" key-value pairs.
    """
    streams = list(aff4.FACTORY.MultiOpen(self.output_streams_map.values(),
                                          aff4_type=aff4.AFF4UnversionedImage,
                                          token=self.token))

    result = {}
    reverse_map = self.reverse_output_streams_map
    for stream in streams:
      result[reverse_map[stream.urn]] = stream

    return result

  def WriteSnapshotZipStream(self, fd, compression=zipfile.ZIP_DEFLATED):
    """Writes available output streams to a new zipped stream."""
    raise NotImplementedError()


class OutputPluginDescriptor(rdf_structs.RDFProtoStruct):
  """An rdfvalue describing the output plugin to create."""

  protobuf = output_plugin_pb2.OutputPluginDescriptor

  def GetPluginClass(self):
    if self.plugin_name:
      plugin_cls = OutputPlugin.classes.get(self.plugin_name)
      if plugin_cls is None:
        raise KeyError("Unknown output plugin %s" % self.plugin_name)
      return plugin_cls

  def GetPluginArgsClass(self):
    plugin_cls = self.GetPluginClass()
    if plugin_cls:
      return plugin_cls.args_type

  def GetPluginForState(self, plugin_state):
    cls = self.GetPluginClass()
    return cls(None, state=plugin_state)

  def GetPluginVerifiersClasses(self):
    result = []
    if self.plugin_name:
      for cls in OutputPluginVerifier.classes.values():
        if cls.plugin_name == self.plugin_name:
          result.append(cls)

    return result

  def GetPluginVerifiers(self):
    return [cls() for cls in self.GetPluginVerifiersClasses()]

  def __str__(self):
    result = self.plugin_name
    if self.plugin_args:
      result += " <%s>" % utils.SmartStr(self.plugin_args)
    return result
