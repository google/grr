#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Contains tests for api_call_handler_utils."""



import hashlib
import os
import tarfile
import zipfile


import yaml

from grr.gui import api_call_handler_utils

from grr.lib import aff4
from grr.lib import flags
from grr.lib import test_lib
from grr.lib.aff4_objects import collects
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import crypto as rdf_crypto
from grr.lib.rdfvalues import paths as rdf_paths


class CollectionArchiveGeneratorTest(test_lib.GRRBaseTest):
  """Test for CollectionArchiveGenerator."""

  def setUp(self):
    super(CollectionArchiveGeneratorTest, self).setUp()

    path1 = "aff4:/C.0000000000000000/fs/os/foo/bar/hello1.txt"
    with aff4.FACTORY.Create(path1,
                             aff4.AFF4MemoryStream,
                             token=self.token) as fd:
      fd.Write("hello1")
      fd.Set(fd.Schema.HASH,
             rdf_crypto.Hash(sha256=hashlib.sha256("hello1").digest()))

    path2 = u"aff4:/C.0000000000000000/fs/os/foo/bar/中国新闻网新闻中.txt"
    with aff4.FACTORY.Create(path2,
                             aff4.AFF4MemoryStream,
                             token=self.token) as fd:
      fd.Write("hello2")
      fd.Set(fd.Schema.HASH,
             rdf_crypto.Hash(sha256=hashlib.sha256("hello2").digest()))

    self.stat_entries = []
    self.paths = [path1, path2]
    for path in self.paths:
      self.stat_entries.append(rdf_client.StatEntry(
          aff4path=path,
          pathspec=rdf_paths.PathSpec(path="fs/os/foo/bar/" + path.split("/")[
              -1], pathtype=rdf_paths.PathSpec.PathType.OS)))

    self.fd = None

  def _GenerateArchive(
      self,
      collection,
      archive_format=api_call_handler_utils.CollectionArchiveGenerator.ZIP):

    self.fd_path = os.path.join(self.temp_dir, "archive")

    archive_generator = api_call_handler_utils.CollectionArchiveGenerator(
        archive_format=archive_format,
        prefix="test_prefix",
        description="Test description")
    with open(self.fd_path, "w") as out_fd:
      for chunk in archive_generator.Generate(collection, token=self.token):
        out_fd.write(chunk)

    self.fd = open(self.fd_path, "r")
    return self.fd, self.fd_path

  def tearDown(self):
    if self.fd:
      self.fd.close()

    super(CollectionArchiveGeneratorTest, self).tearDown()

  def testSkipsFilesWithoutHashWhenZipArchiving(self):
    for path in self.paths:
      with aff4.FACTORY.Open(path, mode="rw", token=self.token) as fd:
        fd.DeleteAttribute(fd.Schema.HASH)

    _, fd_path = self._GenerateArchive(
        self.stat_entries,
        archive_format=api_call_handler_utils.CollectionArchiveGenerator.ZIP)

    with zipfile.ZipFile(fd_path) as zip_fd:
      names = zip_fd.namelist()

      # Check that nothing was written except for the MANIFEST file.
      self.assertEqual(len(names), 1)
      self.assertEqual(names[0], "test_prefix/MANIFEST")

  def testSkipsFilesWithoutHashWhenTarArchiving(self):
    for path in self.paths:
      with aff4.FACTORY.Open(path, mode="rw", token=self.token) as fd:
        fd.DeleteAttribute(fd.Schema.HASH)

    _, fd_path = self._GenerateArchive(
        self.stat_entries,
        archive_format=api_call_handler_utils.CollectionArchiveGenerator.TAR_GZ)

    with tarfile.open(fd_path) as tar_fd:
      infos = list(tar_fd)

      # Check that nothing was written except for the MANIFEST file.
      self.assertEqual(len(infos), 1)
      self.assertEqual(infos[0].name, "test_prefix/MANIFEST")

  def testCreatesZipContainingDeduplicatedCollectionFilesAndManifest(self):
    _, fd_path = self._GenerateArchive(
        self.stat_entries,
        archive_format=api_call_handler_utils.CollectionArchiveGenerator.ZIP)

    zip_fd = zipfile.ZipFile(fd_path)
    names = sorted(zip_fd.namelist())

    link1_name = "test_prefix/C.0000000000000000/fs/os/foo/bar/hello1.txt"
    link2_name = ("test_prefix/C.0000000000000000/fs/os/foo/bar/"
                  "中国新闻网新闻中.txt")
    link1_dest = ("test_prefix/hashes/91e9240f415223982edc345532630710"
                  "e94a7f52cd5f48f5ee1afc555078f0ab")
    link2_dest = ("test_prefix/hashes/87298cc2f31fba73181ea2a9e6ef10dc"
                  "e21ed95e98bdac9c4e1504ea16f486e4")
    manifest_name = "test_prefix/MANIFEST"

    self.assertEqual(
        names,
        sorted([link1_name, link2_name, link1_dest, link2_dest, manifest_name]))

    link_info = zip_fd.getinfo(link1_name)
    self.assertEqual(link_info.external_attr, (0644 | 0120000) << 16)
    self.assertEqual(link_info.create_system, 3)

    link_contents = zip_fd.read(link1_name)
    self.assertEqual(link_contents, "../../../../../../" + link1_dest)

    dest_contents = zip_fd.read(link1_dest)
    self.assertEqual(dest_contents, "hello1")

    link_info = zip_fd.getinfo(link2_name)
    self.assertEqual(link_info.external_attr, (0644 | 0120000) << 16)
    self.assertEqual(link_info.create_system, 3)

    link_contents = zip_fd.read(link2_name)
    self.assertEqual(link_contents, "../../../../../../" + link2_dest)

    dest_contents = zip_fd.read(link2_dest)
    self.assertEqual(dest_contents, "hello2")

    manifest = yaml.safe_load(zip_fd.read(manifest_name))
    self.assertEqual(manifest, {
        "description": "Test description",
        "processed_files": 2,
        "archived_files": 2,
        "skipped_files": 0,
        "failed_files": 0
    })

  def testCreatesTarContainingDeduplicatedCollectionFilesAndReadme(self):
    _, fd_path = self._GenerateArchive(
        self.stat_entries,
        archive_format=api_call_handler_utils.CollectionArchiveGenerator.TAR_GZ)

    with tarfile.open(fd_path) as tar_fd:
      link1_name = "test_prefix/C.0000000000000000/fs/os/foo/bar/hello1.txt"
      link2_name = ("test_prefix/C.0000000000000000/fs/os/foo/bar/"
                    "中国新闻网新闻中.txt")
      link1_dest = ("test_prefix/hashes/91e9240f415223982edc345532630710"
                    "e94a7f52cd5f48f5ee1afc555078f0ab")
      link2_dest = ("test_prefix/hashes/87298cc2f31fba73181ea2a9e6ef10dc"
                    "e21ed95e98bdac9c4e1504ea16f486e4")

      link_info = tar_fd.getmember(link1_name)
      self.assertEqual(link_info.linkname, "../../../../../../" + link1_dest)
      self.assertEqual(tar_fd.extractfile(link1_dest).read(), "hello1")

      link_info = tar_fd.getmember(link2_name)
      self.assertEqual(link_info.linkname, "../../../../../../" + link2_dest)
      self.assertEqual(tar_fd.extractfile(link2_dest).read(), "hello2")

      manifest_fd = tar_fd.extractfile("test_prefix/MANIFEST")
      self.assertEqual(
          yaml.safe_load(manifest_fd.read()), {
              "description": "Test description",
              "processed_files": 2,
              "archived_files": 2,
              "skipped_files": 0,
              "failed_files": 0
          })

  def testCorrectlyAccountsForFailedFiles(self):
    path2 = u"aff4:/C.0000000000000000/fs/os/foo/bar/中国新闻网新闻中.txt"
    with aff4.FACTORY.Create(path2, aff4.AFF4Image, token=self.token) as fd:
      fd.Write("hello2")

    # Delete a single chunk
    aff4.FACTORY.Delete("aff4:/C.0000000000000000/fs/os/foo/bar/中国新闻网新闻中.txt"
                        "/0000000000",
                        token=self.token)

    _, fd_path = self._GenerateArchive(
        self.stat_entries,
        archive_format=api_call_handler_utils.CollectionArchiveGenerator.ZIP)

    zip_fd = zipfile.ZipFile(fd_path)
    names = sorted(zip_fd.namelist())

    link1_name = "test_prefix/C.0000000000000000/fs/os/foo/bar/hello1.txt"
    link2_name = ("test_prefix/C.0000000000000000/fs/os/foo/bar/"
                  "中国新闻网新闻中.txt")
    link1_dest = ("test_prefix/hashes/91e9240f415223982edc345532630710"
                  "e94a7f52cd5f48f5ee1afc555078f0ab")
    manifest_name = "test_prefix/MANIFEST"

    # Link 2 should be present, but the contents should be missing.
    self.assertEqual(
        names, sorted([link1_name, link1_dest, link2_name, manifest_name]))

    link_info = zip_fd.getinfo(link1_name)
    self.assertEqual(link_info.external_attr, (0644 | 0120000) << 16)
    self.assertEqual(link_info.create_system, 3)

    link_contents = zip_fd.read(link1_name)
    self.assertEqual(link_contents, "../../../../../../" + link1_dest)

    dest_contents = zip_fd.read(link1_dest)
    self.assertEqual(dest_contents, "hello1")

    manifest = yaml.safe_load(zip_fd.read(manifest_name))
    self.assertEqual(manifest, {
        "description": "Test description",
        "processed_files": 2,
        "archived_files": 1,
        "skipped_files": 0,
        "failed_files": 1,
        "failed_files_list": [
            u"aff4:/C.0000000000000000/fs/os/foo/bar/中国新闻网新闻中.txt"
        ]
    })


