#!/usr/bin/env python
"""Tests for file collection flows."""

import collections
import contextlib
import hashlib
import os
from typing import List
from unittest import mock

from absl import app

from grr_response_client import vfs
from grr_response_client.vfs_handlers import files as vfs_files
from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util import temp
from grr_response_server import data_store
from grr_response_server import flow_base
from grr_response_server.flows import file
from grr_response_server.flows.general import file_finder
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib

TestFile = collections.namedtuple("TestFile", ["path", "sha1"])


@contextlib.contextmanager
def SetUpTestFiles():
  with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
    file_bar_path = os.path.join(temp_dirpath, "bar")
    with open(file_bar_path, "wb") as fd:
      fd.write(b"bar")

    file_baz_path = os.path.join(temp_dirpath, "baz")
    with open(file_baz_path, "wb") as fd:
      fd.write(b"baz")

    file_foo_path = os.path.join(temp_dirpath, "foo")
    with open(file_foo_path, "wb") as fd:
      fd.write(b"foo")

    yield {
        "bar":
            TestFile(path=file_bar_path, sha1=hashlib.sha1(b"bar").hexdigest()),
        "baz":
            TestFile(path=file_baz_path, sha1=hashlib.sha1(b"baz").hexdigest()),
        "foo":
            TestFile(path=file_foo_path, sha1=hashlib.sha1(b"foo").hexdigest()),
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
        creator=self.test_username)

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
          creator=self.test_username)

  def testFetchIsRetriedWithRawOnWindows(self):
    with mock.patch.object(flow_base.FlowBase, "client_os", "Windows"):
      with _PatchVfs():
        flow_id = flow_test_lib.TestFlowHelper(
            file.CollectSingleFile.__name__,
            self.client_mock,
            client_id=self.client_id,
            path=self.files["bar"].path,
            creator=self.test_username)

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
              creator=self.test_username)
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


