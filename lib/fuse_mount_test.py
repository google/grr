#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests for grr.tools.fuse_mount.py."""

import os


# pylint: disable=unused-import, g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import, g-bad-import-order

from grr.lib import rdfvalue
from grr.lib import test_lib

from grr.tools import fuse_mount


class MockFuseOSError(OSError):
  """A class to mock the fuse module's special OSError."""
  pass


class MockFuse(object):
  """A class to mock the entire fuse module, if it is not present."""

  # We rely on fuse.FuseOSError, so we add a mock of
  # it to this mock module.
  class FuseOSError(MockFuseOSError):
    pass

# pylint: disable=invalid-name

# If fuse is not installed, replace the None returned by utils.ConditionalImport
# with our MockFuse object.
if fuse_mount.fuse is None:
  fuse = MockFuse()
  fuse_mount.fuse = fuse
else:
  # If fuse IS installed, we refer to MockFuseOSError in our tests, so let's
  # make that point to the real FuseOSError class.

  MockFuseOSError = fuse_mount.fuse.FuseOSError

# pylint: enable=invalid-name


class FuseMountTest(test_lib.GRRBaseTest):

  def setUp(self):

    super(FuseMountTest, self).setUp()

    self.client_name = "C." + "1" * 16
    test_lib.ClientFixture(self.client_name, token=self.token)
    self.root = "/"

    self.passthrough = fuse_mount.GRRFuseDatastoreOnly(
        self.root,
        token=self.token)

  def testInvalidAFF4Root(self):
    with self.assertRaises(IOError):
      fuse_mount.GRRFuseDatastoreOnly("not_a_valid_path",
                                      token=self.token)

  def _TestReadDir(self, directory):
    contents = list(self.passthrough.readdir(directory))

    for item in contents:
      # All the filenames should be unicode strings.
      self.assertTrue(isinstance(item, unicode))
    self.assertTrue("." in contents and ".." in contents)
    contents.remove(".")
    contents.remove("..")
    for child in contents:
      child = os.path.join(directory, child)

      # While checking if each child is a directory, we perform a stat on it in
      # the _IsDir method. So this test ensures we can stat every valid path
      # in the filesystem.
      if self.passthrough._IsDir(child):
        self._TestReadDir(child)

  def testReadDir(self):
    """Recursively reads directories, making sure they exist."""
    # Read everything the filesystem says is under the root.
    self._TestReadDir(self.root)

  def testReadExistingDir(self):
    # In case the files reported were wrong, try and find this particular
    # directory, which should exist.
    existing_dir = self.root + self.client_name + "/fs/os/c/bin/"
    self._TestReadDir(existing_dir)

  def testReadDirFile(self):
    # We can't ls a file.
    with self.assertRaises(MockFuseOSError):
      filename = self.root + self.client_name + "/fs/os/c/bin/bash"
      # We iterate through the generator so the error actually gets thrown.
      list(self.passthrough.readdir(filename))

  def testAccessingDirThatDoesNotExist(self):
    with self.assertRaises(MockFuseOSError):
      list(self.passthrough.getattr("aff4:/This string is so silly",
                                    "that it probably is not a directory"))

  def testAccessingBlankDir(self):
    with self.assertRaises(MockFuseOSError):
      list(self.passthrough.getattr(""))

  def testAccessingUnicodeDir(self):
    with self.assertRaises(MockFuseOSError):
      list(self.passthrough.getattr("ಠ_ಠ"))

  def testGetAttrDir(self):
    self.assertEqual(self.passthrough.getattr("/"),
                     self.passthrough._GetDefaultStat(True, "/"))

  def testGetAttrFile(self):
    self.assertEqual(self.passthrough.getattr("/foreman"),
                     self.passthrough._GetDefaultStat(False, "/foreman"))

  def testExistingFileStat(self):
    bash_stat = {
        "st_ctime": rdfvalue.RDFDatetimeSeconds(1299502221),
        "st_rdev": 0,
        "st_mtime": rdfvalue.RDFDatetimeSeconds(1284154642),
        "st_blocks": 16,
        "st_nlink": 1,
        "st_gid": 0,
        "st_blksize": 4096,
        "pathspec": rdfvalue.PathSpec(
            path="/bin/bash",
            pathtype="OS",
            path_options="CASE_LITERAL"),
        "st_dev": 51713,
        "st_size": 4874,
        "st_ino": 1026148,
        "st_uid": 0,
        "st_mode": rdfvalue.StatMode(33261),
        "st_atime": rdfvalue.RDFDatetimeSeconds(1299502220)
        }

    bash_path = os.path.join("/", self.client_name, "fs/os/c/bin/bash")
    self.assertItemsEqual(self.passthrough.getattr(bash_path), bash_stat)
