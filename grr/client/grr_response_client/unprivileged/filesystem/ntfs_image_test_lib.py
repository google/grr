#!/usr/bin/env python
# pylint: mode=test

import abc
import contextlib
import datetime
import os
import stat
import time
from typing import Optional
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


# Default StatEntry.ntfs values for files and directories
S_DEFAULT_FILE = filesystem_pb2.StatEntry.Ntfs(
    is_directory=False, flags=stat.FILE_ATTRIBUTE_ARCHIVE)  # pytype: disable=module-attr
S_DEFAULT_DIR = filesystem_pb2.StatEntry.Ntfs(
    is_directory=True, flags=stat.FILE_ATTRIBUTE_ARCHIVE)  # pytype: disable=module-attr

S_MODE_ALL = stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO
S_MODE_DIR = stat.S_IFDIR | S_MODE_ALL
S_MODE_DEFAULT = stat.S_IFREG | S_MODE_ALL
S_MODE_READ_ONLY = (
    stat.S_IFREG | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH | stat.S_IXUSR
    | stat.S_IXGRP | stat.S_IXOTH)
S_MODE_HIDDEN = (
    stat.S_IFREG | stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH | stat.S_IXUSR
    | stat.S_IXGRP | stat.S_IXOTH)


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


class NtfsImageTest(absltest.TestCase, abc.ABC):

  _IMPLEMENTATION_TYPE: Optional[int] = None

  _server: Optional[communication.Server] = None
  _client: Optional[client.Client] = None
  _exit_stack: Optional[contextlib.ExitStack] = None

  @abc.abstractmethod
  def _ExpectedStatEntry(
      self, st: filesystem_pb2.StatEntry) -> filesystem_pb2.StatEntry:
    """Fixes an expected StatEntry for the respective implementation."""
    pass

  @abc.abstractmethod
  def _FileRefToInode(self, file_ref: int) -> int:
    """Converts a file reference to an inode number."""
    pass

  @abc.abstractmethod
  def _Path(self, path: str) -> str:
    """Fixes a path for the respective implementation."""
    pass

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    cls._exit_stack = contextlib.ExitStack()

    ntfs_image = cls._exit_stack.enter_context(
        open(os.path.join(config.CONFIG["Test.data_dir"], "ntfs.img"), "rb"))
    cls._server = server.CreateFilesystemServer(ntfs_image.fileno())
    cls._server.Start()

    cls._client = cls._exit_stack.enter_context(
        client.CreateFilesystemClient(cls._server.Connect(),
                                      cls._IMPLEMENTATION_TYPE,
                                      client.FileDevice(ntfs_image)))

  @classmethod
  def tearDownClass(cls):
    cls._server.Stop()
    cls._exit_stack.close()
    super().tearDownClass()

  def testRead(self):
    with self._client.Open(path=self._Path("\\numbers.txt")) as file_obj:
      data = file_obj.Read(offset=0, size=50)
      self.assertEqual(
          data,
          b"1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n12\n13\n14\n15\n16\n17\n18\n19\n20"
      )

  def testNonExistent(self):
    with self.assertRaises(client.OperationError):
      self._client.Open(path=self._Path("\\nonexistent.txt"))

  def testNestedFile(self):
    with self._client.Open(path=self._Path("\\a\\b1\\c1\\d")) as file_obj:
      self.assertEqual(file_obj.Read(0, 100), b"foo\n")
      result = file_obj.Stat()
      self.assertEqual(result.st_ino, self._FileRefToInode(A_B1_C1_D_FILE_REF))

  def testRead_PastTheEnd(self):
    with self._client.Open(path=self._Path("\\a\\b1\\c1\\d")) as file_obj:
      data = file_obj.Read(0, 100)
      self.assertEqual(data, b"foo\n")
      self.assertEqual(file_obj.Read(len(data), 100), b"")

  def testOpenByInode(self):
    with self._client.OpenByInode(
        inode=self._FileRefToInode(A_B1_C1_D_FILE_REF)) as file_obj:
      self.assertEqual(file_obj.Read(0, 100), b"foo\n")

  def testOpenByInode_stale(self):
    with self.assertRaises(client.StaleInodeError):
      # Overwrite the version in the upper 16 bits.
      stale_inode = A_B1_C1_D_FILE_REF | (0xFFFF << 48)
      self._client.OpenByInode(inode=self._FileRefToInode(stale_inode))

  def testStat(self):
    with self._client.Open(path="numbers.txt") as file_obj:

      s = file_obj.Stat()
      self.assertEqual(s.name, "numbers.txt")
      self.assertEqual(s.st_ino, self._FileRefToInode(NUMBERS_TXT_FILE_REF))
      self.assertEqual(_FormatTimestamp(s.st_atime), "2020-03-03 20:10:46")
      self.assertEqual(_FormatTimestamp(s.st_mtime), "2020-03-03 20:10:46")
      self.assertEqual(_FormatTimestamp(s.st_btime), "2020-03-03 16:46:00")
      self.assertEqual(s.st_size, 3893)

  def testListFiles(self):
    with self._client.Open(path=self._Path("\\")) as file_obj:
      files = file_obj.ListFiles()
      files = [f for f in files if not f.name.startswith("$")]
      files = list(files)
      files.sort(key=lambda x: x.name)
      expected_files = [
          self._ExpectedStatEntry(
              filesystem_pb2.StatEntry(
                  name="a",
                  st_ino=self._FileRefToInode(A_FILE_REF),
                  st_atime=_ParseTimestamp("2020-03-03 16:48:16.371823"),
                  st_btime=_ParseTimestamp("2020-03-03 16:47:43.605063"),
                  st_mtime=_ParseTimestamp("2020-03-03 16:47:50.945764"),
                  st_ctime=_ParseTimestamp("2020-03-03 16:47:50.945764"),
                  ntfs=S_DEFAULT_DIR,
                  st_gid=0,
                  st_uid=48,
                  st_nlink=1,
                  st_mode=S_MODE_DIR,
              )),
          self._ExpectedStatEntry(
              filesystem_pb2.StatEntry(
                  name="ads",
                  st_ino=self._FileRefToInode(ADS_FILE_REF),
                  st_atime=_ParseTimestamp("2020-04-07 14:57:02.655592"),
                  st_btime=_ParseTimestamp("2020-04-07 13:23:07.389499"),
                  st_mtime=_ParseTimestamp("2020-04-07 14:56:47.778178"),
                  st_ctime=_ParseTimestamp("2020-04-07 14:56:47.778178"),
                  ntfs=S_DEFAULT_DIR,
                  st_gid=0,
                  st_uid=48,
                  st_nlink=1,
                  st_mode=S_MODE_DIR,
              )),
          self._ExpectedStatEntry(
              filesystem_pb2.StatEntry(
                  name="hidden_file.txt",
                  st_ino=self._FileRefToInode(HIDDEN_FILE_TXT_FILE_REF),
                  st_atime=_ParseTimestamp("2020-04-08 20:14:38.260081"),
                  st_btime=_ParseTimestamp("2020-04-08 20:14:38.259955"),
                  st_mtime=_ParseTimestamp("2020-04-08 20:14:38.260081"),
                  st_ctime=_ParseTimestamp("2020-04-08 20:15:07.835354"),
                  ntfs=filesystem_pb2.StatEntry.Ntfs(
                      is_directory=False,
                      flags=stat.FILE_ATTRIBUTE_ARCHIVE  # pytype: disable=module-attr
                      | stat.FILE_ATTRIBUTE_HIDDEN),  # pytype: disable=module-attr
                  st_size=0,
                  st_gid=0,
                  st_uid=48,
                  st_nlink=1,
                  st_mode=S_MODE_HIDDEN,
              )),
          self._ExpectedStatEntry(
              filesystem_pb2.StatEntry(
                  name="numbers.txt",
                  st_ino=self._FileRefToInode(NUMBERS_TXT_FILE_REF),
                  st_atime=_ParseTimestamp("2020-03-03 20:10:46.353317"),
                  st_btime=_ParseTimestamp("2020-03-03 16:46:00.630537"),
                  st_mtime=_ParseTimestamp("2020-03-03 20:10:46.353317"),
                  st_ctime=_ParseTimestamp("2020-03-03 20:10:46.353317"),
                  ntfs=S_DEFAULT_FILE,
                  st_size=3893,
                  st_gid=0,
                  st_uid=48,
                  st_nlink=1,
                  st_mode=S_MODE_DEFAULT,
              )),
          self._ExpectedStatEntry(
              filesystem_pb2.StatEntry(
                  name="read_only_file.txt",
                  st_ino=self._FileRefToInode(READ_ONLY_FILE_TXT_FILE_REF),
                  st_atime=_ParseTimestamp("2020-04-08 20:14:33.306681"),
                  st_btime=_ParseTimestamp("2020-04-08 20:14:33.306441"),
                  st_mtime=_ParseTimestamp("2020-04-08 20:14:33.306681"),
                  st_ctime=_ParseTimestamp("2020-04-08 20:14:55.254657"),
                  ntfs=filesystem_pb2.StatEntry.Ntfs(
                      is_directory=False,
                      flags=stat.FILE_ATTRIBUTE_ARCHIVE  # pytype: disable=module-attr
                      | stat.FILE_ATTRIBUTE_READONLY),  # pytype: disable=module-attr
                  st_size=0,
                  st_gid=0,
                  st_uid=48,
                  st_nlink=1,
                  st_mode=S_MODE_READ_ONLY,
              )),
          self._ExpectedStatEntry(
              filesystem_pb2.StatEntry(
                  name="入乡随俗 海外春节别样过法.txt",
                  st_ino=self._FileRefToInode(CHINESE_FILE_FILE_REF),
                  st_atime=_ParseTimestamp("2020-06-10 13:34:36.872637"),
                  st_btime=_ParseTimestamp("2020-06-10 13:34:36.872637"),
                  st_mtime=_ParseTimestamp("2020-06-10 13:34:36.872802"),
                  st_ctime=_ParseTimestamp("2020-06-10 13:34:36.872802"),
                  ntfs=S_DEFAULT_FILE,
                  st_size=26,
                  st_gid=0,
                  st_uid=48,
                  st_nlink=1,
                  st_mode=S_MODE_DEFAULT,
              )),
      ]
      self.assertEqual(files, expected_files)

  def testListNames(self):
    with self._client.Open(path=self._Path("\\")) as file_obj:
      names = file_obj.ListNames()
      stat_entries = file_obj.ListFiles()
      expected_names = [stat_entry.name for stat_entry in stat_entries]
      self.assertSameElements(names, expected_names)

  def testListFiles_alternateDataStreams(self):
    with self._client.Open(path=self._Path("\\ads")) as file_obj:
      files = file_obj.ListFiles()
      files = list(files)
      files.sort(key=lambda x: x.name)
      expected_files = [
          self._ExpectedStatEntry(
              filesystem_pb2.StatEntry(
                  name="ads.txt",
                  st_ino=self._FileRefToInode(ADS_ADS_TXT_FILE_REF),
                  st_atime=_ParseTimestamp("2020-04-07 13:48:51.172681"),
                  st_btime=_ParseTimestamp("2020-04-07 13:18:53.793003"),
                  st_mtime=_ParseTimestamp("2020-04-07 13:48:56.308416"),
                  st_ctime=_ParseTimestamp("2020-04-07 13:48:56.308416"),
                  ntfs=S_DEFAULT_FILE,
                  st_size=5,
                  st_gid=0,
                  st_uid=48,
                  st_nlink=1,
                  st_mode=S_MODE_DEFAULT,
              )),
          self._ExpectedStatEntry(
              filesystem_pb2.StatEntry(
                  name="ads.txt",
                  st_ino=self._FileRefToInode(ADS_ADS_TXT_FILE_REF),
                  stream_name="one",
                  st_atime=_ParseTimestamp("2020-04-07 13:48:51.172681"),
                  st_btime=_ParseTimestamp("2020-04-07 13:18:53.793003"),
                  st_mtime=_ParseTimestamp("2020-04-07 13:48:56.308416"),
                  st_ctime=_ParseTimestamp("2020-04-07 13:48:56.308416"),
                  ntfs=S_DEFAULT_FILE,
                  st_size=6,
                  st_gid=0,
                  st_uid=48,
                  st_nlink=1,
                  st_mode=S_MODE_DEFAULT,
              )),
          self._ExpectedStatEntry(
              filesystem_pb2.StatEntry(
                  name="ads.txt",
                  st_ino=self._FileRefToInode(ADS_ADS_TXT_FILE_REF),
                  stream_name="two",
                  st_atime=_ParseTimestamp("2020-04-07 13:48:51.172681"),
                  st_btime=_ParseTimestamp("2020-04-07 13:18:53.793003"),
                  st_mtime=_ParseTimestamp("2020-04-07 13:48:56.308416"),
                  st_ctime=_ParseTimestamp("2020-04-07 13:48:56.308416"),
                  ntfs=S_DEFAULT_FILE,
                  st_size=7,
                  st_gid=0,
                  st_uid=48,
                  st_nlink=1,
                  st_mode=S_MODE_DEFAULT,
              )),
      ]
      self.assertEqual(files, expected_files)

  def testListNames_alternateDataStreams(self):
    with self._client.Open(path=self._Path("\\ads\\ads.txt")) as file_obj:
      names = file_obj.ListNames()
      stat_entries = file_obj.ListFiles()
      expected_names = [stat_entry.stream_name for stat_entry in stat_entries]
      self.assertSameElements(names, expected_names)

  def testOpen_alternateDataStreams(self):
    with self._client.Open(path=self._Path("\\ads\\ads.txt")) as file_obj:
      self.assertEqual(file_obj.Read(0, 100), b"Foo.\n")

    with self._client.Open(
        path=self._Path("\\ads\\ads.txt"), stream_name="one") as file_obj:
      self.assertEqual(file_obj.Read(0, 100), b"Bar..\n")

    with self._client.Open(
        path=self._Path("\\ads\\ads.txt"), stream_name="two") as file_obj:
      self.assertEqual(file_obj.Read(0, 100), b"Baz...\n")

  def testOpen_alternateDataStreams_invalid(self):
    with self.assertRaises(client.OperationError):
      self._client.Open(
          path=self._Path("\\ads\\ads.txt"), stream_name="invalid")

  def testStat_alternateDataStreams(self):

    with self._client.Open(
        path=self._Path("\\ads\\ads.txt"), stream_name="one") as file_obj:
      s = file_obj.Stat()
      self.assertEqual(s.name, "ads.txt")
      self.assertEqual(s.stream_name, "one")
      self.assertEqual(_FormatTimestamp(s.st_atime), "2020-04-07 13:48:51")
      self.assertEqual(_FormatTimestamp(s.st_mtime), "2020-04-07 13:48:56")
      self.assertEqual(_FormatTimestamp(s.st_btime), "2020-04-07 13:18:53")
      self.assertEqual(s.st_size, 6)

  def testOpenByInode_alternateDataStreams(self):
    with self._client.OpenByInode(
        inode=self._FileRefToInode(ADS_ADS_TXT_FILE_REF),
        stream_name="one") as file_obj:
      self.assertEqual(file_obj.Read(0, 100), b"Bar..\n")

  def testListFiles_alternateDataStreams_fileOnly(self):
    with self._client.Open(path=self._Path("\\ads\\ads.txt")) as file_obj:
      files = file_obj.ListFiles()
      files = list(files)
      files.sort(key=lambda x: x.name)
      expected_files = [
          self._ExpectedStatEntry(
              filesystem_pb2.StatEntry(
                  name="ads.txt",
                  st_ino=self._FileRefToInode(ADS_ADS_TXT_FILE_REF),
                  stream_name="one",
                  st_atime=_ParseTimestamp("2020-04-07 13:48:51.172681"),
                  st_btime=_ParseTimestamp("2020-04-07 13:18:53.793003"),
                  st_mtime=_ParseTimestamp("2020-04-07 13:48:56.308416"),
                  st_ctime=_ParseTimestamp("2020-04-07 13:48:56.308416"),
                  ntfs=S_DEFAULT_FILE,
                  st_size=6,
                  st_gid=0,
                  st_uid=48,
                  st_nlink=1,
                  st_mode=S_MODE_DEFAULT,
              )),
          self._ExpectedStatEntry(
              filesystem_pb2.StatEntry(
                  name="ads.txt",
                  st_ino=self._FileRefToInode(ADS_ADS_TXT_FILE_REF),
                  stream_name="two",
                  st_atime=_ParseTimestamp("2020-04-07 13:48:51.172681"),
                  st_btime=_ParseTimestamp("2020-04-07 13:18:53.793003"),
                  st_mtime=_ParseTimestamp("2020-04-07 13:48:56.308416"),
                  st_ctime=_ParseTimestamp("2020-04-07 13:48:56.308416"),
                  ntfs=S_DEFAULT_FILE,
                  st_size=7,
                  st_gid=0,
                  st_uid=48,
                  st_nlink=1,
                  st_mode=S_MODE_DEFAULT,
              )),
      ]
      self.assertEqual(files, expected_files)

  def testReadUnicode(self):
    with self._client.Open(path=self._Path("\\入乡随俗 海外春节别样过法.txt")) as file_obj:
      expected = "Chinese news\n中国新闻\n".encode("utf-8")
      self.assertEqual(file_obj.Read(0, 100), expected)

  def testRead_fromDirectoryRaises(self):
    with self.assertRaisesRegex(client.OperationError,
                                "Attempting to read from a directory"):
      with self._client.Open(path=self._Path("\\a")) as file_obj:
        file_obj.Read(offset=0, size=1)
