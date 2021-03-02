#!/usr/bin/env python
import contextlib
import datetime
import os
import time
from typing import Optional, BinaryIO
from unittest import mock
from absl.testing import absltest
import dateutil
from google.protobuf import timestamp_pb2
from grr_response_client.unprivileged import communication
from grr_response_client.unprivileged.filesystem import client
from grr_response_client.unprivileged.filesystem import server
from grr_response_client.unprivileged.proto import filesystem_pb2
from grr_response_core import config

# File references manually extracted from ntfs.img.
A_FILE_REF = 281474976710721
ADS_FILE_REF = 1125899906842697
ADS_ADS_TXT_FILE_REF = 562949953421386
NUMBERS_TXT_FILE_REF = 281474976710720
A_B1_C1_D_FILE_REF = 281474976710728
READ_ONLY_FILE_TXT_FILE_REF = 844424930132043
HIDDEN_FILE_TXT_FILE_REF = 562949953421388
CHINESE_FILE_FILE_REF = 844424930132045

# See
# https://github.com/libyal/libfsntfs/blob/master/documentation/New%20Technologies%20File%20System%20(NTFS).asciidoc#file_attribute_flags
FILE_ATTRIBUTE_READONLY = 0x00000001
FILE_ATTRIBUTE_HIDDEN = 0x00000002
FILE_ATTRIBUTE_ARCHIVE = 0x00000020

# Default StatEntry.ntfs values for files and directories
S_DEFAULT_FILE = filesystem_pb2.StatEntry.Ntfs(
    is_directory=False, flags=FILE_ATTRIBUTE_ARCHIVE)
S_DEFAULT_DIR = filesystem_pb2.StatEntry.Ntfs(
    is_directory=True, flags=FILE_ATTRIBUTE_ARCHIVE)


def _FormatTimestamp(timestamp: timestamp_pb2.Timestamp) -> str:
  dt = timestamp.ToDatetime()
  return dt.strftime("%Y-%m-%d %H:%M:%S")


def _ParseTimestamp(s: str) -> timestamp_pb2.Timestamp:
  default = datetime.datetime(  # pylint: disable=g-tzinfo-datetime
      time.gmtime().tm_year,
      1,
      1,
      0,
      0,
      tzinfo=dateutil.tz.tzutc())
  dt = dateutil.parser.parse(s, default=default)
  result = timestamp_pb2.Timestamp()
  result.FromDatetime(dt)
  return result


