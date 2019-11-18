#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Contains tests for archive_generator."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import hashlib
import os
import tarfile
import zipfile

from absl import app
from future.builtins import str

import mock
import yaml

from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util import compatibility
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server.databases import db
from grr_response_server.gui import archive_generator
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import test_lib


class CollectionArchiveGeneratorTest(test_lib.GRRBaseTest):
  """Test for CollectionArchiveGenerator."""

  def setUp(self):
    super(CollectionArchiveGeneratorTest, self).setUp()
    self.client_id = self.SetupClient(0)

  def _CreateFile(self, client_id, vfs_path, content):
    digest = hashlib.sha256(content).digest()
    path_type, components = rdf_objects.ParseCategorizedPath(vfs_path)

    path_info = rdf_objects.PathInfo()
    path_info.path_type = path_type
    path_info.components = components

    blob_id = rdf_objects.BlobID.FromSerializedBytes(digest)
    data_store.BLOBS.WriteBlobs({blob_id: content})
    blob_ref = rdf_objects.BlobReference(
        offset=0, size=len(content), blob_id=blob_id)
    hash_id = file_store.AddFileWithUnknownHash(
        db.ClientPath.FromPathInfo(client_id, path_info), [blob_ref])
    path_info.hash_entry.sha256 = hash_id.AsBytes()

    data_store.REL_DB.WritePathInfos(client_id, [path_info])

  def _InitializeFiles(self):
    path1 = "fs/os/foo/bar/hello1.txt"
    archive_path1 = ("test_prefix/%s/fs/os/foo/bar/hello1.txt" % self.client_id)
    self._CreateFile(
        client_id=self.client_id,
        vfs_path=path1,
        content="hello1".encode("utf-8"))

    path2 = "fs/os/foo/bar/中国新闻网新闻中.txt"
    archive_path2 = ("test_prefix/%s/fs/os/foo/bar/"
                     "中国新闻网新闻中.txt") % self.client_id
    self._CreateFile(
        client_id=self.client_id,
        vfs_path=path2,
        content="hello2".encode("utf-8"))

    self.stat_entries = []
    self.paths = [path1, path2]
    self.archive_paths = [archive_path1, archive_path2]
    for path in self.paths:
      self.stat_entries.append(
          rdf_client_fs.StatEntry(
              pathspec=rdf_paths.PathSpec(
                  path="foo/bar/" + str(path).split("/")[-1],
                  pathtype=rdf_paths.PathSpec.PathType.OS)))

  def _GenerateArchive(
      self,
      collection,
      archive_format=archive_generator.CollectionArchiveGenerator.ZIP,
      predicate=None):

    fd_path = os.path.join(self.temp_dir, "archive")
    generator = archive_generator.CollectionArchiveGenerator(
        archive_format=archive_format,
        predicate=predicate,
        prefix="test_prefix",
        description="Test description",
        client_id=self.client_id)
    with open(fd_path, "wb") as out_fd:
      for chunk in generator.Generate(collection):
        out_fd.write(chunk)

    return fd_path

  def testCreatesZipContainingFilesAndClientInfosAndManifest(self):
    self._InitializeFiles()

    fd_path = self._GenerateArchive(
        self.stat_entries,
        archive_format=archive_generator.CollectionArchiveGenerator.ZIP)

    zip_fd = zipfile.ZipFile(fd_path)
    names = [str(s) for s in sorted(zip_fd.namelist())]

    client_info_name = ("test_prefix/%s/client_info.yaml" % self.client_id)
    manifest_name = "test_prefix/MANIFEST"

    self.assertCountEqual(
        names, self.archive_paths + [client_info_name, manifest_name])

    contents = zip_fd.read(self.archive_paths[0])
    self.assertEqual(contents, b"hello1")

    contents = zip_fd.read(self.archive_paths[1])
    self.assertEqual(contents, b"hello2")

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
    self._InitializeFiles()

    fd_path = self._GenerateArchive(
        self.stat_entries,
        archive_format=archive_generator.CollectionArchiveGenerator.TAR_GZ)

    with tarfile.open(fd_path, encoding="utf-8") as tar_fd:
      manifest_fd = tar_fd.extractfile("test_prefix/MANIFEST")
      self.assertEqual(
          yaml.safe_load(manifest_fd.read()), {
              "description": "Test description",
              "processed_files": 2,
              "archived_files": 2,
              "ignored_files": 0,
              "failed_files": 0
          })

      archive_path_0 = self.archive_paths[0]
      archive_path_1 = self.archive_paths[1]

      # TODO: In Python 2, `extractfile` expects bytestrings. Once
      # support for Python 2 is dropped, this can be removed.
      if compatibility.PY2:
        archive_path_0 = archive_path_0.encode("utf-8")
        archive_path_1 = archive_path_1.encode("utf-8")

      self.assertEqual(tar_fd.extractfile(archive_path_0).read(), b"hello1")
      self.assertEqual(tar_fd.extractfile(archive_path_1).read(), b"hello2")

      client_info_name = ("test_prefix/%s/client_info.yaml" % self.client_id)
      client_info = yaml.safe_load(tar_fd.extractfile(client_info_name).read())

      try:
        self.assertEqual(client_info["knowledge_base"]["fqdn"],
                         "Host-0.example.com")
      except KeyError:  # AFF4
        self.assertEqual(client_info["system_info"]["fqdn"],
                         "Host-0.example.com")

  def testCorrectlyAccountsForFailedFiles(self):
    self._InitializeFiles()

    with mock.patch.object(
        file_store, "StreamFilesChunks", side_effect=Exception("foobar")):
      with self.assertRaises(Exception) as context:
        self._GenerateArchive(
            self.stat_entries,
            archive_format=archive_generator.CollectionArchiveGenerator.ZIP)
      self.assertEqual(str(context.exception), "foobar")

  def testNotFoundFilesProduceWarning(self):
    self._InitializeFiles()

    stat_entries = list(self.stat_entries)
    stat_entries.append(
        rdf_client_fs.StatEntry(
            pathspec=rdf_paths.PathSpec(
                path="foo/bar/notfound",
                pathtype=rdf_paths.PathSpec.PathType.OS)))

    fd_path = self._GenerateArchive(
        stat_entries,
        archive_format=archive_generator.CollectionArchiveGenerator.ZIP)

    zip_fd = zipfile.ZipFile(fd_path)
    yaml_str = zip_fd.read("test_prefix/MANIFEST")
    manifest = yaml.safe_load(yaml_str)
    self.assertEqual(
        manifest, {
            "description": "Test description",
            "processed_files": 3,
            "archived_files": 2,
            "ignored_files": 0,
            "failed_files": 0,
        })
    self.assertIn(
        archive_generator.CollectionArchiveGenerator.FILES_SKIPPED_WARNING,
        yaml_str)

  def testIgnoresFilesNotMatchingPredicate(self):
    self._InitializeFiles()

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
            "ignored_files_list":
                ["aff4:/%s/fs/os/foo/bar/中国新闻网新闻中.txt" % self.client_id]
        })


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
