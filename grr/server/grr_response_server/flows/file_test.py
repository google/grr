#!/usr/bin/env python
"""Tests for file collection flows."""

import collections
import contextlib
import hashlib
import os
from unittest import mock

from absl import app

from grr_response_client import vfs
from grr_response_client.vfs_handlers import files as vfs_files
from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util import temp
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_server import data_store
from grr_response_server import flow_base
from grr_response_server.flows import file
from grr_response_server.flows.general import file_finder
from grr_response_server.rdfvalues import mig_flow_objects
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib

TestFile = collections.namedtuple("TestFile", ["path", "sha1", "sha256"])


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
        "bar": TestFile(
            path=file_bar_path,
            sha1=hashlib.sha1(b"bar").hexdigest(),
            sha256=hashlib.sha256(b"bar").hexdigest(),
        ),
        "baz": TestFile(
            path=file_baz_path,
            sha1=hashlib.sha1(b"baz").hexdigest(),
            sha256=hashlib.sha256(b"baz").hexdigest(),
        ),
        "foo": TestFile(
            path=file_foo_path,
            sha1=hashlib.sha1(b"foo").hexdigest(),
            sha256=hashlib.sha256(b"foo").hexdigest(),
        ),
    }


def _PatchVfs():
  class _UseOSForRawFile(vfs_files.File):
    supported_pathtype = config.CONFIG["Server.raw_filesystem_access_pathtype"]

  class _FailingOSFile(vfs_files.File):
    supported_pathtype = rdf_paths.PathSpec.PathType.OS

    def Read(self, length=None):
      raise IOError("mock error")

  return mock.patch.dict(
      vfs.VFS_HANDLERS,
      {
          _UseOSForRawFile.supported_pathtype: _UseOSForRawFile,
          _FailingOSFile.supported_pathtype: _FailingOSFile,
      },
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

    flow_id = flow_test_lib.StartAndRunFlow(
        file.CollectFilesByKnownPath,
        self.client_mock,
        client_id=self.client_id,
        flow_args=rdf_file_finder.CollectFilesByKnownPathArgs(
            paths=[file_bar_path],
        ),
        creator=self.test_username,
    )

    progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)
    self.assertEqual(
        rdf_file_finder.CollectFilesByKnownPathProgress(
            num_in_progress=0,
            num_raw_fs_access_retries=0,
            num_collected=1,
            num_failed=0,
        ),
        progress,
    )

    child_flows = data_store.REL_DB.ReadChildFlowObjects(
        self.client_id, flow_id
    )
    self.assertLen(child_flows, 1)

    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    # One "IN_PROGRESS" and one "COLLECTED" result.
    self.assertLen(results, 2)

    for result in results:
      self.assertEqual(
          result.stat.pathspec.pathtype, rdf_paths.PathSpec.PathType.OS
      )

    expected_paths = [file_bar_path, file_bar_path]
    self.assertCountEqual(expected_paths, self._getResultsPaths(results))

    expected_hashes = ["None", file_bar_hash]
    self.assertCountEqual(expected_hashes, self._getResultsHashes(results))

    expected_statuses = [
        rdf_file_finder.CollectFilesByKnownPathResult.Status.IN_PROGRESS,
        rdf_file_finder.CollectFilesByKnownPathResult.Status.COLLECTED,
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

    flow_id = flow_test_lib.StartAndRunFlow(
        file.CollectFilesByKnownPath,
        self.client_mock,
        client_id=self.client_id,
        flow_args=rdf_file_finder.CollectFilesByKnownPathArgs(
            paths=[file_bar_path, file_foo_path],
        ),
        creator=self.test_username,
    )

    progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)
    self.assertEqual(
        rdf_file_finder.CollectFilesByKnownPathProgress(
            num_in_progress=0,
            num_raw_fs_access_retries=0,
            num_collected=2,
            num_failed=0,
        ),
        progress,
    )

    child_flows = data_store.REL_DB.ReadChildFlowObjects(
        self.client_id, flow_id
    )
    self.assertLen(child_flows, 1)

    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    # One "IN_PROGRESS" and one "COLLECTED" result for each file.
    self.assertLen(results, 4)

    for result in results:
      self.assertEqual(
          result.stat.pathspec.pathtype, rdf_paths.PathSpec.PathType.OS
      )

    expected_paths = [
        file_bar_path,
        file_bar_path,  # Bar
        file_foo_path,
        file_foo_path,  # Foo
    ]
    self.assertCountEqual(expected_paths, self._getResultsPaths(results))

    expected_hashes = [
        "None",
        file_bar_hash,  # Bar
        "None",
        file_foo_hash,  # Foo
    ]
    self.assertCountEqual(expected_hashes, self._getResultsHashes(results))

    expected_statuses = [
        # Bar
        rdf_file_finder.CollectFilesByKnownPathResult.Status.IN_PROGRESS,
        rdf_file_finder.CollectFilesByKnownPathResult.Status.COLLECTED,
        # Foo
        rdf_file_finder.CollectFilesByKnownPathResult.Status.IN_PROGRESS,
        rdf_file_finder.CollectFilesByKnownPathResult.Status.COLLECTED,
    ]
    self.assertCountEqual(expected_statuses, self._getResultsStatus(results))

  def testReturnsMultipleFilesStat(self):
    temp_bar_file = self.create_tempfile()
    temp_bar_file.write_bytes(b"bar")
    file_bar_path = temp_bar_file.full_path

    temp_foo_file = self.create_tempfile()
    temp_foo_file.write_bytes(b"foo")
    file_foo_path = temp_foo_file.full_path

    flow_id = flow_test_lib.StartAndRunFlow(
        file.CollectFilesByKnownPath,
        self.client_mock,
        client_id=self.client_id,
        flow_args=rdf_file_finder.CollectFilesByKnownPathArgs(
            paths=[file_bar_path, file_foo_path],
            collection_level=rdf_file_finder.CollectFilesByKnownPathArgs.CollectionLevel.STAT,
        ),
        creator=self.test_username,
    )

    progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)
    self.assertEqual(
        rdf_file_finder.CollectFilesByKnownPathProgress(
            num_in_progress=0,
            num_raw_fs_access_retries=0,
            num_collected=2,
            num_failed=0,
        ),
        progress,
    )

    child_flows = data_store.REL_DB.ReadChildFlowObjects(
        self.client_id, flow_id
    )
    self.assertLen(child_flows, 1)

    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    # One "IN_PROGRESS" and one "COLLECTED" result for each file.
    self.assertLen(results, 4)

    for result in results:
      self.assertEqual(
          result.stat.pathspec.pathtype, rdf_paths.PathSpec.PathType.OS
      )

    expected_paths = [
        file_bar_path,
        file_bar_path,  # Bar
        file_foo_path,
        file_foo_path,  # Foo
    ]
    self.assertCountEqual(expected_paths, self._getResultsPaths(results))

    expected_hashes = [
        "None",
        "None",  # Bar
        "None",
        "None",  # Foo
    ]
    self.assertCountEqual(expected_hashes, self._getResultsHashes(results))

    expected_statuses = [
        # Bar
        rdf_file_finder.CollectFilesByKnownPathResult.Status.IN_PROGRESS,
        rdf_file_finder.CollectFilesByKnownPathResult.Status.COLLECTED,
        # Foo
        rdf_file_finder.CollectFilesByKnownPathResult.Status.IN_PROGRESS,
        rdf_file_finder.CollectFilesByKnownPathResult.Status.COLLECTED,
    ]
    self.assertCountEqual(expected_statuses, self._getResultsStatus(results))

  def testReturnsMultipleFilesHash(self):
    temp_bar_file = self.create_tempfile()
    temp_bar_file.write_bytes(b"bar")
    file_bar_path = temp_bar_file.full_path
    file_bar_hash = hashlib.sha1(b"bar").hexdigest()

    temp_foo_file = self.create_tempfile()
    temp_foo_file.write_bytes(b"foo")
    file_foo_path = temp_foo_file.full_path
    file_foo_hash = hashlib.sha1(b"foo").hexdigest()

    flow_id = flow_test_lib.StartAndRunFlow(
        file.CollectFilesByKnownPath,
        self.client_mock,
        client_id=self.client_id,
        flow_args=rdf_file_finder.CollectFilesByKnownPathArgs(
            paths=[file_bar_path, file_foo_path],
            collection_level=rdf_file_finder.CollectFilesByKnownPathArgs.CollectionLevel.HASH,
        ),
        creator=self.test_username,
    )

    progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)
    self.assertEqual(
        rdf_file_finder.CollectFilesByKnownPathProgress(
            num_in_progress=0,
            num_raw_fs_access_retries=0,
            num_collected=2,
            num_failed=0,
        ),
        progress,
    )

    child_flows = data_store.REL_DB.ReadChildFlowObjects(
        self.client_id, flow_id
    )
    self.assertLen(child_flows, 1)

    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertLen(results, 4)

    for result in results:
      self.assertEqual(
          result.stat.pathspec.pathtype, rdf_paths.PathSpec.PathType.OS
      )

    expected_paths = [
        file_bar_path,
        file_bar_path,  # Bar
        file_foo_path,
        file_foo_path,  # Foo
    ]
    self.assertCountEqual(expected_paths, self._getResultsPaths(results))

    expected_hashes = [
        "None",
        file_bar_hash,  # Bar
        "None",
        file_foo_hash,  # Foo
    ]
    self.assertCountEqual(expected_hashes, self._getResultsHashes(results))

    expected_statuses = [
        # Bar
        rdf_file_finder.CollectFilesByKnownPathResult.Status.IN_PROGRESS,
        rdf_file_finder.CollectFilesByKnownPathResult.Status.COLLECTED,
        # Foo
        rdf_file_finder.CollectFilesByKnownPathResult.Status.IN_PROGRESS,
        rdf_file_finder.CollectFilesByKnownPathResult.Status.COLLECTED,
    ]
    self.assertCountEqual(expected_statuses, self._getResultsStatus(results))

  def testFileNotRetryable(self):
    temp_dir = self.create_tempdir()
    non_existent_file_path = os.path.join(temp_dir.full_path, "/non_existent")

    flow_id = flow_test_lib.StartAndRunFlow(
        file.CollectFilesByKnownPath,
        self.client_mock,
        client_id=self.client_id,
        flow_args=rdf_file_finder.CollectFilesByKnownPathArgs(
            paths=[non_existent_file_path],
        ),
        creator=self.test_username,
    )

    progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)
    self.assertEqual(
        rdf_file_finder.CollectFilesByKnownPathProgress(
            num_in_progress=0,
            num_raw_fs_access_retries=0,
            num_collected=0,
            num_failed=1,
        ),
        progress,
    )

    child_flows = data_store.REL_DB.ReadChildFlowObjects(
        self.client_id, flow_id
    )
    self.assertLen(child_flows, 1)

    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertLen(results, 2)

    for result in results:
      self.assertEqual(result.stat.pathspec.path, non_existent_file_path)
      self.assertEqual(
          result.stat.pathspec.pathtype, rdf_paths.PathSpec.PathType.OS
      )
      self.assertIsNone(result.hash.sha1)

    expected_statuses = [
        rdf_file_finder.CollectFilesByKnownPathResult.Status.IN_PROGRESS,
        rdf_file_finder.CollectFilesByKnownPathResult.Status.FAILED,
    ]
    self.assertCountEqual(expected_statuses, self._getResultsStatus(results))

  def testFetchIs_NOT_RetriedWhenFirstCallSucceeds(self):
    temp_bar_file = self.create_tempfile()
    temp_bar_file.write_bytes(b"bar")
    file_bar_path = temp_bar_file.full_path
    file_bar_hash = hashlib.sha1(b"bar").hexdigest()

    with mock.patch.object(flow_base.FlowBase, "client_os", "Windows"):
      flow_id = flow_test_lib.StartAndRunFlow(
          file.CollectFilesByKnownPath,
          self.client_mock,
          client_id=self.client_id,
          flow_args=rdf_file_finder.CollectFilesByKnownPathArgs(
              paths=[file_bar_path],
          ),
          creator=self.test_username,
      )

    child_flows = data_store.REL_DB.ReadChildFlowObjects(
        self.client_id, flow_id
    )
    self.assertLen(child_flows, 1)

    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)
    self.assertEqual(
        rdf_file_finder.CollectFilesByKnownPathProgress(
            num_in_progress=0,
            num_raw_fs_access_retries=0,
            num_collected=1,
            num_failed=0,
        ),
        progress,
    )

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertLen(results, 2)

    for result in results:
      self.assertEqual(result.stat.pathspec.path, file_bar_path)

    expected_pathtypes = [
        # First call to MultiGetFile (progress, success)
        rdf_paths.PathSpec.PathType.OS,
        # Final status (success)
        rdf_paths.PathSpec.PathType.OS,
    ]
    self.assertCountEqual(expected_pathtypes, self._getResultsPathType(results))

    expected_statuses = [
        # First call to MultiGetFile (progress, success)
        rdf_file_finder.CollectFilesByKnownPathResult.Status.IN_PROGRESS,
        # Final status (success)
        rdf_file_finder.CollectFilesByKnownPathResult.Status.COLLECTED,
    ]
    self.assertCountEqual(expected_statuses, self._getResultsStatus(results))

    expected_hashes = ["None", file_bar_hash]
    self.assertCountEqual(expected_hashes, self._getResultsHashes(results))

  def testFetch_RetriesOnlyNotSuccessfulPaths(self):
    temp_dir = self.create_tempdir()
    non_existent_file_path = os.path.join(temp_dir.full_path, "/non_existent")

    temp_foo_file = self.create_tempfile()
    temp_foo_file.write_bytes(b"foo")
    existent_file_path = temp_foo_file.full_path

    flow_id = flow_test_lib.StartAndRunFlow(
        file.CollectFilesByKnownPath,
        self.client_mock,
        client_id=self.client_id,
        flow_args=rdf_file_finder.CollectFilesByKnownPathArgs(
            paths=[non_existent_file_path, existent_file_path],
        ),
        creator=self.test_username,
    )

    progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)
    self.assertEqual(
        rdf_file_finder.CollectFilesByKnownPathProgress(
            num_in_progress=0,
            num_raw_fs_access_retries=0,
            num_collected=1,
            num_failed=1,
        ),
        progress,
    )

    child_flows = data_store.REL_DB.ReadChildFlowObjects(
        self.client_id, flow_id
    )
    self.assertLen(child_flows, 1)

    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertLen(results, 4)

    in_progress_results = [
        result
        for result in results
        if result.status
        == rdf_file_finder.CollectFilesByKnownPathResult.Status.IN_PROGRESS
    ]
    self.assertLen(in_progress_results, 2)

    self.assertEqual(
        set([result.stat.pathspec.path for result in in_progress_results]),
        set([non_existent_file_path, existent_file_path]),
    )

    collected_results = [
        result
        for result in results
        if result.status
        == rdf_file_finder.CollectFilesByKnownPathResult.Status.COLLECTED
    ]
    self.assertLen(collected_results, 1)
    self.assertEqual(
        collected_results[0].stat.pathspec.path, existent_file_path
    )
    self.assertIsNotNone(collected_results[0].hash.sha1)

    failed_results = [
        result
        for result in results
        if result.status
        == rdf_file_finder.CollectFilesByKnownPathResult.Status.FAILED
    ]
    self.assertLen(failed_results, 1)
    self.assertEqual(
        failed_results[0].stat.pathspec.path, non_existent_file_path
    )
    self.assertIsNone(failed_results[0].hash.sha1)

  def testFetchIsRetriedWithRawOnWindows(self):
    temp_bar_file = self.create_tempfile()
    temp_bar_file.write_bytes(b"bar")
    file_bar_path = temp_bar_file.full_path
    file_bar_hash = hashlib.sha1(b"bar").hexdigest()

    with mock.patch.object(flow_base.FlowBase, "client_os", "Windows"):
      with _PatchVfs():
        flow_id = flow_test_lib.StartAndRunFlow(
            file.CollectFilesByKnownPath,
            self.client_mock,
            client_id=self.client_id,
            flow_args=rdf_file_finder.CollectFilesByKnownPathArgs(
                paths=[file_bar_path],
            ),
            creator=self.test_username,
        )

    progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)
    self.assertEqual(
        rdf_file_finder.CollectFilesByKnownPathProgress(
            num_in_progress=0,
            num_raw_fs_access_retries=1,
            num_collected=1,
            num_failed=0,
        ),
        progress,
    )

    child_flows = data_store.REL_DB.ReadChildFlowObjects(
        self.client_id, flow_id
    )
    self.assertLen(child_flows, 2)

    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertLen(results, 3)

    for result in results:
      self.assertEqual(result.stat.pathspec.path, file_bar_path)

    expected_pathtypes = [
        # First call to MultiGetFile (progress, failure)
        rdf_paths.PathSpec.PathType.OS,
        # Second call to MultiGetFile (progress, will succeed)
        config.CONFIG["Server.raw_filesystem_access_pathtype"],
        # Final status (success)
        config.CONFIG["Server.raw_filesystem_access_pathtype"],
    ]
    self.assertCountEqual(expected_pathtypes, self._getResultsPathType(results))

    expected_statuses = [
        # First call to MultiGetFile (progress, failure)
        rdf_file_finder.CollectFilesByKnownPathResult.Status.IN_PROGRESS,
        # Second call to MultiGetFile (progress, will succeed)
        rdf_file_finder.CollectFilesByKnownPathResult.Status.IN_PROGRESS,
        # Final status (success)
        rdf_file_finder.CollectFilesByKnownPathResult.Status.COLLECTED,
    ]
    self.assertCountEqual(expected_statuses, self._getResultsStatus(results))

    expected_hashes = ["None", "None", file_bar_hash]
    self.assertCountEqual(expected_hashes, self._getResultsHashes(results))

  def testFailsAfterRetryOnFailedFetchOnWindows(self):
    temp_bar_file = self.create_tempfile()
    temp_bar_file.write_bytes(b"bar")
    file_bar_path = temp_bar_file.full_path

    with mock.patch.object(flow_base.FlowBase, "client_os", "Windows"):
      with mock.patch.object(vfs, "VFSOpen", side_effect=IOError("mock err")):
        flow_id = flow_test_lib.StartAndRunFlow(
            file.CollectFilesByKnownPath,
            self.client_mock,
            client_id=self.client_id,
            flow_args=rdf_file_finder.CollectFilesByKnownPathArgs(
                paths=[file_bar_path],
            ),
            creator=self.test_username,
        )

    progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)
    self.assertEqual(
        rdf_file_finder.CollectFilesByKnownPathProgress(
            num_in_progress=0,
            num_raw_fs_access_retries=1,
            num_collected=0,
            num_failed=1,
        ),
        progress,
    )

    child_flows = data_store.REL_DB.ReadChildFlowObjects(
        self.client_id, flow_id
    )
    self.assertLen(child_flows, 2)

    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertLen(results, 3)
    for result in results:
      self.assertEqual(result.stat.pathspec.path, file_bar_path)
      self.assertIsNone(result.hash.sha1)

    expected_pathtypes = [
        # First call to MultiGetFile (progress, failure)
        rdf_paths.PathSpec.PathType.OS,
        # Second call to MultiGetFile (progress, will fail)
        config.CONFIG["Server.raw_filesystem_access_pathtype"],
        # Final status (failure)
        config.CONFIG["Server.raw_filesystem_access_pathtype"],
    ]
    self.assertCountEqual(expected_pathtypes, self._getResultsPathType(results))

    expected_statuses = [
        # First call to MultiGetFile (progress, failure)
        rdf_file_finder.CollectFilesByKnownPathResult.Status.IN_PROGRESS,
        # Second call to MultiGetFile (progress, will fail)
        rdf_file_finder.CollectFilesByKnownPathResult.Status.IN_PROGRESS,
        # Final status (failure)
        rdf_file_finder.CollectFilesByKnownPathResult.Status.FAILED,
    ]
    self.assertCountEqual(expected_statuses, self._getResultsStatus(results))

  def _getResultsPaths(
      self, results: rdf_file_finder.CollectFilesByKnownPathResult
  ) -> list[str]:
    paths: str = []
    for result in results:
      paths.append(result.stat.pathspec.path)
    return paths

  def _getResultsPathType(
      self, results: rdf_file_finder.CollectFilesByKnownPathResult
  ) -> list["rdf_paths.PathSpec.PathType"]:
    pathtypes: rdf_paths.PathSpec.PathType = []
    for result in results:
      pathtypes.append(result.stat.pathspec.pathtype)
    return pathtypes

  def _getResultsStatus(
      self, results: rdf_file_finder.CollectFilesByKnownPathResult
  ) -> list["rdf_file_finder.CollectFilesByKnownPathResult.Status"]:
    statuses: rdf_file_finder.CollectFilesByKnownPathResult.Status = []
    for result in results:
      statuses.append(result.status)
    return statuses

  def _getResultsHashes(
      self, results: rdf_file_finder.CollectFilesByKnownPathResult
  ) -> list[str]:
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

    flow_id = flow_test_lib.StartAndRunFlow(
        file.CollectMultipleFiles,
        self.client_mock,
        client_id=self.client_id,
        flow_args=rdf_file_finder.CollectMultipleFilesArgs(
            path_expressions=[path],
        ),
        creator=self.test_username,
    )

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertLen(results, 2)

    # Check that both returned results are success.
    collected_status = (
        rdf_file_finder.CollectMultipleFilesResult.Status.COLLECTED
    )

    for f in results:
      self.assertEqual(f.status, collected_status)
      self.assertEqual(f.stat.pathspec.pathtype, rdf_paths.PathSpec.PathType.OS)

      # ClientFileFinder flow calculates the sha256 hash of the collected file
      # on the server and adds it to the result.
      if f.stat.pathspec.path == os.path.join(self.files["bar"].path):
        self.assertEqual(str(f.hash.sha256), self.files["bar"].sha256)
      else:
        self.assertEqual(f.stat.pathspec.path, self.files["baz"].path)
        self.assertEqual(str(f.hash.sha256), self.files["baz"].sha256)

  def testFailsAfterRetryOnFailedFetchOnWindows(self):
    temp_bar_file = self.create_tempfile()
    temp_bar_file.write_bytes(b"bar")
    file_bar_path = temp_bar_file.full_path

    def _MockCFF(self):
      if self.args.action.action_type == flows_pb2.FileFinderAction.Action.STAT:
        self.SendReplyProto(
            flows_pb2.FileFinderResult(
                stat_entry=jobs_pb2.StatEntry(
                    pathspec=jobs_pb2.PathSpec(
                        path=file_bar_path,
                        pathtype=jobs_pb2.PathSpec.PathType.OS,
                    ),
                ),
            )
        )
      else:
        raise IOError("Failed to get the file sorry")

    with mock.patch.object(flow_base.FlowBase, "client_os", "Windows"):
      with mock.patch.object(file_finder.ClientFileFinder, "Start", _MockCFF):
        flow_id = flow_test_lib.StartAndRunFlow(
            file.CollectMultipleFiles,
            self.client_mock,
            client_id=self.client_id,
            flow_args=rdf_file_finder.CollectMultipleFilesArgs(
                path_expressions=[file_bar_path],
            ),
            creator=self.test_username,
            check_flow_errors=False,
        )

    # The flow should fail because it found a file, but failed to get
    # its contents (all content-fetching failed).
    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.ERROR)

    progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)
    self.assertEqual(
        rdf_file_finder.CollectMultipleFilesProgress(
            num_found=1,
            num_in_progress=0,
            num_raw_fs_access_retries=1,
            num_collected=0,
            num_failed=1,
        ),
        progress,
    )

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertLen(results, 1)
    self.assertEqual(results[0].stat.pathspec.path, file_bar_path)
    self.assertEqual(
        results[0].stat.pathspec.pathtype,
        config.CONFIG["Server.raw_filesystem_access_pathtype"],
    )
    self.assertFalse(results[0].HasField("hash"))
    self.assertEqual(
        results[0].status,
        rdf_file_finder.CollectMultipleFilesResult.Status.FAILED,
    )

  def testPartialResults_UnfourtunatelyDoesNotWork(self):
    file_should_succeed = self.create_tempfile()
    file_should_succeed.write_bytes(b"succeeds")
    file_should_succeed_path = file_should_succeed.full_path

    file_fails = self.create_tempfile()
    file_fails.write_bytes(b"fails")
    file_fails_path = file_fails.full_path

    def _MockCFF(self):
      # For `STAT` we return both files.
      if self.args.action.action_type == flows_pb2.FileFinderAction.Action.STAT:
        self.SendReplyProto(
            flows_pb2.FileFinderResult(
                stat_entry=jobs_pb2.StatEntry(
                    pathspec=jobs_pb2.PathSpec(
                        path=file_should_succeed_path,
                        pathtype=jobs_pb2.PathSpec.PathType.OS,
                    ),
                ),
            )
        )
        self.SendReplyProto(
            flows_pb2.FileFinderResult(
                stat_entry=jobs_pb2.StatEntry(
                    pathspec=jobs_pb2.PathSpec(
                        path=file_fails_path,
                        pathtype=jobs_pb2.PathSpec.PathType.OS,
                    ),
                ),
            )
        )
      else:
        # We only return for one of the files, then fail.
        self.SendReplyProto(
            flows_pb2.FileFinderResult(
                stat_entry=jobs_pb2.StatEntry(
                    pathspec=jobs_pb2.PathSpec(
                        path=file_should_succeed_path,
                        pathtype=jobs_pb2.PathSpec.PathType.OS,
                    ),
                ),
                hash_entry=jobs_pb2.HashEntry(
                    sha256=hashlib.sha256(b"succeeds").hexdigest(),
                ),
            )
        )
        # Raising an error currently makes partial results (like the above) be
        # ignored (which is unfourtunately what currently happens on the actual
        # CFF implementation). This test documents the behavior while it's not
        # updated.
        self.Error(error_message="Then something went wrong")

    with mock.patch.object(flow_base.FlowBase, "client_os", "Windows"):
      with mock.patch.object(file_finder.ClientFileFinder, "Start", _MockCFF):
        flow_id = flow_test_lib.StartAndRunFlow(
            file.CollectMultipleFiles,
            self.client_mock,
            client_id=self.client_id,
            flow_args=rdf_file_finder.CollectMultipleFilesArgs(
                path_expressions=[file_should_succeed_path],
            ),
            creator=self.test_username,
            check_flow_errors=False,
        )

    # The flow would ideally succeed, because we have partial results.
    # As mentioned above, currently it fails.
    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.ERROR)

    progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)
    self.assertEqual(
        rdf_file_finder.CollectMultipleFilesProgress(
            num_found=2,
            num_in_progress=0,
            num_raw_fs_access_retries=2,
            num_collected=0,
            num_failed=2,
        ),
        progress,
    )

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertLen(results, 2)

    paths = [r.stat.pathspec.path for r in results]
    self.assertCountEqual(paths, [file_should_succeed_path, file_fails_path])

    for r in results:
      self.assertEqual(
          r.stat.pathspec.pathtype,
          config.CONFIG["Server.raw_filesystem_access_pathtype"],
      )
      self.assertFalse(r.HasField("hash"))
      self.assertEqual(
          r.status,
          rdf_file_finder.CollectMultipleFilesResult.Status.FAILED,
      )

  def testCorrectlyReportProgressForSuccessfullyCollectedFiles(self):
    path = os.path.join(self.fixture_path, "b*")

    flow_id = flow_test_lib.StartAndRunFlow(
        file.CollectMultipleFiles,
        self.client_mock,
        client_id=self.client_id,
        flow_args=rdf_file_finder.CollectMultipleFilesArgs(
            path_expressions=[path],
        ),
        creator=self.test_username,
    )

    progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)
    self.assertEqual(
        rdf_file_finder.CollectMultipleFilesProgress(
            num_collected=2,
            num_failed=0,
            num_found=2,
            num_in_progress=0,
            num_raw_fs_access_retries=0,
        ),
        progress,
    )

  def testPassesNoConditionsToClientFileFinderWhenNoConditionsSpecified(self):
    flow_id = flow_test_lib.StartFlow(
        file.CollectMultipleFiles,
        client_id=self.client_id,
        flow_args=rdf_file_finder.CollectMultipleFilesArgs(
            path_expressions=["/some/path"],
        ),
    )

    children = data_store.REL_DB.ReadChildFlowObjects(self.client_id, flow_id)
    self.assertLen(children, 1)

    child = children[0]
    self.assertEqual(
        child.flow_class_name, file_finder.ClientFileFinder.__name__
    )
    conditions = mig_flow_objects.ToRDFFlow(child).args.conditions
    self.assertEmpty(conditions)

  def testPassesAllConditionsToClientFileFinderWhenAllConditionsSpecified(self):
    modification_time = rdf_file_finder.FileFinderModificationTimeCondition(
        min_last_modified_time=rdfvalue.RDFDatetime.Now(),
    )

    access_time = rdf_file_finder.FileFinderAccessTimeCondition(
        min_last_access_time=rdfvalue.RDFDatetime.Now(),
    )

    inode_change_time = rdf_file_finder.FileFinderInodeChangeTimeCondition(
        min_last_inode_change_time=rdfvalue.RDFDatetime.Now(),
    )

    size = rdf_file_finder.FileFinderSizeCondition(
        min_file_size=42,
    )

    ext_flags = rdf_file_finder.FileFinderExtFlagsCondition(
        linux_bits_set=42,
    )

    contents_regex_match = (
        rdf_file_finder.FileFinderContentsRegexMatchCondition(
            regex=b"foo",
        )
    )

    contents_literal_match = (
        rdf_file_finder.FileFinderContentsLiteralMatchCondition(
            literal=b"bar",
        )
    )

    flow_id = flow_test_lib.StartFlow(
        file.CollectMultipleFiles,
        client_id=self.client_id,
        flow_args=rdf_file_finder.CollectMultipleFilesArgs(
            path_expressions=["/some/path"],
            modification_time=modification_time,
            access_time=access_time,
            inode_change_time=inode_change_time,
            size=size,
            ext_flags=ext_flags,
            contents_regex_match=contents_regex_match,
            contents_literal_match=contents_literal_match,
        ),
    )

    children = data_store.REL_DB.ReadChildFlowObjects(self.client_id, flow_id)
    self.assertLen(children, 1)

    child = children[0]
    self.assertEqual(
        child.flow_class_name, file_finder.ClientFileFinder.__name__
    )
    # We expect 7 condition-attributes to be converted
    # to 7 FileFinderConditions.
    conditions = mig_flow_objects.ToRDFFlow(child).args.conditions
    self.assertLen(conditions, 7)

    def _GetCondition(condition_type):
      for c in conditions:
        if c.condition_type == condition_type:
          return c.UnionCast()

      raise RuntimeError(f"Condition of type {condition_type} not found.")

    self.assertEqual(
        _GetCondition(
            rdf_file_finder.FileFinderCondition.Type.MODIFICATION_TIME
        ),
        modification_time,
    )

    self.assertEqual(
        _GetCondition(rdf_file_finder.FileFinderCondition.Type.ACCESS_TIME),
        access_time,
    )

    self.assertEqual(
        _GetCondition(
            rdf_file_finder.FileFinderCondition.Type.INODE_CHANGE_TIME
        ),
        inode_change_time,
    )

    self.assertEqual(
        _GetCondition(rdf_file_finder.FileFinderCondition.Type.SIZE), size
    )

    self.assertEqual(
        _GetCondition(rdf_file_finder.FileFinderCondition.Type.EXT_FLAGS),
        ext_flags,
    )

    self.assertEqual(
        _GetCondition(
            rdf_file_finder.FileFinderCondition.Type.CONTENTS_REGEX_MATCH
        ),
        contents_regex_match,
    )

    self.assertEqual(
        _GetCondition(
            rdf_file_finder.FileFinderCondition.Type.CONTENTS_LITERAL_MATCH
        ),
        contents_literal_match,
    )


