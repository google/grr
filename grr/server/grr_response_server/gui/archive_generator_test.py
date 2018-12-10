#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Contains tests for archive_generator."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import hashlib
import os
import tarfile
import zipfile


import mock
import yaml

from grr_response_core.lib import flags

from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server.gui import archive_generator
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import db_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class CollectionArchiveGeneratorTest(test_lib.GRRBaseTest):
  """Test for CollectionArchiveGenerator."""

  def setUp(self):
    super(CollectionArchiveGeneratorTest, self).setUp()
    self.client_id = self.SetupClient(0)

  def _CreateFile(self,
                  path,
                  content,
                  hashing=False,
                  aff4_type=aff4.AFF4MemoryStream):
    if hashing:
      digest = hashlib.sha256(content).digest()
    else:
      digest = None

    if data_store.RelationalDBReadEnabled("filestore"):
      self.assertTrue(data_store.RelationalDBWriteEnabled())
      self.assertTrue(hashing)
    else:
      with aff4.FACTORY.Create(path, aff4_type, token=self.token) as fd:
        fd.Write(content)

        if digest:
          fd.Set(fd.Schema.HASH, rdf_crypto.Hash(sha256=digest))

    if data_store.RelationalDBWriteEnabled() and hashing:
      client_id, vfs_path = path.Split(2)
      path_type, components = rdf_objects.ParseCategorizedPath(vfs_path)

      path_info = rdf_objects.PathInfo()
      path_info.path_type = path_type
      path_info.components = components

      blob_id = rdf_objects.BlobID.FromBytes(digest)
      data_store.BLOBS.WriteBlobs({blob_id: content})
      hash_id = file_store.AddFileWithUnknownHash([blob_id])
      path_info.hash_entry.sha256 = hash_id.AsBytes()

      data_store.REL_DB.WritePathInfos(client_id, [path_info])

  def _InitializeFiles(self, hashing=False):
    path1 = self.client_id.Add("fs/os/foo/bar/hello1.txt")
    archive_path1 = (
        "test_prefix/%s/fs/os/foo/bar/hello1.txt" % self.client_id.Basename())
    self._CreateFile(
        path=path1, content="hello1".encode("utf-8"), hashing=hashing)

    path2 = self.client_id.Add("fs/os/foo/bar/中国新闻网新闻中.txt")
    archive_path2 = ("test_prefix/%s/fs/os/foo/bar/"
                     "中国新闻网新闻中.txt") % self.client_id.Basename()
    self._CreateFile(
        path=path2, content="hello2".encode("utf-8"), hashing=hashing)

    self.stat_entries = []
    self.paths = [path1, path2]
    self.archive_paths = [archive_path1, archive_path2]
    for path in self.paths:
      self.stat_entries.append(
          rdf_client_fs.StatEntry(
              pathspec=rdf_paths.PathSpec(
                  path="foo/bar/" + unicode(path).split("/")[-1],
                  pathtype=rdf_paths.PathSpec.PathType.OS)))

  def _GenerateArchive(
      self,
      collection,
      archive_format=archive_generator.CollectionArchiveGenerator.ZIP,
      predicate=None):

    fd_path = os.path.join(self.temp_dir, "archive")
    generator = archive_generator.CompatCollectionArchiveGenerator(
        archive_format=archive_format,
        predicate=predicate,
        prefix="test_prefix",
        description="Test description",
        client_id=self.client_id)
    with open(fd_path, "wb") as out_fd:
      for chunk in generator.Generate(collection, token=self.token):
        out_fd.write(chunk)

    return fd_path

  @db_test_lib.LegacyDataStoreOnly
  def testLegacyDoesNotSkipFilesWithoutHashWhenZipArchiving(self):
    self._InitializeFiles(hashing=False)

    fd_path = self._GenerateArchive(
        self.stat_entries,
        archive_format=archive_generator.CollectionArchiveGenerator.ZIP)

    with zipfile.ZipFile(fd_path) as zip_fd:
      names = [unicode(s) for s in zip_fd.namelist()]

      # Check that both files are in the archive.
      for p in self.archive_paths:
        self.assertIn(p, names)

  @db_test_lib.LegacyDataStoreOnly
  def testLegacyDoesNotSkipFilesWithoutHashWhenTarArchiving(self):
    self._InitializeFiles(hashing=False)

    fd_path = self._GenerateArchive(
        self.stat_entries,
        archive_format=archive_generator.CollectionArchiveGenerator.TAR_GZ)

    with tarfile.open(fd_path) as tar_fd:
      infos = list(tar_fd)

      # Check that both files are in the archive.
      names = [i.name.decode("utf-8") for i in infos]
      for p in self.archive_paths:
        self.assertIn(p, names)

  def testCreatesZipContainingFilesAndClientInfosAndManifest(self):
    self._InitializeFiles(hashing=True)

    fd_path = self._GenerateArchive(
        self.stat_entries,
        archive_format=archive_generator.CollectionArchiveGenerator.ZIP)

    zip_fd = zipfile.ZipFile(fd_path)
    names = [unicode(s) for s in sorted(zip_fd.namelist())]

    client_info_name = (
        "test_prefix/%s/client_info.yaml" % self.client_id.Basename())
    manifest_name = "test_prefix/MANIFEST"

    self.assertCountEqual(
        names, self.archive_paths + [client_info_name, manifest_name])

    contents = zip_fd.read(self.archive_paths[0])
    self.assertEqual(contents, "hello1")

    contents = zip_fd.read(self.archive_paths[1])
    self.assertEqual(contents, "hello2")

    manifest = yaml.safe_load(zip_fd.read(manifest_name))
    self.assertEqual(
        manifest, {
            "description": "Test description",
            "processed_files": 2,
            "archived_files": 2,
            "ignored_files": 0,
            "failed_files": 0
        })

    client_info = yaml.safe_load(zip_fd.read(client_info_name))

    try:
      self.assertEqual(client_info["knowledge_base"]["fqdn"],
                       "Host-0.example.com")
    except KeyError:  # AFF4
      self.assertEqual(client_info["system_info"]["fqdn"], "Host-0.example.com")

  def testCreatesTarContainingFilesAndClientInfosAndManifest(self):
    self._InitializeFiles(hashing=True)

    fd_path = self._GenerateArchive(
        self.stat_entries,
        archive_format=archive_generator.CollectionArchiveGenerator.TAR_GZ)

    with tarfile.open(fd_path) as tar_fd:
      manifest_fd = tar_fd.extractfile("test_prefix/MANIFEST")
      self.assertEqual(
          yaml.safe_load(manifest_fd.read()), {
              "description": "Test description",
              "processed_files": 2,
              "archived_files": 2,
              "ignored_files": 0,
              "failed_files": 0
          })

      self.assertEqual(
          tar_fd.extractfile(self.archive_paths[0].encode("utf-8")).read(),
          "hello1")
      self.assertEqual(
          tar_fd.extractfile(self.archive_paths[1].encode("utf-8")).read(),
          "hello2")

      client_info_name = (
          "test_prefix/%s/client_info.yaml" % self.client_id.Basename())
      client_info = yaml.safe_load(tar_fd.extractfile(client_info_name).read())

      try:
        self.assertEqual(client_info["knowledge_base"]["fqdn"],
                         "Host-0.example.com")
      except KeyError:  # AFF4
        self.assertEqual(client_info["system_info"]["fqdn"],
                         "Host-0.example.com")

  def testCorrectlyAccountsForFailedFiles(self):
    self._InitializeFiles(hashing=True)

    orig_stream_file_chunks = file_store.StreamFilesChunks

    def mock_read_file_chunks(client_paths):
      for path in client_paths:
        if path.Path() == "foo/bar/中国新闻网新闻中.txt":
          raise Exception()
      return orig_stream_file_chunks(client_paths)

    orig_aff4_stream = aff4.AFF4Stream.MultiStream

    def mock_aff4_stream(fds):
      results = list(orig_aff4_stream(fds))
      for i, result in enumerate(results):
        if result[0].urn.Path().endswith("foo/bar/中国新闻网新闻中.txt"):
          results[i] = (result[0], None, Exception())
      return results

    with mock.patch.object(
        file_store, "StreamFilesChunks", side_effect=mock_read_file_chunks):
      with mock.patch.object(
          aff4.AFF4Stream, "MultiStream", side_effect=mock_aff4_stream):
        fd_path = self._GenerateArchive(
            self.stat_entries,
            archive_format=archive_generator.CollectionArchiveGenerator.ZIP)

    zip_fd = zipfile.ZipFile(fd_path)
    names = [unicode(s) for s in sorted(zip_fd.namelist())]
    self.assertIn(self.archive_paths[0], names)
    self.assertNotIn(self.archive_paths[1], names)

    manifest = yaml.safe_load(zip_fd.read("test_prefix/MANIFEST"))
    self.assertEqual(
        manifest, {
            "description":
                "Test description",
            "processed_files":
                2,
            "archived_files":
                1,
            "ignored_files":
                0,
            "failed_files":
                1,
            "failed_files_list": [
                "aff4:/%s/fs/os/foo/bar/中国新闻网新闻中.txt" %
                self.client_id.Basename()
            ]
        })

  def testIgnoresFilesNotMatchingPredicate(self):
    self._InitializeFiles(hashing=True)

    def predicate(pathspec):
      return os.path.basename(pathspec.Path()).startswith("hello")

    fd_path = self._GenerateArchive(
        self.stat_entries,
        predicate=predicate,
        archive_format=archive_generator.CollectionArchiveGenerator.ZIP)

    zip_fd = zipfile.ZipFile(fd_path)
    names = sorted(zip_fd.namelist())

    # The archive is expected to contain 1 file contents blob, 1 client info and
    # a manifest.
    self.assertLen(names, 3)

    manifest = yaml.safe_load(zip_fd.read("test_prefix/MANIFEST"))
    self.assertEqual(
        manifest, {
            "description":
                "Test description",
            "processed_files":
                2,
            "archived_files":
                1,
            "ignored_files":
                1,
            "failed_files":
                0,
            "ignored_files_list": [
                "aff4:/%s/fs/os/foo/bar/中国新闻网新闻中.txt" %
                self.client_id.Basename()
            ]
        })


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