class FilterAff4CollectionTest(test_lib.GRRBaseTest):
  """Test for FilterAff4Collection."""

  def setUp(self):
    super(FilterAff4CollectionTest, self).setUp()

    with aff4.FACTORY.Create("aff4:/tmp/foo/bar",
                             collects.RDFValueCollection,
                             token=self.token) as fd:
      for i in range(10):
        fd.Add(rdf_paths.PathSpec(path="/var/os/tmp-%d" % i, pathtype="OS"))

    self.fd = aff4.FACTORY.Open("aff4:/tmp/foo/bar", token=self.token)

  def testFiltersByOffsetAndCount(self):
    data = api_call_handler_utils.FilterAff4Collection(self.fd, 2, 5, None)
    self.assertEqual(len(data), 5)
    self.assertEqual(data[0].path, "/var/os/tmp-2")
    self.assertEqual(data[-1].path, "/var/os/tmp-6")

  def testIngoresTooBigCount(self):
    data = api_call_handler_utils.FilterAff4Collection(self.fd, 0, 50, None)
    self.assertEqual(len(data), 10)
    self.assertEqual(data[0].path, "/var/os/tmp-0")
    self.assertEqual(data[-1].path, "/var/os/tmp-9")

  def testRaisesOnNegativeOffset(self):
    with self.assertRaises(ValueError):
      api_call_handler_utils.FilterAff4Collection(self.fd, -10, 0, None)

  def testRaisesOnNegativeCount(self):
    with self.assertRaises(ValueError):
      api_call_handler_utils.FilterAff4Collection(self.fd, 0, -10, None)

  def testFiltersByFilterString(self):
    data = api_call_handler_utils.FilterAff4Collection(self.fd, 0, 0, "tmp-8")
    self.assertEqual(len(data), 1)
    self.assertEqual(data[0].path, "/var/os/tmp-8")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