class TestStatMultipleFiles(flow_test_lib.FlowTestsBaseclass):

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)
    self.client_mock = action_mocks.CollectMultipleFilesClientMock()

  def testReturnsSingleFileStat(self):
    timestamp_before_file_creation = rdfvalue.RDFDatetimeSeconds.Now()
    temp_bar_file_content = b"bar"
    temp_bar_file = self.create_tempfile()
    temp_bar_file.write_bytes(temp_bar_file_content)
    file_bar_path = temp_bar_file.full_path

    flow_id = flow_test_lib.StartAndRunFlow(
        file.StatMultipleFiles,
        self.client_mock,
        client_id=self.client_id,
        flow_args=rdf_file_finder.StatMultipleFilesArgs(
            path_expressions=[file_bar_path],
        ),
        creator=self.test_username,
    )

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)

    flow_finished_timestamp = rdfvalue.RDFDatetimeSeconds.Now()

    self.assertLen(results, 1)
    self.assertEqual(
        results[0].pathspec.pathtype,
        rdf_paths.PathSpec.PathType.OS,
    )
    self.assertEqual(file_bar_path, results[0].pathspec.path)
    self.assertLen(temp_bar_file_content, results[0].st_size)

    self.assertBetween(
        results[0].st_atime,
        timestamp_before_file_creation,
        flow_finished_timestamp,
    )

    self.assertBetween(
        results[0].st_mtime,
        timestamp_before_file_creation,
        flow_finished_timestamp,
    )

    self.assertBetween(
        results[0].st_ctime,
        timestamp_before_file_creation,
        flow_finished_timestamp,
    )

  def testReturnsMultipleFileStats(self):
    timestamp_before_file_creation = rdfvalue.RDFDatetimeSeconds.Now()
    temp_bar_file_content = b"bar"
    temp_bar_file = self.create_tempfile()
    temp_bar_file.write_bytes(temp_bar_file_content)
    file_bar_path = temp_bar_file.full_path

    temp_foo_file_content = b"bar"
    temp_foo_file = self.create_tempfile()
    temp_foo_file.write_bytes(temp_foo_file_content)
    file_foo_path = temp_foo_file.full_path

    flow_id = flow_test_lib.StartAndRunFlow(
        file.StatMultipleFiles,
        self.client_mock,
        client_id=self.client_id,
        flow_args=rdf_file_finder.StatMultipleFilesArgs(
            path_expressions=[file_bar_path, file_foo_path],
        ),
        creator=self.test_username,
    )

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)

    flow_finished_timestamp = rdfvalue.RDFDatetimeSeconds.Now()

    self.assertLen(results, 2)

    self.assertEqual(results[0].pathspec.path, file_bar_path)
    self.assertEqual(
        results[0].pathspec.pathtype,
        rdf_paths.PathSpec.PathType.OS,
    )

    self.assertLen(temp_bar_file_content, results[0].st_size)
    self.assertBetween(
        results[0].st_atime,
        timestamp_before_file_creation,
        flow_finished_timestamp,
    )

    self.assertBetween(
        results[0].st_mtime,
        timestamp_before_file_creation,
        flow_finished_timestamp,
    )

    self.assertBetween(
        results[0].st_ctime,
        timestamp_before_file_creation,
        flow_finished_timestamp,
    )

    self.assertEqual(results[1].pathspec.path, file_foo_path)
    self.assertEqual(
        results[1].pathspec.pathtype,
        rdf_paths.PathSpec.PathType.OS,
    )
    self.assertEqual(results[1].st_size, len(temp_foo_file_content))
    self.assertBetween(
        results[1].st_atime,
        timestamp_before_file_creation,
        flow_finished_timestamp,
    )

    self.assertBetween(
        results[1].st_mtime,
        timestamp_before_file_creation,
        flow_finished_timestamp,
    )

    self.assertBetween(
        results[1].st_ctime,
        timestamp_before_file_creation,
        flow_finished_timestamp,
    )

  def testFileNotFound(self):
    temp_dir = self.create_tempdir()
    non_existent_file_path = os.path.join(temp_dir.full_path, "/non_existent")

    flow_id = flow_test_lib.StartAndRunFlow(
        file.StatMultipleFiles,
        self.client_mock,
        client_id=self.client_id,
        flow_args=rdf_file_finder.StatMultipleFilesArgs(
            path_expressions=[non_existent_file_path],
        ),
        creator=self.test_username,
    )

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertEmpty(results)

  def testPassesNoConditionsToClientFileFinderWhenNoConditionsSpecified(self):
    flow_id = flow_test_lib.StartFlow(
        file.StatMultipleFiles,
        client_id=self.client_id,
        flow_args=rdf_file_finder.StatMultipleFilesArgs(
            path_expressions=["/some/path"],
        ),
    )

    children = data_store.REL_DB.ReadChildFlowObjects(self.client_id, flow_id)
    self.assertLen(children, 1)

    child = children[0]
    self.assertEqual(
        child.flow_class_name, file_finder.ClientFileFinder.__name__
    )
    conditions = mig_flow_objects.ToRDFFlow(child).args.conditions
    self.assertEmpty(conditions)

  def testPassesAllConditionsToClientFileFinderWhenAllConditionsSpecified(self):
    modification_time = rdf_file_finder.FileFinderModificationTimeCondition(
        min_last_modified_time=rdfvalue.RDFDatetime.Now(),
    )

    access_time = rdf_file_finder.FileFinderAccessTimeCondition(
        min_last_access_time=rdfvalue.RDFDatetime.Now(),
    )

    inode_change_time = rdf_file_finder.FileFinderInodeChangeTimeCondition(
        min_last_inode_change_time=rdfvalue.RDFDatetime.Now(),
    )

    size = rdf_file_finder.FileFinderSizeCondition(
        min_file_size=42,
    )

    ext_flags = rdf_file_finder.FileFinderExtFlagsCondition(
        linux_bits_set=42,
    )

    contents_regex_match = (
        rdf_file_finder.FileFinderContentsRegexMatchCondition(
            regex=b"foo",
        )
    )

    contents_literal_match = (
        rdf_file_finder.FileFinderContentsLiteralMatchCondition(
            literal=b"bar",
        )
    )

    flow_id = flow_test_lib.StartFlow(
        file.StatMultipleFiles,
        client_id=self.client_id,
        flow_args=rdf_file_finder.StatMultipleFilesArgs(
            path_expressions=["/some/path"],
            modification_time=modification_time,
            access_time=access_time,
            inode_change_time=inode_change_time,
            size=size,
            ext_flags=ext_flags,
            contents_regex_match=contents_regex_match,
            contents_literal_match=contents_literal_match,
        ),
    )

    children = data_store.REL_DB.ReadChildFlowObjects(self.client_id, flow_id)
    self.assertLen(children, 1)

    child = children[0]
    self.assertEqual(
        child.flow_class_name, file_finder.ClientFileFinder.__name__
    )
    # We expect 7 condition-attributes to be converted
    # to 7 FileFinderConditions.
    conditions = mig_flow_objects.ToRDFFlow(child).args.conditions
    self.assertLen(conditions, 7)

    def _GetCondition(condition_type):
      for c in conditions:
        if c.condition_type == condition_type:
          return c.UnionCast()

      raise RuntimeError(f"Condition of type {condition_type} not found.")

    self.assertEqual(
        _GetCondition(
            rdf_file_finder.FileFinderCondition.Type.MODIFICATION_TIME
        ),
        modification_time,
    )

    self.assertEqual(
        _GetCondition(rdf_file_finder.FileFinderCondition.Type.ACCESS_TIME),
        access_time,
    )

    self.assertEqual(
        _GetCondition(
            rdf_file_finder.FileFinderCondition.Type.INODE_CHANGE_TIME
        ),
        inode_change_time,
    )

    self.assertEqual(
        _GetCondition(rdf_file_finder.FileFinderCondition.Type.SIZE), size
    )

    self.assertEqual(
        _GetCondition(rdf_file_finder.FileFinderCondition.Type.EXT_FLAGS),
        ext_flags,
    )

    self.assertEqual(
        _GetCondition(
            rdf_file_finder.FileFinderCondition.Type.CONTENTS_REGEX_MATCH
        ),
        contents_regex_match,
    )

    self.assertEqual(
        _GetCondition(
            rdf_file_finder.FileFinderCondition.Type.CONTENTS_LITERAL_MATCH
        ),
        contents_literal_match,
    )


