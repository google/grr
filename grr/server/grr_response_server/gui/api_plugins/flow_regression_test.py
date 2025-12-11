#!/usr/bin/env python
"""This module contains regression tests for flows-related API handlers."""

from unittest import mock

from absl import app

from google.protobuf import any_pb2
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_proto import flows_pb2
from grr_response_proto import objects_pb2
from grr_response_proto.api import flow_pb2 as api_flow_pb2
from grr_response_server import access_control
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server import flow_base
from grr_response_server.flows.general import discovery
from grr_response_server.flows.general import file_finder
from grr_response_server.flows.general import processes
from grr_response_server.gui import api_regression_test_lib
from grr_response_server.gui.api_plugins import flow as flow_plugin
from grr_response_server.output_plugins import email_plugin
from grr_response_server.rdfvalues import output_plugin as rdf_output_plugin
from grr.test_lib import acl_test_lib
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import test_lib


class ApiGetFlowHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest
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
          network_bytes_limit=8192,
          cpu_limit=60,
          creator=self.test_username,
      )

      child_flows = data_store.REL_DB.ReadChildFlowObjects(client_id, flow_id)

      replace = api_regression_test_lib.GetFlowTestReplaceDict(
          client_id, flow_id, "F:ABCDEF12"
      )
      for i, child_flow in enumerate(child_flows):
        replace[child_flow.flow_id] = f"F:FFFFFF{i:02X}"

      # ApiV1 (RDFValues) serializes the `store` field in the flow object in the
      # database as bytes. The `store` here contains the source flow id, and
      # thus, the bytes change on every run.
      # To avoid this, we update the `store` field in the flow object in the
      # database, so it has an empty store.
      # Before that, though, we want to make sure that the `store` field is
      # actually set with what we want, so we test it here.
      # This is not an issue in ApiV2 (protos) so all this can be removed once
      # we remove ApiV1.
      flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
      interrogate_store = flows_pb2.InterrogateStore()
      flow_obj.store.Unpack(interrogate_store)
      want_store = flows_pb2.InterrogateStore(
          client_snapshot=objects_pb2.ClientSnapshot(
              client_id=client_id,
              metadata=objects_pb2.ClientSnapshotMetadata(
                  source_flow_id=flow_id
              ),
          )
      )
      self.assertEqual(want_store, interrogate_store)
      api_regression_test_lib.UpdateFlowStore(
          client_id, flow_id, flows_pb2.InterrogateStore()
      )

      self.Check(
          "GetFlow",
          args=api_flow_pb2.ApiGetFlowArgs(
              client_id=client_id, flow_id=flow_id
          ),
          replace=replace,
      )

      flow_base.TerminateFlow(
          client_id, flow_id, "Pending termination: Some reason"
      )

      replace = api_regression_test_lib.GetFlowTestReplaceDict(
          client_id, flow_id, "F:ABCDEF13"
      )
      for i, child_flow in enumerate(child_flows):
        replace[child_flow.flow_id] = f"F.EEEEEE{i:02X}"

      # Fetch the same flow which is now should be marked as pending
      # termination.
      self.Check(
          "GetFlow",
          args=api_flow_pb2.ApiGetFlowArgs(
              client_id=client_id, flow_id=flow_id
          ),
          replace=replace,
      )


class ApiListFlowsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest
):
  """Test client flows list handler."""

  api_method = "ListFlows"
  handler = flow_plugin.ApiListFlowsHandler

  def Run(self):
    acl_test_lib.CreateUser(self.test_username)
    with test_lib.FakeTime(42):
      client_id = self.SetupClient(0)

    with test_lib.FakeTime(43):
      flow_id_1 = flow_test_lib.StartFlow(
          discovery.Interrogate, client_id, creator=self.test_username
      )

    with test_lib.FakeTime(44):
      flow_id_2 = flow_test_lib.StartFlow(
          processes.ListProcesses,
          client_id,
          creator=access_control._SYSTEM_USERS_LIST[0],
      )

    with test_lib.FakeTime(45):
      flow_id_3 = flow_test_lib.StartFlow(
          flow_test_lib.FlowWithTwoLevelsOfNestedFlows,
          client_id,
          creator=self.test_username,
      )

    # ApiV1 (RDFValues) serializes the `store` field in the flow object in the
    # database as bytes. The `store` here contains the source flow id, and thus,
    # the bytes change on every run.
    # To avoid this, we update the `store` field in the flow object in the
    # database, so it has an empty store.
    # Before that, though, we want to make sure that the `store` field is
    # actually set with what we want, so we test it here.
    # This is not an issue in ApiV2 (protos) so all this can be removed once
    # we remove ApiV1.
    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id_1)
    interrogate_store = flows_pb2.InterrogateStore()
    flow_obj.store.Unpack(interrogate_store)
    want_store = flows_pb2.InterrogateStore(
        client_snapshot=objects_pb2.ClientSnapshot(
            client_id=client_id,
            metadata=objects_pb2.ClientSnapshotMetadata(
                source_flow_id=flow_id_1
            ),
        )
    )
    self.assertEqual(want_store, interrogate_store)
    with test_lib.FakeTime(43):
      api_regression_test_lib.UpdateFlowStore(
          client_id, flow_id_1, flows_pb2.InterrogateStore()
      )

    replace = api_regression_test_lib.GetFlowTestReplaceDict(
        client_id, flow_id_1, "F:ABCDEF10"
    )
    replace.update(
        api_regression_test_lib.GetFlowTestReplaceDict(
            client_id, flow_id_2, "F:ABCDEF11"
        )
    )

    # Flow 3 has two nested flows. We need to find the nested flow ids to
    # replace them in the response.
    nested_flow_id, double_nested_flow_id = None, None
    flow_objects = data_store.REL_DB.ReadAllFlowObjects(client_id)
    for f in flow_objects:
      if f.parent_flow_id == flow_id_3:
        nested_flow_id = f.flow_id
        break
    for f in flow_objects:
      if f.parent_flow_id == nested_flow_id:
        double_nested_flow_id = f.flow_id
        break

    replace.update(
        api_regression_test_lib.GetFlowTestReplaceDict(
            client_id, flow_id_3, "F:ABCDEF12"
        )
    )
    replace.update(
        api_regression_test_lib.GetFlowTestReplaceDict(
            client_id, nested_flow_id, "F:ABCDEF13"
        )
    )
    replace.update(
        api_regression_test_lib.GetFlowTestReplaceDict(
            client_id, double_nested_flow_id, "F:ABCDEF14"
        )
    )

    interrogate_child_flows = data_store.REL_DB.ReadChildFlowObjects(
        client_id=client_id,
        flow_id=flow_id_1,
    )
    for i, interrogate_child_flow in enumerate(interrogate_child_flows):
      replace[interrogate_child_flow.flow_id] = f"F:FFFFFF{i:02X}"

    self.Check(
        "ListFlows",
        args=api_flow_pb2.ApiListFlowsArgs(client_id=client_id),
        replace=replace,
    )

    self.Check(
        "ListFlows",
        args=api_flow_pb2.ApiListFlowsArgs(
            client_id=client_id,
            top_flows_only=True,
        ),
        replace=replace,
    )

    self.Check(
        "ListFlows",
        args=api_flow_pb2.ApiListFlowsArgs(
            client_id=client_id,
            min_started_at=rdfvalue.RDFDatetimeSeconds(
                44
            ).AsMicrosecondsSinceEpoch(),
            top_flows_only=True,
        ),
        replace=replace,
    )

    self.Check(
        "ListFlows",
        args=api_flow_pb2.ApiListFlowsArgs(
            client_id=client_id,
            max_started_at=rdfvalue.RDFDatetimeSeconds(
                43
            ).AsMicrosecondsSinceEpoch(),
            top_flows_only=True,
        ),
        replace=replace,
    )

    self.Check(
        "ListFlows",
        args=api_flow_pb2.ApiListFlowsArgs(
            client_id=client_id,
            human_flows_only=True,
        ),
        replace=replace,
    )


class ApiListFlowRequestsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest
):
  """Regression test for ApiListFlowRequestsHandler."""

  api_method = "ListFlowRequests"
  handler = flow_plugin.ApiListFlowRequestsHandler

  def Run(self):
    client_id = self.SetupClient(0)
    with test_lib.FakeTime(42):
      flow_id = flow_test_lib.StartFlow(
          processes.ListProcesses, client_id, creator=self.test_username
      )
      test_process = rdf_client.Process(name="test_process")
      mock_client = flow_test_lib.MockClient(
          client_id, action_mocks.ListProcessesMock([test_process])
      )
      mock_client.Next()

    replace = api_regression_test_lib.GetFlowTestReplaceDict(client_id, flow_id)

    self.Check(
        "ListFlowRequests",
        args=api_flow_pb2.ApiListFlowRequestsArgs(
            client_id=client_id, flow_id=flow_id
        ),
        replace=replace,
    )


class ApiListFlowResultsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest
):
  """Regression test for ApiListFlowResultsHandler."""

  api_method = "ListFlowResults"
  handler = flow_plugin.ApiListFlowResultsHandler

  def _RunFlow(self, client_id):
    flow_args = rdf_file_finder.FileFinderArgs()
    flow_args.paths = ["/tmp/evil.txt"]
    client_mock = hunt_test_lib.SampleHuntMock(failrate=2)

    with test_lib.FakeTime(42):
      return flow_test_lib.StartAndRunFlow(
          file_finder.ClientFileFinder,
          client_id=client_id,
          client_mock=client_mock,
          flow_args=flow_args,
      )

  def Run(self):
    acl_test_lib.CreateUser(self.test_username)
    client_id = self.SetupClient(0)

    flow_id = self._RunFlow(client_id)
    self.Check(
        "ListFlowResults",
        args=api_flow_pb2.ApiListFlowResultsArgs(
            client_id=client_id, flow_id=flow_id, filter="evil"
        ),
        replace={flow_id: "W:ABCDEF"},
    )
    self.Check(
        "ListFlowResults",
        args=api_flow_pb2.ApiListFlowResultsArgs(
            client_id=client_id, flow_id=flow_id, filter="benign"
        ),
        replace={flow_id: "W:ABCDEF"},
    )


class ApiListFlowLogsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest
):
  """Regression test for ApiListFlowResultsHandler."""

  api_method = "ListFlowLogs"
  handler = flow_plugin.ApiListFlowLogsHandler

  def _AddLogToFlow(self, client_id, flow_id, log_string):
    entry = flows_pb2.FlowLogEntry(
        client_id=client_id, flow_id=flow_id, message=log_string
    )
    data_store.REL_DB.WriteFlowLogEntry(entry)

  def Run(self):
    client_id = self.SetupClient(0)

    flow_id = flow_test_lib.StartFlow(
        processes.ListProcesses, client_id, creator=self.test_username
    )

    with test_lib.FakeTime(52):
      self._AddLogToFlow(client_id, flow_id, "Sample message: foo.")

    with test_lib.FakeTime(55):
      self._AddLogToFlow(client_id, flow_id, "Sample message: bar.")

    replace = {flow_id: "W:ABCDEF"}
    self.Check(
        "ListFlowLogs",
        args=api_flow_pb2.ApiListFlowLogsArgs(
            client_id=client_id, flow_id=flow_id
        ),
        replace=replace,
    )
    self.Check(
        "ListFlowLogs",
        args=api_flow_pb2.ApiListFlowLogsArgs(
            client_id=client_id, flow_id=flow_id, count=1
        ),
        replace=replace,
    )
    self.Check(
        "ListFlowLogs",
        args=api_flow_pb2.ApiListFlowLogsArgs(
            client_id=client_id, flow_id=flow_id, count=1, offset=1
        ),
        replace=replace,
    )


class ApiGetFlowResultsExportCommandHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest
):
  """Regression test for ApiGetFlowResultsExportCommandHandler."""

  api_method = "GetFlowResultsExportCommand"
  handler = flow_plugin.ApiGetFlowResultsExportCommandHandler

  def Run(self):
    client_id = self.SetupClient(0)
    flow_urn = "F:ABCDEF"

    self.Check(
        "GetFlowResultsExportCommand",
        args=api_flow_pb2.ApiGetFlowResultsExportCommandArgs(
            client_id=client_id, flow_id=flow_urn
        ),
    )


class ApiListFlowOutputPluginsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest
):
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
        args=email_plugin.EmailOutputPluginArgs(email_address="test@localhost"),
    )

    with test_lib.FakeTime(42):
      flow_id = flow.StartFlow(
          flow_cls=processes.ListProcesses,
          client_id=client_id,
          output_plugins=[email_descriptor],
      )

    self.Check(
        "ListFlowOutputPlugins",
        args=api_flow_pb2.ApiListFlowOutputPluginsArgs(
            client_id=client_id, flow_id=flow_id
        ),
        replace={flow_id: "W:ABCDEF"},
    )


class ApiListFlowOutputPluginLogsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest
):
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
        args=email_plugin.EmailOutputPluginArgs(
            email_address="test@localhost",
        ),
    )

    with test_lib.FakeTime(42):
      flow_id = flow_test_lib.StartAndRunFlow(
          flow_cls=flow_test_lib.DummyFlowWithSingleReply,
          client_id=client_id,
          output_plugins=[email_descriptor],
      )

    self.Check(
        "ListFlowOutputPluginLogs",
        args=api_flow_pb2.ApiListFlowOutputPluginLogsArgs(
            client_id=client_id,
            flow_id=flow_id,
            plugin_id="EmailOutputPlugin_0",
        ),
        replace={flow_id: "W:ABCDEF"},
    )


class ApiListFlowOutputPluginErrorsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest
):
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
        plugin_name=hunt_test_lib.FailingDummyHuntOutputPlugin.__name__
    )

    with test_lib.FakeTime(42):
      flow_id = flow_test_lib.StartAndRunFlow(
          flow_cls=flow_test_lib.DummyFlowWithSingleReply,
          client_id=client_id,
          output_plugins=[failing_descriptor],
      )

    self.Check(
        "ListFlowOutputPluginErrors",
        args=api_flow_pb2.ApiListFlowOutputPluginErrorsArgs(
            client_id=client_id,
            flow_id=flow_id,
            plugin_id="FailingDummyHuntOutputPlugin_0",
        ),
        replace={flow_id: "W:ABCDEF"},
    )


class ApiCreateFlowHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest
):
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
      flow_args = flows_pb2.ListProcessesArgs(
          filename_regex=".", fetch_binaries=True
      )
      packed_args = any_pb2.Any()
      packed_args.Pack(flow_args)
      self.Check(
          "CreateFlow",
          args=api_flow_pb2.ApiCreateFlowArgs(
              client_id=client_id,
              flow=api_flow_pb2.ApiFlow(
                  name=processes.ListProcesses.__name__,
                  args=packed_args,
                  runner_args=flows_pb2.FlowRunnerArgs(output_plugins=[]),
              ),
          ),
          replace=ReplaceFlowId,
      )


class ApiCancelFlowHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest
):
  """Regression test for ApiCancelFlowHandler."""

  api_method = "CancelFlow"
  handler = flow_plugin.ApiCancelFlowHandler

  def Run(self):
    client_id = self.SetupClient(0)
    with test_lib.FakeTime(42):
      flow_id = flow.StartFlow(
          flow_cls=processes.ListProcesses, client_id=client_id
      )

    with test_lib.FakeTime(4242):
      self.Check(
          "CancelFlow",
          args=api_flow_pb2.ApiCancelFlowArgs(
              client_id=client_id, flow_id=flow_id
          ),
          replace={flow_id: "W:ABCDEF"},
      )


class ApiListFlowDescriptorsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, acl_test_lib.AclTestMixin
):
  """Regression test for ApiListFlowDescriptorsHandler."""

  api_method = "ListFlowDescriptors"
  handler = flow_plugin.ApiListFlowDescriptorsHandler

  def Run(self):
    test_registry = {
        processes.ListProcesses.__name__: processes.ListProcesses,
        file_finder.FileFinder.__name__: file_finder.FileFinder,
    }

    with mock.patch.object(
        registry.FlowRegistry, "FLOW_REGISTRY", test_registry
    ):
      self.CreateAdminUser("test")
      self.Check("ListFlowDescriptors")


class ApiExplainGlobExpressionHandlerTest(
    api_regression_test_lib.ApiRegressionTest
):

  api_method = "ExplainGlobExpression"
  handler = flow_plugin.ApiExplainGlobExpressionHandler

  def Run(self):
    client_id = self.SetupClient(0)
    self.Check(
        "ExplainGlobExpression",
        args=api_flow_pb2.ApiExplainGlobExpressionArgs(
            client_id=client_id, glob_expression="/foo/*"
        ),
    )


def main(argv):
  api_regression_test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
