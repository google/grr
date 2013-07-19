#!/usr/bin/env python
"""Tests for grr.client.client_actions.tempfiles."""

import os
import time

from grr.client.client_actions import tempfiles
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils


class GRRTempFileTest(test_lib.GRRBaseTest):
  """Tests for GRR temp file utils."""

  def setUp(self):
    """Create fake filesystem."""
    super(GRRTempFileTest, self).setUp()
    self.prefix = config_lib.CONFIG.Get("Client.tempfile_prefix")
    self.existsdir = os.path.join(self.temp_dir, "this/exists/")
    os.makedirs(self.existsdir)
    self.not_exists = os.path.join(self.temp_dir, "does/not/exist/")
    self.new_temp_file = os.path.join(self.not_exists, self.prefix)

  def _CheckPermissions(self, filename, expected):
    # Just look at the last 3 octets.
    file_mode = os.stat(filename).st_mode & 0777
    self.assertEqual(file_mode, expected)

  def testCreateGRRTempFile(self):
    fd = tempfiles.CreateGRRTempFile(self.not_exists, suffix=".exe")
    self.assertTrue(fd.name.startswith(self.new_temp_file))
    self.assertTrue(fd.name.endswith(".exe"))
    self.assertTrue(os.path.exists(fd.name))
    self._CheckPermissions(fd.name, 0700)
    self._CheckPermissions(os.path.dirname(fd.name), 0700)

  def testCreateGRRTempFileRelativePath(self):
    self.assertRaises(tempfiles.ErrorBadPath,
                      tempfiles.CreateGRRTempFile, "../../blah")

  def testCreateGRRTempFileWithLifetime(self):
    fd = tempfiles.CreateGRRTempFile(self.not_exists, lifetime=0.1)
    self.assertTrue(os.path.exists(fd.name))
    time.sleep(1)
    self.assertFalse(os.path.exists(fd.name))

  def testDeleteGRRTempFile(self):
    grr_tempfile = os.path.join(self.existsdir, self.prefix)
    open(grr_tempfile, "w").write("something")
    tempfiles.DeleteGRRTempFile(grr_tempfile)
    self.assertFalse(os.path.exists(grr_tempfile))

  def testDeleteGRRTempFileBadPrefix(self):
    self.assertRaises(tempfiles.ErrorNotTempFile,
                      tempfiles.DeleteGRRTempFile,
                      os.path.join(self.existsdir, "/blah"))

  def testDeleteGRRTempFileRelativePath(self):
    self.assertRaises(tempfiles.ErrorBadPath,
                      tempfiles.DeleteGRRTempFile, "../../blah")


class DeleteGRRTempFiles(test_lib.EmptyActionTest):
  """Test DeleteGRRTempFiles client action."""

  def setUp(self):
    super(DeleteGRRTempFiles, self).setUp()
    filename = "%s_blah" % config_lib.CONFIG["Client.tempfile_prefix"]
    self.tempfile = utils.JoinPath(self.temp_dir,
                                   "delete_test", filename)

    self.dirname = os.path.dirname(self.tempfile)
    os.makedirs(self.dirname)

    self.not_tempfile = os.path.join(self.dirname, "notatempfile")
    open(self.not_tempfile, "w").write("something")
    self.temp_fd = tempfiles.CreateGRRTempFile(self.dirname)
    self.temp_fd2 = tempfiles.CreateGRRTempFile(self.dirname)
    self.assertTrue(os.path.exists(self.not_tempfile))
    self.assertTrue(os.path.exists(self.temp_fd.name))
    self.assertTrue(os.path.exists(self.temp_fd2.name))

    self.pathspec = rdfvalue.PathSpec(
        path=self.dirname, pathtype=rdfvalue.PathSpec.PathType.OS)

  def testDeleteGRRTempFilesInDirectory(self):
    result = self.RunAction("DeleteGRRTempFiles",
                            self.pathspec)[0]
    self.assertTrue(os.path.exists(self.not_tempfile))
    self.assertFalse(os.path.exists(self.temp_fd.name))
    self.assertFalse(os.path.exists(self.temp_fd2.name))
    self.assertTrue(self.temp_fd.name in result.data)
    self.assertTrue(self.temp_fd2.name in result.data)

  def testDeleteGRRTempFilesSpecificPath(self):
    self.pathspec = rdfvalue.PathSpec(
        path=self.temp_fd.name, pathtype=rdfvalue.PathSpec.PathType.OS)
    result = self.RunAction("DeleteGRRTempFiles",
                            self.pathspec)[0]
    self.assertTrue(os.path.exists(self.not_tempfile))
    self.assertFalse(os.path.exists(self.temp_fd.name))
    self.assertTrue(os.path.exists(self.temp_fd2.name))
    self.assertTrue(self.temp_fd.name in result.data)
    self.assertFalse(self.temp_fd2.name in result.data)

  def testDeleteGRRTempFilesPathDoesNotExist(self):
    self.pathspec = rdfvalue.PathSpec(
        path="/does/not/exist", pathtype=rdfvalue.PathSpec.PathType.OS)
    self.assertRaises(tempfiles.ErrorBadPath,
                      self.RunAction, "DeleteGRRTempFiles", self.pathspec)


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