class TestCollectFilesByKnownPath(flow_test_lib.FlowTestsBaseclass):

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)
    self.client_mock = action_mocks.FileFinderClientMockWithTimestamps()

  def testReturnsSingleFile(self):
    temp_bar_file = self.create_tempfile()
    temp_bar_file.write_bytes(b"bar")
    file_bar_path = temp_bar_file.full_path
    file_bar_hash = hashlib.sha1(b"bar").hexdigest()

    flow_id = flow_test_lib.TestFlowHelper(
        file.CollectFilesByKnownPath.__name__,
        self.client_mock,
        client_id=self.client_id,
        paths=[file_bar_path],
        creator=self.test_username)

    progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)
    self.assertEqual(
        rdf_file_finder.CollectFilesByKnownPathProgress(
            num_in_progress=0,
            num_raw_fs_access_retries=0,
            num_collected=1,
            num_failed=0,
        ), progress)

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertLen(results, 3)

    for result in results:
      self.assertEqual(result.stat.pathspec.pathtype,
                       rdf_paths.PathSpec.PathType.OS)

    expected_paths = [file_bar_path, file_bar_path, file_bar_path]
    self.assertCountEqual(expected_paths, self._getResultsPaths(results))

    expected_hashes = ["None", file_bar_hash, file_bar_hash]
    self.assertCountEqual(expected_hashes, self._getResultsHashes(results))

    expected_statuses = [
        rdf_file_finder.CollectFilesByKnownPathResult.Status.IN_PROGRESS,
        rdf_file_finder.CollectFilesByKnownPathResult.Status.IN_PROGRESS,
        rdf_file_finder.CollectFilesByKnownPathResult.Status.COLLECTED
    ]
    self.assertCountEqual(expected_statuses, self._getResultsStatus(results))

  def testReturnsMultipleFiles(self):
    temp_bar_file = self.create_tempfile()
    temp_bar_file.write_bytes(b"bar")
    file_bar_path = temp_bar_file.full_path
    file_bar_hash = hashlib.sha1(b"bar").hexdigest()

    temp_foo_file = self.create_tempfile()
    temp_foo_file.write_bytes(b"foo")
    file_foo_path = temp_foo_file.full_path
    file_foo_hash = hashlib.sha1(b"foo").hexdigest()

    flow_id = flow_test_lib.TestFlowHelper(
        file.CollectFilesByKnownPath.__name__,
        self.client_mock,
        client_id=self.client_id,
        paths=[file_bar_path, file_foo_path],
        creator=self.test_username)

    progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)
    self.assertEqual(
        rdf_file_finder.CollectFilesByKnownPathProgress(
            num_in_progress=0,
            num_raw_fs_access_retries=0,
            num_collected=2,
            num_failed=0,
        ), progress)

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertLen(results, 6)

    for result in results:
      self.assertEqual(result.stat.pathspec.pathtype,
                       rdf_paths.PathSpec.PathType.OS)

    expected_paths = [
        file_bar_path,
        file_bar_path,
        file_bar_path,  # Bar
        file_foo_path,
        file_foo_path,
        file_foo_path  # Foo
    ]
    self.assertCountEqual(expected_paths, self._getResultsPaths(results))

    expected_hashes = [
        "None",
        file_bar_hash,
        file_bar_hash,  # Bar
        "None",
        file_foo_hash,
        file_foo_hash  # Foo
    ]
    self.assertCountEqual(expected_hashes, self._getResultsHashes(results))

    expected_statuses = [
        # Bar
        rdf_file_finder.CollectFilesByKnownPathResult.Status.IN_PROGRESS,
        rdf_file_finder.CollectFilesByKnownPathResult.Status.IN_PROGRESS,
        rdf_file_finder.CollectFilesByKnownPathResult.Status.COLLECTED,
        # Foo
        rdf_file_finder.CollectFilesByKnownPathResult.Status.IN_PROGRESS,
        rdf_file_finder.CollectFilesByKnownPathResult.Status.IN_PROGRESS,
        rdf_file_finder.CollectFilesByKnownPathResult.Status.COLLECTED
    ]
    self.assertCountEqual(expected_statuses, self._getResultsStatus(results))

  def testReturnsMultipleFilesStat(self):
    temp_bar_file = self.create_tempfile()
    temp_bar_file.write_bytes(b"bar")
    file_bar_path = temp_bar_file.full_path

    temp_foo_file = self.create_tempfile()
    temp_foo_file.write_bytes(b"foo")
    file_foo_path = temp_foo_file.full_path

    flow_id = flow_test_lib.TestFlowHelper(
        file.CollectFilesByKnownPath.__name__,
        self.client_mock,
        client_id=self.client_id,
        paths=[file_bar_path, file_foo_path],
        collection_level=rdf_file_finder.CollectFilesByKnownPathArgs
        .CollectionLevel.STAT,
        creator=self.test_username)

    progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)
    self.assertEqual(
        rdf_file_finder.CollectFilesByKnownPathProgress(
            num_in_progress=0,
            num_raw_fs_access_retries=0,
            num_collected=2,
            num_failed=0,
        ), progress)

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertLen(results, 2)
    self.assertEqual(results[0].stat.pathspec.path, file_bar_path)
    self.assertEqual(results[0].stat.pathspec.pathtype,
                     rdf_paths.PathSpec.PathType.OS)
    self.assertFalse(results[0].hash)
    self.assertEqual(
        results[0].status,
        rdf_file_finder.CollectFilesByKnownPathResult.Status.COLLECTED)
    self.assertEqual(results[1].stat.pathspec.path, file_foo_path)
    self.assertEqual(results[1].stat.pathspec.pathtype,
                     rdf_paths.PathSpec.PathType.OS)
    self.assertFalse(results[1].hash)
    self.assertEqual(
        results[1].status,
        rdf_file_finder.CollectFilesByKnownPathResult.Status.COLLECTED)

  def testReturnsMultipleFilesHash(self):
    temp_bar_file = self.create_tempfile()
    temp_bar_file.write_bytes(b"bar")
    file_bar_path = temp_bar_file.full_path
    file_bar_hash = hashlib.sha1(b"bar").hexdigest()

    temp_foo_file = self.create_tempfile()
    temp_foo_file.write_bytes(b"foo")
    file_foo_path = temp_foo_file.full_path
    file_foo_hash = hashlib.sha1(b"foo").hexdigest()

    flow_id = flow_test_lib.TestFlowHelper(
        file.CollectFilesByKnownPath.__name__,
        self.client_mock,
        client_id=self.client_id,
        paths=[file_bar_path, file_foo_path],
        collection_level=rdf_file_finder.CollectFilesByKnownPathArgs
        .CollectionLevel.HASH,
        creator=self.test_username)

    progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)
    self.assertEqual(
        rdf_file_finder.CollectFilesByKnownPathProgress(
            num_in_progress=0,
            num_raw_fs_access_retries=0,
            num_collected=2,
            num_failed=0,
        ), progress)

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertLen(results, 4)

    for result in results:
      self.assertEqual(result.stat.pathspec.pathtype,
                       rdf_paths.PathSpec.PathType.OS)

    expected_paths = [
        file_bar_path,
        file_bar_path,  # Bar
        file_foo_path,
        file_foo_path  # Foo
    ]
    self.assertCountEqual(expected_paths, self._getResultsPaths(results))

    expected_hashes = [
        "None",
        file_bar_hash,  # Bar
        "None",
        file_foo_hash  # Foo
    ]
    self.assertCountEqual(expected_hashes, self._getResultsHashes(results))

    expected_statuses = [
        # Bar
        rdf_file_finder.CollectFilesByKnownPathResult.Status.IN_PROGRESS,
        rdf_file_finder.CollectFilesByKnownPathResult.Status.COLLECTED,
        # Foo
        rdf_file_finder.CollectFilesByKnownPathResult.Status.IN_PROGRESS,
        rdf_file_finder.CollectFilesByKnownPathResult.Status.COLLECTED
    ]
    self.assertCountEqual(expected_statuses, self._getResultsStatus(results))

  def testFileNotFound(self):
    temp_dir = self.create_tempdir()
    non_existent_file_path = os.path.join(temp_dir.full_path, "/non_existent")

    flow_id = flow_test_lib.TestFlowHelper(
        file.CollectFilesByKnownPath.__name__,
        self.client_mock,
        client_id=self.client_id,
        paths=[non_existent_file_path],
        creator=self.test_username)

    progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)
    self.assertEqual(
        rdf_file_finder.CollectFilesByKnownPathProgress(
            num_in_progress=0,
            num_raw_fs_access_retries=0,
            num_collected=0,
            num_failed=1,
        ), progress)

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertLen(results, 1)
    self.assertEqual(results[0].stat.pathspec.path, non_existent_file_path)
    self.assertEqual(results[0].stat.pathspec.pathtype,
                     rdf_paths.PathSpec.PathType.OS)
    self.assertEqual(
        results[0].status,
        rdf_file_finder.CollectFilesByKnownPathResult.Status.NOT_FOUND)

  def testFetchIsRetriedWithRawOnWindows(self):
    temp_bar_file = self.create_tempfile()
    temp_bar_file.write_bytes(b"bar")
    file_bar_path = temp_bar_file.full_path
    file_bar_hash = hashlib.sha1(b"bar").hexdigest()

    with mock.patch.object(flow_base.FlowBase, "client_os", "Windows"):
      with _PatchVfs():
        flow_id = flow_test_lib.TestFlowHelper(
            file.CollectFilesByKnownPath.__name__,
            self.client_mock,
            client_id=self.client_id,
            paths=[file_bar_path],
            creator=self.test_username)

    progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)
    self.assertEqual(
        rdf_file_finder.CollectFilesByKnownPathProgress(
            num_in_progress=0,
            num_raw_fs_access_retries=1,
            num_collected=1,
            num_failed=0,
        ), progress)

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertLen(results, 4)

    for result in results:
      self.assertEqual(result.stat.pathspec.path, file_bar_path)

    expected_pathtypes = [
        # First attempt (failure)
        rdf_paths.PathSpec.PathType.OS,
        # Second attempt (success)
        config.CONFIG["Server.raw_filesystem_access_pathtype"],
        config.CONFIG["Server.raw_filesystem_access_pathtype"],
        config.CONFIG["Server.raw_filesystem_access_pathtype"]
    ]
    self.assertCountEqual(expected_pathtypes, self._getResultsPathType(results))

    expected_statuses = [
        # First attempt  (failure)
        rdf_file_finder.CollectFilesByKnownPathResult.Status.IN_PROGRESS,
        # Second attempt (success)
        rdf_file_finder.CollectFilesByKnownPathResult.Status.IN_PROGRESS,
        rdf_file_finder.CollectFilesByKnownPathResult.Status.IN_PROGRESS,
        rdf_file_finder.CollectFilesByKnownPathResult.Status.COLLECTED
    ]
    self.assertCountEqual(expected_statuses, self._getResultsStatus(results))

    expected_hashes = ["None", "None", file_bar_hash, file_bar_hash]
    self.assertCountEqual(expected_hashes, self._getResultsHashes(results))

  def testFailsAfterRetryOnFailedFetchOnWindows(self):
    temp_bar_file = self.create_tempfile()
    temp_bar_file.write_bytes(b"bar")
    file_bar_path = temp_bar_file.full_path

    with mock.patch.object(flow_base.FlowBase, "client_os", "Windows"):
      with mock.patch.object(vfs, "VFSOpen", side_effect=IOError("mock err")):
        flow_id = flow_test_lib.TestFlowHelper(
            file.CollectFilesByKnownPath.__name__,
            self.client_mock,
            client_id=self.client_id,
            paths=[file_bar_path],
            creator=self.test_username)

    progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)
    self.assertEqual(
        rdf_file_finder.CollectFilesByKnownPathProgress(
            num_in_progress=0,
            num_raw_fs_access_retries=1,
            num_collected=0,
            num_failed=1,
        ), progress)

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertLen(results, 1)
    self.assertEqual(results[0].stat.pathspec.path, file_bar_path)
    self.assertEqual(results[0].stat.pathspec.pathtype,
                     config.CONFIG["Server.raw_filesystem_access_pathtype"])
    self.assertIsNone(results[0].hash.sha1)
    self.assertEqual(
        results[0].status,
        rdf_file_finder.CollectFilesByKnownPathResult.Status.FAILED)

  def _getResultsPaths(
      self,
      results: rdf_file_finder.CollectFilesByKnownPathResult) -> List[str]:
    paths: str = []
    for result in results:
      paths.append(result.stat.pathspec.path)
    return paths

  def _getResultsPathType(
      self, results: rdf_file_finder.CollectFilesByKnownPathResult
  ) -> List["rdf_paths.PathSpec.PathType"]:
    pathtypes: rdf_paths.PathSpec.PathType = []
    for result in results:
      pathtypes.append(result.stat.pathspec.pathtype)
    return pathtypes

  def _getResultsStatus(
      self, results: rdf_file_finder.CollectFilesByKnownPathResult
  ) -> List["rdf_file_finder.CollectFilesByKnownPathResult.Status"]:
    statuses: rdf_file_finder.CollectFilesByKnownPathResult.Status = []
    for result in results:
      statuses.append(result.status)
    return statuses

  def _getResultsHashes(
      self,
      results: rdf_file_finder.CollectFilesByKnownPathResult) -> List[str]:
    hashes: str = []
    for result in results:
      hashes.append(str(result.hash.sha1))
    return hashes


