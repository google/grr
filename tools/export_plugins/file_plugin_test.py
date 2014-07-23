#!/usr/bin/env python
"""Tests for the file export tool plugin."""


import argparse
import os

# pylint: disable=unused-import, g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import, g-bad-import-order

from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
from grr.tools.export_plugins import file_plugin


class FileExportPluginTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(FileExportPluginTest, self).setUp()

    client_ids = self.SetupClients(1)
    self.client_id = client_ids[0]
    self.out = self.client_id.Add("fs/os")

    data_store.default_token = rdfvalue.ACLToken(username="user",
                                                 reason="reason")
    self.GrantClientApproval(self.client_id, token=data_store.default_token)

  def CreateDir(self, dirpath):
    path = self.out.Add(dirpath)
    fd = aff4.FACTORY.Create(path, "VFSDirectory", token=self.token)
    fd.Close()

  def CreateFile(self, filepath):
    path = self.out.Add(filepath)
    fd = aff4.FACTORY.Create(path, "VFSMemoryFile", token=self.token)
    fd.Write("some data")
    fd.Close()

  def testExportFile(self):
    """Check we can export a file without errors."""
    self.CreateFile("testfile1")

    plugin = file_plugin.FileExportPlugin()
    parser = argparse.ArgumentParser()
    plugin.ConfigureArgParser(parser)

    with utils.TempDirectory() as tmpdir:
      plugin.Run(parser.parse_args(args=[
          "--path",
          str(self.out.Add("testfile1")),
          "--output",
          tmpdir]))

      expected_outdir = os.path.join(tmpdir, self.out.Path()[1:])
      self.assertTrue("testfile1" in os.listdir(expected_outdir))

  def testExportDir(self):
    """Check we can export a dir without errors."""
    self.CreateDir("testdir")
    self.CreateFile("testdir/testfile1")
    self.CreateFile("testdir/testfile2")
    self.CreateDir("testdir/testdir1")
    self.CreateFile("testdir/testdir1/testfile3")
    self.CreateDir("testdir/testdir1/testdir2")
    self.CreateFile("testdir/testdir1/testdir2/testfile4")

    plugin = file_plugin.FileExportPlugin()
    parser = argparse.ArgumentParser()
    plugin.ConfigureArgParser(parser)

    with utils.TempDirectory() as tmpdir:
      plugin.Run(parser.parse_args(args=[
          "--path",
          str(self.out.Add("testdir")),
          "--output",
          tmpdir]))

      expected_outdir = os.path.join(tmpdir,
                                     self.out.Add("testdir").Path()[1:])
      self.assertTrue("testfile1" in os.listdir(expected_outdir))
      full_outdir = os.path.join(expected_outdir, "testdir1", "testdir2")
      self.assertTrue("testfile4" in os.listdir(full_outdir))


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