class NtfsTestBase(absltest.TestCase):

  _server: Optional[communication.Server] = None
  _client: Optional[client.Client] = None

  def testRead(self):
    with self._client.Open(path="\\numbers.txt") as file_obj:
      data = file_obj.Read(offset=0, size=50)
      self.assertEqual(
          data,
          b"1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n12\n13\n14\n15\n16\n17\n18\n19\n20"
      )

  def testNonExistent(self):
    with self.assertRaises(client.OperationError):
      self._client.Open(path="\\nonexistent.txt")

  def testNestedFile(self):
    with self._client.Open(path="\\a\\b1\\c1\\d") as file_obj:
      self.assertEqual(file_obj.Read(0, 100), b"foo\n")
      result = file_obj.Stat()
      self.assertEqual(result.st_ino, A_B1_C1_D_FILE_REF)

  def testOpenByInode(self):
    with self._client.OpenByInode(inode=A_B1_C1_D_FILE_REF) as file_obj:
      self.assertEqual(file_obj.Read(0, 100), b"foo\n")

  def testOpenByInode_stale(self):
    with self.assertRaises(client.StaleInodeError):
      # Overwrite the version in the upper 16 bits.
      stale_inode = A_B1_C1_D_FILE_REF | (0xFFFF << 48)
      self._client.OpenByInode(inode=stale_inode)

  def testStat(self):
    with self._client.Open(path="numbers.txt") as file_obj:

      s = file_obj.Stat()
      self.assertEqual(s.name, "numbers.txt")
      self.assertEqual(s.st_ino, NUMBERS_TXT_FILE_REF)
      self.assertEqual(_FormatTimestamp(s.st_atime), "2020-03-03 20:10:46")
      self.assertEqual(_FormatTimestamp(s.st_mtime), "2020-03-03 20:10:46")
      self.assertEqual(_FormatTimestamp(s.st_btime), "2020-03-03 16:46:00")
      self.assertEqual(s.st_size, 3893)

  def testListFiles(self):
    with self._client.Open(path="\\") as file_obj:
      files = file_obj.ListFiles()
      files = [f for f in files if not f.name.startswith("$")]
      files = list(files)
      files.sort(key=lambda x: x.name)
      expected_files = [
          filesystem_pb2.StatEntry(
              name="a",
              st_ino=A_FILE_REF,
              st_atime=_ParseTimestamp("2020-03-03 16:48:16.371823"),
              st_btime=_ParseTimestamp("2020-03-03 16:47:43.605063"),
              st_mtime=_ParseTimestamp("2020-03-03 16:47:50.945764"),
              st_ctime=_ParseTimestamp("2020-03-03 16:47:50.945764"),
              ntfs=S_DEFAULT_DIR,
          ),
          filesystem_pb2.StatEntry(
              name="ads",
              st_ino=ADS_FILE_REF,
              st_atime=_ParseTimestamp("2020-04-07 14:57:02.655592"),
              st_btime=_ParseTimestamp("2020-04-07 13:23:07.389499"),
              st_mtime=_ParseTimestamp("2020-04-07 14:56:47.778178"),
              st_ctime=_ParseTimestamp("2020-04-07 14:56:47.778178"),
              ntfs=S_DEFAULT_DIR,
          ),
          filesystem_pb2.StatEntry(
              name="hidden_file.txt",
              st_ino=HIDDEN_FILE_TXT_FILE_REF,
              st_atime=_ParseTimestamp("2020-04-08 20:14:38.260081"),
              st_btime=_ParseTimestamp("2020-04-08 20:14:38.259955"),
              st_mtime=_ParseTimestamp("2020-04-08 20:14:38.260081"),
              st_ctime=_ParseTimestamp("2020-04-08 20:15:07.835354"),
              ntfs=filesystem_pb2.StatEntry.Ntfs(
                  is_directory=False,
                  flags=FILE_ATTRIBUTE_ARCHIVE | FILE_ATTRIBUTE_HIDDEN),
              st_size=0,
          ),
          filesystem_pb2.StatEntry(
              name="numbers.txt",
              st_ino=NUMBERS_TXT_FILE_REF,
              st_atime=_ParseTimestamp("2020-03-03 20:10:46.353317"),
              st_btime=_ParseTimestamp("2020-03-03 16:46:00.630537"),
              st_mtime=_ParseTimestamp("2020-03-03 20:10:46.353317"),
              st_ctime=_ParseTimestamp("2020-03-03 20:10:46.353317"),
              ntfs=S_DEFAULT_FILE,
              st_size=3893,
          ),
          filesystem_pb2.StatEntry(
              name="read_only_file.txt",
              st_ino=READ_ONLY_FILE_TXT_FILE_REF,
              st_atime=_ParseTimestamp("2020-04-08 20:14:33.306681"),
              st_btime=_ParseTimestamp("2020-04-08 20:14:33.306441"),
              st_mtime=_ParseTimestamp("2020-04-08 20:14:33.306681"),
              st_ctime=_ParseTimestamp("2020-04-08 20:14:55.254657"),
              ntfs=filesystem_pb2.StatEntry.Ntfs(
                  is_directory=False,
                  flags=FILE_ATTRIBUTE_ARCHIVE | FILE_ATTRIBUTE_READONLY),
              st_size=0,
          ),
          filesystem_pb2.StatEntry(
              name="入乡随俗 海外春节别样过法.txt",
              st_ino=CHINESE_FILE_FILE_REF,
              st_atime=_ParseTimestamp("2020-06-10 13:34:36.872637"),
              st_btime=_ParseTimestamp("2020-06-10 13:34:36.872637"),
              st_mtime=_ParseTimestamp("2020-06-10 13:34:36.872802"),
              st_ctime=_ParseTimestamp("2020-06-10 13:34:36.872802"),
              ntfs=S_DEFAULT_FILE,
              st_size=26,
          ),
      ]
      self.assertEqual(files, expected_files)

  def testListFiles_alternateDataStreams(self):
    with self._client.Open(path="\\ads") as file_obj:
      files = file_obj.ListFiles()
      files = list(files)
      files.sort(key=lambda x: x.name)
      expected_files = [
          filesystem_pb2.StatEntry(
              name="ads.txt",
              st_ino=ADS_ADS_TXT_FILE_REF,
              st_atime=_ParseTimestamp("2020-04-07 13:48:51.172681"),
              st_btime=_ParseTimestamp("2020-04-07 13:18:53.793003"),
              st_mtime=_ParseTimestamp("2020-04-07 13:48:56.308416"),
              st_ctime=_ParseTimestamp("2020-04-07 13:48:56.308416"),
              ntfs=S_DEFAULT_FILE,
              st_size=5,
          ),
          filesystem_pb2.StatEntry(
              name="ads.txt",
              st_ino=ADS_ADS_TXT_FILE_REF,
              stream_name="one",
              st_atime=_ParseTimestamp("2020-04-07 13:48:51.172681"),
              st_btime=_ParseTimestamp("2020-04-07 13:18:53.793003"),
              st_mtime=_ParseTimestamp("2020-04-07 13:48:56.308416"),
              st_ctime=_ParseTimestamp("2020-04-07 13:48:56.308416"),
              ntfs=S_DEFAULT_FILE,
              st_size=6,
          ),
          filesystem_pb2.StatEntry(
              name="ads.txt",
              st_ino=ADS_ADS_TXT_FILE_REF,
              stream_name="two",
              st_atime=_ParseTimestamp("2020-04-07 13:48:51.172681"),
              st_btime=_ParseTimestamp("2020-04-07 13:18:53.793003"),
              st_mtime=_ParseTimestamp("2020-04-07 13:48:56.308416"),
              st_ctime=_ParseTimestamp("2020-04-07 13:48:56.308416"),
              ntfs=S_DEFAULT_FILE,
              st_size=7,
          ),
      ]
      self.assertEqual(files, expected_files)

  def testOpen_alternateDataStreams(self):
    with self._client.Open(path="\\ads\\ads.txt") as file_obj:
      self.assertEqual(file_obj.Read(0, 100), b"Foo.\n")

    with self._client.Open(
        path="\\ads\\ads.txt", stream_name="one") as file_obj:
      self.assertEqual(file_obj.Read(0, 100), b"Bar..\n")

    with self._client.Open(
        path="\\ads\\ads.txt", stream_name="two") as file_obj:
      self.assertEqual(file_obj.Read(0, 100), b"Baz...\n")

  def testOpen_alternateDataStreams_invalid(self):
    with self.assertRaises(client.OperationError):
      self._client.Open(path="\\ads\\ads.txt", stream_name="invalid")

  def testStat_alternateDataStreams(self):

    with self._client.Open(
        path="\\ads\\ads.txt", stream_name="one") as file_obj:
      s = file_obj.Stat()
      self.assertEqual(s.name, "ads.txt")
      self.assertEqual(s.stream_name, "one")
      self.assertEqual(_FormatTimestamp(s.st_atime), "2020-04-07 13:48:51")
      self.assertEqual(_FormatTimestamp(s.st_mtime), "2020-04-07 13:48:56")
      self.assertEqual(_FormatTimestamp(s.st_btime), "2020-04-07 13:18:53")
      self.assertEqual(s.st_size, 6)

  def testOpenByInode_alternateDataStreams(self):
    with self._client.OpenByInode(
        inode=ADS_ADS_TXT_FILE_REF, stream_name="one") as file_obj:
      self.assertEqual(file_obj.Read(0, 100), b"Bar..\n")

  def testListFiles_alternateDataStreams_fileOnly(self):
    with self._client.Open(path="\\ads\\ads.txt") as file_obj:
      files = file_obj.ListFiles()
      files = list(files)
      files.sort(key=lambda x: x.name)
      expected_files = [
          filesystem_pb2.StatEntry(
              name="ads.txt",
              st_ino=ADS_ADS_TXT_FILE_REF,
              stream_name="one",
              st_atime=_ParseTimestamp("2020-04-07 13:48:51.172681"),
              st_btime=_ParseTimestamp("2020-04-07 13:18:53.793003"),
              st_mtime=_ParseTimestamp("2020-04-07 13:48:56.308416"),
              st_ctime=_ParseTimestamp("2020-04-07 13:48:56.308416"),
              ntfs=S_DEFAULT_FILE,
              st_size=6,
          ),
          filesystem_pb2.StatEntry(
              name="ads.txt",
              st_ino=ADS_ADS_TXT_FILE_REF,
              stream_name="two",
              st_atime=_ParseTimestamp("2020-04-07 13:48:51.172681"),
              st_btime=_ParseTimestamp("2020-04-07 13:18:53.793003"),
              st_mtime=_ParseTimestamp("2020-04-07 13:48:56.308416"),
              st_ctime=_ParseTimestamp("2020-04-07 13:48:56.308416"),
              ntfs=S_DEFAULT_FILE,
              st_size=7,
          ),
      ]
      self.assertEqual(files, expected_files)

  def testReadUnicode(self):
    with self._client.Open(path="\\入乡随俗 海外春节别样过法.txt") as file_obj:
      expected = "Chinese news\n中国新闻\n".encode("utf-8")
      self.assertEqual(file_obj.Read(0, 100), expected)


