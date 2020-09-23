#!/usr/bin/env python
# Lint as: python3
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io
import os
import random
import stat as stat_mode
import time

from absl.testing import absltest

from grr_response_core.lib.rdfvalues import timeline as rdf_timeline
from grr_response_core.lib.util import statx
from grr_response_core.lib.util import temp


class TimelineEntryTest(absltest.TestCase):

  def testFromStat(self):
    with temp.AutoTempFilePath() as filepath:
      time_before = round(time.time())

      with io.open(filepath, mode="wb") as filedesc:
        filedesc.write(b"1234567")

      time_after = round(time.time())

      # TODO(hanuszczak): `AutoTempFilePath` should return a `Path` object.
      filepath_bytes = filepath.encode("utf-8")
      filepath_stat = os.lstat(filepath)

      entry = rdf_timeline.TimelineEntry.FromStat(filepath_bytes, filepath_stat)

      self.assertEqual(entry.size, 7)
      self.assertTrue(stat_mode.S_ISREG(entry.mode))

      # TODO(hanuszczak): Switch this test to use nanosecond precision once we
      # are Python 3.7-only.
      self.assertBetween(round(entry.atime_ns / 1e9), time_before, time_after)
      self.assertBetween(round(entry.mtime_ns / 1e9), time_before, time_after)
      self.assertBetween(round(entry.ctime_ns / 1e9), time_before, time_after)

      self.assertEqual(entry.dev, filepath_stat.st_dev)
      self.assertEqual(entry.ino, filepath_stat.st_ino)
      self.assertEqual(entry.uid, filepath_stat.st_uid)
      self.assertEqual(entry.gid, filepath_stat.st_gid)

  def testFromStatx(self):
    with temp.AutoTempFilePath() as filepath:
      filepath = filepath.encode("utf-8")

      with open(filepath, mode="wb") as filedesc:
        filedesc.write(b"1234567")

      statx_result = statx.Get(filepath)
      entry = rdf_timeline.TimelineEntry.FromStatx(filepath, statx_result)

      self.assertEqual(entry.size, 7)
      self.assertTrue(stat_mode.S_ISREG(entry.mode))

      self.assertEqual(entry.dev, statx_result.dev)
      self.assertEqual(entry.ino, statx_result.ino)
      self.assertEqual(entry.uid, statx_result.uid)
      self.assertEqual(entry.gid, statx_result.gid)
      self.assertEqual(entry.attributes, statx_result.attributes)

      self.assertEqual(entry.atime_ns, statx_result.atime_ns)
      self.assertEqual(entry.btime_ns, statx_result.btime_ns)
      self.assertEqual(entry.ctime_ns, statx_result.ctime_ns)
      self.assertEqual(entry.mtime_ns, statx_result.mtime_ns)

  def testSerializeAndDeserializeStream(self):
    serialize = rdf_timeline.TimelineEntry.SerializeStream
    deserialize = rdf_timeline.TimelineEntry.DeserializeStream

    def RandomEntry() -> rdf_timeline.TimelineEntry:
      entry = rdf_timeline.TimelineEntry()
      entry.path = os.urandom(4096)
      entry.mode = random.randint(0x0000, 0xFFFF - 1)
      entry.size = random.randint(0, 1e9)
      return entry

    entries = [RandomEntry() for _ in range(3000)]

    self.assertEqual(list(deserialize(serialize(iter(entries)))), entries)


if __name__ == "__main__":
  absltest.main()
