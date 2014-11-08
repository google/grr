#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests for grr.tools.fuse_mount.py."""

import datetime
import os


# pylint: disable=unused-import, g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import, g-bad-import-order

from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import flags
from grr.lib import flow_utils
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils

from grr.lib.aff4_objects import standard

from grr.tools import fuse_mount

# pylint: mode=test


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

# If fuse is not installed, replace it with our MockFuse object.
if fuse_mount.fuse is None:
  fuse = MockFuse()
  fuse_mount.fuse = fuse
else:
  # If fuse IS installed, we refer to MockFuseOSError in our tests, so let's
  # make that point to the real FuseOSError class.

  MockFuseOSError = fuse_mount.fuse.FuseOSError

# pylint: enable=invalid-name


class GRRFuseTestBase(test_lib.GRRBaseTest):
  pass


class GRRFuseDatastoreOnlyTest(GRRFuseTestBase):

  def setUp(self):

    super(GRRFuseDatastoreOnlyTest, self).setUp()

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
    existing_dir = os.path.join(self.root, self.client_name, "fs/os/c/bin/")
    self._TestReadDir(existing_dir)

  def testReadDirFile(self):
    # We can't ls a file.
    with self.assertRaises(MockFuseOSError):
      file_path = os.path.join(self.root, self.client_name, "fs/os/c/bin/bash")
      # We iterate through the generator so the error actually gets thrown.
      list(self.passthrough.readdir(file_path))

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
    path = "/"

    fd = aff4.FACTORY.Open(path, token=self.token)

    self.assertEqual(self.passthrough.getattr("/"),
                     self.passthrough.MakePartialStat(fd))

  def testGetAttrFile(self):
    path = "/foreman"

    fd = aff4.FACTORY.Open(path, token=self.token)

    self.assertEqual(self.passthrough.getattr("/foreman"),
                     self.passthrough.MakePartialStat(fd))

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

  def testReadNotFile(self):
    with self.assertRaises(MockFuseOSError):
      existing_dir = os.path.join(self.root, self.client_name, "/fs/os/c/bin")
      self.passthrough.Read(existing_dir)


