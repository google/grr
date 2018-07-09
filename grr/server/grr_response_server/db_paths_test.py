#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

import hashlib

from grr.core.grr_response_core.lib import rdfvalue
from grr.core.grr_response_core.lib.rdfvalues import client as rdf_client
from grr.core.grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr.core.grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr.server.grr_response_server import db
from grr.server.grr_response_server.rdfvalues import objects as rdf_objects


class DatabaseTestPathsMixin(object):
  """An abstract class for testing db.Database implementations.

  This mixin adds methods to test the handling of GRR path data.
  """

  def testWritePathInfosValidatesClientId(self):
    path = ["usr", "local"]

    with self.assertRaises(ValueError):
      self.db.WritePathInfos("", [rdf_objects.PathInfo.OS(components=path)])

  def testWritePathInfosValidatesPathType(self):
    path = ["usr", "local"]
    client_id = "C.bbbbbbbbbbbbbbbb"

    with self.assertRaises(ValueError):
      self.db.WritePathInfos(client_id, [rdf_objects.PathInfo(components=path)])

  def testWritePathInfosValidatesClient(self):
    client_id = "C.0123456789012345"

    with self.assertRaises(db.UnknownClientError) as context:
      self.db.WritePathInfos(
          client_id, [rdf_objects.PathInfo.OS(components=[], directory=True)])

    self.assertEqual(context.exception.client_id, client_id)

  def testWritePathInfosValidateConflictingWrites(self):
    client_id = self.InitializeClient()

    with self.assertRaises(ValueError):
      self.db.WritePathInfos(client_id, [
          rdf_objects.PathInfo.OS(components=["foo", "bar"], directory=False),
          rdf_objects.PathInfo.OS(components=["foo", "bar"], directory=True),
      ])

  def testWritePathInfosMetadata(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(
        client_id,
        [rdf_objects.PathInfo.TSK(components=["foo", "bar"], directory=True)])

    results = self.db.FindPathInfosByPathIDs(
        client_id, rdf_objects.PathInfo.PathType.TSK,
        [rdf_objects.PathID.FromComponents(["foo", "bar"])])

    result_path_info = results[rdf_objects.PathID.FromComponents(["foo",
                                                                  "bar"])]
    self.assertEqual(result_path_info.path_type,
                     rdf_objects.PathInfo.PathType.TSK)
    self.assertEqual(result_path_info.components, ["foo", "bar"])
    self.assertEqual(result_path_info.directory, True)

  def testWritePathInfosMetadataTimestampUpdate(self):
    now = rdfvalue.RDFDatetime.Now

    client_id = self.InitializeClient()

    timestamp_0 = now()

    self.db.WritePathInfos(
        client_id, [rdf_objects.PathInfo.OS(components=["foo"])])

    result = self.db.FindPathInfoByPathID(
        client_id, rdf_objects.PathInfo.PathType.OS,
        rdf_objects.PathID.FromComponents(["foo"]))
    self.assertEqual(result.components, ["foo"])
    self.assertGreater(result.timestamp, timestamp_0)
    self.assertLess(result.timestamp, now())
    self.assertEqual(result.last_stat_entry_timestamp, None)
    self.assertEqual(result.last_hash_entry_timestamp, None)

    timestamp_1 = now()

    stat_entry = rdf_client.StatEntry(st_mode=42)
    self.db.WritePathInfos(
        client_id,
        [rdf_objects.PathInfo.OS(components=["foo"], stat_entry=stat_entry)])

    result = self.db.FindPathInfoByPathID(
        client_id, rdf_objects.PathInfo.PathType.OS,
        rdf_objects.PathID.FromComponents(["foo"]))
    self.assertEqual(result.components, ["foo"])
    self.assertEqual(result.stat_entry.st_mode, 42)
    self.assertGreater(result.timestamp, timestamp_1)
    self.assertLess(result.timestamp, now())
    self.assertGreater(result.last_stat_entry_timestamp, timestamp_1)
    self.assertLess(result.last_stat_entry_timestamp, now())

    timestamp_2 = now()

    hash_entry = rdf_crypto.Hash(md5=b"foo")
    self.db.WritePathInfos(
        client_id,
        [rdf_objects.PathInfo.OS(components=["foo"], hash_entry=hash_entry)])

    result = self.db.FindPathInfoByPathID(
        client_id, rdf_objects.PathInfo.PathType.OS,
        rdf_objects.PathID.FromComponents(["foo"]))
    self.assertEqual(result.components, ["foo"])
    self.assertEqual(result.hash_entry.md5, b"foo")
    self.assertGreater(result.timestamp, timestamp_2)
    self.assertLess(result.timestamp, now())
    self.assertGreater(result.last_hash_entry_timestamp, timestamp_2)
    self.assertLess(result.last_hash_entry_timestamp, now())

    timestamp_3 = now()

    self.db.WritePathInfos(
        client_id,
        [rdf_objects.PathInfo.OS(components=["foo"], directory=True)])

    result = self.db.FindPathInfoByPathID(
        client_id, rdf_objects.PathInfo.PathType.OS,
        rdf_objects.PathID.FromComponents(["foo"]))
    self.assertEqual(result.components, ["foo"])
    self.assertEqual(result.stat_entry.st_mode, 42)
    self.assertEqual(result.hash_entry.md5, b"foo")
    self.assertTrue(result.directory)
    self.assertGreater(result.timestamp, timestamp_3)
    self.assertLess(result.timestamp, now())
    self.assertGreater(result.last_stat_entry_timestamp, timestamp_1)
    self.assertLess(result.last_stat_entry_timestamp, timestamp_2)
    self.assertGreater(result.last_hash_entry_timestamp, timestamp_2)
    self.assertLess(result.last_hash_entry_timestamp, timestamp_3)

    timestamp_4 = now()

    path_info = rdf_objects.PathInfo.OS(components=["foo"])
    path_info.stat_entry.st_mode = 108
    path_info.hash_entry.sha256 = b"norf"
    self.db.WritePathInfos(client_id, [path_info])

    result = self.db.FindPathInfoByPathID(
        client_id, rdf_objects.PathInfo.PathType.OS,
        rdf_objects.PathID.FromComponents(["foo"]))
    self.assertEqual(result.components, ["foo"])
    self.assertEqual(result.stat_entry.st_mode, 108)
    self.assertEqual(result.hash_entry.sha256, b"norf")
    self.assertGreater(result.timestamp, timestamp_4)
    self.assertGreater(result.last_stat_entry_timestamp, timestamp_4)
    self.assertGreater(result.last_hash_entry_timestamp, timestamp_4)
    self.assertLess(result.timestamp, now())
    self.assertLess(result.last_stat_entry_timestamp, now())
    self.assertLess(result.last_hash_entry_timestamp, now())

  def testWritePathInfosStatEntry(self):
    client_id = self.InitializeClient()

    stat_entry = rdf_client.StatEntry()
    stat_entry.pathspec.path = "foo/bar"
    stat_entry.pathspec.pathtype = rdf_paths.PathSpec.PathType.OS
    stat_entry.st_mode = 1337
    stat_entry.st_mtime = 108
    stat_entry.st_atime = 4815162342

    path_info = rdf_objects.PathInfo.FromStatEntry(stat_entry)
    self.db.WritePathInfos(client_id, [path_info])

    results = self.db.FindPathInfosByPathIDs(
        client_id, rdf_objects.PathInfo.PathType.OS, [
            rdf_objects.PathID.FromComponents([]),
            rdf_objects.PathID.FromComponents(["foo"]),
            rdf_objects.PathID.FromComponents(["foo", "bar"]),
        ])

    root_path_info = results[rdf_objects.PathID.FromComponents([])]
    self.assertFalse(root_path_info.HasField("stat_entry"))

    foo_path_info = results[rdf_objects.PathID.FromComponents(["foo"])]
    self.assertFalse(foo_path_info.HasField("stat_entry"))

    foobar_path_info = results[rdf_objects.PathID.FromComponents(["foo",
                                                                  "bar"])]
    self.assertTrue(foobar_path_info.HasField("stat_entry"))
    self.assertFalse(foobar_path_info.HasField("hash_entry"))
    self.assertEqual(foobar_path_info.stat_entry.st_mode, 1337)
    self.assertEqual(foobar_path_info.stat_entry.st_mtime, 108)
    self.assertEqual(foobar_path_info.stat_entry.st_atime, 4815162342)

  def testWritePathInfosHashEntry(self):
    client_id = self.InitializeClient()

    hash_entry = rdf_crypto.Hash()
    hash_entry.sha256 = hashlib.sha256("foo").digest()
    hash_entry.md5 = hashlib.md5("foo").digest()
    hash_entry.num_bytes = len("foo")

    path_info = rdf_objects.PathInfo.OS(
        components=["foo", "bar", "baz"], hash_entry=hash_entry)
    self.db.WritePathInfos(client_id, [path_info])

    result = self.db.FindPathInfoByPathID(
        client_id, rdf_objects.PathInfo.PathType.OS,
        rdf_objects.PathID.FromComponents(["foo", "bar", "baz"]))

    self.assertEqual(result.components, ["foo", "bar", "baz"])
    self.assertTrue(result.HasField("hash_entry"))
    self.assertFalse(result.HasField("stat_entry"))
    self.assertEqual(result.hash_entry.sha256, hashlib.sha256("foo").digest())
    self.assertEqual(result.hash_entry.md5, hashlib.md5("foo").digest())
    self.assertEqual(result.hash_entry.num_bytes, len("foo"))

  def testWritePathInfosHashAndStatEntry(self):
    client_id = self.InitializeClient()

    stat_entry = rdf_client.StatEntry(st_mode=1337)
    hash_entry = rdf_crypto.Hash(md5=hashlib.md5("foo").digest())

    path_info = rdf_objects.PathInfo.OS(
        components=["foo", "bar", "baz"],
        stat_entry=stat_entry,
        hash_entry=hash_entry)
    self.db.WritePathInfos(client_id, [path_info])

    result = self.db.FindPathInfoByPathID(
        client_id, rdf_objects.PathInfo.PathType.OS,
        rdf_objects.PathID.FromComponents(["foo", "bar", "baz"]))

    self.assertEqual(result.components, ["foo", "bar", "baz"])
    self.assertTrue(result.HasField("stat_entry"))
    self.assertTrue(result.HasField("hash_entry"))
    self.assertEqual(result.stat_entry, stat_entry)
    self.assertEqual(result.hash_entry, hash_entry)

  def testWritePathInfoHashAndStatEntrySeparateWrites(self):
    client_id = self.InitializeClient()

    stat_entry = rdf_client.StatEntry(st_mode=1337)
    stat_entry_path_info = rdf_objects.PathInfo.OS(
        components=["foo"], stat_entry=stat_entry)

    stat_entry_timestamp = rdfvalue.RDFDatetime.Now()
    self.db.WritePathInfos(client_id, [stat_entry_path_info])

    hash_entry = rdf_crypto.Hash(sha256=hashlib.sha256("foo").digest())
    hash_entry_path_info = rdf_objects.PathInfo.OS(
        components=["foo"], hash_entry=hash_entry)

    hash_entry_timestamp = rdfvalue.RDFDatetime.Now()
    self.db.WritePathInfos(client_id, [hash_entry_path_info])

    result = self.db.FindPathInfoByPathID(
        client_id, rdf_objects.PathInfo.PathType.OS,
        rdf_objects.PathID.FromComponents(["foo"]))

    now = rdfvalue.RDFDatetime.Now()

    self.assertEqual(result.components, ["foo"])
    self.assertTrue(result.HasField("stat_entry"))
    self.assertTrue(result.HasField("hash_entry"))
    self.assertEqual(result.stat_entry, stat_entry)
    self.assertEqual(result.hash_entry, hash_entry)
    self.assertGreater(result.last_stat_entry_timestamp, stat_entry_timestamp)
    self.assertLess(result.last_stat_entry_timestamp, hash_entry_timestamp)
    self.assertGreater(result.last_hash_entry_timestamp, hash_entry_timestamp)
    self.assertLess(result.last_hash_entry_timestamp, now)

  def testWritePathInfosExpansion(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(
        client_id, [
            rdf_objects.PathInfo.OS(components=["foo", "bar", "baz"]),
        ])

    results = self.db.FindPathInfosByPathIDs(
        client_id, rdf_objects.PathInfo.PathType.OS, [
            rdf_objects.PathID.FromComponents(["foo"]),
            rdf_objects.PathID.FromComponents(["foo", "bar"]),
            rdf_objects.PathID.FromComponents(["foo", "bar", "baz"]),
        ])

    self.assertEqual(len(results), 3)

    foo = results[rdf_objects.PathID.FromComponents(["foo"])]
    self.assertEqual(foo.components, ["foo"])
    self.assertTrue(foo.directory)

    foobar = results[rdf_objects.PathID.FromComponents(["foo", "bar"])]
    self.assertEqual(foobar.components, ["foo", "bar"])
    self.assertTrue(foobar.directory)

    foobarbaz = results[rdf_objects.PathID.FromComponents(["foo", "bar",
                                                           "baz"])]
    self.assertEqual(foobarbaz.components, ["foo", "bar", "baz"])
    self.assertFalse(foobarbaz.directory)

  def testWritePathInfosTypeSeparated(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(client_id, [
        rdf_objects.PathInfo.OS(components=["foo"], directory=True),
        rdf_objects.PathInfo.TSK(components=["foo"], directory=False),
    ])

    os_results = self.db.FindPathInfosByPathIDs(
        client_id, rdf_objects.PathInfo.PathType.OS,
        [rdf_objects.PathID.FromComponents(["foo"])])
    self.assertEqual(len(os_results), 1)
    self.assertTrue(os_results[rdf_objects.PathID.FromComponents(
        ["foo"])].directory)

    tsk_results = self.db.FindPathInfosByPathIDs(
        client_id, rdf_objects.PathInfo.PathType.TSK,
        [rdf_objects.PathID.FromComponents(["foo"])])
    self.assertEqual(len(tsk_results), 1)
    self.assertFalse(tsk_results[rdf_objects.PathID.FromComponents(
        ["foo"])].directory)

  def testWritePathInfosUpdates(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(client_id, [
        rdf_objects.PathInfo.OS(
            components=["foo", "bar", "baz"], directory=False),
    ])

    self.db.WritePathInfos(client_id, [
        rdf_objects.PathInfo.OS(
            components=["foo", "bar", "baz"], directory=True),
    ])

    results = self.db.FindPathInfosByPathIDs(
        client_id, rdf_objects.PathInfo.PathType.OS, [
            rdf_objects.PathID.FromComponents(["foo", "bar", "baz"]),
        ])

    result_path_info = results[rdf_objects.PathID.FromComponents(
        ["foo", "bar", "baz"])]
    self.assertTrue(result_path_info.directory)

  def testWritePathInfosUpdatesAncestors(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(client_id, [
        rdf_objects.PathInfo.OS(components=["foo"], directory=False),
    ])
    self.db.WritePathInfos(
        client_id, [
            rdf_objects.PathInfo.OS(components=["foo", "bar"]),
        ])

    results = self.db.FindPathInfosByPathIDs(
        client_id, rdf_objects.PathInfo.PathType.OS,
        [rdf_objects.PathID.FromComponents(["foo"])])

    self.assertEqual(len(results), 1)
    self.assertTrue(results[rdf_objects.PathID.FromComponents(
        ["foo"])].directory)

  def testWritePathInfosDuplicatedData(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(
        client_id, [
            rdf_objects.PathInfo.OS(components=["foo", "bar"]),
        ])
    self.db.WritePathInfos(
        client_id, [
            rdf_objects.PathInfo.OS(components=["foo", "bar"]),
        ])

    results = self.db.FindPathInfosByPathIDs(
        client_id, rdf_objects.PathInfo.PathType.OS,
        [rdf_objects.PathID.FromComponents(["foo", "bar"])])
    self.assertEqual(len(results), 1)

    result_path_info = results[rdf_objects.PathID.FromComponents(["foo",
                                                                  "bar"])]
    self.assertEqual(result_path_info.components, ["foo", "bar"])
    self.assertEqual(result_path_info.directory, False)

  def testWritePathInfosStoresCopy(self):
    client_id = self.InitializeClient()

    path_info = rdf_objects.PathInfo.OS(components=["foo", "bar"])

    path_info.stat_entry.st_size = 1337
    path_info.hash_entry.sha256 = b"foo"
    self.db.WritePathInfos(client_id, [path_info])

    timestamp_1 = rdfvalue.RDFDatetime.Now()

    path_info.stat_entry.st_size = 42
    path_info.hash_entry.sha256 = b"bar"
    self.db.WritePathInfos(client_id, [path_info])

    timestamp_2 = rdfvalue.RDFDatetime.Now()

    result_1 = self.db.FindPathInfoByPathID(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        rdf_objects.PathID.FromComponents(["foo", "bar"]),
        timestamp=timestamp_1)
    self.assertEqual(result_1.stat_entry.st_size, 1337)
    self.assertEqual(result_1.hash_entry.sha256, b"foo")

    result_2 = self.db.FindPathInfoByPathID(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        rdf_objects.PathID.FromComponents(["foo", "bar"]),
        timestamp=timestamp_2)
    self.assertEqual(result_2.stat_entry.st_size, 42)
    self.assertEqual(result_2.hash_entry.sha256, b"bar")

  def testWriteStatHistory(self):
    datetime = rdfvalue.RDFDatetime.FromHumanReadable

    client_id = self.InitializeClient()
    path_info = rdf_objects.PathInfo.OS(components=["foo", "bar"])

    stat_entries = {
        datetime("2010-10-10"): rdf_client.StatEntry(st_size=10),
        datetime("2011-11-11"): rdf_client.StatEntry(st_size=11),
        datetime("2012-12-12"): rdf_client.StatEntry(st_size=12),
    }

    self.db.WritePathInfos(client_id, [path_info])
    self.db.WritePathStatHistory(client_id, path_info, stat_entries)

    path_info_0 = self.db.FindPathInfoByPathID(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        path_info.GetPathID(),
        timestamp=datetime("2010-10-20"))
    self.assertEqual(path_info_0.stat_entry.st_size, 10)

    path_info_1 = self.db.FindPathInfoByPathID(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        path_info.GetPathID(),
        timestamp=datetime("2011-11-20"))
    self.assertEqual(path_info_1.stat_entry.st_size, 11)

    path_info_2 = self.db.FindPathInfoByPathID(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        path_info.GetPathID(),
        timestamp=datetime("2012-12-20"))
    self.assertEqual(path_info_2.stat_entry.st_size, 12)

    path_info = self.db.FindPathInfoByPathID(client_id,
                                             rdf_objects.PathInfo.PathType.OS,
                                             path_info.GetPathID())
    self.assertEqual(path_info.stat_entry.st_size, 12)
    self.assertEqual(path_info.last_stat_entry_timestamp,
                     datetime("2012-12-12"))

  def testWriteHashHistory(self):
    datetime = rdfvalue.RDFDatetime.FromHumanReadable

    client_id = self.InitializeClient()
    path_info = rdf_objects.PathInfo.OS(components=["foo", "bar"])

    hash_entries = {
        datetime("2000-01-01"): rdf_crypto.Hash(md5=b"quux"),
        datetime("2000-02-01"): rdf_crypto.Hash(md5=b"norf"),
        datetime("2000-03-01"): rdf_crypto.Hash(md5=b"thud"),
    }

    self.db.WritePathInfos(client_id, [path_info])
    self.db.WritePathHashHistory(client_id, path_info, hash_entries)

    path_info_1 = self.db.FindPathInfoByPathID(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        path_info.GetPathID(),
        timestamp=datetime("2000-01-20"))
    self.assertEqual(path_info_1.hash_entry.md5, b"quux")

    path_info_2 = self.db.FindPathInfoByPathID(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        path_info.GetPathID(),
        timestamp=datetime("2000-02-20"))
    self.assertEqual(path_info_2.hash_entry.md5, b"norf")

    path_info_3 = self.db.FindPathInfoByPathID(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        path_info.GetPathID(),
        timestamp=datetime("2000-03-20"))
    self.assertEqual(path_info_3.hash_entry.md5, b"thud")

    path_info = self.db.FindPathInfoByPathID(client_id,
                                             rdf_objects.PathInfo.PathType.OS,
                                             path_info.GetPathID())
    self.assertEqual(path_info.hash_entry.md5, b"thud")
    self.assertEqual(path_info.last_hash_entry_timestamp,
                     datetime("2000-03-01"))

  def testMultiWriteHistoryEmpty(self):
    client_id = self.InitializeClient()
    self.db.MultiWritePathHistory(client_id, {}, {})  # Should not rise.

  def testMultiWriteHistoryStatAndHash(self):
    client_id = self.InitializeClient()

    path_info = rdf_objects.PathInfo.OS(components=["foo"])
    path_info.timestamp = rdfvalue.RDFDatetime.FromHumanReadable("2000-01-01")

    self.db.WritePathInfos(client_id, [path_info])

    stat_entries = {path_info: rdf_client.StatEntry(st_size=42)}
    hash_entries = {path_info: rdf_crypto.Hash(md5=b"quux")}

    self.db.MultiWritePathHistory(client_id, stat_entries, hash_entries)

    result_path_info = self.db.FindPathInfoByPathID(
        client_id, rdf_objects.PathInfo.PathType.OS, path_info.GetPathID())
    self.assertEqual(result_path_info.stat_entry.st_size, 42)
    self.assertEqual(result_path_info.hash_entry.md5, b"quux")
    self.assertEqual(result_path_info.last_stat_entry_timestamp,
                     rdfvalue.RDFDatetime.FromHumanReadable("2000-01-01"))
    self.assertEqual(result_path_info.last_hash_entry_timestamp,
                     rdfvalue.RDFDatetime.FromHumanReadable("2000-01-01"))

  def testMultiWriteHistoryTwoPathTypes(self):
    client_id = self.InitializeClient()

    path_info_1 = rdf_objects.PathInfo.OS(components=["foo"])
    path_info_1.timestamp = rdfvalue.RDFDatetime.FromHumanReadable("1999-01-01")

    path_info_2 = rdf_objects.PathInfo.TSK(components=["bar"])
    path_info_2.timestamp = rdfvalue.RDFDatetime.FromHumanReadable("1988-01-01")

    self.db.WritePathInfos(client_id, [path_info_1, path_info_2])

    stat_entries = {
        path_info_1: rdf_client.StatEntry(st_mode=1337),
        path_info_2: rdf_client.StatEntry(st_mode=108),
    }
    self.db.MultiWritePathHistory(client_id, stat_entries, {})

    path_info = self.db.FindPathInfoByPathID(
        client_id, rdf_objects.PathInfo.PathType.OS,
        rdf_objects.PathID.FromComponents(["foo"]))
    self.assertEqual(path_info.stat_entry.st_mode, 1337)
    self.assertEqual(path_info.last_stat_entry_timestamp,
                     rdfvalue.RDFDatetime.FromHumanReadable("1999-01-01"))

    path_info = self.db.FindPathInfoByPathID(
        client_id, rdf_objects.PathInfo.PathType.TSK,
        rdf_objects.PathID.FromComponents(["bar"]))
    self.assertEqual(path_info.stat_entry.st_mode, 108)
    self.assertEqual(path_info.last_stat_entry_timestamp,
                     rdfvalue.RDFDatetime.FromHumanReadable("1988-01-01"))

  def testMultiWriteHistoryTwoPaths(self):
    client_id = self.InitializeClient()

    path_info_foo = rdf_objects.PathInfo.OS(
        components=["foo"],
        timestamp=rdfvalue.RDFDatetime.FromHumanReadable("2010-10-10"))

    path_info_bar = rdf_objects.PathInfo.OS(
        components=["bar"],
        timestamp=rdfvalue.RDFDatetime.FromHumanReadable("2011-11-11"))

    self.db.WritePathInfos(client_id, [path_info_foo, path_info_bar])

    hash_entries = {
        path_info_foo: rdf_crypto.Hash(md5=b"foo"),
        path_info_bar: rdf_crypto.Hash(md5=b"bar"),
    }
    self.db.MultiWritePathHistory(client_id, {}, hash_entries)

    path_info = self.db.FindPathInfoByPathID(
        client_id, rdf_objects.PathInfo.PathType.OS,
        rdf_objects.PathID.FromComponents(["foo"]))
    self.assertEqual(path_info.hash_entry.md5, b"foo")
    self.assertEqual(path_info.last_hash_entry_timestamp,
                     rdfvalue.RDFDatetime.FromHumanReadable("2010-10-10"))

    path_info = self.db.FindPathInfoByPathID(
        client_id, rdf_objects.PathInfo.PathType.OS,
        rdf_objects.PathID.FromComponents(["bar"]))
    self.assertEqual(path_info.hash_entry.md5, b"bar")
    self.assertEqual(path_info.last_hash_entry_timestamp,
                     rdfvalue.RDFDatetime.FromHumanReadable("2011-11-11"))

  def testFindPathInfosByPathIDsNonExistent(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(
        client_id, [
            rdf_objects.PathInfo.OS(components=["foo", "bar"]),
        ])

    results = self.db.FindPathInfosByPathIDs(
        client_id, rdf_objects.PathInfo.PathType.OS, [
            rdf_objects.PathID.FromComponents(["foo", "bar"]),
            rdf_objects.PathID.FromComponents(["foo", "baz"]),
            rdf_objects.PathID.FromComponents(["quux", "norf"])
        ])
    self.assertEqual(len(results), 3)
    self.assertIsNotNone(results[rdf_objects.PathID.FromComponents(
        ["foo", "bar"])])
    self.assertIsNone(results[rdf_objects.PathID.FromComponents(["foo",
                                                                 "baz"])])
    self.assertIsNone(results[rdf_objects.PathID.FromComponents(
        ["quux", "norf"])])

  def testFindPathInfoByPathIDValidatesTimestamp(self):
    client_id = self.InitializeClient()
    path_id = rdf_objects.PathID.FromComponents(["foo", "bar", "baz"])

    with self.assertRaises(TypeError):
      self.db.FindPathInfoByPathID(
          client_id,
          rdf_objects.PathInfo.PathType.REGISTRY,
          path_id,
          timestamp=rdfvalue.Duration("10s"))

  def testFindPathInfoByPathIDNonExistent(self):
    client_id = self.InitializeClient()
    path_id = rdf_objects.PathID.FromComponents(["foo", "bar", "baz"])

    with self.assertRaises(db.UnknownPathError):
      self.db.FindPathInfoByPathID(client_id, rdf_objects.PathInfo.PathType.OS,
                                   path_id)

  def testFindPathInfoByPathIDTimestampStatEntry(self):
    client_id = self.InitializeClient()

    pathspec = rdf_paths.PathSpec(
        path="foo/bar/baz", pathtype=rdf_paths.PathSpec.PathType.OS)

    stat_entry = rdf_client.StatEntry(pathspec=pathspec, st_size=42)
    self.db.WritePathInfos(client_id,
                           [rdf_objects.PathInfo.FromStatEntry(stat_entry)])
    timestamp_1 = rdfvalue.RDFDatetime.Now()

    stat_entry = rdf_client.StatEntry(pathspec=pathspec, st_size=101)
    self.db.WritePathInfos(client_id,
                           [rdf_objects.PathInfo.FromStatEntry(stat_entry)])
    timestamp_2 = rdfvalue.RDFDatetime.Now()

    stat_entry = rdf_client.StatEntry(pathspec=pathspec, st_size=1337)
    self.db.WritePathInfos(client_id,
                           [rdf_objects.PathInfo.FromStatEntry(stat_entry)])
    timestamp_3 = rdfvalue.RDFDatetime.Now()

    path_id = rdf_objects.PathID.FromComponents(["foo", "bar", "baz"])

    path_info_last = self.db.FindPathInfoByPathID(
        client_id, rdf_objects.PathInfo.PathType.OS, path_id)
    self.assertEqual(path_info_last.stat_entry.st_size, 1337)
    self.assertEqual(path_info_last.components, ["foo", "bar", "baz"])

    path_info_1 = self.db.FindPathInfoByPathID(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        path_id,
        timestamp=timestamp_1)
    self.assertEqual(path_info_1.stat_entry.st_size, 42)
    self.assertEqual(path_info_last.components, ["foo", "bar", "baz"])

    path_info_2 = self.db.FindPathInfoByPathID(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        path_id,
        timestamp=timestamp_2)
    self.assertEqual(path_info_2.stat_entry.st_size, 101)
    self.assertEqual(path_info_last.components, ["foo", "bar", "baz"])

    path_info_3 = self.db.FindPathInfoByPathID(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        path_id,
        timestamp=timestamp_3)
    self.assertEqual(path_info_3.stat_entry.st_size, 1337)
    self.assertEqual(path_info_last.components, ["foo", "bar", "baz"])

  def testFindPathInfoByPathIDTimestampHashEntry(self):
    client_id = self.InitializeClient()

    path_info = rdf_objects.PathInfo.OS(components=["foo"])
    path_id = rdf_objects.PathID.FromComponents(["foo"])

    path_info.hash_entry = rdf_crypto.Hash(md5=b"bar")
    self.db.WritePathInfos(client_id, [path_info])
    bar_timestamp = rdfvalue.RDFDatetime.Now()

    path_info.hash_entry = rdf_crypto.Hash(md5=b"baz")
    self.db.WritePathInfos(client_id, [path_info])
    baz_timestamp = rdfvalue.RDFDatetime.Now()

    path_info.hash_entry = rdf_crypto.Hash(md5=b"quux")
    self.db.WritePathInfos(client_id, [path_info])
    quux_timestamp = rdfvalue.RDFDatetime.Now()

    bar_path_info = self.db.FindPathInfoByPathID(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        path_id,
        timestamp=bar_timestamp)
    self.assertEqual(bar_path_info.hash_entry.md5, b"bar")

    baz_path_info = self.db.FindPathInfoByPathID(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        path_id,
        timestamp=baz_timestamp)
    self.assertEqual(baz_path_info.hash_entry.md5, b"baz")

    quux_path_info = self.db.FindPathInfoByPathID(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        path_id,
        timestamp=quux_timestamp)
    self.assertEqual(quux_path_info.hash_entry.md5, b"quux")

  def testFindPathInfosByPathIDsMany(self):
    client_id = self.InitializeClient()

    path_info_1 = rdf_objects.PathInfo.OS(components=["foo", "bar"])
    path_info_1.stat_entry.st_mode = 42
    path_info_1.hash_entry.md5 = b"foobar"

    path_info_2 = rdf_objects.PathInfo.OS(components=["baz", "quux", "norf"])
    path_info_2.hash_entry.sha256 = b"bazquuxnorf"

    path_info_3 = rdf_objects.PathInfo.OS(components=["blargh"], directory=True)
    path_info_3.stat_entry.st_size = 1337

    self.db.WritePathInfos(client_id, [path_info_1, path_info_2, path_info_3])

    path_id_1 = rdf_objects.PathID.FromComponents(["foo", "bar"])
    path_id_2 = rdf_objects.PathID.FromComponents(["baz", "quux", "norf"])
    path_id_3 = rdf_objects.PathID.FromComponents(["blargh"])

    results = self.db.FindPathInfosByPathIDs(client_id,
                                             rdf_objects.PathInfo.PathType.OS,
                                             [path_id_1, path_id_2, path_id_3])

    self.assertEqual(results[path_id_1].components, ["foo", "bar"])
    self.assertEqual(results[path_id_1].stat_entry.st_mode, 42)
    self.assertEqual(results[path_id_1].hash_entry.md5, b"foobar")

    self.assertEqual(results[path_id_2].components, ["baz", "quux", "norf"])
    self.assertEqual(results[path_id_2].hash_entry.sha256, b"bazquuxnorf")

    self.assertEqual(results[path_id_3].components, ["blargh"])
    self.assertEqual(results[path_id_3].stat_entry.st_size, 1337)
    self.assertEqual(results[path_id_3].directory, True)

  def testFindPathInfoByPathIDTimestampStatAndHashEntry(self):
    client_id = self.InitializeClient()

    path_info = rdf_objects.PathInfo.OS(components=["foo"])
    path_id = rdf_objects.PathID.FromComponents(["foo"])

    path_info.stat_entry = rdf_client.StatEntry(st_mode=42)
    path_info.hash_entry = None
    self.db.WritePathInfos(client_id, [path_info])
    timestamp_1 = rdfvalue.RDFDatetime.Now()

    path_info.stat_entry = None
    path_info.hash_entry = rdf_crypto.Hash(md5=b"quux")
    self.db.WritePathInfos(client_id, [path_info])
    timestamp_2 = rdfvalue.RDFDatetime.Now()

    path_info.stat_entry = rdf_client.StatEntry(st_mode=1337)
    path_info.hash_entry = None
    self.db.WritePathInfos(client_id, [path_info])
    timestamp_3 = rdfvalue.RDFDatetime.Now()

    path_info.stat_entry = rdf_client.StatEntry(st_mode=4815162342)
    path_info.hash_entry = rdf_crypto.Hash(md5=b"norf")
    self.db.WritePathInfos(client_id, [path_info])
    timestamp_4 = rdfvalue.RDFDatetime.Now()

    path_info_1 = self.db.FindPathInfoByPathID(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        path_id,
        timestamp=timestamp_1)
    self.assertEqual(path_info_1.stat_entry.st_mode, 42)
    self.assertFalse(path_info_1.HasField("hash_entry"))

    path_info_2 = self.db.FindPathInfoByPathID(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        path_id,
        timestamp=timestamp_2)
    self.assertEqual(path_info_2.stat_entry.st_mode, 42)
    self.assertEqual(path_info_2.hash_entry.md5, b"quux")

    path_info_3 = self.db.FindPathInfoByPathID(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        path_id,
        timestamp=timestamp_3)
    self.assertEqual(path_info_3.stat_entry.st_mode, 1337)
    self.assertEqual(path_info_3.hash_entry.md5, b"quux")

    path_info_4 = self.db.FindPathInfoByPathID(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        path_id,
        timestamp=timestamp_4)
    self.assertEqual(path_info_4.stat_entry.st_mode, 4815162342)
    self.assertEqual(path_info_4.hash_entry.md5, b"norf")

  def testFindPathInfoByPathIDOlder(self):
    client_id = self.InitializeClient()

    path_info = rdf_objects.PathInfo.OS(components=["foo"])
    path_info.stat_entry.st_mode = 42
    path_info.hash_entry.md5 = b"foo"
    self.db.WritePathInfos(client_id, [path_info])

    path_info = rdf_objects.PathInfo.OS(components=["bar"])
    path_info.stat_entry.st_mode = 1337
    path_info.hash_entry.md5 = b"bar"
    self.db.WritePathInfos(client_id, [path_info])

    path_info = self.db.FindPathInfoByPathID(
        client_id, rdf_objects.PathInfo.PathType.OS,
        rdf_objects.PathID.FromComponents(["foo"]))
    self.assertEqual(path_info.stat_entry.st_mode, 42)
    self.assertEqual(path_info.hash_entry.md5, b"foo")

    path_info = self.db.FindPathInfoByPathID(
        client_id, rdf_objects.PathInfo.PathType.OS,
        rdf_objects.PathID.FromComponents(["bar"]))
    self.assertEqual(path_info.stat_entry.st_mode, 1337)
    self.assertEqual(path_info.hash_entry.md5, b"bar")

  def testFindDescendentPathIDsEmptyResult(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(
        client_id, [rdf_objects.PathInfo.OS(components=["foo"])])

    results = self.db.FindDescendentPathIDs(
        client_id, rdf_objects.PathInfo.PathType.OS,
        rdf_objects.PathID.FromComponents(["foo"]))
    self.assertItemsEqual(results, [])

  def testFindDescendentPathIDsSingleResult(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(
        client_id, [
            rdf_objects.PathInfo.OS(components=["foo", "bar"]),
        ])

    results = self.db.FindDescendentPathIDs(
        client_id, rdf_objects.PathInfo.PathType.OS,
        rdf_objects.PathID.FromComponents(["foo"]))

    self.assertItemsEqual(results,
                          [rdf_objects.PathID.FromComponents(["foo", "bar"])])

  def testFindDescendentPathIDsSingle(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(
        client_id, [
            rdf_objects.PathInfo.OS(components=["foo", "bar", "baz", "quux"]),
        ])

    results = self.db.FindDescendentPathIDs(
        client_id, rdf_objects.PathInfo.PathType.OS,
        rdf_objects.PathID.FromComponents(["foo"]))

    self.assertItemsEqual(results, [
        rdf_objects.PathID.FromComponents(["foo", "bar"]),
        rdf_objects.PathID.FromComponents(["foo", "bar", "baz"]),
        rdf_objects.PathID.FromComponents(["foo", "bar", "baz", "quux"]),
    ])

  def testFindDescendentPathIDsBranching(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(
        client_id, [
            rdf_objects.PathInfo.OS(components=["foo", "bar", "quux"]),
            rdf_objects.PathInfo.OS(components=["foo", "baz"]),
        ])

    results = self.db.FindDescendentPathIDs(
        client_id, rdf_objects.PathInfo.PathType.OS,
        rdf_objects.PathID.FromComponents(["foo"]))

    self.assertItemsEqual(results, [
        rdf_objects.PathID.FromComponents(["foo", "bar"]),
        rdf_objects.PathID.FromComponents(["foo", "bar", "quux"]),
        rdf_objects.PathID.FromComponents(["foo", "baz"]),
    ])

  def testFindDescendentPathIDsLimited(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(
        client_id, [
            rdf_objects.PathInfo.OS(components=["foo", "bar", "baz", "quux"]),
            rdf_objects.PathInfo.OS(components=["foo", "bar", "blargh"]),
            rdf_objects.PathInfo.OS(
                components=["foo", "norf", "thud", "plugh"]),
        ])

    results = self.db.FindDescendentPathIDs(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        rdf_objects.PathID.FromComponents(["foo"]),
        max_depth=2)

    self.assertIn(rdf_objects.PathID.FromComponents(["foo", "bar"]), results)
    self.assertIn(
        rdf_objects.PathID.FromComponents(["foo", "bar", "baz"]), results)
    self.assertIn(
        rdf_objects.PathID.FromComponents(["foo", "bar", "blargh"]), results)
    self.assertIn(
        rdf_objects.PathID.FromComponents(["foo", "norf", "thud"]), results)

    self.assertNotIn(
        rdf_objects.PathID.FromComponents(["foo", "bar", "baz", "quux"]),
        results)
    self.assertNotIn(
        rdf_objects.PathID.FromComponents(["foo", "norf", "thud", "plugh"]),
        results)

  def testFindDescendentPathIDsTypeSeparated(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(
        client_id, [
            rdf_objects.PathInfo.OS(components=["usr", "bin", "javac"]),
            rdf_objects.PathInfo.TSK(components=["usr", "bin", "gdb"]),
        ])

    os_results = self.db.FindDescendentPathIDs(
        client_id, rdf_objects.PathInfo.PathType.OS,
        rdf_objects.PathID.FromComponents(["usr", "bin"]))
    self.assertEqual(
        os_results,
        {rdf_objects.PathID.FromComponents(["usr", "bin", "javac"])})

    tsk_results = self.db.FindDescendentPathIDs(
        client_id, rdf_objects.PathInfo.PathType.TSK,
        rdf_objects.PathID.FromComponents(["usr", "bin"]))
    self.assertEqual(tsk_results,
                     {rdf_objects.PathID.FromComponents(["usr", "bin", "gdb"])})

  def testFindDescendentPathIDsAll(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(
        client_id, [
            rdf_objects.PathInfo.OS(components=["foo", "bar"]),
            rdf_objects.PathInfo.OS(components=["baz", "quux"]),
        ])

    results = self.db.FindDescendentPathIDs(
        client_id, rdf_objects.PathInfo.PathType.OS,
        rdf_objects.PathID.FromComponents([]))
    self.assertItemsEqual(results, [
        rdf_objects.PathID.FromComponents(["foo"]),
        rdf_objects.PathID.FromComponents(["foo", "bar"]),
        rdf_objects.PathID.FromComponents(["baz"]),
        rdf_objects.PathID.FromComponents(["baz", "quux"]),
    ])
