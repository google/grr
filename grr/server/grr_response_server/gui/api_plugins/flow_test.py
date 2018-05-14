#!/usr/bin/env python
"""This module contains tests for flows-related API handlers."""

import os
import StringIO
import tarfile
import zipfile


import yaml

from grr.lib import flags
from grr.lib import utils
from grr.lib.rdfvalues import file_finder as rdf_file_finder

from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import test_base as rdf_test_base
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import flow
from grr.server.grr_response_server.flows.general import file_finder
from grr.server.grr_response_server.flows.general import processes
from grr.server.grr_response_server.gui import api_test_lib
from grr.server.grr_response_server.gui.api_plugins import client as client_plugin
from grr.server.grr_response_server.gui.api_plugins import flow as flow_plugin
from grr.server.grr_response_server.hunts import implementation
from grr.server.grr_response_server.hunts import standard
from grr.server.grr_response_server.output_plugins import test_plugins
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import test_lib


class ApiFlowIdTest(rdf_test_base.RDFValueTestMixin,
                    hunt_test_lib.StandardHuntTestMixin, test_lib.GRRBaseTest):
  """Test for ApiFlowId."""

  rdfvalue_class = flow_plugin.ApiFlowId

  def setUp(self):
    super(ApiFlowIdTest, self).setUp()
    self.client_urn = self.SetupClient(0)

  def GenerateSample(self, number=0):
    return flow_plugin.ApiFlowId("F:" + "123" * (number + 1))

  def testRaisesWhenInitializedFromInvalidValues(self):
    with self.assertRaises(ValueError):
      flow_plugin.ApiFlowId("blah")

    with self.assertRaises(ValueError):
      flow_plugin.ApiFlowId("foo/bar")

  def testResolvesSimpleFlowURN(self):
    flow_urn = flow.GRRFlow.StartFlow(
        flow_name=flow_test_lib.FlowWithOneNestedFlow.__name__,
        client_id=self.client_urn,
        token=self.token)
    flow_id = flow_plugin.ApiFlowId(flow_urn.Basename())

    self.assertEqual(
        flow_id.ResolveClientFlowURN(
            client_plugin.ApiClientId(self.client_urn), token=self.token),
        flow_urn)

  def testResolvesNestedFlowURN(self):
    flow_urn = flow.GRRFlow.StartFlow(
        flow_name=flow_test_lib.FlowWithOneNestedFlow.__name__,
        client_id=self.client_urn,
        token=self.token)

    children = list(
        aff4.FACTORY.MultiOpen(
            list(aff4.FACTORY.ListChildren(flow_urn)),
            aff4_type=flow.GRRFlow,
            token=self.token))
    self.assertEqual(len(children), 1)

    flow_id = flow_plugin.ApiFlowId(flow_urn.Basename() + "/" + children[0]
                                    .urn.Basename())
    self.assertEqual(
        flow_id.ResolveClientFlowURN(
            client_plugin.ApiClientId(self.client_urn), token=self.token),
        children[0].urn)

  def _StartHunt(self):
    with implementation.GRRHunt.StartHunt(
        hunt_name=standard.GenericHunt.__name__,
        flow_runner_args=rdf_flows.FlowRunnerArgs(
            flow_name=flow_test_lib.FlowWithOneNestedFlow.__name__),
        client_rate=0,
        token=self.token) as hunt:
      hunt.Run()

    self.AssignTasksToClients(client_ids=[self.client_urn])
    self.RunHunt(client_ids=[self.client_urn])

  def testResolvesHuntFlowURN(self):
    self._StartHunt()

    client_flows_urns = list(
        aff4.FACTORY.ListChildren(self.client_urn.Add("flows")))
    self.assertEqual(len(client_flows_urns), 1)

    flow_id = flow_plugin.ApiFlowId(client_flows_urns[0].Basename())
    self.assertEqual(
        flow_id.ResolveClientFlowURN(
            client_plugin.ApiClientId(self.client_urn), token=self.token),
        client_flows_urns[0])

  def testResolvesNestedHuntFlowURN(self):
    self._StartHunt()

    client_flows_urns = list(
        aff4.FACTORY.ListChildren(self.client_urn.Add("flows")))
    self.assertEqual(len(client_flows_urns), 1)

    flow_fd = aff4.FACTORY.Open(client_flows_urns[0], token=self.token)
    nested_flows_urns = list(flow_fd.ListChildren())
    nested_flows = list(
        aff4.FACTORY.MultiOpen(
            nested_flows_urns, aff4_type=flow.GRRFlow, token=self.token))
    self.assertEqual(len(nested_flows), 1)

    flow_id = flow_plugin.ApiFlowId(client_flows_urns[0].Basename() + "/" +
                                    nested_flows[0].urn.Basename())
    self.assertEqual(
        flow_id.ResolveClientFlowURN(
            client_plugin.ApiClientId(self.client_urn), token=self.token),
        nested_flows[0].urn)


