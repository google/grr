#!/usr/bin/env python
"""Tests the client file finder action."""

import collections
import glob
import hashlib
import os
import platform
import shutil
import subprocess
import unittest

import mock
import psutil

import unittest
from grr.client import comms
from grr.client.client_actions import file_finder as client_file_finder
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import crypto as rdf_crypto
from grr.lib.rdfvalues import file_finder as rdf_file_finder
from grr.lib.rdfvalues import standard as rdf_standard
from grr.test_lib import client_test_lib
from grr.test_lib import test_lib


def MyStat(path):
  stat_obj = MyStat.old_target(path)
  if path.endswith("auth.log"):
    res = list(stat_obj)
    # Sets atime, ctime, and mtime to some time in 2022.
    res[-1] = 1672466423
    res[-2] = 1672466423
    res[-3] = 1672466423
    return os.stat_result(res)
  return stat_obj


class FileFinderTest(client_test_lib.EmptyActionTest):

  def setUp(self):
    super(FileFinderTest, self).setUp()
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
                     **kw):
    return self.RunAction(
        client_file_finder.FileFinderOS,
        arg=rdf_file_finder.FileFinderArgs(
            paths=paths,
            action=action,
            conditions=conditions,
            process_non_regular_files=True,
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
    paths = [self.base_path + "/rekall*.gz"]
    results = self._RunFileFinder(paths, self.stat_action)
    relative_results = self._GetRelativeResults(results)
    for glob_result in glob.glob(self.base_path + "/rekall*gz"):
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
      with open(lnk_target_contents, "wb") as fd:
        fd.write("sometext")

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
    literal = "pam_unix(ssh:session)"

    clmc = rdf_file_finder.FileFinderContentsLiteralMatchCondition
    bytes_before = 10
    bytes_after = 20
    condition = rdf_file_finder.FileFinderCondition(
        condition_type="CONTENTS_LITERAL_MATCH",
        contents_literal_match=clmc(
            literal=literal, bytes_before=bytes_before,
            bytes_after=bytes_after))
    raw_results = self._RunFileFinder(
        paths, self.stat_action, conditions=[condition])
    relative_results = self._GetRelativeResults(
        raw_results, base_path=searching_path)
    self.assertEqual(len(relative_results), 1)
    self.assertIn("auth.log", relative_results)
    self.assertEqual(len(raw_results[0].matches), 1)
    buffer_ref = raw_results[0].matches[0]
    orig_data = open(os.path.join(searching_path, "auth.log")).read()

    self.assertEqual(
        len(buffer_ref.data), bytes_before + len(literal) + bytes_after)
    self.assertEqual(
        orig_data[buffer_ref.offset:buffer_ref.offset + buffer_ref.length],
        buffer_ref.data)

  def testLiteralMatchConditionAllHits(self):
    searching_path = os.path.join(self.base_path, "searching")
    paths = [searching_path + "/{dpkg.log,dpkg_false.log,auth.log}"]

    clmc = rdf_file_finder.FileFinderContentsLiteralMatchCondition
    bytes_before = 10
    bytes_after = 20

    literal = "mydomain.com"
    condition = rdf_file_finder.FileFinderCondition(
        condition_type="CONTENTS_LITERAL_MATCH",
        contents_literal_match=clmc(
            literal=literal,
            mode="ALL_HITS",
            bytes_before=bytes_before,
            bytes_after=bytes_after))

    raw_results = self._RunFileFinder(
        paths, self.stat_action, conditions=[condition])
    self.assertEqual(len(raw_results), 1)
    self.assertEqual(len(raw_results[0].matches), 6)
    for buffer_ref in raw_results[0].matches:
      self.assertEqual(
          buffer_ref.data[bytes_before:bytes_before + len(literal)], literal)

  def testLiteralMatchConditionLargeFile(self):
    paths = [os.path.join(self.base_path, "new_places.sqlite")]
    literal = "RecentlyBookmarked"

    clmc = rdf_file_finder.FileFinderContentsLiteralMatchCondition
    bytes_before = 10
    bytes_after = 20

    condition = rdf_file_finder.FileFinderCondition(
        condition_type="CONTENTS_LITERAL_MATCH",
        contents_literal_match=clmc(
            literal=literal,
            mode="ALL_HITS",
            bytes_before=bytes_before,
            bytes_after=bytes_after))

    raw_results = self._RunFileFinder(
        paths, self.stat_action, conditions=[condition])
    self.assertEqual(len(raw_results), 1)
    self.assertEqual(len(raw_results[0].matches), 1)
    buffer_ref = raw_results[0].matches[0]
    with open(paths[0], "rb") as fd:
      fd.seek(buffer_ref.offset)
      self.assertEqual(buffer_ref.data, fd.read(buffer_ref.length))
      self.assertEqual(
          buffer_ref.data[bytes_before:bytes_before + len(literal)], literal)

  def testRegexMatchCondition(self):
    searching_path = os.path.join(self.base_path, "searching")
    paths = [searching_path + "/{dpkg.log,dpkg_false.log,auth.log}"]
    regex = r"pa[nm]_o?unix\(s{2}h"

    bytes_before = 10
    bytes_after = 20
    crmc = rdf_file_finder.FileFinderContentsRegexMatchCondition
    condition = rdf_file_finder.FileFinderCondition(
        condition_type="CONTENTS_REGEX_MATCH",
        contents_regex_match=crmc(
            regex=regex,
            bytes_before=bytes_before,
            bytes_after=bytes_after,
        ))
    raw_results = self._RunFileFinder(
        paths, self.stat_action, conditions=[condition])
    relative_results = self._GetRelativeResults(
        raw_results, base_path=searching_path)
    self.assertEqual(len(relative_results), 1)
    self.assertIn("auth.log", relative_results)
    self.assertEqual(len(raw_results[0].matches), 1)
    buffer_ref = raw_results[0].matches[0]
    orig_data = open(os.path.join(searching_path, "auth.log")).read()
    self.assertEqual(
        orig_data[buffer_ref.offset:buffer_ref.offset + buffer_ref.length],
        buffer_ref.data)

  def testRegexMatchConditionAllHits(self):
    searching_path = os.path.join(self.base_path, "searching")
    paths = [searching_path + "/{dpkg.log,dpkg_false.log,auth.log}"]

    bytes_before = 10
    bytes_after = 20
    crmc = rdf_file_finder.FileFinderContentsRegexMatchCondition

    regex = r"mydo....\.com"
    condition = rdf_file_finder.FileFinderCondition(
        condition_type="CONTENTS_REGEX_MATCH",
        contents_regex_match=crmc(
            regex=regex,
            mode="ALL_HITS",
            bytes_before=bytes_before,
            bytes_after=bytes_after,
        ))
    raw_results = self._RunFileFinder(
        paths, self.stat_action, conditions=[condition])
    self.assertEqual(len(raw_results), 1)
    self.assertEqual(len(raw_results[0].matches), 6)
    for buffer_ref in raw_results[0].matches:
      needle = "mydomain.com"
      self.assertEqual(buffer_ref.data[bytes_before:bytes_before + len(needle)],
                       needle)

  def testHashAction(self):
    paths = [os.path.join(self.base_path, "hello.exe")]

    hash_action = rdf_file_finder.FileFinderAction(
        action_type=rdf_file_finder.FileFinderAction.Action.HASH)
    results = self._RunFileFinder(paths, hash_action)
    self.assertEqual(len(results), 1)
    res = results[0]
    data = open(paths[0], "rb").read()
    self.assertEqual(res.hash_entry.num_bytes, len(data))
    self.assertEqual(res.hash_entry.md5.HexDigest(),
                     hashlib.md5(data).hexdigest())
    self.assertEqual(res.hash_entry.sha1.HexDigest(),
                     hashlib.sha1(data).hexdigest())
    self.assertEqual(res.hash_entry.sha256.HexDigest(),
                     hashlib.sha256(data).hexdigest())

    hash_action = rdf_file_finder.FileFinderAction(
        action_type=rdf_file_finder.FileFinderAction.Action.HASH,
        hash=rdf_file_finder.FileFinderHashActionOptions(
            max_size=100, oversized_file_policy="SKIP"))
    results = self._RunFileFinder(paths, hash_action)
    self.assertEqual(len(results), 1)
    res = results[0]
    self.assertFalse(res.HasField("hash"))

    hash_action = rdf_file_finder.FileFinderAction(
        action_type=rdf_file_finder.FileFinderAction.Action.HASH,
        hash=rdf_file_finder.FileFinderHashActionOptions(
            max_size=100, oversized_file_policy="HASH_TRUNCATED"))
    results = self._RunFileFinder(paths, hash_action)
    self.assertEqual(len(results), 1)
    res = results[0]
    data = open(paths[0], "rb").read()[:100]
    self.assertEqual(res.hash_entry.num_bytes, len(data))
    self.assertEqual(res.hash_entry.md5.HexDigest(),
                     hashlib.md5(data).hexdigest())
    self.assertEqual(res.hash_entry.sha1.HexDigest(),
                     hashlib.sha1(data).hexdigest())
    self.assertEqual(res.hash_entry.sha256.HexDigest(),
                     hashlib.sha256(data).hexdigest())

  def _RunFileFinderDownloadHello(self, upload, opts=None):
    action = rdf_file_finder.FileFinderAction.Download()
    action.download = opts

    upload.return_value = rdf_client.UploadedFile(
        bytes_uploaded=42, file_id="foo", hash=rdf_crypto.Hash())

    hello_path = os.path.join(self.base_path, "hello.exe")
    return self._RunFileFinder([hello_path], action)

  @mock.patch.object(comms.GRRClientWorker, "UploadFile")
  def testDownloadActionDefault(self, upload):
    results = self._RunFileFinderDownloadHello(upload)
    self.assertEquals(len(results), 1)
    self.assertTrue(upload.called_with(max_bytes=None))
    self.assertTrue(results[0].HasField("uploaded_file"))
    self.assertEquals(results[0].uploaded_file, upload.return_value)

  @mock.patch.object(comms.GRRClientWorker, "UploadFile")
  def testDownloadActionSkip(self, upload):
    opts = rdf_file_finder.FileFinderDownloadActionOptions(
        max_size=0, oversized_file_policy="SKIP")

    results = self._RunFileFinderDownloadHello(upload, opts=opts)
    self.assertEquals(len(results), 1)
    self.assertFalse(upload.called)
    self.assertFalse(results[0].HasField("uploaded_file"))

  @mock.patch.object(comms.GRRClientWorker, "UploadFile")
  def testDownloadActionTruncate(self, upload):
    opts = rdf_file_finder.FileFinderDownloadActionOptions(
        max_size=42, oversized_file_policy="DOWNLOAD_TRUNCATED")

    results = self._RunFileFinderDownloadHello(upload, opts=opts)
    self.assertEquals(len(results), 1)
    self.assertTrue(upload.called_with(max_bytes=42))
    self.assertTrue(results[0].HasField("uploaded_file"))
    self.assertEquals(results[0].uploaded_file, upload.return_value)

  EXT2_COMPR_FL = 0x00000004
  EXT2_IMMUTABLE_FL = 0x00000010

  # TODO(hanuszczak): Maybe it would make sense to refactor this to a helper
  # constructor of the `rdf_file_finder.FileFinderAction`.
  @staticmethod
  def _StatAction(**kwargs):
    action_type = rdf_file_finder.FileFinderAction.Action.STAT
    opts = rdf_file_finder.FileFinderStatActionOptions(**kwargs)
    return rdf_file_finder.FileFinderAction(action_type=action_type, stat=opts)

  @unittest.skipIf(platform.system() != "Linux", "requires Linux")
  def testStatExtFlags(self):
    with test_lib.AutoTempFilePath() as temp_filepath:
      if subprocess.call(["which", "chattr"]) != 0:
        raise unittest.SkipTest("`chattr` command is not available")
      if subprocess.call(["chattr", "+c", temp_filepath]) != 0:
        reason = "extended attributes not supported by filesystem"
        raise unittest.SkipTest(reason)

      action = self._StatAction()
      results = self._RunFileFinder([temp_filepath], action)
      self.assertEqual(len(results), 1)

      stat_entry = results[0].stat_entry
      self.assertTrue(stat_entry.st_flags_linux & self.EXT2_COMPR_FL)
      self.assertFalse(stat_entry.st_flags_linux & self.EXT2_IMMUTABLE_FL)

  def testStatExtAttrs(self):
    with test_lib.AutoTempFilePath() as temp_filepath:
      self._SetExtAttr(temp_filepath, "user.foo", "bar")
      self._SetExtAttr(temp_filepath, "user.quux", "norf")

      action = self._StatAction()
      results = self._RunFileFinder([temp_filepath], action)
      self.assertEqual(len(results), 1)

      ext_attrs = results[0].stat_entry.ext_attrs
      self.assertEqual(ext_attrs[0].name, "user.foo")
      self.assertEqual(ext_attrs[0].value, "bar")
      self.assertEqual(ext_attrs[1].name, "user.quux")
      self.assertEqual(ext_attrs[1].value, "norf")

      action = self._StatAction(ext_attrs=False)
      results = self._RunFileFinder([temp_filepath], action)
      self.assertEqual(len(results), 1)

      ext_attrs = results[0].stat_entry.ext_attrs
      self.assertFalse(ext_attrs)

  @classmethod
  def _SetExtAttr(cls, filepath, name, value):
    if platform.system() == "Linux":
      cls._SetExtAttrLinux(filepath, name, value)
    elif platform.system() == "Darwin":
      cls._SetExtAttrOsx(filepath, name, value)
    else:
      raise unittest.SkipTest("unsupported system")

  @classmethod
  def _SetExtAttrLinux(cls, filepath, name, value):
    if subprocess.call(["which", "setfattr"]) != 0:
      raise unittest.SkipTest("`setfattr` command is not available")
    if subprocess.call(["setfattr", filepath, "-n", name, "-v", value]) != 0:
      raise unittest.SkipTest("extended attributes not supported by filesystem")

  @classmethod
  def _SetExtAttrOsx(cls, filepath, name, value):
    if subprocess.call(["xattr", "-w", name, value, filepath]) != 0:
      raise unittest.SkipTest("extended attributes not supported")

  def testLinkStat(self):
    """Tests resolving symlinks when getting stat entries."""
    test_dir = os.path.join(self.temp_dir, "lnk_stat_test")
    lnk = os.path.join(test_dir, "lnk")
    lnk_target = os.path.join(test_dir, "lnk_target")

    os.mkdir(test_dir)
    with open(lnk_target, "wb") as fd:
      fd.write("sometext")
    os.symlink(lnk_target, lnk)

    paths = [lnk]
    link_size = os.lstat(lnk).st_size
    target_size = os.stat(lnk).st_size
    for expected_size, resolve_links in [(link_size, False), (target_size,
                                                              True)]:
      stat_action = rdf_file_finder.FileFinderAction.Stat(
          resolve_links=resolve_links)
      results = self._RunFileFinder(paths, stat_action)
      self.assertEqual(len(results), 1)
      res = results[0]
      self.assertEqual(res.stat_entry.st_size, expected_size)

  def testModificationTimeCondition(self):
    with utils.Stubber(os, "lstat", MyStat):
      test_dir = self._PrepareTimestampedFiles()

      # We have one "old" file, auth.log, and two "new" ones, dpkg*.
      paths = [test_dir + "/{dpkg.log,dpkg_false.log,auth.log}"]

      change_time = rdfvalue.RDFDatetime.FromHumanReadable("2020-01-01")

      modification_time_condition = rdf_file_finder.FileFinderCondition(
          condition_type="MODIFICATION_TIME",
          modification_time=rdf_file_finder.FileFinderModificationTimeCondition(
              max_last_modified_time=change_time))

      self.RunAndCheck(
          paths,
          conditions=[modification_time_condition],
          expected=["dpkg.log", "dpkg_false.log"],
          unexpected=["auth.log"],
          base_path=test_dir)

      # Now just the file from 2022.
      modification_time_condition = rdf_file_finder.FileFinderCondition(
          condition_type="MODIFICATION_TIME",
          modification_time=rdf_file_finder.FileFinderModificationTimeCondition(
              min_last_modified_time=change_time))

      self.RunAndCheck(
          paths,
          conditions=[modification_time_condition],
          expected=["auth.log"],
          unexpected=["dpkg.log", "dpkg_false.log"],
          base_path=test_dir)

  def testAccessTimeCondition(self):
    with utils.Stubber(os, "lstat", MyStat):
      test_dir = self._PrepareTimestampedFiles()

      paths = [test_dir + "/{dpkg.log,dpkg_false.log,auth.log}"]

      change_time = rdfvalue.RDFDatetime.FromHumanReadable("2020-01-01")

      # Check we can get the normal files.
      access_time_condition = rdf_file_finder.FileFinderCondition(
          condition_type="ACCESS_TIME",
          access_time=rdf_file_finder.FileFinderAccessTimeCondition(
              max_last_access_time=change_time))

      self.RunAndCheck(
          paths,
          conditions=[access_time_condition],
          expected=["dpkg.log", "dpkg_false.log"],
          unexpected=["auth.log"],
          base_path=test_dir)

      # Now just the file from 2022.
      access_time_condition = rdf_file_finder.FileFinderCondition(
          condition_type="ACCESS_TIME",
          access_time=rdf_file_finder.FileFinderAccessTimeCondition(
              min_last_access_time=change_time))

      self.RunAndCheck(
          paths,
          conditions=[access_time_condition],
          expected=["auth.log"],
          unexpected=["dpkg.log", "dpkg_false.log"],
          base_path=test_dir)

  def testInodeChangeTimeCondition(self):
    with utils.Stubber(os, "lstat", MyStat):
      test_dir = self._PrepareTimestampedFiles()

      # We have one "old" file, auth.log, and two "new" ones, dpkg*.
      paths = [test_dir + "/{dpkg.log,dpkg_false.log,auth.log}"]

      # Check we can get the auth log only (huge ctime).
      change_time = rdfvalue.RDFDatetime.FromHumanReadable("2020-01-01")

      ichange_time_condition = rdf_file_finder.FileFinderCondition(
          condition_type="INODE_CHANGE_TIME",
          inode_change_time=rdf_file_finder.FileFinderInodeChangeTimeCondition(
              min_last_inode_change_time=change_time))

      self.RunAndCheck(
          paths,
          conditions=[ichange_time_condition],
          expected=["auth.log"],
          unexpected=["dpkg.log", "dpkg_false.log"],
          base_path=test_dir)

      # Now just the others.
      ichange_time_condition = rdf_file_finder.FileFinderCondition(
          condition_type="INODE_CHANGE_TIME",
          inode_change_time=rdf_file_finder.FileFinderInodeChangeTimeCondition(
              max_last_inode_change_time=change_time))

      self.RunAndCheck(
          paths,
          conditions=[ichange_time_condition],
          expected=["dpkg.log", "dpkg_false.log"],
          unexpected=["auth.log"],
          base_path=test_dir)

  def testSizeCondition(self):
    test_dir = self._PrepareTimestampedFiles()

    # We have one "old" file, auth.log, and two "new" ones, dpkg*.
    paths = [test_dir + "/{dpkg.log,dpkg_false.log,auth.log}"]

    # Auth.log is 770 bytes, the other two ~620 each.
    size_condition = rdf_file_finder.FileFinderCondition(
        condition_type="SIZE",
        size=rdf_file_finder.FileFinderSizeCondition(min_file_size=700))

    self.RunAndCheck(
        paths,
        conditions=[size_condition],
        expected=["auth.log"],
        unexpected=["dpkg.log", "dpkg_false.log"],
        base_path=test_dir)

    size_condition = rdf_file_finder.FileFinderCondition(
        condition_type="SIZE",
        size=rdf_file_finder.FileFinderSizeCondition(max_file_size=700))

    self.RunAndCheck(
        paths,
        conditions=[size_condition],
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
    with open(local_file, "wb") as fd:
      fd.write("local_data")
    with open(net_file, "wb") as fd:
      fd.write("net_data")

    all_mountpoints = [local_dev_dir, net_dev_dir, "/some/other/dir"]
    local_mountpoints = [local_dev_dir]

    def MyDiskPartitions(all=False):  # pylint: disable=redefined-builtin
      mp = collections.namedtuple("MountPoint", ["mountpoint"])
      if all:
        return [mp(mountpoint=m) for m in all_mountpoints]
      else:
        return [mp(mountpoint=m) for m in local_mountpoints]

    with utils.Stubber(psutil, "disk_partitions", MyDiskPartitions):
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


class RegexMatcherTest(unittest.TestCase):

  @staticmethod
  def _RegexMatcher(string):
    regex = rdf_standard.RegularExpression(string)
    return client_file_finder.RegexMatcher(regex)

  def testMatchLiteral(self):
    matcher = self._RegexMatcher("foo")

    span = matcher.Match("foobar", 0)
    self.assertTrue(span)
    self.assertEqual(span.begin, 0)
    self.assertEqual(span.end, 3)

    span = matcher.Match("foobarfoobar", 2)
    self.assertTrue(span)
    self.assertEqual(span.begin, 6)
    self.assertEqual(span.end, 9)

  def testNoMatchLiteral(self):
    matcher = self._RegexMatcher("baz")

    span = matcher.Match("foobar", 0)
    self.assertFalse(span)

    span = matcher.Match("foobazbar", 5)
    self.assertFalse(span)

  def testMatchWildcard(self):
    matcher = self._RegexMatcher("foo.*bar")

    span = matcher.Match("foobar", 0)
    self.assertTrue(span)
    self.assertEqual(span.begin, 0)
    self.assertEqual(span.end, 6)

    span = matcher.Match("quuxfoobazbarnorf", 2)
    self.assertTrue(span)
    self.assertEqual(span.begin, 4)
    self.assertEqual(span.end, 13)

  def testMatchRepeated(self):
    matcher = self._RegexMatcher("qu+x")

    span = matcher.Match("quuuux", 0)
    self.assertTrue(span)
    self.assertEqual(span.begin, 0)
    self.assertEqual(span.end, 6)

    span = matcher.Match("qx", 0)
    self.assertFalse(span)

    span = matcher.Match("qvvvvx", 0)
    self.assertFalse(span)


class LiteralMatcherTest(unittest.TestCase):

  def testMatchLiteral(self):
    matcher = client_file_finder.LiteralMatcher("bar")

    span = matcher.Match("foobarbaz", 0)
    self.assertTrue(span)
    self.assertEqual(span.begin, 3)
    self.assertEqual(span.end, 6)

    span = matcher.Match("barbarbar", 0)
    self.assertTrue(span)
    self.assertEqual(span.begin, 0)
    self.assertEqual(span.end, 3)

    span = matcher.Match("barbarbar", 4)
    self.assertTrue(span)
    self.assertEqual(span.begin, 6)
    self.assertEqual(span.end, 9)

  def testNoMatchLiteral(self):
    matcher = client_file_finder.LiteralMatcher("norf")

    span = matcher.Match("quux", 0)
    self.assertFalse(span)

    span = matcher.Match("norf", 2)
    self.assertFalse(span)

    span = matcher.Match("quuxnorf", 5)
    self.assertFalse(span)


class ConditionTestMixin(object):

  def setUp(self):
    super(ConditionTestMixin, self).setUp()
    self.temp_filepath = test_lib.TempFilePath()

  def tearDown(self):
    super(ConditionTestMixin, self).tearDown()
    os.remove(self.temp_filepath)


@unittest.skipIf(platform.system() == "Windows", "requires Unix-like system")
class MetadataConditionTestMixin(ConditionTestMixin):

  def Stat(self):
    return utils.Stat(self.temp_filepath, follow_symlink=False)

  def Touch(self, mode, date):
    self.assertIn(mode, ["-m", "-a"])
    result = subprocess.call(["touch", mode, "-t", date, self.temp_filepath])
    # Sanity check in case something is wrong with the test.
    self.assertEqual(result, 0)


class ModificationTimeConditionTest(MetadataConditionTestMixin,
                                    unittest.TestCase):

  def testDefault(self):
    params = rdf_file_finder.FileFinderCondition()
    condition = client_file_finder.ModificationTimeCondition(params)

    self.Touch("-m", "198309121200")  # 1983-09-12 12:00
    self.assertTrue(condition.Check(self.Stat()))

    self.Touch("-m", "201710020815")  # 2017-10-02 8:15
    self.assertTrue(condition.Check(self.Stat()))

  def testMinTime(self):
    time = rdfvalue.RDFDatetime.FromHumanReadable("2017-12-24 19:00:00")

    params = rdf_file_finder.FileFinderCondition()
    params.modification_time.min_last_modified_time = time
    condition = client_file_finder.ModificationTimeCondition(params)

    self.Touch("-m", "201712240100")  # 2017-12-24 1:30
    self.assertFalse(condition.Check(self.Stat()))

    self.Touch("-m", "201806141700")  # 2018-06-14 17:00
    self.assertTrue(condition.Check(self.Stat()))

  def testMaxTime(self):
    time = rdfvalue.RDFDatetime.FromHumanReadable("2925-12-28 18:45")

    params = rdf_file_finder.FileFinderCondition()
    params.modification_time.max_last_modified_time = time
    condition = client_file_finder.ModificationTimeCondition(params)

    self.Touch("-m", "291811111200")  # 2918-11-11 12:00
    self.assertTrue(condition.Check(self.Stat()))

    self.Touch("-m", "301210201500")  # 3012-10-20 15:00
    self.assertFalse(condition.Check(self.Stat()))


class AccessTimeConditionTest(MetadataConditionTestMixin, unittest.TestCase):

  def testDefault(self):
    params = rdf_file_finder.FileFinderCondition()
    condition = client_file_finder.AccessTimeCondition(params)

    self.Touch("-a", "241007151200")  # 2410-07-15 12:00
    self.assertTrue(condition.Check(self.Stat()))

    self.Touch("-a", "201005160745")  # 2010-05-16 7:45
    self.assertTrue(condition.Check(self.Stat()))

  def testRange(self):
    min_time = rdfvalue.RDFDatetime.FromHumanReadable("2756-01-27")
    max_time = rdfvalue.RDFDatetime.FromHumanReadable("2791-12-05")

    params = rdf_file_finder.FileFinderCondition()
    params.access_time.min_last_access_time = min_time
    params.access_time.max_last_access_time = max_time
    condition = client_file_finder.AccessTimeCondition(params)

    self.Touch("-a", "275007280000")  # 2750-07-28 0:00
    self.assertFalse(condition.Check(self.Stat()))

    self.Touch("-a", "279101010000")  # 2791-01-01 0:00
    self.assertTrue(condition.Check(self.Stat()))

    self.Touch("-a", "281003010000")  # 2810-03-01 0:00
    self.assertFalse(condition.Check(self.Stat()))


class SizeConditionTest(MetadataConditionTestMixin, unittest.TestCase):

  def testDefault(self):
    params = rdf_file_finder.FileFinderCondition()
    condition = client_file_finder.SizeCondition(params)

    with open(self.temp_filepath, "wb") as fd:
      fd.write("1234567")
    self.assertTrue(condition.Check(self.Stat()))

    with open(self.temp_filepath, "wb") as fd:
      fd.write("")
    self.assertTrue(condition.Check(self.Stat()))

  def testRange(self):
    params = rdf_file_finder.FileFinderCondition()
    params.size.min_file_size = 2
    params.size.max_file_size = 6
    condition = client_file_finder.SizeCondition(params)

    with open(self.temp_filepath, "wb") as fd:
      fd.write("1")
    self.assertFalse(condition.Check(self.Stat()))

    with open(self.temp_filepath, "wb") as fd:
      fd.write("12")
    self.assertTrue(condition.Check(self.Stat()))

    with open(self.temp_filepath, "wb") as fd:
      fd.write("1234")
    self.assertTrue(condition.Check(self.Stat()))

    with open(self.temp_filepath, "wb") as fd:
      fd.write("123456")
    self.assertTrue(condition.Check(self.Stat()))

    with open(self.temp_filepath, "wb") as fd:
      fd.write("1234567")
    self.assertFalse(condition.Check(self.Stat()))


class ExtFlagsConditionTest(MetadataConditionTestMixin, unittest.TestCase):

  # https://github.com/apple/darwin-xnu/blob/master/bsd/sys/stat.h
  UF_NODUMP = 0x00000001
  UF_IMMUTABLE = 0x00000002
  UF_HIDDEN = 0x00008000

  # https://github.com/torvalds/linux/blob/master/include/uapi/linux/fs.h
  FS_COMPR_FL = 0x00000004
  FS_IMMUTABLE_FL = 0x00000010
  FS_NODUMP_FL = 0x00000040

  def testDefault(self):
    params = rdf_file_finder.FileFinderCondition()
    condition = client_file_finder.ExtFlagsCondition(params)

    self.assertTrue(condition.Check(self.Stat()))

  def testNoMatchOsxBitsSet(self):
    params = rdf_file_finder.FileFinderCondition()
    params.ext_flags.osx_bits_set = self.UF_IMMUTABLE | self.UF_NODUMP
    condition = client_file_finder.ExtFlagsCondition(params)

    self._Chflags(["nodump"])

    self.assertFalse(condition.Check(self.Stat()))

  def testNoMatchOsxBitsUnset(self):
    params = rdf_file_finder.FileFinderCondition()
    params.ext_flags.osx_bits_unset = self.UF_NODUMP | self.UF_HIDDEN
    condition = client_file_finder.ExtFlagsCondition(params)

    self._Chflags(["hidden"])

    self.assertFalse(condition.Check(self.Stat()))

  def testNoMatchLinuxBitsSet(self):
    params = rdf_file_finder.FileFinderCondition()
    params.ext_flags.linux_bits_set = self.FS_IMMUTABLE_FL
    condition = client_file_finder.ExtFlagsCondition(params)

    self.assertFalse(condition.Check(self.Stat()))

  def testNoMatchLinuxBitsUnset(self):
    params = rdf_file_finder.FileFinderCondition()
    params.ext_flags.linux_bits_unset = self.FS_COMPR_FL
    condition = client_file_finder.ExtFlagsCondition(params)

    self._Chattr(["+c", "+d"])

    self.assertFalse(condition.Check(self.Stat()))

  def testMatchOsxBitsSet(self):
    params = rdf_file_finder.FileFinderCondition()
    params.ext_flags.osx_bits_set = self.UF_NODUMP | self.UF_HIDDEN
    condition = client_file_finder.ExtFlagsCondition(params)

    self._Chflags(["nodump", "hidden", "uappend"])

    self.assertTrue(condition.Check(self.Stat()))

  def testMatchLinuxBitsSet(self):
    params = rdf_file_finder.FileFinderCondition()
    params.ext_flags.linux_bits_set = self.FS_COMPR_FL | self.FS_NODUMP_FL
    condition = client_file_finder.ExtFlagsCondition(params)

    self._Chattr(["+c", "+d"])

    self.assertTrue(condition.Check(self.Stat()))

  def testMatchOsxBitsUnset(self):
    params = rdf_file_finder.FileFinderCondition()
    params.ext_flags.osx_bits_unset = self.UF_NODUMP | self.UF_IMMUTABLE
    condition = client_file_finder.ExtFlagsCondition(params)

    self._Chflags(["hidden", "uappend"])

    self.assertTrue(condition.Check(self.Stat()))

  def testMatchLinuxBitsUnset(self):
    params = rdf_file_finder.FileFinderCondition()
    params.ext_flags.linux_bits_unset = self.FS_IMMUTABLE_FL
    condition = client_file_finder.ExtFlagsCondition(params)

    self._Chattr(["+c", "+d"])

    self.assertTrue(condition.Check(self.Stat()))

  def testMatchOsxBitsMixed(self):
    params = rdf_file_finder.FileFinderCondition()
    params.ext_flags.osx_bits_set = self.UF_NODUMP
    params.ext_flags.osx_bits_unset = self.UF_HIDDEN
    params.ext_flags.linux_bits_unset = self.FS_NODUMP_FL
    condition = client_file_finder.ExtFlagsCondition(params)

    self._Chflags(["nodump", "uappend"])

    self.assertTrue(condition.Check(self.Stat()))

  def testMatchLinuxBitsMixed(self):
    params = rdf_file_finder.FileFinderCondition()
    params.ext_flags.linux_bits_set = self.FS_NODUMP_FL
    params.ext_flags.linux_bits_unset = self.FS_COMPR_FL
    params.ext_flags.osx_bits_unset = self.UF_IMMUTABLE
    condition = client_file_finder.ExtFlagsCondition(params)

    self._Chattr(["+d"])

    self.assertTrue(condition.Check(self.Stat()))

  def _Chattr(self, args):
    if platform.system() != "Linux":
      raise unittest.SkipTest("requires Linux")
    if subprocess.call(["which", "chattr"]) != 0:
      raise unittest.SkipTest("the `chattr` command is not available")
    if subprocess.call(["chattr"] + args + [self.temp_filepath]) != 0:
      reason = "extended attributes are not supported by filesystem"
      raise unittest.SkipTest(reason)

  def _Chflags(self, args):
    if platform.system() != "Darwin":
      raise unittest.SkipTest("requires macOS")
    subprocess.check_call(["chflags"] + args + [self.temp_filepath])


# TODO(hanuszczak): Write tests for the metadata change condition.


class LiteralMatchConditionTest(ConditionTestMixin, unittest.TestCase):

  def testNoHits(self):
    with open(self.temp_filepath, "wb") as fd:
      fd.write("foo bar quux")

    params = rdf_file_finder.FileFinderCondition()
    params.contents_literal_match.literal = "baz"
    params.contents_literal_match.mode = "ALL_HITS"
    condition = client_file_finder.LiteralMatchCondition(params)

    results = list(condition.Search(self.temp_filepath))
    self.assertFalse(results)

  def testSomeHits(self):
    with open(self.temp_filepath, "wb") as fd:
      fd.write("foo bar foo")

    params = rdf_file_finder.FileFinderCondition()
    params.contents_literal_match.literal = "foo"
    params.contents_literal_match.mode = "ALL_HITS"
    condition = client_file_finder.LiteralMatchCondition(params)

    results = list(condition.Search(self.temp_filepath))
    self.assertEqual(len(results), 2)
    self.assertEqual(results[0].data, "foo")
    self.assertEqual(results[0].offset, 0)
    self.assertEqual(results[0].length, 3)
    self.assertEqual(results[1].data, "foo")
    self.assertEqual(results[1].offset, 8)
    self.assertEqual(results[1].length, 3)

  def testFirstHit(self):
    with open(self.temp_filepath, "wb") as fd:
      fd.write("bar foo baz foo")

    params = rdf_file_finder.FileFinderCondition()
    params.contents_literal_match.literal = "foo"
    params.contents_literal_match.mode = "FIRST_HIT"
    condition = client_file_finder.LiteralMatchCondition(params)

    results = list(condition.Search(self.temp_filepath))
    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].data, "foo")
    self.assertEqual(results[0].offset, 4)
    self.assertEqual(results[0].length, 3)

  def testContext(self):
    with open(self.temp_filepath, "wb") as fd:
      fd.write("foo foo foo")

    params = rdf_file_finder.FileFinderCondition()
    params.contents_literal_match.literal = "foo"
    params.contents_literal_match.mode = "ALL_HITS"
    params.contents_literal_match.bytes_before = 3
    params.contents_literal_match.bytes_after = 2
    condition = client_file_finder.LiteralMatchCondition(params)

    results = list(condition.Search(self.temp_filepath))
    self.assertEqual(len(results), 3)
    self.assertEqual(results[0].data, "foo f")
    self.assertEqual(results[0].offset, 0)
    self.assertEqual(results[0].length, 5)
    self.assertEqual(results[1].data, "oo foo f")
    self.assertEqual(results[1].offset, 1)
    self.assertEqual(results[1].length, 8)
    self.assertEqual(results[2].data, "oo foo")
    self.assertEqual(results[2].offset, 5)
    self.assertEqual(results[2].length, 6)

  def testStartOffset(self):
    with open(self.temp_filepath, "wb") as fd:
      fd.write("oooooooo")

    params = rdf_file_finder.FileFinderCondition()
    params.contents_literal_match.literal = "ooo"
    params.contents_literal_match.mode = "ALL_HITS"
    params.contents_literal_match.start_offset = 2
    condition = client_file_finder.LiteralMatchCondition(params)

    results = list(condition.Search(self.temp_filepath))
    self.assertEqual(len(results), 2)
    self.assertEqual(results[0].data, "ooo")
    self.assertEqual(results[0].offset, 2)
    self.assertEqual(results[0].length, 3)
    self.assertEqual(results[1].data, "ooo")
    self.assertEqual(results[1].offset, 5)
    self.assertEqual(results[1].length, 3)


class RegexMatchCondition(ConditionTestMixin, unittest.TestCase):

  def testNoHits(self):
    with open(self.temp_filepath, "wb") as fd:
      fd.write("foo bar quux")

    params = rdf_file_finder.FileFinderCondition()
    params.contents_regex_match.regex = "\\d+"
    params.contents_regex_match.mode = "FIRST_HIT"
    condition = client_file_finder.RegexMatchCondition(params)

    results = list(condition.Search(self.temp_filepath))
    self.assertFalse(results)

  def testSomeHits(self):
    with open(self.temp_filepath, "wb") as fd:
      fd.write("foo 7 bar 49 baz343")

    params = rdf_file_finder.FileFinderCondition()
    params.contents_regex_match.regex = "\\d+"
    params.contents_regex_match.mode = "ALL_HITS"
    condition = client_file_finder.RegexMatchCondition(params)

    results = list(condition.Search(self.temp_filepath))
    self.assertEqual(len(results), 3)
    self.assertEqual(results[0].data, "7")
    self.assertEqual(results[0].offset, 4)
    self.assertEqual(results[0].length, 1)
    self.assertEqual(results[1].data, "49")
    self.assertEqual(results[1].offset, 10)
    self.assertEqual(results[1].length, 2)
    self.assertEqual(results[2].data, "343")
    self.assertEqual(results[2].offset, 16)
    self.assertEqual(results[2].length, 3)

  def testFirstHit(self):
    with open(self.temp_filepath, "wb") as fd:
      fd.write("4 8 15 16 23 42 foo 108 bar")

    params = rdf_file_finder.FileFinderCondition()
    params.contents_regex_match.regex = "[a-z]+"
    params.contents_regex_match.mode = "FIRST_HIT"
    condition = client_file_finder.RegexMatchCondition(params)

    results = list(condition.Search(self.temp_filepath))
    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].data, "foo")
    self.assertEqual(results[0].offset, 16)
    self.assertEqual(results[0].length, 3)

  def testContext(self):
    with open(self.temp_filepath, "wb") as fd:
      fd.write("foobarbazbaaarquux")

    params = rdf_file_finder.FileFinderCondition()
    params.contents_regex_match.regex = "ba+r"
    params.contents_regex_match.mode = "ALL_HITS"
    params.contents_regex_match.bytes_before = 3
    params.contents_regex_match.bytes_after = 4
    condition = client_file_finder.RegexMatchCondition(params)

    results = list(condition.Search(self.temp_filepath))
    self.assertEqual(len(results), 2)
    self.assertEqual(results[0].data, "foobarbazb")
    self.assertEqual(results[0].offset, 0)
    self.assertEqual(results[0].length, 10)
    self.assertEqual(results[1].data, "bazbaaarquux")
    self.assertEqual(results[1].offset, 6)
    self.assertEqual(results[1].length, 12)

  def testStartOffset(self):
    with open(self.temp_filepath, "wb") as fd:
      fd.write("ooooooo")

    params = rdf_file_finder.FileFinderCondition()
    params.contents_regex_match.regex = "o+"
    params.contents_regex_match.mode = "FIRST_HIT"
    params.contents_regex_match.start_offset = 3
    condition = client_file_finder.RegexMatchCondition(params)

    results = list(condition.Search(self.temp_filepath))
    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].data, "oooo")
    self.assertEqual(results[0].offset, 3)
    self.assertEqual(results[0].length, 4)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