class TestHashMultipleFiles(flow_test_lib.FlowTestsBaseclass):

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)
    self.client_mock = action_mocks.CollectMultipleFilesClientMock()

  def testReturnsSingleFileHash(self):
    temp_bar_file = self.create_tempfile()
    temp_bar_file.write_bytes(b"bar")
    file_bar_path = temp_bar_file.full_path
    file_bar_hash = hashlib.sha1(b"bar").hexdigest()

    flow_id = flow_test_lib.StartAndRunFlow(
        file.HashMultipleFiles,
        self.client_mock,
        client_id=self.client_id,
        flow_args=rdf_file_finder.HashMultipleFilesArgs(
            path_expressions=[file_bar_path],
        ),
        creator=self.test_username,
    )

    progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)
    self.assertEqual(
        rdf_file_finder.HashMultipleFilesProgress(
            num_found=1,
            num_in_progress=0,
            num_raw_fs_access_retries=0,
            num_hashed=1,
            num_failed=0,
        ),
        progress,
    )

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)

    self.assertLen(results, 1)
    self.assertEqual(
        results[0].stat.pathspec.pathtype,
        rdf_paths.PathSpec.PathType.OS,
    )
    self.assertEqual(file_bar_path, results[0].stat.pathspec.path)
    self.assertEqual(
        results[0].status,
        rdf_file_finder.CollectMultipleFilesResult.Status.COLLECTED,
    )
    self.assertEqual(results[0].hash.sha1, file_bar_hash)

  def testReturnsMultipleFileHashes(self):
    temp_bar_file = self.create_tempfile()
    temp_bar_file.write_bytes(b"bar")
    file_bar_path = temp_bar_file.full_path
    file_bar_hash = hashlib.sha1(b"bar").hexdigest()

    temp_foo_file = self.create_tempfile()
    temp_foo_file.write_bytes(b"foo")
    file_foo_path = temp_foo_file.full_path
    file_foo_hash = hashlib.sha1(b"foo").hexdigest()

    flow_id = flow_test_lib.StartAndRunFlow(
        file.HashMultipleFiles,
        self.client_mock,
        client_id=self.client_id,
        flow_args=rdf_file_finder.HashMultipleFilesArgs(
            path_expressions=[file_bar_path, file_foo_path],
        ),
        creator=self.test_username,
    )

    progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)
    self.assertEqual(
        rdf_file_finder.HashMultipleFilesProgress(
            num_found=2,
            num_in_progress=0,
            num_raw_fs_access_retries=0,
            num_hashed=2,
            num_failed=0,
        ),
        progress,
    )

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)

    self.assertLen(results, 2)
    # TODO: Refactor not to depend on the sorting.
    order = {file_bar_path: 0, file_foo_path: 1}
    results.sort(key=lambda r: order[r.stat.pathspec.path])

    self.assertEqual(results[0].stat.pathspec.path, file_bar_path)
    self.assertEqual(
        results[0].stat.pathspec.pathtype, rdf_paths.PathSpec.PathType.OS
    )
    self.assertEqual(
        results[0].status,
        rdf_file_finder.CollectFilesByKnownPathResult.Status.COLLECTED,
    )
    self.assertEqual(results[0].hash.sha1, file_bar_hash)

    self.assertEqual(results[1].stat.pathspec.path, file_foo_path)
    self.assertEqual(
        results[1].stat.pathspec.pathtype, rdf_paths.PathSpec.PathType.OS
    )
    self.assertEqual(
        results[1].status,
        rdf_file_finder.CollectFilesByKnownPathResult.Status.COLLECTED,
    )
    self.assertEqual(results[1].hash.sha1, file_foo_hash)

  def testFileNotFound(self):
    temp_dir = self.create_tempdir()
    non_existent_file_path = os.path.join(temp_dir.full_path, "/non_existent")

    flow_id = flow_test_lib.StartAndRunFlow(
        file.HashMultipleFiles,
        self.client_mock,
        client_id=self.client_id,
        flow_args=rdf_file_finder.HashMultipleFilesArgs(
            path_expressions=[non_existent_file_path],
        ),
        creator=self.test_username,
    )

    progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)
    self.assertEqual(
        rdf_file_finder.HashMultipleFilesProgress(
            num_found=0,
            num_in_progress=0,
            num_raw_fs_access_retries=0,
            num_hashed=0,
            num_failed=0,
        ),
        progress,
    )

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertEmpty(results)

  def testEarlyFinishesIfNoStatsFound(self):
    def _MockCFF(self):
      if self.args.action.action_type == flows_pb2.FileFinderAction.Action.STAT:
        pass  # No files found.
      else:
        raise IOError("Shouldn't be called")

    with mock.patch.object(file_finder.ClientFileFinder, "Start", _MockCFF):
      flow_id = flow_test_lib.StartAndRunFlow(
          file.HashMultipleFiles,
          self.client_mock,
          client_id=self.client_id,
          flow_args=rdf_file_finder.HashMultipleFilesArgs(
              path_expressions=[
                  "for some reason doesn't return a stat but succeeds"
              ],
          ),
          creator=self.test_username,
      )

    # The flow should succeed.
    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    children = data_store.REL_DB.ReadChildFlowObjects(self.client_id, flow_id)
    self.assertLen(children, 1)  # One STAT call.

    progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)
    self.assertEqual(
        rdf_file_finder.HashMultipleFilesProgress(
            num_found=0,
            num_in_progress=0,
            num_raw_fs_access_retries=0,
            num_hashed=0,
            num_failed=0,
        ),
        progress,
    )

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertEmpty(results)

  def testFailsAfterRetryOnFailedFetchOnWindows(self):
    temp_bar_file = self.create_tempfile()
    temp_bar_file.write_bytes(b"bar")
    file_bar_path = temp_bar_file.full_path

    def _MockCFF(self):
      if self.args.action.action_type == flows_pb2.FileFinderAction.Action.STAT:
        self.SendReplyProto(
            flows_pb2.FileFinderResult(
                stat_entry=jobs_pb2.StatEntry(
                    pathspec=jobs_pb2.PathSpec(
                        path=file_bar_path,
                        pathtype=jobs_pb2.PathSpec.PathType.OS,
                    ),
                ),
            )
        )
      else:
        raise IOError("Failed to get the hash sorry")

    with mock.patch.object(flow_base.FlowBase, "client_os", "Windows"):
      with mock.patch.object(file_finder.ClientFileFinder, "Start", _MockCFF):
        flow_id = flow_test_lib.StartAndRunFlow(
            file.HashMultipleFiles,
            self.client_mock,
            client_id=self.client_id,
            flow_args=rdf_file_finder.HashMultipleFilesArgs(
                path_expressions=[file_bar_path],
            ),
            creator=self.test_username,
            check_flow_errors=False,
        )

    # The flow should fail because it found a file, but failed to get
    # its hash.
    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.ERROR)

    progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)
    self.assertEqual(
        rdf_file_finder.HashMultipleFilesProgress(
            num_found=1,
            num_in_progress=0,
            num_raw_fs_access_retries=1,
            num_hashed=0,
            num_failed=1,
        ),
        progress,
    )

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertLen(results, 1)
    self.assertEqual(results[0].stat.pathspec.path, file_bar_path)
    self.assertEqual(
        results[0].stat.pathspec.pathtype,
        config.CONFIG["Server.raw_filesystem_access_pathtype"],
    )
    self.assertEqual(
        results[0].status,
        rdf_file_finder.CollectMultipleFilesResult.Status.FAILED,
    )
    self.assertIsNone(results[0].hash.sha1)

  def testCorrectlyReportProgressForSuccessfullyCollectedFileHashes(self):
    temp_bar_file = self.create_tempfile()
    temp_bar_file.write_bytes(b"bar")
    file_bar_path = temp_bar_file.full_path

    temp_foo_file = self.create_tempfile()
    temp_foo_file.write_bytes(b"foo")
    file_foo_path = temp_foo_file.full_path

    flow_id = flow_test_lib.StartAndRunFlow(
        file.HashMultipleFiles,
        self.client_mock,
        client_id=self.client_id,
        flow_args=rdf_file_finder.HashMultipleFilesArgs(
            path_expressions=[file_bar_path, file_foo_path],
        ),
        creator=self.test_username,
    )

    progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)
    self.assertEqual(
        rdf_file_finder.HashMultipleFilesProgress(
            num_hashed=2,
            num_failed=0,
            num_found=2,
            num_in_progress=0,
            num_raw_fs_access_retries=0,
        ),
        progress,
    )

  def testPassesNoConditionsToClientFileFinderWhenNoConditionsSpecified(self):
    flow_id = flow_test_lib.StartFlow(
        file.HashMultipleFiles,
        client_id=self.client_id,
        flow_args=rdf_file_finder.HashMultipleFilesArgs(
            path_expressions=["/some/path"],
        ),
    )

    children = data_store.REL_DB.ReadChildFlowObjects(self.client_id, flow_id)
    self.assertLen(children, 1)

    child = children[0]
    self.assertEqual(
        child.flow_class_name, file_finder.ClientFileFinder.__name__
    )
    conditions = mig_flow_objects.ToRDFFlow(child).args.conditions
    self.assertEmpty(conditions)

  def testPassesAllConditionsToClientFileFinderWhenAllConditionsSpecified(self):
    modification_time = rdf_file_finder.FileFinderModificationTimeCondition(
        min_last_modified_time=rdfvalue.RDFDatetime.Now(),
    )

    access_time = rdf_file_finder.FileFinderAccessTimeCondition(
        min_last_access_time=rdfvalue.RDFDatetime.Now(),
    )

    inode_change_time = rdf_file_finder.FileFinderInodeChangeTimeCondition(
        min_last_inode_change_time=rdfvalue.RDFDatetime.Now(),
    )

    size = rdf_file_finder.FileFinderSizeCondition(
        min_file_size=42,
    )

    ext_flags = rdf_file_finder.FileFinderExtFlagsCondition(
        linux_bits_set=42,
    )

    contents_regex_match = (
        rdf_file_finder.FileFinderContentsRegexMatchCondition(
            regex=b"foo",
        )
    )

    contents_literal_match = (
        rdf_file_finder.FileFinderContentsLiteralMatchCondition(
            literal=b"bar",
        )
    )

    flow_id = flow_test_lib.StartFlow(
        file.HashMultipleFiles,
        client_id=self.client_id,
        flow_args=rdf_file_finder.HashMultipleFilesArgs(
            path_expressions=["/some/path"],
            modification_time=modification_time,
            access_time=access_time,
            inode_change_time=inode_change_time,
            size=size,
            ext_flags=ext_flags,
            contents_regex_match=contents_regex_match,
            contents_literal_match=contents_literal_match,
        ),
    )

    children = data_store.REL_DB.ReadChildFlowObjects(self.client_id, flow_id)
    self.assertLen(children, 1)

    child = children[0]
    self.assertEqual(
        child.flow_class_name, file_finder.ClientFileFinder.__name__
    )
    # We expect 7 condition-attributes to be converted
    # to 7 FileFinderConditions.
    conditions = mig_flow_objects.ToRDFFlow(child).args.conditions
    self.assertLen(conditions, 7)

    def _GetCondition(condition_type):
      for c in conditions:
        if c.condition_type == condition_type:
          return c.UnionCast()

      raise RuntimeError(f"Condition of type {condition_type} not found.")

    self.assertEqual(
        _GetCondition(
            rdf_file_finder.FileFinderCondition.Type.MODIFICATION_TIME
        ),
        modification_time,
    )

    self.assertEqual(
        _GetCondition(rdf_file_finder.FileFinderCondition.Type.ACCESS_TIME),
        access_time,
    )

    self.assertEqual(
        _GetCondition(
            rdf_file_finder.FileFinderCondition.Type.INODE_CHANGE_TIME
        ),
        inode_change_time,
    )

    self.assertEqual(
        _GetCondition(rdf_file_finder.FileFinderCondition.Type.SIZE), size
    )

    self.assertEqual(
        _GetCondition(rdf_file_finder.FileFinderCondition.Type.EXT_FLAGS),
        ext_flags,
    )

    self.assertEqual(
        _GetCondition(
            rdf_file_finder.FileFinderCondition.Type.CONTENTS_REGEX_MATCH
        ),
        contents_regex_match,
    )

    self.assertEqual(
        _GetCondition(
            rdf_file_finder.FileFinderCondition.Type.CONTENTS_LITERAL_MATCH
        ),
        contents_literal_match,
    )


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
