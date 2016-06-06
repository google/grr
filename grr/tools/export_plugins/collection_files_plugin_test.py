#!/usr/bin/env python
"""Tests for the collection_files export tool plugin."""


import argparse
import os

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import collects
from grr.lib.aff4_objects import standard as aff4_standard

from grr.tools.export_plugins import collection_files_plugin


class CollectionFilesExportPluginTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(CollectionFilesExportPluginTest, self).setUp()

    client_ids = self.SetupClients(1)
    self.client_id = client_ids[0]
    self.out = self.client_id.Add("fs/os")

    data_store.default_token = access_control.ACLToken(username="user",
                                                       reason="reason")

  def CreateDir(self, dirpath):
    path = self.out.Add(dirpath)
    fd = aff4.FACTORY.Create(path, aff4_standard.VFSDirectory, token=self.token)
    fd.Close()

  def CreateFile(self, filepath):
    path = self.out.Add(filepath)
    fd = aff4.FACTORY.Create(path, aff4_grr.VFSMemoryFile, token=self.token)
    fd.Write("some data")
    fd.Close()

    return path

  def CreateCollection(self, collection_path, paths):
    with aff4.FACTORY.Create(collection_path,
                             collects.RDFValueCollection,
                             token=self.token) as fd:
      for p in paths:
        fd.Add(rdfvalue.RDFURN(p))

  def testExportsFilesFromRDFURNs(self):
    """Check we can export a file without errors."""
    testfile1_path = self.CreateFile("testfile1")
    self.CreateDir("some_dir")
    testfile2_path = self.CreateFile("some_dir/testfile2")
    collection_path = self.client_id.Add("Results")
    self.CreateCollection(collection_path, [testfile1_path, testfile2_path])

    plugin = collection_files_plugin.CollectionFilesExportPlugin()
    parser = argparse.ArgumentParser()
    plugin.ConfigureArgParser(parser)

    with utils.TempDirectory() as tmpdir:
      plugin.Run(parser.parse_args(args=[
          "--path", str(collection_path), "--output", tmpdir
      ]))

      expected_outdir = os.path.join(tmpdir, self.out.Path()[1:])
      self.assertTrue("testfile1" in os.listdir(expected_outdir))
      self.assertTrue("some_dir" in os.listdir(expected_outdir))
      self.assertTrue(
          "testfile2" in os.listdir(os.path.join(expected_outdir, "some_dir")))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
