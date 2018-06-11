#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests for the FileFinder flow."""

import collections
import glob
import hashlib
import os

from grr_response_client import vfs
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import file_finder as rdf_file_finder
from grr.lib.rdfvalues import paths as rdf_paths
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import flow
from grr.server.grr_response_server.aff4_objects import aff4_grr
from grr.server.grr_response_server.aff4_objects import standard as aff4_standard
# TODO(user):
# TestFileFinderFlow.testTreatsGlobsAsPathsWhenMemoryPathTypeIsUsed expects
# auditign system to work. Refactor and remove the unused import
# pylint: disable=unused-import
from grr.server.grr_response_server.flows.general import audit as _
# pylint: enable=unused-import
from grr.server.grr_response_server.flows.general import file_finder
from grr.test_lib import action_mocks
from grr.test_lib import client_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib

# pylint:mode=test


class FileFinderActionMock(action_mocks.FileFinderClientMock):

  def HandleMessage(self, message):
    responses = super(FileFinderActionMock, self).HandleMessage(message)

    predefined_values = {
        "auth.log": (1333333330, 1333333332, 1333333334),
        "dpkg.log": (1444444440, 1444444442, 1444444444),
        "dpkg_false.log": (1555555550, 1555555552, 1555555554)
    }

    processed_responses = []

    for response in responses:
      payload = response.payload
      if isinstance(payload, rdf_client.FindSpec):
        basename = payload.hit.pathspec.Basename()
        try:
          payload.hit.st_atime = predefined_values[basename][0]
          payload.hit.st_mtime = predefined_values[basename][1]
          payload.hit.st_ctime = predefined_values[basename][2]
          response.payload = payload
        except KeyError:
          pass
      processed_responses.append(response)

    return processed_responses


