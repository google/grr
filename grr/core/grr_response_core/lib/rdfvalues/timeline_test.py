#!/usr/bin/env python
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

  def testSerializeAndDeserializeStream(self):
    serialize = rdf_timeline.TimelineEntry.SerializeStream
    deserialize = rdf_timeline.TimelineEntry.DeserializeStream

    def RandomEntry():
      entry = rdf_timeline.TimelineEntry()
      entry.path = os.urandom(4096)
      entry.mode = random.randint(0x0000, 0xFFFF - 1)
      entry.size = random.randint(0, 1e9)
      return entry

    entries = [RandomEntry() for _ in range(3000)]

    self.assertEqual(list(deserialize(serialize(iter(entries)))), entries)


if __name__ == "__main__":
  absltest.main()
