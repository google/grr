#!/usr/bin/env python
"""Tests for the FileFinder flow."""

import glob
import hashlib
import io
import os
import shutil
import stat
import struct
import time
from typing import Iterable, Optional
from unittest import mock

from absl import app

from google.protobuf import any_pb2
from grr_response_client import vfs
from grr_response_client.client_actions.file_finder_utils import uploading
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import mig_paths
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util import temp
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import knowledge_base_pb2
from grr_response_proto import objects_pb2
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server.databases import db
from grr_response_server.databases import db_test_utils
from grr_response_server.flows.general import file_finder
from grr_response_server.flows.general import transfer
from grr_response_server.models import blobs as models_blobs
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import filesystem_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import rrg_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib
from grr_response_proto.rrg import os_pb2 as rrg_os_pb2

# pylint:mode=test


class TestFileFinderFlow(
    vfs_test_lib.VfsTestCase, flow_test_lib.FlowTestsBaseclass
):
  """Test the FileFinder flow."""

  def FileNameToURN(self, fname):
    return (
        rdfvalue.RDFURN(self.client_id)
        .Add("/fs/os")
        .Add(os.path.join(self.base_path, "searching", fname))
    )

  def FilenameToPathComponents(self, fname):
    path = os.path.join(self.base_path, "searching", fname).lstrip("/")
    return tuple(path.split(os.path.sep))

  EXPECTED_SHA256_HASHES = {
      "auth.log": (
          "91c8d6287a095a6fa6437dac50ffe3fe5c5e0d06dff3ae830eedfce515ad6451"
      ),
      "dpkg.log": (
          "48303a1e7ceec679f6d417b819f42779575ffe8eabf9c880d286a1ee074d8145"
      ),
      "dpkg_false.log": (
          "a35aface4b45e3f1a95b0df24efc50e14fbedcaa6a750ba32358eaaffe3c4fb0"
      ),
  }

  def CheckFilesHashed(self, fnames):
    """Checks the returned hashes."""

    for fname in fnames:
      try:
        file_hash = self.EXPECTED_SHA256_HASHES[fname]
      except KeyError as e:
        raise RuntimeError(
            "Can't check unexpected result for correct hashes: %s" % fname
        ) from e

      path_info = data_store.REL_DB.ReadPathInfo(
          self.client_id,
          rdf_objects.PathInfo.PathType.OS,
          components=self.FilenameToPathComponents(fname),
      )
      hash_obj = path_info.hash_entry

      self.assertEqual(hash_obj.sha256, bytes.fromhex(file_hash))

  def CheckFilesNotHashed(self, fnames):
    for fname in fnames:
      try:
        path_info = data_store.REL_DB.ReadPathInfo(
            self.client_id,
            rdf_objects.PathInfo.PathType.OS,
            components=self.FilenameToPathComponents(fname),
        )
        self.assertFalse(path_info.HasField("hash_entry"))
      except db.UnknownPathError:
        pass  # No path at all, everything is okay.

  def CheckFilesDownloaded(self, fnames):
    for fname in fnames:
      path_info = data_store.REL_DB.ReadPathInfo(
          self.client_id,
          rdf_objects.PathInfo.PathType.OS,
          components=self.FilenameToPathComponents(fname),
      )
      size = path_info.stat_entry.st_size

      filepath = os.path.join(self.base_path, "searching", fname)
      with io.open(filepath, mode="rb") as fd:
        test_data = fd.read()

      self.assertEqual(size, len(test_data))

      fd = file_store.OpenFile(
          db.ClientPath(
              self.client_id,
              rdf_objects.PathInfo.PathType.OS,
              components=self.FilenameToPathComponents(fname),
          )
      )

      # Make sure we can actually read the file.
      self.assertEqual(fd.read(), test_data)

  def CheckFilesNotDownloaded(self, fnames):
    for fname in fnames:
      try:
        file_store.OpenFile(
            db.ClientPath(
                self.client_id,
                rdf_objects.PathInfo.PathType.OS,
                components=self.FilenameToPathComponents(fname),
            )
        )
        self.fail("Found downloaded file: %s" % fname)
      except (file_store.FileHasNoContentError, file_store.FileNotFoundError):
        pass

  def CheckFiles(self, expected_fnames, skipped_fnames, results):
    if expected_fnames is None:
      self.assertFalse(results)
      return

    # If results are expected, check that they are present in the results.
    # Also check that there are no other files.
    self.assertLen(results, len(set(expected_fnames + skipped_fnames)))

    for r in results:
      self.assertIsInstance(r, flows_pb2.FileFinderResult)

    self.assertCountEqual(
        [os.path.basename(r.stat_entry.pathspec.path) for r in results],
        expected_fnames + skipped_fnames,
    )

  def CheckReplies(self, replies, action, expected_files, skipped_files):
    reply_count = 0
    for reply in replies:
      self.assertIsInstance(reply, flows_pb2.FileFinderResult)

      is_skipped = (
          mig_paths.ToRDFPathSpec(reply.stat_entry.pathspec).Basename()
          in skipped_files
      )

      reply_count += 1
      if action == flows_pb2.FileFinderAction.Action.STAT:
        self.assertTrue(reply.stat_entry)
        self.assertFalse(reply.HasField("hash_entry"))
      elif action == flows_pb2.FileFinderAction.Action.DOWNLOAD:
        self.assertTrue(reply.stat_entry)
        if not is_skipped:
          self.assertTrue(reply.hash_entry)
      elif action == flows_pb2.FileFinderAction.Action.HASH:
        self.assertTrue(reply.stat_entry)
        if not is_skipped:
          self.assertTrue(reply.hash_entry)

      if action != flows_pb2.FileFinderAction.Action.STAT and not is_skipped:
        # Check that file's hash is correct.
        file_basename = mig_paths.ToRDFPathSpec(
            reply.stat_entry.pathspec
        ).Basename()
        try:
          file_hash = self.EXPECTED_SHA256_HASHES[file_basename]
        except KeyError as e:
          raise RuntimeError(
              "Can't check unexpected result for correct hashes: %s"
              % file_basename
          ) from e

        self.assertEqual(reply.hash_entry.sha256.hex(), file_hash)

    # Skipped files are reported, but not collected/hashed (i.e. the action is
    # skipped).
    self.assertEqual(reply_count, len(expected_files) + len(skipped_files))

  def RunFlow(
      self,
      paths: Optional[list[str]] = None,
      conditions: Optional[list[flows_pb2.FileFinderCondition]] = None,
      action: Optional[flows_pb2.FileFinderAction] = None,
  ) -> list[flows_pb2.FileFinderResult]:
    self.last_session_id = flow_test_lib.StartAndRunFlow(
        file_finder.FileFinder,
        self.client_mock,
        client_id=self.client_id,
        flow_args=flows_pb2.FileFinderArgs(
            paths=paths or [self.path],
            pathtype=jobs_pb2.PathSpec.PathType.OS,
            action=action,
            conditions=conditions,
        ),
        creator=self.test_username,
    )
    flow_results = data_store.REL_DB.ReadFlowResults(
        self.client_id, self.last_session_id, 0, 100_000
    )
    results = []
    for r in flow_results:
      ff_result = flows_pb2.FileFinderResult()
      r.payload.Unpack(ff_result)
      results.append(ff_result)
    return results

  def RunFlowAndCheckResults(
      self,
      conditions=None,
      action=flows_pb2.FileFinderAction.Action.STAT,
      expected_files=None,
      non_expected_files=None,
      skipped_files=None,
      paths=None,
  ):
    if not isinstance(action, flows_pb2.FileFinderAction):
      action = flows_pb2.FileFinderAction(action_type=action)
    action_type = action.action_type

    conditions = conditions or []
    expected_files = expected_files or []
    non_expected_files = non_expected_files or []
    skipped_files = skipped_files or []

    results = self.RunFlow(paths=paths, conditions=conditions, action=action)
    self.CheckReplies(results, action_type, expected_files, skipped_files)

    self.CheckFiles(expected_files, skipped_files, results)

    if action_type == flows_pb2.FileFinderAction.Action.STAT:
      self.CheckFilesNotDownloaded(
          expected_files + non_expected_files + skipped_files
      )
      self.CheckFilesNotHashed(
          expected_files + non_expected_files + skipped_files
      )
    elif action_type == flows_pb2.FileFinderAction.Action.DOWNLOAD:
      self.CheckFilesHashed(expected_files)
      self.CheckFilesNotHashed(non_expected_files + skipped_files)
      self.CheckFilesDownloaded(expected_files)
      self.CheckFilesNotDownloaded(non_expected_files + skipped_files)
      # Downloaded files are hashed to allow for deduping.
    elif action_type == flows_pb2.FileFinderAction.Action.HASH:
      self.CheckFilesNotDownloaded(
          expected_files + non_expected_files + skipped_files
      )
      self.CheckFilesHashed(expected_files)
      self.CheckFilesNotHashed(non_expected_files + skipped_files)
    return results

  def setUp(self):
    super().setUp()
    self.client_mock = action_mocks.ClientFileFinderClientMock()

    self.fixture_path = os.path.join(self.base_path, "searching")
    self.path = os.path.join(self.fixture_path, "*.log")
    self.client_id = self.SetupClient(0)
    vfs.Init()

  def testFileFinderStatActionWithoutConditions(self):
    self.RunFlowAndCheckResults(
        action=flows_pb2.FileFinderAction.Action.STAT,
        expected_files=["auth.log", "dpkg.log", "dpkg_false.log"],
    )

  def testCollectingSingleFileCreatesNecessaryPathInfos(self):
    path = os.path.join(self.fixture_path, "auth.log")
    self.RunFlowAndCheckResults(
        action=flows_pb2.FileFinderAction.Action.DOWNLOAD,
        paths=[path],
        expected_files=[os.path.basename(path)],
    )

    # If the call below doesn't raise, then we have a correct entry in the DB.
    data_store.REL_DB.ReadPathInfo(
        self.client_id,
        rdf_objects.PathInfo.PathType.OS,
        tuple(path.strip(os.path.sep).split(os.path.sep)),
    )

  def testFileFinderStat(self):
    files_to_check = [
        # Some files.
        "VFSFixture/etc/netgroup",
        "osx_fsdata",
        # Matches lsb-release, lsb-release-bad, lsb-release-notubuntu
        "parser_test/lsb-release*",
        # Some directories.
        "a",
        "profiles",
    ]

    paths = [os.path.join(self.base_path, name) for name in files_to_check]
    expected_paths = []
    for name in paths:
      for result in glob.glob(name):
        expected_paths.append(result)

    # There was a bug in FileFinder with files/directories in the root dir.
    paths.append("/bin")
    expected_paths.append("/bin")

    # Make sure all the files still exist.
    self.assertLen(expected_paths, 8)

    results = self.RunFlow(
        action=flows_pb2.FileFinderAction(
            action_type=flows_pb2.FileFinderAction.Action.STAT
        ),
        paths=paths,
    )

    result_paths = [r.stat_entry.pathspec.path for r in results]

    self.assertCountEqual(expected_paths, result_paths)

  FS_NODUMP_FL = 0x00000040
  FS_UNRM_FL = 0x00000002

  def testFileFinderStatExtFlags(self):
    with temp.AutoTempFilePath() as temp_filepath:
      filesystem_test_lib.Chattr(temp_filepath, attrs=["+d"])

      action = flows_pb2.FileFinderAction(
          action_type=flows_pb2.FileFinderAction.Action.STAT
      )
      results = self.RunFlow(action=action, paths=[temp_filepath])
      self.assertLen(results, 1)

      stat_entry = results[0].stat_entry
      self.assertTrue(stat_entry.st_flags_linux & self.FS_NODUMP_FL)
      self.assertFalse(stat_entry.st_flags_linux & self.FS_UNRM_FL)

  def testFileFinderStatExtAttrs(self):
    with temp.AutoTempFilePath() as temp_filepath:
      filesystem_test_lib.SetExtAttr(
          temp_filepath, name=b"user.bar", value=b"quux"
      )
      filesystem_test_lib.SetExtAttr(
          temp_filepath, name=b"user.baz", value=b"norf"
      )

      action = flows_pb2.FileFinderAction(
          action_type=flows_pb2.FileFinderAction.Action.STAT,
          stat=flows_pb2.FileFinderStatActionOptions(
              collect_ext_attrs=True,
          ),
      )
      results = self.RunFlow(action=action, paths=[temp_filepath])
      self.assertLen(results, 1)

      stat_entry = results[0].stat_entry
      self.assertCountEqual(
          stat_entry.ext_attrs,
          [
              jobs_pb2.StatEntry.ExtAttr(name=b"user.bar", value=b"quux"),
              jobs_pb2.StatEntry.ExtAttr(name=b"user.baz", value=b"norf"),
          ],
      )

  def testFileFinderDownloadActionWithMultiplePathsAndFilesInFilestore(self):
    # Do a first run to put all files into the file store.
    self.RunFlowAndCheckResults(
        action=flows_pb2.FileFinderAction.Action.DOWNLOAD,
        expected_files=["auth.log", "dpkg.log", "dpkg_false.log"],
    )

    # This will get the file contents from the filestore instead of collecting
    # them.
    self.RunFlowAndCheckResults(
        action=flows_pb2.FileFinderAction.Action.DOWNLOAD,
        expected_files=["auth.log", "dpkg.log", "dpkg_false.log"],
    )

  def testFileFinderDownloadActionWithoutConditions(self):
    self.RunFlowAndCheckResults(
        action=flows_pb2.FileFinderAction.Action.DOWNLOAD,
        expected_files=["auth.log", "dpkg.log", "dpkg_false.log"],
    )

  def testFileFinderHashActionWithoutConditions(self):
    self.RunFlowAndCheckResults(
        action=flows_pb2.FileFinderAction.Action.HASH,
        expected_files=["auth.log", "dpkg.log", "dpkg_false.log"],
    )

  CONDITION_TESTS_ACTIONS = sorted(
      set(flows_pb2.FileFinderAction.Action.values())
  )

  def testLiteralMatchConditionWithEmptyLiteral(self):
    # No `literal=` provided.
    match = flows_pb2.FileFinderContentsLiteralMatchCondition()
    literal_condition = flows_pb2.FileFinderCondition(
        condition_type=flows_pb2.FileFinderCondition.Type.CONTENTS_LITERAL_MATCH,
        contents_literal_match=match,
    )

    for action in self.CONDITION_TESTS_ACTIONS:
      # Flow arguments validation should fail with an empty literal.
      with self.assertRaises(ValueError):
        self.RunFlowAndCheckResults(
            action=action, conditions=[literal_condition]
        )

  def testLiteralMatchConditionWithDifferentActions(self):
    expected_files = ["auth.log"]
    non_expected_files = ["dpkg.log", "dpkg_false.log"]

    match = flows_pb2.FileFinderContentsLiteralMatchCondition(
        literal=b"session opened for user dearjohn",
    )
    literal_condition = flows_pb2.FileFinderCondition(
        condition_type=flows_pb2.FileFinderCondition.Type.CONTENTS_LITERAL_MATCH,
        contents_literal_match=match,
    )

    for action in self.CONDITION_TESTS_ACTIONS:
      results = self.RunFlowAndCheckResults(
          action=action,
          conditions=[literal_condition],
          expected_files=expected_files,
          non_expected_files=non_expected_files,
      )

      self.assertLen(results, 1)

  def testLiteralMatchConditionWithHexEncodedValue(self):
    match = flows_pb2.FileFinderContentsLiteralMatchCondition(
        literal=b"\x4D\x5A\x90",
    )
    literal_condition = flows_pb2.FileFinderCondition(
        condition_type=flows_pb2.FileFinderCondition.Type.CONTENTS_LITERAL_MATCH,
        contents_literal_match=match,
    )

    paths = [os.path.join(os.path.dirname(self.fixture_path), "win_hello.exe")]

    results = self.RunFlow(paths=paths, conditions=[literal_condition])

    # Expecting a match from win_hello.exe
    self.assertLen(results, 1)

  def testRegexMatchConditionWithDifferentActions(self):
    expected_files = ["auth.log"]
    non_expected_files = ["dpkg.log", "dpkg_false.log"]

    regex_condition = flows_pb2.FileFinderCondition(
        condition_type=(
            flows_pb2.FileFinderCondition.Type.CONTENTS_REGEX_MATCH
        ),
        contents_regex_match=(
            flows_pb2.FileFinderContentsRegexMatchCondition(
                regex=b"session opened for user .*?john",
            )
        ),
    )

    for action in self.CONDITION_TESTS_ACTIONS:
      results = self.RunFlowAndCheckResults(
          action=action,
          conditions=[regex_condition],
          expected_files=expected_files,
          non_expected_files=non_expected_files,
      )

      self.assertLen(results, 1)

  def testTwoRegexMatchConditionsWithDifferentActions1(self):
    expected_files = ["auth.log"]
    non_expected_files = ["dpkg.log", "dpkg_false.log"]

    regex_condition1 = flows_pb2.FileFinderCondition(
        condition_type=(
            flows_pb2.FileFinderCondition.Type.CONTENTS_REGEX_MATCH
        ),
        contents_regex_match=(
            flows_pb2.FileFinderContentsRegexMatchCondition(
                regex=b"session opened for user .*?john",
            )
        ),
    )
    regex_condition2 = flows_pb2.FileFinderCondition(
        condition_type=(
            flows_pb2.FileFinderCondition.Type.CONTENTS_REGEX_MATCH
        ),
        contents_regex_match=(
            flows_pb2.FileFinderContentsRegexMatchCondition(
                regex=b"format.*should",
            )
        ),
    )

    for action in self.CONDITION_TESTS_ACTIONS:
      results = self.RunFlowAndCheckResults(
          action=action,
          conditions=[regex_condition1, regex_condition2],
          expected_files=expected_files,
          non_expected_files=non_expected_files,
      )

      self.assertLen(results, 1)

  def testTwoRegexMatchConditionsWithDifferentActions2(self):
    expected_files = ["auth.log"]
    non_expected_files = ["dpkg.log", "dpkg_false.log"]

    regex_condition1 = flows_pb2.FileFinderCondition(
        condition_type=(
            flows_pb2.FileFinderCondition.Type.CONTENTS_REGEX_MATCH
        ),
        contents_regex_match=(
            flows_pb2.FileFinderContentsRegexMatchCondition(
                regex=b"session opened for user .*?john",
            )
        ),
    )
    regex_condition2 = flows_pb2.FileFinderCondition(
        condition_type=(
            flows_pb2.FileFinderCondition.Type.CONTENTS_REGEX_MATCH
        ),
        contents_regex_match=(
            flows_pb2.FileFinderContentsRegexMatchCondition(
                regex=b".*",
            )
        ),
    )

    for action in self.CONDITION_TESTS_ACTIONS:
      results = self.RunFlowAndCheckResults(
          action=action,
          conditions=[regex_condition1, regex_condition2],
          expected_files=expected_files,
          non_expected_files=non_expected_files,
      )

      self.assertLen(results, 1)

  def testSizeConditionWithDifferentActions(self):
    expected_files = ["dpkg.log", "dpkg_false.log"]
    non_expected_files = ["auth.log"]

    sizes = [
        os.stat(os.path.join(self.fixture_path, f)).st_size
        for f in expected_files
    ]

    size_condition = flows_pb2.FileFinderCondition(
        condition_type=flows_pb2.FileFinderCondition.Type.SIZE,
        size=flows_pb2.FileFinderSizeCondition(max_file_size=max(sizes) + 1),
    )

    for action in self.CONDITION_TESTS_ACTIONS:
      self.RunFlowAndCheckResults(
          action=action,
          conditions=[size_condition],
          expected_files=expected_files,
          non_expected_files=non_expected_files,
      )

  def testDownloadAndHashActionSizeLimitWithSkipPolicy(self):
    expected_files = ["dpkg.log", "dpkg_false.log"]
    skipped_files = ["auth.log"]
    sizes = [
        os.stat(os.path.join(self.fixture_path, f)).st_size
        for f in expected_files
    ]

    hash_action = flows_pb2.FileFinderAction(
        action_type=flows_pb2.FileFinderAction.Action.HASH,
        hash=flows_pb2.FileFinderHashActionOptions(
            max_size=max(sizes) + 1,
            oversized_file_policy=flows_pb2.FileFinderHashActionOptions.OversizedFilePolicy.SKIP,
        ),
    )
    download_action = flows_pb2.FileFinderAction(
        action_type=flows_pb2.FileFinderAction.Action.DOWNLOAD,
        download=flows_pb2.FileFinderDownloadActionOptions(
            max_size=max(sizes) + 1,
            oversized_file_policy=flows_pb2.FileFinderDownloadActionOptions.OversizedFilePolicy.SKIP,
        ),
    )

    for action in [hash_action, download_action]:
      self.RunFlowAndCheckResults(
          paths=[self.path],
          action=action,
          expected_files=expected_files,
          skipped_files=skipped_files,
      )

  def testDownloadAndHashActionSizeLimitWithHashTruncatedPolicy(self):
    image_path = os.path.join(self.base_path, "test_img.dd")
    # Read a bit more than a typical chunk (600 * 1024).
    expected_size = 750 * 1024
    with io.open(image_path, "rb") as fd:
      expected_data = fd.read(expected_size)

    d = hashlib.sha1()
    d.update(expected_data)
    expected_hash = d.digest()

    hash_action = flows_pb2.FileFinderAction(
        action_type=flows_pb2.FileFinderAction.Action.HASH,
        hash=flows_pb2.FileFinderHashActionOptions(
            max_size=expected_size,
            oversized_file_policy=flows_pb2.FileFinderHashActionOptions.OversizedFilePolicy.HASH_TRUNCATED,
        ),
    )
    download_action = flows_pb2.FileFinderAction(
        action_type=flows_pb2.FileFinderAction.Action.DOWNLOAD,
        download=flows_pb2.FileFinderDownloadActionOptions(
            max_size=expected_size,
            oversized_file_policy=flows_pb2.FileFinderDownloadActionOptions.OversizedFilePolicy.HASH_TRUNCATED,
        ),
    )

    for action in [hash_action, download_action]:
      self.RunFlow(paths=[image_path], action=action)

      with self.assertRaises(file_store.FileHasNoContentError):
        self._ReadTestFile(
            ["test_img.dd"], path_type=rdf_objects.PathInfo.PathType.OS
        )

      path_info = self._ReadTestPathInfo(
          ["test_img.dd"], path_type=rdf_objects.PathInfo.PathType.OS
      )
      self.assertEqual(path_info.hash_entry.sha1, expected_hash)
      self.assertEqual(path_info.hash_entry.num_bytes, expected_size)

  def testDownloadActionSizeLimitWithDownloadTruncatedPolicy(self):
    image_path = os.path.join(self.base_path, "test_img.dd")
    # Read a bit more than a typical chunk (600 * 1024).
    expected_size = 750 * 1024

    action = flows_pb2.FileFinderAction(
        action_type=flows_pb2.FileFinderAction.Action.DOWNLOAD,
        download=flows_pb2.FileFinderDownloadActionOptions(
            max_size=expected_size,
            oversized_file_policy=flows_pb2.FileFinderDownloadActionOptions.OversizedFilePolicy.DOWNLOAD_TRUNCATED,
        ),
    )

    self.RunFlow(paths=[image_path], action=action)
    with io.open(image_path, "rb") as fd:
      expected_data = fd.read(expected_size)

    d = hashlib.sha256()
    d.update(expected_data)
    expected_hash = d.digest()

    data = self._ReadTestFile(
        ["test_img.dd"], path_type=rdf_objects.PathInfo.PathType.OS
    )
    self.assertEqual(data, expected_data)

    path_info = self._ReadTestPathInfo(
        ["test_img.dd"], path_type=rdf_objects.PathInfo.PathType.OS
    )
    self.assertEqual(path_info.hash_entry.num_bytes, expected_size)
    self.assertEqual(path_info.hash_entry.sha256, expected_hash)

  def testDownloadActionWithMultipleAttemptsWithMultipleSizeLimits(self):
    total_num_chunks = 10
    total_size = (
        total_num_chunks * uploading.TransferStoreUploader.DEFAULT_CHUNK_SIZE
    )

    path = os.path.join(self.temp_dir, "test_big.txt")
    with io.open(path, "wb") as fd:
      for i in range(total_num_chunks):
        fd.write(
            struct.pack("b", i)
            * uploading.TransferStoreUploader.DEFAULT_CHUNK_SIZE
        )

    da = flows_pb2.FileFinderDownloadActionOptions

    # Read a truncated version of the file. This tests against a bug in
    # MultiGetFileLogic when first N chunks of the file were already
    # fetched during a previous MultiGetFileLogic run, and as a consequence
    # the file was considered fully fetched, even if the max_file_size value
    # of the current run was much bigger than the size of the previously
    # fetched file.
    action = flows_pb2.FileFinderAction(
        action_type=flows_pb2.FileFinderAction.Action.DOWNLOAD,
        download=flows_pb2.FileFinderDownloadActionOptions(
            max_size=2 * uploading.TransferStoreUploader.DEFAULT_CHUNK_SIZE,
            oversized_file_policy=da.OversizedFilePolicy.DOWNLOAD_TRUNCATED,
        ),
    )
    self.RunFlow(paths=[path], action=action)

    action = flows_pb2.FileFinderAction(
        action_type=flows_pb2.FileFinderAction.Action.DOWNLOAD,
        download=flows_pb2.FileFinderDownloadActionOptions(
            max_size=total_size,
            oversized_file_policy=da.OversizedFilePolicy.DOWNLOAD_TRUNCATED,
        ),
    )
    self.RunFlow(paths=[path], action=action)

    # Check that the first FileFinder run that downloaded a smaller version
    # of the file, hasn't influenced the next runs.
    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS, path=path
    )
    client_path = db.ClientPath.FromPathSpec(self.client_id, pathspec)
    fd = file_store.OpenFile(client_path)
    self.assertEqual(fd.size, total_size)

  def testSizeAndRegexConditionsWithDifferentActions(self):
    files_over_size_limit = ["auth.log"]
    filtered_files = ["dpkg.log", "dpkg_false.log"]
    expected_files = []
    non_expected_files = files_over_size_limit + filtered_files

    sizes = [
        os.stat(os.path.join(self.fixture_path, f)).st_size
        for f in files_over_size_limit
    ]

    size_condition = flows_pb2.FileFinderCondition(
        condition_type=flows_pb2.FileFinderCondition.Type.SIZE,
        size=flows_pb2.FileFinderSizeCondition(max_file_size=min(sizes) - 1),
    )

    regex_condition = flows_pb2.FileFinderCondition(
        condition_type=(
            flows_pb2.FileFinderCondition.Type.CONTENTS_REGEX_MATCH
        ),
        contents_regex_match=flows_pb2.FileFinderContentsRegexMatchCondition(
            regex=b"session opened for user .*?john",
        ),
    )

    for action in self.CONDITION_TESTS_ACTIONS:
      self.RunFlowAndCheckResults(
          action=action,
          conditions=[size_condition, regex_condition],
          expected_files=expected_files,
          non_expected_files=non_expected_files,
      )

    # Check that order of conditions doesn't influence results
    for action in self.CONDITION_TESTS_ACTIONS:
      self.RunFlowAndCheckResults(
          action=action,
          conditions=[regex_condition, size_condition],
          expected_files=expected_files,
          non_expected_files=non_expected_files,
      )

  def testModificationTimeConditionWithDifferentActions(self):
    expected_files = ["dpkg.log", "dpkg_false.log"]
    non_expected_files = ["auth.log"]
    change_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1444444440)

    with temp.AutoTempDirPath(remove_non_empty=True) as tempdir:
      os.mkdir(os.path.join(tempdir, "searching"))
      for fname in expected_files + non_expected_files:
        shutil.copyfile(
            os.path.join(self.fixture_path, fname),
            os.path.join(tempdir, "searching", fname),
        )

      # TODO - the complexity of these tests and their reliance on
      # shared state is horrible. All these tests should be rewritten.
      self.base_path = tempdir
      self.fixture_path = os.path.join(self.base_path, "searching")

      os.utime(
          os.path.join(self.fixture_path, "dpkg.log"),
          times=(
              change_time.AsSecondsSinceEpoch() + 1,
              change_time.AsSecondsSinceEpoch() + 1,
          ),
      )
      os.utime(
          os.path.join(self.fixture_path, "dpkg_false.log"),
          times=(
              change_time.AsSecondsSinceEpoch() + 2,
              change_time.AsSecondsSinceEpoch() + 2,
          ),
      )
      os.utime(
          os.path.join(self.fixture_path, "auth.log"),
          times=(
              change_time.AsSecondsSinceEpoch() - 1,
              change_time.AsSecondsSinceEpoch() - 1,
          ),
      )

      modification_time_condition = flows_pb2.FileFinderCondition(
          condition_type=flows_pb2.FileFinderCondition.Type.MODIFICATION_TIME,
          modification_time=flows_pb2.FileFinderModificationTimeCondition(
              min_last_modified_time=change_time.AsMicrosecondsSinceEpoch()
          ),
      )

      for action in self.CONDITION_TESTS_ACTIONS:
        with self.subTest(action):
          self.RunFlowAndCheckResults(
              paths=[os.path.join(self.fixture_path, "*.log")],
              action=action,
              conditions=[modification_time_condition],
              expected_files=expected_files,
              non_expected_files=non_expected_files,
          )

  def testAccessTimeConditionWithDifferentActions(self):
    expected_files = ["dpkg.log", "dpkg_false.log"]
    non_expected_files = ["auth.log"]
    change_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1444444440)

    with temp.AutoTempDirPath(remove_non_empty=True) as tempdir:
      os.mkdir(os.path.join(tempdir, "searching"))
      for fname in expected_files + non_expected_files:
        shutil.copyfile(
            os.path.join(self.fixture_path, fname),
            os.path.join(tempdir, "searching", fname),
        )

      # TODO - the complexity of these tests and their reliance on
      # shared state is horrible. All these tests should be rewritten.
      self.base_path = tempdir
      self.fixture_path = os.path.join(self.base_path, "searching")

      os.utime(
          os.path.join(self.fixture_path, "dpkg.log"),
          times=(
              change_time.AsSecondsSinceEpoch() + 1,
              change_time.AsSecondsSinceEpoch() + 1,
          ),
      )
      os.utime(
          os.path.join(self.fixture_path, "dpkg_false.log"),
          times=(
              change_time.AsSecondsSinceEpoch() + 2,
              change_time.AsSecondsSinceEpoch() + 2,
          ),
      )
      os.utime(
          os.path.join(self.fixture_path, "auth.log"),
          times=(
              change_time.AsSecondsSinceEpoch() - 1,
              change_time.AsSecondsSinceEpoch() - 1,
          ),
      )

      modification_time_condition = flows_pb2.FileFinderCondition(
          condition_type=flows_pb2.FileFinderCondition.Type.ACCESS_TIME,
          access_time=flows_pb2.FileFinderAccessTimeCondition(
              min_last_access_time=change_time.AsMicrosecondsSinceEpoch()
          ),
      )

      for action in self.CONDITION_TESTS_ACTIONS:
        with self.subTest(action):
          self.RunFlowAndCheckResults(
              paths=[os.path.join(self.fixture_path, "*.log")],
              action=action,
              conditions=[modification_time_condition],
              expected_files=expected_files,
              non_expected_files=non_expected_files,
          )

  def testInodeChangeTimeConditionWithDifferentActions(self):
    expected_files = ["dpkg.log", "dpkg_false.log"]
    non_expected_files = ["auth.log"]

    with temp.AutoTempDirPath(remove_non_empty=True) as tempdir:
      os.mkdir(os.path.join(tempdir, "searching"))
      for fname in non_expected_files + expected_files:
        time.sleep(0.1)
        shutil.copyfile(
            os.path.join(self.fixture_path, fname),
            os.path.join(tempdir, "searching", fname),
        )

      # In the loop above auth.log is written first, so if we take a timestamp
      # that's right after its inode change time, it should filter out auth.log,
      # but keep dpkg.log and dpkg_false.log, as they would match the condition.
      auth_log_ctime_ns = int(
          os.stat(os.path.join(tempdir, "searching", "auth.log")).st_ctime_ns
          * 1e-3
      )
      change_time = rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
          auth_log_ctime_ns + 1
      )

      # TODO - the complexity of these tests and their reliance on
      # shared state is horrible. All these tests should be rewritten.
      self.base_path = tempdir
      self.fixture_path = os.path.join(self.base_path, "searching")

      inode_change_time_condition = flows_pb2.FileFinderCondition(
          condition_type=flows_pb2.FileFinderCondition.Type.INODE_CHANGE_TIME,
          inode_change_time=flows_pb2.FileFinderInodeChangeTimeCondition(
              min_last_inode_change_time=change_time.AsMicrosecondsSinceEpoch()
          ),
      )

      for action in self.CONDITION_TESTS_ACTIONS:
        with self.subTest(action):
          self.RunFlowAndCheckResults(
              paths=[os.path.join(self.fixture_path, "*.log")],
              action=action,
              conditions=[inode_change_time_condition],
              expected_files=expected_files,
              non_expected_files=non_expected_files,
          )

  def _RunTSKFileFinder(self, paths):
    image_path = os.path.join(self.base_path, "ntfs_img.dd")
    with mock.patch.object(
        vfs,
        "_VFS_VIRTUALROOTS",
        {
            rdf_paths.PathSpec.PathType.TSK: rdf_paths.PathSpec(
                path=image_path, pathtype="OS", offset=63 * 512
            )
        },
    ):

      action = flows_pb2.FileFinderAction.Action.DOWNLOAD
      with test_lib.SuppressLogs():
        flow_test_lib.StartAndRunFlow(
            file_finder.FileFinder,
            client_mock=action_mocks.ClientFileFinderWithVFS(),
            client_id=self.client_id,
            flow_args=flows_pb2.FileFinderArgs(
                paths=paths,
                pathtype=rdf_paths.PathSpec.PathType.TSK,
                action=flows_pb2.FileFinderAction(action_type=action),
            ),
            creator=self.test_username,
        )

  def _ListTestChildPathInfos(
      self,
      path_components,
      path_type=rdf_objects.PathInfo.PathType.TSK,
  ):
    components = self.base_path.strip("/").split("/")
    components += path_components
    return data_store.REL_DB.ListChildPathInfos(
        self.client_id, path_type, tuple(components)
    )

  def _ReadTestPathInfo(
      self,
      path_components,
      path_type=rdf_objects.PathInfo.PathType.TSK,
  ) -> objects_pb2.PathInfo:
    components = self.base_path.strip("/").split("/")
    components += path_components
    return data_store.REL_DB.ReadPathInfo(
        self.client_id, path_type, tuple(components)
    )

  def _ReadTestFile(
      self,
      path_components,
      path_type=rdf_objects.PathInfo.PathType.TSK,
  ):
    components = self.base_path.strip("/").split("/")
    components += path_components

    fd = file_store.OpenFile(
        db.ClientPath(self.client_id, path_type, components=tuple(components))
    )
    return fd.read(10000000)

  def testEmptyPathListDoesNothing(self):
    flow_test_lib.StartAndRunFlow(
        file_finder.FileFinder,
        self.client_mock,
        client_id=self.client_id,
        flow_args=flows_pb2.FileFinderArgs(
            paths=[],
            pathtype=jobs_pb2.PathSpec.PathType.OS,
        ),
        creator=self.test_username,
    )

  def testUseExternalStores(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as tempdir:
      path = os.path.join(tempdir, "foo")
      with io.open(path, "w") as fd:
        fd.write("some content")

      paths = [path]
      action = flows_pb2.FileFinderAction(
          action_type=flows_pb2.FileFinderAction.Action.DOWNLOAD
      )

      action.download.use_external_stores = False

      with mock.patch.object(file_store.EXTERNAL_FILE_STORE, "AddFiles") as efs:
        flow_id = flow_test_lib.StartAndRunFlow(
            file_finder.FileFinder,
            self.client_mock,
            client_id=self.client_id,
            flow_args=flows_pb2.FileFinderArgs(
                paths=paths,
                pathtype=jobs_pb2.PathSpec.PathType.OS,
                action=action,
                process_non_regular_files=True,
            ),
            creator=self.test_username,
        )

      results = flow_test_lib.GetUnpackedFlowResults(
          client_id=self.client_id,
          flow_id=flow_id,
          result_type=flows_pb2.FileFinderResult,
      )

      self.assertLen(results, 1)

      self.assertEqual(efs.call_count, 0)

      # Change the file or the file finder will see that it was downloaded
      # already and skip it.
      with io.open(path, "w") as fd:
        fd.write("some other content")

      action.download.use_external_stores = True

      with mock.patch.object(file_store.EXTERNAL_FILE_STORE, "AddFiles") as efs:
        flow_id = flow_test_lib.StartAndRunFlow(
            file_finder.FileFinder,
            self.client_mock,
            client_id=self.client_id,
            flow_args=flows_pb2.FileFinderArgs(
                paths=paths,
                pathtype=jobs_pb2.PathSpec.PathType.OS,
                action=action,
                process_non_regular_files=True,
            ),
            creator=self.test_username,
        )

      results = flow_test_lib.GetUnpackedFlowResults(
          client_id=self.client_id,
          flow_id=flow_id,
          result_type=flows_pb2.FileFinderResult,
      )
      self.assertLen(results, 1)

      self.assertEqual(efs.call_count, 1)

  def testFollowLinks(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as tempdir:
      path = os.path.join(tempdir, "foo")
      lnk_path = os.path.join(tempdir, "foo_lnk")
      path_glob = os.path.join(tempdir, "*")
      with io.open(path, "w") as fd:
        fd.write("some content")

      os.symlink(path, lnk_path)

      results = self.RunFlow(
          action=flows_pb2.FileFinderAction(
              action_type=flows_pb2.FileFinderAction.Action.STAT,
              stat=flows_pb2.FileFinderStatActionOptions(resolve_links=False),
          ),
          paths=[path_glob],
      )

      self.assertLen(results, 2)

      lnk_stats = [
          r.stat_entry
          for r in results
          if stat.S_ISLNK(int(r.stat_entry.st_mode))
      ]
      self.assertNotEmpty(lnk_stats, "No stat entry containing a link found.")

      self.assertNotEqual(
          results[0].stat_entry.st_ino, results[1].stat_entry.st_ino
      )

      results = self.RunFlow(
          action=flows_pb2.FileFinderAction(
              action_type=flows_pb2.FileFinderAction.Action.STAT,
              stat=flows_pb2.FileFinderStatActionOptions(resolve_links=True),
          ),
          paths=[path_glob],
      )

      self.assertLen(results, 2)

      lnk_stats = [
          r.stat_entry
          for r in results
          if stat.S_ISLNK(int(r.stat_entry.st_mode))
      ]
      self.assertEmpty(lnk_stats, "Stat entry containing a link found.")

      self.assertEqual(
          results[0].stat_entry.st_ino, results[1].stat_entry.st_ino
      )

  def testLinksAndContent(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as tempdir:
      # This sets up a structure as follows:
      # <dir>  tempdir/dir
      # <file> tempdir/foo
      # <lnk>  tempdir/foo_lnk
      # <lnk>  tempdir/dir_lnk

      # foo_lnk is a symbolic link to foo (a file).
      # dir_lnk is a symbolic link to dir (a directory).

      path = os.path.join(tempdir, "foo")
      with io.open(path, "w") as fd:
        fd.write("some content")

      dir_path = os.path.join(tempdir, "dir")
      os.mkdir(dir_path)

      lnk_path = os.path.join(tempdir, "foo_lnk")
      os.symlink(path, lnk_path)

      dir_lnk_path = os.path.join(tempdir, "dir_lnk")
      os.symlink(dir_path, dir_lnk_path)

      path_glob = os.path.join(tempdir, "**3")
      condition = flows_pb2.FileFinderCondition(
          condition_type=flows_pb2.FileFinderCondition.Type.CONTENTS_LITERAL_MATCH,
          contents_literal_match=flows_pb2.FileFinderContentsLiteralMatchCondition(
              literal=b"some"
          ),
      )
      results = self.RunFlow(
          action=flows_pb2.FileFinderAction(
              action_type=flows_pb2.FileFinderAction.Action.STAT,
              stat=flows_pb2.FileFinderStatActionOptions(resolve_links=False),
          ),
          conditions=[condition],
          paths=[path_glob],
      )

      self.assertLen(results, 2)

      results = self.RunFlow(
          action=flows_pb2.FileFinderAction(
              action_type=flows_pb2.FileFinderAction.Action.STAT,
              stat=flows_pb2.FileFinderStatActionOptions(resolve_links=True),
          ),
          conditions=[condition],
          paths=[path_glob],
      )

      self.assertLen(results, 2)


class TestClientFileFinderFlow(flow_test_lib.FlowTestsBaseclass):
  """Test the ClientFileFinder flow."""

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)

  def _RunCFF(self, paths, action, conditions=None, check_flow_errors=True):
    flow_id = flow_test_lib.StartAndRunFlow(
        file_finder.ClientFileFinder,
        action_mocks.ClientFileFinderClientMock(),
        client_id=self.client_id,
        flow_args=flows_pb2.FileFinderArgs(
            paths=paths,
            pathtype=jobs_pb2.PathSpec.PathType.OS,
            action=flows_pb2.FileFinderAction(action_type=action),
            conditions=conditions,
            process_non_regular_files=True,
        ),
        creator=self.test_username,
        check_flow_errors=check_flow_errors,
    )

    results = flow_test_lib.GetUnpackedFlowResults(
        client_id=self.client_id,
        flow_id=flow_id,
        result_type=flows_pb2.FileFinderResult,
    )
    return results, flow_id

  def testClientFileFinder(self):
    paths = [os.path.join(self.base_path, "{**,.}/*.plist")]
    action = flows_pb2.FileFinderAction.Action.STAT
    results, _ = self._RunCFF(paths, action)

    self.assertLen(results, 5)
    relpaths = [
        os.path.relpath(p.stat_entry.pathspec.path, self.base_path)
        for p in results
    ]
    self.assertCountEqual(
        relpaths,
        [
            "History.plist",
            "History.xml.plist",
            "test.plist",
            "parser_test/com.google.code.grr.plist",
            "parser_test/InstallHistory.plist",
        ],
    )

  @mock.patch.object(
      file_finder.ClientFileFinder, "BLOB_CHECK_DELAY", rdfvalue.Duration(0)
  )
  def testErrorsWhenDownloadingFileAndNotReceivingBlobs(self):
    paths = [os.path.join(self.base_path, "test.plist")]
    action = flows_pb2.FileFinderAction(
        action_type=flows_pb2.FileFinderAction.Action.DOWNLOAD
    )

    # Make sure BlobHandler doesn't accept any incoming blobs. Thus
    # ClientFileFinder will timeout waiting for one.
    with mock.patch.object(transfer.BlobHandler, "ProcessMessages"):
      flow_id = flow_test_lib.StartFlow(
          file_finder.ClientFileFinder,
          client_id=self.client_id,
          flow_args=flows_pb2.FileFinderArgs(
              paths=paths,
              pathtype=jobs_pb2.PathSpec.PathType.OS,
              action=action,
          ),
          creator=self.test_username,
      )
      with self.assertRaisesRegex(
          RuntimeError, "Could not find one of referenced blobs"
      ):
        flow_test_lib.RunFlow(
            client_id=self.client_id,
            flow_id=flow_id,
            client_mock=action_mocks.ClientFileFinderClientMock(),
        )

    store_any: any_pb2.Any = flow_test_lib.GetFlowStore(self.client_id, flow_id)
    store = flows_pb2.FileFinderStore()
    store_any.Unpack(store)
    # Check that the flow has actually reached the maximum number of checks.
    self.assertEqual(
        store.num_blob_waits,
        file_finder.ClientFileFinder.MAX_BLOB_CHECKS + 1,
    )

  def testUseExternalStores(self):
    paths = [os.path.join(self.base_path, "test.plist")]
    action = flows_pb2.FileFinderAction(
        action_type=flows_pb2.FileFinderAction.Action.DOWNLOAD
    )

    action.download.use_external_stores = False

    with mock.patch.object(file_store.EXTERNAL_FILE_STORE, "AddFiles") as efs:
      flow_id = flow_test_lib.StartAndRunFlow(
          file_finder.ClientFileFinder,
          action_mocks.ClientFileFinderClientMock(),
          client_id=self.client_id,
          flow_args=flows_pb2.FileFinderArgs(
              paths=paths,
              pathtype=jobs_pb2.PathSpec.PathType.OS,
              action=action,
              process_non_regular_files=True,
          ),
          creator=self.test_username,
      )

    results = flow_test_lib.GetUnpackedFlowResults(
        client_id=self.client_id,
        flow_id=flow_id,
        result_type=flows_pb2.FileFinderResult,
    )
    self.assertLen(results, 1)

    self.assertEqual(efs.call_count, 0)

    action.download.use_external_stores = True

    with mock.patch.object(file_store.EXTERNAL_FILE_STORE, "AddFiles") as efs:
      flow_id = flow_test_lib.StartAndRunFlow(
          file_finder.ClientFileFinder,
          action_mocks.ClientFileFinderClientMock(),
          client_id=self.client_id,
          flow_args=flows_pb2.FileFinderArgs(
              paths=paths,
              pathtype=jobs_pb2.PathSpec.PathType.OS,
              action=action,
              process_non_regular_files=True,
          ),
          creator=self.test_username,
      )

    results = flow_test_lib.GetUnpackedFlowResults(
        client_id=self.client_id,
        flow_id=flow_id,
        result_type=flows_pb2.FileFinderResult,
    )
    self.assertLen(results, 1)

    self.assertEqual(efs.call_count, 1)

  def _VerifyDownloadedFiles(self, results):
    for r in results:
      original_path = r.stat_entry.pathspec.path
      fd = file_store.OpenFile(
          db.ClientPath(
              self.client_id,
              rdf_objects.PathInfo.PathType.OS,
              components=original_path.strip("/").split("/"),
          )
      )

      with io.open(original_path, "rb") as orig_fd:
        orig_content = orig_fd.read()

      orig_sha256 = hashlib.sha256(orig_content).digest()

      self.assertEqual(fd.read(), orig_content)
      self.assertEqual(r.hash_entry.sha256, orig_sha256)

  def testFileWithMoreThanOneChunk(self):
    path = os.path.join(self.base_path, "History.plist")
    s = os.stat(path).st_size
    action = flows_pb2.FileFinderAction(
        action_type=flows_pb2.FileFinderAction.Action.DOWNLOAD,
        download=flows_pb2.FileFinderDownloadActionOptions(chunk_size=s // 4),
    )

    flow_id = flow_test_lib.StartAndRunFlow(
        file_finder.ClientFileFinder,
        action_mocks.ClientFileFinderClientMock(),
        client_id=self.client_id,
        flow_args=flows_pb2.FileFinderArgs(
            paths=[path],
            pathtype=jobs_pb2.PathSpec.PathType.OS,
            action=action,
            process_non_regular_files=True,
        ),
        creator=self.test_username,
    )

    results = flow_test_lib.GetUnpackedFlowResults(
        client_id=self.client_id,
        flow_id=flow_id,
        result_type=flows_pb2.FileFinderResult,
    )

    self.assertLen(results, 1)

    self._VerifyDownloadedFiles(results)

  def testFileWithExactlyThanOneChunk(self):
    path = os.path.join(self.base_path, "History.plist")
    s = os.stat(path).st_size
    action = flows_pb2.FileFinderAction(
        action_type=flows_pb2.FileFinderAction.Action.DOWNLOAD,
        download=flows_pb2.FileFinderDownloadActionOptions(chunk_size=s * 2),
    )

    flow_id = flow_test_lib.StartAndRunFlow(
        file_finder.ClientFileFinder,
        action_mocks.ClientFileFinderClientMock(),
        client_id=self.client_id,
        flow_args=flows_pb2.FileFinderArgs(
            paths=[path],
            pathtype=jobs_pb2.PathSpec.PathType.OS,
            action=action,
            process_non_regular_files=True,
        ),
        creator=self.test_username,
    )

    results = flow_test_lib.GetUnpackedFlowResults(
        client_id=self.client_id,
        flow_id=flow_id,
        result_type=flows_pb2.FileFinderResult,
    )

    self.assertLen(results, 1)

    self._VerifyDownloadedFiles(results)

  def testClientFileFinderDownload(self):
    paths = [os.path.join(self.base_path, "{**,.}/*.plist")]
    action = flows_pb2.FileFinderAction.Action.DOWNLOAD
    results, _ = self._RunCFF(paths, action)

    self.assertLen(results, 5)
    relpaths = [
        os.path.relpath(p.stat_entry.pathspec.path, self.base_path)
        for p in results
    ]
    self.assertCountEqual(
        relpaths,
        [
            "History.plist",
            "History.xml.plist",
            "test.plist",
            "parser_test/com.google.code.grr.plist",
            "parser_test/InstallHistory.plist",
        ],
    )

    self._VerifyDownloadedFiles(results)

  def testClientFileFinderPathCasing(self):
    paths = [
        os.path.join(self.base_path, "PARSER_TEST/*.plist"),
        os.path.join(self.base_path, "history.plist"),
        os.path.join(self.base_path, "InstallHistory.plist"),
    ]
    action = flows_pb2.FileFinderAction.Action.STAT
    results, _ = self._RunCFF(paths, action)
    self.assertLen(results, 3)
    relpaths = [
        os.path.relpath(p.stat_entry.pathspec.path, self.base_path)
        for p in results
    ]
    self.assertCountEqual(
        relpaths,
        [
            "History.plist",
            "parser_test/InstallHistory.plist",
            "parser_test/com.google.code.grr.plist",
        ],
    )

  def _SetupUnicodePath(self, path):
    try:
      dir_path = os.path.join(path, "厨房")
      os.mkdir(dir_path)
    except UnicodeEncodeError:
      self.skipTest("Test needs a unicode capable file system.")

    file_path = os.path.join(dir_path, "卫浴洁.txt")

    with io.open(file_path, "w") as f:
      f.write("hello world!")

  def testClientFileFinderUnicodeRegex(self):
    self._SetupUnicodePath(self.temp_dir)
    paths = [
        os.path.join(self.temp_dir, "*"),
        os.path.join(self.temp_dir, "厨房/*.txt"),
    ]
    action = flows_pb2.FileFinderAction.Action.STAT
    results, _ = self._RunCFF(paths, action)
    self.assertLen(results, 2)
    relpaths = [
        os.path.relpath(p.stat_entry.pathspec.path, self.temp_dir)
        for p in results
    ]
    self.assertCountEqual(relpaths, ["厨房", "厨房/卫浴洁.txt"])

  def testClientFileFinderUnicodeLiteral(self):
    self._SetupUnicodePath(self.temp_dir)

    paths = [os.path.join(self.temp_dir, "厨房/卫浴洁.txt")]
    action = flows_pb2.FileFinderAction.Action.STAT
    results, _ = self._RunCFF(paths, action)
    self.assertLen(results, 1)
    relpaths = [
        os.path.relpath(p.stat_entry.pathspec.path, self.temp_dir)
        for p in results
    ]
    self.assertCountEqual(relpaths, ["厨房/卫浴洁.txt"])

  def testPathInterpolationOsUserFqdn(self):
    bar = knowledge_base_pb2.User(username="bar")
    baz = knowledge_base_pb2.User(username="baz")
    self.client_id = self.SetupClient(
        0, system="foo", fqdn="norf", users=[bar, baz]
    )

    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      self._Touch(os.path.join(temp_dirpath, "foo", "bar"))
      self._Touch(os.path.join(temp_dirpath, "foo", "baz"))
      self._Touch(os.path.join(temp_dirpath, "foo", "quux"))
      self._Touch(os.path.join(temp_dirpath, "thud", "norf", "plugh"))
      self._Touch(os.path.join(temp_dirpath, "thud", "norf", "blargh"))

      paths = [
          os.path.join(temp_dirpath, "%%os%%", "%%users.username%%"),
          os.path.join(temp_dirpath, "thud", "%%fqdn%%", "plugh"),
      ]

      action = flows_pb2.FileFinderAction.Action.STAT
      results, flow_id = self._RunCFF(paths, action)

      result_paths = [result.stat_entry.pathspec.path for result in results]
      self.assertCountEqual(
          result_paths,
          [
              os.path.join(temp_dirpath, "foo", "bar"),
              os.path.join(temp_dirpath, "foo", "baz"),
              os.path.join(temp_dirpath, "thud", "norf", "plugh"),
          ],
      )

    # Also check that the argument protobuf still has the original values.
    flow_obj = flow_test_lib.GetFlowObj(self.client_id, flow_id)
    args = flow_obj.args
    self.assertCountEqual(args.paths, paths)

  def testPathGlobWithStarStar(self):
    self.client_id = self.SetupClient(0, system="foo")

    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      # Test case insensitive
      self._Touch(os.path.join(temp_dirpath, "1", "2", "fOo2"))
      self._Touch(os.path.join(temp_dirpath, "1", "2", "foo2"))
      self._Touch(os.path.join(temp_dirpath, "1", "2", "3", "fOo3"))
      self._Touch(os.path.join(temp_dirpath, "1", "2", "3", "foo3"))
      self._Touch(os.path.join(temp_dirpath, "1", "2", "3", "4", "fOo4"))
      self._Touch(os.path.join(temp_dirpath, "1", "2", "3", "4", "foo4"))
      # Test filename and directory with spaces
      self._Touch(os.path.join(temp_dirpath, "1", "2 space", "foo something"))
      # Too deep for default recursion depth
      self._Touch(
          os.path.join(temp_dirpath, "1", "2", "3", "4", "5", "foo deep")
      )

      # Get the foos using default of 3 directory levels.
      paths = [os.path.join(temp_dirpath, "1/**/foo*")]

      action = flows_pb2.FileFinderAction.Action.STAT
      results, flow_id = self._RunCFF(paths, action)

      result_paths = [result.stat_entry.pathspec.path for result in results]
      self.assertCountEqual(
          result_paths,
          [
              os.path.join(temp_dirpath, "1", "2", "fOo2"),
              os.path.join(temp_dirpath, "1", "2", "foo2"),
              os.path.join(temp_dirpath, "1", "2", "3", "fOo3"),
              os.path.join(temp_dirpath, "1", "2", "3", "foo3"),
              os.path.join(temp_dirpath, "1", "2", "3", "4", "fOo4"),
              os.path.join(temp_dirpath, "1", "2", "3", "4", "foo4"),
              os.path.join(temp_dirpath, "1", "2 space", "foo something"),
          ],
      )

    # Also check that the argument protobuf still has the original values.
    flow_obj = flow_test_lib.GetFlowObj(self.client_id, flow_id)
    args = flow_obj.args
    self.assertCountEqual(args.paths, paths)

  def testPathGlobFailsWithMultipleStarStar(self):
    self.client_id = self.SetupClient(0, system="foo")

    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      # Using ** two times in the same expression is not supported.
      paths = [os.path.join(temp_dirpath, "1/**/**/foo")]

      action = flows_pb2.FileFinderAction.Action.STAT
      results, flow_id = self._RunCFF(paths, action, check_flow_errors=False)

      flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
      self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.ERROR)
      self.assertIn(
          "path cannot have more than one recursive component",
          flow_obj.error_message,
      )
      self.assertEmpty(results)

  def testPathGlobFailsWithInexistentAttribute(self):
    self.client_id = self.SetupClient(0, system="foo")

    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      paths = [os.path.join(temp_dirpath, "%%weird_illegal_attribute%%")]

      action = flows_pb2.FileFinderAction.Action.STAT
      results, flow_id = self._RunCFF(paths, action, check_flow_errors=False)

      flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
      self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.ERROR)
      self.assertIn(
          "`%%weird_illegal_attribute%%` does not exist", flow_obj.error_message
      )
      self.assertEmpty(results)

  def testPathGlobWithStarStarBiggerDepth(self):
    self.client_id = self.SetupClient(0, system="foo")

    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      # Test case insensitive
      self._Touch(os.path.join(temp_dirpath, "1", "2", "foo2"))
      self._Touch(os.path.join(temp_dirpath, "1", "2", "3", "foo3"))
      self._Touch(os.path.join(temp_dirpath, "1", "2", "3", "4", "foo4"))
      self._Touch(os.path.join(temp_dirpath, "1", "2", "3", "4", "5", "foo5"))

      # Get the foos using longer depth (default is 3).
      paths = [os.path.join(temp_dirpath, "1/**4/foo*")]

      action = flows_pb2.FileFinderAction.Action.STAT
      results, flow_id = self._RunCFF(paths, action)

      result_paths = [result.stat_entry.pathspec.path for result in results]
      self.assertCountEqual(
          result_paths,
          [
              os.path.join(temp_dirpath, "1", "2", "foo2"),
              os.path.join(temp_dirpath, "1", "2", "3", "foo3"),
              os.path.join(temp_dirpath, "1", "2", "3", "4", "foo4"),
              os.path.join(temp_dirpath, "1", "2", "3", "4", "5", "foo5"),
          ],
      )

    # Also check that the argument protobuf still has the original values.
    flow_obj = flow_test_lib.GetFlowObj(self.client_id, flow_id)
    args = flow_obj.args
    self.assertCountEqual(args.paths, paths)

  def testPathGlobWithStarStarShorterDepth(self):
    self.client_id = self.SetupClient(0, system="foo")

    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      # Test case insensitive
      self._Touch(os.path.join(temp_dirpath, "1", "2", "foo2"))
      self._Touch(os.path.join(temp_dirpath, "1", "2", "3", "foo3"))
      self._Touch(os.path.join(temp_dirpath, "1", "2", "3", "4", "foo4"))

      # Get the foos using SHORTER depth.
      paths = [os.path.join(temp_dirpath, "1/**1/foo*")]

      action = flows_pb2.FileFinderAction.Action.STAT
      results, flow_id = self._RunCFF(paths, action)

      result_paths = [result.stat_entry.pathspec.path for result in results]
      self.assertCountEqual(
          result_paths,
          [
              os.path.join(temp_dirpath, "1", "2", "foo2"),
          ],
      )

    # Also check that the argument protobuf still has the original values.
    flow_obj = flow_test_lib.GetFlowObj(self.client_id, flow_id)
    args = flow_obj.args
    self.assertCountEqual(args.paths, paths)

  def testPathGlobWithTwoStars(self):
    self.client_id = self.SetupClient(0, system="foo")

    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      # Test case insensitive
      self._Touch(os.path.join(temp_dirpath, "1", "2", "foo2"))
      self._Touch(os.path.join(temp_dirpath, "1", "2", "3", "foo3"))
      self._Touch(os.path.join(temp_dirpath, "1", "2", "3", "fOo3"))
      self._Touch(os.path.join(temp_dirpath, "1", "2", "3", "4", "foo4"))

      # MUST have two dirs in between, case insensitive.
      paths = [os.path.join(temp_dirpath, "1/*/*/foo*")]

      action = flows_pb2.FileFinderAction.STAT
      results, flow_id = self._RunCFF(paths, action)

      result_paths = [result.stat_entry.pathspec.path for result in results]
      self.assertCountEqual(
          result_paths,
          [
              os.path.join(temp_dirpath, "1", "2", "3", "fOo3"),
              os.path.join(temp_dirpath, "1", "2", "3", "foo3"),
          ],
      )

    # Also check that the argument protobuf still has the original values.
    flow_obj = flow_test_lib.GetFlowObj(self.client_id, flow_id)
    args = flow_obj.args
    self.assertCountEqual(args.paths, paths)

  def testPathGlobGrouping(self):
    self.client_id = self.SetupClient(0, system="foo")

    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      # Test case insensitive
      self._Touch(os.path.join(temp_dirpath, "foo", "a"))
      self._Touch(os.path.join(temp_dirpath, "foo", "b"))
      self._Touch(os.path.join(temp_dirpath, "foo", "bb"))
      self._Touch(os.path.join(temp_dirpath, "foo", "c"))

      # Should catch either `a` or anything starting with `b`.
      paths = [os.path.join(temp_dirpath, "foo/{a,b*}")]

      action = flows_pb2.FileFinderAction.STAT
      results, _ = self._RunCFF(paths, action)

      result_paths = [result.stat_entry.pathspec.path for result in results]
      self.assertCountEqual(
          result_paths,
          [
              os.path.join(temp_dirpath, "foo", "a"),
              os.path.join(temp_dirpath, "foo", "b"),
              os.path.join(temp_dirpath, "foo", "bb"),
          ],
      )

  def testPathGlobUnicode(self):
    self.client_id = self.SetupClient(0, system="foo")

    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      # Test case insensitive
      self._Touch(os.path.join(temp_dirpath, "foo", "notfound.exe"))
      self._Touch(os.path.join(temp_dirpath, "foo", "a.txt"))
      self._Touch(os.path.join(temp_dirpath, "foo", "b.txt"))
      self._Touch(os.path.join(temp_dirpath, "foo", "这看起来很酷.txt"))

      # Should catch all files with .txt extension.
      paths = [os.path.join(temp_dirpath, "foo/*.txt")]

      action = flows_pb2.FileFinderAction.STAT
      results, _ = self._RunCFF(paths, action)

      result_paths = [result.stat_entry.pathspec.path for result in results]
      self.assertCountEqual(
          result_paths,
          [
              os.path.join(temp_dirpath, "foo", "a.txt"),
              os.path.join(temp_dirpath, "foo", "b.txt"),
              os.path.join(temp_dirpath, "foo", "这看起来很酷.txt"),
          ],
      )

  # TODO(hanuszczak): Similar function can be found in other modules. It should
  # be implemented once in the test library.
  def _Touch(self, filepath):
    dirpath = os.path.dirname(filepath)
    if not os.path.exists(dirpath):
      os.makedirs(dirpath)

    with io.open(filepath, "wb"):
      pass

  def testLinksAndContent(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as tempdir:
      # This sets up a structure as follows:
      # <dir>  tempdir/dir
      # <file> tempdir/foo
      # <lnk>  tempdir/foo_lnk
      # <lnk>  tempdir/dir_lnk

      # foo_lnk is a symbolic link to foo (a file).
      # dir_lnk is a symbolic link to dir (a directory).

      path = os.path.join(tempdir, "foo")
      with io.open(path, "w") as fd:
        fd.write("some content")

      dir_path = os.path.join(tempdir, "dir")
      os.mkdir(dir_path)

      lnk_path = os.path.join(tempdir, "foo_lnk")
      os.symlink(path, lnk_path)

      dir_lnk_path = os.path.join(tempdir, "dir_lnk")
      os.symlink(dir_path, dir_lnk_path)

      path_glob = os.path.join(tempdir, "**3")
      action = flows_pb2.FileFinderAction.Action.STAT
      condition = flows_pb2.FileFinderCondition(
          condition_type=flows_pb2.FileFinderCondition.Type.CONTENTS_LITERAL_MATCH,
          contents_literal_match=flows_pb2.FileFinderContentsLiteralMatchCondition(
              literal=b"some"
          ),
      )

      results, _ = self._RunCFF([path_glob], action, conditions=[condition])

      # ClientFileFinder follows links that point to regulat files by default,
      # hence 2 results: one for the link and one for the file.
      self.assertLen(results, 2)
      self.assertCountEqual(
          [
              results[0].stat_entry.pathspec.path,
              results[1].stat_entry.pathspec.path,
          ],
          [path, lnk_path],
      )

  def testInterpolationMissingAttributes(self):
    creator = db_test_utils.InitializeUser(data_store.REL_DB)
    client_id = db_test_utils.InitializeClient(data_store.REL_DB)

    # We need to write some dummy snapshot to ensure the knowledgebase is there.
    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.fqdn = "foobar.example.com"
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    flow_args = flows_pb2.FileFinderArgs(
        action=flows_pb2.FileFinderAction(
            action_type=flows_pb2.FileFinderAction.Action.STAT
        ),
        paths=["%%environ_path%%", "%%environ_temp%%"],
    )

    flow_id = flow_test_lib.StartFlow(
        file_finder.ClientFileFinder,
        creator=creator,
        client_id=client_id,
        flow_args=flow_args,
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.ERROR)

    log_entries = data_store.REL_DB.ReadFlowLogEntries(
        client_id=client_id, flow_id=flow_id, offset=0, count=1024
    )
    self.assertLen(log_entries, 2)
    self.assertIn("environ_path", log_entries[0].message)
    self.assertIn("environ_temp", log_entries[1].message)

  def testInterpolationUnknownAttributes(self):
    creator = db_test_utils.InitializeUser(data_store.REL_DB)
    client_id = db_test_utils.InitializeClient(data_store.REL_DB)

    # We need to write some dummy snapshot to ensure the knowledgebase is there.
    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.fqdn = "foobar.example.com"
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    flow_args = flows_pb2.FileFinderArgs(
        action=flows_pb2.FileFinderAction(
            action_type=flows_pb2.FileFinderAction.Action.STAT
        ),
        paths=["%%foo%%", "%%bar%%"],
    )

    flow_id = flow_test_lib.StartFlow(
        file_finder.ClientFileFinder,
        creator=creator,
        client_id=client_id,
        flow_args=flow_args,
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.ERROR)
    self.assertEqual("`%%foo%%` does not exist", flow_obj.error_message)

  def testSkipsGlobsWithInterpolationWhenNoKnowledgeBase(self):
    creator = db_test_utils.InitializeUser(data_store.REL_DB)
    client_id = db_test_utils.InitializeClient(data_store.REL_DB)

    # We do not write any snapshot not to have any knowledgebase for the client.

    flow_args = flows_pb2.FileFinderArgs(
        action=flows_pb2.FileFinderAction(
            action_type=flows_pb2.FileFinderAction.Action.STAT
        ),
        paths=["/var/foo", "%%os%%"],
    )

    flow_id = flow_test_lib.StartFlow(
        file_finder.ClientFileFinder,
        creator=creator,
        client_id=client_id,
        flow_args=flow_args,
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.RUNNING)
    log_entries = data_store.REL_DB.ReadFlowLogEntries(
        client_id=client_id, flow_id=flow_id, offset=0, count=1024
    )
    self.assertLen(log_entries, 1)
    self.assertIn(
        "knowledgebase interpolation: 'os' is missing",
        log_entries[0].message,
    )

  def testFailsIfAllGlobsWithAreSkippedDueToNoKnowledgeBase(self):
    creator = db_test_utils.InitializeUser(data_store.REL_DB)
    client_id = db_test_utils.InitializeClient(data_store.REL_DB)

    # We do not write any snapshot not to have any knowledgebase for the client.

    flow_args = flows_pb2.FileFinderArgs(
        action=flows_pb2.FileFinderAction(
            action_type=flows_pb2.FileFinderAction.Action.STAT
        ),
        paths=["%%os%%"],
    )

    flow_id = flow_test_lib.StartFlow(
        file_finder.ClientFileFinder,
        creator=creator,
        client_id=client_id,
        flow_args=flow_args,
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.ERROR)
    self.assertIn(
        "All globs skipped, as there's no knowledgebase available for"
        " interpolation",
        flow_obj.error_message,
    )

  def testReportsProgressStart(self):
    creator = db_test_utils.InitializeUser(data_store.REL_DB)
    client_id = db_test_utils.InitializeClient(data_store.REL_DB)

    with temp.AutoTempDirPath(remove_non_empty=True) as tempdir:
      path = os.path.join(tempdir, "foo")
      with io.open(path, "w") as fd:
        fd.write("some content")

      flow_args = flows_pb2.FileFinderArgs(
          action=flows_pb2.FileFinderAction(
              action_type=flows_pb2.FileFinderAction.Action.STAT
          ),
          paths=[path],
      )
      flow_id = flow_test_lib.StartFlow(
          file_finder.ClientFileFinder,
          creator=creator,
          client_id=client_id,
          flow_args=flow_args,
      )

      flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
      progress = flows_pb2.FileFinderProgress()
      flow_obj.progress.Unpack(progress)
      self.assertTrue(progress.HasField("files_found"))
      self.assertEqual(progress.files_found, 0)

  def testReportsProgressEnd(self):
    creator = db_test_utils.InitializeUser(data_store.REL_DB)
    client_id = db_test_utils.InitializeClient(data_store.REL_DB)

    with temp.AutoTempDirPath(remove_non_empty=True) as tempdir:
      path = os.path.join(tempdir, "foo")
      with io.open(path, "w") as fd:
        fd.write("some content")

      flow_args = flows_pb2.FileFinderArgs(
          action=flows_pb2.FileFinderAction(
              action_type=flows_pb2.FileFinderAction.Action.STAT
          ),
          paths=[path],
      )
      flow_id = flow_test_lib.StartAndRunFlow(
          file_finder.ClientFileFinder,
          action_mocks.ClientFileFinderClientMock(),
          creator=creator,
          client_id=client_id,
          flow_args=flow_args,
      )

      flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
      progress = flows_pb2.FileFinderProgress()
      flow_obj.progress.Unpack(progress)
      self.assertEqual(progress.files_found, 1)

  @db_test_lib.WithDatabase
  def testRRG_Stat(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.FileFinderArgs(
        action=flows_pb2.FileFinderAction(
            action_type=flows_pb2.FileFinderAction.Action.STAT
        ),
        pathtype=jobs_pb2.PathSpec.PathType.OS,
        paths=["/foo/bar"],
    )

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=file_finder.ClientFileFinder,
        flow_args=args,
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/bar": b"Lorem ipsum.",
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=8)
    self.assertLen(flow_results, 1)

    result = flows_pb2.FileFinderResult()
    self.assertTrue(flow_results[0].payload.Unpack(result))

    self.assertTrue(stat.S_ISREG(result.stat_entry.st_mode))
    self.assertEqual(result.stat_entry.st_size, len(b"Lorem ipsum."))  # pylint: disable=g-generic-assert
    self.assertEmpty(result.hash_entry.md5)
    self.assertEmpty(result.hash_entry.sha1)
    self.assertEmpty(result.hash_entry.sha256)

    path_info = rel_db.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("foo", "bar"),
    )
    self.assertTrue(stat.S_ISREG(path_info.stat_entry.st_mode))
    self.assertEqual(path_info.stat_entry.st_size, len(b"Lorem ipsum."))  # pylint: disable=g-generic-assert
    self.assertEmpty(path_info.hash_entry.md5)
    self.assertEmpty(path_info.hash_entry.sha1)
    self.assertEmpty(path_info.hash_entry.sha256)

  @db_test_lib.WithDatabase
  def testRRG_Stat_Windows(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.WINDOWS,
    )

    args = flows_pb2.FileFinderArgs(
        action=flows_pb2.FileFinderAction(
            action_type=flows_pb2.FileFinderAction.Action.STAT
        ),
        pathtype=jobs_pb2.PathSpec.PathType.OS,
        paths=["X:\\Foo\\Bar Baz"],
    )

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=file_finder.ClientFileFinder,
        flow_args=args,
        handlers=rrg_test_lib.FakeWindowsFileHandlers({
            "X:\\Foo\\Bar Baz": b"Lorem ipsum.",
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=8)
    self.assertLen(flow_results, 1)

    result = flows_pb2.FileFinderResult()
    self.assertTrue(flow_results[0].payload.Unpack(result))

    self.assertTrue(stat.S_ISREG(result.stat_entry.st_mode))
    self.assertEqual(result.stat_entry.pathspec.path, "X:/Foo/Bar Baz")
    self.assertEqual(result.stat_entry.st_size, len(b"Lorem ipsum."))  # pylint: disable=g-generic-assert
    self.assertEmpty(result.hash_entry.md5)
    self.assertEmpty(result.hash_entry.sha1)
    self.assertEmpty(result.hash_entry.sha256)

    path_info = rel_db.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("X:", "Foo", "Bar Baz"),
    )
    self.assertTrue(stat.S_ISREG(path_info.stat_entry.st_mode))
    self.assertEqual(path_info.stat_entry.st_size, len(b"Lorem ipsum."))  # pylint: disable=g-generic-assert
    self.assertEmpty(path_info.hash_entry.md5)
    self.assertEmpty(path_info.hash_entry.sha1)
    self.assertEmpty(path_info.hash_entry.sha256)

  @db_test_lib.WithDatabase
  def testRRG_Stat_Condition_Size(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.FileFinderArgs(
        action=flows_pb2.FileFinderAction(
            action_type=flows_pb2.FileFinderAction.Action.STAT
        ),
        pathtype=jobs_pb2.PathSpec.PathType.OS,
        paths=["/foo/bar", "/foo/baz"],
        conditions=[
            flows_pb2.FileFinderCondition(
                condition_type=flows_pb2.FileFinderCondition.SIZE,
                size=flows_pb2.FileFinderSizeCondition(
                    min_file_size=len(b"Lorem ipsum."),
                    max_file_size=len(b"Lorem ipsum."),
                ),
            )
        ],
    )

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=file_finder.ClientFileFinder,
        flow_args=args,
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/bar": b"Lorem ipsum.",
            "/foo/baz": b"Dolor sit amet.",
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=8)
    self.assertLen(flow_results, 1)

    results_by_path = {}

    for flow_result in flow_results:
      result = flows_pb2.FileFinderResult()
      self.assertTrue(flow_result.payload.Unpack(result))

      results_by_path[result.stat_entry.pathspec.path] = result

    self.assertIn("/foo/bar", results_by_path)
    self.assertNotIn("/foo/baz", results_by_path)

  @db_test_lib.WithDatabase
  def testRRG_Stat_Condition_Time(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.FileFinderArgs(
        action=flows_pb2.FileFinderAction(
            action_type=flows_pb2.FileFinderAction.Action.STAT
        ),
        pathtype=jobs_pb2.PathSpec.PathType.OS,
        paths=["/foo/bar", "/foo/baz"],
        conditions=[
            flows_pb2.FileFinderCondition(
                condition_type=flows_pb2.FileFinderCondition.MODIFICATION_TIME,
                modification_time=flows_pb2.FileFinderModificationTimeCondition(
                    min_last_modified_time=int(rdfvalue.RDFDatetime.Now()),
                    max_last_modified_time=int(
                        rdfvalue.RDFDatetime.Now()
                        + rdfvalue.Duration.From(1, rdfvalue.DAYS)
                    ),
                ),
            ),
            flows_pb2.FileFinderCondition(
                condition_type=flows_pb2.FileFinderCondition.ACCESS_TIME,
                access_time=flows_pb2.FileFinderAccessTimeCondition(
                    min_last_access_time=int(rdfvalue.RDFDatetime.Now()),
                    max_last_access_time=int(
                        rdfvalue.RDFDatetime.Now()
                        + rdfvalue.Duration.From(1, rdfvalue.DAYS)
                    ),
                ),
            ),
        ],
    )

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=file_finder.ClientFileFinder,
        flow_args=args,
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/bar": b"Lorem ipsum.",
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=8)
    self.assertLen(flow_results, 1)

    result = flows_pb2.FileFinderResult()
    self.assertTrue(flow_results[0].payload.Unpack(result))
    self.assertEqual(result.stat_entry.pathspec.path, "/foo/bar")

  @db_test_lib.WithDatabase
  def testRRG_Stat_Condition_ContentsLiteral(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.FileFinderArgs(
        action=flows_pb2.FileFinderAction(
            action_type=flows_pb2.FileFinderAction.Action.STAT
        ),
        pathtype=jobs_pb2.PathSpec.PathType.OS,
        paths=["/foo", "/bar", "/baz"],
        conditions=[
            flows_pb2.FileFinderCondition(
                condition_type=flows_pb2.FileFinderCondition.CONTENTS_LITERAL_MATCH,
                contents_literal_match=flows_pb2.FileFinderContentsLiteralMatchCondition(
                    literal=b"FOO"
                ),
            ),
            flows_pb2.FileFinderCondition(
                condition_type=flows_pb2.FileFinderCondition.SIZE,
                size=flows_pb2.FileFinderSizeCondition(
                    max_file_size=1024,
                ),
            ),
        ],
    )

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=file_finder.ClientFileFinder,
        flow_args=args,
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo": b"== FOO ==",
            "/bar": b"== BAR ==",
            "/baz": b"== BAZ ==",
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    results_by_path = {}

    flow_results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=8)
    for flow_result in flow_results:
      result = flows_pb2.FileFinderResult()
      self.assertTrue(flow_result.payload.Unpack(result))

      results_by_path[result.stat_entry.pathspec.path] = result

    self.assertIn("/foo", results_by_path)
    self.assertNotIn("/bar", results_by_path)
    self.assertNotIn("/baz", results_by_path)

  @db_test_lib.WithDatabase
  def testRRG_Stat_Condition_ContentsLiteral_NoMaxSize(
      self,
      rel_db: db.Database,
  ):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.FileFinderArgs()
    args.action.action_type = flows_pb2.FileFinderAction.Action.STAT
    args.pathtype = jobs_pb2.PathSpec.PathType.OS
    args.paths.extend(["/**"])

    cond = args.conditions.add()
    cond.condition_type = flows_pb2.FileFinderCondition.CONTENTS_LITERAL_MATCH
    cond.contents_literal_match.literal = b"FOO"

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=file_finder.ClientFileFinder,
        flow_args=args,
        handlers=rrg_test_lib.FakePosixFileHandlers({}),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.ERROR)
    self.assertIn("no `max_file_size`", flow_obj.error_message)

  @db_test_lib.WithDatabase
  def testRRG_Stat_Condition_ContentsRegex(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.FileFinderArgs(
        action=flows_pb2.FileFinderAction(
            action_type=flows_pb2.FileFinderAction.Action.STAT
        ),
        pathtype=jobs_pb2.PathSpec.PathType.OS,
        paths=["/foo", "/bar", "/baz"],
        conditions=[
            flows_pb2.FileFinderCondition(
                condition_type=flows_pb2.FileFinderCondition.CONTENTS_REGEX_MATCH,
                contents_regex_match=flows_pb2.FileFinderContentsRegexMatchCondition(
                    regex=b"BA[RZ]"
                ),
            ),
            flows_pb2.FileFinderCondition(
                condition_type=flows_pb2.FileFinderCondition.SIZE,
                size=flows_pb2.FileFinderSizeCondition(
                    max_file_size=1024,
                ),
            ),
        ],
    )

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=file_finder.ClientFileFinder,
        flow_args=args,
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo": b"== FOO ==",
            "/bar": b"== BAR ==",
            "/baz": b"== BAZ ==",
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    results_by_path = {}

    flow_results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=8)
    for flow_result in flow_results:
      result = flows_pb2.FileFinderResult()
      self.assertTrue(flow_result.payload.Unpack(result))

      results_by_path[result.stat_entry.pathspec.path] = result

    self.assertIn("/bar", results_by_path)
    self.assertIn("/baz", results_by_path)
    self.assertNotIn("/foo", results_by_path)

  @db_test_lib.WithDatabase
  def testRRG_Stat_Condition_ContentsRegex_NoMaxSize(
      self,
      rel_db: db.Database,
  ):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.FileFinderArgs()
    args.action.action_type = flows_pb2.FileFinderAction.Action.STAT
    args.pathtype = jobs_pb2.PathSpec.PathType.OS
    args.paths.extend(["/**"])

    cond = args.conditions.add()
    cond.condition_type = flows_pb2.FileFinderCondition.CONTENTS_REGEX_MATCH
    cond.contents_regex_match.regex = b"BA[RZ]"

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=file_finder.ClientFileFinder,
        flow_args=args,
        handlers=rrg_test_lib.FakePosixFileHandlers({}),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.ERROR)
    self.assertIn("no `max_file_size`", flow_obj.error_message)

  @db_test_lib.WithDatabase
  def testRRG_Hash(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.FileFinderArgs(
        action=flows_pb2.FileFinderAction(
            action_type=flows_pb2.FileFinderAction.Action.HASH
        ),
        pathtype=jobs_pb2.PathSpec.PathType.OS,
        paths=["/foo/bar"],
    )

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=file_finder.ClientFileFinder,
        flow_args=args,
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/bar": b"Lorem ipsum.",
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=8)
    self.assertLen(flow_results, 1)

    result = flows_pb2.FileFinderResult()
    self.assertTrue(flow_results[0].payload.Unpack(result))

    self.assertTrue(stat.S_ISREG(result.stat_entry.st_mode))
    self.assertEqual(result.stat_entry.st_size, len(b"Lorem ipsum."))  # pylint: disable=g-generic-assert
    self.assertEqual(
        result.hash_entry.md5,
        hashlib.md5(b"Lorem ipsum.").digest(),
    )
    self.assertEqual(
        result.hash_entry.sha1,
        hashlib.sha1(b"Lorem ipsum.").digest(),
    )
    self.assertEqual(
        result.hash_entry.sha256,
        hashlib.sha256(b"Lorem ipsum.").digest(),
    )

    path_info = rel_db.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("foo", "bar"),
    )
    self.assertTrue(stat.S_ISREG(path_info.stat_entry.st_mode))
    self.assertEqual(path_info.stat_entry.st_size, len(b"Lorem ipsum."))  # pylint: disable=g-generic-assert
    self.assertEqual(
        path_info.hash_entry.md5,
        hashlib.md5(b"Lorem ipsum.").digest(),
    )
    self.assertEqual(
        path_info.hash_entry.sha1,
        hashlib.sha1(b"Lorem ipsum.").digest(),
    )
    self.assertEqual(
        path_info.hash_entry.sha256,
        hashlib.sha256(b"Lorem ipsum.").digest(),
    )

  @db_test_lib.WithDatabase
  def testRRG_Hash_Windows(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.WINDOWS,
    )

    args = flows_pb2.FileFinderArgs(
        action=flows_pb2.FileFinderAction(
            action_type=flows_pb2.FileFinderAction.Action.HASH
        ),
        pathtype=jobs_pb2.PathSpec.PathType.OS,
        paths=["X:\\Foo\\Bar Baz"],
    )

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=file_finder.ClientFileFinder,
        flow_args=args,
        handlers=rrg_test_lib.FakeWindowsFileHandlers({
            "X:\\Foo\\Bar Baz": b"Lorem ipsum.",
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=8)
    self.assertLen(flow_results, 1)

    result = flows_pb2.FileFinderResult()
    self.assertTrue(flow_results[0].payload.Unpack(result))

    self.assertTrue(stat.S_ISREG(result.stat_entry.st_mode))
    self.assertEqual(result.stat_entry.pathspec.path, "X:/Foo/Bar Baz")
    self.assertEqual(result.stat_entry.st_size, len(b"Lorem ipsum."))  # pylint: disable=g-generic-assert
    self.assertEqual(
        result.hash_entry.md5,
        hashlib.md5(b"Lorem ipsum.").digest(),
    )
    self.assertEqual(
        result.hash_entry.sha1,
        hashlib.sha1(b"Lorem ipsum.").digest(),
    )
    self.assertEqual(
        result.hash_entry.sha256,
        hashlib.sha256(b"Lorem ipsum.").digest(),
    )

    path_info = rel_db.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("X:", "Foo", "Bar Baz"),
    )
    self.assertTrue(stat.S_ISREG(path_info.stat_entry.st_mode))
    self.assertEqual(path_info.stat_entry.st_size, len(b"Lorem ipsum."))  # pylint: disable=g-generic-assert
    self.assertEqual(
        path_info.hash_entry.md5,
        hashlib.md5(b"Lorem ipsum.").digest(),
    )
    self.assertEqual(
        path_info.hash_entry.sha1,
        hashlib.sha1(b"Lorem ipsum.").digest(),
    )
    self.assertEqual(
        path_info.hash_entry.sha256,
        hashlib.sha256(b"Lorem ipsum.").digest(),
    )

  @db_test_lib.WithDatabase
  def testRRG_Hash_Condition(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.FileFinderArgs(
        action=flows_pb2.FileFinderAction(
            action_type=flows_pb2.FileFinderAction.Action.HASH
        ),
        pathtype=jobs_pb2.PathSpec.PathType.OS,
        paths=["/foo/bar", "/foo/baz"],
        conditions=[
            flows_pb2.FileFinderCondition(
                condition_type=flows_pb2.FileFinderCondition.SIZE,
                size=flows_pb2.FileFinderSizeCondition(
                    min_file_size=len(b"Lorem ipsum."),
                    max_file_size=len(b"Lorem ipsum."),
                ),
            )
        ],
    )

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=file_finder.ClientFileFinder,
        flow_args=args,
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/bar": b"Lorem ipsum.",
            "/foo/baz": b"Dolor sit amet.",
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=8)
    self.assertLen(flow_results, 1)

    results_by_path = {}

    for flow_result in flow_results:
      result = flows_pb2.FileFinderResult()
      self.assertTrue(flow_result.payload.Unpack(result))

      results_by_path[result.stat_entry.pathspec.path] = result

    self.assertIn("/foo/bar", results_by_path)
    self.assertNotIn("/foo/baz", results_by_path)

    self.assertEqual(
        results_by_path["/foo/bar"].hash_entry.md5,
        hashlib.md5(b"Lorem ipsum.").digest(),
    )
    self.assertEqual(
        results_by_path["/foo/bar"].hash_entry.sha1,
        hashlib.sha1(b"Lorem ipsum.").digest(),
    )
    self.assertEqual(
        results_by_path["/foo/bar"].hash_entry.sha256,
        hashlib.sha256(b"Lorem ipsum.").digest(),
    )

  @db_test_lib.WithDatabase
  def testRRG_Hash_Condition_Windows(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.WINDOWS,
    )

    args = flows_pb2.FileFinderArgs(
        action=flows_pb2.FileFinderAction(
            action_type=flows_pb2.FileFinderAction.Action.HASH
        ),
        pathtype=jobs_pb2.PathSpec.PathType.OS,
        paths=["X:\\Foo\\Bar", "X:\\Foo\\Baz"],
        conditions=[
            flows_pb2.FileFinderCondition(
                condition_type=flows_pb2.FileFinderCondition.SIZE,
                size=flows_pb2.FileFinderSizeCondition(
                    min_file_size=len(b"Lorem ipsum."),
                    max_file_size=len(b"Lorem ipsum."),
                ),
            ),
        ],
    )

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=file_finder.ClientFileFinder,
        flow_args=args,
        handlers=rrg_test_lib.FakeWindowsFileHandlers({
            "X:\\Foo\\Bar": b"Lorem ipsum.",
            "X:\\Foo\\Baz": b"Dolor sit amet.",
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=8)
    self.assertLen(flow_results, 1)

    results_by_path = {}

    for flow_result in flow_results:
      result = flows_pb2.FileFinderResult()
      self.assertTrue(flow_result.payload.Unpack(result))

      results_by_path[result.stat_entry.pathspec.path] = result

    self.assertIn("X:/Foo/Bar", results_by_path)
    self.assertNotIn("X:/Foo/Baz", results_by_path)

    self.assertEqual(
        results_by_path["X:/Foo/Bar"].hash_entry.md5,
        hashlib.md5(b"Lorem ipsum.").digest(),
    )
    self.assertEqual(
        results_by_path["X:/Foo/Bar"].hash_entry.sha1,
        hashlib.sha1(b"Lorem ipsum.").digest(),
    )
    self.assertEqual(
        results_by_path["X:/Foo/Bar"].hash_entry.sha256,
        hashlib.sha256(b"Lorem ipsum.").digest(),
    )

  @db_test_lib.WithDatabase
  def testRRG_Download(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.FileFinderArgs(
        action=flows_pb2.FileFinderAction(
            action_type=flows_pb2.FileFinderAction.Action.DOWNLOAD
        ),
        pathtype=jobs_pb2.PathSpec.PathType.OS,
        paths=["/foo/bar"],
    )

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=file_finder.ClientFileFinder,
        flow_args=args,
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/bar": b"Lorem ipsum.",
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=8)
    self.assertLen(flow_results, 1)

    result = flows_pb2.FileFinderResult()
    self.assertTrue(flow_results[0].payload.Unpack(result))

    self.assertTrue(stat.S_ISREG(result.stat_entry.st_mode))
    self.assertEqual(result.stat_entry.st_size, len(b"Lorem ipsum."))  # pylint: disable=g-generic-assert
    self.assertEqual(
        result.hash_entry.md5,
        hashlib.md5(b"Lorem ipsum.").digest(),
    )
    self.assertEqual(
        result.hash_entry.sha1,
        hashlib.sha1(b"Lorem ipsum.").digest(),
    )
    self.assertEqual(
        result.hash_entry.sha256,
        hashlib.sha256(b"Lorem ipsum.").digest(),
    )

    path_info = rel_db.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("foo", "bar"),
    )
    self.assertTrue(stat.S_ISREG(path_info.stat_entry.st_mode))
    self.assertEqual(path_info.stat_entry.st_size, len(b"Lorem ipsum."))  # pylint: disable=g-generic-assert
    self.assertEqual(
        path_info.hash_entry.sha256,
        hashlib.sha256(b"Lorem ipsum.").digest(),
    )

    file = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("foo", "bar"),
        ),
    )
    self.assertEqual(file.read(), b"Lorem ipsum.")

  @db_test_lib.WithDatabase
  def testRRG_Download_Windows(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.WINDOWS,
    )

    args = flows_pb2.FileFinderArgs(
        action=flows_pb2.FileFinderAction(
            action_type=flows_pb2.FileFinderAction.Action.DOWNLOAD
        ),
        pathtype=jobs_pb2.PathSpec.PathType.OS,
        paths=["X:\\Foo\\Bar Baz"],
    )

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=file_finder.ClientFileFinder,
        flow_args=args,
        handlers=rrg_test_lib.FakeWindowsFileHandlers({
            "X:\\Foo\\Bar Baz": b"Lorem ipsum.",
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=8)
    self.assertLen(flow_results, 1)

    result = flows_pb2.FileFinderResult()
    self.assertTrue(flow_results[0].payload.Unpack(result))

    self.assertTrue(stat.S_ISREG(result.stat_entry.st_mode))
    self.assertEqual(result.stat_entry.pathspec.path, "X:/Foo/Bar Baz")
    self.assertEqual(result.stat_entry.st_size, len(b"Lorem ipsum."))  # pylint: disable=g-generic-assert
    self.assertEqual(
        result.hash_entry.md5,
        hashlib.md5(b"Lorem ipsum.").digest(),
    )
    self.assertEqual(
        result.hash_entry.sha1,
        hashlib.sha1(b"Lorem ipsum.").digest(),
    )
    self.assertEqual(
        result.hash_entry.sha256,
        hashlib.sha256(b"Lorem ipsum.").digest(),
    )

    path_info = rel_db.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("X:", "Foo", "Bar Baz"),
    )
    self.assertTrue(stat.S_ISREG(path_info.stat_entry.st_mode))
    self.assertEqual(path_info.stat_entry.st_size, len(b"Lorem ipsum."))  # pylint: disable=g-generic-assert
    self.assertEqual(
        path_info.hash_entry.sha256,
        hashlib.sha256(b"Lorem ipsum.").digest(),
    )
    self.assertEqual(  # pylint: disable=g-generic-assert
        path_info.hash_entry.num_bytes,
        len(b"Lorem ipsum."),
    )

    file = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("X:", "Foo", "Bar Baz"),
        ),
    )
    self.assertEqual(file.read(), b"Lorem ipsum.")

  @db_test_lib.WithDatabase
  def testRRG_Download_Large(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )
    content = os.urandom(13371337)

    args = flows_pb2.FileFinderArgs(
        action=flows_pb2.FileFinderAction(
            action_type=flows_pb2.FileFinderAction.Action.DOWNLOAD
        ),
        pathtype=jobs_pb2.PathSpec.PathType.OS,
        paths=["/foo/bar"],
    )

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=file_finder.ClientFileFinder,
        flow_args=args,
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/bar": content,
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=8)
    self.assertLen(flow_results, 1)

    result = flows_pb2.FileFinderResult()
    self.assertTrue(flow_results[0].payload.Unpack(result))

    self.assertTrue(stat.S_ISREG(result.stat_entry.st_mode))
    self.assertEqual(result.stat_entry.st_size, 13371337)
    self.assertEqual(
        result.hash_entry.md5,
        hashlib.md5(content).digest(),
    )
    self.assertEqual(
        result.hash_entry.sha1,
        hashlib.sha1(content).digest(),
    )
    self.assertEqual(
        result.hash_entry.sha256,
        hashlib.sha256(content).digest(),
    )

    path_info = rel_db.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("foo", "bar"),
    )
    self.assertTrue(stat.S_ISREG(path_info.stat_entry.st_mode))
    self.assertEqual(path_info.stat_entry.st_size, 13371337)
    self.assertEqual(
        path_info.hash_entry.sha256,
        hashlib.sha256(content).digest(),
    )

    file = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("foo", "bar"),
        ),
    )
    # We need to explicitly pass length to `read` as otherwise it fails with
    # oversized read error. Oversized reads are not enforced if the length is
    # specifiad manually.
    self.assertEqual(file.read(13371337), content)

  @db_test_lib.WithDatabase
  def testRRG_Download_Special(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.FileFinderArgs()
    args.action.action_type = flows_pb2.FileFinderAction.Action.DOWNLOAD
    args.action.download.max_size = 42
    args.pathtype = jobs_pb2.PathSpec.PathType.OS
    args.paths.append("/dev/random")

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=file_finder.ClientFileFinder,
        flow_args=args,
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/dev/random": None,
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=8)
    self.assertLen(flow_results, 1)

    result = flows_pb2.FileFinderResult()
    self.assertTrue(flow_results[0].payload.Unpack(result))

    self.assertTrue(stat.S_ISCHR(result.stat_entry.st_mode))
    self.assertEqual(result.stat_entry.st_size, 0)

    path_info = rel_db.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("dev", "random"),
    )
    self.assertTrue(stat.S_ISCHR(path_info.stat_entry.st_mode))
    self.assertEqual(path_info.stat_entry.st_size, 0)
    self.assertEqual(path_info.hash_entry.num_bytes, 42)

    file = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("dev", "random"),
        ),
    )
    self.assertLen(file.read(), 42)

  @db_test_lib.WithDatabase
  def testRRG_Download_Special_NoMaxSize(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.FileFinderArgs()
    args.action.action_type = flows_pb2.FileFinderAction.Action.DOWNLOAD
    args.action.download.max_size = 0
    args.pathtype = jobs_pb2.PathSpec.PathType.OS
    args.paths.append("/dev/random")

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=file_finder.ClientFileFinder,
        flow_args=args,
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/dev/random": None,
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=8)
    self.assertLen(flow_results, 1)

    result = flows_pb2.FileFinderResult()
    self.assertTrue(flow_results[0].payload.Unpack(result))

    self.assertTrue(stat.S_ISCHR(result.stat_entry.st_mode))
    self.assertEqual(result.stat_entry.st_size, 0)

    path_info = rel_db.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("dev", "random"),
    )
    self.assertTrue(stat.S_ISCHR(path_info.stat_entry.st_mode))
    self.assertEqual(path_info.stat_entry.st_size, 0)

    # The size limit was not specified, it should not be collected.
    with self.assertRaises(file_store.FileHasNoContentError):
      file_store.OpenFile(
          db.ClientPath.OS(
              client_id=client_id,
              components=("dev", "random"),
          ),
      )

  @db_test_lib.WithDatabase
  def testRRG_Download_Multiple(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.FileFinderArgs(
        action=flows_pb2.FileFinderAction(
            action_type=flows_pb2.FileFinderAction.Action.DOWNLOAD
        ),
        pathtype=jobs_pb2.PathSpec.PathType.OS,
        paths=["/quux/foo", "/quux/bar", "/quux/baz"],
    )

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=file_finder.ClientFileFinder,
        flow_args=args,
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/quux/foo": b"Lorem ipsum.",
            "/quux/bar": b"Dolor sit amet.",
            "/quux/baz": b"Consectetur adipiscing elit.",
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=8)
    self.assertLen(flow_results, 3)

    results_by_path: dict[str, flows_pb2.FileFinderResult] = {}
    for flow_result in flow_results:
      result = flows_pb2.FileFinderResult()
      self.assertTrue(flow_result.payload.Unpack(result))

      results_by_path[result.stat_entry.pathspec.path] = result

    result_foo = results_by_path["/quux/foo"]
    self.assertTrue(stat.S_ISREG(result_foo.stat_entry.st_mode))
    self.assertEqual(  # pylint: disable=g-generic-assert
        result_foo.stat_entry.st_size,
        len(b"Lorem ipsum."),
    )
    self.assertEqual(
        result_foo.hash_entry.md5,
        hashlib.md5(b"Lorem ipsum.").digest(),
    )
    self.assertEqual(
        result_foo.hash_entry.sha1,
        hashlib.sha1(b"Lorem ipsum.").digest(),
    )
    self.assertEqual(
        result_foo.hash_entry.sha256,
        hashlib.sha256(b"Lorem ipsum.").digest(),
    )

    result_bar = results_by_path["/quux/bar"]
    self.assertTrue(stat.S_ISREG(result_bar.stat_entry.st_mode))
    self.assertEqual(  # pylint: disable=g-generic-assert
        result_bar.stat_entry.st_size,
        len(b"Dolor sit amet."),
    )
    self.assertEqual(
        result_bar.hash_entry.md5,
        hashlib.md5(b"Dolor sit amet.").digest(),
    )
    self.assertEqual(
        result_bar.hash_entry.sha1,
        hashlib.sha1(b"Dolor sit amet.").digest(),
    )
    self.assertEqual(
        result_bar.hash_entry.sha256,
        hashlib.sha256(b"Dolor sit amet.").digest(),
    )

    result_baz = results_by_path["/quux/baz"]
    self.assertTrue(stat.S_ISREG(result_baz.stat_entry.st_mode))
    self.assertEqual(  # pylint: disable=g-generic-assert
        result_baz.stat_entry.st_size,
        len(b"Consectetur adipiscing elit."),
    )
    self.assertEqual(
        result_baz.hash_entry.md5,
        hashlib.md5(b"Consectetur adipiscing elit.").digest(),
    )
    self.assertEqual(
        result_baz.hash_entry.sha1,
        hashlib.sha1(b"Consectetur adipiscing elit.").digest(),
    )
    self.assertEqual(
        result_baz.hash_entry.sha256,
        hashlib.sha256(b"Consectetur adipiscing elit.").digest(),
    )

    path_info_foo = rel_db.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("quux", "foo"),
    )
    self.assertTrue(stat.S_ISREG(path_info_foo.stat_entry.st_mode))
    self.assertEqual(  # pylint: disable=g-generic-assert
        path_info_foo.stat_entry.st_size,
        len(b"Lorem ipsum."),
    )
    self.assertEqual(
        path_info_foo.hash_entry.sha256,
        hashlib.sha256(b"Lorem ipsum.").digest(),
    )
    self.assertEqual(  # pylint: disable=g-generic-assert
        path_info_foo.hash_entry.num_bytes,
        len(b"Lorem ipsum."),
    )

    path_info_bar = rel_db.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("quux", "bar"),
    )
    self.assertTrue(stat.S_ISREG(path_info_bar.stat_entry.st_mode))
    self.assertEqual(  # pylint: disable=g-generic-assert
        path_info_bar.stat_entry.st_size,
        len(b"Dolor sit amet."),
    )
    self.assertEqual(
        path_info_bar.hash_entry.sha256,
        hashlib.sha256(b"Dolor sit amet.").digest(),
    )
    self.assertEqual(  # pylint: disable=g-generic-assert
        path_info_bar.hash_entry.num_bytes,
        len(b"Dolor sit amet."),
    )

    path_info_baz = rel_db.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("quux", "baz"),
    )
    self.assertTrue(stat.S_ISREG(path_info_baz.stat_entry.st_mode))
    self.assertEqual(  # pylint: disable=g-generic-assert
        path_info_baz.stat_entry.st_size,
        len(b"Consectetur adipiscing elit."),
    )
    self.assertEqual(
        path_info_baz.hash_entry.sha256,
        hashlib.sha256(b"Consectetur adipiscing elit.").digest(),
    )
    self.assertEqual(  # pylint: disable=g-generic-assert
        path_info_baz.hash_entry.num_bytes,
        len(b"Consectetur adipiscing elit."),
    )

    file_foo = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("quux", "foo"),
        ),
    )
    self.assertEqual(file_foo.read(), b"Lorem ipsum.")

    file_bar = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("quux", "bar"),
        ),
    )
    self.assertEqual(file_bar.read(), b"Dolor sit amet.")

    file_baz = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("quux", "baz"),
        ),
    )
    self.assertEqual(file_baz.read(), b"Consectetur adipiscing elit.")

  @db_test_lib.WithDatabase
  def testRRG_Download_Duplicate(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.FileFinderArgs(
        action=flows_pb2.FileFinderAction(
            action_type=flows_pb2.FileFinderAction.Action.DOWNLOAD
        ),
        pathtype=jobs_pb2.PathSpec.PathType.OS,
        paths=["/foo/bar", "/foo/bar"],
    )

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=file_finder.ClientFileFinder,
        flow_args=args,
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/bar": b"Lorem ipsum.",
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=8)
    self.assertLen(flow_results, 1)

    result = flows_pb2.FileFinderResult()
    self.assertTrue(flow_results[0].payload.Unpack(result))

    self.assertTrue(stat.S_ISREG(result.stat_entry.st_mode))
    self.assertEqual(result.stat_entry.st_size, len(b"Lorem ipsum."))  # pylint: disable=g-generic-assert
    self.assertEqual(
        result.hash_entry.md5,
        hashlib.md5(b"Lorem ipsum.").digest(),
    )
    self.assertEqual(
        result.hash_entry.sha1,
        hashlib.sha1(b"Lorem ipsum.").digest(),
    )
    self.assertEqual(
        result.hash_entry.sha256,
        hashlib.sha256(b"Lorem ipsum.").digest(),
    )

    path_info = rel_db.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("foo", "bar"),
    )
    self.assertTrue(stat.S_ISREG(path_info.stat_entry.st_mode))
    self.assertEqual(path_info.stat_entry.st_size, len(b"Lorem ipsum."))  # pylint: disable=g-generic-assert
    self.assertEqual(
        path_info.hash_entry.sha256,
        hashlib.sha256(b"Lorem ipsum.").digest(),
    )
    self.assertEqual(  # pylint: disable=g-generic-assert
        path_info.hash_entry.num_bytes,
        len(b"Lorem ipsum."),
    )

    file = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("foo", "bar"),
        ),
    )
    self.assertEqual(file.read(), b"Lorem ipsum.")

  @db_test_lib.WithDatabase
  def testRRG_Download_Delayed(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.FileFinderArgs(
        action=flows_pb2.FileFinderAction(
            action_type=flows_pb2.FileFinderAction.Action.DOWNLOAD
        ),
        pathtype=jobs_pb2.PathSpec.PathType.OS,
        paths=["/foo/bar"],
    )

    check_blobs_exist_orig = data_store.BLOBS.CheckBlobsExist
    check_blobs_exist_count = 0

    def CheckBlobsExistDelayed(
        blob_ids: Iterable[models_blobs.BlobID],
    ) -> dict[models_blobs.BlobID, bool]:
      nonlocal check_blobs_exist_count
      check_blobs_exist_count += 1

      if check_blobs_exist_count <= 2:
        return {blob_id: False for blob_id in blob_ids}

      return check_blobs_exist_orig(blob_ids)

    self.enter_context(
        mock.patch.object(
            data_store.BLOBS,
            "CheckBlobsExist",
            CheckBlobsExistDelayed,
        )
    )
    self.enter_context(
        mock.patch.object(
            file_finder.ClientFileFinder,
            "BLOB_CHECK_DELAY",
            rdfvalue.Duration(0),
        )
    )

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=file_finder.ClientFileFinder,
        flow_args=args,
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/bar": b"Lorem ipsum.",
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=8)
    self.assertLen(flow_results, 1)

    result = flows_pb2.FileFinderResult()
    self.assertTrue(flow_results[0].payload.Unpack(result))

    self.assertTrue(stat.S_ISREG(result.stat_entry.st_mode))
    self.assertEqual(result.stat_entry.st_size, len(b"Lorem ipsum."))  # pylint: disable=g-generic-assert
    self.assertEqual(
        result.hash_entry.md5,
        hashlib.md5(b"Lorem ipsum.").digest(),
    )
    self.assertEqual(
        result.hash_entry.sha1,
        hashlib.sha1(b"Lorem ipsum.").digest(),
    )
    self.assertEqual(
        result.hash_entry.sha256,
        hashlib.sha256(b"Lorem ipsum.").digest(),
    )

    path_info = rel_db.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("foo", "bar"),
    )
    self.assertTrue(stat.S_ISREG(path_info.stat_entry.st_mode))
    self.assertEqual(path_info.stat_entry.st_size, len(b"Lorem ipsum."))  # pylint: disable=g-generic-assert
    self.assertEqual(
        path_info.hash_entry.sha256,
        hashlib.sha256(b"Lorem ipsum.").digest(),
    )

    file = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("foo", "bar"),
        ),
    )
    self.assertEqual(file.read(), b"Lorem ipsum.")

  @db_test_lib.WithDatabase
  def testRRG_Download_Glob(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.FileFinderArgs(
        action=flows_pb2.FileFinderAction(
            action_type=flows_pb2.FileFinderAction.Action.DOWNLOAD
        ),
        pathtype=jobs_pb2.PathSpec.PathType.OS,
        paths=["/quux/*"],
    )

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=file_finder.ClientFileFinder,
        flow_args=args,
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/quux/foo": b"Lorem ipsum.",
            "/quux/bar": b"Dolor sit amet.",
            "/quux/baz": b"Consectetur adipiscing elit.",
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    file_foo = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("quux", "foo"),
        ),
    )
    self.assertEqual(file_foo.read(), b"Lorem ipsum.")

    file_bar = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("quux", "bar"),
        ),
    )
    self.assertEqual(file_bar.read(), b"Dolor sit amet.")

    file_baz = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("quux", "baz"),
        ),
    )
    self.assertEqual(file_baz.read(), b"Consectetur adipiscing elit.")

  @db_test_lib.WithDatabase
  def testRRG_Download_RecursiveGlob(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.FileFinderArgs(
        action=flows_pb2.FileFinderAction(
            action_type=flows_pb2.FileFinderAction.Action.DOWNLOAD
        ),
        pathtype=jobs_pb2.PathSpec.PathType.OS,
        paths=["/**2"],
    )

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=file_finder.ClientFileFinder,
        flow_args=args,
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo": b"Lorem ipsum.",
            "/bar/quux": b"Dolor sit amet.",
            "/bar/norf": b"Consectetur adipiscing elit.",
            "/bar/thud/blargh": b"Sed do eiusmod.",
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    file_foo = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("foo",),
        ),
    )
    self.assertEqual(file_foo.read(), b"Lorem ipsum.")

    file_bar_quux = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("bar", "quux"),
        ),
    )
    self.assertEqual(file_bar_quux.read(), b"Dolor sit amet.")

    file_bar_norf = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("bar", "norf"),
        ),
    )
    self.assertEqual(file_bar_norf.read(), b"Consectetur adipiscing elit.")

    # This file is too deep, it should not be collected.
    with self.assertRaises(file_store.FileNotFoundError):
      file_store.OpenFile(
          db.ClientPath.OS(
              client_id=client_id,
              components=("bar", "thud", "blargh"),
          ),
      )

  @db_test_lib.WithDatabase
  def testRRG_Download_Oversized_Truncate(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.FileFinderArgs()
    args.pathtype = jobs_pb2.PathSpec.PathType.OS
    args.paths.append("/foo/bar")
    args.action.action_type = flows_pb2.FileFinderAction.Action.DOWNLOAD
    args.action.download.max_size = len(b"Lorem")
    args.action.download.oversized_file_policy = (
        flows_pb2.FileFinderDownloadActionOptions.DOWNLOAD_TRUNCATED
    )

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=file_finder.ClientFileFinder,
        flow_args=args,
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/bar": b"Lorem ipsum.",
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=8)
    self.assertLen(flow_results, 1)

    result = flows_pb2.FileFinderResult()
    self.assertTrue(flow_results[0].payload.Unpack(result))

    self.assertTrue(stat.S_ISREG(result.stat_entry.st_mode))
    self.assertEqual(result.stat_entry.st_size, len(b"Lorem ipsum."))  # pylint: disable=g-generic-assert
    self.assertEqual(
        result.hash_entry.md5,
        hashlib.md5(b"Lorem ipsum.").digest(),
    )
    self.assertEqual(
        result.hash_entry.sha1,
        hashlib.sha1(b"Lorem ipsum.").digest(),
    )
    self.assertEqual(
        result.hash_entry.sha256,
        hashlib.sha256(b"Lorem ipsum.").digest(),
    )

    file = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("foo", "bar"),
        ),
    )
    self.assertEqual(file.read(), b"Lorem")

  @db_test_lib.WithDatabase
  def testRRG_Download_Oversized_Skip(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.FileFinderArgs()
    args.pathtype = jobs_pb2.PathSpec.PathType.OS
    args.paths.append("/foo/bar")
    args.action.action_type = flows_pb2.FileFinderAction.Action.DOWNLOAD
    args.action.download.max_size = len(b"Lorem")
    args.action.download.oversized_file_policy = (
        flows_pb2.FileFinderDownloadActionOptions.SKIP
    )

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=file_finder.ClientFileFinder,
        flow_args=args,
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/bar": b"Lorem ipsum.",
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=8)
    self.assertLen(flow_results, 1)

    result = flows_pb2.FileFinderResult()
    self.assertTrue(flow_results[0].payload.Unpack(result))

    self.assertTrue(stat.S_ISREG(result.stat_entry.st_mode))
    self.assertEqual(result.stat_entry.st_size, len(b"Lorem ipsum."))  # pylint: disable=g-generic-assert
    self.assertEqual(
        result.hash_entry.md5,
        hashlib.md5(b"Lorem ipsum.").digest(),
    )
    self.assertEqual(
        result.hash_entry.sha1,
        hashlib.sha1(b"Lorem ipsum.").digest(),
    )
    self.assertEqual(
        result.hash_entry.sha256,
        hashlib.sha256(b"Lorem ipsum.").digest(),
    )

    # This file is too big, it should not be collected.
    with self.assertRaises(file_store.FileHasNoContentError):
      file_store.OpenFile(
          db.ClientPath.OS(
              client_id=client_id,
              components=("foo", "bar"),
          ),
      )

  @db_test_lib.WithDatabase
  def testRRG_PathsExcessive(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.FileFinderArgs(
        action=flows_pb2.FileFinderAction(
            action_type=flows_pb2.FileFinderAction.Action.STAT
        ),
        pathtype=jobs_pb2.PathSpec.PathType.OS,
        paths=["/*/*.txt"],
    )

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=file_finder.ClientFileFinder,
        flow_args=args,
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/bar.txt": b"",
            "/foo/bar.bin": b"",
            "/foo/baz.txt": b"",
            "/foo/baz.bin": b"",
            "/quux/norf.txt": b"",
            "/quux/thud.bin": b"",
            "/quux/blargh.txt": b"",
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=8)
    self.assertLen(flow_results, 4)

    results_by_path: dict[str, flows_pb2.FileFinderResult] = {}
    for flow_result in flow_results:
      result = flows_pb2.FileFinderResult()
      self.assertTrue(flow_result.payload.Unpack(result))

      results_by_path[result.stat_entry.pathspec.path] = result

    self.assertIn("/foo/bar.txt", results_by_path)
    self.assertIn("/foo/baz.txt", results_by_path)
    self.assertIn("/quux/norf.txt", results_by_path)
    self.assertIn("/quux/blargh.txt", results_by_path)

    self.assertNotIn("/foo/bar.bin", results_by_path)
    self.assertNotIn("/foo/baz.bin", results_by_path)
    self.assertNotIn("/quux/thud.bin", results_by_path)

  @db_test_lib.WithDatabase
  def testRRG_PathsMixed(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.FileFinderArgs(
        action=flows_pb2.FileFinderAction(
            action_type=flows_pb2.FileFinderAction.Action.STAT
        ),
        pathtype=jobs_pb2.PathSpec.PathType.OS,
        paths=["/*/*.txt", "/quux/thud.bin"],
    )

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=file_finder.ClientFileFinder,
        flow_args=args,
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/bar.txt": b"",
            "/foo/bar.bin": b"",
            "/foo/baz.txt": b"",
            "/foo/baz.bin": b"",
            "/quux/norf.txt": b"",
            "/quux/thud.bin": b"",
            "/quux/blargh.txt": b"",
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=8)
    # self.assertLen(flow_results, 5)

    results_by_path: dict[str, flows_pb2.FileFinderResult] = {}
    for flow_result in flow_results:
      result = flows_pb2.FileFinderResult()
      self.assertTrue(flow_result.payload.Unpack(result))

      results_by_path[result.stat_entry.pathspec.path] = result

    self.assertIn("/foo/bar.txt", results_by_path)
    self.assertIn("/foo/baz.txt", results_by_path)
    self.assertIn("/quux/norf.txt", results_by_path)
    self.assertIn("/quux/blargh.txt", results_by_path)
    self.assertIn("/quux/thud.bin", results_by_path)

    self.assertNotIn("/foo/bar.bin", results_by_path)
    self.assertNotIn("/foo/baz.bin", results_by_path)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
