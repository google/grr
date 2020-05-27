#!/usr/bin/env python
# Lint as: python3
"""This module contains regression tests for flows-related API handlers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server import flow_base
from grr_response_server.flows.general import discovery
from grr_response_server.flows.general import file_finder
from grr_response_server.flows.general import processes
from grr_response_server.flows.general import transfer
from grr_response_server.gui import api_regression_test_lib
from grr_response_server.gui.api_plugins import flow as flow_plugin
from grr_response_server.output_plugins import email_plugin
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import output_plugin as rdf_output_plugin
from grr.test_lib import acl_test_lib
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import test_lib


class ApiGetFlowHandlerRegressionTest(api_regression_test_lib.ApiRegressionTest
                                     ):
  """Regression test for ApiGetFlowHandler."""

  api_method = "GetFlow"
  handler = flow_plugin.ApiGetFlowHandler

  def Run(self):
    # Fix the time to avoid regressions.
    with test_lib.FakeTime(42):
      client_id = self.SetupClient(0)
      flow_id = flow_test_lib.StartFlow(
          discovery.Interrogate,
          client_id=client_id,
          creator=self.token.username)

      replace = api_regression_test_lib.GetFlowTestReplaceDict(
          client_id, flow_id, "F:ABCDEF12")

      self.Check(
          "GetFlow",
          args=flow_plugin.ApiGetFlowArgs(client_id=client_id, flow_id=flow_id),
          replace=replace)

      flow_base.TerminateFlow(client_id, flow_id,
                              "Pending termination: Some reason")

      replace = api_regression_test_lib.GetFlowTestReplaceDict(
          client_id, flow_id, "F:ABCDEF13")

      # Fetch the same flow which is now should be marked as pending
      # termination.
      self.Check(
          "GetFlow",
          args=flow_plugin.ApiGetFlowArgs(client_id=client_id, flow_id=flow_id),
          replace=replace)


class ApiListFlowsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest):
  """Test client flows list handler."""

  api_method = "ListFlows"
  handler = flow_plugin.ApiListFlowsHandler

  def Run(self):
    acl_test_lib.CreateUser(self.token.username)
    with test_lib.FakeTime(42):
      client_id = self.SetupClient(0)

    with test_lib.FakeTime(43):
      flow_id_1 = flow_test_lib.StartFlow(
          discovery.Interrogate, client_id, creator=self.token.username)

    with test_lib.FakeTime(44):
      flow_id_2 = flow_test_lib.StartFlow(
          processes.ListProcesses, client_id, creator=self.token.username)

    replace = api_regression_test_lib.GetFlowTestReplaceDict(
        client_id, flow_id_1, "F:ABCDEF10")
    replace.update(
        api_regression_test_lib.GetFlowTestReplaceDict(client_id, flow_id_2,
                                                       "F:ABCDEF11"))

    self.Check(
        "ListFlows",
        args=flow_plugin.ApiListFlowsArgs(client_id=client_id),
        replace=replace)

    self.Check(
        "ListFlows",
        args=flow_plugin.ApiListFlowsArgs(
            client_id=client_id,
            top_flows_only=True,
        ),
        replace=replace)

    self.Check(
        "ListFlows",
        args=flow_plugin.ApiListFlowsArgs(
            client_id=client_id,
            min_started_at=rdfvalue.RDFDatetimeSeconds(44),
            top_flows_only=True,
        ),
        replace=replace)

    self.Check(
        "ListFlows",
        args=flow_plugin.ApiListFlowsArgs(
            client_id=client_id,
            max_started_at=rdfvalue.RDFDatetimeSeconds(43),
            top_flows_only=True,
        ),
        replace=replace)


class ApiListFlowRequestsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest):
  """Regression test for ApiListFlowRequestsHandler."""

  api_method = "ListFlowRequests"
  handler = flow_plugin.ApiListFlowRequestsHandler

  def Run(self):
    client_id = self.SetupClient(0)
    with test_lib.FakeTime(42):
      flow_id = flow_test_lib.StartFlow(
          processes.ListProcesses, client_id, creator=self.token.username)
      test_process = rdf_client.Process(name="test_process")
      mock = flow_test_lib.MockClient(
          client_id,
          action_mocks.ListProcessesMock([test_process]),
          token=self.token)
      mock.Next()

    replace = api_regression_test_lib.GetFlowTestReplaceDict(client_id, flow_id)

    self.Check(
        "ListFlowRequests",
        args=flow_plugin.ApiListFlowRequestsArgs(
            client_id=client_id, flow_id=flow_id),
        replace=replace)


class ApiListFlowResultsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest):
  """Regression test for ApiListFlowResultsHandler."""

  api_method = "ListFlowResults"
  handler = flow_plugin.ApiListFlowResultsHandler

  def _RunFlow(self, client_id):
    flow_args = transfer.GetFileArgs(
        pathspec=rdf_paths.PathSpec(
            path="/tmp/evil.txt", pathtype=rdf_paths.PathSpec.PathType.OS))
    client_mock = hunt_test_lib.SampleHuntMock(failrate=2)

    with test_lib.FakeTime(42):
      return flow_test_lib.StartAndRunFlow(
          transfer.GetFile,
          client_id=client_id,
          client_mock=client_mock,
          flow_args=flow_args)

  def Run(self):
    acl_test_lib.CreateUser(self.token.username)
    client_id = self.SetupClient(0)

    flow_id = self._RunFlow(client_id)
    self.Check(
        "ListFlowResults",
        args=flow_plugin.ApiListFlowResultsArgs(
            client_id=client_id, flow_id=flow_id, filter="evil"),
        replace={flow_id: "W:ABCDEF"})
    self.Check(
        "ListFlowResults",
        args=flow_plugin.ApiListFlowResultsArgs(
            client_id=client_id, flow_id=flow_id, filter="benign"),
        replace={flow_id: "W:ABCDEF"})


class ApiListFlowLogsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest):
  """Regression test for ApiListFlowResultsHandler."""

  api_method = "ListFlowLogs"
  handler = flow_plugin.ApiListFlowLogsHandler

  def _AddLogToFlow(self, client_id, flow_id, log_string):
    entry = rdf_flow_objects.FlowLogEntry(
        client_id=client_id, flow_id=flow_id, message=log_string)
    data_store.REL_DB.WriteFlowLogEntries([entry])

  def Run(self):
    client_id = self.SetupClient(0)

    flow_id = flow_test_lib.StartFlow(
        processes.ListProcesses, client_id, creator=self.token.username)

    with test_lib.FakeTime(52):
      self._AddLogToFlow(client_id, flow_id, "Sample message: foo.")

    with test_lib.FakeTime(55):
      self._AddLogToFlow(client_id, flow_id, "Sample message: bar.")

    replace = {flow_id: "W:ABCDEF"}
    self.Check(
        "ListFlowLogs",
        args=flow_plugin.ApiListFlowLogsArgs(
            client_id=client_id, flow_id=flow_id),
        replace=replace)
    self.Check(
        "ListFlowLogs",
        args=flow_plugin.ApiListFlowLogsArgs(
            client_id=client_id, flow_id=flow_id, count=1),
        replace=replace)
    self.Check(
        "ListFlowLogs",
        args=flow_plugin.ApiListFlowLogsArgs(
            client_id=client_id, flow_id=flow_id, count=1, offset=1),
        replace=replace)


class ApiGetFlowResultsExportCommandHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest):
  """Regression test for ApiGetFlowResultsExportCommandHandler."""

  api_method = "GetFlowResultsExportCommand"
  handler = flow_plugin.ApiGetFlowResultsExportCommandHandler

  def Run(self):
    client_id = self.SetupClient(0)
    flow_urn = "F:ABCDEF"

    self.Check(
        "GetFlowResultsExportCommand",
        args=flow_plugin.ApiGetFlowResultsExportCommandArgs(
            client_id=client_id, flow_id=flow_urn))


class ApiListFlowOutputPluginsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest):
  """Regression test for ApiListFlowOutputPluginsHandler."""

  api_method = "ListFlowOutputPlugins"
  handler = flow_plugin.ApiListFlowOutputPluginsHandler

  # ApiOutputPlugin's state is an AttributedDict containing URNs that
  # are always random. Given that currently their JSON representation
  # is proto-serialized and then base64-encoded, there's no way
  # we can replace these URNs with something stable.
  uses_legacy_dynamic_protos = True

  def Run(self):
    client_id = self.SetupClient(0)
    email_descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name=email_plugin.EmailOutputPlugin.__name__,
        plugin_args=email_plugin.EmailOutputPluginArgs(
            email_address="test@localhost", emails_limit=42))

    with test_lib.FakeTime(42):
      flow_id = flow.StartFlow(
          flow_cls=processes.ListProcesses,
          client_id=client_id,
          output_plugins=[email_descriptor])

    self.Check(
        "ListFlowOutputPlugins",
        args=flow_plugin.ApiListFlowOutputPluginsArgs(
            client_id=client_id, flow_id=flow_id),
        replace={flow_id: "W:ABCDEF"})


class ApiListFlowOutputPluginLogsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest):
  """Regression test for ApiListFlowOutputPluginLogsHandler."""

  api_method = "ListFlowOutputPluginLogs"
  handler = flow_plugin.ApiListFlowOutputPluginLogsHandler

  # ApiOutputPlugin's state is an AttributedDict containing URNs that
  # are always random. Given that currently their JSON representation
  # is proto-serialized and then base64-encoded, there's no way
  # we can replace these URNs with something stable.
  uses_legacy_dynamic_protos = True

  def Run(self):
    client_id = self.SetupClient(0)
    email_descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name=email_plugin.EmailOutputPlugin.__name__,
        plugin_args=email_plugin.EmailOutputPluginArgs(
            email_address="test@localhost", emails_limit=42))

    with test_lib.FakeTime(42):
      flow_id = flow_test_lib.StartAndRunFlow(
          flow_cls=flow_test_lib.DummyFlowWithSingleReply,
          client_id=client_id,
          output_plugins=[email_descriptor])

    self.Check(
        "ListFlowOutputPluginLogs",
        args=flow_plugin.ApiListFlowOutputPluginLogsArgs(
            client_id=client_id,
            flow_id=flow_id,
            plugin_id="EmailOutputPlugin_0"),
        replace={flow_id: "W:ABCDEF"})


class ApiListFlowOutputPluginErrorsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest):
  """Regression test for ApiListFlowOutputPluginErrorsHandler."""

  api_method = "ListFlowOutputPluginErrors"
  handler = flow_plugin.ApiListFlowOutputPluginErrorsHandler

  # ApiOutputPlugin's state is an AttributedDict containing URNs that
  # are always random. Given that currently their JSON representation
  # is proto-serialized and then base64-encoded, there's no way
  # we can replace these URNs with something stable.
  uses_legacy_dynamic_protos = True

  def Run(self):
    client_id = self.SetupClient(0)
    failing_descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name=hunt_test_lib.FailingDummyHuntOutputPlugin.__name__)

    with test_lib.FakeTime(42):
      flow_id = flow_test_lib.StartAndRunFlow(
          flow_cls=flow_test_lib.DummyFlowWithSingleReply,
          client_id=client_id,
          output_plugins=[failing_descriptor])

    self.Check(
        "ListFlowOutputPluginErrors",
        args=flow_plugin.ApiListFlowOutputPluginErrorsArgs(
            client_id=client_id,
            flow_id=flow_id,
            plugin_id="FailingDummyHuntOutputPlugin_0"),
        replace={flow_id: "W:ABCDEF"})


class ApiCreateFlowHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest):
  """Regression test for ApiCreateFlowHandler."""

  api_method = "CreateFlow"
  handler = flow_plugin.ApiCreateFlowHandler

  def Run(self):
    client_id = self.SetupClient(0)

    def ReplaceFlowId():
      flows = data_store.REL_DB.ReadAllFlowObjects(client_id=client_id)
      self.assertNotEmpty(flows)
      flow_id = flows[0].flow_id

      return api_regression_test_lib.GetFlowTestReplaceDict(client_id, flow_id)

    with test_lib.FakeTime(42):
      self.Check(
          "CreateFlow",
          args=flow_plugin.ApiCreateFlowArgs(
              client_id=client_id,
              flow=flow_plugin.ApiFlow(
                  name=processes.ListProcesses.__name__,
                  args=processes.ListProcessesArgs(
                      filename_regex=".", fetch_binaries=True),
                  runner_args=rdf_flow_runner.FlowRunnerArgs(
                      output_plugins=[], notify_to_user=True))),
          replace=ReplaceFlowId)


class ApiCancelFlowHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest):
  """Regression test for ApiCancelFlowHandler."""

  api_method = "CancelFlow"
  handler = flow_plugin.ApiCancelFlowHandler

  def Run(self):
    client_id = self.SetupClient(0)
    with test_lib.FakeTime(42):
      flow_id = flow.StartFlow(
          flow_cls=processes.ListProcesses, client_id=client_id)

    with test_lib.FakeTime(4242):
      self.Check(
          "CancelFlow",
          args=flow_plugin.ApiCancelFlowArgs(
              client_id=client_id, flow_id=flow_id),
          replace={flow_id: "W:ABCDEF"})


class ApiListFlowDescriptorsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, acl_test_lib.AclTestMixin):
  """Regression test for ApiListFlowDescriptorsHandler."""

  api_method = "ListFlowDescriptors"
  handler = flow_plugin.ApiListFlowDescriptorsHandler

  def Run(self):
    test_registry = {
        processes.ListProcesses.__name__: processes.ListProcesses,
        file_finder.FileFinder.__name__: file_finder.FileFinder,
    }

    with utils.Stubber(registry.FlowRegistry, "FLOW_REGISTRY", test_registry):
      self.CreateAdminUser(u"test")
      self.Check("ListFlowDescriptors")


class ApiExplainGlobExpressionHandlerTest(
    api_regression_test_lib.ApiRegressionTest):

  api_method = "ExplainGlobExpression"
  handler = flow_plugin.ApiExplainGlobExpressionHandler

  def Run(self):
    client_id = self.SetupClient(0)
    self.Check(
        "ExplainGlobExpression",
        args=flow_plugin.ApiExplainGlobExpressionArgs(
            client_id=client_id, glob_expression="/foo/*"))


def main(argv):
  api_regression_test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
