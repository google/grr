#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Contains tests for api_call_handler_utils."""

import hashlib
import os
import tarfile
import zipfile


import yaml

from grr.lib import flags

from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import crypto as rdf_crypto
from grr.lib.rdfvalues import paths as rdf_paths
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import data_store
from grr.server.grr_response_server import sequential_collection
from grr.server.grr_response_server.gui import api_call_handler_utils
from grr.server.grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import db_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class CollectionArchiveGeneratorTest(test_lib.GRRBaseTest):
  """Test for CollectionArchiveGenerator."""

  def setUp(self):
    super(CollectionArchiveGeneratorTest, self).setUp()
    self.client_id = self.SetupClient(0)

  def _CreateFile(self, path, content, hashing=False):
    with aff4.FACTORY.Create(
        path, aff4.AFF4MemoryStream, token=self.token) as fd:
      fd.Write(content)

      if hashing:
        digest = hashlib.sha256(content).digest()
        fd.Set(fd.Schema.HASH, rdf_crypto.Hash(sha256=digest))

        if data_store.RelationalDBWriteEnabled():
          client_id, vfs_path = path.Split(2)
          path_type, components = rdf_objects.ParseCategorizedPath(vfs_path)

          path_info = rdf_objects.PathInfo()
          path_info.path_type = path_type
          path_info.components = components
          path_info.hash_entry.sha256 = digest
          data_store.REL_DB.WritePathInfos(client_id, [path_info])

  def _InitializeFiles(self, hashing=False):
    path1 = self.client_id.Add("fs/os/foo/bar/hello1.txt")
    archive_path1 = (
        u"test_prefix/%s/fs/os/foo/bar/hello1.txt" % self.client_id.Basename())
    self._CreateFile(path=path1, content="hello1", hashing=hashing)

    path2 = self.client_id.Add(u"fs/os/foo/bar/中国新闻网新闻中.txt")
    archive_path2 = (u"test_prefix/%s/fs/os/foo/bar/"
                     u"中国新闻网新闻中.txt") % self.client_id.Basename()
    self._CreateFile(path=path2, content="hello2", hashing=hashing)

    self.stat_entries = []
    self.paths = [path1, path2]
    self.archive_paths = [archive_path1, archive_path2]
    for path in self.paths:
      self.stat_entries.append(
          rdf_client.StatEntry(
              pathspec=rdf_paths.PathSpec(
                  path="foo/bar/" + str(path).split("/")[-1],
                  pathtype=rdf_paths.PathSpec.PathType.OS)))

  def _GenerateArchive(
      self,
      collection,
      archive_format=api_call_handler_utils.CollectionArchiveGenerator.ZIP,
      predicate=None):

    fd_path = os.path.join(self.temp_dir, "archive")
    archive_generator = api_call_handler_utils.CollectionArchiveGenerator(
        archive_format=archive_format,
        predicate=predicate,
        prefix="test_prefix",
        description="Test description",
        client_id=self.client_id)
    with open(fd_path, "wb") as out_fd:
      for chunk in archive_generator.Generate(collection, token=self.token):
        out_fd.write(chunk)

    return fd_path

  def testDoesNotSkipFilesWithoutHashWhenZipArchiving(self):
    self._InitializeFiles(hashing=False)

    fd_path = self._GenerateArchive(
        self.stat_entries,
        archive_format=api_call_handler_utils.CollectionArchiveGenerator.ZIP)

    with zipfile.ZipFile(fd_path) as zip_fd:
      names = [utils.SmartUnicode(s) for s in zip_fd.namelist()]

      # Check that both files are in the archive.
      for p in self.archive_paths:
        self.assertTrue(p in names)

  def testDoesNotSkipFilesWithoutHashWhenTarArchiving(self):
    self._InitializeFiles(hashing=False)

    fd_path = self._GenerateArchive(
        self.stat_entries,
        archive_format=api_call_handler_utils.CollectionArchiveGenerator.TAR_GZ)

    with tarfile.open(fd_path) as tar_fd:
      infos = list(tar_fd)

      # Check that both files are in the archive.
      names = [utils.SmartUnicode(i.name) for i in infos]
      for p in self.archive_paths:
        self.assertTrue(p in names)

  def testCreatesZipContainingFilesAndClientInfosAndManifest(self):
    self._InitializeFiles(hashing=True)

    fd_path = self._GenerateArchive(
        self.stat_entries,
        archive_format=api_call_handler_utils.CollectionArchiveGenerator.ZIP)

    zip_fd = zipfile.ZipFile(fd_path)
    names = [utils.SmartUnicode(s) for s in sorted(zip_fd.namelist())]

    client_info_name = (
        u"test_prefix/%s/client_info.yaml" % self.client_id.Basename())
    manifest_name = u"test_prefix/MANIFEST"

    self.assertEqual(
        names, sorted(self.archive_paths + [client_info_name, manifest_name]))

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
    self.assertEqual(client_info["system_info"]["fqdn"], "Host-0.example.com")

  def testCreatesTarContainingFilesAndClientInfosAndManifest(self):
    self._InitializeFiles(hashing=True)

    fd_path = self._GenerateArchive(
        self.stat_entries,
        archive_format=api_call_handler_utils.CollectionArchiveGenerator.TAR_GZ)

    with tarfile.open(fd_path) as tar_fd:
      self.assertEqual(
          tar_fd.extractfile(utils.SmartStr(self.archive_paths[0])).read(),
          "hello1")
      self.assertEqual(
          tar_fd.extractfile(utils.SmartStr(self.archive_paths[1])).read(),
          "hello2")

      manifest_fd = tar_fd.extractfile("test_prefix/MANIFEST")
      self.assertEqual(
          yaml.safe_load(manifest_fd.read()), {
              "description": "Test description",
              "processed_files": 2,
              "archived_files": 2,
              "ignored_files": 0,
              "failed_files": 0
          })

      client_info_name = (
          "test_prefix/%s/client_info.yaml" % self.client_id.Basename())
      client_info = yaml.safe_load(tar_fd.extractfile(client_info_name).read())
      self.assertEqual(client_info["system_info"]["fqdn"], "Host-0.example.com")

  def testCorrectlyAccountsForFailedFiles(self):
    self._InitializeFiles(hashing=True)

    path2 = (u"aff4:/%s/fs/os/foo/bar/中国新闻网新闻中.txt" % self.client_id.Basename())
    with aff4.FACTORY.Create(path2, aff4.AFF4Image, token=self.token) as fd:
      fd.Write("hello2")

    # Delete a single chunk
    aff4.FACTORY.Delete(
        utils.SmartStr("aff4:/%s/fs/os/foo/bar/中国新闻网新闻中.txt/0000000000") %
        utils.SmartStr(self.client_id.Basename()),
        token=self.token)

    fd_path = self._GenerateArchive(
        self.stat_entries,
        archive_format=api_call_handler_utils.CollectionArchiveGenerator.ZIP)

    zip_fd = zipfile.ZipFile(fd_path)
    names = [utils.SmartUnicode(s) for s in sorted(zip_fd.namelist())]
    self.assertTrue(self.archive_paths[0] in names)
    self.assertTrue(self.archive_paths[1] not in names)

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
                u"aff4:/%s/fs/os/foo/bar/中国新闻网新闻中.txt" %
                self.client_id.Basename()
            ]
        })

  def testIgnoresFilesNotMatchingPredicate(self):
    self._InitializeFiles(hashing=True)

    fd_path = self._GenerateArchive(
        self.stat_entries,
        predicate=lambda fd: fd.urn.Basename().startswith("hello"),
        archive_format=api_call_handler_utils.CollectionArchiveGenerator.ZIP)

    zip_fd = zipfile.ZipFile(fd_path)
    names = sorted(zip_fd.namelist())

    # The archive is expected to contain 1 file contents blob, 1 client info and
    # a manifest.
    self.assertEqual(len(names), 3)

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
                u"aff4:/%s/fs/os/foo/bar/中国新闻网新闻中.txt" %
                self.client_id.Basename()
            ]
        })


