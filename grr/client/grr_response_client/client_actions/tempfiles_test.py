#!/usr/bin/env python
"""Tests for grr_response_client.client_actions.tempfiles."""

import io
import os
import shutil
import tempfile
from unittest import mock

from absl import app

from grr_response_client.client_actions import tempfiles
from grr_response_core import config
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr.test_lib import client_test_lib
from grr.test_lib import test_lib


class GRRTempFileTestFilename(test_lib.GRRBaseTest):
  """Tests for GRR temp file utils when filename is provided."""

  def setUp(self):
    """Create fake filesystem."""
    super().setUp()
    # This is where temp files go if a directory is not provided.
    # For this test it has to be different from the temp directory
    # so we create a new one.
    self.client_tempdir = tempfile.mkdtemp(
        dir=config.CONFIG.Get("Client.tempdir_roots")[0])

    tempdir_overrider = test_lib.ConfigOverrider({
        "Client.tempdir_roots": [os.path.dirname(self.client_tempdir)],
        "Client.grr_tempdir": os.path.basename(self.client_tempdir)
    })
    tempdir_overrider.Start()
    self.addCleanup(tempdir_overrider.Stop)

    # Remove the actual GRR temp dir.
    def cleanup():
      shutil.rmtree(tempfiles.GetDefaultGRRTempDirectory())

    self.addCleanup(cleanup)

  def testCreateAndDelete(self):
    fd = tempfiles.CreateGRRTempFile(filename="process.42.exe", mode="wb")
    fd.close()
    self.assertTrue(os.path.exists(fd.name))
    self.assertEqual(os.path.basename(fd.name), "process.42.exe")
    tempfiles.DeleteGRRTempFile(fd.name)
    self.assertFalse(os.path.exists(fd.name))

    with io.open(os.path.join(self.temp_dir, "notatmpfile"), "wb") as fd:
      fd.write(b"something")
    self.assertTrue(os.path.exists(fd.name))
    self.assertRaises(tempfiles.ErrorNotTempFile, tempfiles.DeleteGRRTempFile,
                      fd.name)
    self.assertTrue(os.path.exists(fd.name))

  def testWrongOwnerGetsFixed(self):

    lstat = os.lstat

    def mystat(filename):
      stat_info = lstat(filename)
      stat_list = list(stat_info)
      # Adjust the UID.
      stat_list[4] += 1
      return os.stat_result(stat_list)

    # Place a malicious file in the temp dir. This needs to be deleted
    # before we can use the temp dir.
    fd = tempfiles.CreateGRRTempFile(filename="maliciousfile", mode="wb")
    fd.close()

    self.assertTrue(os.path.exists(fd.name))

    with mock.patch.object(os, "lstat", mystat):
      fd2 = tempfiles.CreateGRRTempFile(filename="temptemp", mode="wb")
      fd2.close()

    # Old file is gone.
    self.assertFalse(os.path.exists(fd.name))

    # Cleanup.
    tempfiles.DeleteGRRTempFile(fd2.name)


