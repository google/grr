#!/usr/bin/env python
"""Tests for export utils functions."""

import os
import stat


from grr.lib import aff4
from grr.lib import export_utils
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import collects
from grr.lib.aff4_objects import standard
from grr.lib.flows.general import collectors
from grr.lib.flows.general import file_finder
from grr.lib.hunts import results
from grr.lib.rdfvalues import client as rdf_client


class TestExports(test_lib.FlowTestsBaseclass):
  """Tests exporting of data."""

  def setUp(self):
    super(TestExports, self).setUp()

    self.out = self.client_id.Add("fs/os")
    self.CreateFile("testfile1")
    self.CreateFile("testfile2")
    self.CreateFile("testfile5")
    self.CreateFile("testfile6")
    self.CreateDir("testdir1")
    self.CreateFile("testdir1/testfile3")
    self.CreateDir("testdir1/testdir2")
    self.CreateFile("testdir1/testdir2/testfile4")

  def CreateDir(self, dirpath):
    path = self.out.Add(*dirpath.split("/"))
    fd = aff4.FACTORY.Create(path, standard.VFSDirectory, token=self.token)
    fd.Close()

  def CreateFile(self, filepath):
    path = self.out.Add(filepath)
    fd = aff4.FACTORY.Create(path, aff4_grr.VFSMemoryFile, token=self.token)
    fd.Write("some data")
    fd.Close()

  def testExportFile(self):
    """Check we can export a file without errors."""
    with utils.TempDirectory() as tmpdir:
      export_utils.CopyAFF4ToLocal(
          self.out.Add("testfile1"),
          tmpdir,
          overwrite=True,
          token=self.token)
      expected_outdir = os.path.join(tmpdir, self.out.Path()[1:])
      self.assertTrue("testfile1" in os.listdir(expected_outdir))

  def _VerifyDownload(self):
    with utils.TempDirectory() as tmpdir:
      export_utils.DownloadCollection("aff4:/testcoll",
                                      tmpdir,
                                      overwrite=True,
                                      dump_client_info=True,
                                      token=self.token,
                                      max_threads=2)
      expected_outdir = os.path.join(tmpdir, self.out.Path()[1:])

      # Check we found both files.
      self.assertTrue("testfile1" in os.listdir(expected_outdir))
      self.assertTrue("testfile2" in os.listdir(expected_outdir))
      self.assertTrue("testfile5" in os.listdir(expected_outdir))
      self.assertTrue("testfile6" in os.listdir(expected_outdir))

      # Check we dumped a YAML file to the root of the client.
      expected_rootdir = os.path.join(tmpdir, self.client_id.Basename())
      self.assertTrue("client_info.yaml" in os.listdir(expected_rootdir))

  def testDownloadHuntResultCollection(self):
    """Check we can download files references in HuntResultCollection."""
    # Create a collection with URNs to some files.
    fd = aff4.FACTORY.Create("aff4:/testcoll",
                             results.HuntResultCollection,
                             token=self.token)
    fd.AddAsMessage(rdfvalue.RDFURN(self.out.Add("testfile1")), self.client_id)
    fd.AddAsMessage(
        rdf_client.StatEntry(aff4path=self.out.Add("testfile2")),
        self.client_id)
    fd.AddAsMessage(
        file_finder.FileFinderResult(stat_entry=rdf_client.StatEntry(
            aff4path=self.out.Add("testfile5"))),
        self.client_id)
    fd.AddAsMessage(
        collectors.ArtifactFilesDownloaderResult(
            downloaded_file=rdf_client.StatEntry(
                aff4path=self.out.Add("testfile6"))),
        self.client_id)
    fd.Close()
    self._VerifyDownload()

  def testDownloadCollection(self):
    """Check we can download files references in RDFValueCollection."""
    # Create a collection with URNs to some files.
    fd = aff4.FACTORY.Create("aff4:/testcoll",
                             collects.RDFValueCollection,
                             token=self.token)
    fd.Add(rdfvalue.RDFURN(self.out.Add("testfile1")))
    fd.Add(rdf_client.StatEntry(aff4path=self.out.Add("testfile2")))
    fd.Add(file_finder.FileFinderResult(stat_entry=rdf_client.StatEntry(
        aff4path=self.out.Add("testfile5"))))
    fd.Add(collectors.ArtifactFilesDownloaderResult(
        downloaded_file=rdf_client.StatEntry(aff4path=self.out.Add(
            "testfile6"))))
    fd.Close()
    self._VerifyDownload()

  def testDownloadCollectionIgnoresArtifactResultsWithoutFiles(self):
    # Create a collection with URNs to some files.
    fd = aff4.FACTORY.Create("aff4:/testcoll",
                             collects.RDFValueCollection,
                             token=self.token)
    fd.Add(collectors.ArtifactFilesDownloaderResult())
    fd.Close()

    with utils.TempDirectory() as tmpdir:
      export_utils.DownloadCollection("aff4:/testcoll",
                                      tmpdir,
                                      overwrite=True,
                                      dump_client_info=True,
                                      token=self.token,
                                      max_threads=2)
      expected_outdir = os.path.join(tmpdir, self.out.Path()[1:])
      self.assertFalse(os.path.exists(expected_outdir))

  def testDownloadCollectionWithFlattenOption(self):
    """Check we can download files references in RDFValueCollection."""
    # Create a collection with URNs to some files.
    fd = aff4.FACTORY.Create("aff4:/testcoll",
                             collects.RDFValueCollection,
                             token=self.token)
    fd.Add(rdfvalue.RDFURN(self.out.Add("testfile1")))
    fd.Add(rdf_client.StatEntry(aff4path=self.out.Add("testfile2")))
    fd.Add(file_finder.FileFinderResult(stat_entry=rdf_client.StatEntry(
        aff4path=self.out.Add("testfile5"))))
    fd.Close()

    with utils.TempDirectory() as tmpdir:
      export_utils.DownloadCollection("aff4:/testcoll",
                                      tmpdir,
                                      overwrite=True,
                                      dump_client_info=True,
                                      flatten=True,
                                      token=self.token,
                                      max_threads=2)

      # Check that "files" folder is filled with symlinks to downloaded files.
      symlinks = os.listdir(os.path.join(tmpdir, "files"))
      self.assertEqual(len(symlinks), 3)
      self.assertListEqual(
          sorted(symlinks), ["C.1000000000000000_fs_os_testfile1",
                             "C.1000000000000000_fs_os_testfile2",
                             "C.1000000000000000_fs_os_testfile5"])
      self.assertEqual(
          os.readlink(os.path.join(tmpdir, "files",
                                   "C.1000000000000000_fs_os_testfile1")),
          os.path.join(tmpdir, "C.1000000000000000", "fs", "os", "testfile1"))

  def testDownloadCollectionWithFoldersEntries(self):
    """Check we can download RDFValueCollection that also references folders."""
    fd = aff4.FACTORY.Create("aff4:/testcoll",
                             collects.RDFValueCollection,
                             token=self.token)
    fd.Add(file_finder.FileFinderResult(stat_entry=rdf_client.StatEntry(
        aff4path=self.out.Add("testfile5"))))
    fd.Add(file_finder.FileFinderResult(stat_entry=rdf_client.StatEntry(
        aff4path=self.out.Add("testdir1"),
        st_mode=stat.S_IFDIR)))
    fd.Close()

    with utils.TempDirectory() as tmpdir:
      export_utils.DownloadCollection("aff4:/testcoll",
                                      tmpdir,
                                      overwrite=True,
                                      dump_client_info=True,
                                      token=self.token,
                                      max_threads=2)
      expected_outdir = os.path.join(tmpdir, self.out.Path()[1:])

      # Check we found both files.
      self.assertTrue("testfile5" in os.listdir(expected_outdir))
      self.assertTrue("testdir1" in os.listdir(expected_outdir))

  def testRecursiveDownload(self):
    """Check we can export a file without errors."""
    with utils.TempDirectory() as tmpdir:
      export_utils.RecursiveDownload(
          aff4.FACTORY.Open(self.out, token=self.token),
          tmpdir,
          overwrite=True)
      expected_outdir = os.path.join(tmpdir, self.out.Path()[1:])
      self.assertTrue("testfile1" in os.listdir(expected_outdir))
      full_outdir = os.path.join(expected_outdir, "testdir1", "testdir2")
      self.assertTrue("testfile4" in os.listdir(full_outdir))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
