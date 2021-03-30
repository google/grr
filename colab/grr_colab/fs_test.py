#!/usr/bin/env python
import io
import os

from absl.testing import absltest
from absl.testing import flagsaver
import requests

from grr_colab import _api
from grr_colab import errors
from grr_colab import fs
from grr_colab import testing
from grr_response_core.lib.util import temp
from grr_response_proto import jobs_pb2
from grr_response_server import data_store


class FileSystemTest(testing.ColabE2ETest):

  FAKE_CLIENT_ID = 'C.0123456789abcdef'

  def testLs_ContainsFiles(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=FileSystemTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    dir_nodes = [
        # name, content
        ('file1', b'foo'),
        ('file2', b'foo\nbar'),
    ]

    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      for filename, file_content in dir_nodes:
        filepath = os.path.join(temp_dirpath, filename)
        with io.open(filepath, 'wb') as filedesc:
          filedesc.write(file_content)

      fs_obj = fs.FileSystem(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

      stat_entries = fs_obj.ls(temp_dirpath)
      stat_entries = sorted(stat_entries, key=lambda _: _.pathspec.path)
      self.assertLen(stat_entries, 2)

      self.assertEqual(stat_entries[0].pathspec.path,
                       os.path.join(temp_dirpath, 'file1'))
      self.assertEqual(stat_entries[0].st_size, 3)

      self.assertEqual(stat_entries[1].pathspec.path,
                       os.path.join(temp_dirpath, 'file2'))
      self.assertEqual(stat_entries[1].st_size, 7)

  def testLs_EmptyDirectory(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=FileSystemTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      fs_obj = fs.FileSystem(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

      stat_entries = fs_obj.ls(temp_dirpath)
      self.assertEmpty(stat_entries)

  def testLs_Recursive(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=FileSystemTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    dir_nodes = [
        'file0',
        os.path.join('dir1', 'file1'),
        os.path.join('dir2', 'file2'),
        os.path.join('dir2', 'file3'),
    ]

    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      os.mkdir(os.path.join(temp_dirpath, 'dir1'))
      os.mkdir(os.path.join(temp_dirpath, 'dir2'))
      for path in dir_nodes:
        with io.open(os.path.join(temp_dirpath, path), 'wb') as filedesc:
          filedesc.write(b'foo')

      fs_obj = fs.FileSystem(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

      stat_entries = fs_obj.ls(temp_dirpath, max_depth=5)
      stat_entries = sorted(stat_entries, key=lambda _: _.pathspec.path)

      self.assertLen(stat_entries, 6)
      self.assertEqual(stat_entries[0].pathspec.path,
                       os.path.join(temp_dirpath, 'dir1'))
      self.assertEqual(stat_entries[1].pathspec.path,
                       os.path.join(temp_dirpath, 'dir1', 'file1'))
      self.assertEqual(stat_entries[2].pathspec.path,
                       os.path.join(temp_dirpath, 'dir2'))
      self.assertEqual(stat_entries[3].pathspec.path,
                       os.path.join(temp_dirpath, 'dir2', 'file2'))
      self.assertEqual(stat_entries[4].pathspec.path,
                       os.path.join(temp_dirpath, 'dir2', 'file3'))
      self.assertEqual(stat_entries[5].pathspec.path,
                       os.path.join(temp_dirpath, 'file0'))

  def testLs_MaxDepth(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=FileSystemTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    dir_components = ['dir1', 'dir2', 'dir3', 'dir4', 'dir5']

    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      os.makedirs(os.path.join(temp_dirpath, *dir_components))

      fs_obj = fs.FileSystem(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

      stat_entries = fs_obj.ls(temp_dirpath, max_depth=3)
      stat_entries = sorted(stat_entries, key=lambda _: _.pathspec.path)

      self.assertLen(stat_entries, 3)
      self.assertEqual(stat_entries[0].pathspec.path,
                       os.path.join(temp_dirpath, 'dir1'))
      self.assertEqual(stat_entries[1].pathspec.path,
                       os.path.join(temp_dirpath, 'dir1', 'dir2'))
      self.assertEqual(stat_entries[2].pathspec.path,
                       os.path.join(temp_dirpath, 'dir1', 'dir2', 'dir3'))

  @testing.with_approval_checks
  def testLs_WithoutApproval(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=FileSystemTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    fs_obj = fs.FileSystem(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

    with self.assertRaises(errors.ApprovalMissingError) as context:
      fs_obj.ls('/foo/bar')

    self.assertEqual(context.exception.client_id, FileSystemTest.FAKE_CLIENT_ID)

  def testGlob_SingleFile(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=FileSystemTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      os.mkdir(os.path.join(temp_dirpath, 'dir'))
      os.mkdir(os.path.join(temp_dirpath, 'dir1'))
      os.mkdir(os.path.join(temp_dirpath, 'dir2'))

      fs_obj = fs.FileSystem(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

      stat_entries = fs_obj.glob(os.path.join(temp_dirpath, 'dir'))
      self.assertLen(stat_entries, 1)
      self.assertEqual(stat_entries[0].pathspec.path,
                       os.path.join(temp_dirpath, 'dir'))

  def testGlob_MultipleFiles(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=FileSystemTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      os.mkdir(os.path.join(temp_dirpath, 'dir'))
      os.mkdir(os.path.join(temp_dirpath, 'dir1'))
      os.mkdir(os.path.join(temp_dirpath, 'dir2'))
      os.mkdir(os.path.join(temp_dirpath, 'new_dir'))

      fs_obj = fs.FileSystem(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

      stat_entries = fs_obj.glob(os.path.join(temp_dirpath, 'dir*'))
      stat_entries = sorted(stat_entries, key=lambda _: _.pathspec.path)

      self.assertLen(stat_entries, 3)
      self.assertEqual(stat_entries[0].pathspec.path,
                       os.path.join(temp_dirpath, 'dir'))
      self.assertEqual(stat_entries[1].pathspec.path,
                       os.path.join(temp_dirpath, 'dir1'))
      self.assertEqual(stat_entries[2].pathspec.path,
                       os.path.join(temp_dirpath, 'dir2'))

  def testGlob_NoFiles(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=FileSystemTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      fs_obj = fs.FileSystem(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

      stat_entries = fs_obj.glob(os.path.join(temp_dirpath, '*'))
      self.assertEmpty(stat_entries)

  @testing.with_approval_checks
  def testGlob_WithoutApproval(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=FileSystemTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    fs_obj = fs.FileSystem(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

    with self.assertRaises(errors.ApprovalMissingError) as context:
      fs_obj.glob('/foo/bar')

    self.assertEqual(context.exception.client_id, FileSystemTest.FAKE_CLIENT_ID)

  def testGrep_HasMatches(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=FileSystemTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    filename = 'foo'
    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      with io.open(os.path.join(temp_dirpath, filename), 'wb') as filedesc:
        filedesc.write(b'foo bar\nbar Foo\nFoo foo')

      fs_obj = fs.FileSystem(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

      matches = fs_obj.grep(os.path.join(temp_dirpath, filename), b'foo')

      self.assertLen(matches, 4)
      self.assertEqual(matches[0].data, b'foo')
      self.assertEqual(matches[0].offset, 0)
      self.assertEqual(matches[1].data, b'Foo')
      self.assertEqual(matches[1].offset, 12)
      self.assertEqual(matches[2].data, b'Foo')
      self.assertEqual(matches[2].offset, 16)
      self.assertEqual(matches[3].data, b'foo')
      self.assertEqual(matches[3].offset, 20)

  def testGrep_Regex(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=FileSystemTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    filename = 'foo'
    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      with io.open(os.path.join(temp_dirpath, filename), 'wb') as filedesc:
        filedesc.write(b'foo bar\nbar Foo.oo')

      fs_obj = fs.FileSystem(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

      matches = fs_obj.grep(os.path.join(temp_dirpath, filename), b'.oo')

      self.assertLen(matches, 3)
      self.assertEqual(matches[0].data, b'foo')
      self.assertEqual(matches[0].offset, 0)
      self.assertEqual(matches[1].data, b'Foo')
      self.assertEqual(matches[1].offset, 12)
      self.assertEqual(matches[2].data, b'.oo')
      self.assertEqual(matches[2].offset, 15)

  def testGrep_NoMatches(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=FileSystemTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    filename = 'foo'
    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      with io.open(os.path.join(temp_dirpath, filename), 'wb') as filedesc:
        filedesc.write(b'foo bar')

      fs_obj = fs.FileSystem(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

      matches = fs_obj.grep(os.path.join(temp_dirpath, filename), b'foobaar')

      self.assertLen(matches, 0)

  def testGrep_BinaryPattern(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=FileSystemTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    filename = 'foo'
    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      with io.open(os.path.join(temp_dirpath, filename), 'wb') as filedesc:
        filedesc.write(b'foo \xffOO\nFoo \xffoo')

      fs_obj = fs.FileSystem(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

      matches = fs_obj.grep(os.path.join(temp_dirpath, filename), b'\xffoo')

      self.assertLen(matches, 2)
      self.assertEqual(matches[0].data, b'\xffOO')
      self.assertEqual(matches[0].offset, 4)
      self.assertEqual(matches[1].data, b'\xffoo')
      self.assertEqual(matches[1].offset, 12)

  @testing.with_approval_checks
  def testGrep_WithoutApproval(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=FileSystemTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    fs_obj = fs.FileSystem(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

    with self.assertRaises(errors.ApprovalMissingError) as context:
      fs_obj.grep('/foo/bar', b'quux')

    self.assertEqual(context.exception.client_id, FileSystemTest.FAKE_CLIENT_ID)

  def testFgrep_HasMatches(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=FileSystemTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    filename = 'foo'
    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      with io.open(os.path.join(temp_dirpath, filename), 'wb') as filedesc:
        filedesc.write(b'foo bar\nbar Foo\nFoo foo')

      fs_obj = fs.FileSystem(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

      matches = fs_obj.fgrep(os.path.join(temp_dirpath, filename), b'foo')

      self.assertLen(matches, 2)
      self.assertEqual(matches[0].data, b'foo')
      self.assertEqual(matches[0].offset, 0)
      self.assertEqual(matches[1].data, b'foo')
      self.assertEqual(matches[1].offset, 20)

  def testFgrep_Regex(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=FileSystemTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    filename = 'foo'
    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      with io.open(os.path.join(temp_dirpath, filename), 'wb') as filedesc:
        filedesc.write(b'foo bar\nbar Foo.oo')

      fs_obj = fs.FileSystem(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

      matches = fs_obj.fgrep(os.path.join(temp_dirpath, filename), b'.oo')

      self.assertLen(matches, 1)
      self.assertEqual(matches[0].data, b'.oo')
      self.assertEqual(matches[0].offset, 15)

  def testFgrep_NoMatches(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=FileSystemTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    filename = 'foo'
    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      with io.open(os.path.join(temp_dirpath, filename), 'wb') as filedesc:
        filedesc.write(b'foo bar')

      fs_obj = fs.FileSystem(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

      matches = fs_obj.fgrep(os.path.join(temp_dirpath, filename), b'Foo')

      self.assertLen(matches, 0)

  def testFgrep_BinaryPattern(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=FileSystemTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    filename = 'foo'
    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      with io.open(os.path.join(temp_dirpath, filename), 'wb') as filedesc:
        filedesc.write(b'foo \xffOO\nFoo \xffoo')

      fs_obj = fs.FileSystem(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

      matches = fs_obj.fgrep(os.path.join(temp_dirpath, filename), b'\xffoo')

      self.assertLen(matches, 1)
      self.assertEqual(matches[0].data, b'\xffoo')
      self.assertEqual(matches[0].offset, 12)

  @testing.with_approval_checks
  def testFgrep_WithoutApproval(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=FileSystemTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    fs_obj = fs.FileSystem(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

    with self.assertRaises(errors.ApprovalMissingError) as context:
      fs_obj.fgrep('/foo/bar', b'quux')

    self.assertEqual(context.exception.client_id, FileSystemTest.FAKE_CLIENT_ID)

  @testing.with_approval_checks
  def testWget_WithoutApproval(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=FileSystemTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    fs_obj = fs.FileSystem(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

    with flagsaver.flagsaver(grr_admin_ui_url=self.endpoint):
      with self.assertRaises(errors.ApprovalMissingError) as context:
        fs_obj.wget('/foo/bar')

    self.assertEqual(context.exception.client_id, FileSystemTest.FAKE_CLIENT_ID)

  def testWget_NoAdminURLSpecified(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=FileSystemTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)
    fs_obj = fs.FileSystem(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

    with flagsaver.flagsaver(grr_admin_ui_url=''):
      with temp.AutoTempFilePath() as temp_file:

        with self.assertRaises(ValueError):
          fs_obj.wget(temp_file)

  def testWget_FileDoesNotExist(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=FileSystemTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)
    fs_obj = fs.FileSystem(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

    with flagsaver.flagsaver(grr_admin_ui_url=self.endpoint):
      with self.assertRaises(Exception):
        fs_obj.wget('/non/existing/file')

  def testWget_IsDirectory(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=FileSystemTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)
    fs_obj = fs.FileSystem(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

    with flagsaver.flagsaver(grr_admin_ui_url=self.endpoint):
      with temp.AutoTempDirPath() as temp_dir:

        with self.assertRaises(Exception):
          fs_obj.wget(temp_dir)

  def testWget_LinkWorksWithOfflineClient(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=FileSystemTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)
    fs_obj = fs.FileSystem(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

    content = b'foo bar'
    with flagsaver.flagsaver(grr_admin_ui_url=self.endpoint):
      with temp.AutoTempFilePath() as temp_file:
        with io.open(temp_file, 'wb') as filedesc:
          filedesc.write(content)

        link = fs_obj.wget(temp_file)

      self.assertEqual(requests.get(link).content, content)

  def testOpen_ReadAll(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=FileSystemTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    filename = 'foo'
    content = b'foo bar'
    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      with io.open(os.path.join(temp_dirpath, filename), 'wb') as filedesc:
        filedesc.write(content)

      fs_obj = fs.FileSystem(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

      with fs_obj.open(os.path.join(temp_dirpath, filename)) as filedesc:
        self.assertEqual(filedesc.read(), content)

  def testOpen_ReadMore(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=FileSystemTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    filename = 'foo'
    content = b'foo bar'
    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      with io.open(os.path.join(temp_dirpath, filename), 'wb') as filedesc:
        filedesc.write(content)

      fs_obj = fs.FileSystem(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

      with fs_obj.open(os.path.join(temp_dirpath, filename)) as filedesc:
        self.assertEqual(filedesc.read(10), content)

  def testOpen_ReadLess(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=FileSystemTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    filename = 'foo'
    content = b'foo bar'
    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      with io.open(os.path.join(temp_dirpath, filename), 'wb') as filedesc:
        filedesc.write(content)

      fs_obj = fs.FileSystem(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

      with fs_obj.open(os.path.join(temp_dirpath, filename)) as filedesc:
        self.assertEqual(filedesc.read(3), b'foo')

  def testOpen_Buffering(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=FileSystemTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    filename = 'foo'
    size = 1024 * 1024
    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      with io.open(os.path.join(temp_dirpath, filename), 'wb') as filedesc:
        filedesc.write(b'a' * size)

      fs_obj = fs.FileSystem(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

      with fs_obj.open(os.path.join(temp_dirpath, filename)) as filedesc:
        self.assertEqual(filedesc.tell(), 0)
        self.assertLess(len(filedesc.read1()), size)
        self.assertGreater(filedesc.tell(), 0)

  def testOpen_ReadLargeFile(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=FileSystemTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    filename = 'foo'
    size = 1024 * 1024
    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      with io.open(os.path.join(temp_dirpath, filename), 'wb') as filedesc:
        filedesc.write(b'a' * size)

      fs_obj = fs.FileSystem(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

      with fs_obj.open(os.path.join(temp_dirpath, filename)) as filedesc:
        self.assertEqual(len(filedesc.read()), size)

  def testOpen_SeekWithinOneBuffer(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=FileSystemTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    content = b'foo bar'
    with temp.AutoTempFilePath() as temp_filepath:
      with io.open(temp_filepath, 'wb') as filedesc:
        filedesc.write(content)

      fs_obj = fs.FileSystem(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

      with fs_obj.open(temp_filepath) as filedesc:
        filedesc.read(1)
        self.assertEqual(filedesc.seek(4), 4)
        self.assertEqual(filedesc.read(), b'bar')

  def testOpen_SeekOutOfBuffer(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=FileSystemTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    size = 1024 * 512
    with temp.AutoTempFilePath() as temp_filepath:
      with io.open(temp_filepath, 'wb') as filedesc:
        filedesc.write(b'a' * size)
        filedesc.write(b'b' * size)

      fs_obj = fs.FileSystem(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

      with fs_obj.open(temp_filepath) as filedesc:
        self.assertEqual(filedesc.seek(size - 1), size - 1)
        self.assertEqual(filedesc.read(2), b'ab')

  @testing.with_approval_checks
  def testOpen_WithoutApproval(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=FileSystemTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    fs_obj = fs.FileSystem(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

    with self.assertRaises(errors.ApprovalMissingError) as context:
      fs_obj.open('/foo/bar')

    self.assertEqual(context.exception.client_id, FileSystemTest.FAKE_CLIENT_ID)

  @classmethod
  def _get_fake_api_client(cls):
    return _api.get().Client(cls.FAKE_CLIENT_ID).Get()


if __name__ == '__main__':
  absltest.main()