class DeleteGRRTempFiles(client_test_lib.EmptyActionTest):
  """Test DeleteGRRTempFiles client action."""

  def setUp(self):
    super().setUp()
    filename = "%s_blah" % config.CONFIG["Client.tempfile_prefix"]
    self.tempfile = utils.JoinPath(self.temp_dir, "delete_test", filename)
    self.dirname = os.path.dirname(self.tempfile)
    os.makedirs(self.dirname)
    tempdir_overrider = test_lib.ConfigOverrider({
        "Client.tempdir_roots": [os.path.dirname(self.dirname)],
        "Client.grr_tempdir": os.path.basename(self.dirname)
    })
    tempdir_overrider.Start()
    self.addCleanup(tempdir_overrider.Stop)

    self.not_tempfile = os.path.join(self.temp_dir, "notatempfile")
    with io.open(self.not_tempfile, "wb") as fd:
      fd.write(b"something")

    self.temp_fd = tempfiles.CreateGRRTempFile(filename="file1")
    self.temp_fd2 = tempfiles.CreateGRRTempFile(filename="file2")
    self.assertTrue(os.path.exists(self.not_tempfile))
    self.assertTrue(os.path.exists(self.temp_fd.name))
    self.assertTrue(os.path.exists(self.temp_fd2.name))

    self.pathspec = rdf_paths.PathSpec(
        path=self.dirname, pathtype=rdf_paths.PathSpec.PathType.OS)

  def _SetUpTempDirStructure(self, grr_tempdir="grr_temp"):
    temproot1 = utils.JoinPath(self.temp_dir, "del_test1")
    temproot2 = utils.JoinPath(self.temp_dir, "del_test2")
    temproot3 = utils.JoinPath(self.temp_dir, "del_test3")
    tempdir1 = utils.JoinPath(temproot1, grr_tempdir)
    tempdir2 = utils.JoinPath(temproot2, grr_tempdir)
    tempdir3 = utils.JoinPath(temproot3, grr_tempdir)
    os.makedirs(tempdir1)
    os.makedirs(tempdir2)
    # Omit tempdir3.

    file1 = utils.JoinPath(tempdir1, "file1")
    file2 = utils.JoinPath(tempdir2, "file2")
    with io.open(file1, "wb") as fd:
      fd.write(b"something")
    with io.open(file2, "wb") as fd:
      fd.write(b"something")

    # Unrelated file in the tempdir_roots should be left alone.
    not_a_grr_file1 = utils.JoinPath(temproot1, "file1")
    not_a_grr_file2 = utils.JoinPath(temproot1, "file2")
    with io.open(not_a_grr_file1, "wb") as fd:
      fd.write(b"something")
    with io.open(not_a_grr_file2, "wb") as fd:
      fd.write(b"something")

    self.assertTrue(os.path.exists(file1))
    self.assertTrue(os.path.exists(file2))
    self.assertTrue(os.path.exists(not_a_grr_file1))
    self.assertTrue(os.path.exists(not_a_grr_file2))
    return ([temproot1, temproot2, temproot3], [tempdir1, tempdir2], [tempdir3],
            [file1, file2], [not_a_grr_file1, not_a_grr_file1])

  def testDeleteMultipleRoots(self):
    temp_dir = "grr_temp"
    test_data = self._SetUpTempDirStructure(temp_dir)
    roots, _, invalid_temp_dirs, temp_files, other_files = test_data

    with test_lib.ConfigOverrider({
        "Client.tempdir_roots": roots,
        "Client.grr_tempdir": temp_dir
    }):

      result = self.RunAction(tempfiles.DeleteGRRTempFiles,
                              rdf_paths.PathSpec())
      self.assertLen(result, 1)
      log = result[0].data
      for f in temp_files:
        self.assertIn(f, log)
      for f in invalid_temp_dirs:
        self.assertNotIn(f, log)

    for f in temp_files:
      self.assertFalse(os.path.exists(f))
    for f in other_files:
      self.assertTrue(os.path.exists(f))

  def testDeleteFilesInRoot(self):
    temp_dir = "grr_temp"
    test_data = self._SetUpTempDirStructure(temp_dir)
    roots, _, _, temp_files, other_files = test_data

    with test_lib.ConfigOverrider({
        "Client.tempdir_roots": roots,
        "Client.grr_tempdir": temp_dir
    }):

      for f in temp_files:
        result = self.RunAction(tempfiles.DeleteGRRTempFiles,
                                rdf_paths.PathSpec(path=f))
        self.assertLen(result, 1)
        self.assertIn(f, result[0].data)

      for f in other_files:
        self.assertRaises(tempfiles.ErrorNotTempFile, self.RunAction,
                          tempfiles.DeleteGRRTempFiles,
                          rdf_paths.PathSpec(path=f))

  def testDeleteGRRTempFilesInDirectory(self):
    result = self.RunAction(tempfiles.DeleteGRRTempFiles, self.pathspec)[0]
    self.assertTrue(os.path.exists(self.not_tempfile))
    self.assertFalse(os.path.exists(self.temp_fd.name))
    self.assertFalse(os.path.exists(self.temp_fd2.name))
    self.assertIn(self.temp_fd.name, result.data)
    self.assertIn(self.temp_fd2.name, result.data)

  def testDeleteGRRTempFilesSpecificPath(self):
    self.pathspec = rdf_paths.PathSpec(
        path=self.temp_fd.name, pathtype=rdf_paths.PathSpec.PathType.OS)
    result = self.RunAction(tempfiles.DeleteGRRTempFiles, self.pathspec)[0]
    self.assertTrue(os.path.exists(self.not_tempfile))
    self.assertFalse(os.path.exists(self.temp_fd.name))
    self.assertTrue(os.path.exists(self.temp_fd2.name))
    self.assertIn(self.temp_fd.name, result.data)
    self.assertNotIn(self.temp_fd2.name, result.data)

  def testDeleteGRRTempFilesPathDoesNotExist(self):
    self.pathspec = rdf_paths.PathSpec(
        path="/does/not/exist", pathtype=rdf_paths.PathSpec.PathType.OS)
    self.assertRaises(tempfiles.ErrorBadPath, self.RunAction,
                      tempfiles.DeleteGRRTempFiles, self.pathspec)

  def testOneFileFails(self):
    # Sneak in a non existing file.
    def listdir(path):
      _ = path
      res = []
      res.append(os.path.basename(self.temp_fd.name))
      res.append("not_really_a_file")
      res.append(os.path.basename(self.temp_fd2.name))
      return res

    with mock.patch.object(os, "listdir", listdir):
      result = self.RunAction(tempfiles.DeleteGRRTempFiles, self.pathspec)[0]
      self.assertIn("not_really_a_file does not exist", result.data)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
