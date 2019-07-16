#!/usr/bin/env python
"""This module contains tests for flows-related API handlers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io
import os
import tarfile
import zipfile

from absl import app
from future.builtins import str
import yaml

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import test_base as rdf_test_base
from grr_response_core.lib.util import compatibility
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server.flows.general import file_finder
from grr_response_server.flows.general import processes
from grr_response_server.gui import api_test_lib
from grr_response_server.gui.api_plugins import client as client_plugin
from grr_response_server.gui.api_plugins import flow as flow_plugin
from grr_response_server.output_plugins import test_plugins
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import test_lib


class ApiFlowIdTest(rdf_test_base.RDFValueTestMixin,
                    hunt_test_lib.StandardHuntTestMixin, test_lib.GRRBaseTest):
  """Test for ApiFlowId."""

  rdfvalue_class = flow_plugin.ApiFlowId

  def GenerateSample(self, number=0):
    return flow_plugin.ApiFlowId("F:" + "123" * (number + 1))

  def testRaisesWhenInitializedFromInvalidValues(self):
    with self.assertRaises(ValueError):
      flow_plugin.ApiFlowId("bla%h")


class ApiFlowTest(test_lib.GRRBaseTest):
  """Test for ApiFlow."""

  def testInitializesClientIdForClientBasedFlows(self):
    client_id = self.SetupClient(0)
    flow_id = flow.StartFlow(
        client_id=client_id, flow_cls=processes.ListProcesses)
    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    flow_api_obj = flow_plugin.ApiFlow().InitFromFlowObject(flow_obj)

    self.assertEqual(flow_api_obj.client_id,
                     client_plugin.ApiClientId(client_id))


class ApiCreateFlowHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Test for ApiCreateFlowHandler."""

  def setUp(self):
    super(ApiCreateFlowHandlerTest, self).setUp()
    self.client_id = self.SetupClient(0)
    self.handler = flow_plugin.ApiCreateFlowHandler()

  def testRunnerArgsBaseSessionIdDoesNotAffectCreatedFlow(self):
    """When multiple clients match, check we run on the latest one."""
    flow_runner_args = rdf_flow_runner.FlowRunnerArgs(
        base_session_id="aff4:/foo")
    args = flow_plugin.ApiCreateFlowArgs(
        client_id=self.client_id,
        flow=flow_plugin.ApiFlow(
            name=processes.ListProcesses.__name__,
            runner_args=flow_runner_args))

    result = self.handler.Handle(args, token=self.token)
    self.assertNotStartsWith(str(result.urn), "aff4:/foo")


class ApiGetFlowFilesArchiveHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Tests for ApiGetFlowFilesArchiveHandler."""

  def setUp(self):
    super(ApiGetFlowFilesArchiveHandlerTest, self).setUp()

    self.handler = flow_plugin.ApiGetFlowFilesArchiveHandler()

    self.client_id = self.SetupClient(0)

    action_mock = action_mocks.FileFinderClientMock()
    self.flow_id = flow_test_lib.TestFlowHelper(
        file_finder.FileFinder.__name__,
        action_mock,
        client_id=self.client_id,
        token=self.token,
        paths=[os.path.join(self.base_path, "test.plist")],
        action=rdf_file_finder.FileFinderAction(action_type="DOWNLOAD"))

    if isinstance(self.flow_id, rdfvalue.SessionID):
      self.flow_id = self.flow_id.Basename()

  def _GetZipManifest(self, result):
    out_fd = io.BytesIO()

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
            flow_id=self.flow_id,
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
            flow_id=self.flow_id,
            archive_format="ZIP"),
        token=self.token)
    manifest = self._GetZipManifest(result)
    self.assertEqual(manifest["archived_files"], 0)
    self.assertEqual(manifest["failed_files"], 0)
    self.assertEqual(manifest["processed_files"], 1)
    self.assertEqual(manifest["ignored_files"], 1)
    self.assertEqual(
        manifest["ignored_files_list"],
        ["aff4:/%s/fs/os%s/test.plist" % (self.client_id, self.base_path)])

  def testArchivesFileMatchingPathGlobsWhitelist(self):
    handler = flow_plugin.ApiGetFlowFilesArchiveHandler(
        path_globs_blacklist=[],
        path_globs_whitelist=[rdf_paths.GlobExpression("/**/*/test.plist")])
    result = handler.Handle(
        flow_plugin.ApiGetFlowFilesArchiveArgs(
            client_id=self.client_id,
            flow_id=self.flow_id,
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
            flow_id=self.flow_id,
            archive_format="ZIP"),
        token=self.token)
    manifest = self._GetZipManifest(result)
    self.assertEqual(manifest["archived_files"], 0)
    self.assertEqual(manifest["failed_files"], 0)
    self.assertEqual(manifest["processed_files"], 1)
    self.assertEqual(manifest["ignored_files"], 1)
    self.assertEqual(
        manifest["ignored_files_list"],
        ["aff4:/%s/fs/os%s/test.plist" % (self.client_id, self.base_path)])

  def testGeneratesTarGzArchive(self):
    result = self.handler.Handle(
        flow_plugin.ApiGetFlowFilesArchiveArgs(
            client_id=self.client_id,
            flow_id=self.flow_id,
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
      sid = flow_test_lib.TestFlowHelper(
          compatibility.GetName(flow_test_lib.DummyFlowWithSingleReply),
          client_id=self.client_id,
          token=self.token)

    result = self.handler.Handle(
        flow_plugin.ApiGetExportedFlowResultsArgs(
            client_id=self.client_id,
            flow_id=sid,
            plugin_name=test_plugins.TestInstantOutputPlugin.plugin_name),
        token=self.token)

    chunks = list(result.GenerateContent())

    self.assertListEqual(chunks, [
        "Start: aff4:/%s/flows/%s" %
        (self.client_id, sid), "Values of type: RDFString",
        "First pass: oh (source=aff4:/%s)" % self.client_id,
        "Second pass: oh (source=aff4:/%s)" % self.client_id,
        "Finish: aff4:/%s/flows/%s" % (self.client_id, sid)
    ])


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
