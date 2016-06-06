#!/usr/bin/env python
"""This module contains tests for flows-related API handlers."""



import os
import StringIO
import tarfile
import zipfile


import yaml

from grr.gui import api_test_lib
from grr.gui.api_plugins import flow as flow_plugin

from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import flags
from grr.lib import flow
from grr.lib import flow_runner
from grr.lib import output_plugin
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import throttle
from grr.lib import utils
from grr.lib.aff4_objects import collects as aff4_collections
from grr.lib.flows.general import administrative
from grr.lib.flows.general import discovery
from grr.lib.flows.general import file_finder
from grr.lib.flows.general import processes
from grr.lib.flows.general import transfer
from grr.lib.hunts import standard_test
from grr.lib.output_plugins import email_plugin
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths


class ApiGetFlowHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiGetFlowHandler."""

  handler = "ApiGetFlowHandler"

  def Run(self):
    # Fix the time to avoid regressions.
    with test_lib.FakeTime(42):
      client_urn = self.SetupClients(1)[0]

      # Delete the certificates as it's being regenerated every time the
      # client is created.
      with aff4.FACTORY.Open(client_urn, mode="rw",
                             token=self.token) as client_obj:
        client_obj.DeleteAttribute(client_obj.Schema.CERT)

      flow_id = flow.GRRFlow.StartFlow(flow_name=discovery.Interrogate.__name__,
                                       client_id=client_urn,
                                       token=self.token)

      self.Check("GET",
                 "/api/clients/%s/flows/%s" % (client_urn.Basename(),
                                               flow_id.Basename()),
                 replace={flow_id.Basename(): "F:ABCDEF12"})


class ApiListFlowsHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Test client flows list handler."""

  handler = "ApiListFlowsHandler"

  def Run(self):
    with test_lib.FakeTime(42):
      client_urn = self.SetupClients(1)[0]

    with test_lib.FakeTime(43):
      flow_id_1 = flow.GRRFlow.StartFlow(
          flow_name=discovery.Interrogate.__name__,
          client_id=client_urn,
          # TODO(user): output="" has to be specified because otherwise
          # output collection object is created and stored in state.context.
          # When AFF4Object is serialized, it gets serialized as
          # <AFF4Object@[address] blah> which breaks the regression, because
          # the address is always different. Storing AFF4Object in a state
          # is bad, and we should use blind writes to write to the output
          # collection. Remove output="" as soon as the issue is resolved.
          output="",
          token=self.token)

    with test_lib.FakeTime(44):
      flow_id_2 = flow.GRRFlow.StartFlow(
          flow_name=processes.ListProcesses.__name__,
          client_id=client_urn,
          # TODO(user): See comment above regarding output="".
          output="",
          token=self.token)

    self.Check("GET",
               "/api/clients/%s/flows" % client_urn.Basename(),
               replace={flow_id_1.Basename(): "F:ABCDEF10",
                        flow_id_2.Basename(): "F:ABCDEF11"})


class ApiListFlowResultsHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiListFlowResultsHandler."""

  handler = "ApiListFlowResultsHandler"

  def setUp(self):
    super(ApiListFlowResultsHandlerRegressionTest, self).setUp()
    self.client_id = self.SetupClients(1)[0]

  def Run(self):
    runner_args = flow_runner.FlowRunnerArgs(
        flow_name=transfer.GetFile.__name__)

    flow_args = transfer.GetFileArgs(pathspec=rdf_paths.PathSpec(
        path="/tmp/evil.txt",
        pathtype=rdf_paths.PathSpec.PathType.OS))

    client_mock = test_lib.SampleHuntMock()

    with test_lib.FakeTime(42):
      flow_urn = flow.GRRFlow.StartFlow(client_id=self.client_id,
                                        args=flow_args,
                                        runner_args=runner_args,
                                        token=self.token)

      for _ in test_lib.TestFlowHelper(flow_urn,
                                       client_mock=client_mock,
                                       client_id=self.client_id,
                                       token=self.token):
        pass

    self.Check("GET",
               "/api/clients/%s/flows/%s/results" % (self.client_id.Basename(),
                                                     flow_urn.Basename()),
               replace={flow_urn.Basename(): "W:ABCDEF"})


class ApiListFlowLogsHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiListFlowResultsHandler."""

  handler = "ApiListHuntLogsHandler"

  def setUp(self):
    super(ApiListFlowLogsHandlerRegressionTest, self).setUp()
    self.client_id = self.SetupClients(1)[0]

  def Run(self):
    flow_urn = flow.GRRFlow.StartFlow(
        flow_name=processes.ListProcesses.__name__,
        client_id=self.client_id,
        token=self.token)

    with aff4.FACTORY.Open(flow_urn, mode="rw", token=self.token) as flow_obj:
      with test_lib.FakeTime(52):
        flow_obj.Log("Sample message: foo.")

      with test_lib.FakeTime(55):
        flow_obj.Log("Sample message: bar.")

    base_url = "/api/clients/%s/flows/%s/log" % (self.client_id.Basename(),
                                                 flow_urn.Basename())
    replace = {flow_urn.Basename(): "W:ABCDEF"}

    self.Check("GET", base_url, replace=replace)
    self.Check("GET", base_url + "?count=1", replace=replace)
    self.Check("GET", base_url + "?count=1&offset=1", replace=replace)


class ApiGetFlowResultsExportCommandHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiGetFlowResultsExportCommandHandler."""

  handler = "ApiGetFlowResultsExportCommandHandler"

  def setUp(self):
    super(ApiGetFlowResultsExportCommandHandlerRegressionTest, self).setUp()
    self.client_id = self.SetupClients(1)[0]

  def Run(self):
    with test_lib.FakeTime(42):
      flow_urn = flow.GRRFlow.StartFlow(
          flow_name=processes.ListProcesses.__name__,
          client_id=self.client_id,
          token=self.token)

    self.Check("GET",
               "/api/clients/%s/flows/%s/results/export-command" %
               (self.client_id.Basename(), flow_urn.Basename()),
               replace={flow_urn.Basename(): "W:ABCDEF"})


class ApiListFlowOutputPluginsHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiListFlowOutputPluginsHandler."""

  handler = "ApiListFlowOutputPluginsHandler"

  def setUp(self):
    super(ApiListFlowOutputPluginsHandlerRegressionTest, self).setUp()
    self.client_id = self.SetupClients(1)[0]

  def Run(self):
    email_descriptor = output_plugin.OutputPluginDescriptor(
        plugin_name=email_plugin.EmailOutputPlugin.__name__,
        plugin_args=email_plugin.EmailOutputPluginArgs(
            email_address="test@localhost",
            emails_limit=42))

    with test_lib.FakeTime(42):
      flow_urn = flow.GRRFlow.StartFlow(
          flow_name=processes.ListProcesses.__name__,
          client_id=self.client_id,
          output_plugins=[email_descriptor],
          token=self.token)

    self.Check("GET",
               "/api/clients/%s/flows/%s/output-plugins" %
               (self.client_id.Basename(), flow_urn.Basename()),
               replace={flow_urn.Basename(): "W:ABCDEF"})


class DummyFlowWithSingleReply(flow.GRRFlow):
  """Just emits 1 reply."""

  @flow.StateHandler()
  def Start(self, unused_response=None):
    self.CallState(next_state="SendSomething")

  @flow.StateHandler()
  def SendSomething(self, unused_response=None):
    self.SendReply(rdfvalue.RDFString("oh"))


class ApiListFlowOutputPluginLogsHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiListFlowOutputPluginLogsHandler."""

  handler = "ApiListFlowOutputPluginLogsHandler"

  def setUp(self):
    super(ApiListFlowOutputPluginLogsHandlerRegressionTest, self).setUp()
    self.client_id = self.SetupClients(1)[0]

  def Run(self):
    email_descriptor = output_plugin.OutputPluginDescriptor(
        plugin_name=email_plugin.EmailOutputPlugin.__name__,
        plugin_args=email_plugin.EmailOutputPluginArgs(
            email_address="test@localhost",
            emails_limit=42))

    with test_lib.FakeTime(42):
      flow_urn = flow.GRRFlow.StartFlow(
          flow_name=DummyFlowWithSingleReply.__name__,
          client_id=self.client_id,
          output_plugins=[email_descriptor],
          token=self.token)

    with test_lib.FakeTime(43):
      for _ in test_lib.TestFlowHelper(flow_urn, token=self.token):
        pass

    self.Check("GET",
               "/api/clients/%s/flows/%s/output-plugins/"
               "EmailOutputPlugin_0/logs" % (self.client_id.Basename(),
                                             flow_urn.Basename()),
               replace={flow_urn.Basename(): "W:ABCDEF"})


class ApiListFlowOutputPluginErrorsHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiListFlowOutputPluginErrorsHandler."""

  handler = "ApiListFlowOutputPluginErrorsHandler"

  def setUp(self):
    super(ApiListFlowOutputPluginErrorsHandlerRegressionTest, self).setUp()
    self.client_id = self.SetupClients(1)[0]

  def Run(self):
    failing_descriptor = output_plugin.OutputPluginDescriptor(
        plugin_name=standard_test.FailingDummyHuntOutputPlugin.__name__)

    with test_lib.FakeTime(42):
      flow_urn = flow.GRRFlow.StartFlow(
          flow_name=DummyFlowWithSingleReply.__name__,
          client_id=self.client_id,
          output_plugins=[failing_descriptor],
          token=self.token)

    with test_lib.FakeTime(43):
      for _ in test_lib.TestFlowHelper(flow_urn, token=self.token):
        pass

    self.Check("GET",
               "/api/clients/%s/flows/%s/output-plugins/"
               "FailingDummyHuntOutputPlugin_0/errors" %
               (self.client_id.Basename(), flow_urn.Basename()),
               replace={flow_urn.Basename(): "W:ABCDEF"})


class ApiCreateFlowHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiCreateFlowHandler."""

  handler = "ApiCreateFlowHandler"

  def setUp(self):
    super(ApiCreateFlowHandlerRegressionTest, self).setUp()
    self.client_id = self.SetupClients(1)[0]

  def Run(self):

    def ReplaceFlowId():
      flows_dir_fd = aff4.FACTORY.Open(
          self.client_id.Add("flows"),
          token=self.token)
      flow_urn = list(flows_dir_fd.ListChildren())[0]
      return {flow_urn.Basename(): "W:ABCDEF"}

    with test_lib.FakeTime(42):
      self.Check("POST",
                 "/api/clients/%s/flows" % self.client_id.Basename(), {"flow": {
                     "name": processes.ListProcesses.__name__,
                     "args": {
                         "filename_regex": ".",
                         "fetch_binaries": True
                     },
                     "runner_args": {
                         "output_plugins": [],
                         "priority": "HIGH_PRIORITY",
                         "notify_to_user": False,
                     },
                 }},
                 replace=ReplaceFlowId)


class ApiCancelFlowHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiCancelFlowHandler."""

  handler = "ApiCancelFlowHandler"

  def setUp(self):
    super(ApiCancelFlowHandlerRegressionTest, self).setUp()
    self.client_id = self.SetupClients(1)[0]

  def Run(self):
    with test_lib.FakeTime(42):
      flow_urn = flow.GRRFlow.StartFlow(
          flow_name=processes.ListProcesses.__name__,
          client_id=self.client_id,
          token=self.token)

    self.Check("POST",
               "/api/clients/%s/flows/%s/actions/cancel" %
               (self.client_id.Basename(), flow_urn.Basename()),
               replace={flow_urn.Basename(): "W:ABCDEF"})


class ApiListFlowDescriptorsHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiListFlowDescriptorsHandler."""

  handler = "ApiListFlowDescriptorsHandler"

  def Run(self):
    with utils.Stubber(flow.GRRFlow, "classes", {
        "ListProcesses": processes.ListProcesses,
        "FileFinder": file_finder.FileFinder,
        "RunReport": administrative.RunReport
    }):
      # RunReport flow is only shown for admins.
      self.CreateAdminUser("test")

      self.Check("GET", "/api/flows/descriptors")
      self.Check("GET", "/api/flows/descriptors?flow_type=client")
      self.Check("GET", "/api/flows/descriptors?flow_type=global")


class ApiStartRobotGetFilesOperationHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  handler = "ApiStartRobotGetFilesOperationHandler"

  def setUp(self):
    super(ApiStartRobotGetFilesOperationHandlerRegressionTest, self).setUp()
    self.client_id = self.SetupClients(1)[0]

  def Run(self):

    def ReplaceFlowId():
      flows_dir_fd = aff4.FACTORY.Open(
          self.client_id.Add("flows"),
          token=self.token)
      flow_urn = list(flows_dir_fd.ListChildren())[0]
      return {flow_urn.Basename(): "W:ABCDEF"}

    with test_lib.FakeTime(42):
      self.Check("POST",
                 "/api/robot-actions/get-files",
                 {"hostname": self.client_id.Basename(),
                  "paths": ["/tmp/test"]},
                 replace=ReplaceFlowId)


class ApiStartRobotGetFilesOperationHandlerTest(test_lib.GRRBaseTest):
  """Test for ApiStartRobotGetFilesOperationHandler."""

  def setUp(self):
    super(ApiStartRobotGetFilesOperationHandlerTest, self).setUp()
    self.client_ids = self.SetupClients(4)
    self.handler = flow_plugin.ApiStartRobotGetFilesOperationHandler()

  def testClientLookup(self):
    """When multiple clients match, check we run on the latest one."""
    args = flow_plugin.ApiStartRobotGetFilesOperationArgs(hostname="Host",
                                                          paths=["/test"])
    result = self.handler.Handle(args, token=self.token)
    # Here we exploit the fact that operation_id is effectively a flow URN.
    self.assertIn("C.1000000000000003", result.operation_id)

  def testThrottle(self):
    """Calling the same flow should raise."""
    args = flow_plugin.ApiStartRobotGetFilesOperationArgs(hostname="Host",
                                                          paths=["/test"])
    self.handler.Handle(args, token=self.token)

    with self.assertRaises(throttle.ErrorFlowDuplicate):
      self.handler.Handle(args, token=self.token)


class ApiGetRobotGetFilesOperationStateHandlerTest(test_lib.GRRBaseTest):
  """Test for ApiGetRobotGetFilesOperationStateHandler."""

  def setUp(self):
    super(ApiGetRobotGetFilesOperationStateHandlerTest, self).setUp()
    self.client_id = self.SetupClients(1)[0]
    self.handler = flow_plugin.ApiGetRobotGetFilesOperationStateHandler()

  def testValidatesFlowId(self):
    """Check bad flows id is rejected.

    Make sure our input is validated because this API doesn't require
    authorization.
    """
    bad_opid = flow_plugin.ApiGetRobotGetFilesOperationStateArgs(
        operation_id=utils.SmartUnicode(self.client_id.Add("flows").Add(
            "X:<script>")))
    with self.assertRaises(ValueError):
      self.handler.Handle(bad_opid, token=self.token)

  def testValidatesClientId(self):
    """Check bad client id is rejected.

    Make sure our input is validated because this API doesn't require
    authorization.
    """
    bad_opid = flow_plugin.ApiGetRobotGetFilesOperationStateArgs(
        operation_id="aff4:/C.1234546<script>/flows/X:12345678")
    with self.assertRaises(ValueError):
      self.handler.Handle(bad_opid, token=self.token)

  def testRaisesIfNoFlowIsFound(self):
    bad_opid = flow_plugin.ApiGetRobotGetFilesOperationStateArgs(
        operation_id=utils.SmartUnicode(self.client_id.Add("flows").Add(
            "X:123456")))
    with self.assertRaises(flow_plugin.RobotGetFilesOperationNotFoundError):
      self.handler.Handle(bad_opid, token=self.token)

  def testRaisesIfFlowIsNotFileFinder(self):
    flow_id = flow.GRRFlow.StartFlow(flow_name=processes.ListProcesses.__name__,
                                     client_id=self.client_id,
                                     token=self.token)

    bad_opid = flow_plugin.ApiGetRobotGetFilesOperationStateArgs(
        operation_id=utils.SmartUnicode(flow_id))
    with self.assertRaises(flow_plugin.RobotGetFilesOperationNotFoundError):
      self.handler.Handle(bad_opid, token=self.token)

  def testReturnsCorrectResultIfFlowIsFileFinder(self):
    flow_id = flow.GRRFlow.StartFlow(flow_name=file_finder.FileFinder.__name__,
                                     paths=["/*"],
                                     client_id=self.client_id,
                                     token=self.token)

    opid = flow_plugin.ApiGetRobotGetFilesOperationStateArgs(
        operation_id=utils.SmartUnicode(flow_id))
    result = self.handler.Handle(opid, token=self.token)
    self.assertEqual(result.state, "RUNNING")
    self.assertEqual(result.result_count, 0)


class ApiGetRobotGetFilesOperationStateHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Test flow status handler.

  This handler is disabled by default in the ACLs so we need to do some
  patching to get the proper output and not just "access denied".
  """
  handler = "ApiGetRobotGetFilesOperationStateHandler"

  def Run(self):
    # Fix the time to avoid regressions.
    with test_lib.FakeTime(42):
      self.SetupClients(1)

      start_handler = flow_plugin.ApiStartRobotGetFilesOperationHandler()
      start_args = flow_plugin.ApiStartRobotGetFilesOperationArgs(
          hostname="Host", paths=["/test"])
      start_result = start_handler.Handle(start_args, token=self.token)

      # Exploit the fact that 'get files' operation id is effectively a flow
      # URN.
      flow_urn = rdfvalue.RDFURN(start_result.operation_id)

      # Put something in the output collection
      flow_obj = aff4.FACTORY.Open(flow_urn,
                                   aff4_type=flow.GRRFlow,
                                   token=self.token)
      flow_state = flow_obj.Get(flow_obj.Schema.FLOW_STATE)

      with aff4.FACTORY.Create(flow_state.context.output_urn,
                               aff4_type=aff4_collections.RDFValueCollection,
                               token=self.token) as collection:
        collection.Add(rdf_client.ClientSummary())

      self.Check("GET",
                 "/api/robot-actions/get-files/%s" % start_result.operation_id,
                 replace={flow_urn.Basename(): "F:ABCDEF12"})