class NtfsWithRemoteDeviceTest(NtfsTestBase):
  """Test variant sharing the device via RPC calls with the server."""

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    cls._server = server.CreateFilesystemServer()
    cls._server.Start()

  @classmethod
  def tearDownClass(cls):
    cls._server.Stop()
    super().tearDownClass()

  def setUp(self):
    super().setUp()
    stack = contextlib.ExitStack()
    self.addCleanup(stack.close)

    ntfs_image = stack.enter_context(
        open(os.path.join(config.CONFIG["Test.data_dir"], "ntfs.img"), "rb"))

    # The FileDevice won't return a file descriptor.
    stack.enter_context(
        mock.patch.object(client.FileDevice, "file_descriptor", None))

    self._client = stack.enter_context(
        client.CreateFilesystemClient(self._server.Connect(),
                                      filesystem_pb2.NTFS,
                                      client.FileDevice(ntfs_image)))


class NtfsWithFileDescriptorSharingTest(NtfsTestBase):
  """Test variant sharing a file descriptor of the device with the server."""

  _ntfs_image: BinaryIO = None

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    cls._ntfs_image = open(
        os.path.join(config.CONFIG["Test.data_dir"], "ntfs.img"), "rb")
    cls._server = server.CreateFilesystemServer(cls._ntfs_image.fileno())
    cls._server.Start()

  @classmethod
  def tearDownClass(cls):
    cls._server.Stop()
    cls._ntfs_image.close()
    super().tearDownClass()

  def setUp(self):
    super().setUp()
    stack = contextlib.ExitStack()
    self.addCleanup(stack.close)

    self._client = stack.enter_context(
        client.CreateFilesystemClient(self._server.Connect(),
                                      filesystem_pb2.NTFS,
                                      client.FileDevice(self._ntfs_image)))


# Don't run tests from the base class.
# TODO(user): Remove this once there
# is support for abstract test cases.
del NtfsTestBase

if __name__ == "__main__":
  absltest.main()
