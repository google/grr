#!/usr/bin/env python
import csv
import io

from absl.testing import absltest

from grr_response_core.lib.util import body
from grr_response_proto import timeline_pb2


class StreamTest(absltest.TestCase):

  def testSingle(self):
    entry = timeline_pb2.TimelineEntry()
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
    entry.btime_ns = 1337 * 1_000_000_000

    content = b"".join(body.Stream(iter([entry]))).decode("utf-8")
    expected = "0|/foo/bar/baz|404|-rw-r--r--|13|7|42|123|456|789|1337\n"

    self.assertEqual(content, expected)

  def testMultiple(self):
    entries = []

    for idx in range(100):
      entry = timeline_pb2.TimelineEntry()
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
      entry = timeline_pb2.TimelineEntry()
      entry.path = "/foo/bar{}".format(idx).encode("utf-8")

      entries.append(entry)

    opts = body.Opts()
    opts.chunk_size = 6

    chunks = list(body.Stream(iter(entries), opts=opts))
    self.assertLen(chunks, len(entries))

    content = b"".join(chunks).decode("utf-8")
    reader = csv.reader(io.StringIO(content), delimiter="|")

    rows = list(reader)
    self.assertLen(rows, len(entries))

    for idx, row in enumerate(rows):
      self.assertEqual(row[1].encode("utf-8"), entries[idx].path)

  def testUnicode(self):
    entry = timeline_pb2.TimelineEntry()
    entry.path = "/zażółć/gęślą/jaźń/💪".encode("utf-8")

    content = b"".join(body.Stream(iter([entry]))).decode("utf-8")
    reader = csv.reader(io.StringIO(content), delimiter="|")

    rows = list(reader)
    self.assertLen(rows, 1)
    self.assertEqual(rows[0][1].encode("utf-8"), entry.path)

  def testNonUnicode(self):
    entry = timeline_pb2.TimelineEntry()
    entry.path = b"/\xff\x00\x00/\xfb\xfa\xf5"

    content = b"".join(body.Stream(iter([entry])))
    self.assertIn(b"/\xff\x00\x00/\xfb\xfa\xf5", content)

  def testSubsecondPrecision(self):
    entry = timeline_pb2.TimelineEntry()
    entry.path = "/foo/bar".encode("utf-8")
    entry.atime_ns = 123_456_789_000

    opts = body.Opts()
    opts.timestamp_subsecond_precision = True

    stream = body.Stream(iter([entry]), opts=opts)
    content = b"".join(stream).decode("utf-8")

    self.assertIn("/foo/bar", content)
    self.assertIn("123.456789", content)

  def testNtfsFileReference(self):
    entry = timeline_pb2.TimelineEntry()
    entry.path = "/foo/bar".encode("utf-8")
    entry.ino = 1688849860339456

    opts = body.Opts()
    opts.inode_format = body.Opts.InodeFormat.NTFS_FILE_REFERENCE

    stream = body.Stream(iter([entry]), opts=opts)
    content = b"".join(stream).decode("utf-8")

    self.assertIn("/foo/bar", content)
    self.assertIn("75520-6", content)

  def testBackslashEscape(self):
    entry = timeline_pb2.TimelineEntry()
    entry.path = "C:\\Windows\\system32\\notepad.exe".encode("utf-8")

    opts = body.Opts()
    opts.backslash_escape = True

    stream = body.Stream(iter([entry]), opts=opts)
    content = b"".join(stream).decode("utf-8")

    self.assertIn("|C:\\\\Windows\\\\system32\\\\notepad.exe|", content)

  def testCarriageReturnEscape(self):
    entry = timeline_pb2.TimelineEntry()
    entry.path = "C:\\Foo\rBar\\Baz\r\rQuux".encode("utf-8")

    opts = body.Opts()
    opts.carriage_return_escape = True

    stream = body.Stream(iter([entry]), opts=opts)
    content = b"".join(stream).decode("utf-8")

    self.assertIn("|C:\\Foo\\rBar\\Baz\\r\\rQuux|", content)

  def testNonPrintableEscape(self):
    entry = timeline_pb2.TimelineEntry()
    entry.path = b"/f\x00b\x0ar\x1baz"

    opts = body.Opts()
    opts.non_printable_escape = True

    stream = body.Stream(iter([entry]), opts=opts)
    content = b"".join(stream).decode("utf-8")

    self.assertIn(r"|/f\x00b\x0ar\x1baz|", content)

  def testPathWithPipe(self):
    entry = timeline_pb2.TimelineEntry()
    entry.path = "/foo|bar/baz".encode("utf-8")

    stream = body.Stream(iter([entry]))
    content = b"".join(stream).decode("utf-8")

    self.assertIn("|/foo\\|bar/baz|", content)

  def testPathWithWhitespace(self):
    entry = timeline_pb2.TimelineEntry()
    entry.path = "/foo bar\tbaz\rquux   norf/thud".encode("utf-8")

    stream = body.Stream(iter([entry]))
    content = b"".join(stream).decode("utf-8")

    self.assertIn("|/foo bar\tbaz\rquux   norf/thud|", content)

  def testPathWithNewline(self):
    entry = timeline_pb2.TimelineEntry()
    entry.path = "/foo bar\nbaz\n\nquux/thud".encode("utf-8")

    stream = body.Stream(iter([entry]))
    content = b"".join(stream).decode("utf-8")

    self.assertIn("|/foo bar\\nbaz\\n\\nquux/thud|", content)

  def testPathWithQuote(self):
    entry = timeline_pb2.TimelineEntry()
    entry.path = '/foo"bar'.encode("utf-8")

    stream = body.Stream(iter([entry]))
    content = b"".join(stream).decode("utf-8")

    self.assertIn('|/foo"bar|', content)

  def testPathWithBackslash(self):
    entry = timeline_pb2.TimelineEntry()
    entry.path = "C:\\Windows\\system32".encode("utf-8")

    stream = body.Stream(iter([entry]))
    content = b"".join(stream).decode("utf-8")

    self.assertIn("|C:\\Windows\\system32|", content)

  def testPathWithCarriageReturn(self):
    entry = timeline_pb2.TimelineEntry()
    entry.path = "/foo/bar\rbaz/quux\r\rnorf".encode("utf-8")

    stream = body.Stream(iter([entry]))
    content = b"".join(stream).decode("utf-8")

    self.assertIn("|/foo/bar\rbaz/quux\r\rnorf|", content)

  def testModeWindows(self):
    entry_system32 = timeline_pb2.TimelineEntry()
    entry_system32.path = "C:\\Windows\\system32".encode("utf-8")
    entry_system32.attributes = 0x30

    entry_notepad = timeline_pb2.TimelineEntry()
    entry_notepad.path = "C:\\Windows\\system32\\notepad.exe".encode("utf-8")
    entry_notepad.attributes = 0x20

    entry_desktop = timeline_pb2.TimelineEntry()
    entry_desktop.path = "C:\\Users\\Public\\Desktop".encode("utf-8")
    entry_desktop.attributes = 0x13

    stream = body.Stream(iter([entry_system32, entry_notepad, entry_desktop]))
    content = b"".join(stream).decode("utf-8")

    self.assertIn("0|C:\\Windows\\system32|0|drwxrwxrwx|", content)
    self.assertIn("0|C:\\Windows\\system32\\notepad.exe|0|-rwxrwxrwx|", content)
    self.assertIn("0|C:\\Users\\Public\\Desktop|0|dr-xr-xr-x|", content)


if __name__ == "__main__":
  absltest.main()
