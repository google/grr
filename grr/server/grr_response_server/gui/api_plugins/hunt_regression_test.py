#!/usr/bin/env python
"""This modules contains regression tests for hunts API handlers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import pdb


from builtins import range  # pylint: disable=redefined-builtin

from grr_response_core.lib import flags

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server.gui import api_regression_test_lib
from grr_response_server.gui.api_plugins import hunt as hunt_plugin
from grr_response_server.hunts import implementation
from grr_response_server.hunts import process_results
from grr_response_server.output_plugins import test_plugins
from grr_response_server.rdfvalues import hunts as rdf_hunts
from grr_response_server.rdfvalues import objects as rdf_objects
from grr_response_server.rdfvalues import output_plugin as rdf_output_plugin
from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import test_lib


class ApiListHuntsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin):

  api_method = "ListHunts"
  handler = hunt_plugin.ApiListHuntsHandler
  # Hunts are aff4 only for now.
  aff4_only_test = True

  def Run(self):
    replace = {}
    for i in range(0, 2):
      with test_lib.FakeTime((1 + i) * 1000):
        with self.CreateHunt(description="hunt_%d" % i) as hunt_obj:
          if i % 2:
            hunt_obj.Stop()

          replace[hunt_obj.urn.Basename()] = "H:00000%d" % i

    self.Check(
        "ListHunts", args=hunt_plugin.ApiListHuntsArgs(), replace=replace)
    self.Check(
        "ListHunts",
        args=hunt_plugin.ApiListHuntsArgs(count=1),
        replace=replace)
    self.Check(
        "ListHunts",
        args=hunt_plugin.ApiListHuntsArgs(offset=1, count=1),
        replace=replace)


class ApiListHuntResultsRegressionTest(
    api_regression_test_lib.ApiRegressionTest):

  api_method = "ListHuntResults"
  handler = hunt_plugin.ApiListHuntResultsHandler
  # Hunts are aff4 only for now.
  aff4_only_test = True

  def Run(self):
    hunt_urn = rdfvalue.RDFURN("aff4:/hunts/H:123456")
    results = implementation.GRRHunt.ResultCollectionForHID(hunt_urn)
    with data_store.DB.GetMutationPool() as pool:
      result = rdf_flows.GrrMessage(
          payload=rdfvalue.RDFString("blah1"),
          age=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1))
      results.Add(
          result,
          timestamp=result.age + rdfvalue.Duration("1s"),
          mutation_pool=pool)

      result = rdf_flows.GrrMessage(
          payload=rdfvalue.RDFString("blah2-foo"),
          age=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42))
      results.Add(
          result,
          timestamp=result.age + rdfvalue.Duration("1s"),
          mutation_pool=pool)

    self.Check(
        "ListHuntResults",
        args=hunt_plugin.ApiListHuntResultsArgs(hunt_id="H:123456"))
    self.Check(
        "ListHuntResults",
        args=hunt_plugin.ApiListHuntResultsArgs(hunt_id="H:123456", count=1))
    self.Check(
        "ListHuntResults",
        args=hunt_plugin.ApiListHuntResultsArgs(
            hunt_id="H:123456", offset=1, count=1))
    self.Check(
        "ListHuntResults",
        args=hunt_plugin.ApiListHuntResultsArgs(
            hunt_id="H:123456", filter="foo"))


class ApiGetHuntHandlerRegressionTest(api_regression_test_lib.ApiRegressionTest,
                                      hunt_test_lib.StandardHuntTestMixin):

  api_method = "GetHunt"
  handler = hunt_plugin.ApiGetHuntHandler
  # Hunts are aff4 only for now.
  aff4_only_test = True

  def Run(self):
    with test_lib.FakeTime(42):
      with self.CreateHunt(description="the hunt") as hunt_obj:
        hunt_urn = hunt_obj.urn

        hunt_stats = hunt_obj.context.usage_stats
        hunt_stats.user_cpu_stats.sum = 5000
        hunt_stats.network_bytes_sent_stats.sum = 1000000

    self.Check(
        "GetHunt",
        args=hunt_plugin.ApiGetHuntArgs(hunt_id=hunt_urn.Basename()),
        replace={hunt_urn.Basename(): "H:123456"})


class ApiGetHuntHandlerHuntCopyRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin):

  api_method = "GetHunt"
  handler = hunt_plugin.ApiGetHuntHandler
  # Hunts are aff4 only for now.
  aff4_only_test = True

  def Run(self):
    with test_lib.FakeTime(42):
      ref = rdf_hunts.FlowLikeObjectReference(
          object_type="HUNT_REFERENCE",
          hunt_reference=rdf_objects.HuntReference(hunt_id="H:332211"))
      with self.CreateHunt(
          description="the hunt", original_object=ref) as hunt_obj:
        hunt_urn = hunt_obj.urn

        hunt_stats = hunt_obj.context.usage_stats
        hunt_stats.user_cpu_stats.sum = 5000
        hunt_stats.network_bytes_sent_stats.sum = 1000000

    self.Check(
        "GetHunt",
        args=hunt_plugin.ApiGetHuntArgs(hunt_id=hunt_urn.Basename()),
        replace={hunt_urn.Basename(): "H:123456"})


class ApiGetHuntHandlerFlowCopyRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin):

  api_method = "GetHunt"
  handler = hunt_plugin.ApiGetHuntHandler
  # Hunts are aff4 only for now.
  aff4_only_test = True

  def Run(self):
    with test_lib.FakeTime(42):
      ref = rdf_hunts.FlowLikeObjectReference(
          object_type="FLOW_REFERENCE",
          flow_reference=rdf_objects.FlowReference(
              flow_id="F:332211", client_id="C.1111111111111111"))
      with self.CreateHunt(
          description="the hunt", original_object=ref) as hunt_obj:
        hunt_urn = hunt_obj.urn

        hunt_stats = hunt_obj.context.usage_stats
        hunt_stats.user_cpu_stats.sum = 5000
        hunt_stats.network_bytes_sent_stats.sum = 1000000

    self.Check(
        "GetHunt",
        args=hunt_plugin.ApiGetHuntArgs(hunt_id=hunt_urn.Basename()),
        replace={hunt_urn.Basename(): "H:123456"})


class ApiListHuntLogsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin):

  api_method = "ListHuntLogs"
  handler = hunt_plugin.ApiListHuntLogsHandler
  # Hunts are aff4 only for now.
  aff4_only_test = True

  def Run(self):
    with test_lib.FakeTime(42):
      with self.CreateHunt(description="the hunt") as hunt_obj:

        with test_lib.FakeTime(52):
          hunt_obj.Log("Sample message: foo.")

        with test_lib.FakeTime(55):
          hunt_obj.Log("Sample message: bar.")

    self.Check(
        "ListHuntLogs",
        args=hunt_plugin.ApiListHuntLogsArgs(hunt_id=hunt_obj.urn.Basename()),
        replace={hunt_obj.urn.Basename(): "H:123456"})
    self.Check(
        "ListHuntLogs",
        args=hunt_plugin.ApiListHuntLogsArgs(
            hunt_id=hunt_obj.urn.Basename(), count=1),
        replace={hunt_obj.urn.Basename(): "H:123456"})
    self.Check(
        "ListHuntLogs",
        args=hunt_plugin.ApiListHuntLogsArgs(
            hunt_id=hunt_obj.urn.Basename(), offset=1, count=1),
        replace={hunt_obj.urn.Basename(): "H:123456"})


class ApiListHuntErrorsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin):

  api_method = "ListHuntErrors"
  handler = hunt_plugin.ApiListHuntErrorsHandler
  # Hunts are aff4 only for now.
  aff4_only_test = True

  def Run(self):
    with test_lib.FakeTime(42):
      with self.CreateHunt(description="the hunt") as hunt_obj:

        with test_lib.FakeTime(52):
          hunt_obj.LogClientError(
              rdf_client.ClientURN("C.0000111122223333"), "Error foo.")

        with test_lib.FakeTime(55):
          hunt_obj.LogClientError(
              rdf_client.ClientURN("C.1111222233334444"), "Error bar.",
              "<some backtrace>")

    self.Check(
        "ListHuntErrors",
        args=hunt_plugin.ApiListHuntErrorsArgs(hunt_id=hunt_obj.urn.Basename()),
        replace={hunt_obj.urn.Basename(): "H:123456"})
    self.Check(
        "ListHuntErrors",
        args=hunt_plugin.ApiListHuntErrorsArgs(
            hunt_id=hunt_obj.urn.Basename(), count=1),
        replace={hunt_obj.urn.Basename(): "H:123456"})
    self.Check(
        "ListHuntErrors",
        args=hunt_plugin.ApiListHuntErrorsArgs(
            hunt_id=hunt_obj.urn.Basename(), offset=1, count=1),
        replace={hunt_obj.urn.Basename(): "H:123456"})


class ApiListHuntCrashesHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin):

  api_method = "ListHuntCrashes"
  handler = hunt_plugin.ApiListHuntCrashesHandler
  # Hunts are aff4 only for now.
  aff4_only_test = True

  def Run(self):
    if data_store.RelationalDBReadEnabled():
      client_obj = self.SetupTestClientObject(0)
      client_id = client_obj.client_id
    else:
      client_id = self.SetupClient(0).Basename()

    client_mocks = {
        client_id: flow_test_lib.CrashClientMock(client_id, self.token)
    }

    with test_lib.FakeTime(42):
      with self.CreateHunt(description="the hunt") as hunt_obj:
        hunt_obj.Run()

    with test_lib.FakeTime(45):
      self.AssignTasksToClients([client_id])
      hunt_test_lib.TestHuntHelperWithMultipleMocks(client_mocks, False,
                                                    self.token)

    crashes = implementation.GRRHunt.CrashCollectionForHID(hunt_obj.urn)
    crash = list(crashes)[0]
    session_id = crash.session_id.Basename()
    replace = {hunt_obj.urn.Basename(): "H:123456", session_id: "H:11223344"}

    self.Check(
        "ListHuntCrashes",
        args=hunt_plugin.ApiListHuntCrashesArgs(
            hunt_id=hunt_obj.urn.Basename()),
        replace=replace)
    self.Check(
        "ListHuntCrashes",
        args=hunt_plugin.ApiListHuntCrashesArgs(
            hunt_id=hunt_obj.urn.Basename(), count=1),
        replace=replace)
    self.Check(
        "ListHuntCrashes",
        args=hunt_plugin.ApiListHuntCrashesArgs(
            hunt_id=hunt_obj.urn.Basename(), offset=1, count=1),
        replace=replace)


class ApiGetHuntClientCompletionStatsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin):

  api_method = "GetHuntClientCompletionStats"
  handler = hunt_plugin.ApiGetHuntClientCompletionStatsHandler
  # Hunts are aff4 only for now.
  aff4_only_test = True

  def Run(self):
    if data_store.RelationalDBReadEnabled():
      clients = self.SetupTestClientObjects(10)
      client_ids = sorted(clients)
    else:
      client_ids = [urn.Basename() for urn in self.SetupClients(10)]

    client_mock = hunt_test_lib.SampleHuntMock()

    with test_lib.FakeTime(42):
      with self.CreateHunt(description="the hunt") as hunt_obj:
        hunt_obj.Run()

    time_offset = 0
    for client_id in client_ids:
      with test_lib.FakeTime(45 + time_offset):
        self.AssignTasksToClients([client_id])
        hunt_test_lib.TestHuntHelper(
            client_mock, [rdf_client.ClientURN(client_id)], False, self.token)
        time_offset += 10

    replace = {hunt_obj.urn.Basename(): "H:123456"}
    self.Check(
        "GetHuntClientCompletionStats",
        args=hunt_plugin.ApiGetHuntClientCompletionStatsArgs(
            hunt_id=hunt_obj.urn.Basename()),
        replace=replace)
    self.Check(
        "GetHuntClientCompletionStats",
        args=hunt_plugin.ApiGetHuntClientCompletionStatsArgs(
            hunt_id=hunt_obj.urn.Basename(), size=4),
        replace=replace)
    self.Check(
        "GetHuntClientCompletionStats",
        args=hunt_plugin.ApiGetHuntClientCompletionStatsArgs(
            hunt_id=hunt_obj.urn.Basename(), size=1000),
        replace=replace)


class ApiGetHuntResultsExportCommandHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin):

  api_method = "GetHuntResultsExportCommand"
  handler = hunt_plugin.ApiGetHuntResultsExportCommandHandler
  # Hunts are aff4 only for now.
  aff4_only_test = True

  def Run(self):
    with test_lib.FakeTime(42):
      with self.CreateHunt(description="the hunt") as hunt_obj:
        pass

    self.Check(
        "GetHuntResultsExportCommand",
        args=hunt_plugin.ApiGetHuntResultsExportCommandArgs(
            hunt_id=hunt_obj.urn.Basename()),
        replace={hunt_obj.urn.Basename()[2:]: "123456"})


class ApiListHuntOutputPluginsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin):

  api_method = "ListHuntOutputPlugins"
  handler = hunt_plugin.ApiListHuntOutputPluginsHandler
  # Hunts are aff4 only for now.
  aff4_only_test = True

  # ApiOutputPlugin's state is an AttributedDict containing URNs that
  # are always random. Given that currently their JSON representation
  # is proto-serialized and then base64-encoded, there's no way
  # we can replace these URNs with something stable.
  uses_legacy_dynamic_protos = True

  def Run(self):
    with test_lib.FakeTime(42):
      with self.CreateHunt(
          description="the hunt",
          output_plugins=[
              rdf_output_plugin.OutputPluginDescriptor(
                  plugin_name=test_plugins.DummyHuntTestOutputPlugin.__name__,
                  plugin_args=test_plugins.DummyHuntTestOutputPlugin.args_type(
                      filename_regex="blah!", fetch_binaries=True))
          ]) as hunt_obj:
        pass

    self.Check(
        "ListHuntOutputPlugins",
        args=hunt_plugin.ApiListHuntOutputPluginsArgs(
            hunt_id=hunt_obj.urn.Basename()),
        replace={hunt_obj.urn.Basename(): "H:123456"})


class ApiListHuntOutputPluginLogsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin):

  api_method = "ListHuntOutputPluginLogs"
  handler = hunt_plugin.ApiListHuntOutputPluginLogsHandler
  # Hunts are aff4 only for now.
  aff4_only_test = True

  # ApiOutputPlugin's state is an AttributedDict containing URNs that
  # are always random. Given that currently their JSON representation
  # is proto-serialized and then base64-encoded, there's no way
  # we can replace these URNs with something stable.
  uses_legacy_dynamic_protos = True

  def Run(self):
    with test_lib.FakeTime(42, increment=1):
      hunt_urn = self.StartHunt(
          description="the hunt",
          output_plugins=[
              rdf_output_plugin.OutputPluginDescriptor(
                  plugin_name=test_plugins.DummyHuntTestOutputPlugin.__name__,
                  plugin_args=test_plugins.DummyHuntTestOutputPlugin.args_type(
                      filename_regex="blah!", fetch_binaries=True))
          ])

      self.client_ids = self.SetupClients(2)
      for index, client_id in enumerate(self.client_ids):
        self.AssignTasksToClients(client_ids=[client_id])
        self.RunHunt(failrate=-1)
        with test_lib.FakeTime(100042 + index * 100):
          self.ProcessHuntOutputPlugins()

    self.Check(
        "ListHuntOutputPluginLogs",
        args=hunt_plugin.ApiListHuntOutputPluginLogsArgs(
            hunt_id=hunt_urn.Basename(),
            plugin_id="DummyHuntTestOutputPlugin_0"),
        replace={hunt_urn.Basename(): "H:123456"})


class ApiListHuntOutputPluginErrorsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin):

  api_method = "ListHuntOutputPluginErrors"
  handler = hunt_plugin.ApiListHuntOutputPluginErrorsHandler
  # Hunts are aff4 only for now.
  aff4_only_test = True

  # ApiOutputPlugin's state is an AttributedDict containing URNs that
  # are always random. Given that currently their JSON representation
  # is proto-serialized and then base64-encoded, there's no way
  # we can replace these URNs with something stable.
  uses_legacy_dynamic_protos = True

  def Run(self):
    failing_descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name=hunt_test_lib.FailingDummyHuntOutputPlugin.__name__)

    with test_lib.FakeTime(42, increment=1):
      hunt_urn = self.StartHunt(
          description="the hunt", output_plugins=[failing_descriptor])

      self.client_ids = self.SetupClients(2)
      for index, client_id in enumerate(self.client_ids):
        self.AssignTasksToClients(client_ids=[client_id])
        self.RunHunt(failrate=-1)
        with test_lib.FakeTime(100042 + index * 100):
          try:
            self.ProcessHuntOutputPlugins()
          except process_results.ResultsProcessingError:
            if flags.FLAGS.debug:
              pdb.post_mortem()

    self.Check(
        "ListHuntOutputPluginErrors",
        args=hunt_plugin.ApiListHuntOutputPluginErrorsArgs(
            hunt_id=hunt_urn.Basename(),
            plugin_id="FailingDummyHuntOutputPlugin_0"),
        replace={hunt_urn.Basename(): "H:123456"})


class ApiGetHuntStatsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin):

  api_method = "GetHuntStats"
  handler = hunt_plugin.ApiGetHuntStatsHandler
  # Hunts are aff4 only for now.
  aff4_only_test = True

  def Run(self):
    with test_lib.FakeTime(42):
      hunt_urn = self.StartHunt(description="the hunt")

      if data_store.RelationalDBReadEnabled():
        client = self.SetupTestClientObject(0)
        client_ids = [rdf_client.ClientURN(client.client_id)]
      else:
        client_ids = self.SetupClients(1)
      self.AssignTasksToClients(client_ids=client_ids)
      self.RunHunt(client_ids=client_ids)

    # Create replace dictionary.
    replace = {hunt_urn.Basename(): "H:123456"}
    with aff4.FACTORY.Open(hunt_urn, mode="r", token=self.token) as hunt:
      stats = hunt.GetRunner().context.usage_stats
      for performance in stats.worst_performers:
        session_id = performance.session_id.Basename()
        replace[session_id] = "<replaced session value>"

    self.Check(
        "GetHuntStats",
        args=hunt_plugin.ApiGetHuntStatsArgs(hunt_id=hunt_urn.Basename()),
        replace=replace)


class ApiListHuntClientsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin):

  api_method = "ListHuntClients"
  handler = hunt_plugin.ApiListHuntClientsHandler
  # Hunts are aff4 only for now.
  aff4_only_test = True

  def Run(self):
    with test_lib.FakeTime(42):
      hunt_urn = self.StartHunt(description="the hunt")

      if data_store.RelationalDBReadEnabled():
        clients = self.SetupTestClientObjects(5)
        client_ids = sorted(clients)
      else:
        client_ids = [urn.Basename() for urn in self.SetupClients(5)]

      self.AssignTasksToClients(client_ids=client_ids)
      # Only running the hunt on a single client, as SampleMock
      # implementation is non-deterministic in terms of resources
      # usage that gets reported back to the hunt.
      client_urns = [rdf_client.ClientURN(client_ids[-1])]
      self.RunHunt(client_ids=client_urns, failrate=0)

    # Create replace dictionary.
    replace = {hunt_urn.Basename(): "H:123456"}

    self.Check(
        "ListHuntClients",
        args=hunt_plugin.ApiListHuntClientsArgs(
            hunt_id=hunt_urn.Basename(), client_status="STARTED"),
        replace=replace)
    self.Check(
        "ListHuntClients",
        args=hunt_plugin.ApiListHuntClientsArgs(
            hunt_id=hunt_urn.Basename(), client_status="OUTSTANDING"),
        replace=replace)
    self.Check(
        "ListHuntClients",
        args=hunt_plugin.ApiListHuntClientsArgs(
            hunt_id=hunt_urn.Basename(), client_status="COMPLETED"),
        replace=replace)


class ApiModifyHuntHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin):

  api_method = "ModifyHunt"
  handler = hunt_plugin.ApiModifyHuntHandler
  # Hunts are aff4 only for now.
  aff4_only_test = True

  def Run(self):
    # Check client_limit update.
    with test_lib.FakeTime(42):
      hunt = self.CreateHunt(description="the hunt")

    # Create replace dictionary.
    replace = {hunt.urn.Basename(): "H:123456"}

    with test_lib.FakeTime(43):
      self.Check(
          "ModifyHunt",
          args=hunt_plugin.ApiModifyHuntArgs(
              hunt_id=hunt.urn.Basename(), client_limit=142),
          replace=replace)
      self.Check(
          "ModifyHunt",
          args=hunt_plugin.ApiModifyHuntArgs(
              hunt_id=hunt.urn.Basename(), state="STOPPED"),
          replace=replace)


class ApiDeleteHuntHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin):

  api_method = "DeleteHunt"
  handler = hunt_plugin.ApiDeleteHuntHandler
  # Hunts are aff4 only for now.
  aff4_only_test = True

  def Run(self):
    with test_lib.FakeTime(42):
      hunt = self.CreateHunt(description="the hunt")

    self.Check(
        "DeleteHunt",
        args=hunt_plugin.ApiDeleteHuntArgs(hunt_id=hunt.urn.Basename()),
        replace={hunt.urn.Basename(): "H:123456"})


def main(argv):
  api_regression_test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