class ApiFlowTest(test_lib.GRRBaseTest):
  """Test for ApiFlow."""

  def testInitializesClientIdForClientBasedFlows(self):
    client_id = self.SetupClient(0)
    flow_urn = flow.GRRFlow.StartFlow(
        # Override base session id, so that the flow URN looks
        # like: aff4:/F:112233
        base_session_id="aff4:/",
        client_id=client_id,
        flow_name=processes.ListProcesses.__name__,
        token=self.token)
    flow_obj = aff4.FACTORY.Open(flow_urn, token=self.token)
    flow_api_obj = flow_plugin.ApiFlow().InitFromAff4Object(
        flow_obj, flow_id=flow_urn.Basename())

    self.assertIsNone(flow_api_obj.client_id)

  def testLeavesClientIdEmptyForNonClientBasedFlows(self):
    client_id = self.SetupClient(0)
    flow_urn = flow.GRRFlow.StartFlow(
        client_id=client_id,
        flow_name=processes.ListProcesses.__name__,
        token=self.token)
    flow_obj = aff4.FACTORY.Open(flow_urn, token=self.token)
    flow_api_obj = flow_plugin.ApiFlow().InitFromAff4Object(
        flow_obj, flow_id=flow_urn.Basename())

    self.assertEquals(flow_api_obj.client_id,
                      client_plugin.ApiClientId(client_id))


class ApiCreateFlowHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Test for ApiCreateFlowHandler."""

  def setUp(self):
    super(ApiCreateFlowHandlerTest, self).setUp()
    self.client_id = self.SetupClient(0)
    self.handler = flow_plugin.ApiCreateFlowHandler()

  def testRunnerArgsBaseSessionIdDoesNotAffectCreatedFlow(self):
    """When multiple clients match, check we run on the latest one."""
    flow_runner_args = rdf_flows.FlowRunnerArgs(base_session_id="aff4:/foo")
    args = flow_plugin.ApiCreateFlowArgs(
        client_id=self.client_id.Basename(),
        flow=flow_plugin.ApiFlow(
            name=processes.ListProcesses.__name__,
            runner_args=flow_runner_args))

    result = self.handler.Handle(args, token=self.token)
    self.assertFalse(utils.SmartStr(result.urn).startswith("aff4:/foo"))


class ApiGetFlowFilesArchiveHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Tests for ApiGetFlowFilesArchiveHandler."""

  def setUp(self):
    super(ApiGetFlowFilesArchiveHandlerTest, self).setUp()

    self.handler = flow_plugin.ApiGetFlowFilesArchiveHandler()

    self.client_id = self.SetupClient(0)

    self.flow_urn = flow.GRRFlow.StartFlow(
        flow_name=file_finder.FileFinder.__name__,
        client_id=self.client_id,
        paths=[os.path.join(self.base_path, "test.plist")],
        action=rdf_file_finder.FileFinderAction(action_type="DOWNLOAD"),
        token=self.token)
    action_mock = action_mocks.FileFinderClientMock()
    flow_test_lib.TestFlowHelper(
        self.flow_urn, action_mock, client_id=self.client_id, token=self.token)

  def _GetZipManifest(self, result):
    out_fd = StringIO.StringIO()

    for chunk in result.GenerateContent():
      out_fd.write(chunk)

    zip_fd = zipfile.ZipFile(out_fd, "r")
    for name in zip_fd.namelist():
      if name.endswith("MANIFEST"):
        return yaml.safe_load(zip_fd.read(name))

    return None

  def testGeneratesZipArchive(self):
    result = self.handler.Handle(
        flow_plugin.ApiGetFlowFilesArchiveArgs(
            client_id=self.client_id,
            flow_id=self.flow_urn.Basename(),
            archive_format="ZIP"),
        token=self.token)
    manifest = self._GetZipManifest(result)

    self.assertEqual(manifest["archived_files"], 1)
    self.assertEqual(manifest["failed_files"], 0)
    self.assertEqual(manifest["processed_files"], 1)
    self.assertEqual(manifest["ignored_files"], 0)

  def testIgnoresFileNotMatchingPathGlobsWhitelist(self):
    handler = flow_plugin.ApiGetFlowFilesArchiveHandler(
        path_globs_blacklist=[],
        path_globs_whitelist=[rdf_paths.GlobExpression("/**/foo.bar")])
    result = handler.Handle(
        flow_plugin.ApiGetFlowFilesArchiveArgs(
            client_id=self.client_id,
            flow_id=self.flow_urn.Basename(),
            archive_format="ZIP"),
        token=self.token)
    manifest = self._GetZipManifest(result)
    self.assertEqual(manifest["archived_files"], 0)
    self.assertEqual(manifest["failed_files"], 0)
    self.assertEqual(manifest["processed_files"], 1)
    self.assertEqual(manifest["ignored_files"], 1)
    self.assertEqual(manifest["ignored_files_list"], [
        utils.SmartUnicode(
            self.client_id.Add("fs/os").Add(self.base_path).Add("test.plist"))
    ])

  def testArchivesFileMatchingPathGlobsWhitelist(self):
    handler = flow_plugin.ApiGetFlowFilesArchiveHandler(
        path_globs_blacklist=[],
        path_globs_whitelist=[rdf_paths.GlobExpression("/**/*/test.plist")])
    result = handler.Handle(
        flow_plugin.ApiGetFlowFilesArchiveArgs(
            client_id=self.client_id,
            flow_id=self.flow_urn.Basename(),
            archive_format="ZIP"),
        token=self.token)
    manifest = self._GetZipManifest(result)
    self.assertEqual(manifest["archived_files"], 1)
    self.assertEqual(manifest["failed_files"], 0)
    self.assertEqual(manifest["processed_files"], 1)
    self.assertEqual(manifest["ignored_files"], 0)

  def testIgnoresFileNotMatchingPathGlobsBlacklist(self):
    handler = flow_plugin.ApiGetFlowFilesArchiveHandler(
        path_globs_whitelist=[rdf_paths.GlobExpression("/**/*/test.plist")],
        path_globs_blacklist=[rdf_paths.GlobExpression("**/*.plist")])
    result = handler.Handle(
        flow_plugin.ApiGetFlowFilesArchiveArgs(
            client_id=self.client_id,
            flow_id=self.flow_urn.Basename(),
            archive_format="ZIP"),
        token=self.token)
    manifest = self._GetZipManifest(result)
    self.assertEqual(manifest["archived_files"], 0)
    self.assertEqual(manifest["failed_files"], 0)
    self.assertEqual(manifest["processed_files"], 1)
    self.assertEqual(manifest["ignored_files"], 1)
    self.assertEqual(manifest["ignored_files_list"], [
        utils.SmartUnicode(
            self.client_id.Add("fs/os").Add(self.base_path).Add("test.plist"))
    ])

  def testGeneratesTarGzArchive(self):
    result = self.handler.Handle(
        flow_plugin.ApiGetFlowFilesArchiveArgs(
            client_id=self.client_id,
            flow_id=self.flow_urn.Basename(),
            archive_format="TAR_GZ"),
        token=self.token)

    with utils.TempDirectory() as temp_dir:
      tar_path = os.path.join(temp_dir, "archive.tar.gz")
      with open(tar_path, "wb") as fd:
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
      with open(manifest_file_path, "rb") as fd:
        manifest = yaml.safe_load(fd.read())

        self.assertEqual(manifest["archived_files"], 1)
        self.assertEqual(manifest["failed_files"], 0)
        self.assertEqual(manifest["processed_files"], 1)
        self.assertEqual(manifest["ignored_files"], 0)


class ApiGetExportedFlowResultsHandlerTest(test_lib.GRRBaseTest):
  """Tests for ApiGetExportedFlowResultsHandler."""

  def setUp(self):
    super(ApiGetExportedFlowResultsHandlerTest, self).setUp()

    self.handler = flow_plugin.ApiGetExportedFlowResultsHandler()
    self.client_id = self.SetupClient(0)

  def testWorksCorrectlyWithTestOutputPluginOnFlowWithSingleResult(self):
    with test_lib.FakeTime(42):
      flow_urn = flow.GRRFlow.StartFlow(
          flow_name=flow_test_lib.DummyFlowWithSingleReply.__name__,
          client_id=self.client_id,
          token=self.token)

      flow_test_lib.TestFlowHelper(flow_urn, token=self.token)

    result = self.handler.Handle(
        flow_plugin.ApiGetExportedFlowResultsArgs(
            client_id=self.client_id,
            flow_id=flow_urn.Basename(),
            plugin_name=test_plugins.TestInstantOutputPlugin.plugin_name),
        token=self.token)

    chunks = list(result.GenerateContent())

    self.assertListEqual(
        chunks,
        ["Start: %s" % utils.SmartStr(flow_urn),
         "Values of type: RDFString",
         "First pass: oh (source=%s)" % utils.SmartStr(self.client_id),
         "Second pass: oh (source=%s)" % utils.SmartStr(self.client_id),
         "Finish: %s" % utils.SmartStr(flow_urn)])  # pyformat: disable


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