class TestFileFinderFlow(flow_test_lib.FlowTestsBaseclass):
  """Test the FileFinder flow."""

  def FileNameToURN(self, fname):
    return rdfvalue.RDFURN(self.client_id).Add("/fs/os").Add(
        os.path.join(self.base_path, "searching", fname))

  EXPECTED_HASHES = {
      "auth.log": ("67b8fc07bd4b6efc3b2dce322e8ddf609b540805",
                   "264eb6ff97fc6c37c5dd4b150cb0a797",
                   "91c8d6287a095a6fa6437dac50ffe3fe5c5e0d06dff"
                   "3ae830eedfce515ad6451"),
      "dpkg.log": ("531b1cfdd337aa1663f7361b2fd1c8fe43137f4a",
                   "26973f265ce5ecc1f86bc413e65bfc1d",
                   "48303a1e7ceec679f6d417b819f42779575ffe8eabf"
                   "9c880d286a1ee074d8145"),
      "dpkg_false.log": ("a2c9cc03c613a44774ae97ed6d181fe77c13e01b",
                         "ab48f3548f311c77e75ac69ac4e696df",
                         "a35aface4b45e3f1a95b0df24efc50e14fbedcaa6a7"
                         "50ba32358eaaffe3c4fb0")
  }

  def CheckFilesHashed(self, fnames):
    """Checks the returned hashes."""

    for fname in fnames:
      try:
        file_hashes = self.EXPECTED_HASHES[fname]
      except KeyError:
        raise RuntimeError("Can't check unexpected result for correct "
                           "hashes: %s" % fname)

      fd = aff4.FACTORY.Open(self.FileNameToURN(fname), token=self.token)

      hash_obj = fd.Get(fd.Schema.HASH)
      self.assertEqual(str(hash_obj.sha1), file_hashes[0])
      self.assertEqual(str(hash_obj.md5), file_hashes[1])
      self.assertEqual(str(hash_obj.sha256), file_hashes[2])

  def CheckFilesNotHashed(self, fnames):
    for fname in fnames:
      fd = aff4.FACTORY.Open(self.FileNameToURN(fname), token=self.token)
      self.assertIsNone(fd.Get(fd.Schema.HASH))

  def CheckFilesDownloaded(self, fnames):
    for fname in fnames:
      fd = aff4.FACTORY.Open(self.FileNameToURN(fname), token=self.token)
      self.assertGreater(fd.Get(fd.Schema.SIZE), 100)

  def CheckFilesNotDownloaded(self, fnames):
    for fname in fnames:
      fd = aff4.FACTORY.Open(self.FileNameToURN(fname), token=self.token)
      # Directories have no size attribute.
      if fd.Get(fd.Schema.TYPE) == aff4_standard.VFSDirectory:
        continue
      if fd.Schema.SIZE is not None:
        self.assertEqual(fd.Get(fd.Schema.SIZE), 0)

  def CheckFilesInCollection(self, fnames, session_id=None):
    session_id = session_id or self.last_session_id
    if fnames:
      # If results are expected, check that they are present in the collection.
      # Also check that there are no other files.
      output = flow.GRRFlow.ResultCollectionForFID(session_id)
      self.assertEqual(len(output), len(fnames))

      sorted_output = sorted(
          output,
          key=lambda x: x.stat_entry.AFF4Path(self.client_id).Basename())
      for fname, result in zip(sorted(fnames), sorted_output):
        self.assertTrue(isinstance(result, rdf_file_finder.FileFinderResult))
        self.assertEqual(
            result.stat_entry.AFF4Path(self.client_id).Basename(), fname)
    else:
      # No results expected.
      results = flow.GRRFlow.ResultCollectionForFID(session_id)
      self.assertEqual(len(results), 0)

  def CheckReplies(self, replies, action, expected_files):
    reply_count = 0
    for _, reply in replies:
      self.assertTrue(isinstance(reply, rdf_file_finder.FileFinderResult))

      reply_count += 1
      if action == rdf_file_finder.FileFinderAction.Action.STAT:
        self.assertTrue(reply.stat_entry)
        self.assertFalse(reply.hash_entry)
      elif action == rdf_file_finder.FileFinderAction.Action.DOWNLOAD:
        self.assertTrue(reply.stat_entry)
        self.assertTrue(reply.hash_entry)
      elif action == rdf_file_finder.FileFinderAction.Action.HASH:
        self.assertTrue(reply.stat_entry)
        self.assertTrue(reply.hash_entry)

      if action != rdf_file_finder.FileFinderAction.Action.STAT:
        # Check that file's hash is correct.
        file_basename = reply.stat_entry.pathspec.Basename()
        try:
          file_hashes = self.EXPECTED_HASHES[file_basename]
        except KeyError:
          raise RuntimeError("Can't check unexpected result for correct "
                             "hashes: %s" % file_basename)

        self.assertEqual(str(reply.hash_entry.sha1), file_hashes[0])
        self.assertEqual(str(reply.hash_entry.md5), file_hashes[1])
        self.assertEqual(str(reply.hash_entry.sha256), file_hashes[2])

    self.assertEqual(reply_count, len(expected_files))

  def RunFlow(self, paths=None, conditions=None, action=None):
    send_reply = test_lib.Instrument(flow.GRRFlow, "SendReply")
    with send_reply:
      self.last_session_id = flow_test_lib.TestFlowHelper(
          file_finder.FileFinder.__name__,
          self.client_mock,
          client_id=self.client_id,
          paths=paths or [self.path],
          pathtype=rdf_paths.PathSpec.PathType.OS,
          action=action,
          conditions=conditions,
          token=self.token)

    return send_reply.args

  def RunFlowAndCheckResults(
      self,
      conditions=None,
      action=rdf_file_finder.FileFinderAction.Action.STAT,
      expected_files=None,
      non_expected_files=None,
      paths=None):
    if not isinstance(action, rdf_file_finder.FileFinderAction):
      action = rdf_file_finder.FileFinderAction(action_type=action)
    action_type = action.action_type

    conditions = conditions or []
    expected_files = expected_files or []
    non_expected_files = non_expected_files or []

    for fname in expected_files + non_expected_files:
      aff4.FACTORY.Delete(self.FileNameToURN(fname), token=self.token)

    results = self.RunFlow(paths=paths, conditions=conditions, action=action)
    self.CheckReplies(results, action_type, expected_files)

    self.CheckFilesInCollection(expected_files)

    if action_type == rdf_file_finder.FileFinderAction.Action.STAT:
      self.CheckFilesNotDownloaded(expected_files + non_expected_files)
      self.CheckFilesNotHashed(expected_files + non_expected_files)
    elif action_type == rdf_file_finder.FileFinderAction.Action.DOWNLOAD:
      self.CheckFilesHashed(expected_files)
      self.CheckFilesNotHashed(non_expected_files)
      self.CheckFilesDownloaded(expected_files)
      self.CheckFilesNotDownloaded(non_expected_files)
      # Downloaded files are hashed to allow for deduping.
    elif action_type == rdf_file_finder.FileFinderAction.Action.HASH:
      self.CheckFilesNotDownloaded(expected_files + non_expected_files)
      self.CheckFilesHashed(expected_files)
      self.CheckFilesNotHashed(non_expected_files)

  def setUp(self):
    super(TestFileFinderFlow, self).setUp()
    self.client_mock = FileFinderActionMock()
    self.fixture_path = os.path.join(self.base_path, "searching")
    self.path = os.path.join(self.fixture_path, "*.log")
    self.client_id = self.SetupClient(0)

  def testFileFinderStatActionWithoutConditions(self):
    self.RunFlowAndCheckResults(
        action=rdf_file_finder.FileFinderAction.Action.STAT,
        expected_files=["auth.log", "dpkg.log", "dpkg_false.log"])

  def testFileFinderStat(self):
    files_to_check = [
        # Some files.
        "netgroup",
        "osx_fsdata",
        # Matches lsb-release, lsb-release-bad, lsb-release-notubuntu
        "lsb-release*",
        # Some directories.
        "a",
        "checks",
        "profiles"
    ]

    paths = [os.path.join(self.fixture_path, name) for name in files_to_check]
    expected_files = []
    for name in paths:
      for result in glob.glob(name):
        expected_files.append(self.FileNameToURN(os.path.basename(result)))

    # There was a bug in FileFinder with files/directories in the root dir.
    paths.append("/bin")
    expected_files.append(self.client_id.Add("fs/os/bin"))

    results = self.RunFlow(
        action=rdf_file_finder.FileFinderAction(
            action_type=rdf_file_finder.FileFinderAction.Action.STAT),
        paths=paths)

    stat_entries = [result[1].stat_entry for result in results]
    result_paths = [stat.AFF4Path(self.client_id) for stat in stat_entries]

    self.assertItemsEqual(expected_files, result_paths)

  FS_NODUMP_FL = 0x00000040
  FS_UNRM_FL = 0x00000002

  def testFileFinderStatExtFlags(self):
    with test_lib.AutoTempFilePath() as temp_filepath:
      client_test_lib.Chattr(temp_filepath, attrs=["+d"])

      action = rdf_file_finder.FileFinderAction.Stat()
      results = self.RunFlow(action=action, paths=[temp_filepath])
      self.assertEqual(len(results), 1)

      stat_entry = results[0][1].stat_entry
      self.assertTrue(stat_entry.st_flags_linux & self.FS_NODUMP_FL)
      self.assertFalse(stat_entry.st_flags_linux & self.FS_UNRM_FL)

  def testFileFinderStatExtAttrs(self):
    with test_lib.AutoTempFilePath() as temp_filepath:
      client_test_lib.SetExtAttr(temp_filepath, name="user.bar", value="baz")
      client_test_lib.SetExtAttr(temp_filepath, name="user.quux", value="norf")

      action = rdf_file_finder.FileFinderAction.Stat()
      results = self.RunFlow(action=action, paths=[temp_filepath])
      self.assertEqual(len(results), 1)

      stat_entry = results[0][1].stat_entry
      self.assertItemsEqual(stat_entry.ext_attrs, [
          rdf_client.ExtAttr(name="user.bar", value="baz"),
          rdf_client.ExtAttr(name="user.quux", value="norf"),
      ])

  def testFileFinderDownloadActionWithoutConditions(self):
    self.RunFlowAndCheckResults(
        action=rdf_file_finder.FileFinderAction.Action.DOWNLOAD,
        expected_files=["auth.log", "dpkg.log", "dpkg_false.log"])

  def testFileFinderHashActionWithoutConditions(self):
    self.RunFlowAndCheckResults(
        action=rdf_file_finder.FileFinderAction.Action.HASH,
        expected_files=["auth.log", "dpkg.log", "dpkg_false.log"])

  CONDITION_TESTS_ACTIONS = sorted(
      set(rdf_file_finder.FileFinderAction.Action.enum_dict.values()))

  def testLiteralMatchConditionWithDifferentActions(self):
    expected_files = ["auth.log"]
    non_expected_files = ["dpkg.log", "dpkg_false.log"]

    match = rdf_file_finder.FileFinderContentsLiteralMatchCondition(
        mode=rdf_file_finder.FileFinderContentsLiteralMatchCondition.Mode.
        ALL_HITS,
        bytes_before=10,
        bytes_after=10,
        literal="session opened for user dearjohn")
    literal_condition = rdf_file_finder.FileFinderCondition(
        condition_type=rdf_file_finder.FileFinderCondition.Type.
        CONTENTS_LITERAL_MATCH,
        contents_literal_match=match)

    for action in self.CONDITION_TESTS_ACTIONS:
      self.RunFlowAndCheckResults(
          action=action,
          conditions=[literal_condition],
          expected_files=expected_files,
          non_expected_files=non_expected_files)

      # Check that the results' matches fields are correctly filled.
      fd = flow.GRRFlow.ResultCollectionForFID(self.last_session_id)
      self.assertEqual(len(fd), 1)
      self.assertEqual(len(fd[0].matches), 1)
      self.assertEqual(fd[0].matches[0].offset, 350)
      self.assertEqual(fd[0].matches[0].data,
                       "session): session opened for user dearjohn by (uid=0")

  def testLiteralMatchConditionWithHexEncodedValue(self):
    match = rdf_file_finder.FileFinderContentsLiteralMatchCondition(
        mode=rdf_file_finder.FileFinderContentsLiteralMatchCondition.Mode.
        FIRST_HIT,
        bytes_before=10,
        bytes_after=10,
        literal="\x4D\x5A\x90")
    literal_condition = rdf_file_finder.FileFinderCondition(
        condition_type=rdf_file_finder.FileFinderCondition.Type.
        CONTENTS_LITERAL_MATCH,
        contents_literal_match=match)

    paths = [os.path.join(os.path.dirname(self.fixture_path), "hello.exe")]

    session_id = flow_test_lib.TestFlowHelper(
        file_finder.FileFinder.__name__,
        self.client_mock,
        client_id=self.client_id,
        paths=paths,
        pathtype=rdf_paths.PathSpec.PathType.OS,
        conditions=[literal_condition],
        token=self.token)

    # Check that the results' matches fields are correctly filled. Expecting a
    # match from hello.exe
    fd = flow.GRRFlow.ResultCollectionForFID(session_id)
    self.assertEqual(len(fd[0].matches), 1)
    self.assertEqual(fd[0].matches[0].offset, 0)
    self.assertEqual(fd[0].matches[0].data,
                     "MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff")

  def testRegexMatchConditionWithDifferentActions(self):
    expected_files = ["auth.log"]
    non_expected_files = ["dpkg.log", "dpkg_false.log"]

    regex_condition = rdf_file_finder.FileFinderCondition(
        condition_type=(
            rdf_file_finder.FileFinderCondition.Type.CONTENTS_REGEX_MATCH),
        contents_regex_match=(
            rdf_file_finder.FileFinderContentsRegexMatchCondition(
                mode="ALL_HITS",
                bytes_before=10,
                bytes_after=10,
                regex="session opened for user .*?john")))

    for action in self.CONDITION_TESTS_ACTIONS:
      self.RunFlowAndCheckResults(
          action=action,
          conditions=[regex_condition],
          expected_files=expected_files,
          non_expected_files=non_expected_files)

      fd = flow.GRRFlow.ResultCollectionForFID(self.last_session_id)
      self.assertEqual(len(fd), 1)
      self.assertEqual(len(fd[0].matches), 1)
      self.assertEqual(fd[0].matches[0].offset, 350)
      self.assertEqual(fd[0].matches[0].data,
                       "session): session opened for user dearjohn by (uid=0")

  def testTwoRegexMatchConditionsWithDifferentActions1(self):
    expected_files = ["auth.log"]
    non_expected_files = ["dpkg.log", "dpkg_false.log"]

    regex_condition1 = rdf_file_finder.FileFinderCondition(
        condition_type=(
            rdf_file_finder.FileFinderCondition.Type.CONTENTS_REGEX_MATCH),
        contents_regex_match=(
            rdf_file_finder.FileFinderContentsRegexMatchCondition(
                mode="ALL_HITS",
                bytes_before=10,
                bytes_after=10,
                regex="session opened for user .*?john")))
    regex_condition2 = rdf_file_finder.FileFinderCondition(
        condition_type=(
            rdf_file_finder.FileFinderCondition.Type.CONTENTS_REGEX_MATCH),
        contents_regex_match=(
            rdf_file_finder.FileFinderContentsRegexMatchCondition(
                mode="ALL_HITS",
                bytes_before=10,
                bytes_after=10,
                regex="format.*should")))

    for action in self.CONDITION_TESTS_ACTIONS:
      self.RunFlowAndCheckResults(
          action=action,
          conditions=[regex_condition1, regex_condition2],
          expected_files=expected_files,
          non_expected_files=non_expected_files)

      # Check the output file is created
      fd = flow.GRRFlow.ResultCollectionForFID(self.last_session_id)

      self.assertEqual(len(fd), 1)
      self.assertEqual(len(fd[0].matches), 2)
      self.assertEqual(fd[0].matches[0].offset, 350)
      self.assertEqual(fd[0].matches[0].data,
                       "session): session opened for user dearjohn by (uid=0")
      self.assertEqual(fd[0].matches[1].offset, 513)
      self.assertEqual(fd[0].matches[1].data,
                       "rong line format.... should not be he")

  def testTwoRegexMatchConditionsWithDifferentActions2(self):
    expected_files = ["auth.log"]
    non_expected_files = ["dpkg.log", "dpkg_false.log"]

    regex_condition1 = rdf_file_finder.FileFinderCondition(
        condition_type=(
            rdf_file_finder.FileFinderCondition.Type.CONTENTS_REGEX_MATCH),
        contents_regex_match=(
            rdf_file_finder.FileFinderContentsRegexMatchCondition(
                mode="ALL_HITS",
                bytes_before=10,
                bytes_after=10,
                regex="session opened for user .*?john")))
    regex_condition2 = rdf_file_finder.FileFinderCondition(
        condition_type=(
            rdf_file_finder.FileFinderCondition.Type.CONTENTS_REGEX_MATCH),
        contents_regex_match=(
            rdf_file_finder.FileFinderContentsRegexMatchCondition(
                mode="FIRST_HIT", bytes_before=10, bytes_after=10, regex=".*")))

    for action in self.CONDITION_TESTS_ACTIONS:
      self.RunFlowAndCheckResults(
          action=action,
          conditions=[regex_condition1, regex_condition2],
          expected_files=expected_files,
          non_expected_files=non_expected_files)

      fd = flow.GRRFlow.ResultCollectionForFID(self.last_session_id)

      self.assertEqual(len(fd), 1)
      self.assertEqual(len(fd[0].matches), 2)
      self.assertEqual(fd[0].matches[0].offset, 350)
      self.assertEqual(fd[0].matches[0].data,
                       "session): session opened for user dearjohn by (uid=0")
      self.assertEqual(fd[0].matches[1].offset, 0)
      self.assertEqual(fd[0].matches[1].length, 770)

  def testSizeConditionWithDifferentActions(self):
    expected_files = ["dpkg.log", "dpkg_false.log"]
    non_expected_files = ["auth.log"]

    sizes = [
        os.stat(os.path.join(self.fixture_path, f)).st_size
        for f in expected_files
    ]

    size_condition = rdf_file_finder.FileFinderCondition(
        condition_type=rdf_file_finder.FileFinderCondition.Type.SIZE,
        size=rdf_file_finder.FileFinderSizeCondition(
            max_file_size=max(sizes) + 1))

    for action in self.CONDITION_TESTS_ACTIONS:
      self.RunFlowAndCheckResults(
          action=action,
          conditions=[size_condition],
          expected_files=expected_files,
          non_expected_files=non_expected_files)

  def testDownloadAndHashActionSizeLimitWithSkipPolicy(self):
    expected_files = ["dpkg.log", "dpkg_false.log"]
    non_expected_files = ["auth.log"]
    sizes = [
        os.stat(os.path.join(self.fixture_path, f)).st_size
        for f in expected_files
    ]

    hash_action = rdf_file_finder.FileFinderAction.Hash(
        max_size=max(sizes) + 1, oversized_file_policy="SKIP")
    download_action = rdf_file_finder.FileFinderAction.Download(
        max_size=max(sizes) + 1, oversized_file_policy="SKIP")

    for action in [hash_action, download_action]:
      self.RunFlowAndCheckResults(
          paths=[self.path],
          action=action,
          expected_files=expected_files,
          non_expected_files=non_expected_files)

  def testDownloadAndHashActionSizeLimitWithHashTruncatedPolicy(self):
    image_path = os.path.join(self.base_path, "test_img.dd")
    # Read a bit more than a typical chunk (600 * 1024).
    expected_size = 750 * 1024

    hash_action = rdf_file_finder.FileFinderAction.Hash(
        max_size=expected_size, oversized_file_policy="HASH_TRUNCATED")
    download_action = rdf_file_finder.FileFinderAction.Download(
        max_size=expected_size, oversized_file_policy="HASH_TRUNCATED")

    for action in [hash_action, download_action]:
      results = self.RunFlow(paths=[image_path], action=action)

      urn = rdfvalue.RDFURN(self.client_id).Add("/fs/os").Add(image_path)
      vfs_file = aff4.FACTORY.Open(urn, token=self.token)
      # Make sure just a VFSFile got written.
      self.assertTrue(isinstance(vfs_file, aff4_grr.VFSFile))

      expected_data = open(image_path, "rb").read(expected_size)
      d = hashlib.sha1()
      d.update(expected_data)
      expected_hash = d.hexdigest()

      self.assertEqual(vfs_file.Get(vfs_file.Schema.HASH).sha1, expected_hash)

      unused_flow, flow_reply = results[0]
      self.assertEqual(flow_reply.hash_entry.sha1, expected_hash)

  def testDownloadActionSizeLimitWithDownloadTruncatedPolicy(self):
    image_path = os.path.join(self.base_path, "test_img.dd")
    # Read a bit more than a typical chunk (600 * 1024).
    expected_size = 750 * 1024

    action = rdf_file_finder.FileFinderAction.Download(
        max_size=expected_size, oversized_file_policy="DOWNLOAD_TRUNCATED")

    results = self.RunFlow(paths=[image_path], action=action)

    urn = rdfvalue.RDFURN(self.client_id).Add("/fs/os").Add(image_path)
    blobimage = aff4.FACTORY.Open(urn, token=self.token)
    # Make sure a VFSBlobImage got written.
    self.assertTrue(isinstance(blobimage, aff4_grr.VFSBlobImage))

    self.assertEqual(len(blobimage), expected_size)
    data = blobimage.read(100 * expected_size)
    self.assertEqual(len(data), expected_size)

    expected_data = open(image_path, "rb").read(expected_size)
    self.assertEqual(data, expected_data)
    hash_obj = blobimage.Get(blobimage.Schema.HASH)

    d = hashlib.sha1()
    d.update(expected_data)
    expected_hash = d.hexdigest()
    self.assertEqual(hash_obj.sha1, expected_hash)

    unused_flow, flow_reply = results[0]
    self.assertEqual(flow_reply.hash_entry.sha1, expected_hash)

  def testSizeAndRegexConditionsWithDifferentActions(self):
    files_over_size_limit = ["auth.log"]
    filtered_files = ["dpkg.log", "dpkg_false.log"]
    expected_files = []
    non_expected_files = files_over_size_limit + filtered_files

    sizes = [
        os.stat(os.path.join(self.fixture_path, f)).st_size
        for f in files_over_size_limit
    ]

    size_condition = rdf_file_finder.FileFinderCondition(
        condition_type=rdf_file_finder.FileFinderCondition.Type.SIZE,
        size=rdf_file_finder.FileFinderSizeCondition(
            max_file_size=min(sizes) - 1))

    regex_condition = rdf_file_finder.FileFinderCondition(
        condition_type=(
            rdf_file_finder.FileFinderCondition.Type.CONTENTS_REGEX_MATCH),
        contents_regex_match=rdf_file_finder.
        FileFinderContentsRegexMatchCondition(
            mode=(rdf_file_finder.FileFinderContentsRegexMatchCondition.Mode.
                  ALL_HITS),
            bytes_before=10,
            bytes_after=10,
            regex="session opened for user .*?john"))

    for action in self.CONDITION_TESTS_ACTIONS:
      self.RunFlowAndCheckResults(
          action=action,
          conditions=[size_condition, regex_condition],
          expected_files=expected_files,
          non_expected_files=non_expected_files)

    # Check that order of conditions doesn't influence results
    for action in self.CONDITION_TESTS_ACTIONS:
      self.RunFlowAndCheckResults(
          action=action,
          conditions=[regex_condition, size_condition],
          expected_files=expected_files,
          non_expected_files=non_expected_files)

  def testModificationTimeConditionWithDifferentActions(self):
    expected_files = ["dpkg.log", "dpkg_false.log"]
    non_expected_files = ["auth.log"]

    change_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1444444440)
    modification_time_condition = rdf_file_finder.FileFinderCondition(
        condition_type=rdf_file_finder.FileFinderCondition.Type.
        MODIFICATION_TIME,
        modification_time=rdf_file_finder.FileFinderModificationTimeCondition(
            min_last_modified_time=change_time))

    for action in self.CONDITION_TESTS_ACTIONS:
      self.RunFlowAndCheckResults(
          action=action,
          conditions=[modification_time_condition],
          expected_files=expected_files,
          non_expected_files=non_expected_files)

  def testAccessTimeConditionWithDifferentActions(self):
    expected_files = ["dpkg.log", "dpkg_false.log"]
    non_expected_files = ["auth.log"]

    change_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1444444440)
    access_time_condition = rdf_file_finder.FileFinderCondition(
        condition_type=rdf_file_finder.FileFinderCondition.Type.ACCESS_TIME,
        access_time=rdf_file_finder.FileFinderAccessTimeCondition(
            min_last_access_time=change_time))

    for action in self.CONDITION_TESTS_ACTIONS:
      self.RunFlowAndCheckResults(
          action=action,
          conditions=[access_time_condition],
          expected_files=expected_files,
          non_expected_files=non_expected_files)

  def testInodeChangeTimeConditionWithDifferentActions(self):
    expected_files = ["dpkg.log", "dpkg_false.log"]
    non_expected_files = ["auth.log"]

    change_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1444444440)
    inode_change_time_condition = rdf_file_finder.FileFinderCondition(
        condition_type=rdf_file_finder.FileFinderCondition.Type.
        INODE_CHANGE_TIME,
        inode_change_time=rdf_file_finder.FileFinderInodeChangeTimeCondition(
            min_last_inode_change_time=change_time))

    for action in self.CONDITION_TESTS_ACTIONS:
      self.RunFlowAndCheckResults(
          action=action,
          conditions=[inode_change_time_condition],
          expected_files=expected_files,
          non_expected_files=non_expected_files)

  def _RunTSKFileFinder(self, paths):

    image_path = os.path.join(self.base_path, "ntfs_img.dd")
    with utils.Stubber(
        vfs, "VFS_VIRTUALROOTS", {
            rdf_paths.PathSpec.PathType.TSK:
                rdf_paths.PathSpec(
                    path=image_path, pathtype="OS", offset=63 * 512)
        }):

      action = rdf_file_finder.FileFinderAction.Action.DOWNLOAD
      flow_test_lib.TestFlowHelper(
          file_finder.FileFinder.__name__,
          self.client_mock,
          client_id=self.client_id,
          paths=paths,
          pathtype=rdf_paths.PathSpec.PathType.TSK,
          action=rdf_file_finder.FileFinderAction(action_type=action),
          token=self.token)

  def testRecursiveADSHandling(self):
    """This tests some more obscure NTFS features - ADSs on directories."""
    self._RunTSKFileFinder(["adstest/**"])
    self._CheckDir()
    self._CheckSubdir()

  def testADSHandling(self):
    self._RunTSKFileFinder(["adstest/*"])
    self._CheckDir()

  def _CheckDir(self):
    output = self.client_id.Add("fs/tsk").Add(
        self.base_path).Add("ntfs_img.dd:63").Add("adstest")

    results = list(aff4.FACTORY.Open(output, token=self.token).OpenChildren())

    # There should be four entries:
    # one file, one directory, and one ADS for each.
    self.assertEqual(len(results), 4)

    counter = collections.Counter([type(x) for x in results])

    # There should be one directory and three files. It's important that all
    # ADSs have been created as files or we won't be able to access the data.
    self.assertEqual(counter[aff4_grr.VFSBlobImage], 3)
    self.assertEqual(counter[aff4_standard.VFSDirectory], 1)

    # Make sure we can access all the data.
    fd = aff4.FACTORY.Open(output.Add("a.txt"), token=self.token)
    self.assertEqual(fd.read(100), "This is a.txt")
    fd = aff4.FACTORY.Open(output.Add("a.txt:ads.txt"), token=self.token)
    self.assertEqual(fd.read(100), "This is the ads for a.txt")
    fd = aff4.FACTORY.Open(output.Add("dir:ads.txt"), token=self.token)
    self.assertEqual(fd.read(100), "This is the dir ads")

  def _CheckSubdir(self):
    # Also in the subdirectory.
    output = self.client_id.Add("fs/tsk").Add(
        self.base_path).Add("ntfs_img.dd:63").Add("adstest").Add("dir")
    fd = aff4.FACTORY.Open(output, token=self.token)
    results = list(fd.OpenChildren())

    # Here we have two files, one has an ads.
    self.assertEqual(len(results), 3)
    base_urn = fd.urn
    # Make sure we can access all the data.
    fd = aff4.FACTORY.Open(base_urn.Add("b.txt"), token=self.token)
    self.assertEqual(fd.read(100), "This is b.txt")
    fd = aff4.FACTORY.Open(base_urn.Add("b.txt:ads.txt"), token=self.token)
    self.assertEqual(fd.read(100), "This is the ads for b.txt")
    # This tests for a regression where ADS data attached to the base directory
    # leaked into files inside the directory.
    fd = aff4.FACTORY.Open(base_urn.Add("no_ads.txt"), token=self.token)
    self.assertEqual(fd.read(100), "This file has no ads")


