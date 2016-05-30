#!/usr/bin/env python
"""Tests for the FileFinder flow."""



import collections
import glob
import os

from grr.client import vfs
from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import flags
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import collects
from grr.lib.aff4_objects import standard
from grr.lib.flows.general import file_finder
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths

# pylint:mode=test


class FileFinderActionMock(action_mocks.ActionMock):

  def __init__(self):
    super(FileFinderActionMock, self).__init__("Find", "TransferBuffer",
                                               "HashBuffer", "FingerprintFile",
                                               "HashFile", "Grep", "StatFile")

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


class TestFileFinderFlow(test_lib.FlowTestsBaseclass):
  """Test the FileFinder flow."""

  def FileNameToURN(self, fname):
    return rdfvalue.RDFURN(self.client_id).Add("/fs/os").Add(os.path.join(
        self.base_path, "searching", fname))

  def CheckFilesHashed(self, fnames):
    """Checks the returned hashes."""
    hashes = {
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

    for fname in fnames:
      try:
        file_hashes = hashes[fname]
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
      self.assertTrue(fd.Get(fd.Schema.SIZE) > 100)

  def CheckFilesNotDownloaded(self, fnames):
    for fname in fnames:
      fd = aff4.FACTORY.Open(self.FileNameToURN(fname), token=self.token)
      # Directories have no size attribute.
      if fd.Get(fd.Schema.TYPE) == standard.VFSDirectory:
        continue
      self.assertEqual(fd.Get(fd.Schema.SIZE), 0)

  def CheckFilesInCollection(self, fnames):
    if fnames:
      # If results are expected, check that they are present in the collection.
      # Also check that there are no other files.
      output = aff4.FACTORY.Open(
          self.client_id.Add(self.output_path),
          aff4_type=collects.RDFValueCollection,
          token=self.token)
      self.assertEqual(len(output), len(fnames))

      sorted_output = sorted(output,
                             key=lambda x: x.stat_entry.aff4path.Basename())
      for fname, result in zip(sorted(fnames), sorted_output):
        self.assertTrue(isinstance(result, file_finder.FileFinderResult))
        self.assertEqual(result.stat_entry.aff4path.Basename(), fname)
    else:
      # If no results are expected, collection shouldn't be created.
      self.assertRaises(aff4.InstantiationError,
                        aff4.FACTORY.Open,
                        self.client_id.Add(self.output_path),
                        aff4_type=collects.RDFValueCollection,
                        token=self.token)

  def CheckReplies(self, replies, action, expected_files):
    reply_count = 0
    for _, reply in replies:
      if isinstance(reply, file_finder.FileFinderResult):
        reply_count += 1
        if action == file_finder.FileFinderAction.Action.STAT:
          self.assertTrue(reply.stat_entry)
          self.assertFalse(reply.hash_entry)
        elif action == file_finder.FileFinderAction.Action.DOWNLOAD:
          self.assertTrue(reply.stat_entry)
          self.assertTrue(reply.hash_entry)
        elif action == file_finder.FileFinderAction.Action.HASH:
          self.assertTrue(reply.stat_entry)
          self.assertTrue(reply.hash_entry)
    self.assertEqual(reply_count, len(expected_files))

  def RunFlow(self,
              paths=None,
              conditions=None,
              action=file_finder.FileFinderAction.Action.STAT):
    send_reply = test_lib.Instrument(flow.GRRFlow, "SendReply")
    with send_reply:
      for _ in test_lib.TestFlowHelper("FileFinder",
                                       self.client_mock,
                                       client_id=self.client_id,
                                       paths=paths or [self.path],
                                       pathtype=rdf_paths.PathSpec.PathType.OS,
                                       action=file_finder.FileFinderAction(
                                           action_type=action),
                                       conditions=conditions,
                                       token=self.token,
                                       output=self.output_path):
        pass

    return send_reply.args

  def RunFlowAndCheckResults(self,
                             conditions=None,
                             action=file_finder.FileFinderAction.Action.STAT,
                             expected_files=None,
                             non_expected_files=None,
                             paths=None):

    conditions = conditions or []
    expected_files = expected_files or []
    non_expected_files = non_expected_files or []

    for fname in expected_files + non_expected_files:
      aff4.FACTORY.Delete(self.FileNameToURN(fname), token=self.token)

      results = self.RunFlow(paths=paths, conditions=conditions, action=action)
      self.CheckReplies(results, action, expected_files)

    self.CheckFilesInCollection(expected_files)

    if action == file_finder.FileFinderAction.Action.STAT:
      self.CheckFilesNotDownloaded(expected_files + non_expected_files)
      self.CheckFilesNotHashed(expected_files + non_expected_files)
    elif action == file_finder.FileFinderAction.Action.DOWNLOAD:
      self.CheckFilesDownloaded(expected_files)
      self.CheckFilesNotDownloaded(non_expected_files)
      # Downloaded files are hashed to allow for deduping.
    elif action == file_finder.FileFinderAction.Action.HASH:
      self.CheckFilesNotDownloaded(expected_files + non_expected_files)
      self.CheckFilesHashed(expected_files)
      self.CheckFilesNotHashed(non_expected_files)

  def setUp(self):
    super(TestFileFinderFlow, self).setUp()
    self.output_path = "analysis/file_finder"
    self.client_mock = FileFinderActionMock()
    self.fixture_path = os.path.join(self.base_path, "searching")
    self.path = os.path.join(self.fixture_path, "*.log")

  def testFileFinderStatActionWithoutConditions(self):
    self.RunFlowAndCheckResults(
        action=file_finder.FileFinderAction.Action.STAT,
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

    results = self.RunFlow(action=file_finder.FileFinderAction.Action.STAT,
                           paths=paths)

    stat_entries = [result[1].stat_entry for result in results]
    result_paths = [stat.aff4path for stat in stat_entries]

    self.assertItemsEqual(expected_files, result_paths)

  def testFileFinderDownloadActionWithoutConditions(self):
    self.RunFlowAndCheckResults(
        action=file_finder.FileFinderAction.Action.DOWNLOAD,
        expected_files=["auth.log", "dpkg.log", "dpkg_false.log"])

  def testFileFinderHashActionWithoutConditions(self):
    self.RunFlowAndCheckResults(
        action=file_finder.FileFinderAction.Action.HASH,
        expected_files=["auth.log", "dpkg.log", "dpkg_false.log"])

  def testLiteralMatchConditionWithDifferentActions(self):
    expected_files = ["auth.log"]
    non_expected_files = ["dpkg.log", "dpkg_false.log"]

    match = file_finder.FileFinderContentsLiteralMatchCondition(
        mode=file_finder.FileFinderContentsLiteralMatchCondition.Mode.ALL_HITS,
        bytes_before=10,
        bytes_after=10,
        literal="session opened for user dearjohn")
    literal_condition = file_finder.FileFinderCondition(
        condition_type=file_finder.FileFinderCondition.Type.
        CONTENTS_LITERAL_MATCH,
        contents_literal_match=match)

    for action in sorted(file_finder.FileFinderAction.Action.enum_dict.values(
    )):
      self.RunFlowAndCheckResults(action=action,
                                  conditions=[literal_condition],
                                  expected_files=expected_files,
                                  non_expected_files=non_expected_files)

      # Check that the results' matches fields are correctly filled.
      fd = aff4.FACTORY.Open(
          self.client_id.Add(self.output_path),
          aff4_type=collects.RDFValueCollection,
          token=self.token)
      self.assertEqual(len(fd), 1)
      self.assertEqual(len(fd[0].matches), 1)
      self.assertEqual(fd[0].matches[0].offset, 350)
      self.assertEqual(fd[0].matches[0].data,
                       "session): session opened for user dearjohn by (uid=0")

  def testLiteralMatchConditionWithHexEncodedValue(self):
    match = file_finder.FileFinderContentsLiteralMatchCondition(
        mode=file_finder.FileFinderContentsLiteralMatchCondition.Mode.FIRST_HIT,
        bytes_before=10,
        bytes_after=10,
        literal="\x4D\x5A\x90")
    literal_condition = file_finder.FileFinderCondition(
        condition_type=file_finder.FileFinderCondition.Type.
        CONTENTS_LITERAL_MATCH,
        contents_literal_match=match)

    paths = [os.path.join(os.path.dirname(self.fixture_path), "hello.exe")]

    for _ in test_lib.TestFlowHelper("FileFinder",
                                     self.client_mock,
                                     client_id=self.client_id,
                                     paths=paths,
                                     pathtype=rdf_paths.PathSpec.PathType.OS,
                                     conditions=[literal_condition],
                                     token=self.token,
                                     output=self.output_path):
      pass

    # Check that the results' matches fields are correctly filled. Expecting a
    # match from hello.exe
    fd = aff4.FACTORY.Open(
        self.client_id.Add(self.output_path),
        aff4_type=collects.RDFValueCollection,
        token=self.token)
    self.assertEqual(len(fd[0].matches), 1)
    self.assertEqual(fd[0].matches[0].offset, 0)
    self.assertEqual(fd[0].matches[0].data,
                     "MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff")

  def testRegexMatchConditionWithDifferentActions(self):
    expected_files = ["auth.log"]
    non_expected_files = ["dpkg.log", "dpkg_false.log"]

    regex_condition = file_finder.FileFinderCondition(
        condition_type=(
            file_finder.FileFinderCondition.Type.CONTENTS_REGEX_MATCH),
        contents_regex_match=file_finder.FileFinderContentsRegexMatchCondition(
            mode=(
                file_finder.FileFinderContentsRegexMatchCondition.Mode.ALL_HITS
            ),
            bytes_before=10,
            bytes_after=10,
            regex="session opened for user .*?john"))

    for action in sorted(file_finder.FileFinderAction.Action.enum_dict.values(
    )):
      self.RunFlowAndCheckResults(action=action,
                                  conditions=[regex_condition],
                                  expected_files=expected_files,
                                  non_expected_files=non_expected_files)

      fd = aff4.FACTORY.Open(
          self.client_id.Add(self.output_path),
          aff4_type=collects.RDFValueCollection,
          token=self.token)
      self.assertEqual(len(fd), 1)
      self.assertEqual(len(fd[0].matches), 1)
      self.assertEqual(fd[0].matches[0].offset, 350)
      self.assertEqual(fd[0].matches[0].data,
                       "session): session opened for user dearjohn by (uid=0")

  def testTwoRegexMatchConditionsWithDifferentActions1(self):
    expected_files = ["auth.log"]
    non_expected_files = ["dpkg.log", "dpkg_false.log"]

    regex_condition1 = file_finder.FileFinderCondition(
        condition_type=(
            file_finder.FileFinderCondition.Type.CONTENTS_REGEX_MATCH),
        contents_regex_match=file_finder.FileFinderContentsRegexMatchCondition(
            mode=(
                file_finder.FileFinderContentsRegexMatchCondition.Mode.ALL_HITS
            ),
            bytes_before=10,
            bytes_after=10,
            regex="session opened for user .*?john"))
    regex_condition2 = file_finder.FileFinderCondition(
        condition_type=(
            file_finder.FileFinderCondition.Type.CONTENTS_REGEX_MATCH),
        contents_regex_match=file_finder.FileFinderContentsRegexMatchCondition(
            mode=(
                file_finder.FileFinderContentsRegexMatchCondition.Mode.ALL_HITS
            ),
            bytes_before=10,
            bytes_after=10,
            regex="format.*should"))

    for action in sorted(file_finder.FileFinderAction.Action.enum_dict.values(
    )):
      self.RunFlowAndCheckResults(
          action=action,
          conditions=[regex_condition1, regex_condition2],
          expected_files=expected_files,
          non_expected_files=non_expected_files)

      # Check the output file is created
      fd = aff4.FACTORY.Open(
          self.client_id.Add(self.output_path),
          aff4_type=collects.RDFValueCollection,
          token=self.token)

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

    regex_condition1 = file_finder.FileFinderCondition(
        condition_type=(
            file_finder.FileFinderCondition.Type.CONTENTS_REGEX_MATCH),
        contents_regex_match=file_finder.FileFinderContentsRegexMatchCondition(
            mode=(
                file_finder.FileFinderContentsRegexMatchCondition.Mode.ALL_HITS
            ),
            bytes_before=10,
            bytes_after=10,
            regex="session opened for user .*?john"))
    regex_condition2 = file_finder.FileFinderCondition(
        condition_type=(
            file_finder.FileFinderCondition.Type.CONTENTS_REGEX_MATCH),
        contents_regex_match=file_finder.FileFinderContentsRegexMatchCondition(
            mode=file_finder.FileFinderContentsRegexMatchCondition.Mode.
            FIRST_HIT,
            bytes_before=10,
            bytes_after=10,
            regex=".*"))

    for action in sorted(file_finder.FileFinderAction.Action.enum_dict.values(
    )):
      self.RunFlowAndCheckResults(
          action=action,
          conditions=[regex_condition1, regex_condition2],
          expected_files=expected_files,
          non_expected_files=non_expected_files)

      # Check the output file is created
      fd = aff4.FACTORY.Open(
          self.client_id.Add(self.output_path),
          aff4_type=collects.RDFValueCollection,
          token=self.token)

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

    sizes = [os.stat(os.path.join(self.fixture_path, f)).st_size
             for f in expected_files]

    size_condition = file_finder.FileFinderCondition(
        condition_type=file_finder.FileFinderCondition.Type.SIZE,
        size=file_finder.FileFinderSizeCondition(max_file_size=max(sizes) + 1))

    for action in sorted(file_finder.FileFinderAction.Action.enum_dict.values(
    )):
      self.RunFlowAndCheckResults(action=action,
                                  conditions=[size_condition],
                                  expected_files=expected_files,
                                  non_expected_files=non_expected_files)

  def testDownloadActionSizeLimit(self):
    expected_files = ["dpkg.log", "dpkg_false.log"]
    non_expected_files = ["auth.log"]

    sizes = [os.stat(os.path.join(self.fixture_path, f)).st_size
             for f in expected_files]

    action = file_finder.FileFinderAction(
        action_type=file_finder.FileFinderAction.Action.DOWNLOAD)
    action.download.max_size = max(sizes) + 1

    for _ in test_lib.TestFlowHelper("FileFinder",
                                     self.client_mock,
                                     client_id=self.client_id,
                                     paths=[self.path],
                                     pathtype=rdf_paths.PathSpec.PathType.OS,
                                     action=action,
                                     token=self.token,
                                     output=self.output_path):
      pass

    self.CheckFilesDownloaded(expected_files)
    self.CheckFilesNotDownloaded(non_expected_files)
    # Even though the file is too big to download, we still want the
    # hash.
    self.CheckFilesHashed(non_expected_files)

  def testSizeAndRegexConditionsWithDifferentActions(self):
    files_over_size_limit = ["auth.log"]
    filtered_files = ["dpkg.log", "dpkg_false.log"]
    expected_files = []
    non_expected_files = files_over_size_limit + filtered_files

    sizes = [os.stat(os.path.join(self.fixture_path, f)).st_size
             for f in files_over_size_limit]

    size_condition = file_finder.FileFinderCondition(
        condition_type=file_finder.FileFinderCondition.Type.SIZE,
        size=file_finder.FileFinderSizeCondition(max_file_size=min(sizes) - 1))

    regex_condition = file_finder.FileFinderCondition(
        condition_type=(
            file_finder.FileFinderCondition.Type.CONTENTS_REGEX_MATCH),
        contents_regex_match=file_finder.FileFinderContentsRegexMatchCondition(
            mode=(
                file_finder.FileFinderContentsRegexMatchCondition.Mode.ALL_HITS
            ),
            bytes_before=10,
            bytes_after=10,
            regex="session opened for user .*?john"))

    for action in sorted(file_finder.FileFinderAction.Action.enum_dict.values(
    )):
      self.RunFlowAndCheckResults(action=action,
                                  conditions=[size_condition, regex_condition],
                                  expected_files=expected_files,
                                  non_expected_files=non_expected_files)

    # Check that order of conditions doesn't influence results
    for action in sorted(file_finder.FileFinderAction.Action.enum_dict.values(
    )):
      self.RunFlowAndCheckResults(action=action,
                                  conditions=[regex_condition, size_condition],
                                  expected_files=expected_files,
                                  non_expected_files=non_expected_files)

  def testModificationTimeConditionWithDifferentActions(self):
    expected_files = ["dpkg.log", "dpkg_false.log"]
    non_expected_files = ["auth.log"]

    change_time = rdfvalue.RDFDatetime().FromSecondsFromEpoch(1444444440)
    modification_time_condition = file_finder.FileFinderCondition(
        condition_type=file_finder.FileFinderCondition.Type.MODIFICATION_TIME,
        modification_time=file_finder.FileFinderModificationTimeCondition(
            min_last_modified_time=change_time))

    for action in sorted(file_finder.FileFinderAction.Action.enum_dict.values(
    )):
      self.RunFlowAndCheckResults(action=action,
                                  conditions=[modification_time_condition],
                                  expected_files=expected_files,
                                  non_expected_files=non_expected_files)

  def testAccessTimeConditionWithDifferentActions(self):
    expected_files = ["dpkg.log", "dpkg_false.log"]
    non_expected_files = ["auth.log"]

    change_time = rdfvalue.RDFDatetime().FromSecondsFromEpoch(1444444440)
    access_time_condition = file_finder.FileFinderCondition(
        condition_type=file_finder.FileFinderCondition.Type.ACCESS_TIME,
        access_time=file_finder.FileFinderAccessTimeCondition(
            min_last_access_time=change_time))

    for action in sorted(file_finder.FileFinderAction.Action.enum_dict.values(
    )):
      self.RunFlowAndCheckResults(action=action,
                                  conditions=[access_time_condition],
                                  expected_files=expected_files,
                                  non_expected_files=non_expected_files)

  def testInodeChangeTimeConditionWithDifferentActions(self):
    expected_files = ["dpkg.log", "dpkg_false.log"]
    non_expected_files = ["auth.log"]

    change_time = rdfvalue.RDFDatetime().FromSecondsFromEpoch(1444444440)
    inode_change_time_condition = file_finder.FileFinderCondition(
        condition_type=file_finder.FileFinderCondition.Type.INODE_CHANGE_TIME,
        inode_change_time=file_finder.FileFinderInodeChangeTimeCondition(
            min_last_inode_change_time=change_time))

    for action in sorted(file_finder.FileFinderAction.Action.enum_dict.values(
    )):
      self.RunFlowAndCheckResults(action=action,
                                  conditions=[inode_change_time_condition],
                                  expected_files=expected_files,
                                  non_expected_files=non_expected_files)

  def testTreatsGlobsAsPathsWhenMemoryPathTypeIsUsed(self):
    # No need to setup VFS handlers as we're not actually looking at the files,
    # as there's no condition/action specified.

    paths = [os.path.join(
        os.path.dirname(self.fixture_path), "*.log"), os.path.join(
            os.path.dirname(self.fixture_path), "auth.log")]

    for _ in test_lib.TestFlowHelper(
        "FileFinder",
        self.client_mock,
        client_id=self.client_id,
        paths=paths,
        pathtype=rdf_paths.PathSpec.PathType.MEMORY,
        token=self.token,
        output=self.output_path):
      pass

    # Both auth.log and *.log should be present, because we don't apply
    # any conditions and by default FileFinder treats given paths as paths
    # to memory devices when using PathType=MEMORY. So checking
    # files existence doesn't make much sense.
    self.CheckFilesInCollection(["*.log", "auth.log"])

  def testAppliesLiteralConditionWhenMemoryPathTypeIsUsed(self):
    with test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                               test_lib.FakeTestDataVFSHandler):
      with test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.MEMORY,
                                 test_lib.FakeTestDataVFSHandler):
        paths = ["/var/log/auth.log", "/etc/ssh/sshd_config"]

        literal_condition = file_finder.FileFinderContentsLiteralMatchCondition
        all_hits = literal_condition.Mode.ALL_HITS
        literal_condition = file_finder.FileFinderCondition(
            condition_type=file_finder.FileFinderCondition.Type.
            CONTENTS_LITERAL_MATCH,
            contents_literal_match=literal_condition(
                mode=all_hits,
                bytes_before=10,
                bytes_after=10,
                literal="session opened for user dearjohn"))

        # Check this condition with all the actions. This makes sense, as we may
        # download memeory or send it to the socket.
        for action in sorted(
            file_finder.FileFinderAction.Action.enum_dict.values()):
          for _ in test_lib.TestFlowHelper(
              "FileFinder",
              self.client_mock,
              client_id=self.client_id,
              paths=paths,
              pathtype=rdf_paths.PathSpec.PathType.MEMORY,
              conditions=[literal_condition],
              action=file_finder.FileFinderAction(action_type=action),
              token=self.token,
              output=self.output_path):
            pass

          self.CheckFilesInCollection(["auth.log"])

          fd = aff4.FACTORY.Open(
              self.client_id.Add(self.output_path),
              aff4_type=collects.RDFValueCollection,
              token=self.token)
          self.assertEqual(fd[0].stat_entry.pathspec.CollapsePath(), paths[0])
          self.assertEqual(len(fd), 1)
          self.assertEqual(len(fd[0].matches), 1)
          self.assertEqual(fd[0].matches[0].offset, 350)
          self.assertEqual(
              fd[0].matches[0].data,
              "session): session opened for user dearjohn by (uid=0")

  def _RunTSKFileFinder(self, paths):

    image_path = os.path.join(self.base_path, "ntfs_img.dd")
    with utils.Stubber(vfs,
                       "VFS_VIRTUALROOTS",
                       {
                           rdf_paths.PathSpec.PathType.TSK: rdf_paths.PathSpec(
                               path=image_path,
                               pathtype="OS",
                               offset=63 * 512)
                       }):

      action = file_finder.FileFinderAction.Action.DOWNLOAD
      for _ in test_lib.TestFlowHelper("FileFinder",
                                       self.client_mock,
                                       client_id=self.client_id,
                                       paths=paths,
                                       pathtype=rdf_paths.PathSpec.PathType.TSK,
                                       action=file_finder.FileFinderAction(
                                           action_type=action),
                                       token=self.token):
        pass

  def testRecursiveADSHandling(self):
    """This tests some more obscure NTFS features - ADSs on directories."""
    self._RunTSKFileFinder(["adstest/**"])
    self._CheckDir()
    self._CheckSubdir()

  def testADSHandling(self):
    self._RunTSKFileFinder(["adstest/*"])
    self._CheckDir()

  def _CheckDir(self):
    output = self.client_id.Add("fs/tsk").Add(self.base_path).Add(
        "ntfs_img.dd:63").Add("adstest")

    results = list(aff4.FACTORY.Open(output, token=self.token).OpenChildren())

    # There should be four entries:
    # one file, one directory, and one ADS for each.
    self.assertEqual(len(results), 4)

    counter = collections.Counter([type(x) for x in results])

    # There should be one directory and three files. It's important that all
    # ADSs have been created as files or we won't be able to access the data.
    self.assertEqual(counter[aff4_grr.VFSBlobImage], 3)
    self.assertEqual(counter[standard.VFSDirectory], 1)

    # Make sure we can access all the data.
    fd = aff4.FACTORY.Open(output.Add("a.txt"), token=self.token)
    self.assertEqual(fd.read(100), "This is a.txt")
    fd = aff4.FACTORY.Open(output.Add("a.txt:ads.txt"), token=self.token)
    self.assertEqual(fd.read(100), "This is the ads for a.txt")
    fd = aff4.FACTORY.Open(output.Add("dir:ads.txt"), token=self.token)
    self.assertEqual(fd.read(100), "This is the dir ads")

  def _CheckSubdir(self):
    # Also in the subdirectory.
    output = self.client_id.Add("fs/tsk").Add(self.base_path).Add(
        "ntfs_img.dd:63").Add("adstest").Add("dir")
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


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
