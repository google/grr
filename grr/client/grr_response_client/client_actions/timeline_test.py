#!/usr/bin/env python
# Lint as: python3
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import ctypes
import hashlib
import io
import os
import platform
import random
import stat as stat_mode
import time
from typing import Text

from absl.testing import absltest

from grr_response_client.client_actions import timeline
from grr_response_core.lib.rdfvalues import timeline as rdf_timeline
from grr_response_core.lib.util import temp
from grr.test_lib import client_test_lib
from grr.test_lib import skip
from grr.test_lib import testing_startup


# TODO(hanuszczak): `GRRBaseTest` is terrible, try to avoid it in any new code.
class TimelineTest(client_test_lib.EmptyActionTest):

  @classmethod
  def setUpClass(cls):
    super(TimelineTest, cls).setUpClass()
    testing_startup.TestInit()

  def testRun(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      for idx in range(64):
        temp_filepath = os.path.join(temp_dirpath, "foo{}".format(idx))
        _Touch(temp_filepath, content=os.urandom(random.randint(0, 1024)))

      args = rdf_timeline.TimelineArgs()
      args.root = temp_dirpath.encode("utf-8")

      results = self.RunAction(timeline.Timeline, args)

      self.assertNotEmpty(results)
      self.assertNotEmpty(results[-1].entry_batch_blob_ids)

      blob_ids = results[-1].entry_batch_blob_ids
      for blob in results[:-1]:
        self.assertIn(hashlib.sha256(blob.data).digest(), blob_ids)


class WalkTest(absltest.TestCase):

  def testSingleFile(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as dirpath:
      filepath = os.path.join(dirpath, "foo")
      _Touch(filepath, content=b"foobar")

      entries = list(timeline.Walk(dirpath.encode("utf-8")))
      self.assertLen(entries, 2)

      self.assertTrue(stat_mode.S_ISDIR(entries[0].mode))
      self.assertEqual(entries[0].path, dirpath.encode("utf-8"))

      self.assertTrue(stat_mode.S_ISREG(entries[1].mode))
      self.assertEqual(entries[1].path, filepath.encode("utf-8"))
      self.assertEqual(entries[1].size, 6)

  def testMultipleFiles(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as dirpath:
      foo_filepath = os.path.join(dirpath, "foo")
      bar_filepath = os.path.join(dirpath, "bar")
      baz_filepath = os.path.join(dirpath, "baz")

      _Touch(foo_filepath)
      _Touch(bar_filepath)
      _Touch(baz_filepath)

      entries = list(timeline.Walk(dirpath.encode("utf-8")))
      self.assertLen(entries, 4)

      paths = [_.path for _ in entries[1:]]
      self.assertIn(foo_filepath.encode("utf-8"), paths)
      self.assertIn(bar_filepath.encode("utf-8"), paths)
      self.assertIn(baz_filepath.encode("utf-8"), paths)

  def testNestedDirectories(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as root_dirpath:
      foobar_dirpath = os.path.join(root_dirpath, "foo", "bar")
      os.makedirs(foobar_dirpath)

      foobaz_dirpath = os.path.join(root_dirpath, "foo", "baz")
      os.makedirs(foobaz_dirpath)

      quuxnorfthud_dirpath = os.path.join(root_dirpath, "quux", "norf", "thud")
      os.makedirs(quuxnorfthud_dirpath)

      entries = list(timeline.Walk(root_dirpath.encode("utf-8")))
      self.assertLen(entries, 7)

      paths = [_.path.decode("utf-8") for _ in entries]
      self.assertCountEqual(paths, [
          os.path.join(root_dirpath),
          os.path.join(root_dirpath, "foo"),
          os.path.join(root_dirpath, "foo", "bar"),
          os.path.join(root_dirpath, "foo", "baz"),
          os.path.join(root_dirpath, "quux"),
          os.path.join(root_dirpath, "quux", "norf"),
          os.path.join(root_dirpath, "quux", "norf", "thud"),
      ])

      for entry in entries:
        self.assertTrue(stat_mode.S_ISDIR(entry.mode))

  @skip.If(
      platform.system() == "Windows",
      reason="Symlinks are not supported on Windows.")
  def testSymlinks(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as root_dirpath:
      sub_dirpath = os.path.join(root_dirpath, "foo", "bar", "baz")
      link_path = os.path.join(sub_dirpath, "quux")

      # This creates a cycle, walker should be able to cope with that.
      os.makedirs(sub_dirpath)
      os.symlink(root_dirpath, os.path.join(sub_dirpath, link_path))

      entries = list(timeline.Walk(root_dirpath.encode("utf-8")))
      self.assertLen(entries, 5)

      paths = [_.path.decode("utf-8") for _ in entries]
      self.assertEqual(paths, [
          os.path.join(root_dirpath),
          os.path.join(root_dirpath, "foo"),
          os.path.join(root_dirpath, "foo", "bar"),
          os.path.join(root_dirpath, "foo", "bar", "baz"),
          os.path.join(root_dirpath, "foo", "bar", "baz", "quux")
      ])

      for entry in entries[:-1]:
        self.assertTrue(stat_mode.S_ISDIR(entry.mode))
      self.assertTrue(stat_mode.S_ISLNK(entries[-1].mode))

  @skip.Unless(hasattr(time, "time_ns"), reason="timing precision too low")
  def testTimestamp(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as dirpath:
      filepath = os.path.join(dirpath, "foo")

      with open(filepath, mode="wb"):
        pass

      with open(filepath, mode="wb") as filedesc:
        filedesc.write(b"quux")

      with open(filepath, mode="rb") as filedesc:
        _ = filedesc.read()

      now_ns = time.time_ns()

      entries = list(timeline.Walk(dirpath.encode("utf-8")))
      self.assertLen(entries, 2)

      self.assertEqual(entries[0].path, dirpath.encode("utf-8"))
      self.assertEqual(entries[1].path, filepath.encode("utf-8"))

      self.assertGreater(entries[1].ctime_ns, 0)
      self.assertGreaterEqual(entries[1].mtime_ns, entries[1].ctime_ns)
      self.assertGreaterEqual(entries[1].atime_ns, entries[1].mtime_ns)
      self.assertLess(entries[1].atime_ns, now_ns)

  @skip.Unless(hasattr(time, "time_ns"), reason="timing precision too low")
  def testBirthTimestamp(self):
    if platform.system() == "Linux":
      try:
        ctypes.CDLL("libc.so.6").statx
      except AttributeError:
        raise absltest.SkipTest("`statx` not available")

    with temp.AutoTempDirPath(remove_non_empty=True) as dirpath:
      filepath = os.path.join(dirpath, "foo")

      with open(filepath, mode="wb") as filedesc:
        filedesc.write(b"foobar")

      entries = list(timeline.Walk(dirpath.encode("utf-8")))
      self.assertLen(entries, 2)

      self.assertEqual(entries[0].path, dirpath.encode("utf-8"))
      self.assertEqual(entries[1].path, filepath.encode("utf-8"))

      now_ns = time.time_ns()
      self.assertBetween(entries[1].btime_ns, 0, now_ns)

  def testIncorrectPath(self):
    not_existing_path = os.path.join("some", "not", "existing", "path")

    entries = list(timeline.Walk(not_existing_path.encode("utf-8")))
    self.assertEmpty(entries)


def _Touch(filepath: Text, content: bytes = b"") -> None:
  with io.open(filepath, mode="wb") as filedesc:
    filedesc.write(content)


if __name__ == "__main__":
  absltest.main()
