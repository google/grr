#!/usr/bin/env python
"""Tests the client file finder action."""

import collections
import glob
import hashlib
import io
import os
import shutil
import stat
from unittest import mock
import zlib

from absl import app

from grr_response_client.client_actions import file_finder as client_file_finder
from grr_response_client.client_actions.file_finder_utils import globbing
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.util import temp
from grr.test_lib import client_test_lib
from grr.test_lib import filesystem_test_lib
from grr.test_lib import test_lib
from grr.test_lib import worker_mocks

# TODO(hanuszczak): This test suite is very bad, it needs to be rewritten.


class FileFinderTest(client_test_lib.EmptyActionTest):

  def setUp(self):
    super().setUp()
    self.stat_action = rdf_file_finder.FileFinderAction.Stat()

  def _GetRelativeResults(self, raw_results, base_path=None):
    base_path = base_path or self.base_path
    return [
        result.stat_entry.pathspec.path[len(base_path) + 1:]
        for result in raw_results
    ]

  def _RunFileFinder(self,
                     paths,
                     action,
                     conditions=None,
                     follow_links=True,
                     process_non_regular_files=True,
                     **kw):
    return self.RunAction(
        client_file_finder.FileFinderOS,
        arg=rdf_file_finder.FileFinderArgs(
            paths=paths,
            action=action,
            conditions=conditions,
            process_non_regular_files=process_non_regular_files,
            follow_links=follow_links,
            **kw))

  def testFileFinder(self):
    paths = [self.base_path + "/*"]
    results = self._RunFileFinder(paths, self.stat_action)
    self.assertEqual(
        self._GetRelativeResults(results), os.listdir(self.base_path))

    profiles_path = os.path.join(self.base_path, "profiles/v1.0")
    paths = [os.path.join(self.base_path, "profiles/v1.0") + "/*"]
    results = self._RunFileFinder(paths, self.stat_action)
    self.assertEqual(
        self._GetRelativeResults(results, base_path=profiles_path),
        os.listdir(profiles_path))

  def testNonExistentPath(self):
    paths = [self.base_path + "/does/not/exist/**"]
    results = self._RunFileFinder(paths, self.stat_action)
    self.assertEmpty(results)

  def testRecursiveGlobCallsProgressWithoutMatches(self):
    paths = [self.base_path + "/**4/nonexistent"]

    progress = mock.MagicMock()

    with mock.patch.object(client_file_finder.FileFinderOS, "Progress",
                           progress):
      results = self._RunFileFinder(paths, self.stat_action)
    self.assertEmpty(results)

    # progress.call_count should rise linearly to the number of files and
    # folders in the test data folder. At the time of writing test data contains
    # 140 files and folders. progress is called 135 times.
    self.assertGreater(progress.call_count, 100)

  def testRecursiveGlob(self):
    paths = [self.base_path + "/**3"]
    results = self._RunFileFinder(paths, self.stat_action)
    relative_results = self._GetRelativeResults(results)
    self.assertIn("a/b", relative_results)
    self.assertIn("a/b/c", relative_results)
    self.assertIn("a/b/d", relative_results)
    self.assertNotIn("a/b/c/helloc.txt", relative_results)
    self.assertNotIn("a/b/d/hellod.txt", relative_results)

    paths = [self.base_path + "/**4"]
    results = self._RunFileFinder(paths, self.stat_action)
    relative_results = self._GetRelativeResults(results)
    self.assertIn("a/b", relative_results)
    self.assertIn("a/b/c", relative_results)
    self.assertIn("a/b/d", relative_results)
    self.assertIn("a/b/c/helloc.txt", relative_results)
    self.assertIn("a/b/d/hellod.txt", relative_results)

  def testRegexGlob(self):
    paths = [self.base_path + "/valid_win_mbr*.gz"]
    results = self._RunFileFinder(paths, self.stat_action)
    relative_results = self._GetRelativeResults(results)
    for glob_result in glob.glob(self.base_path + "/valid_win_mbr*gz"):
      self.assertIn(os.path.basename(glob_result), relative_results)

  def testRecursiveRegexGlob(self):
    paths = [self.base_path + "/**3/*.gz"]
    results = self._RunFileFinder(paths, self.stat_action)
    relative_results = self._GetRelativeResults(results)
    self.assertIn("profiles/v1.0/nt/index.gz", relative_results)
    self.assertIn("bigquery/ExportedFile.json.gz", relative_results)
    for r in relative_results:
      self.assertEqual(os.path.splitext(r)[1], ".gz")

    paths = [self.base_path + "/**2/*.gz"]
    results = self._RunFileFinder(paths, self.stat_action)
    relative_results = self._GetRelativeResults(results)
    self.assertNotIn("profiles/v1.0/nt/index.gz", relative_results)
    self.assertIn("bigquery/ExportedFile.json.gz", relative_results)
    for r in relative_results:
      self.assertEqual(os.path.splitext(r)[1], ".gz")

  def testDoubleRecursionFails(self):
    paths = [self.base_path + "/**/**/test.exe"]
    with self.assertRaises(ValueError):
      self._RunFileFinder(paths, self.stat_action)

  def testInvalidInput(self):
    paths = [self.base_path + "/r**z"]
    with self.assertRaises(ValueError):
      self._RunFileFinder(paths, self.stat_action)

    paths = [self.base_path + "/**.exe"]
    with self.assertRaises(ValueError):
      self._RunFileFinder(paths, self.stat_action)

    paths = [self.base_path + "/test**"]
    with self.assertRaises(ValueError):
      self._RunFileFinder(paths, self.stat_action)

  def testGroupings(self):
    paths = [self.base_path + "/a/b/{c,d}/hello*"]
    results = self._RunFileFinder(paths, self.stat_action)
    relative_results = self._GetRelativeResults(results)
    self.assertIn("a/b/c/helloc.txt", relative_results)
    self.assertIn("a/b/d/hellod.txt", relative_results)

    paths = [self.base_path + "/a/b/*/hello{c,d}.txt"]
    results = self._RunFileFinder(paths, self.stat_action)
    relative_results = self._GetRelativeResults(results)
    self.assertIn("a/b/c/helloc.txt", relative_results)
    self.assertIn("a/b/d/hellod.txt", relative_results)

  def testLinksAndContent(self):
    try:
      # This sets up a structure as follows:
      # <file> tmp_dir/lnk_test/lnk_target/contents
      # <dir>  tmp_dir/lnk_test/lnk_target
      # <lnk>  tmp_dir/lnk_test/lnk

      # lnk is a symbolic link to lnk_target (a directory).

      test_dir = os.path.join(self.temp_dir, "lnk_test")
      lnk = os.path.join(test_dir, "lnk")
      lnk_target = os.path.join(test_dir, "lnk_target")
      contents = os.path.join(lnk_target, "contents")

      os.mkdir(test_dir)
      os.mkdir(lnk_target)

      os.symlink(lnk_target, lnk)

      with io.open(contents, "wb") as fd:
        fd.write(b"sometexttofind")

      paths = [self.temp_dir + "/**"]
      condition = rdf_file_finder.FileFinderCondition.ContentsLiteralMatch(
          literal=b"sometext")

      results = self._RunFileFinder(
          paths, self.stat_action, conditions=[condition], follow_links=True)
      self.assertLen(results, 2)
      relative_results = self._GetRelativeResults(results, base_path=test_dir)
      self.assertIn("lnk_target/contents", relative_results)
      self.assertIn("lnk/contents", relative_results)

      results = self._RunFileFinder(
          paths, self.stat_action, conditions=[condition], follow_links=False)
      self.assertLen(results, 1)
      self.assertEqual(results[0].stat_entry.pathspec.path, contents)

    finally:
      try:
        shutil.rmtree(test_dir)
      except OSError:
        pass

  def testFollowLinks(self):
    try:
      # This sets up a structure as follows:
      # tmp_dir/lnk_test/contains_lnk
      # tmp_dir/lnk_test/contains_lnk/lnk
      # tmp_dir/lnk_test/lnk_target
      # tmp_dir/lnk_test/lnk_target/target

      # lnk is a symbolic link to lnk_target. A recursive find in
      # contains_lnk will find the target iff follow_links is allowed.

      test_dir = os.path.join(self.temp_dir, "lnk_test")
      contains_lnk = os.path.join(test_dir, "contains_lnk")
      lnk = os.path.join(contains_lnk, "lnk")
      lnk_target = os.path.join(test_dir, "lnk_target")
      lnk_target_contents = os.path.join(lnk_target, "target")

      os.mkdir(test_dir)
      os.mkdir(contains_lnk)
      os.mkdir(lnk_target)
      os.symlink(lnk_target, lnk)
      with io.open(lnk_target_contents, "wb") as fd:
        fd.write(b"sometext")

      paths = [contains_lnk + "/**"]
      results = self._RunFileFinder(paths, self.stat_action)
      relative_results = self._GetRelativeResults(results, base_path=test_dir)

      self.assertIn("contains_lnk/lnk", relative_results)
      self.assertIn("contains_lnk/lnk/target", relative_results)

      results = self._RunFileFinder(paths, self.stat_action, follow_links=False)
      relative_results = self._GetRelativeResults(results, base_path=test_dir)

      self.assertIn("contains_lnk/lnk", relative_results)
      self.assertNotIn("contains_lnk/lnk/target", relative_results)

    finally:
      try:
        shutil.rmtree(test_dir)
      except OSError:
        pass

  def _PrepareTimestampedFiles(self):
    searching_path = os.path.join(self.base_path, "searching")
    test_dir = os.path.join(self.temp_dir, "times_test")
    os.mkdir(test_dir)
    for f in ["dpkg.log", "dpkg_false.log", "auth.log"]:
      src = os.path.join(searching_path, f)
      dst = os.path.join(test_dir, f)
      shutil.copy(src, dst)

    return test_dir

  def RunAndCheck(self,
                  paths,
                  action=None,
                  conditions=None,
                  expected=None,
                  unexpected=None,
                  base_path=None,
                  **kw):
    action = action or self.stat_action

    raw_results = self._RunFileFinder(
        paths, action, conditions=conditions, **kw)
    relative_results = self._GetRelativeResults(
        raw_results, base_path=base_path)

    for f in unexpected:
      self.assertNotIn(f, relative_results)
    for f in expected:
      self.assertIn(f, relative_results)

  def testLiteralMatchCondition(self):
    searching_path = os.path.join(self.base_path, "searching")
    paths = [searching_path + "/{dpkg.log,dpkg_false.log,auth.log}"]

    literal = b"pam_unix(ssh:session)"
    bytes_before = 10
    bytes_after = 20

    condition = rdf_file_finder.FileFinderCondition.ContentsLiteralMatch(
        literal=literal, bytes_before=bytes_before, bytes_after=bytes_after)

    raw_results = self._RunFileFinder(
        paths, self.stat_action, conditions=[condition])
    relative_results = self._GetRelativeResults(
        raw_results, base_path=searching_path)
    self.assertLen(relative_results, 1)
    self.assertIn("auth.log", relative_results)
    self.assertLen(raw_results[0].matches, 1)
    buffer_ref = raw_results[0].matches[0]

    with io.open(os.path.join(searching_path, "auth.log"), "rb") as filedesc:
      orig_data = filedesc.read()

    self.assertLen(buffer_ref.data, bytes_before + len(literal) + bytes_after)
    self.assertEqual(
        orig_data[buffer_ref.offset:buffer_ref.offset + buffer_ref.length],
        buffer_ref.data)

  def testLiteralMatchConditionAllHits(self):
    searching_path = os.path.join(self.base_path, "searching")
    paths = [searching_path + "/{dpkg.log,dpkg_false.log,auth.log}"]

    literal = b"mydomain.com"
    bytes_before = 10
    bytes_after = 20

    condition = rdf_file_finder.FileFinderCondition.ContentsLiteralMatch(
        literal=literal,
        mode="ALL_HITS",
        bytes_before=bytes_before,
        bytes_after=bytes_after)

    raw_results = self._RunFileFinder(
        paths, self.stat_action, conditions=[condition])
    self.assertLen(raw_results, 1)
    self.assertLen(raw_results[0].matches, 6)
    for buffer_ref in raw_results[0].matches:
      self.assertEqual(
          buffer_ref.data[bytes_before:bytes_before + len(literal)], literal)

  def testLiteralMatchConditionLargeFile(self):
    paths = [os.path.join(self.base_path, "new_places.sqlite")]

    literal = b"RecentlyBookmarked"
    bytes_before = 10
    bytes_after = 20

    condition = rdf_file_finder.FileFinderCondition.ContentsLiteralMatch(
        literal=literal,
        mode="ALL_HITS",
        bytes_before=bytes_before,
        bytes_after=bytes_after)

    raw_results = self._RunFileFinder(
        paths, self.stat_action, conditions=[condition])
    self.assertLen(raw_results, 1)
    self.assertLen(raw_results[0].matches, 1)
    buffer_ref = raw_results[0].matches[0]
    with open(paths[0], "rb") as fd:
      fd.seek(buffer_ref.offset)
      self.assertEqual(buffer_ref.data, fd.read(buffer_ref.length))
      self.assertEqual(
          buffer_ref.data[bytes_before:bytes_before + len(literal)], literal)

  def testRegexMatchCondition(self):
    searching_path = os.path.join(self.base_path, "searching")
    paths = [searching_path + "/{dpkg.log,dpkg_false.log,auth.log}"]

    regex = br"pa[nm]_o?unix\(s{2}h"
    bytes_before = 10
    bytes_after = 20

    condition = rdf_file_finder.FileFinderCondition.ContentsRegexMatch(
        regex=regex, bytes_before=bytes_before, bytes_after=bytes_after)

    raw_results = self._RunFileFinder(
        paths, self.stat_action, conditions=[condition])
    relative_results = self._GetRelativeResults(
        raw_results, base_path=searching_path)
    self.assertLen(relative_results, 1)
    self.assertIn("auth.log", relative_results)
    self.assertLen(raw_results[0].matches, 1)
    buffer_ref = raw_results[0].matches[0]

    with io.open(os.path.join(searching_path, "auth.log"), "rb") as filedesc:
      orig_data = filedesc.read()

    self.assertEqual(
        orig_data[buffer_ref.offset:buffer_ref.offset + buffer_ref.length],
        buffer_ref.data)

  def testRegexMatchConditionAllHits(self):
    searching_path = os.path.join(self.base_path, "searching")
    paths = [searching_path + "/{dpkg.log,dpkg_false.log,auth.log}"]

    regex = br"mydo....\.com"
    bytes_before = 10
    bytes_after = 20

    condition = rdf_file_finder.FileFinderCondition.ContentsRegexMatch(
        regex=regex,
        mode="ALL_HITS",
        bytes_before=bytes_before,
        bytes_after=bytes_after)

    raw_results = self._RunFileFinder(
        paths, self.stat_action, conditions=[condition])
    self.assertLen(raw_results, 1)
    self.assertLen(raw_results[0].matches, 6)
    for buffer_ref in raw_results[0].matches:
      needle = b"mydomain.com"
      self.assertEqual(buffer_ref.data[bytes_before:bytes_before + len(needle)],
                       needle)

  def testContentMatchIgnoreDirsWildcard(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      os.makedirs(os.path.join(temp_dirpath, "foo"))
      os.makedirs(os.path.join(temp_dirpath, "bar"))

      with io.open(os.path.join(temp_dirpath, "quux"), "wb") as filedesc:
        filedesc.write(b"quuxfoobar")

      with io.open(os.path.join(temp_dirpath, "norf"), "wb") as filedesc:
        filedesc.write(b"norfbarbaz")

      with io.open(os.path.join(temp_dirpath, "thud"), "wb") as filedesc:
        filedesc.write(b"thudfoobaz")

      condition = rdf_file_finder.FileFinderCondition.ContentsLiteralMatch(
          literal=b"fooba")

      results = self._RunFileFinder(
          paths=[os.path.join(temp_dirpath, "*")],
          action=rdf_file_finder.FileFinderAction.Stat(),
          conditions=[condition])

      result_paths = [result.stat_entry.pathspec.path for result in results]
      self.assertCountEqual(result_paths, [
          os.path.join(temp_dirpath, "quux"),
          os.path.join(temp_dirpath, "thud"),
      ])

  def testContentMatchIgnoreDirsRecursive(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      os.makedirs(os.path.join(temp_dirpath, "foo", "bar"))
      os.makedirs(os.path.join(temp_dirpath, "foo", "baz"))

      os.makedirs(os.path.join(temp_dirpath, "foo", "bar", "quux"))
      os.makedirs(os.path.join(temp_dirpath, "foo", "bar", "thud"))

      norf_path = os.path.join(temp_dirpath, "foo", "bar", "norf")
      with io.open(norf_path, "wb") as filedesc:
        filedesc.write(b"123")

      blargh_path = os.path.join(temp_dirpath, "foo", "bar", "blargh")
      with io.open(blargh_path, "wb") as filedesc:
        filedesc.write(b"abc")

      ztesch_path = os.path.join(temp_dirpath, "foo", "bar", "ztesch")
      with io.open(ztesch_path, "wb") as filedesc:
        filedesc.write(b"456")

      condition = rdf_file_finder.FileFinderCondition.ContentsRegexMatch(
          regex=b"\\d+")

      results = self._RunFileFinder(
          paths=[os.path.join(temp_dirpath, "**", "*")],
          action=rdf_file_finder.FileFinderAction.Stat(),
          conditions=[condition])

      result_paths = [result.stat_entry.pathspec.path for result in results]
      self.assertCountEqual(result_paths, [
          os.path.join(temp_dirpath, "foo", "bar", "norf"),
          os.path.join(temp_dirpath, "foo", "bar", "ztesch"),
      ])

  def testHashAction(self):
    paths = [os.path.join(self.base_path, "win_hello.exe")]

    hash_action = rdf_file_finder.FileFinderAction.Hash()
    results = self._RunFileFinder(paths, hash_action)
    self.assertLen(results, 1)
    res = results[0]
    data = open(paths[0], "rb").read()
    self.assertLen(data, res.hash_entry.num_bytes)
    self.assertEqual(res.hash_entry.md5.HexDigest(),
                     hashlib.md5(data).hexdigest())
    self.assertEqual(res.hash_entry.sha1.HexDigest(),
                     hashlib.sha1(data).hexdigest())
    self.assertEqual(res.hash_entry.sha256.HexDigest(),
                     hashlib.sha256(data).hexdigest())

    hash_action = rdf_file_finder.FileFinderAction.Hash(
        max_size=100, oversized_file_policy="SKIP")

    results = self._RunFileFinder(paths, hash_action)
    self.assertLen(results, 1)
    res = results[0]
    self.assertFalse(res.HasField("hash"))

    hash_action = rdf_file_finder.FileFinderAction.Hash(
        max_size=100, oversized_file_policy="HASH_TRUNCATED")

    results = self._RunFileFinder(paths, hash_action)
    self.assertLen(results, 1)
    res = results[0]
    data = open(paths[0], "rb").read()[:100]
    self.assertLen(data, res.hash_entry.num_bytes)
    self.assertEqual(res.hash_entry.md5.HexDigest(),
                     hashlib.md5(data).hexdigest())
    self.assertEqual(res.hash_entry.sha1.HexDigest(),
                     hashlib.sha1(data).hexdigest())
    self.assertEqual(res.hash_entry.sha256.HexDigest(),
                     hashlib.sha256(data).hexdigest())

  def testHashDirectory(self):
    action = rdf_file_finder.FileFinderAction.Hash()
    path = os.path.join(self.base_path, "a")

    results = self._RunFileFinder([path], action)
    self.assertLen(results, 1)
    self.assertTrue(results[0].HasField("stat_entry"))
    self.assertTrue(stat.S_ISDIR(int(results[0].stat_entry.st_mode)))
    self.assertFalse(results[0].HasField("hash_entry"))

  def testDownloadDirectory(self):
    action = rdf_file_finder.FileFinderAction.Download()
    path = os.path.join(self.base_path, "a")

    results = self._RunFileFinder([path], action)
    self.assertLen(results, 1)
    self.assertTrue(results[0].HasField("stat_entry"))
    self.assertTrue(stat.S_ISDIR(int(results[0].stat_entry.st_mode)))
    self.assertFalse(results[0].HasField("uploaded_file"))

  def testDownloadActionDefault(self):
    action = rdf_file_finder.FileFinderAction.Download()
    args = rdf_file_finder.FileFinderArgs(
        action=action,
        paths=[os.path.join(self.base_path, "win_hello.exe")],
        process_non_regular_files=True)

    transfer_store = MockTransferStore()
    executor = ClientActionExecutor()
    executor.RegisterWellKnownFlow(transfer_store)
    results = executor.Execute(client_file_finder.FileFinderOS, args)

    self.assertLen(results, 1)
    with open(os.path.join(self.base_path, "win_hello.exe"), "rb") as filedesc:
      actual = transfer_store.Retrieve(results[0].transferred_file)
      expected = filedesc.read()
      self.assertEqual(actual, expected)

  def testDownloadActionSkip(self):
    action = rdf_file_finder.FileFinderAction.Download(
        max_size=0, oversized_file_policy="SKIP")
    args = rdf_file_finder.FileFinderArgs(
        action=action,
        paths=[os.path.join(self.base_path, "win_hello.exe")],
        process_non_regular_files=True)

    transfer_store = MockTransferStore()
    executor = ClientActionExecutor()
    executor.RegisterWellKnownFlow(transfer_store)
    results = executor.Execute(client_file_finder.FileFinderOS, args)

    self.assertEmpty(transfer_store.blobs)
    self.assertLen(results, 1)
    self.assertFalse(results[0].HasField("transferred_file"))
    self.assertTrue(results[0].HasField("stat_entry"))

  def testDownloadActionTruncate(self):
    action = rdf_file_finder.FileFinderAction.Download(
        max_size=42, oversized_file_policy="DOWNLOAD_TRUNCATED")
    args = rdf_file_finder.FileFinderArgs(
        action=action,
        paths=[os.path.join(self.base_path, "win_hello.exe")],
        process_non_regular_files=True)

    transfer_store = MockTransferStore()
    executor = ClientActionExecutor()
    executor.RegisterWellKnownFlow(transfer_store)
    results = executor.Execute(client_file_finder.FileFinderOS, args)

    self.assertLen(results, 1)
    with open(os.path.join(self.base_path, "win_hello.exe"), "rb") as filedesc:
      actual = transfer_store.Retrieve(results[0].transferred_file)
      expected = filedesc.read(42)
      self.assertEqual(actual, expected)

  def testDownloadActionHash(self):
    action = rdf_file_finder.FileFinderAction.Download(
        max_size=42, oversized_file_policy="HASH_TRUNCATED")
    args = rdf_file_finder.FileFinderArgs(
        action=action,
        paths=[os.path.join(self.base_path, "win_hello.exe")],
        process_non_regular_files=True)

    transfer_store = MockTransferStore()
    executor = ClientActionExecutor()
    executor.RegisterWellKnownFlow(transfer_store)
    results = executor.Execute(client_file_finder.FileFinderOS, args)

    self.assertEmpty(transfer_store.blobs)
    self.assertLen(results, 1)
    self.assertFalse(results[0].HasField("transferred_file"))
    self.assertTrue(results[0].HasField("hash_entry"))
    self.assertTrue(results[0].HasField("stat_entry"))
    self.assertEqual(results[0].hash_entry.num_bytes, 42)
    self.assertGreater(results[0].stat_entry.st_size, 42)

  EXT2_COMPR_FL = 0x00000004
  EXT2_IMMUTABLE_FL = 0x00000010

  def testStatExtFlags(self):
    with temp.AutoTempFilePath() as temp_filepath:
      filesystem_test_lib.Chattr(temp_filepath, attrs=["+c"])

      action = rdf_file_finder.FileFinderAction.Stat(collect_ext_attrs=True)
      results = self._RunFileFinder([temp_filepath], action)
      self.assertLen(results, 1)

      stat_entry = results[0].stat_entry
      self.assertTrue(stat_entry.st_flags_linux & self.EXT2_COMPR_FL)
      self.assertFalse(stat_entry.st_flags_linux & self.EXT2_IMMUTABLE_FL)

  def testStatExtAttrs(self):
    with temp.AutoTempFilePath() as temp_filepath:
      filesystem_test_lib.SetExtAttr(
          temp_filepath, name=b"user.foo", value=b"norf")
      filesystem_test_lib.SetExtAttr(
          temp_filepath, name=b"user.bar", value=b"quux")

      action = rdf_file_finder.FileFinderAction.Stat(collect_ext_attrs=True)
      results = self._RunFileFinder([temp_filepath], action)
      self.assertLen(results, 1)

      ext_attrs = results[0].stat_entry.ext_attrs
      self.assertEqual(ext_attrs[0].name, b"user.foo")
      self.assertEqual(ext_attrs[0].value, b"norf")
      self.assertEqual(ext_attrs[1].name, b"user.bar")
      self.assertEqual(ext_attrs[1].value, b"quux")

      action = rdf_file_finder.FileFinderAction.Stat(collect_ext_attrs=False)
      results = self._RunFileFinder([temp_filepath], action)
      self.assertLen(results, 1)

      ext_attrs = results[0].stat_entry.ext_attrs
      self.assertFalse(ext_attrs)

  def testStatExtAttrUnicode(self):
    with temp.AutoTempFilePath() as temp_filepath:
      name_0 = "user.żółć".encode("utf-8")
      value_0 = "jaźń".encode("utf-8")
      filesystem_test_lib.SetExtAttr(temp_filepath, name=name_0, value=value_0)

      name_1 = "user.rtęć".encode("utf-8")
      value_1 = "kość".encode("utf-8")
      filesystem_test_lib.SetExtAttr(temp_filepath, name=name_1, value=value_1)

      action = rdf_file_finder.FileFinderAction.Stat(collect_ext_attrs=True)
      results = self._RunFileFinder([temp_filepath], action)
      self.assertLen(results, 1)

      ext_attrs = results[0].stat_entry.ext_attrs
      self.assertLen(ext_attrs, 2)
      self.assertEqual(ext_attrs[0].name, name_0)
      self.assertEqual(ext_attrs[0].value, value_0)
      self.assertEqual(ext_attrs[1].name, name_1)
      self.assertEqual(ext_attrs[1].value, value_1)

  def testStatExtAttrBytesValue(self):
    with temp.AutoTempFilePath() as temp_filepath:
      name = b"user.foo"
      value = b"\xDE\xAD\xBE\xEF"

      filesystem_test_lib.SetExtAttr(temp_filepath, name=name, value=value)

      action = rdf_file_finder.FileFinderAction.Stat(collect_ext_attrs=True)
      results = self._RunFileFinder([temp_filepath], action)
      self.assertLen(results, 1)

      ext_attrs = results[0].stat_entry.ext_attrs
      self.assertLen(ext_attrs, 1)
      self.assertEqual(ext_attrs[0].name, name)
      self.assertEqual(ext_attrs[0].value, value)

  def testStatExtAttrBytesName(self):
    with temp.AutoTempFilePath() as temp_filepath:
      name = b"user.\xDE\xAD\xBE\xEF"
      value = b"bar"

      filesystem_test_lib.SetExtAttr(temp_filepath, name=name, value=value)

      # This should not explode (`xattr` does not handle non-unicode names).
      action = rdf_file_finder.FileFinderAction.Stat(collect_ext_attrs=True)
      results = self._RunFileFinder([temp_filepath], action)
      self.assertLen(results, 1)
      # We do not have an assertion whether the attributes were collected or not
      # because apparently `xattr` is sometimes able to do that and sometimes
      # not depending on the file system. This is fine as primary objective of
      # this test is to ensure that failures are handled gracefully and nothing
      # explodes.

  def testLinkStat(self):
    """Tests resolving symlinks when getting stat entries."""
    test_dir = os.path.join(self.temp_dir, "lnk_stat_test")
    lnk = os.path.join(test_dir, "lnk")
    lnk_target = os.path.join(test_dir, "lnk_target")

    os.mkdir(test_dir)
    with io.open(lnk_target, "wb") as fd:
      fd.write(b"somebytes")
    os.symlink(lnk_target, lnk)

    paths = [lnk]
    link_size = os.lstat(lnk).st_size
    target_size = os.stat(lnk).st_size
    for expected_size, resolve_links in [(link_size, False),
                                         (target_size, True)]:
      stat_action = rdf_file_finder.FileFinderAction.Stat(
          resolve_links=resolve_links)
      results = self._RunFileFinder(paths, stat_action)
      self.assertLen(results, 1)
      res = results[0]
      self.assertEqual(res.stat_entry.st_size, expected_size)
      self.assertEqual(res.stat_entry.symlink, lnk_target)

  def testLinkStatWithProcessNonRegularFilesSetToFalse(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as test_dir:
      lnk = os.path.join(test_dir, "lnk")
      lnk_target = os.path.join(test_dir, "lnk_target")

      with io.open(lnk_target, "wb") as fd:
        fd.write(b"somebytes")
      os.symlink(lnk_target, lnk)

      paths = [lnk]
      link_size = os.lstat(lnk).st_size
      target_size = os.stat(lnk).st_size
      for expected_size, resolve_links in [(link_size, False),
                                           (target_size, True)]:
        stat_action = rdf_file_finder.FileFinderAction.Stat(
            resolve_links=resolve_links)
        results = self._RunFileFinder(
            paths,
            stat_action,
            follow_links=False,
            process_non_regular_files=False)
        self.assertLen(results, 1)
        res = results[0]
        self.assertEqual(res.stat_entry.st_size, expected_size)
        self.assertEqual(res.stat_entry.symlink, lnk_target)

  def testModificationTimeCondition(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      files = ["file1", "file2", "file3"]
      for f in files:
        with open(os.path.join(temp_dirpath, f), "wb"):
          pass

      now = rdfvalue.RDFDatetime.Now()
      change_time = now + rdfvalue.Duration.From(1, rdfvalue.DAYS)
      time_secs = change_time.AsSecondsSinceEpoch() + 10
      os.utime(os.path.join(temp_dirpath, files[2]), (time_secs, time_secs))

      paths = [os.path.join(temp_dirpath, "{{{}}}".format(",".join(files)))]

      condition = rdf_file_finder.FileFinderCondition.ModificationTime(
          max_last_modified_time=change_time)

      self.RunAndCheck(
          paths,
          conditions=[condition],
          expected=files[:2],
          unexpected=files[2:],
          base_path=temp_dirpath)

      # Now just the file from 2022.
      condition = rdf_file_finder.FileFinderCondition.ModificationTime(
          min_last_modified_time=change_time)

      self.RunAndCheck(
          paths,
          conditions=[condition],
          expected=files[2:],
          unexpected=files[:2],
          base_path=temp_dirpath)

  def testAccessTimeCondition(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      files = ["file1", "file2", "file3"]
      for f in files:
        with open(os.path.join(temp_dirpath, f), "wb"):
          pass

      now = rdfvalue.RDFDatetime.Now()
      change_time = now + rdfvalue.Duration.From(1, rdfvalue.DAYS)
      time_secs = change_time.AsSecondsSinceEpoch() + 10
      os.utime(os.path.join(temp_dirpath, files[2]), (time_secs, time_secs))

      paths = [os.path.join(temp_dirpath, "{{{}}}".format(",".join(files)))]

      # Check we can get the normal files.
      condition = rdf_file_finder.FileFinderCondition.AccessTime(
          max_last_access_time=change_time)

      self.RunAndCheck(
          paths,
          conditions=[condition],
          expected=files[:2],
          unexpected=files[2:],
          base_path=temp_dirpath)

      # Now just the file from 2022.
      condition = rdf_file_finder.FileFinderCondition.AccessTime(
          min_last_access_time=change_time)

      self.RunAndCheck(
          paths,
          conditions=[condition],
          expected=files[2:],
          unexpected=files[:2],
          base_path=temp_dirpath)

  # TODO(hanuszczak): Add tests for change metadata time conditions.

  def testSizeCondition(self):
    test_dir = self._PrepareTimestampedFiles()

    # We have one "old" file, auth.log, and two "new" ones, dpkg*.
    paths = [test_dir + "/{dpkg.log,dpkg_false.log,auth.log}"]

    # Auth.log is 770 bytes, the other two ~620 each.
    condition = rdf_file_finder.FileFinderCondition.Size(min_file_size=700)

    self.RunAndCheck(
        paths,
        conditions=[condition],
        expected=["auth.log"],
        unexpected=["dpkg.log", "dpkg_false.log"],
        base_path=test_dir)

    condition = rdf_file_finder.FileFinderCondition.Size(max_file_size=700)

    self.RunAndCheck(
        paths,
        conditions=[condition],
        expected=["dpkg.log", "dpkg_false.log"],
        unexpected=["auth.log"],
        base_path=test_dir)

  def testXDEV(self):
    test_dir = os.path.join(self.temp_dir, "xdev_test")
    local_dev_dir = os.path.join(test_dir, "local_dev")
    net_dev_dir = os.path.join(test_dir, "net_dev")

    os.mkdir(test_dir)
    os.mkdir(local_dev_dir)
    os.mkdir(net_dev_dir)

    local_file = os.path.join(local_dev_dir, "local_file")
    net_file = os.path.join(net_dev_dir, "net_file")
    with io.open(local_file, "wb") as fd:
      fd.write(b"local_data")
    with io.open(net_file, "wb") as fd:
      fd.write(b"net_data")

    def MyGetAllowedDevices(xdev, path):
      if xdev == rdf_file_finder.FileFinderArgs.XDev.ALWAYS:
        # Never stop at any device boundary.
        return globbing._XDEV_ALL_ALLOWED

      elif xdev == rdf_file_finder.FileFinderArgs.XDev.NEVER:
        base_dev = os.stat(path).st_dev
        return set([base_dev])

      elif xdev == rdf_file_finder.FileFinderArgs.XDev.LOCAL:
        base_dev = os.stat(path).st_dev
        # The fake device numbers are base + 5 for local and base + 15 for net.
        return set([base_dev, base_dev + 5])

      else:
        raise ValueError("Incorrect `xdev` value: %s" % xdev)

    def MyStat(path):
      stat_entry = MyStat.old_target(path)

      if "local_dev" in path or "net_dev" in path:
        stat_entry_list = list(stat_entry)
        old_dev = stat_entry.st_dev
        # Make sure we are modifying the right field.
        self.assertEqual(old_dev, stat_entry_list[2])
        if "local_dev" in path:
          stat_entry_list[2] = old_dev + 5
        else:
          stat_entry_list[2] = old_dev + 15

        return type(stat_entry)(stat_entry_list)

      return stat_entry

    with utils.MultiStubber(
        (os, "stat", MyStat),
        (globbing, "_GetAllowedDevices", MyGetAllowedDevices)):
      paths = [test_dir + "/**5"]
      self.RunAndCheck(
          paths,
          expected=[
              "local_dev", "local_dev/local_file", "net_dev", "net_dev/net_file"
          ],
          unexpected=[],
          base_path=test_dir,
          xdev="ALWAYS")

      self.RunAndCheck(
          paths,
          expected=["local_dev", "local_dev/local_file", "net_dev"],
          unexpected=["net_dev/net_file"],
          base_path=test_dir,
          xdev="LOCAL")

      self.RunAndCheck(
          paths,
          expected=["local_dev", "net_dev"],
          unexpected=["local_dev/local_file", "net_dev/net_file"],
          base_path=test_dir,
          xdev="NEVER")


# TODO(hanuszczak): Revist this class after refactoring the GRR client worker
# class. `SendReply` should be split into three methods (for replying, for
# sending status and for communicating with well-known flows) and inspecting
# session ids should no longer be relevant.
class ClientActionExecutor(object):

  def __init__(self):
    self.wkfs = dict()

  def RegisterWellKnownFlow(self, wkf):
    session_id = rdfvalue.SessionID(flow_name=wkf.FLOW_NAME)
    self.wkfs[str(session_id)] = wkf

  def Execute(self, action_cls, args):
    responses = list()

    def SendReply(value,
                  session_id=None,
                  message_type=rdf_flows.GrrMessage.Type.MESSAGE):
      if message_type != rdf_flows.GrrMessage.Type.MESSAGE:
        return

      if str(session_id) in self.wkfs:
        message = rdf_flows.GrrMessage(
            name=action_cls.__name__,
            payload=value,
            auth_state="AUTHENTICATED",
            session_id=session_id)
        self.wkfs[str(session_id)].ProcessMessage(message)
      else:
        responses.append(value)

    message = rdf_flows.GrrMessage(
        name=action_cls.__name__,
        payload=args,
        auth_state="AUTHENTICATED",
        session_id=rdfvalue.SessionID())

    action = action_cls(grr_worker=worker_mocks.FakeClientWorker())
    action.SendReply = SendReply
    action.Execute(message)

    return responses


# TODO(hanuszczak): Maybe it is possible to refactor the `FakeTransferStore`
# class such that it can be used in tests directly (backed by some fake data
# store).
class MockTransferStore(object):

  FLOW_NAME = "TransferStore"

  def __init__(self):
    self.blobs = dict()

  def ProcessMessages(self, messages):
    for message in messages:
      self.ProcessMessage(message)

  def ProcessMessage(self, message):
    if message.auth_state != "AUTHENTICATED":
      raise ValueError("message is not authenticated")

    data_blob = message.payload
    if data_blob.compression == "UNCOMPRESSED":
      data = data_blob.data
    elif data_blob.compression == "ZCOMPRESSION":
      data = zlib.decompress(data_blob.data)
    else:
      raise ValueError("unknown blob compression: %s" % data_blob.compression)

    digest = hashlib.sha256(data).digest()
    self.blobs[digest] = data

  def Retrieve(self, blobdesc):
    # A rich blob is essentially the same as a chunk of fragmented file but with
    # original data instead of its digest.
    RichBlob = collections.namedtuple("RichBlob", ("data", "offset", "length"))  # pylint: disable=invalid-name

    blobs = list()
    for chunk in blobdesc.chunks:
      blob = RichBlob(
          data=self.blobs[chunk.digest],
          offset=chunk.offset,
          length=chunk.length)
      blobs.append(blob)
    blobs.sort(key=lambda blob: blob.offset)

    data = bytes()
    for blob in blobs:
      if blob.offset != len(data):
        message = "unexpected blob offset: expected %d but got %d"
        raise ValueError(message % (len(data), blob.offset))
      if blob.length != len(blob.data):
        message = "unexpected blob length: expected %d but got %d"
        raise ValueError(message % (len(blob.data), blob.length))
      data += blob.data

    return data


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
