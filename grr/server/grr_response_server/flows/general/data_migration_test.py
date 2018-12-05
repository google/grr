#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server.aff4_objects import aff4_grr
from grr_response_server.flows.general import data_migration
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class ClientVfsMigrationTest(flow_test_lib.FlowTestsBaseclass):

  def _Aff4Open(self, urn):
    return aff4.FACTORY.Open(
        urn, aff4_type=aff4_grr.VFSFile, mode="w", token=self.token)

  def _RunFlow(self, client_urn):
    session_id = flow_test_lib.TestFlowHelper(
        data_migration.ClientVfsMigrationFlow.__name__,
        client_id=client_urn,
        token=self.token)

    return list(flow.GRRFlow.ResultCollectionForFID(session_id))

  def testMigratesStatEntries(self):
    client_urn = self.SetupClient(0)

    with self._Aff4Open(client_urn.Add("fs/os").Add("foo")) as filedesc:
      filedesc.Set(filedesc.Schema.STAT, rdf_client_fs.StatEntry(st_size=42))

    result = self._RunFlow(client_urn)
    self.assertEqual(result, [])

    path_info = data_store.REL_DB.ReadPathInfo(
        client_id=client_urn.Basename(),
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=("foo",))
    self.assertEqual(path_info.stat_entry.st_size, 42)

  def testMigrateHashEntries(self):
    client_urn = self.SetupClient(0)

    with self._Aff4Open(client_urn.Add("fs/os").Add("foo")) as filedesc:
      filedesc.Set(filedesc.Schema.HASH, rdf_crypto.Hash(md5=b"quux"))

    result = self._RunFlow(client_urn)
    self.assertEqual(result, [])

    path_info = data_store.REL_DB.ReadPathInfo(
        client_id=client_urn.Basename(),
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=("foo",))
    self.assertEqual(path_info.hash_entry.md5, b"quux")

  def testMigrateHistory(self):
    datetime = rdfvalue.RDFDatetime.FromHumanReadable

    client_urn = self.SetupClient(0)
    file_urn = client_urn.Add("fs/os").Add("foo")

    with test_lib.FakeTime(datetime("2009-09-09")):
      with self._Aff4Open(file_urn) as filedesc:
        filedesc.Set(filedesc.Schema.STAT, rdf_client_fs.StatEntry(st_size=108))

    with test_lib.FakeTime(datetime("2010-10-10")):
      with self._Aff4Open(file_urn) as filedesc:
        filedesc.Set(filedesc.Schema.STAT, rdf_client_fs.StatEntry(st_size=101))
        filedesc.Set(filedesc.Schema.HASH, rdf_crypto.Hash(sha256=b"quux"))

    with test_lib.FakeTime(datetime("2011-11-11")):
      with self._Aff4Open(file_urn) as filedesc:
        filedesc.Set(filedesc.Schema.HASH, rdf_crypto.Hash(md5=b"norf"))

    with test_lib.FakeTime(datetime("2012-12-12")):
      with self._Aff4Open(file_urn) as filedesc:
        filedesc.Set(filedesc.Schema.STAT, rdf_client_fs.StatEntry(st_size=42))
        filedesc.Set(filedesc.Schema.HASH, rdf_crypto.Hash(md5=b"thud"))

    result = self._RunFlow(client_urn)
    self.assertEqual(result, [])

    path_info = data_store.REL_DB.ReadPathInfo(
        client_id=client_urn.Basename(),
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=("foo",),
        timestamp=datetime("2009-09-09"))
    self.assertEqual(path_info.stat_entry.st_size, 108)
    self.assertFalse(path_info.hash_entry.sha256)

    path_info = data_store.REL_DB.ReadPathInfo(
        client_id=client_urn.Basename(),
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=("foo",),
        timestamp=datetime("2010-10-10"))
    self.assertEqual(path_info.stat_entry.st_size, 101)
    self.assertEqual(path_info.hash_entry.sha256, b"quux")

    path_info = data_store.REL_DB.ReadPathInfo(
        client_id=client_urn.Basename(),
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=("foo",),
        timestamp=datetime("2011-11-11"))
    self.assertEqual(path_info.stat_entry.st_size, 101)
    self.assertEqual(path_info.hash_entry.md5, b"norf")

    path_info = data_store.REL_DB.ReadPathInfo(
        client_id=client_urn.Basename(),
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=("foo",),
        timestamp=datetime("2012-12-12"))
    self.assertEqual(path_info.stat_entry.st_size, 42)
    self.assertEqual(path_info.hash_entry.md5, b"thud")


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