class TestCollectMultipleFiles(flow_test_lib.FlowTestsBaseclass):

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)
    self.client_mock = action_mocks.CollectMultipleFilesClientMock()

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
        creator=self.test_username)

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertLen(results, 2)

    # Check that both returned results are success.
    collected_status = (
        rdf_file_finder.CollectMultipleFilesResult.Status.COLLECTED)

    for f in results:
      self.assertEqual(f.status, collected_status)
      self.assertEqual(f.stat.pathspec.pathtype, rdf_paths.PathSpec.PathType.OS)

      if f.stat.pathspec.path == os.path.join(self.files["bar"].path):
        self.assertEqual(str(f.hash.sha1), self.files["bar"].sha1)
      else:
        self.assertEqual(f.stat.pathspec.path, self.files["baz"].path)
        self.assertEqual(str(f.hash.sha1), self.files["baz"].sha1)

  def testCorrectlyReportProgressForSuccessfullyCollectedFiles(self):
    path = os.path.join(self.fixture_path, "b*")

    flow_id = flow_test_lib.TestFlowHelper(
        file.CollectMultipleFiles.__name__,
        self.client_mock,
        client_id=self.client_id,
        path_expressions=[path],
        creator=self.test_username)

    progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)
    self.assertEqual(
        rdf_file_finder.CollectMultipleFilesProgress(
            num_collected=2,
            num_failed=0,
            num_found=2,
            num_in_progress=0,
            num_raw_fs_access_retries=0,
        ), progress)

  def testPassesNoConditionsToClientFileFinderWhenNoConditionsSpecified(self):
    flow_id = flow_test_lib.StartFlow(
        file.CollectMultipleFiles,
        client_id=self.client_id,
        path_expressions=["/some/path"])

    children = data_store.REL_DB.ReadChildFlowObjects(self.client_id, flow_id)
    self.assertLen(children, 1)

    child = children[0]
    self.assertEqual(child.flow_class_name,
                     file_finder.ClientFileFinder.__name__)
    self.assertEmpty(child.args.conditions)

  def testPassesAllConditionsToClientFileFinderWhenAllConditionsSpecified(self):
    modification_time = rdf_file_finder.FileFinderModificationTimeCondition(
        min_last_modified_time=rdfvalue.RDFDatetime.Now(),)

    access_time = rdf_file_finder.FileFinderAccessTimeCondition(
        min_last_access_time=rdfvalue.RDFDatetime.Now(),)

    inode_change_time = rdf_file_finder.FileFinderInodeChangeTimeCondition(
        min_last_inode_change_time=rdfvalue.RDFDatetime.Now(),)

    size = rdf_file_finder.FileFinderSizeCondition(min_file_size=42,)

    ext_flags = rdf_file_finder.FileFinderExtFlagsCondition(linux_bits_set=42,)

    contents_regex_match = (
        rdf_file_finder.FileFinderContentsRegexMatchCondition(regex=b"foo",))

    contents_literal_match = (
        rdf_file_finder.FileFinderContentsLiteralMatchCondition(
            literal=b"bar",))

    flow_id = flow_test_lib.StartFlow(
        file.CollectMultipleFiles,
        client_id=self.client_id,
        path_expressions=["/some/path"],
        modification_time=modification_time,
        access_time=access_time,
        inode_change_time=inode_change_time,
        size=size,
        ext_flags=ext_flags,
        contents_regex_match=contents_regex_match,
        contents_literal_match=contents_literal_match,
    )

    children = data_store.REL_DB.ReadChildFlowObjects(self.client_id, flow_id)
    self.assertLen(children, 1)

    child = children[0]
    self.assertEqual(child.flow_class_name,
                     file_finder.ClientFileFinder.__name__)
    # We expect 7 condition-attributes to be converted
    # to 7 FileFinderConditions.
    self.assertLen(child.args.conditions, 7)

    def _GetCondition(condition_type):
      for c in child.args.conditions:
        if c.condition_type == condition_type:
          return c.UnionCast()

      raise RuntimeError(f"Condition of type {condition_type} not found.")

    self.assertEqual(
        _GetCondition(
            rdf_file_finder.FileFinderCondition.Type.MODIFICATION_TIME),
        modification_time)

    self.assertEqual(
        _GetCondition(rdf_file_finder.FileFinderCondition.Type.ACCESS_TIME),
        access_time)

    self.assertEqual(
        _GetCondition(
            rdf_file_finder.FileFinderCondition.Type.INODE_CHANGE_TIME),
        inode_change_time)

    self.assertEqual(
        _GetCondition(rdf_file_finder.FileFinderCondition.Type.SIZE), size)

    self.assertEqual(
        _GetCondition(rdf_file_finder.FileFinderCondition.Type.EXT_FLAGS),
        ext_flags)

    self.assertEqual(
        _GetCondition(
            rdf_file_finder.FileFinderCondition.Type.CONTENTS_REGEX_MATCH),
        contents_regex_match)

    self.assertEqual(
        _GetCondition(
            rdf_file_finder.FileFinderCondition.Type.CONTENTS_LITERAL_MATCH),
        contents_literal_match)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
