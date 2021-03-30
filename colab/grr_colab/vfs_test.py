#!/usr/bin/env python
import io
import os

from absl.testing import absltest
from absl.testing import flagsaver
import requests


from grr_api_client import errors as api_errors
import grr_colab
from grr_colab import _api
from grr_colab import errors
from grr_colab import testing
from grr_colab import vfs
from grr_response_core.lib.util import temp
from grr_response_proto import jobs_pb2
from grr_response_server import data_store


class VfsTest(testing.ColabE2ETest):

  FAKE_CLIENT_ID = 'C.0123456789abcdef'

  @testing.with_approval_checks
  def testOpen_WithoutApproval(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=VfsTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    vfs_obj = vfs.VFS(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

    with self.assertRaises(errors.ApprovalMissingError) as context:
      vfs_obj.open('/foo/bar')

    self.assertEqual(context.exception.client_id, VfsTest.FAKE_CLIENT_ID)

  def testOpen_DoesNotExist(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=VfsTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    vfs_obj = vfs.VFS(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

    with self.assertRaises(api_errors.ResourceNotFoundError):
      vfs_obj.open('/foo/bar')

  def testOpen_NotCollected(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=VfsTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    content = b'foo bar'
    api_client = self._get_fake_api_client()
    client = grr_colab.Client(api_client)
    vfs_obj = vfs.VFS(api_client, jobs_pb2.PathSpec.OS)

    with temp.AutoTempFilePath() as temp_filepath:
      with io.open(temp_filepath, 'wb') as filedesc:
        filedesc.write(content)

      client.ls(os.path.dirname(temp_filepath))

    with self.assertRaises(api_errors.ResourceNotFoundError):
      vfs_obj.open(temp_filepath)

  def testOpen_ReadAll(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=VfsTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    content = b'foo bar'
    api_client = self._get_fake_api_client()
    client = grr_colab.Client(api_client)
    vfs_obj = vfs.VFS(api_client, jobs_pb2.PathSpec.OS)

    with temp.AutoTempFilePath() as temp_filepath:
      with io.open(temp_filepath, 'wb') as filedesc:
        filedesc.write(content)

      with client.open(temp_filepath):
        pass

      with vfs_obj.open(temp_filepath) as filedesc:
        self.assertEqual(filedesc.read(), content)

  def testOpen_ReadMore(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=VfsTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    content = b'foo bar'
    api_client = self._get_fake_api_client()
    client = grr_colab.Client(api_client)
    vfs_obj = vfs.VFS(api_client, jobs_pb2.PathSpec.OS)

    with temp.AutoTempFilePath() as temp_filepath:
      with io.open(temp_filepath, 'wb') as filedesc:
        filedesc.write(content)

      with client.open(temp_filepath):
        pass

      with vfs_obj.open(temp_filepath) as filedesc:
        self.assertEqual(filedesc.read(10), content)

  def testOpen_ReadLess(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=VfsTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    content = b'foo bar'
    api_client = self._get_fake_api_client()
    client = grr_colab.Client(api_client)
    vfs_obj = vfs.VFS(api_client, jobs_pb2.PathSpec.OS)

    with temp.AutoTempFilePath() as temp_filepath:
      with io.open(temp_filepath, 'wb') as filedesc:
        filedesc.write(content)

      with client.open(temp_filepath):
        pass

      with vfs_obj.open(temp_filepath) as filedesc:
        self.assertEqual(filedesc.read(3), b'foo')

  def testOpen_Buffering(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=VfsTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    size = 1024 * 1024
    api_client = self._get_fake_api_client()
    client = grr_colab.Client(api_client)
    vfs_obj = vfs.VFS(api_client, jobs_pb2.PathSpec.OS)

    with temp.AutoTempFilePath() as temp_filepath:
      with io.open(temp_filepath, 'wb') as filedesc:
        filedesc.write(b'a' * size)

      with client.open(temp_filepath):
        pass

      with vfs_obj.open(temp_filepath) as filedesc:
        self.assertEqual(filedesc.tell(), 0)
        self.assertLess(len(filedesc.read1()), size)
        self.assertGreater(filedesc.tell(), 0)

  def testOpen_ReadLargeFile(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=VfsTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    size = 1024 * 1024
    api_client = self._get_fake_api_client()
    client = grr_colab.Client(api_client)
    vfs_obj = vfs.VFS(api_client, jobs_pb2.PathSpec.OS)

    with temp.AutoTempFilePath() as temp_filepath:
      with io.open(temp_filepath, 'wb') as filedesc:
        filedesc.write(b'a' * size)

      with client.open(temp_filepath):
        pass

      with vfs_obj.open(temp_filepath) as filedesc:
        self.assertEqual(len(filedesc.read()), size)

  def testOpen_SeekWithinOneBuffer(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=VfsTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    content = b'foo bar'
    api_client = self._get_fake_api_client()
    client = grr_colab.Client(api_client)
    vfs_obj = vfs.VFS(api_client, jobs_pb2.PathSpec.OS)

    with temp.AutoTempFilePath() as temp_filepath:
      with io.open(temp_filepath, 'wb') as filedesc:
        filedesc.write(content)

      with client.open(temp_filepath):
        pass

      with vfs_obj.open(temp_filepath) as filedesc:
        filedesc.read(1)
        self.assertEqual(filedesc.seek(4), 4)
        self.assertEqual(filedesc.read(), b'bar')

  def testOpen_SeekOutOfBuffer(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=VfsTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    size = 1024 * 512
    api_client = self._get_fake_api_client()
    client = grr_colab.Client(api_client)
    vfs_obj = vfs.VFS(api_client, jobs_pb2.PathSpec.OS)

    with temp.AutoTempFilePath() as temp_filepath:
      with io.open(temp_filepath, 'wb') as filedesc:
        filedesc.write(b'a' * size)
        filedesc.write(b'b' * size)

      with client.open(temp_filepath):
        pass

      with vfs_obj.open(temp_filepath) as filedesc:
        self.assertEqual(filedesc.seek(size - 1), size - 1)
        self.assertEqual(filedesc.read(2), b'ab')

  @testing.with_approval_checks
  def testLs_WithoutApproval(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=VfsTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    vfs_obj = vfs.VFS(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)
    with self.assertRaises(errors.ApprovalMissingError) as context:
      vfs_obj.ls('/foo/bar')

    self.assertEqual(context.exception.client_id, VfsTest.FAKE_CLIENT_ID)

  def testLs_DoesNotExist(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=VfsTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    vfs_obj = vfs.VFS(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)
    with self.assertRaises(api_errors.ResourceNotFoundError):
      vfs_obj.ls('/foo/bar')

  def testLs_ContainsFiles(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=VfsTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    dir_nodes = [
        # name, content
        ('file1', b'foo'),
        ('file2', b'foo\nbar'),
    ]

    api_client = self._get_fake_api_client()
    client = grr_colab.Client(api_client)
    vfs_obj = vfs.VFS(api_client, jobs_pb2.PathSpec.OS)

    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      for filename, file_content in dir_nodes:
        filepath = os.path.join(temp_dirpath, filename)
        with io.open(filepath, 'wb') as filedesc:
          filedesc.write(file_content)

      client.ls(temp_dirpath)

      stat_entries = vfs_obj.ls(temp_dirpath)
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
        client_id=VfsTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    api_client = self._get_fake_api_client()
    client = grr_colab.Client(api_client)
    vfs_obj = vfs.VFS(api_client, jobs_pb2.PathSpec.OS)

    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      client.ls(temp_dirpath)

      stat_entries = vfs_obj.ls(temp_dirpath)
      self.assertEmpty(stat_entries)

  def testLs_NotDirectory(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=VfsTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    api_client = self._get_fake_api_client()
    client = grr_colab.Client(api_client)
    vfs_obj = vfs.VFS(api_client, jobs_pb2.PathSpec.OS)

    with temp.AutoTempFilePath() as temp_file:
      client.glob(temp_file)

      with self.assertRaises(errors.NotDirectoryError):
        vfs_obj.ls(temp_file)

  def testLs_Recursive(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=VfsTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    dir_nodes = [
        'file0',
        os.path.join('dir1', 'file1'),
        os.path.join('dir2', 'file2'),
        os.path.join('dir2', 'file3'),
    ]

    api_client = self._get_fake_api_client()
    client = grr_colab.Client(api_client)
    vfs_obj = vfs.VFS(api_client, jobs_pb2.PathSpec.OS)

    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      os.mkdir(os.path.join(temp_dirpath, 'dir1'))
      os.mkdir(os.path.join(temp_dirpath, 'dir2'))
      for path in dir_nodes:
        with io.open(os.path.join(temp_dirpath, path), 'wb') as filedesc:
          filedesc.write(b'foo')

      client.ls(temp_dirpath, max_depth=10)

      stat_entries = vfs_obj.ls(temp_dirpath, max_depth=5)
      paths = sorted(_.pathspec.path for _ in stat_entries)

      self.assertLen(paths, 6)
      self.assertEqual(paths[0], os.path.join(temp_dirpath, 'dir1'))
      self.assertEqual(paths[1], os.path.join(temp_dirpath, 'dir1', 'file1'))
      self.assertEqual(paths[2], os.path.join(temp_dirpath, 'dir2'))
      self.assertEqual(paths[3], os.path.join(temp_dirpath, 'dir2', 'file2'))
      self.assertEqual(paths[4], os.path.join(temp_dirpath, 'dir2', 'file3'))
      self.assertEqual(paths[5], os.path.join(temp_dirpath, 'file0'))

  def testLs_MaxDepth(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=VfsTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    dir_components = ['dir1', 'dir2', 'dir3', 'dir4', 'dir5']

    api_client = self._get_fake_api_client()
    client = grr_colab.Client(api_client)
    vfs_obj = vfs.VFS(api_client, jobs_pb2.PathSpec.OS)

    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      os.makedirs(os.path.join(temp_dirpath, *dir_components))

      client.ls(temp_dirpath, max_depth=10)

      stat_entries = vfs_obj.ls(temp_dirpath, max_depth=3)
      paths = sorted(_.pathspec.path for _ in stat_entries)

      self.assertLen(paths, 3)
      self.assertEqual(paths[0], os.path.join(temp_dirpath, 'dir1'))
      self.assertEqual(paths[1], os.path.join(temp_dirpath, 'dir1', 'dir2'))
      self.assertEqual(paths[2],
                       os.path.join(temp_dirpath, 'dir1', 'dir2', 'dir3'))

  @testing.with_approval_checks
  def testRefresh_WithoutApproval(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=VfsTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    vfs_obj = vfs.VFS(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

    with self.assertRaises(errors.ApprovalMissingError) as context:
      vfs_obj.refresh('/foo/bar')

    self.assertEqual(context.exception.client_id, VfsTest.FAKE_CLIENT_ID)

  def testRefresh_DoesNotExist(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=VfsTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    vfs_obj = vfs.VFS(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)
    with self.assertRaises(api_errors.ResourceNotFoundError):
      vfs_obj.refresh('/foo/bar')

  def testRefresh_Plain(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=VfsTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    api_client = self._get_fake_api_client()
    client = grr_colab.Client(api_client)
    vfs_obj = vfs.VFS(api_client, jobs_pb2.PathSpec.OS)

    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      os.mkdir(os.path.join(temp_dirpath, 'dir1'))

      client.ls(temp_dirpath)

      stat_entries = vfs_obj.ls(temp_dirpath)
      self.assertLen(stat_entries, 1)
      self.assertEqual(stat_entries[0].pathspec.path,
                       os.path.join(temp_dirpath, 'dir1'))

      os.mkdir(os.path.join(temp_dirpath, 'dir2'))

      vfs_obj.refresh(temp_dirpath)
      stat_entries = vfs_obj.ls(temp_dirpath)
      paths = sorted(_.pathspec.path for _ in stat_entries)

      self.assertLen(paths, 2)
      self.assertEqual(paths[0], os.path.join(temp_dirpath, 'dir1'))
      self.assertEqual(paths[1], os.path.join(temp_dirpath, 'dir2'))

  def testRefresh_Recursive(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=VfsTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    dir_components = ['dir1', 'dir2', 'dir3', 'dir4', 'dir5']

    api_client = self._get_fake_api_client()
    client = grr_colab.Client(api_client)
    vfs_obj = vfs.VFS(api_client, jobs_pb2.PathSpec.OS)

    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      os.makedirs(os.path.join(temp_dirpath, dir_components[0]))

      client.ls(temp_dirpath)
      os.makedirs(os.path.join(temp_dirpath, *dir_components))

      vfs_obj.refresh(temp_dirpath, max_depth=3)
      stat_entries = vfs_obj.ls(temp_dirpath, max_depth=10)
      paths = sorted(_.pathspec.path for _ in stat_entries)

      self.assertLen(paths, 3)
      self.assertEqual(paths[0], os.path.join(temp_dirpath, 'dir1'))
      self.assertEqual(paths[1], os.path.join(temp_dirpath, 'dir1', 'dir2'))
      self.assertEqual(paths[2],
                       os.path.join(temp_dirpath, 'dir1', 'dir2', 'dir3'))

  @testing.with_approval_checks
  def testWget_WithoutApproval(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=VfsTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    vfs_obj = vfs.VFS(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

    with flagsaver.flagsaver(grr_admin_ui_url=self.endpoint):
      with self.assertRaises(errors.ApprovalMissingError) as context:
        vfs_obj.wget('/foo/bar')

    self.assertEqual(context.exception.client_id, VfsTest.FAKE_CLIENT_ID)

  def testWget_NoAdminURLSpecified(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=VfsTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    api_client = self._get_fake_api_client()
    client = grr_colab.Client(api_client)
    vfs_obj = vfs.VFS(api_client, jobs_pb2.PathSpec.OS)

    with flagsaver.flagsaver(grr_admin_ui_url=''):
      with temp.AutoTempFilePath() as temp_file:
        with io.open(temp_file, 'wb') as filedesc:
          filedesc.write(b'foo bar')

        with client.open(temp_file):
          pass

        with self.assertRaises(ValueError):
          vfs_obj.wget(temp_file)

  def testWget_FileDoesNotExist(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=VfsTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    vfs_obj = vfs.VFS(self._get_fake_api_client(), jobs_pb2.PathSpec.OS)

    with flagsaver.flagsaver(grr_admin_ui_url=self.endpoint):
      with self.assertRaises(Exception):
        vfs_obj.wget('/non/existing/file')

  def testWget_IsDirectory(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=VfsTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    api_client = self._get_fake_api_client()
    client = grr_colab.Client(api_client)
    vfs_obj = vfs.VFS(api_client, jobs_pb2.PathSpec.OS)

    with flagsaver.flagsaver(grr_admin_ui_url=self.endpoint):
      with temp.AutoTempDirPath() as temp_dir:
        client.ls(temp_dir)

        with self.assertRaises(ValueError):
          vfs_obj.wget(temp_dir)

  def testWget_LinkWorksWithOfflineClient(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=VfsTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    api_client = self._get_fake_api_client()
    client = grr_colab.Client(api_client)
    vfs_obj = vfs.VFS(api_client, jobs_pb2.PathSpec.OS)

    content = b'foo bar'
    with flagsaver.flagsaver(grr_admin_ui_url=self.endpoint):
      with temp.AutoTempFilePath() as temp_file:
        with io.open(temp_file, 'wb') as filedesc:
          filedesc.write(content)

        with client.open(temp_file):
          pass

        link = vfs_obj.wget(temp_file)

      self.assertEqual(requests.get(link).content, content)

  @classmethod
  def _get_fake_api_client(cls):
    return _api.get().Client(cls.FAKE_CLIENT_ID).Get()


class VfsFileTest(absltest.TestCase):

  def testClosed_AfterClose(self):
    f = vfs.VfsFile(lambda _: iter([]))
    self.assertFalse(f.closed)

    f.close()
    self.assertTrue(f.closed)

  def testClose_DoesNotFailOnDoubleClose(self):
    f = vfs.VfsFile(lambda _: iter([]))

    f.close()
    f.close()

  def testFileno_UnsupportedOperation(self):
    f = vfs.VfsFile(lambda _: iter([]))

    with self.assertRaises(io.UnsupportedOperation):
      f.fileno()

  def testFlush_DoesNotFail(self):
    f = vfs.VfsFile(lambda _: iter([]))
    f.flush()

  def testIsatty(self):
    f = vfs.VfsFile(lambda _: iter([]))

    self.assertFalse(f.isatty())

  def testSeekable(self):
    f = vfs.VfsFile(lambda _: iter([]))

    self.assertTrue(f.seekable())

  def testSeek_SetWhence(self):
    f = vfs.VfsFile(lambda _: iter([b'foobar']))

    f.read(5)
    self.assertEqual(f.seek(2), 2)
    self.assertEqual(f.read(), b'obar')

  def testSeek_CurWhence(self):
    f = vfs.VfsFile(lambda _: iter([b'foobar']))

    f.read(5)
    self.assertEqual(f.seek(-2, whence=io.SEEK_CUR), 3)
    self.assertEqual(f.read(), b'bar')

  def testSeek_EndWhenceUnsupportedOperation(self):
    f = vfs.VfsFile(lambda _: iter([]))

    with self.assertRaises(io.UnsupportedOperation):
      f.seek(0, whence=io.SEEK_END)

  def testSeek_ValueErrorOnFileClosed(self):
    f = vfs.VfsFile(lambda _: iter([]))

    f.close()
    with self.assertRaises(ValueError):
      f.seek(0)

  def testSeek_OutOfBuffer(self):
    data = [b'a', b'b', b'c', b'd', b'e']
    f = vfs.VfsFile(lambda offset: iter(data[offset:]))

    f.read(1)
    self.assertEqual(f.seek(2, whence=io.SEEK_CUR), 3)
    self.assertEqual(f.read(), b'de')

  def testTell(self):
    f = vfs.VfsFile(lambda _: iter([b'foo', b'bar']))
    self.assertEqual(f.tell(), 0)

    f.read(4)
    self.assertEqual(f.tell(), 4)

    f.read(1)
    self.assertEqual(f.tell(), 5)

  def testTell_ValueErrorOnFileClosed(self):
    f = vfs.VfsFile(lambda _: iter([]))

    f.close()
    with self.assertRaises(ValueError):
      f.tell()

  def testTruncate_UnsupportedOperation(self):
    f = vfs.VfsFile(lambda _: iter([]))

    with self.assertRaises(io.UnsupportedOperation):
      f.truncate()

  def testWritable(self):
    f = vfs.VfsFile(lambda _: iter([]))

    self.assertFalse(f.writable())

  def testWrite_UnsupportedOperation(self):
    f = vfs.VfsFile(lambda _: iter([]))

    with self.assertRaises(io.UnsupportedOperation):
      f.write(b'foo')

  def testWritelines_UnsupportedOperation(self):
    f = vfs.VfsFile(lambda _: iter([]))

    with self.assertRaises(io.UnsupportedOperation):
      f.writelines([b'foo'])

  def testDetach_UnsupportedOperation(self):
    f = vfs.VfsFile(lambda _: iter([]))

    with self.assertRaises(io.UnsupportedOperation):
      f.detach()

  def testReadable(self):
    f = vfs.VfsFile(lambda _: iter([]))

    self.assertTrue(f.readable())

  def testRead_LessThanBuffer(self):
    f = vfs.VfsFile(lambda _: iter([b'foo']))

    self.assertEqual(f.read(2), b'fo')

  def testRead_MoreThanBuffer(self):
    f = vfs.VfsFile(lambda _: iter([b'foo', b'bar']))

    self.assertEqual(f.read(4), b'foob')

  def testRead_AllWithSingleBuffer(self):
    f = vfs.VfsFile(lambda _: iter([b'foo']))

    self.assertEqual(f.read(), b'foo')

  def testRead_AllWithMultipleBuffers(self):
    f = vfs.VfsFile(lambda _: iter([b'foo', b'bar']))

    self.assertEqual(f.read(), b'foobar')

  def testRead_ValueErrorOnFileClosed(self):
    f = vfs.VfsFile(lambda _: iter([]))

    f.close()
    with self.assertRaises(ValueError):
      f.read()

  def testRead_EmptyOnEof(self):
    f = vfs.VfsFile(lambda _: iter([b'foo']))

    self.assertEqual(f.read(), b'foo')
    self.assertEqual(f.read(), b'')

  def testRead1_LessThanBuffer(self):
    f = vfs.VfsFile(lambda _: iter([b'foo', b'bar', b'quux']))

    self.assertEqual(f.read1(2), b'fo')

  def testRead1_MoreThanBuffer(self):
    f = vfs.VfsFile(lambda _: iter([b'foo', b'bar', b'quux']))

    self.assertEqual(f.read1(5), b'foo')

  def testRead1_ReadCachedAndPartlyNextBuffer(self):
    f = vfs.VfsFile(lambda _: iter([b'foo', b'bar', b'quux']))
    f.read(1)

    self.assertEqual(f.read1(4), b'ooba')

  def testRead1_ReadCachedAndWholeNextBuffer(self):
    f = vfs.VfsFile(lambda _: iter([b'foo', b'bar', b'quux']))
    f.read(1)

    self.assertEqual(f.read1(), b'oobar')

  def testRead1_ValueErrorOnFileClosed(self):
    f = vfs.VfsFile(lambda _: iter([]))

    f.close()
    with self.assertRaises(ValueError):
      f.read1()

  def testRead1_EmptyOnEof(self):
    f = vfs.VfsFile(lambda _: iter([b'foo']))

    self.assertEqual(f.read1(), b'foo')
    self.assertEqual(f.read1(), b'')
    self.assertEqual(f.read1(), b'')

  def testReadinto1_LessThanBuffer(self):
    f = vfs.VfsFile(lambda _: iter([b'foo', b'bar', b'quux']))
    b = bytearray(2)

    self.assertEqual(f.readinto1(b), 2)
    self.assertEqual(b, b'fo')

  def testReadinto1_MoreThanBuffer(self):
    f = vfs.VfsFile(lambda _: iter([b'foo', b'bar', b'quux']))
    b = bytearray(5)

    self.assertEqual(f.readinto1(b), 3)
    self.assertEqual(b[:3], b'foo')

  def testReadinto1_ReadCachedAndPartlyNextBuffer(self):
    f = vfs.VfsFile(lambda _: iter([b'foo', b'bar', b'quux']))
    f.read(1)
    b = bytearray(4)

    self.assertEqual(f.readinto1(b), 4)
    self.assertEqual(b, b'ooba')

  def testReadinto1_ReadCachedAndWholeNextBuffer(self):
    f = vfs.VfsFile(lambda _: iter([b'foo', b'bar', b'quux']))
    f.read(1)
    b = bytearray(10)

    self.assertEqual(f.readinto1(b), 5)
    self.assertEqual(b[:5], b'oobar')

  def testReadinto1_EmptyOnEof(self):
    f = vfs.VfsFile(lambda _: iter([b'foo']))
    b = bytearray(3)

    self.assertEqual(f.readinto1(b), 3)
    self.assertEqual(b, b'foo')
    self.assertEqual(f.readinto1(b), 0)
    self.assertEqual(f.readinto1(b), 0)

  def testReadinto1_ValueErrorOnFileClosed(self):
    f = vfs.VfsFile(lambda _: iter([]))

    f.close()
    with self.assertRaises(ValueError):
      f.readinto1(bytearray())


if __name__ == '__main__':
  absltest.main()