class TestClientFileFinderFlow(flow_test_lib.FlowTestsBaseclass):
  """Test the ClientFileFinder flow."""

  def setUp(self):
    super(TestClientFileFinderFlow, self).setUp()
    self.client_id = self.SetupClient(0)

  def _RunCFF(self, paths, action):
    session_id = flow_test_lib.TestFlowHelper(
        file_finder.ClientFileFinder.__name__,
        action_mocks.ClientFileFinderClientMock(),
        client_id=self.client_id,
        paths=paths,
        pathtype=rdf_paths.PathSpec.PathType.OS,
        action=rdf_file_finder.FileFinderAction(action_type=action),
        process_non_regular_files=True,
        token=self.token)

    collection = flow.GRRFlow.ResultCollectionForFID(session_id)
    results = list(collection)
    return results

  def testClientFileFinder(self):
    paths = [os.path.join(self.base_path, "{**,.}/*.plist")]
    action = rdf_file_finder.FileFinderAction.Action.STAT
    results = self._RunCFF(paths, action)

    self.assertEqual(len(results), 4)
    relpaths = [
        os.path.relpath(p.stat_entry.pathspec.path, self.base_path)
        for p in results
    ]
    self.assertItemsEqual(relpaths, [
        "History.plist", "History.xml.plist", "test.plist",
        "parser_test/com.google.code.grr.plist"
    ])

  def testClientFileFinderPathCasing(self):
    paths = [
        os.path.join(self.base_path, "PARSER_TEST/*.plist"),
        os.path.join(self.base_path, "history.plist")
    ]
    action = rdf_file_finder.FileFinderAction.Action.STAT
    results = self._RunCFF(paths, action)
    self.assertEqual(len(results), 2)
    relpaths = [
        os.path.relpath(p.stat_entry.pathspec.path, self.base_path)
        for p in results
    ]
    self.assertItemsEqual(
        relpaths, ["History.plist", "parser_test/com.google.code.grr.plist"])

  def _SetupUnicodePath(self, path):
    try:
      dir_path = os.path.join(path, u"厨房")
      os.mkdir(dir_path)
    except UnicodeEncodeError:
      self.skipTest("Test needs a unicode capable file system.")

    file_path = os.path.join(dir_path, u"卫浴洁.txt")

    with open(utils.SmartStr(file_path), "wb") as f:
      f.write("hello world!")

  def testClientFileFinderUnicodeRegex(self):
    self._SetupUnicodePath(self.temp_dir)
    paths = [
        os.path.join(self.temp_dir, "*"),
        os.path.join(self.temp_dir, u"厨房/*.txt")
    ]
    action = rdf_file_finder.FileFinderAction.Action.STAT
    results = self._RunCFF(paths, action)
    self.assertEqual(len(results), 2)
    relpaths = [
        os.path.relpath(p.stat_entry.pathspec.path, self.temp_dir)
        for p in results
    ]
    self.assertItemsEqual(relpaths, [u"厨房", u"厨房/卫浴洁.txt"])

  def testClientFileFinderUnicodeLiteral(self):
    self._SetupUnicodePath(self.temp_dir)

    paths = [os.path.join(self.temp_dir, u"厨房/卫浴洁.txt")]
    action = rdf_file_finder.FileFinderAction.Action.STAT
    results = self._RunCFF(paths, action)
    self.assertEqual(len(results), 1)
    relpaths = [
        os.path.relpath(p.stat_entry.pathspec.path, self.temp_dir)
        for p in results
    ]
    self.assertItemsEqual(relpaths, [u"厨房/卫浴洁.txt"])

  def testPathInterpolation(self):
    self.client_id = self.SetupClient(0)

    bar = rdf_client.User(username="bar")
    baz = rdf_client.User(username="baz")
    kb = rdf_client.KnowledgeBase(os="foo", domain="norf", users=[bar, baz])

    client = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    with client:
      client.Set(client.Schema.KNOWLEDGE_BASE, kb)

    with test_lib.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      self._Touch(os.path.join(temp_dirpath, "foo", "bar"))
      self._Touch(os.path.join(temp_dirpath, "foo", "baz"))
      self._Touch(os.path.join(temp_dirpath, "foo", "quux"))
      self._Touch(os.path.join(temp_dirpath, "thud", "norf", "plugh"))
      self._Touch(os.path.join(temp_dirpath, "thud", "norf", "blargh"))

      paths = [
          os.path.join(temp_dirpath, "%%os%%", "%%users.username%%"),
          os.path.join(temp_dirpath, "thud", "%%domain%%", "plugh"),
      ]

      action = rdf_file_finder.FileFinderAction.Action.STAT
      results = self._RunCFF(paths, action)

      paths = [result.stat_entry.pathspec.path for result in results]
      self.assertItemsEqual(paths, [
          os.path.join(temp_dirpath, "foo", "bar"),
          os.path.join(temp_dirpath, "foo", "baz"),
          os.path.join(temp_dirpath, "thud", "norf", "plugh")
      ])

  # TODO(hanuszczak): Similar function can be found in other modules. It should
  # be implemented once in the test library.
  def _Touch(self, filepath):
    dirpath = os.path.dirname(filepath)
    if not os.path.exists(dirpath):
      os.makedirs(dirpath)

    with open(filepath, "wb"):
      pass


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