class FilterCollectionTest(test_lib.GRRBaseTest):
  """Test for FilterCollection."""

  def setUp(self):
    super(FilterCollectionTest, self).setUp()

    self.fd = sequential_collection.GeneralIndexedCollection(
        rdfvalue.RDFURN("aff4:/tmp/foo/bar"))
    with data_store.DB.GetMutationPool() as pool:
      for i in range(10):
        self.fd.Add(
            rdf_paths.PathSpec(path="/var/os/tmp-%d" % i, pathtype="OS"),
            mutation_pool=pool)

  def testFiltersByOffsetAndCount(self):
    data = api_call_handler_utils.FilterCollection(self.fd, 2, 5, None)
    self.assertEqual(len(data), 5)
    self.assertEqual(data[0].path, "/var/os/tmp-2")
    self.assertEqual(data[-1].path, "/var/os/tmp-6")

  def testIngoresTooBigCount(self):
    data = api_call_handler_utils.FilterCollection(self.fd, 0, 50, None)
    self.assertEqual(len(data), 10)
    self.assertEqual(data[0].path, "/var/os/tmp-0")
    self.assertEqual(data[-1].path, "/var/os/tmp-9")

  def testRaisesOnNegativeOffset(self):
    with self.assertRaises(ValueError):
      api_call_handler_utils.FilterCollection(self.fd, -10, 0, None)

  def testRaisesOnNegativeCount(self):
    with self.assertRaises(ValueError):
      api_call_handler_utils.FilterCollection(self.fd, 0, -10, None)

  def testFiltersByFilterString(self):
    data = api_call_handler_utils.FilterCollection(self.fd, 0, 0, "tmp-8")
    self.assertEqual(len(data), 1)
    self.assertEqual(data[0].path, "/var/os/tmp-8")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
