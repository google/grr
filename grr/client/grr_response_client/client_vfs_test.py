#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test client vfs."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io
import logging
import os
import shutil
import stat


from absl.testing import absltest
from builtins import range  # pylint: disable=redefined-builtin
import mock
import psutil

# pylint: disable=unused-import,g-bad-import-order
from grr_response_client import client_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr_response_client import vfs
from grr_response_client.vfs_handlers import files
from grr_response_core.lib import flags
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr.test_lib import temp
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib

# pylint: mode=test


class VFSTest(test_lib.GRRBaseTest):
  """Test the client VFS switch."""

  def GetNumbers(self):
    """Generate a test string."""
    result = ""
    for i in range(1, 1001):
      result += "%s\n" % i

    return result

  def TestFileHandling(self, fd):
    """Test the file like object behaviour."""
    original_string = self.GetNumbers()

    self.assertEqual(fd.size, len(original_string))

    fd.Seek(0)
    self.assertEqual(fd.Read(100), original_string[0:100])
    self.assertEqual(fd.Tell(), 100)

    fd.Seek(-10, 1)
    self.assertEqual(fd.Tell(), 90)
    self.assertEqual(fd.Read(10), original_string[90:100])

    fd.Seek(0, 2)
    self.assertEqual(fd.Tell(), len(original_string))
    self.assertEqual(fd.Read(10), "")
    self.assertEqual(fd.Tell(), len(original_string))

    # Raise if we try to list the contents of a file object.
    self.assertRaises(IOError, lambda: list(fd.ListFiles()))

  def testRegularFile(self):
    """Test our ability to read regular files."""
    path = os.path.join(self.base_path, "morenumbers.txt")
    pathspec = rdf_paths.PathSpec(
        path=path, pathtype=rdf_paths.PathSpec.PathType.OS)
    fd = vfs.VFSOpen(pathspec)

    self.TestFileHandling(fd)

  def testOpenFilehandles(self):
    """Test that file handles are cached."""
    current_process = psutil.Process(os.getpid())
    num_open_files = len(current_process.open_files())

    path = os.path.join(self.base_path, "morenumbers.txt")

    fds = []
    for _ in range(100):
      fd = vfs.VFSOpen(
          rdf_paths.PathSpec(
              path=path, pathtype=rdf_paths.PathSpec.PathType.OS))
      self.assertEqual(fd.read(20), "1\n2\n3\n4\n5\n6\n7\n8\n9\n10")
      fds.append(fd)

    # This should not create any new file handles.
    self.assertLess(len(current_process.open_files()) - num_open_files, 5)

  def testOpenFilehandlesExpire(self):
    """Test that file handles expire from cache."""
    files.FILE_HANDLE_CACHE = utils.FastStore(max_size=10)

    current_process = psutil.Process(os.getpid())
    num_open_files = len(current_process.open_files())

    path = os.path.join(self.base_path, "morenumbers.txt")
    fd = vfs.VFSOpen(
        rdf_paths.PathSpec(path=path, pathtype=rdf_paths.PathSpec.PathType.OS))

    fds = []
    for filename in fd.ListNames():
      child_fd = vfs.VFSOpen(
          rdf_paths.PathSpec(
              path=os.path.join(path, filename),
              pathtype=rdf_paths.PathSpec.PathType.OS))
      fd.read(20)
      fds.append(child_fd)

    # This should not create any new file handles.
    self.assertLess(len(current_process.open_files()) - num_open_files, 5)

    # Make sure we exceeded the size of the cache.
    self.assertGreater(fds, 20)

  def testFileCasing(self):
    """Test our ability to read the correct casing from filesystem."""
    try:
      os.lstat(os.path.join(self.base_path, "nUmBeRs.txt"))
      os.lstat(os.path.join(self.base_path, "nuMbErs.txt"))
      # If we reached this point we are on a case insensitive file system
      # and the tests below do not make any sense.
      logging.warning("Case insensitive file system detected. Skipping test.")
      return
    except (IOError, OSError):
      pass

    # Create 2 files with names that differ only in casing.
    with utils.TempDirectory() as temp_dir:
      path1 = os.path.join(temp_dir, "numbers.txt")
      shutil.copy(os.path.join(self.base_path, "numbers.txt"), path1)

      path2 = os.path.join(temp_dir, "numbers.TXT")
      shutil.copy(os.path.join(self.base_path, "numbers.txt.ver2"), path2)

      fd = vfs.VFSOpen(
          rdf_paths.PathSpec(
              path=path1, pathtype=rdf_paths.PathSpec.PathType.OS))
      self.assertEqual(fd.pathspec.Basename(), "numbers.txt")

      fd = vfs.VFSOpen(
          rdf_paths.PathSpec(
              path=path2, pathtype=rdf_paths.PathSpec.PathType.OS))
      self.assertEqual(fd.pathspec.Basename(), "numbers.TXT")

      path = os.path.join(self.base_path, "Numbers.txt")
      fd = vfs.VFSOpen(
          rdf_paths.PathSpec(
              path=path, pathtype=rdf_paths.PathSpec.PathType.OS))
      read_path = fd.pathspec.Basename()

      # The exact file now is non deterministic but should be either of the two:
      if read_path != "numbers.txt" and read_path != "numbers.TXT":
        raise RuntimeError("read path is %s" % read_path)

      # Ensure that the produced pathspec specified no case folding:
      s = fd.Stat()
      self.assertEqual(s.pathspec.path_options,
                       rdf_paths.PathSpec.Options.CASE_LITERAL)

      # Case folding will only occur when requested - this should raise because
      # we have the CASE_LITERAL option:
      pathspec = rdf_paths.PathSpec(
          path=path,
          pathtype=rdf_paths.PathSpec.PathType.OS,
          path_options=rdf_paths.PathSpec.Options.CASE_LITERAL)
      self.assertRaises(IOError, vfs.VFSOpen, pathspec)

  def testTSKFile(self):
    """Test our ability to read from image files."""
    path = os.path.join(self.base_path, "test_img.dd")
    path2 = "Test Directory/numbers.txt"

    p2 = rdf_paths.PathSpec(
        path=path2, pathtype=rdf_paths.PathSpec.PathType.TSK)
    p1 = rdf_paths.PathSpec(path=path, pathtype=rdf_paths.PathSpec.PathType.OS)
    p1.Append(p2)
    fd = vfs.VFSOpen(p1)
    self.TestFileHandling(fd)

  def testTSKFileInode(self):
    """Test opening a file through an indirect pathspec."""
    pathspec = rdf_paths.PathSpec(
        path=os.path.join(self.base_path, "test_img.dd"),
        pathtype=rdf_paths.PathSpec.PathType.OS)
    pathspec.Append(
        pathtype=rdf_paths.PathSpec.PathType.TSK,
        inode=12,
        path="/Test Directory")
    pathspec.Append(
        pathtype=rdf_paths.PathSpec.PathType.TSK, path="numbers.txt")

    fd = vfs.VFSOpen(pathspec)

    # Check that the new pathspec is correctly reduced to two components.
    self.assertEqual(
        fd.pathspec.first.path,
        utils.NormalizePath(os.path.join(self.base_path, "test_img.dd")))
    self.assertEqual(fd.pathspec[1].path, "/Test Directory/numbers.txt")

    # And the correct inode is placed in the final branch.
    self.assertEqual(fd.Stat().pathspec.nested_path.inode, 15)
    self.TestFileHandling(fd)

  def testTSKFileCasing(self):
    """Test our ability to read the correct casing from image."""
    path = os.path.join(self.base_path, "test_img.dd")
    path2 = os.path.join("test directory", "NuMbErS.TxT")

    ps2 = rdf_paths.PathSpec(
        path=path2, pathtype=rdf_paths.PathSpec.PathType.TSK)

    ps = rdf_paths.PathSpec(path=path, pathtype=rdf_paths.PathSpec.PathType.OS)
    ps.Append(ps2)
    fd = vfs.VFSOpen(ps)

    # This fixes Windows paths.
    path = path.replace("\\", "/")
    # The pathspec should have 2 components.

    self.assertEqual(fd.pathspec.first.path, utils.NormalizePath(path))
    self.assertEqual(fd.pathspec.first.pathtype, rdf_paths.PathSpec.PathType.OS)

    nested = fd.pathspec.last
    self.assertEqual(nested.path, u"/Test Directory/numbers.txt")
    self.assertEqual(nested.pathtype, rdf_paths.PathSpec.PathType.TSK)

  def testTSKInodeHandling(self):
    """Test that we can open files by inode."""
    path = os.path.join(self.base_path, "ntfs_img.dd")
    ps2 = rdf_paths.PathSpec(
        inode=65,
        ntfs_type=128,
        ntfs_id=0,
        path="/this/will/be/ignored",
        pathtype=rdf_paths.PathSpec.PathType.TSK)

    ps = rdf_paths.PathSpec(
        path=path, pathtype=rdf_paths.PathSpec.PathType.OS, offset=63 * 512)
    ps.Append(ps2)
    fd = vfs.VFSOpen(ps)

    self.assertEqual(fd.Read(100), "Hello world\n")

    ps2 = rdf_paths.PathSpec(
        inode=65,
        ntfs_type=128,
        ntfs_id=4,
        pathtype=rdf_paths.PathSpec.PathType.TSK)
    ps = rdf_paths.PathSpec(
        path=path, pathtype=rdf_paths.PathSpec.PathType.OS, offset=63 * 512)
    ps.Append(ps2)
    fd = vfs.VFSOpen(ps)

    self.assertEqual(fd.read(100), "I am a real ADS\n")

    # Make sure the size is correct:
    self.assertEqual(fd.Stat().st_size, len("I am a real ADS\n"))

  def testTSKNTFSHandling(self):
    """Test that TSK can correctly encode NTFS features."""
    path = os.path.join(self.base_path, "ntfs_img.dd")
    path2 = "test directory"

    ps2 = rdf_paths.PathSpec(
        path=path2, pathtype=rdf_paths.PathSpec.PathType.TSK)

    ps = rdf_paths.PathSpec(
        path=path, pathtype=rdf_paths.PathSpec.PathType.OS, offset=63 * 512)
    ps.Append(ps2)
    fd = vfs.VFSOpen(ps)

    # This fixes Windows paths.
    path = path.replace("\\", "/")
    listing = []
    pathspecs = []

    for f in fd.ListFiles():
      # Make sure the CASE_LITERAL option is set for all drivers so we can just
      # resend this proto back.
      self.assertEqual(f.pathspec.path_options,
                       rdf_paths.PathSpec.Options.CASE_LITERAL)
      pathspec = f.pathspec.nested_path
      self.assertEqual(pathspec.path_options,
                       rdf_paths.PathSpec.Options.CASE_LITERAL)
      pathspecs.append(f.pathspec)
      listing.append((pathspec.inode, pathspec.ntfs_type, pathspec.ntfs_id))

    # The tsk_fs_attr_type enum:
    tsk_fs_attr_type = rdf_paths.PathSpec.tsk_fs_attr_type

    ref = [(65, tsk_fs_attr_type.TSK_FS_ATTR_TYPE_DEFAULT, 0),
           (65, tsk_fs_attr_type.TSK_FS_ATTR_TYPE_NTFS_DATA, 4),
           (66, tsk_fs_attr_type.TSK_FS_ATTR_TYPE_DEFAULT, 0),
           (67, tsk_fs_attr_type.TSK_FS_ATTR_TYPE_DEFAULT, 0)]

    # Make sure that the ADS is recovered.
    self.assertEqual(listing, ref)

    # Try to read the main file
    self.assertEqual(pathspecs[0].nested_path.path, "/Test Directory/notes.txt")
    fd = vfs.VFSOpen(pathspecs[0])
    self.assertEqual(fd.read(1000), "Hello world\n")

    s = fd.Stat()
    self.assertEqual(s.pathspec.nested_path.inode, 65)
    self.assertEqual(s.pathspec.nested_path.ntfs_type, 1)
    self.assertEqual(s.pathspec.nested_path.ntfs_id, 0)

    # Check that the name of the ads is consistent.
    self.assertEqual(pathspecs[1].nested_path.path, "/Test Directory/notes.txt")
    self.assertEqual(pathspecs[1].nested_path.stream_name, "ads")

    # Check that the ADS name is encoded correctly in the AFF4 URN for this
    # file.
    aff4_urn = pathspecs[1].AFF4Path(rdf_client.ClientURN("C.1234567812345678"))
    self.assertEqual(aff4_urn.Basename(), "notes.txt:ads")

    fd = vfs.VFSOpen(pathspecs[1])
    self.assertEqual(fd.read(1000), "I am a real ADS\n")

    # Test that the stat contains the inode:
    s = fd.Stat()
    self.assertEqual(s.pathspec.nested_path.inode, 65)
    self.assertEqual(s.pathspec.nested_path.ntfs_type, 128)
    self.assertEqual(s.pathspec.nested_path.ntfs_id, 4)

  def testNTFSProgressCallback(self):

    self.progress_counter = 0

    def Progress():
      self.progress_counter += 1

    path = os.path.join(self.base_path, "ntfs_img.dd")
    path2 = "test directory"

    ps2 = rdf_paths.PathSpec(
        path=path2, pathtype=rdf_paths.PathSpec.PathType.TSK)

    ps = rdf_paths.PathSpec(
        path=path, pathtype=rdf_paths.PathSpec.PathType.OS, offset=63 * 512)
    ps.Append(ps2)

    vfs.VFSOpen(ps, progress_callback=Progress)

    self.assertGreater(self.progress_counter, 0)

  def testUnicodeFile(self):
    """Test ability to read unicode files from images."""
    path = os.path.join(self.base_path, "test_img.dd")
    path2 = os.path.join(u"איןד ןד ש אקדא", u"איןד.txt")

    ps2 = rdf_paths.PathSpec(
        path=path2, pathtype=rdf_paths.PathSpec.PathType.TSK)

    ps = rdf_paths.PathSpec(path=path, pathtype=rdf_paths.PathSpec.PathType.OS)
    ps.Append(ps2)
    fd = vfs.VFSOpen(ps)
    self.TestFileHandling(fd)

  def testListDirectory(self):
    """Test our ability to list a directory."""
    directory = vfs.VFSOpen(
        rdf_paths.PathSpec(
            path=self.base_path, pathtype=rdf_paths.PathSpec.PathType.OS))

    self.CheckDirectoryListing(directory, "morenumbers.txt")

  def testTSKListDirectory(self):
    """Test directory listing in sleuthkit."""
    path = os.path.join(self.base_path, u"test_img.dd")
    ps2 = rdf_paths.PathSpec(
        path=u"入乡随俗 海外春节别样过法", pathtype=rdf_paths.PathSpec.PathType.TSK)
    ps = rdf_paths.PathSpec(path=path, pathtype=rdf_paths.PathSpec.PathType.OS)
    ps.Append(ps2)
    directory = vfs.VFSOpen(ps)
    self.CheckDirectoryListing(directory, u"入乡随俗.txt")

  def testRecursiveImages(self):
    """Test directory listing in sleuthkit."""
    p3 = rdf_paths.PathSpec(
        path="/home/a.txt", pathtype=rdf_paths.PathSpec.PathType.TSK)
    p2 = rdf_paths.PathSpec(
        path="/home/image2.img", pathtype=rdf_paths.PathSpec.PathType.TSK)
    p1 = rdf_paths.PathSpec(
        path=os.path.join(self.base_path, "test_img.dd"),
        pathtype=rdf_paths.PathSpec.PathType.OS)
    p2.Append(p3)
    p1.Append(p2)
    f = vfs.VFSOpen(p1)

    self.assertEqual(f.read(3), "yay")

  def testGuessPathSpec(self):
    """Test that we can guess a pathspec from a path."""
    path = os.path.join(self.base_path, "test_img.dd", "home/image2.img",
                        "home/a.txt")

    pathspec = rdf_paths.PathSpec(
        path=path, pathtype=rdf_paths.PathSpec.PathType.OS)

    fd = vfs.VFSOpen(pathspec)
    self.assertEqual(fd.read(3), "yay")

  def testFileNotFound(self):
    """Test that we raise an IOError for file not found."""
    path = os.path.join(self.base_path, "test_img.dd", "home/image2.img",
                        "home/nosuchfile.txt")

    pathspec = rdf_paths.PathSpec(
        path=path, pathtype=rdf_paths.PathSpec.PathType.OS)
    self.assertRaises(IOError, vfs.VFSOpen, pathspec)

  def testGuessPathSpecPartial(self):
    """Test that we can guess a pathspec from a partial pathspec."""
    path = os.path.join(self.base_path, "test_img.dd")
    pathspec = rdf_paths.PathSpec(
        path=path, pathtype=rdf_paths.PathSpec.PathType.OS)
    pathspec.nested_path.path = "/home/image2.img/home/a.txt"
    pathspec.nested_path.pathtype = rdf_paths.PathSpec.PathType.TSK

    fd = vfs.VFSOpen(pathspec)
    self.assertEqual(fd.read(3), "yay")

    # Open as a directory
    pathspec.nested_path.path = "/home/image2.img/home/"

    fd = vfs.VFSOpen(pathspec)

    names = []
    for s in fd.ListFiles():
      # Make sure that the stat pathspec is correct - it should be 3 levels
      # deep.
      self.assertEqual(s.pathspec.nested_path.path, "/home/image2.img")
      names.append(s.pathspec.nested_path.nested_path.path)

    self.assertIn("home/a.txt", names)

  def testRegistryListing(self):
    """Test our ability to list registry keys."""
    reg = rdf_paths.PathSpec.PathType.REGISTRY
    with vfs_test_lib.VFSOverrider(reg, vfs_test_lib.FakeRegistryVFSHandler):
      pathspec = rdf_paths.PathSpec(
          pathtype=rdf_paths.PathSpec.PathType.REGISTRY,
          path=("/HKEY_USERS/S-1-5-20/Software/Microsoft"
                "/Windows/CurrentVersion/Run"))

      expected_names = {"MctAdmin": stat.S_IFDIR, "Sidebar": stat.S_IFDIR}
      expected_data = [
          u"%ProgramFiles%\\Windows Sidebar\\Sidebar.exe /autoRun",
          u"%TEMP%\\Sidebar.exe"
      ]

      for f in vfs.VFSOpen(pathspec).ListFiles():
        base, name = os.path.split(f.pathspec.CollapsePath())
        self.assertEqual(base, pathspec.CollapsePath())
        self.assertIn(name, expected_names)
        self.assertIn(f.registry_data.GetValue(), expected_data)

  def CheckDirectoryListing(self, directory, test_file):
    """Check that the directory listing is sensible."""

    found = False
    for f in directory.ListFiles():
      # TSK makes virtual files with $ if front of them
      path = f.pathspec.Basename()
      if path.startswith("$"):
        continue

      # Check the time is reasonable
      self.assertGreater(f.st_mtime, 10000000)
      self.assertGreater(f.st_atime, 10000000)
      self.assertGreater(f.st_ctime, 10000000)

      if path == test_file:
        found = True
        # Make sure its a regular file with the right size
        self.assertTrue(stat.S_ISREG(f.st_mode))
        self.assertEqual(f.st_size, 3893)

    self.assertEqual(found, True)

    # Raise if we try to read the contents of a directory object.
    self.assertRaises(IOError, directory.Read, 5)

  def testVFSVirtualRoot(self):

    # Let's open a file in the virtual root.
    os_root = "os:%s" % self.base_path
    with test_lib.ConfigOverrider({"Client.vfs_virtualroots": [os_root]}):
      # We need to reset the vfs.VFS_VIRTUALROOTS too.
      vfs.VFSInit().Run()

      fd = vfs.VFSOpen(
          rdf_paths.PathSpec(
              path="/morenumbers.txt", pathtype=rdf_paths.PathSpec.PathType.OS))
      data = fd.read(10)
      self.assertEqual(data, "1\n2\n3\n4\n5\n")

    # This should also work with TSK.
    tsk_root = "tsk:%s" % os.path.join(self.base_path, "test_img.dd")
    with test_lib.ConfigOverrider({"Client.vfs_virtualroots": [tsk_root]}):
      vfs.VFSInit().Run()

      image_file_ps = rdf_paths.PathSpec(
          path=u"איןד ןד ש אקדא/איןד.txt",
          pathtype=rdf_paths.PathSpec.PathType.TSK)

      fd = vfs.VFSOpen(image_file_ps)

      data = fd.read(10)
      self.assertEqual(data, "1\n2\n3\n4\n5\n")

      # This should not influence vfs handlers other than OS and TSK.
      reg_type = rdf_paths.PathSpec.PathType.REGISTRY
      os_handler = vfs.VFS_HANDLERS[rdf_paths.PathSpec.PathType.OS]
      with vfs_test_lib.VFSOverrider(reg_type, os_handler):
        with self.assertRaises(IOError):
          image_file_ps.pathtype = reg_type
          vfs.VFSOpen(image_file_ps)

  def testFileSizeOverride(self):

    # We assume /dev/null exists and has a 0 size.
    fname = "/dev/null"
    try:
      st = os.stat(fname)
    except OSError:
      self.skipTest("%s not accessible." % fname)
    if st.st_size != 0:
      self.skipTest("%s doesn't have 0 size." % fname)

    pathspec = rdf_paths.PathSpec(
        path=fname, pathtype="OS", file_size_override=100000000)
    fd = vfs.VFSOpen(pathspec)
    self.assertEqual(fd.size, 100000000)


