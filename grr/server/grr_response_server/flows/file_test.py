#!/usr/bin/env python
# Lint as: python3
"""Tests for file collection flows."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import contextlib
import os

from absl import app
import mock

from grr_response_client import vfs
from grr_response_client.vfs_handlers import files as vfs_files
from grr_response_core import config
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util import temp
from grr_response_server import flow_base
from grr_response_server.flows import file
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


TestFile = collections.namedtuple("TestFile", ["path", "sha1"])


@contextlib.contextmanager
def SetUpTestFiles():
  with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
    file_bar_path = os.path.join(temp_dirpath, "bar")
    with open(file_bar_path, "w") as fd:
      fd.write("bar")

    file_baz_path = os.path.join(temp_dirpath, "baz")
    with open(file_baz_path, "w") as fd:
      fd.write("baz")

    file_foo_path = os.path.join(temp_dirpath, "foo")
    with open(file_foo_path, "w") as fd:
      fd.write("foo")

    yield {
        "bar":
            TestFile(
                path=file_bar_path,
                sha1="62cdb7020ff920e5aa642c3d4066950dd1f01f4d"),
        "baz":
            TestFile(
                path=file_baz_path,
                sha1="bbe960a25ea311d21d40669e93df2003ba9b90a2"),
        "foo":
            TestFile(
                path=file_foo_path,
                sha1="0beec7b5ea3f0fdbc95d0dd47f3c5bc275da8a33")
    }


def _PatchVfs():

  class _UseOSForRawFile(vfs_files.File):
    supported_pathtype = config.CONFIG["Server.raw_filesystem_access_pathtype"]

  class _FailingOSFile(vfs_files.File):
    supported_pathtype = rdf_paths.PathSpec.PathType.OS

    def Read(self, length=None):
      raise IOError("mock error")

  return mock.patch.dict(
      vfs.VFS_HANDLERS, {
          _UseOSForRawFile.supported_pathtype: _UseOSForRawFile,
          _FailingOSFile.supported_pathtype: _FailingOSFile,
      })


class TestCollectSingleFile(flow_test_lib.FlowTestsBaseclass):

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)
    self.client_mock = action_mocks.FileFinderClientMockWithTimestamps()

    stack = contextlib.ExitStack()
    self.files = stack.enter_context(SetUpTestFiles())
    self.addCleanup(stack.close)

  def testCollectSingleFileReturnsFile(self):
    flow_id = flow_test_lib.TestFlowHelper(
        file.CollectSingleFile.__name__,
        self.client_mock,
        client_id=self.client_id,
        path=self.files["bar"].path,
        token=self.token)

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertLen(results, 1)
    self.assertEqual(results[0].stat.pathspec.path, self.files["bar"].path)
    self.assertEqual(results[0].stat.pathspec.pathtype,
                     rdf_paths.PathSpec.PathType.OS)
    self.assertEqual(str(results[0].hash.sha1), self.files["bar"].sha1)

  def testFileNotFoundRaisesError(self):
    with self.assertRaisesRegex(RuntimeError, "File not found"):
      flow_test_lib.TestFlowHelper(
          file.CollectSingleFile.__name__,
          self.client_mock,
          client_id=self.client_id,
          path="/nonexistent",
          token=self.token)

  def testFetchIsRetriedWithRawOnWindows(self):
    with mock.patch.object(flow_base.FlowBase, "client_os", "Windows"):
      with _PatchVfs():
        flow_id = flow_test_lib.TestFlowHelper(
            file.CollectSingleFile.__name__,
            self.client_mock,
            client_id=self.client_id,
            path=self.files["bar"].path,
            token=self.token)

        results = flow_test_lib.GetFlowResults(self.client_id, flow_id)

    self.assertLen(results, 1)
    self.assertEqual(results[0].stat.pathspec.path, self.files["bar"].path)
    self.assertEqual(results[0].stat.pathspec.pathtype,
                     config.CONFIG["Server.raw_filesystem_access_pathtype"])
    self.assertEqual(str(results[0].hash.sha1), self.files["bar"].sha1)

  def testRaisesAfterRetryOnFailedFetchOnWindows(self):
    with mock.patch.object(flow_base.FlowBase, "client_os", "Windows"):
      with mock.patch.object(vfs, "VFSOpen", side_effect=IOError("mock err")):
        with self.assertRaisesRegex(RuntimeError, r"mock err.*bar.*") as e:
          flow_test_lib.TestFlowHelper(
              file.CollectSingleFile.__name__,
              self.client_mock,
              client_id=self.client_id,
              path=self.files["bar"].path,
              token=self.token)
        self.assertIn(
            str(config.CONFIG["Server.raw_filesystem_access_pathtype"]),
            str(e.exception))

  def testCorrectlyReportsProgressInFlight(self):
    flow_id = flow_test_lib.StartFlow(
        file.CollectSingleFile, client_id=self.client_id, path="/some/path")
    progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)
    self.assertEqual(
        progress.status,
        rdf_file_finder.CollectSingleFileProgress.Status.IN_PROGRESS)

  def testProgressContainsResultOnSuccess(self):
    flow_id = flow_test_lib.StartAndRunFlow(
        file.CollectSingleFile,
        self.client_mock,
        client_id=self.client_id,
        path=self.files["bar"].path)

    progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)

    self.assertEqual(progress.status,
                     rdf_file_finder.CollectSingleFileProgress.Status.COLLECTED)
    self.assertEqual(progress.result.stat.pathspec.path, self.files["bar"].path)
    self.assertEqual(progress.result.stat.pathspec.pathtype,
                     rdf_paths.PathSpec.PathType.OS)
    self.assertEqual(str(progress.result.hash.sha1), self.files["bar"].sha1)

  def testProgressCorrectlyIndicatesNotFoundStatus(self):
    flow_id = flow_test_lib.StartAndRunFlow(
        file.CollectSingleFile,
        self.client_mock,
        client_id=self.client_id,
        check_flow_errors=False,
        path="/nonexistent")

    progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)
    self.assertEqual(progress.status,
                     rdf_file_finder.CollectSingleFileProgress.Status.NOT_FOUND)

  def testProgressCorrectlyIndicatesErrorStatus(self):
    with mock.patch.object(flow_base.FlowBase, "client_os", "Windows"):
      with mock.patch.object(vfs, "VFSOpen", side_effect=IOError("mock err")):
        flow_id = flow_test_lib.StartAndRunFlow(
            file.CollectSingleFile,
            self.client_mock,
            client_id=self.client_id,
            check_flow_errors=False,
            path="/nonexistent")

    progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)
    self.assertEqual(progress.status,
                     rdf_file_finder.CollectSingleFileProgress.Status.FAILED)
    self.assertEqual(
        progress.error_description,
        f"mock err when fetching /nonexistent with {config.CONFIG['Server.raw_filesystem_access_pathtype']}"
    )


class TestCollectMultipleFiles(flow_test_lib.FlowTestsBaseclass):

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)
    self.client_mock = action_mocks.FileFinderClientMockWithTimestamps()

    stack = contextlib.ExitStack()
    self.files = stack.enter_context(SetUpTestFiles())
    self.addCleanup(stack.close)
    self.fixture_path = os.path.dirname(self.files["bar"].path)

  def testCollectMultipleFilesReturnsFiles(self):
    path = os.path.join(self.fixture_path, "b*")

    flow_id = flow_test_lib.TestFlowHelper(
        file.CollectMultipleFiles.__name__,
        self.client_mock,
        client_id=self.client_id,
        path_expressions=[path],
        token=self.token)

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertLen(results, 1)
    self.assertLen(results[0].files, 2)

    for f in results[0].files:
      self.assertEqual(f.stat.pathspec.pathtype, rdf_paths.PathSpec.PathType.OS)
      if f.stat.pathspec.path == os.path.join(self.files["bar"].path):
        self.assertEqual(str(f.hash.sha1), self.files["bar"].sha1)
      else:
        self.assertEqual(f.stat.pathspec.path, self.files["baz"].path)
        self.assertEqual(str(f.hash.sha1), self.files["baz"].sha1)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
