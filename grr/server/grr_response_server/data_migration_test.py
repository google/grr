#!/usr/bin/env python
from grr.core.grr_response_core.lib import flags
from grr.core.grr_response_core.lib import rdfvalue
from grr.core.grr_response_core.lib.rdfvalues import client as rdf_client
from grr.core.grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import data_migration
from grr.server.grr_response_server import data_store
from grr.server.grr_response_server.aff4_objects import aff4_grr
from grr.server.grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import test_lib


class ListVfsTest(test_lib.GRRBaseTest):

  def _Touch(self, urn, content=""):
    with aff4.FACTORY.Open(
        urn, aff4_type=aff4_grr.VFSFile, mode="w", token=self.token) as fd:
      fd.Write(content)

  def testTree(self):
    client_urn = self.SetupClient(0)

    self._Touch(client_urn.Add("fs/os").Add("foo/bar/baz"), content="aaa")
    self._Touch(client_urn.Add("fs/os").Add("foo/quux/norf"), content="bbb")

    vfs = data_migration.ListVfs(client_urn)
    self.assertIn(client_urn.Add("fs/os").Add("foo"), vfs)
    self.assertIn(client_urn.Add("fs/os").Add("foo/bar"), vfs)
    self.assertIn(client_urn.Add("fs/os").Add("foo/bar/baz"), vfs)
    self.assertIn(client_urn.Add("fs/os").Add("foo/quux"), vfs)
    self.assertIn(client_urn.Add("fs/os").Add("foo/quux/norf"), vfs)

  def testVariousRoots(self):
    client_urn = self.SetupClient(0)

    self._Touch(client_urn.Add("fs/os").Add("foo"), content="foo")
    self._Touch(client_urn.Add("fs/tsk").Add("bar"), content="bar")
    self._Touch(client_urn.Add("temp").Add("foo"), content="foo")
    self._Touch(client_urn.Add("registry").Add("bar"), content="bar")

    vfs = data_migration.ListVfs(client_urn)
    self.assertIn(client_urn.Add("fs/os").Add("foo"), vfs)
    self.assertIn(client_urn.Add("fs/tsk").Add("bar"), vfs)
    self.assertIn(client_urn.Add("temp").Add("foo"), vfs)
    self.assertIn(client_urn.Add("registry").Add("bar"), vfs)


