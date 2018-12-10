#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests for grr.tools.fuse_mount.py."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import datetime
import os


from grr_response_client.client_actions import admin
from grr_response_client.client_actions import searching
from grr_response_client.client_actions import standard
from grr_response_client.client_actions.linux import linux
from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import aff4
from grr_response_server import flow_utils
from grr_response_server.aff4_objects import aff4_grr
from grr_response_server.aff4_objects import standard as aff4_standard
from grr_response_server.bin import fuse_mount
from grr_response_server.flows.general import filesystem
from grr.test_lib import action_mocks
from grr.test_lib import fixture_test_lib

from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib

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
    fixture_test_lib.ClientFixture(self.client_name, token=self.token)
    self.root = "/"

    self.passthrough = fuse_mount.GRRFuseDatastoreOnly(
        self.root, token=self.token)

  def testInvalidAFF4Root(self):
    with self.assertRaises(IOError):
      fuse_mount.GRRFuseDatastoreOnly("not_a_valid_path", token=self.token)

  def _TestReadDir(self, directory):
    contents = list(self.passthrough.readdir(directory))

    for item in contents:
      # All the filenames should be unicode strings.
      self.assertIsInstance(item, unicode)
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
    file_path = os.path.join(self.root, self.client_name, "fs/os/c/bin/bash")
    with self.assertRaises(MockFuseOSError):
      # We iterate through the generator so the error actually gets thrown.
      list(self.passthrough.readdir(file_path))

  def testAccessingDirThatDoesNotExist(self):
    with self.assertRaises(MockFuseOSError):
      list(
          self.passthrough.getattr("aff4:/This string is so silly",
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

    self.assertEqual(
        self.passthrough.getattr("/"), self.passthrough.MakePartialStat(fd))

  def testGetAttrFile(self):
    path = "/foreman"

    fd = aff4.FACTORY.Open(path, token=self.token)

    self.assertEqual(
        self.passthrough.getattr("/foreman"),
        self.passthrough.MakePartialStat(fd))

  def testExistingFileStat(self):
    bash_stat = {
        "st_ctime":
            rdfvalue.RDFDatetimeSeconds(1299502221),
        "st_rdev":
            0,
        "st_mtime":
            rdfvalue.RDFDatetimeSeconds(1284154642),
        "st_blocks":
            16,
        "st_nlink":
            1,
        "st_gid":
            0,
        "st_blksize":
            4096,
        "pathspec":
            rdf_paths.PathSpec(
                path="/bin/bash", pathtype="OS", path_options="CASE_LITERAL"),
        "st_dev":
            51713,
        "st_size":
            4874,
        "st_ino":
            1026148,
        "st_uid":
            0,
        "st_mode":
            rdf_client_fs.StatMode(33261),
        "st_atime":
            rdfvalue.RDFDatetimeSeconds(1299502220)
    }

    bash_path = os.path.join("/", self.client_name, "fs/os/c/bin/bash")
    self.assertCountEqual(self.passthrough.getattr(bash_path), bash_stat)

  def testReadNotFile(self):
    existing_dir = os.path.join(self.root, self.client_name, "/fs/os/c/bin")
    with self.assertRaises(MockFuseOSError):
      self.passthrough.Read(existing_dir)


class GRRFuseTest(GRRFuseTestBase):

  # Whether the tests are done and the fake server can stop running.
  done = False

  def setUp(self):
    super(GRRFuseTest, self).setUp()

    self.client_id = self.SetupClient(0, system="Linux")

    self.client_name = str(self.client_id)[len("aff4:/"):]

    with aff4.FACTORY.Create(
        self.client_id.Add("fs/os"),
        aff4_standard.VFSDirectory,
        mode="rw",
        token=self.token) as fd:
      fd.Set(fd.Schema.PATHSPEC(path="/", pathtype="OS"))

    # Ignore cache so our tests always get client side updates.
    self.grr_fuse = fuse_mount.GRRFuse(
        root="/", token=self.token, ignore_cache=True)

    self.action_mock = action_mocks.ActionMock(
        admin.GetClientInfo,
        admin.GetConfiguration,
        admin.GetPlatformInfo,
        linux.EnumerateFilesystems,
        linux.EnumerateInterfaces,
        linux.EnumerateUsers,
        linux.GetInstallDate,
        searching.Find,
        standard.HashBuffer,
        standard.HashFile,
        standard.ListDirectory,
        standard.GetFileStat,
        standard.TransferBuffer,
    )

    self.client_mock = flow_test_lib.MockClient(
        self.client_id, self.action_mock, token=self.token)

    self.update_stubber = utils.Stubber(self.grr_fuse,
                                        "_RunAndWaitForVFSFileUpdate",
                                        self._RunAndWaitForVFSFileUpdate)
    self.update_stubber.Start()

    self.start_flow_stubber = utils.Stubber(flow_utils, "StartFlowAndWait",
                                            self.StartFlowAndWait)
    self.start_flow_stubber.Start()

  def tearDown(self):
    super(GRRFuseTest, self).tearDown()
    self.update_stubber.Stop()
    self.start_flow_stubber.Stop()

  def _RunAndWaitForVFSFileUpdate(self, path):
    flow_test_lib.TestFlowHelper(
        aff4_grr.UpdateVFSFile.__name__,
        self.action_mock,
        token=self.token,
        client_id=self.client_id,
        vfs_file_urn=path)

  def ClientPathToAFF4Path(self, client_side_path):
    return "/%s/fs/os%s" % (self.client_name, client_side_path)

  def StartFlowAndWait(self, client_id, token=None, timeout=None, **flow_args):
    flow_test_lib.TestFlowHelper(
        flow_args.pop("flow_name"),
        self.action_mock,
        token=self.token,
        client_id=self.client_id,
        **flow_args)

  def ListDirectoryOnClient(self, path):
    # NOTE: Path is a client side path, so does not have a leading
    # /<client name>/fs/os

    pathspec = rdf_paths.PathSpec(path=path, pathtype="OS")

    flow_test_lib.TestFlowHelper(
        filesystem.ListDirectory.__name__,
        self.action_mock,
        pathspec=pathspec,
        token=self.token,
        client_id=self.client_id)

  def testReadDoesNotTimeOut(self):

    # Make sure to use the least topical meme we can think of as dummy data.
    filename = self.WriteFileAndList("password.txt", "hunter2")
    self.assertEqual(
        self.grr_fuse.Read(
            self.ClientPathToAFF4Path(filename),
            length=len("hunter2"),
            offset=0), "hunter2")

  def WriteFileAndList(self, filename, contents):
    path = os.path.join(self.temp_dir, filename)
    with open(path, "wb") as f:
      f.write(contents)

    self.ListDirectoryOnClient(self.temp_dir)

    return path

  def testUpdateSparseImageChunks(self):
    """Make sure the right chunks get updated when we read a sparse file."""
    with utils.MultiStubber((self.grr_fuse, "force_sparse_image", True),
                            (self.grr_fuse, "max_age_before_refresh",
                             datetime.timedelta(seconds=30)),
                            (self.grr_fuse, "size_threshold", 0)):
      self._testUpdateSparseImageChunks()

  def _testUpdateSparseImageChunks(self):
    """Make sure the right chunks get updated when we read a sparse file."""
    filename = "bigfile.txt"
    path = os.path.join(self.temp_dir, filename)
    chunksize = aff4_standard.AFF4SparseImage.chunksize

    # 8 chunks of data.
    contents = "bigdata!" * chunksize
    # We want to start reading in the middle of a chunk.
    start_point = int(2.5 * chunksize)
    read_len = int(2.5 * chunksize)

    client_path = self.ClientPathToAFF4Path(path)

    with open(path, "wb") as f:
      f.seek(start_point)
      f.write(contents)

    # Update the directory listing so we can see the file.
    self.ListDirectoryOnClient(self.temp_dir)

    # Make sure refreshing is allowed.
    with utils.Stubber(self.grr_fuse, "max_age_before_refresh",
                       datetime.timedelta(seconds=0)):
      # Read 3 chunks, from #2 to #4.
      data = self.grr_fuse.Read(
          client_path, length=read_len, offset=start_point)
      self.assertEqual(data, contents[start_point:start_point + read_len],
                       "Fuse contents don't match.")

    # Make sure it's an AFF4SparseImage
    fd = aff4.FACTORY.Open(client_path, mode="rw", token=self.token)
    self.assertIsInstance(fd, aff4_standard.AFF4SparseImage)

    missing_chunks = self.grr_fuse.GetMissingChunks(
        fd, length=10 * chunksize, offset=0)
    # 10 chunks but not #2 - #4 that we already got.
    self.assertEqual(missing_chunks, [0, 1, 5, 6, 7, 8, 9])

    # Make sure refreshing is allowed.
    with utils.Stubber(self.grr_fuse, "max_age_before_refresh",
                       datetime.timedelta(seconds=0)):
      # Now we read and make sure the contents are as we expect.
      fuse_contents = self.grr_fuse.Read(
          client_path, length=8 * chunksize, offset=0)
      expected_contents = ("\x00" * start_point + contents)[:8 * chunksize]

    self.assertEqual(fuse_contents, expected_contents,
                     "Fuse contents don't match.")

    expected_contents = ("Y" * start_point + contents)[:8 * chunksize]

    # Now, we'll write to the file in those previously missing chunks.
    with open(path, "wb+") as f:
      f.seek(0)
      f.write(expected_contents)

    # Enable refresh.
    with utils.Stubber(self.grr_fuse, "max_age_before_refresh",
                       datetime.timedelta(seconds=0)):
      fuse_contents = self.grr_fuse.Read(
          client_path, length=len(contents), offset=0)

    self.assertEqual(fuse_contents, expected_contents,
                     "Fuse contents don't match.")

    # Put a cache time back on, all chunks should be not missing.
    self.grr_fuse.max_age_before_refresh = datetime.timedelta(seconds=30)
    missing_chunks = self.grr_fuse.GetMissingChunks(
        fd, length=8 * chunksize, offset=0)

    self.assertEqual(missing_chunks, [])

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
    self.assertEqual(
        self.grr_fuse.Read(
            self.ClientPathToAFF4Path(filename), length=5, offset=3), "sword")

  def RunFakeWorkerAndClient(self, client_mock, worker_mock):
    """Runs a fake client and worker until both have empty queues.

    This function will run in a background thread while the tests run, and will
    end when self.done is True.

    Args:
      client_mock: The MockClient object whose queue we'll grab tasks from.
      worker_mock: Used to mock run the flows.
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


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
