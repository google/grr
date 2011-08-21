#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2010 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test client vfs."""


import os
import platform
import stat

from grr.client import conf
from grr.client import conf
from grr.client import vfs
from grr.lib import test_lib
from grr.proto import jobs_pb2

FLAGS = conf.PARSER.flags




def setUp():
  # Initialize the VFS system
  vfs.VFSInit()


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

  def testRegularFile(self):
    """Test our ability to read regular files."""
    path = os.path.join(self.base_path, "numbers.txt")

    fd = vfs.VFSHandlerFactory(jobs_pb2.Path(path=path,
                                             pathtype=jobs_pb2.Path.OS))

    self.TestFileHandling(fd)

  def testFileCasing(self):
    """Test our ability to read the correct casing from filesystem."""
    path = os.path.join(self.base_path, "numbers.txt")

    fd = vfs.VFSHandlerFactory(jobs_pb2.Path(path=path,
                                             pathtype=jobs_pb2.Path.OS))
    self.assertEqual(os.path.basename(fd.path), "numbers.txt")

    path = os.path.join(self.base_path, "numbers.TXT")

    fd = vfs.VFSHandlerFactory(jobs_pb2.Path(path=path,
                                             pathtype=jobs_pb2.Path.OS))
    self.assertEqual(os.path.basename(fd.path), "numbers.TXT")

    path = os.path.join(self.base_path, "Numbers.txt")
    fd = vfs.VFSHandlerFactory(jobs_pb2.Path(path=path,
                                             pathtype=jobs_pb2.Path.OS))
    read_path = os.path.basename(fd.path)
    # The exact file now is non deterministic but should be either of the two:
    if read_path != "numbers.txt" and read_path != "numbers.TXT":
      raise RuntimeError("read path is %s" % read_path)

  def testTSKFile(self):
    """Test our ability to read from image files."""
    path = os.path.join(self.base_path, "test_img.dd",
                        "Test Directory", "numbers.txt")

    fd = vfs.VFSHandlerFactory(jobs_pb2.Path(path=path,
                                             pathtype=jobs_pb2.Path.TSK))
    self.TestFileHandling(fd)

  def testTSKFileCasing(self):
    """Test our ability to read the correct casing from image."""
    path = os.path.join(self.base_path, "test_img.dd",
                        "test directory", "NuMbErS.TxT")

    fd = vfs.VFSHandlerFactory(jobs_pb2.Path(path=path,
                                             pathtype=jobs_pb2.Path.TSK))
    self.assertEqual(fd.path, u"/Test Directory/numbers.txt")

  def testUnicodeFile(self):
    """Test ability to read unicode files from images."""
    path = os.path.join(self.base_path, "test_img.dd",
                        u"איןד ןד ש אקדא", u"איןד.txt")

    fd = vfs.VFSHandlerFactory(jobs_pb2.Path(path=path,
                                             pathtype=jobs_pb2.Path.TSK))
    self.TestFileHandling(fd)

  def testListDirectory(self):
    """Test our ability to list a directory."""
    directory = vfs.VFSHandlerFactory(jobs_pb2.Path(path=self.base_path,
                                                    pathtype=jobs_pb2.Path.OS))

    self.CheckDirectoryListing(directory, "numbers.txt")

  def testTSKListDirectory(self):
    """Test directory listing in sleuthkit."""
    path = os.path.join(self.base_path, "test_img.dd",
                        u"入乡随俗 海外春节别样过法")

    directory = vfs.VFSHandlerFactory(jobs_pb2.Path(path=path,
                                                    pathtype=jobs_pb2.Path.TSK))

    self.CheckDirectoryListing(directory, u"入乡随俗.txt")

  def testRegistryListing(self):
    """Test our ability to list registry keys."""
    if platform.system() != "Windows":
      return

    # Make a value we can test for
    from winsys import registry

    registry.create("HKCU\\Software\\GRR_Test").set_value("foo", "bar")

    vfs_path = "HKEY_CURRENT_USER/Software/GRR_Test"

    pathspec = jobs_pb2.Path(path=vfs_path,
                             pathtype=jobs_pb2.Path.REGISTRY)
    for f in vfs.VFSHandlerFactory(pathspec).ListFiles():
      self.assertEqual(f.path, "foo")
      self.assertEqual(f.resident, "bar")

  def CheckDirectoryListing(self, directory, test_file):
    """Check that the directory listing is sensible."""
    found = False
    for f in directory.ListFiles():
      # TSK makes virtual files with $ if front of them
      path = os.path.basename(f.pathspec.path)
      if path.startswith("$"): continue

      # Check the time is reasonable
      self.assert_(f.st_mtime > 10000000)
      self.assert_(f.st_atime > 10000000)
      self.assert_(f.st_ctime > 10000000)

      if path == test_file:
        found = True
        # Make sure its a regular file with the right size
        self.assert_(stat.S_ISREG(f.st_mode))
        self.assertEqual(f.st_size, 3893)

    self.assertEqual(found, True)


def main(argv):
  vfs.VFSInit()
  test_lib.main(argv)

if __name__ == "__main__":
  conf.StartMain(main)