class GRRFuseTest(GRRFuseTestBase):

  # Whether the tests are done and the fake server can stop running.
  done = False

  def setUp(self):
    super(GRRFuseTest, self).setUp()

    self.client_id = self.SetupClients(1)[0]

    self.client_name = str(self.client_id)[len("aff4:/"):]

    with aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw") as fd:
      fd.Set(fd.Schema.SYSTEM("Linux"))
      kb = fd.Schema.KNOWLEDGE_BASE()
      fd.Set(kb)

    with aff4.FACTORY.Create(self.client_id.Add("fs/os"), "VFSDirectory",
                             mode="rw", token=self.token) as fd:
      fd.Set(fd.Schema.PATHSPEC(path="/", pathtype="OS"))

    # Ignore cache so our tests always get client side updates.
    self.grr_fuse = fuse_mount.GRRFuse(root="/", token=self.token,
                                       ignore_cache=True)

    self.action_mock = action_mocks.ActionMock("TransferBuffer", "StatFile",
                                               "Find", "FingerprintFile",
                                               "HashBuffer", "UpdateVFSFile",
                                               "EnumerateInterfaces",
                                               "EnumerateFilesystems",
                                               "GetConfiguration", "GetConfig",
                                               "GetClientInfo",
                                               "GetInstallDate",
                                               "GetPlatformInfo",
                                               "EnumerateUsers",
                                               "ListDirectory")

    self.client_mock = test_lib.MockClient(self.client_id, self.action_mock,
                                           token=self.token)

    self.update_stubber = utils.Stubber(
        self.grr_fuse, "_RunAndWaitForVFSFileUpdate",
        self._RunAndWaitForVFSFileUpdate)
    self.update_stubber.Start()

    self.start_flow_stubber = utils.Stubber(
        flow_utils, "StartFlowAndWait",
        self.StartFlowAndWait)
    self.start_flow_stubber.Start()

  def tearDown(self):
    super(GRRFuseTest, self).tearDown()
    self.update_stubber.Stop()
    self.update_stubber.Stop()

  def _RunAndWaitForVFSFileUpdate(self, path):
    for _ in test_lib.TestFlowHelper("UpdateVFSFile", self.action_mock,
                                     token=self.token, client_id=self.client_id,
                                     vfs_file_urn=path):
      pass

  def ClientPathToAFF4Path(self, client_side_path):
    return "/%s/fs/os%s" % (self.client_name, client_side_path)

  def StartFlowAndWait(self, client_id, token=None,
                       timeout=None, **flow_args):
    for _ in test_lib.TestFlowHelper(
        flow_args.pop("flow_name"), self.action_mock, token=self.token,
        client_id=self.client_id, **flow_args):
      pass

  def ListDirectoryOnClient(self, path):
    # NOTE: Path is a client side path, so does not have a leading
    # /<client name>/fs/os

    pathspec = rdfvalue.PathSpec(path=path, pathtype="OS")

    for _ in test_lib.TestFlowHelper("ListDirectory", self.action_mock,
                                     pathspec=pathspec, token=self.token,
                                     client_id=self.client_id):
      pass

  def testReadDoesNotTimeOut(self):

    # Make sure to use the least topical meme we can think of as dummy data.
    filename = self.WriteFileAndList("password.txt", "hunter2")
    self.assertEqual(self.grr_fuse.Read(self.ClientPathToAFF4Path(filename),
                                        length=len("hunter2"), offset=0),
                     "hunter2")

  def WriteFileAndList(self, filename, contents):
    path = os.path.join(self.temp_dir, filename)
    with open(path, "w") as f:
      f.write(contents)

    self.ListDirectoryOnClient(self.temp_dir)

    return path

  def testUpdateSparseImageChunks(self):
    """Make sure the right chunks get updated when we read a sparse file."""
    filename = "bigfile.txt"
    path = os.path.join(self.temp_dir, filename)
    contents = "bigdata!"* 1024 * 8 * 20
    start_point = 1024 * 64 * 10

    with open(path, "w") as f:
      f.seek(start_point)
      f.write(contents)

    # Update the directory listing so we can see the file.
    self.ListDirectoryOnClient(self.temp_dir)

    # Backup the previous settings.
    old_size_threshold = self.grr_fuse.size_threshold
    old_max_age = self.grr_fuse.max_age_before_refresh

    # Make sure the file is a sparse image (It's too small to fulfil the default
    # size requirements).
    self.grr_fuse.force_sparse_image = True
    self.grr_fuse.size_threshold = 0

    # Temporarily use cache so we can check which chunks are missing properly.
    self.grr_fuse.max_age_before_refresh = datetime.timedelta(seconds=30)

    self.assertEqual(self.grr_fuse.Read(self.ClientPathToAFF4Path(path),
                                        length=len(contents),
                                        offset=start_point),
                     contents)

    # Make sure it's an AFF4SparseImage
    fd = aff4.FACTORY.Open(self.ClientPathToAFF4Path(path), token=self.token)
    fd.Flush()
    self.assertIsInstance(fd, standard.AFF4SparseImage)

    missing_chunks = self.grr_fuse.GetMissingChunks(
        fd,
        # Subtract 1 so we don't overflow into the next chunk (30), which is of
        # course missing.
        length=len(contents) + start_point - 1,
        offset=0)

    # We don't have anything written before start_point,
    # so we should say the chunks are missing.
    self.assertSequenceEqual(missing_chunks, range(10))

    # Now we read and make sure the contents are as we expect.
    fuse_contents = self.grr_fuse.Read(self.ClientPathToAFF4Path(path),
                                       length=len(contents),
                                       offset=start_point)

    self.assertEqual(fuse_contents, contents)

    # Now, we'll write to the file in those previously missing chunks.
    with open(path, "w+") as f:
      f.seek(0)
      f.write("Y" * (start_point))

    # Expire the chunks so we update all of them.
    self.grr_fuse.max_age_before_refresh = datetime.timedelta(seconds=0)
    # After we read, there should be no missing chunks in the range from before.
    # Note that we read from offset 0, not from start_point.
    # We also only read halfway into the data from before.
    fuse_contents = self.grr_fuse.Read(self.ClientPathToAFF4Path(path),
                                       length=len(contents), offset=0)

    # Put a cache time back on, all chunks should be not missing.
    self.grr_fuse.max_age_before_refresh = datetime.timedelta(seconds=30)
    missing_chunks = self.grr_fuse.GetMissingChunks(
        fd,
        # Subtract 1 so we don't overflow into the next chunk (30), which is of
        # course missing.
        length=len(contents) + start_point - 1,
        offset=0)

    self.assertFalse(missing_chunks)

    # Reset all the flags we set earlier.
    self.grr_fuse.force_sparse_image = False
    self.grr_fuse.size_threshold = old_size_threshold
    self.grr_fuse.max_age_before_refresh = old_max_age

  def testCacheExpiry(self):
    with test_lib.FakeDateTimeUTC(1000):
      with test_lib.FakeTime(1000):
        max_age_before_refresh_seconds = 5
        # For this test only, actually set a cache expiry.
        self.grr_fuse.max_age_before_refresh = datetime.timedelta(
            seconds=max_age_before_refresh_seconds)

        # Make a new, uncached directory.
        new_dir = os.path.join(self.temp_dir, "new_caching_dir")
        os.mkdir(new_dir)
        aff4_path = self.ClientPathToAFF4Path(new_dir)

        # Access it, caching it.
        self.grr_fuse.readdir(aff4_path)

    with test_lib.FakeDateTimeUTC(1004):
      self.assertFalse(self.grr_fuse.DataRefreshRequired(aff4_path))

    with test_lib.FakeDateTimeUTC(1006):
      self.assertTrue(self.grr_fuse.DataRefreshRequired(aff4_path))

    # Remove the temp cache expiry we set earlier.
    self.grr_fuse.max_age_before_refresh = datetime.timedelta(seconds=0)

  def testClientSideUpdateDirectoryContents(self):
    self.ListDirectoryOnClient(self.temp_dir)
    contents = self.grr_fuse.Readdir(self.ClientPathToAFF4Path(self.temp_dir))
    self.assertNotIn("password.txt", contents)
    self.WriteFileAndList("password.txt", "hunter2")
    contents = self.grr_fuse.Readdir(self.ClientPathToAFF4Path(self.temp_dir))
    self.assertIn("password.txt", contents)

  def testClientSideUpdateFileContents(self):

    new_contents = "hunter2" * 5
    filename = self.WriteFileAndList("password.txt", "password1")
    aff4path = self.ClientPathToAFF4Path(filename)
    read_data = self.grr_fuse.Read(aff4path)
    self.assertEqual(read_data, "password1")
    filename = self.WriteFileAndList("password.txt", new_contents)
    read_data = self.grr_fuse.Read(aff4path)
    self.assertEqual(read_data, new_contents)

  def testReadNonzeroOffset(self):

    filename = self.WriteFileAndList("password.txt", "password1")
    self.assertEqual(self.grr_fuse.Read(self.ClientPathToAFF4Path(filename),
                                        length=5, offset=3),
                     "sword")

  def RunFakeWorkerAndClient(self, client_mock, worker_mock):
    """Runs a fake client and worker until both have empty queues.

    Args:
      client_mock: The MockClient object whose queue we'll grab tasks from.
      worker_mock: Used to mock run the flows.

    This function will run in a background thread while the tests run, and
    will end when self.done is True.
    """
    # Run the client and worker until nothing changes any more.
    while True:
      if self.done:
        break

      if client_mock:
        client_processed = client_mock.Next()
      else:
        client_processed = 0

      flows_run = []
      for flow_run in worker_mock.Next():
        self.total_flows.add(flow_run)
        flows_run.append(flow_run)

      if client_processed == 0 and not flows_run:
        # If we're stopping because there's nothing in the queue, don't stop
        # running if we've more tests to do.
        if self.done:
          break


class FlowTestLoader(test_lib.GRRTestLoader):
  base_class = GRRFuseTestBase


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv, testLoader=FlowTestLoader())

if __name__ == "__main__":
  flags.StartMain(main)
