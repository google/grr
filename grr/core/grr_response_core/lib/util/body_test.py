#!/usr/bin/env python
# Lint as: python3
import csv
import io

from absl.testing import absltest

from grr_response_core.lib.rdfvalues import timeline as rdf_timeline
from grr_response_core.lib.util import body


class StreamTest(absltest.TestCase):

  def testSingle(self):
    entry = rdf_timeline.TimelineEntry()
    entry.path = "/foo/bar/baz".encode("utf-8")
    entry.mode = 0o100644
    entry.size = 42
    entry.dev = 101
    entry.ino = 404
    entry.uid = 13
    entry.gid = 7
    entry.atime_ns = 123 * 1_000_000_000
    entry.mtime_ns = 456 * 1_000_000_000
    entry.ctime_ns = 789 * 1_000_000_000

    content = b"".join(body.Stream(iter([entry]))).decode("utf-8")
    expected = "0|/foo/bar/baz|404|-rw-r--r--|13|7|42|123|456|789|0\n"

    self.assertEqual(content, expected)

  def testMultiple(self):
    entries = []

    for idx in range(100):
      entry = rdf_timeline.TimelineEntry()
      entry.path = "/foo/bar/baz{}".format(idx).encode("utf-8")
      entry.size = idx

      entries.append(entry)

    content = b"".join(body.Stream(iter(entries))).decode("utf-8")
    reader = csv.reader(io.StringIO(content), delimiter="|")

    rows = list(reader)
    self.assertLen(rows, len(entries))

    for idx, row in enumerate(rows):
      self.assertEqual(row[1].encode("utf-8"), entries[idx].path)
      self.assertEqual(int(row[6]), entries[idx].size)

  def testChunks(self):
    entries = []
    for idx in range(1024):
      entry = rdf_timeline.TimelineEntry()
      entry.path = "/foo/bar{}".format(idx).encode("utf-8")

      entries.append(entry)

    chunks = list(body.Stream(iter(entries), chunk_size=6))
    self.assertLen(chunks, len(entries))

    content = b"".join(chunks).decode("utf-8")
    reader = csv.reader(io.StringIO(content), delimiter="|")

    rows = list(reader)
    self.assertLen(rows, len(entries))

    for idx, row in enumerate(rows):
      self.assertEqual(row[1].encode("utf-8"), entries[idx].path)

  def testUnicode(self):
    entry = rdf_timeline.TimelineEntry()
    entry.path = "/zażółć/gęślą/jaźń/💪".encode("utf-8")

    content = b"".join(body.Stream(iter([entry]))).decode("utf-8")
    reader = csv.reader(io.StringIO(content), delimiter="|")

    rows = list(reader)
    self.assertLen(rows, 1)
    self.assertEqual(rows[0][1].encode("utf-8"), entry.path)

  # TODO(hanuszczak): Add tests for paths with `|` after making sure what is the
  # proper way of handling this in the body format.


if __name__ == "__main__":
  absltest.main()
