#!/usr/bin/env python
"""Output plugins used for testing."""

import os

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_server import instant_output_plugin
from grr_response_server import output_plugin
from grr_response_server.flows.general import processes
from grr.test_lib import test_lib


class DummyHuntTestOutputPlugin(output_plugin.OutputPlugin):
  """A dummy output plugin."""

  name = "dummy"
  description = "Dummy do do."
  args_type = processes.ListProcessesArgs

  def ProcessResponses(self, state, responses):
    pass


class InstantOutputPluginTestBase(test_lib.GRRBaseTest):
  """Mixing with helper methods."""

  plugin_cls = None

  def setUp(self):
    super().setUp()

    self.client_id = self.SetupClient(0)
    self.results_urn = rdf_client.ClientURN(self.client_id).Add("foo/bar")

    # pylint: disable=not-callable
    self.plugin = self.__class__.plugin_cls(source_urn=self.results_urn)
    # pylint: enable=not-callable

  def ProcessValues(self, values_by_cls):
    chunks = []

    chunks.extend(list(self.plugin.Start()))

    for value_cls in sorted(values_by_cls, key=lambda cls: cls.__name__):
      values = values_by_cls[value_cls]
      messages = []
      for value in values:
        messages.append(
            rdf_flows.GrrMessage(source=self.client_id, payload=value)
        )

      # pylint: disable=cell-var-from-loop
      chunks.extend(
          list(self.plugin.ProcessValues(value_cls, lambda: messages))
      )
      # pylint: enable=cell-var-from-loop

    chunks.extend(list(self.plugin.Finish()))

    fd_path = os.path.join(self.temp_dir, self.plugin.output_file_name)
    with open(fd_path, "wb") as fd:
      for chunk in chunks:
        fd.write(chunk)

    return fd_path


class TestInstantOutputPlugin(instant_output_plugin.InstantOutputPlugin):
  """Test plugin."""

  plugin_name = "test"
  friendly_name = "test plugin"
  description = "test plugin description"

  def Start(self):
    yield "Start: %s" % self.source_urn

  def ProcessValues(self, value_cls, values_generator_fn):
    yield "Values of type: %s" % value_cls.__name__
    for item in values_generator_fn():
      yield "First pass: %s (source=%s)" % (item.payload, item.source)
    for item in values_generator_fn():
      yield "Second pass: %s (source=%s)" % (item.payload, item.source)

  def Finish(self):
    yield "Finish: %s" % self.source_urn


class TestInstantOutputPluginWithExportConverstion(
    instant_output_plugin.InstantOutputPluginWithExportConversion
):
  """Test plugin with export conversion."""

  def Start(self):
    yield "Start\n".encode("utf-8")

  def ProcessSingleTypeExportedValues(self, original_cls, exported_values):
    yield ("Original: %s\n" % original_cls.__name__).encode("utf-8")

    for item in exported_values:
      yield ("Exported value: %s\n" % item).encode("utf-8")

  def Finish(self):
    yield "Finish".encode("utf-8")
