#!/usr/bin/env python
"""Contains tests for archive_generator."""

import hashlib
import os
import tarfile
from unittest import mock
import zipfile

from absl import app

import yaml

from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server import flow_base
from grr_response_server.databases import db
from grr_response_server.gui import archive_generator
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib


class CollectionArchiveGeneratorTest(test_lib.GRRBaseTest):
  """Test for CollectionArchiveGenerator."""

  def setUp(self):
    super().setUp()
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


class FlowArchiveGeneratorTest(test_lib.GRRBaseTest):
  """Test for CollectionArchiveGenerator."""

  def _GenerateArchive(self, generator):
    fd_path = os.path.join(self.temp_dir, "archive")
    with open(fd_path, "wb") as out_fd:
      for chunk in generator:
        out_fd.write(chunk)

    return fd_path

  def setUp(self):
    super().setUp()

    self.client_id = self.SetupClient(0)
    self.flow_id = flow_test_lib.StartFlow(
        flow_test_lib.DummyFlow, client_id=self.client_id)
    self.flow = data_store.REL_DB.ReadFlowObject(self.client_id, self.flow_id)

    self.path1 = db.ClientPath.OS(self.client_id, ["foo", "bar", "hello1.txt"])
    self.path1_content = "hello1".encode("utf-8")
    self.path2 = db.ClientPath.TSK(
        self.client_id, ["foo", "bar", "中国新闻网新闻中.txt"])
    self.path2_content = "hello2".encode("utf-8")

    vfs_test_lib.CreateFile(self.path1, self.path1_content)
    vfs_test_lib.CreateFile(self.path2, self.path2_content)

  def testCreatesZipContainingTwoMappedFilesAndManifest(self):
    generator = archive_generator.FlowArchiveGenerator(
        self.flow, archive_generator.ArchiveFormat.ZIP)
    mappings = [
        flow_base.ClientPathArchiveMapping(self.path1, "foo/file"),
        flow_base.ClientPathArchiveMapping(self.path2, "foo/bar/file"),
    ]
    fd_path = self._GenerateArchive(generator.Generate(mappings))

    zip_fd = zipfile.ZipFile(fd_path)
    names = [str(s) for s in sorted(zip_fd.namelist())]

    # Expecting in the archive: 2 files and a manifest.
    self.assertLen(names, 3)

    contents = zip_fd.read(os.path.join(generator.prefix, "foo", "file"))
    self.assertEqual(contents, b"hello1")

    contents = zip_fd.read(os.path.join(generator.prefix, "foo", "bar", "file"))
    self.assertEqual(contents, b"hello2")

    manifest = yaml.safe_load(
        zip_fd.read(os.path.join(generator.prefix, "MANIFEST")))
    self.assertCountEqual(manifest["processed_files"].items(),
                          [(self.path1.vfs_path, "foo/file"),
                           (self.path2.vfs_path, "foo/bar/file")])
    self.assertCountEqual(manifest["missing_files"], [])
    self.assertEqual(manifest["client_id"], self.client_id)
    self.assertEqual(manifest["flow_id"], self.flow_id)

  def testCreatesTarContainingTwoMappedFilesAndManifest(self):
    generator = archive_generator.FlowArchiveGenerator(
        self.flow, archive_generator.ArchiveFormat.TAR_GZ)
    mappings = [
        flow_base.ClientPathArchiveMapping(self.path1, "foo/file"),
        flow_base.ClientPathArchiveMapping(self.path2, "foo/bar/file"),
    ]
    fd_path = self._GenerateArchive(generator.Generate(mappings))

    with tarfile.open(fd_path, encoding="utf-8") as tar_fd:
      self.assertLen(tar_fd.getnames(), 3)

      contents = tar_fd.extractfile(
          os.path.join(generator.prefix, "foo", "file")).read()
      self.assertEqual(contents, b"hello1")

      contents = tar_fd.extractfile(
          os.path.join(generator.prefix, "foo", "bar", "file")).read()
      self.assertEqual(contents, b"hello2")

      manifest = yaml.safe_load(
          tar_fd.extractfile(os.path.join(generator.prefix, "MANIFEST")).read())
      self.assertCountEqual(manifest["processed_files"].items(),
                            [(self.path1.vfs_path, "foo/file"),
                             (self.path2.vfs_path, "foo/bar/file")])
      self.assertCountEqual(manifest["missing_files"], [])
      self.assertEqual(manifest["client_id"], self.client_id)
      self.assertEqual(manifest["flow_id"], self.flow_id)

  def testPropagatesStreamingExceptions(self):
    generator = archive_generator.FlowArchiveGenerator(
        self.flow, archive_generator.ArchiveFormat.TAR_GZ)
    mappings = [
        flow_base.ClientPathArchiveMapping(self.path1, "foo/file"),
        flow_base.ClientPathArchiveMapping(self.path2, "foo/bar/file"),
    ]

    with mock.patch.object(
        file_store, "StreamFilesChunks", side_effect=Exception("foobar")):
      with self.assertRaises(Exception) as context:
        self._GenerateArchive(generator.Generate(mappings))
      self.assertEqual(str(context.exception), "foobar")

  def testMissingFilesAreListedInManifest(self):
    generator = archive_generator.FlowArchiveGenerator(
        self.flow, archive_generator.ArchiveFormat.ZIP)
    mappings = [
        flow_base.ClientPathArchiveMapping(self.path1, "foo/file"),
        flow_base.ClientPathArchiveMapping(
            db.ClientPath.OS(self.client_id, ["non", "existing"]),
            "foo/bar/file"),
    ]
    fd_path = self._GenerateArchive(generator.Generate(mappings))

    zip_fd = zipfile.ZipFile(fd_path)
    names = [str(s) for s in sorted(zip_fd.namelist())]

    # Expecting in the archive: 1 file (the other shouldn't be found)
    # and a manifest.
    self.assertLen(names, 2)

    contents = zip_fd.read(os.path.join(generator.prefix, "foo", "file"))
    self.assertEqual(contents, b"hello1")

    manifest = yaml.safe_load(
        zip_fd.read(os.path.join(generator.prefix, "MANIFEST")))
    self.assertCountEqual(manifest["processed_files"].items(),
                          [(self.path1.vfs_path, "foo/file")])
    self.assertCountEqual(manifest["missing_files"], ["fs/os/non/existing"])


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
