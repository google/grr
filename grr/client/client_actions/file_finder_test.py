#!/usr/bin/env python
"""Tests the client file finder action."""

import collections
import glob
import hashlib
import os
import shutil

import psutil

from grr.client.client_actions import file_finder as client_file_finder
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import file_finder as rdf_file_finder
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
    self.stat_action = rdf_file_finder.FileFinderAction(
        action_type=rdf_file_finder.FileFinderAction.Action.STAT)

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
            bytes_after=bytes_after,))
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
            bytes_after=bytes_after,))
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
      stat_action = rdf_file_finder.FileFinderAction(
          action_type=rdf_file_finder.FileFinderAction.Action.STAT,
          stat=rdf_file_finder.FileFinderStatActionOptions(
              resolve_links=resolve_links))
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


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
