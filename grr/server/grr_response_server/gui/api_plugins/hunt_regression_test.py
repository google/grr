#!/usr/bin/env python
"""This modules contains regression tests for hunts API handlers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import pdb

from absl import app
from absl import flags
from future.builtins import range

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import grr_collections
from grr_response_server import hunt
from grr_response_server.databases import db
from grr_response_server.flows.general import processes as flows_processes
from grr_response_server.gui import api_regression_test_lib
from grr_response_server.gui.api_plugins import hunt as hunt_plugin
from grr_response_server.hunts import implementation
from grr_response_server.hunts import process_results
from grr_response_server.output_plugins import test_plugins
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import hunts as rdf_hunts
from grr_response_server.rdfvalues import objects as rdf_objects
from grr_response_server.rdfvalues import output_plugin as rdf_output_plugin
from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import test_lib


class ApiListHuntsHandlerRegressionTest(
    hunt_test_lib.StandardHuntTestMixin,
    api_regression_test_lib.ApiRegressionTest,
):

  api_method = "ListHunts"
  handler = hunt_plugin.ApiListHuntsHandler

  def Run(self):
    if data_store.RelationalDBEnabled():
      replace = {}
      for i in range(0, 2):
        with test_lib.FakeTime((1 + i) * 1000):
          hunt_id = self.CreateHunt(description="hunt_%d" % i)
          if i % 2:
            hunt.StopHunt(hunt_id)

          replace[hunt_id] = "H:00000%d" % i
    else:
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


class ApiListHuntResultsRegressionTest(hunt_test_lib.StandardHuntTestMixin,
                                       api_regression_test_lib.ApiRegressionTest
                                      ):

  api_method = "ListHuntResults"
  handler = hunt_plugin.ApiListHuntResultsHandler

  def Run(self):
    client_id = self.SetupClient(0).Basename()

    if data_store.RelationalDBEnabled():
      hunt_id = self.CreateHunt()
      flow_id = flow_test_lib.StartFlow(
          flows_processes.ListProcesses,
          client_id=client_id,
          parent_hunt_id=hunt_id)

      with test_lib.FakeTime(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(2)):
        data_store.REL_DB.WriteFlowResults([
            rdf_flow_objects.FlowResult(
                client_id=client_id,
                flow_id=flow_id,
                hunt_id=hunt_id,
                payload=rdfvalue.RDFString("blah1"))
        ])

      with test_lib.FakeTime(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(43)):
        data_store.REL_DB.WriteFlowResults([
            rdf_flow_objects.FlowResult(
                client_id=client_id,
                flow_id=flow_id,
                hunt_id=hunt_id,
                payload=rdfvalue.RDFString("blah2-foo"))
        ])
    else:
      hunt_urn = rdfvalue.RDFURN("aff4:/hunts/H:123456")
      hunt_id = hunt_urn.Basename()

      results = implementation.GRRHunt.ResultCollectionForHID(hunt_urn)
      with data_store.DB.GetMutationPool() as pool:
        result = rdf_flows.GrrMessage(
            source=client_id,
            payload=rdfvalue.RDFString("blah1"),
            age=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1))
        results.Add(
            result,
            timestamp=result.age + rdfvalue.Duration("1s"),
            mutation_pool=pool)

        result = rdf_flows.GrrMessage(
            source=client_id,
            payload=rdfvalue.RDFString("blah2-foo"),
            age=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42))
        results.Add(
            result,
            timestamp=result.age + rdfvalue.Duration("1s"),
            mutation_pool=pool)

    replace = {hunt_id: "H:123456"}
    self.Check(
        "ListHuntResults",
        args=hunt_plugin.ApiListHuntResultsArgs(hunt_id=hunt_id),
        replace=replace)
    self.Check(
        "ListHuntResults",
        args=hunt_plugin.ApiListHuntResultsArgs(hunt_id=hunt_id, count=1),
        replace=replace)
    self.Check(
        "ListHuntResults",
        args=hunt_plugin.ApiListHuntResultsArgs(
            hunt_id=hunt_id, offset=1, count=1),
        replace=replace)
    self.Check(
        "ListHuntResults",
        args=hunt_plugin.ApiListHuntResultsArgs(hunt_id=hunt_id, filter="foo"),
        replace=replace)


class ApiGetHuntHandlerRegressionTest(api_regression_test_lib.ApiRegressionTest,
                                      hunt_test_lib.StandardHuntTestMixin):

  api_method = "GetHunt"
  handler = hunt_plugin.ApiGetHuntHandler

  def Run(self):
    with test_lib.FakeTime(42):
      # TODO(user): make hunt stats non-zero when AFF4 is gone to
      # improve test coverage.
      if data_store.RelationalDBEnabled():
        hunt_id = self.CreateHunt(description="the hunt")
      else:
        with self.CreateHunt(description="the hunt") as hunt_obj:
          hunt_urn = hunt_obj.urn
          hunt_id = hunt_urn.Basename()

    self.Check(
        "GetHunt",
        args=hunt_plugin.ApiGetHuntArgs(hunt_id=hunt_id),
        replace={hunt_id: "H:123456"})


class ApiGetHuntHandlerHuntCopyRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin):

  api_method = "GetHunt"
  handler = hunt_plugin.ApiGetHuntHandler

  def Run(self):
    ref = rdf_hunts.FlowLikeObjectReference(
        object_type="HUNT_REFERENCE",
        hunt_reference=rdf_objects.HuntReference(hunt_id="H:332211"))

    if data_store.RelationalDBEnabled():
      # TODO(user): make hunt stats non-zero when AFF4 is gone to
      # improve test coverage.
      with test_lib.FakeTime(42):
        hunt_id = self.CreateHunt(description="the hunt", original_object=ref)
    else:
      with test_lib.FakeTime(42):
        with self.CreateHunt(
            description="the hunt", original_object=ref) as hunt_obj:
          hunt_id = hunt_obj.urn.Basename()

    self.Check(
        "GetHunt",
        args=hunt_plugin.ApiGetHuntArgs(hunt_id=hunt_id),
        replace={hunt_id: "H:123456"})


class ApiGetHuntHandlerFlowCopyRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin):

  api_method = "GetHunt"
  handler = hunt_plugin.ApiGetHuntHandler

  def Run(self):
    ref = rdf_hunts.FlowLikeObjectReference(
        object_type="FLOW_REFERENCE",
        flow_reference=rdf_objects.FlowReference(
            flow_id="F:332211", client_id="C.1111111111111111"))

    if data_store.RelationalDBEnabled():
      # TODO(user): make hunt stats non-zero when AFF4 is gone to
      # improve test coverage.
      with test_lib.FakeTime(42):
        hunt_id = self.CreateHunt(description="the hunt", original_object=ref)
    else:
      with test_lib.FakeTime(42):
        with self.CreateHunt(
            description="the hunt", original_object=ref) as hunt_obj:
          hunt_id = hunt_obj.urn.Basename()

    self.Check(
        "GetHunt",
        args=hunt_plugin.ApiGetHuntArgs(hunt_id=hunt_id),
        replace={hunt_id: "H:123456"})


class ApiListHuntLogsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin):

  api_method = "ListHuntLogs"
  handler = hunt_plugin.ApiListHuntLogsHandler

  def Run(self):
    if data_store.RelationalDBEnabled():
      with test_lib.FakeTime(42):
        hunt_id = self.CreateHunt()

      client_id = self.SetupClient(0).Basename()
      flow_id = flow_test_lib.StartFlow(
          flows_processes.ListProcesses,
          client_id=client_id,
          parent_hunt_id=hunt_id)

      with test_lib.FakeTime(52):
        data_store.REL_DB.WriteFlowLogEntries([
            rdf_flow_objects.FlowLogEntry(
                client_id=client_id,
                flow_id=flow_id,
                hunt_id=hunt_id,
                message="Sample message: foo")
        ])

      with test_lib.FakeTime(55):
        data_store.REL_DB.WriteFlowLogEntries([
            rdf_flow_objects.FlowLogEntry(
                client_id=client_id,
                flow_id=flow_id,
                hunt_id=hunt_id,
                message="Sample message: bar")
        ])
    else:
      with test_lib.FakeTime(42):
        client_id = self.SetupClient(0)
        flow_id = "H:123456"
        with self.CreateHunt(description="the hunt") as hunt_obj:
          hunt_id = hunt_obj.urn.Basename()
          logs_collection_urn = hunt_obj.logs_collection_urn

        log_entry = rdf_flows.FlowLog(
            client_id=client_id,
            urn=client_id.Add(flow_id),
            flow_name=hunt_obj.__class__.__name__,
            log_message="Sample message: foo")
        with test_lib.FakeTime(52):
          with data_store.DB.GetMutationPool() as pool:
            grr_collections.LogCollection.StaticAdd(
                logs_collection_urn, log_entry, mutation_pool=pool)

        log_entry = rdf_flows.FlowLog(
            client_id=client_id,
            urn=client_id.Add(flow_id),
            flow_name=hunt_obj.__class__.__name__,
            log_message="Sample message: bar")
        with test_lib.FakeTime(55):
          with data_store.DB.GetMutationPool() as pool:
            grr_collections.LogCollection.StaticAdd(
                logs_collection_urn, log_entry, mutation_pool=pool)

    self.Check(
        "ListHuntLogs",
        args=hunt_plugin.ApiListHuntLogsArgs(hunt_id=hunt_id),
        replace={hunt_id: "H:123456"})
    self.Check(
        "ListHuntLogs",
        args=hunt_plugin.ApiListHuntLogsArgs(hunt_id=hunt_id, count=1),
        replace={hunt_id: "H:123456"})
    self.Check(
        "ListHuntLogs",
        args=hunt_plugin.ApiListHuntLogsArgs(
            hunt_id=hunt_id, offset=1, count=1),
        replace={hunt_id: "H:123456"})


class ApiListHuntErrorsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin):

  api_method = "ListHuntErrors"
  handler = hunt_plugin.ApiListHuntErrorsHandler

  def Run(self):
    client_id_1 = self.SetupClient(0).Basename()
    client_id_2 = self.SetupClient(1).Basename()

    if data_store.RelationalDBEnabled():
      with test_lib.FakeTime(42):
        hunt_id = self.CreateHunt(description="the hunt")

      with test_lib.FakeTime(52):
        flow_id = flow_test_lib.StartFlow(
            flows_processes.ListProcesses,
            client_id=client_id_1,
            parent_hunt_id=hunt_id)
        flow_obj = data_store.REL_DB.ReadFlowObject(client_id_1, flow_id)
        flow_obj.flow_state = flow_obj.FlowState.ERROR
        flow_obj.error_message = "Error foo."
        data_store.REL_DB.UpdateFlow(client_id_1, flow_id, flow_obj=flow_obj)

      with test_lib.FakeTime(55):
        flow_id = flow_test_lib.StartFlow(
            flows_processes.ListProcesses,
            client_id=client_id_2,
            parent_hunt_id=hunt_id)
        flow_obj = data_store.REL_DB.ReadFlowObject(client_id_2, flow_id)
        flow_obj.flow_state = flow_obj.FlowState.ERROR
        flow_obj.error_message = "Error bar."
        flow_obj.backtrace = "<some backtrace>"
        data_store.REL_DB.UpdateFlow(client_id_2, flow_id, flow_obj=flow_obj)

    else:
      with test_lib.FakeTime(42):
        with self.CreateHunt(description="the hunt") as hunt_obj:
          hunt_id = hunt_obj.urn.Basename()

          with test_lib.FakeTime(52):
            hunt_obj.LogClientError(
                rdf_client.ClientURN(client_id_1), "Error foo.")

          with test_lib.FakeTime(55):
            hunt_obj.LogClientError(
                rdf_client.ClientURN(client_id_2), "Error bar.",
                "<some backtrace>")

    self.Check(
        "ListHuntErrors",
        args=hunt_plugin.ApiListHuntErrorsArgs(hunt_id=hunt_id),
        replace={hunt_id: "H:123456"})
    self.Check(
        "ListHuntErrors",
        args=hunt_plugin.ApiListHuntErrorsArgs(hunt_id=hunt_id, count=1),
        replace={hunt_id: "H:123456"})
    self.Check(
        "ListHuntErrors",
        args=hunt_plugin.ApiListHuntErrorsArgs(
            hunt_id=hunt_id, offset=1, count=1),
        replace={hunt_id: "H:123456"})


class ApiListHuntCrashesHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin):

  api_method = "ListHuntCrashes"
  handler = hunt_plugin.ApiListHuntCrashesHandler

  def Run(self):
    if data_store.RelationalDBEnabled():
      client_obj = self.SetupTestClientObject(0)
      client_id = client_obj.client_id
    else:
      client_id = self.SetupClient(0).Basename()

    client_mocks = {
        client_id: flow_test_lib.CrashClientMock(client_id, self.token)
    }

    if data_store.RelationalDBEnabled():
      hunt_id = self.CreateHunt(description="the hunt")
      hunt.StartHunt(hunt_id)
    else:
      with test_lib.FakeTime(42):
        with self.CreateHunt(description="the hunt") as hunt_obj:
          hunt_obj.Run()
          hunt_id = hunt_obj.urn.Basename()

    with test_lib.FakeTime(45):
      self.AssignTasksToClients([client_id])
      hunt_test_lib.TestHuntHelperWithMultipleMocks(client_mocks, False,
                                                    self.token)

    if data_store.RelationalDBEnabled():
      crash = data_store.REL_DB.ReadHuntFlows(
          hunt_id,
          0,
          1,
          filter_condition=db.HuntFlowsCondition.CRASHED_FLOWS_ONLY,
      )[0].client_crash_info
    else:
      crashes = implementation.GRRHunt.CrashCollectionForHID(hunt_obj.urn)
      crash = list(crashes)[0]

    replace = {
        hunt_id:
            "H:123456",
        unicode(crash.session_id):
            "aff4:/hunts/H:123456/C.1000000000000000/H:11223344"
    }

    self.Check(
        "ListHuntCrashes",
        args=hunt_plugin.ApiListHuntCrashesArgs(hunt_id=hunt_id),
        replace=replace)
    self.Check(
        "ListHuntCrashes",
        args=hunt_plugin.ApiListHuntCrashesArgs(hunt_id=hunt_id, count=1),
        replace=replace)
    self.Check(
        "ListHuntCrashes",
        args=hunt_plugin.ApiListHuntCrashesArgs(
            hunt_id=hunt_id, offset=1, count=1),
        replace=replace)


class ApiGetHuntClientCompletionStatsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin):

  api_method = "GetHuntClientCompletionStats"
  handler = hunt_plugin.ApiGetHuntClientCompletionStatsHandler

  def Run(self):
    if data_store.RelationalDBEnabled():
      clients = self.SetupTestClientObjects(10)
      client_ids = sorted(clients)
    else:
      client_ids = [urn.Basename() for urn in self.SetupClients(10)]

    client_mock = hunt_test_lib.SampleHuntMock(failrate=2)

    if data_store.RelationalDBEnabled():
      hunt_id = self.CreateHunt(description="the hunt")
      hunt.StartHunt(hunt_id)
    else:
      with test_lib.FakeTime(42):
        with self.CreateHunt(description="the hunt") as hunt_obj:
          hunt_obj.Run()
          hunt_id = hunt_obj.urn.Basename()

    time_offset = 0
    for client_id in client_ids:
      with test_lib.FakeTime(45 + time_offset):
        self.AssignTasksToClients([client_id])
        hunt_test_lib.TestHuntHelper(client_mock,
                                     [rdf_client.ClientURN(client_id)], False,
                                     self.token)
        time_offset += 10

    replace = {hunt_id: "H:123456"}
    self.Check(
        "GetHuntClientCompletionStats",
        args=hunt_plugin.ApiGetHuntClientCompletionStatsArgs(hunt_id=hunt_id),
        replace=replace)
    self.Check(
        "GetHuntClientCompletionStats",
        args=hunt_plugin.ApiGetHuntClientCompletionStatsArgs(
            hunt_id=hunt_id, size=4),
        replace=replace)
    self.Check(
        "GetHuntClientCompletionStats",
        args=hunt_plugin.ApiGetHuntClientCompletionStatsArgs(
            hunt_id=hunt_id, size=1000),
        replace=replace)


class ApiGetHuntResultsExportCommandHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin):

  api_method = "GetHuntResultsExportCommand"
  handler = hunt_plugin.ApiGetHuntResultsExportCommandHandler

  def Run(self):
    with test_lib.FakeTime(42):
      if data_store.RelationalDBEnabled():
        hunt_id = self.CreateHunt(description="the hunt")
        # TODO(user): replacement done for backwards compatibility with
        # the AFF4 implementation. Simply change to {hunt_id: "123456"} when
        # AFF4 is gone.
        replace = {hunt_id: "H:123456", "_%s" % hunt_id: "_H_123456"}
      else:
        with self.CreateHunt(description="the hunt") as hunt_obj:
          hunt_id = hunt_obj.urn.Basename()
          replace = {hunt_id[2:]: "123456"}

    self.Check(
        "GetHuntResultsExportCommand",
        args=hunt_plugin.ApiGetHuntResultsExportCommandArgs(hunt_id=hunt_id),
        replace=replace)


class ApiListHuntOutputPluginsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin):

  api_method = "ListHuntOutputPlugins"
  handler = hunt_plugin.ApiListHuntOutputPluginsHandler

  # ApiOutputPlugin's state is an AttributedDict containing URNs that
  # are always random. Given that currently their JSON representation
  # is proto-serialized and then base64-encoded, there's no way
  # we can replace these URNs with something stable.
  uses_legacy_dynamic_protos = True

  def Run(self):
    output_plugins = [
        rdf_output_plugin.OutputPluginDescriptor(
            plugin_name=test_plugins.DummyHuntTestOutputPlugin.__name__,
            plugin_args=test_plugins.DummyHuntTestOutputPlugin.args_type(
                filename_regex="blah!", fetch_binaries=True))
    ]

    with test_lib.FakeTime(42):
      if data_store.RelationalDBEnabled():
        hunt_id = self.CreateHunt(
            description="the hunt", output_plugins=output_plugins)
        hunt.StartHunt(hunt_id)
      else:
        with self.CreateHunt(
            description="the hunt", output_plugins=output_plugins) as hunt_obj:
          hunt_id = hunt_obj.urn.Basename()

    self.Check(
        "ListHuntOutputPlugins",
        args=hunt_plugin.ApiListHuntOutputPluginsArgs(hunt_id=hunt_id),
        replace={hunt_id: "H:123456"})


class ApiListHuntOutputPluginLogsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin):

  api_method = "ListHuntOutputPluginLogs"
  handler = hunt_plugin.ApiListHuntOutputPluginLogsHandler

  # ApiOutputPlugin's state is an AttributedDict containing URNs that
  # are always random. Given that currently their JSON representation
  # is proto-serialized and then base64-encoded, there's no way
  # we can replace these URNs with something stable.
  uses_legacy_dynamic_protos = True

  def Run(self):
    output_plugins = [
        rdf_output_plugin.OutputPluginDescriptor(
            plugin_name=test_plugins.DummyHuntTestOutputPlugin.__name__,
            plugin_args=test_plugins.DummyHuntTestOutputPlugin.args_type(
                filename_regex="blah!", fetch_binaries=True))
    ]
    with test_lib.FakeTime(42, increment=1):
      if data_store.RelationalDBEnabled():
        hunt_id = self.CreateHunt(
            description="the hunt", output_plugins=output_plugins)
        hunt.StartHunt(hunt_id)
      else:
        hunt_urn = self.StartHunt(
            description="the hunt", output_plugins=output_plugins)
        hunt_id = hunt_urn.Basename()

      self.client_ids = self.SetupClients(2)
      for index, client_id in enumerate(self.client_ids):
        self.RunHunt(client_ids=[client_id], failrate=-1)
        with test_lib.FakeTime(100042 + index * 100):
          self.ProcessHuntOutputPlugins()

    self.Check(
        "ListHuntOutputPluginLogs",
        args=hunt_plugin.ApiListHuntOutputPluginLogsArgs(
            hunt_id=hunt_id, plugin_id="DummyHuntTestOutputPlugin_0"),
        replace={hunt_id: "H:123456"})


class ApiListHuntOutputPluginErrorsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin):

  api_method = "ListHuntOutputPluginErrors"
  handler = hunt_plugin.ApiListHuntOutputPluginErrorsHandler

  # ApiOutputPlugin's state is an AttributedDict containing URNs that
  # are always random. Given that currently their JSON representation
  # is proto-serialized and then base64-encoded, there's no way
  # we can replace these URNs with something stable.
  uses_legacy_dynamic_protos = True

  def Run(self):
    failing_descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name=hunt_test_lib.FailingDummyHuntOutputPlugin.__name__)

    with test_lib.FakeTime(42, increment=1):
      if data_store.RelationalDBEnabled():
        hunt_id = self.CreateHunt(
            description="the hunt", output_plugins=[failing_descriptor])
        hunt.StartHunt(hunt_id)
      else:
        hunt_urn = self.StartHunt(
            description="the hunt", output_plugins=[failing_descriptor])
        hunt_id = hunt_urn.Basename()

      self.client_ids = self.SetupClients(2)
      for index, client_id in enumerate(self.client_ids):
        self.RunHunt(client_ids=[client_id], failrate=-1)
        with test_lib.FakeTime(100042 + index * 100):
          try:
            self.ProcessHuntOutputPlugins()
          except process_results.ResultsProcessingError:
            if flags.FLAGS.pdb_post_mortem:
              pdb.post_mortem()

    self.Check(
        "ListHuntOutputPluginErrors",
        args=hunt_plugin.ApiListHuntOutputPluginErrorsArgs(
            hunt_id=hunt_id, plugin_id="FailingDummyHuntOutputPlugin_0"),
        replace={hunt_id: "H:123456"})


class ApiGetHuntStatsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin):

  api_method = "GetHuntStats"
  handler = hunt_plugin.ApiGetHuntStatsHandler

  def Run(self):
    with test_lib.FakeTime(42):
      if data_store.RelationalDBEnabled():
        hunt_id = self.CreateHunt(description="the hunt")
        hunt.StartHunt(hunt_id)
      else:
        hunt_urn = self.StartHunt(description="the hunt")
        hunt_id = hunt_urn.Basename()

      if data_store.RelationalDBEnabled():
        client = self.SetupTestClientObject(0)
        client_ids = [rdf_client.ClientURN(client.client_id)]
      else:
        client_ids = self.SetupClients(1)
      self.RunHunt(failrate=2, client_ids=client_ids)

    # Create replace dictionary.
    replace = {hunt_id: "H:123456"}
    if data_store.RelationalDBEnabled():
      stats = data_store.REL_DB.ReadHuntClientResourcesStats(hunt_id)
      for performance in stats.worst_performers:
        session_id = unicode(performance.session_id)
        replace[session_id] = "<replaced session value>"
    else:
      with aff4.FACTORY.Open(hunt_urn, mode="r", token=self.token) as hunt_obj:
        stats = hunt_obj.GetRunner().context.usage_stats
        for performance in stats.worst_performers:
          session_id = unicode(performance.session_id)
          replace[session_id] = "<replaced session value>"

    self.Check(
        "GetHuntStats",
        args=hunt_plugin.ApiGetHuntStatsArgs(hunt_id=hunt_id),
        replace=replace)


class ApiListHuntClientsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin):

  api_method = "ListHuntClients"
  handler = hunt_plugin.ApiListHuntClientsHandler

  def Run(self):
    with test_lib.FakeTime(42):
      if data_store.RelationalDBEnabled():
        hunt_id = self.CreateHunt(description="the hunt")
        hunt.StartHunt(hunt_id)
      else:
        hunt_urn = self.StartHunt(description="the hunt")
        hunt_id = hunt_urn.Basename()

      if data_store.RelationalDBEnabled():
        clients = self.SetupTestClientObjects(5)
        client_ids = sorted(clients)
      else:
        client_ids = [urn.Basename() for urn in self.SetupClients(5)]

      self.AssignTasksToClients(client_ids=client_ids[:-1])
      # Only running the hunt on a single client, as SampleMock
      # implementation is non-deterministic in terms of resources
      # usage that gets reported back to the hunt.
      client_urns = [rdf_client.ClientURN(client_ids[-1])]
      self.RunHunt(client_ids=client_urns, failrate=0)

    # Create replace dictionary.
    replace = {hunt_id: "H:123456", hunt_id + ":hunt": "H:123456"}

    self.Check(
        "ListHuntClients",
        args=hunt_plugin.ApiListHuntClientsArgs(
            hunt_id=hunt_id, client_status="STARTED"),
        replace=replace)
    self.Check(
        "ListHuntClients",
        args=hunt_plugin.ApiListHuntClientsArgs(
            hunt_id=hunt_id, client_status="OUTSTANDING"),
        replace=replace)
    self.Check(
        "ListHuntClients",
        args=hunt_plugin.ApiListHuntClientsArgs(
            hunt_id=hunt_id, client_status="COMPLETED"),
        replace=replace)


class ApiModifyHuntHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin):

  api_method = "ModifyHunt"
  handler = hunt_plugin.ApiModifyHuntHandler

  def Run(self):
    # Check client_limit update.
    with test_lib.FakeTime(42):
      if data_store.RelationalDBEnabled():
        hunt_id = self.CreateHunt(description="the hunt")
      else:
        hunt_obj = self.CreateHunt(description="the hunt")
        hunt_id = hunt_obj.urn.Basename()

    # Create replace dictionary.
    replace = {hunt_id: "H:123456"}

    with test_lib.FakeTime(43):
      self.Check(
          "ModifyHunt",
          args=hunt_plugin.ApiModifyHuntArgs(hunt_id=hunt_id, client_limit=142),
          replace=replace)
      self.Check(
          "ModifyHunt",
          args=hunt_plugin.ApiModifyHuntArgs(hunt_id=hunt_id, state="STOPPED"),
          replace=replace)


class ApiDeleteHuntHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin):

  api_method = "DeleteHunt"
  handler = hunt_plugin.ApiDeleteHuntHandler

  def Run(self):
    with test_lib.FakeTime(42):
      if data_store.RelationalDBEnabled():
        hunt_id = self.CreateHunt(description="the hunt")
      else:
        hunt_obj = self.CreateHunt(description="the hunt")
        hunt_id = hunt_obj.urn.Basename()

    self.Check(
        "DeleteHunt",
        args=hunt_plugin.ApiDeleteHuntArgs(hunt_id=hunt_id),
        replace={hunt_id: "H:123456"})


def main(argv):
  api_regression_test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