class ApiGetFlowFilesArchiveHandlerTest(test_lib.GRRBaseTest):
  """Tests for ApiGetFlowFilesArchiveHandler."""

  def setUp(self):
    super(ApiGetFlowFilesArchiveHandlerTest, self).setUp()

    self.handler = flow_plugin.ApiGetFlowFilesArchiveHandler()

    self.client_id = self.SetupClients(1)[0]

    self.flow_urn = flow.GRRFlow.StartFlow(
        flow_name=file_finder.FileFinder.__name__,
        client_id=self.client_id,
        paths=[os.path.join(self.base_path, "test.plist")],
        action=file_finder.FileFinderAction(action_type="DOWNLOAD"),
        token=self.token)
    action_mock = action_mocks.ActionMock("TransferBuffer", "StatFile",
                                          "HashFile", "HashBuffer")
    for _ in test_lib.TestFlowHelper(self.flow_urn,
                                     action_mock,
                                     client_id=self.client_id,
                                     token=self.token):
      pass

  def testGeneratesZipArchive(self):
    result = self.handler.Handle(
        flow_plugin.ApiGetFlowFilesArchiveArgs(client_id=self.client_id,
                                               flow_id=self.flow_urn.Basename(),
                                               archive_format="ZIP"),
        token=self.token)

    out_fd = StringIO.StringIO()
    for chunk in result.GenerateContent():
      out_fd.write(chunk)

    zip_fd = zipfile.ZipFile(out_fd, "r")
    manifest = None
    for name in zip_fd.namelist():
      if name.endswith("MANIFEST"):
        manifest = yaml.safe_load(zip_fd.read(name))

    self.assertEqual(manifest["archived_files"], 1)
    self.assertEqual(manifest["failed_files"], 0)
    self.assertEqual(manifest["processed_files"], 1)
    self.assertEqual(manifest["skipped_files"], 0)

  def testGeneratesTarGzArchive(self):
    result = self.handler.Handle(
        flow_plugin.ApiGetFlowFilesArchiveArgs(client_id=self.client_id,
                                               flow_id=self.flow_urn.Basename(),
                                               archive_format="TAR_GZ"),
        token=self.token)

    with utils.TempDirectory() as temp_dir:
      tar_path = os.path.join(temp_dir, "archive.tar.gz")
      with open(tar_path, "w") as fd:
        for chunk in result.GenerateContent():
          fd.write(chunk)

      with tarfile.open(tar_path) as tar_fd:
        tar_fd.extractall(path=temp_dir)

      manifest_file_path = None
      for parent, _, files in os.walk(temp_dir):
        if "MANIFEST" in files:
          manifest_file_path = os.path.join(parent, "MANIFEST")
          break

      self.assertTrue(manifest_file_path)
      with open(manifest_file_path) as fd:
        manifest = yaml.safe_load(fd.read())

        self.assertEqual(manifest["archived_files"], 1)
        self.assertEqual(manifest["failed_files"], 0)
        self.assertEqual(manifest["processed_files"], 1)
        self.assertEqual(manifest["skipped_files"], 0)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