class VfsMigrationTest(test_lib.GRRBaseTest):

  def _Aff4Open(self, urn):
    return aff4.FACTORY.Open(
        urn, aff4_type=aff4_grr.VFSFile, mode="w", token=self.token)

  def testStatEntryFromSimpleFile(self):
    client_urn = self.SetupClient(0)

    with self._Aff4Open(client_urn.Add("fs/os").Add("foo")) as fd:
      stat_entry = rdf_client.StatEntry(st_mode=1337, st_size=42)
      fd.Set(fd.Schema.STAT, stat_entry)

    data_migration.MigrateClientVfs(client_urn)

    path_info = data_store.REL_DB.FindPathInfoByPathID(
        client_id=client_urn.Basename(),
        path_type=rdf_objects.PathInfo.PathType.OS,
        path_id=rdf_objects.PathID.FromComponents(["foo"]))
    self.assertEqual(path_info.stat_entry.st_mode, 1337)
    self.assertEqual(path_info.stat_entry.st_size, 42)

  def testHashEntryFromSimpleFile(self):
    client_urn = self.SetupClient(0)

    with self._Aff4Open(client_urn.Add("fs/os").Add("foo")) as fd:
      hash_entry = rdf_crypto.Hash(md5=b"bar", sha256=b"baz")
      fd.Set(fd.Schema.HASH, hash_entry)

    data_migration.MigrateClientVfs(client_urn)

    path_info = data_store.REL_DB.FindPathInfoByPathID(
        client_id=client_urn.Basename(),
        path_type=rdf_objects.PathInfo.PathType.OS,
        path_id=rdf_objects.PathID.FromComponents(["foo"]))
    self.assertEqual(path_info.hash_entry.md5, b"bar")
    self.assertEqual(path_info.hash_entry.sha256, b"baz")

  def testStatAndHashEntryFromSimpleFile(self):
    client_urn = self.SetupClient(0)

    with self._Aff4Open(client_urn.Add("fs/os").Add("foo")) as fd:
      stat_entry = rdf_client.StatEntry(st_mode=108)
      fd.Set(fd.Schema.STAT, stat_entry)

      hash_entry = rdf_crypto.Hash(sha256=b"quux")
      fd.Set(fd.Schema.HASH, hash_entry)

    data_migration.MigrateClientVfs(client_urn)

    path_info = data_store.REL_DB.FindPathInfoByPathID(
        client_id=client_urn.Basename(),
        path_type=rdf_objects.PathInfo.PathType.OS,
        path_id=rdf_objects.PathID.FromComponents(["foo"]))
    self.assertEqual(path_info.stat_entry.st_mode, 108)
    self.assertEqual(path_info.hash_entry.sha256, b"quux")

  def testStatFromTree(self):
    client_urn = self.SetupClient(0)

    with self._Aff4Open(client_urn.Add("fs/os").Add("foo/bar/baz")) as fd:
      stat_entry = rdf_client.StatEntry(st_mtime=101)
      fd.Set(fd.Schema.STAT, stat_entry)

    data_migration.MigrateClientVfs(client_urn)

    foo_path_id = rdf_objects.PathID.FromComponents(["foo"])
    foo_bar_path_id = rdf_objects.PathID.FromComponents(["foo", "bar"])
    foo_bar_baz_path_id = rdf_objects.PathID.FromComponents(
        ["foo", "bar", "baz"])

    path_infos = data_store.REL_DB.FindPathInfosByPathIDs(
        client_id=client_urn.Basename(),
        path_type=rdf_objects.PathInfo.PathType.OS,
        path_ids=[foo_path_id, foo_bar_path_id, foo_bar_baz_path_id])

    self.assertEqual(path_infos[foo_path_id].stat_entry.st_mtime, None)
    self.assertEqual(path_infos[foo_bar_path_id].stat_entry.st_mtime, None)
    self.assertEqual(path_infos[foo_bar_baz_path_id].stat_entry.st_mtime, 101)

  def testStatHistory(self):
    datetime = rdfvalue.RDFDatetime.FromHumanReadable

    client_urn = self.SetupClient(0)
    file_urn = client_urn.Add("fs/os").Add("foo")

    with test_lib.FakeTime(datetime("2000-01-01")):
      with self._Aff4Open(file_urn) as fd:
        fd.Set(fd.Schema.STAT, rdf_client.StatEntry(st_size=10))

    with test_lib.FakeTime(datetime("2000-02-02")):
      with self._Aff4Open(file_urn) as fd:
        fd.Set(fd.Schema.STAT, rdf_client.StatEntry(st_size=20))

    with test_lib.FakeTime(datetime("2000-03-03")):
      with self._Aff4Open(file_urn) as fd:
        fd.Set(fd.Schema.STAT, rdf_client.StatEntry(st_size=30))

    data_migration.MigrateClientVfs(client_urn)

    path_info = data_store.REL_DB.FindPathInfoByPathID(
        client_id=client_urn.Basename(),
        path_type=rdf_objects.PathInfo.PathType.OS,
        path_id=rdf_objects.PathID.FromComponents(["foo"]),
        timestamp=datetime("2000-01-10"))
    self.assertEqual(path_info.stat_entry.st_size, 10)

    path_info = data_store.REL_DB.FindPathInfoByPathID(
        client_id=client_urn.Basename(),
        path_type=rdf_objects.PathInfo.PathType.OS,
        path_id=rdf_objects.PathID.FromComponents(["foo"]),
        timestamp=datetime("2000-02-20"))
    self.assertEqual(path_info.stat_entry.st_size, 20)

    path_info = data_store.REL_DB.FindPathInfoByPathID(
        client_id=client_urn.Basename(),
        path_type=rdf_objects.PathInfo.PathType.OS,
        path_id=rdf_objects.PathID.FromComponents(["foo"]),
        timestamp=datetime("2000-03-30"))
    self.assertEqual(path_info.stat_entry.st_size, 30)

  def testHashHistory(self):
    datetime = rdfvalue.RDFDatetime.FromHumanReadable

    client_urn = self.SetupClient(0)
    file_urn = client_urn.Add("fs/os").Add("bar")

    with test_lib.FakeTime(datetime("2010-01-01")):
      with self._Aff4Open(file_urn) as fd:
        fd.Set(fd.Schema.HASH, rdf_crypto.Hash(md5=b"quux"))

    with test_lib.FakeTime(datetime("2020-01-01")):
      with self._Aff4Open(file_urn) as fd:
        fd.Set(fd.Schema.HASH, rdf_crypto.Hash(md5=b"norf"))

    with test_lib.FakeTime(datetime("2030-01-01")):
      with self._Aff4Open(file_urn) as fd:
        fd.Set(fd.Schema.HASH, rdf_crypto.Hash(md5=b"blargh"))

    data_migration.MigrateClientVfs(client_urn)

    path_info = data_store.REL_DB.FindPathInfoByPathID(
        client_id=client_urn.Basename(),
        path_type=rdf_objects.PathInfo.PathType.OS,
        path_id=rdf_objects.PathID.FromComponents(["bar"]),
        timestamp=datetime("2010-12-31"))
    self.assertEqual(path_info.hash_entry.md5, b"quux")

    path_info = data_store.REL_DB.FindPathInfoByPathID(
        client_id=client_urn.Basename(),
        path_type=rdf_objects.PathInfo.PathType.OS,
        path_id=rdf_objects.PathID.FromComponents(["bar"]),
        timestamp=datetime("2020-12-31"))
    self.assertEqual(path_info.hash_entry.md5, b"norf")

    path_info = data_store.REL_DB.FindPathInfoByPathID(
        client_id=client_urn.Basename(),
        path_type=rdf_objects.PathInfo.PathType.OS,
        path_id=rdf_objects.PathID.FromComponents(["bar"]),
        timestamp=datetime("2030-12-31"))
    self.assertEqual(path_info.hash_entry.md5, b"blargh")


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