class VFSMultiOpenTest(absltest.TestCase):

  _VFS_OVERRIDER = vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                             files.File)

  def setUp(self):
    self._VFS_OVERRIDER.Start()

  def tearDown(self):
    self._VFS_OVERRIDER.Stop()

  def testMultipleFiles(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as tempdir:
      foo_path = os.path.join(tempdir, "foo")
      bar_path = os.path.join(tempdir, "bar")
      baz_path = os.path.join(tempdir, "baz")

      self._Touch(foo_path, b"FOO")
      self._Touch(bar_path, b"BAR")
      self._Touch(baz_path, b"BAZ")

      foo_pathspec = rdf_paths.PathSpec(
          pathtype=rdf_paths.PathSpec.PathType.OS, path=foo_path)
      bar_pathspec = rdf_paths.PathSpec(
          pathtype=rdf_paths.PathSpec.PathType.OS, path=bar_path)
      baz_pathspec = rdf_paths.PathSpec(
          pathtype=rdf_paths.PathSpec.PathType.OS, path=baz_path)

      pathspecs = [foo_pathspec, bar_pathspec, baz_pathspec]
      with vfs.VFSMultiOpen(pathspecs) as filedescs:
        self.assertLen(filedescs, 3)
        self.assertEqual(filedescs[0].Read(), b"FOO")
        self.assertEqual(filedescs[1].Read(), b"BAR")
        self.assertEqual(filedescs[2].Read(), b"BAZ")

  def testProgressCallback(self):
    with temp.AutoTempFilePath() as temppath:
      self._Touch(temppath, b"QUUX")

      pathspec = rdf_paths.PathSpec(
          pathtype=rdf_paths.PathSpec.PathType.OS, path=temppath)

      func = mock.MagicMock()

      with vfs.VFSMultiOpen([pathspec], progress_callback=func) as filedescs:
        self.assertLen(filedescs, 1)
        self.assertEqual(filedescs[0].Read(), b"QUUX")

      self.assertTrue(func.called)

  def _Touch(self, filepath, content=b""):
    with io.open(filepath, mode="wb") as filedesc:
      filedesc.write(content)


def main(argv):
  vfs.VFSInit()
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
