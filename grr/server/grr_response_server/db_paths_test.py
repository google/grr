#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import hashlib

from future.utils import itervalues

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import db
from grr_response_server.rdfvalues import objects as rdf_objects


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

    results = self.db.ReadPathInfos(
        client_id, rdf_objects.PathInfo.PathType.TSK, [("foo", "bar")])

    result_path_info = results[("foo", "bar")]
    self.assertEqual(result_path_info.path_type,
                     rdf_objects.PathInfo.PathType.TSK)
    self.assertEqual(result_path_info.components, ["foo", "bar"])
    self.assertEqual(result_path_info.directory, True)

  def testWritePathInfosMetadataTimestampUpdate(self):
    now = rdfvalue.RDFDatetime.Now

    client_id = self.InitializeClient()

    timestamp_0 = now()

    self.db.WritePathInfos(client_id,
                           [rdf_objects.PathInfo.OS(components=["foo"])])

    result = self.db.ReadPathInfo(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))
    self.assertEqual(result.components, ["foo"])
    self.assertGreater(result.timestamp, timestamp_0)
    self.assertLess(result.timestamp, now())
    self.assertEqual(result.last_stat_entry_timestamp, None)
    self.assertEqual(result.last_hash_entry_timestamp, None)

    timestamp_1 = now()

    stat_entry = rdf_client_fs.StatEntry(st_mode=42)
    self.db.WritePathInfos(
        client_id,
        [rdf_objects.PathInfo.OS(components=["foo"], stat_entry=stat_entry)])

    result = self.db.ReadPathInfo(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))
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

    result = self.db.ReadPathInfo(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))
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

    result = self.db.ReadPathInfo(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))
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

    result = self.db.ReadPathInfo(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))
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

    stat_entry = rdf_client_fs.StatEntry()
    stat_entry.pathspec.path = "foo/bar"
    stat_entry.pathspec.pathtype = rdf_paths.PathSpec.PathType.OS
    stat_entry.st_mode = 1337
    stat_entry.st_mtime = 108
    stat_entry.st_atime = 4815162342

    path_info = rdf_objects.PathInfo.FromStatEntry(stat_entry)
    self.db.WritePathInfos(client_id, [path_info])

    results = self.db.ReadPathInfos(client_id, rdf_objects.PathInfo.PathType.OS,
                                    [
                                        (),
                                        ("foo",),
                                        ("foo", "bar"),
                                    ])

    root_path_info = results[()]
    self.assertFalse(root_path_info.HasField("stat_entry"))

    foo_path_info = results[("foo",)]
    self.assertFalse(foo_path_info.HasField("stat_entry"))

    foobar_path_info = results[("foo", "bar")]
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

    result = self.db.ReadPathInfo(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo", "bar", "baz"))

    self.assertEqual(result.components, ["foo", "bar", "baz"])
    self.assertTrue(result.HasField("hash_entry"))
    self.assertFalse(result.HasField("stat_entry"))
    self.assertEqual(result.hash_entry.sha256, hashlib.sha256("foo").digest())
    self.assertEqual(result.hash_entry.md5, hashlib.md5("foo").digest())
    self.assertEqual(result.hash_entry.num_bytes, len("foo"))

  def testWritePathInfosHashAndStatEntry(self):
    client_id = self.InitializeClient()

    stat_entry = rdf_client_fs.StatEntry(st_mode=1337)
    hash_entry = rdf_crypto.Hash(md5=hashlib.md5("foo").digest())

    path_info = rdf_objects.PathInfo.OS(
        components=["foo", "bar", "baz"],
        stat_entry=stat_entry,
        hash_entry=hash_entry)
    self.db.WritePathInfos(client_id, [path_info])

    result = self.db.ReadPathInfo(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo", "bar", "baz"))

    self.assertEqual(result.components, ["foo", "bar", "baz"])
    self.assertTrue(result.HasField("stat_entry"))
    self.assertTrue(result.HasField("hash_entry"))
    self.assertEqual(result.stat_entry, stat_entry)
    self.assertEqual(result.hash_entry, hash_entry)

  def testWritePathInfoHashAndStatEntrySeparateWrites(self):
    client_id = self.InitializeClient()

    stat_entry = rdf_client_fs.StatEntry(st_mode=1337)
    stat_entry_path_info = rdf_objects.PathInfo.OS(
        components=["foo"], stat_entry=stat_entry)

    stat_entry_timestamp = rdfvalue.RDFDatetime.Now()
    self.db.WritePathInfos(client_id, [stat_entry_path_info])

    hash_entry = rdf_crypto.Hash(sha256=hashlib.sha256("foo").digest())
    hash_entry_path_info = rdf_objects.PathInfo.OS(
        components=["foo"], hash_entry=hash_entry)

    hash_entry_timestamp = rdfvalue.RDFDatetime.Now()
    self.db.WritePathInfos(client_id, [hash_entry_path_info])

    result = self.db.ReadPathInfo(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))

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

    self.db.WritePathInfos(client_id, [
        rdf_objects.PathInfo.OS(components=["foo", "bar", "baz"]),
    ])

    results = self.db.ReadPathInfos(client_id, rdf_objects.PathInfo.PathType.OS,
                                    [
                                        ("foo",),
                                        ("foo", "bar"),
                                        ("foo", "bar", "baz"),
                                    ])

    self.assertLen(results, 3)

    foo = results[("foo",)]
    self.assertEqual(foo.components, ["foo"])
    self.assertTrue(foo.directory)

    foobar = results[("foo", "bar")]
    self.assertEqual(foobar.components, ["foo", "bar"])
    self.assertTrue(foobar.directory)

    foobarbaz = results[("foo", "bar", "baz")]
    self.assertEqual(foobarbaz.components, ["foo", "bar", "baz"])
    self.assertFalse(foobarbaz.directory)

  def testWritePathInfosTypeSeparated(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(client_id, [
        rdf_objects.PathInfo.OS(components=["foo"], directory=True),
        rdf_objects.PathInfo.TSK(components=["foo"], directory=False),
    ])

    os_results = self.db.ReadPathInfos(
        client_id, rdf_objects.PathInfo.PathType.OS, [("foo",)])
    self.assertLen(os_results, 1)
    self.assertTrue(os_results[("foo",)].directory)

    tsk_results = self.db.ReadPathInfos(
        client_id, rdf_objects.PathInfo.PathType.TSK, [("foo",)])
    self.assertLen(tsk_results, 1)
    self.assertFalse(tsk_results[("foo",)].directory)

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

    results = self.db.ReadPathInfos(client_id, rdf_objects.PathInfo.PathType.OS,
                                    [("foo", "bar", "baz")])

    result_path_info = results[("foo", "bar", "baz")]
    self.assertTrue(result_path_info.directory)

  def testWritePathInfosUpdatesAncestors(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(client_id, [
        rdf_objects.PathInfo.OS(components=["foo"], directory=False),
    ])
    self.db.WritePathInfos(client_id, [
        rdf_objects.PathInfo.OS(components=["foo", "bar"]),
    ])

    results = self.db.ReadPathInfos(client_id, rdf_objects.PathInfo.PathType.OS,
                                    [("foo",)])

    self.assertLen(results, 1)
    self.assertTrue(results[("foo",)].directory)

  def testWritePathInfosDuplicatedData(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(client_id, [
        rdf_objects.PathInfo.OS(components=["foo", "bar"]),
    ])
    self.db.WritePathInfos(client_id, [
        rdf_objects.PathInfo.OS(components=["foo", "bar"]),
    ])

    results = self.db.ReadPathInfos(client_id, rdf_objects.PathInfo.PathType.OS,
                                    [("foo", "bar")])
    self.assertLen(results, 1)

    result_path_info = results[("foo", "bar")]
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

    result_1 = self.db.ReadPathInfo(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo", "bar"),
        timestamp=timestamp_1)
    self.assertEqual(result_1.stat_entry.st_size, 1337)
    self.assertEqual(result_1.hash_entry.sha256, b"foo")

    result_2 = self.db.ReadPathInfo(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo", "bar"),
        timestamp=timestamp_2)
    self.assertEqual(result_2.stat_entry.st_size, 42)
    self.assertEqual(result_2.hash_entry.sha256, b"bar")

  def testMultiWritePathInfos(self):
    client_a_id = self.InitializeClient()
    client_b_id = self.InitializeClient()

    path_info_a_1 = rdf_objects.PathInfo.OS(components=["foo", "bar"])
    path_info_a_1.stat_entry.st_size = 42

    path_info_a_2 = rdf_objects.PathInfo.OS(components=["foo", "baz"])
    path_info_a_2.hash_entry.md5 = b"aaa"

    path_info_b_1 = rdf_objects.PathInfo.TSK(components=["norf", "thud"])
    path_info_b_1.hash_entry.sha256 = b"bbb"

    path_info_b_2 = rdf_objects.PathInfo.TSK(components=["quux", "blargh"])
    path_info_b_2.stat_entry.st_mode = 1337

    path_infos = {
        client_a_id: [path_info_a_1, path_info_a_2],
        client_b_id: [path_info_b_1, path_info_b_2],
    }
    self.db.MultiWritePathInfos(path_infos)

    path_infos_a = self.db.ReadPathInfos(client_a_id,
                                         rdf_objects.PathInfo.PathType.OS, [
                                             ("foo", "bar"),
                                             ("foo", "baz"),
                                         ])
    self.assertEqual(path_infos_a[("foo", "bar")].stat_entry.st_size, 42)
    self.assertEqual(path_infos_a[("foo", "baz")].hash_entry.md5, b"aaa")

    path_infos_b = self.db.ReadPathInfos(client_b_id,
                                         rdf_objects.PathInfo.PathType.TSK, [
                                             ("norf", "thud"),
                                             ("quux", "blargh"),
                                         ])
    self.assertEqual(path_infos_b[("norf", "thud")].hash_entry.sha256, b"bbb")
    self.assertEqual(path_infos_b[("quux", "blargh")].stat_entry.st_mode, 1337)

  def testWriteStatHistory(self):
    datetime = rdfvalue.RDFDatetime.FromHumanReadable

    client_id = self.InitializeClient()
    path_info = rdf_objects.PathInfo.OS(components=["foo", "bar"])

    stat_entries = {
        datetime("2010-10-10"): rdf_client_fs.StatEntry(st_size=10),
        datetime("2011-11-11"): rdf_client_fs.StatEntry(st_size=11),
        datetime("2012-12-12"): rdf_client_fs.StatEntry(st_size=12),
    }

    self.db.WritePathInfos(client_id, [path_info])
    self.db.WritePathStatHistory(
        client_path=db.ClientPath.OS(client_id, ("foo", "bar")),
        stat_entries=stat_entries)

    path_info_0 = self.db.ReadPathInfo(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo", "bar"),
        timestamp=datetime("2010-10-20"))
    self.assertEqual(path_info_0.stat_entry.st_size, 10)

    path_info_1 = self.db.ReadPathInfo(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo", "bar"),
        timestamp=datetime("2011-11-20"))
    self.assertEqual(path_info_1.stat_entry.st_size, 11)

    path_info_2 = self.db.ReadPathInfo(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo", "bar"),
        timestamp=datetime("2012-12-20"))
    self.assertEqual(path_info_2.stat_entry.st_size, 12)

    path_info = self.db.ReadPathInfo(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo", "bar"))
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
    self.db.WritePathHashHistory(
        client_path=db.ClientPath.OS(client_id, ("foo", "bar")),
        hash_entries=hash_entries)

    path_info_1 = self.db.ReadPathInfo(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo", "bar"),
        timestamp=datetime("2000-01-20"))
    self.assertEqual(path_info_1.hash_entry.md5, b"quux")

    path_info_2 = self.db.ReadPathInfo(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo", "bar"),
        timestamp=datetime("2000-02-20"))
    self.assertEqual(path_info_2.hash_entry.md5, b"norf")

    path_info_3 = self.db.ReadPathInfo(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo", "bar"),
        timestamp=datetime("2000-03-20"))
    self.assertEqual(path_info_3.hash_entry.md5, b"thud")

    path_info = self.db.ReadPathInfo(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo", "bar"))
    self.assertEqual(path_info.hash_entry.md5, b"thud")
    self.assertEqual(path_info.last_hash_entry_timestamp,
                     datetime("2000-03-01"))

  def testMultiWriteHistoryEmpty(self):
    client_id = self.InitializeClient()

    client_path = db.ClientPath.OS(client_id, components=("foo", "bar", "baz"))
    client_path_history = db.ClientPathHistory()

    # Should not rise.
    self.db.MultiWritePathHistory({client_path: client_path_history})

  def testMultiWriteHistoryStatAndHash(self):
    datetime = rdfvalue.RDFDatetime.FromHumanReadable

    client_id = self.InitializeClient()

    path_info = rdf_objects.PathInfo.OS(components=["foo"])
    self.db.WritePathInfos(client_id, [path_info])

    client_path = db.ClientPath.OS(client_id, components=("foo",))
    client_path_history = db.ClientPathHistory()
    client_path_history.AddStatEntry(
        datetime("2000-01-01"), rdf_client_fs.StatEntry(st_size=42))
    client_path_history.AddHashEntry(
        datetime("2000-01-01"), rdf_crypto.Hash(md5=b"quux"))

    self.db.MultiWritePathHistory({client_path: client_path_history})

    result_path_info = self.db.ReadPathInfo(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))
    self.assertEqual(result_path_info.stat_entry.st_size, 42)
    self.assertEqual(result_path_info.hash_entry.md5, b"quux")
    self.assertEqual(result_path_info.last_stat_entry_timestamp,
                     datetime("2000-01-01"))
    self.assertEqual(result_path_info.last_hash_entry_timestamp,
                     datetime("2000-01-01"))

  def testMultiWriteHistoryTwoPathTypes(self):
    datetime = rdfvalue.RDFDatetime.FromHumanReadable

    client_id = self.InitializeClient()

    path_info_1 = rdf_objects.PathInfo.OS(components=["foo"])
    path_info_2 = rdf_objects.PathInfo.TSK(components=["bar"])
    self.db.WritePathInfos(client_id, [path_info_1, path_info_2])

    client_path_1 = db.ClientPath.OS(client_id, components=("foo",))
    client_path_1_history = db.ClientPathHistory()
    client_path_1_history.AddStatEntry(
        datetime("1999-01-01"), rdf_client_fs.StatEntry(st_mode=1337))

    client_path_2 = db.ClientPath.TSK(client_id, components=("bar",))
    client_path_2_history = db.ClientPathHistory()
    client_path_2_history.AddStatEntry(
        datetime("1988-01-01"), rdf_client_fs.StatEntry(st_mode=108))

    self.db.MultiWritePathHistory({
        client_path_1: client_path_1_history,
        client_path_2: client_path_2_history,
    })

    path_info = self.db.ReadPathInfo(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))
    self.assertEqual(path_info.stat_entry.st_mode, 1337)
    self.assertEqual(path_info.last_stat_entry_timestamp,
                     datetime("1999-01-01"))

    path_info = self.db.ReadPathInfo(
        client_id, rdf_objects.PathInfo.PathType.TSK, components=("bar",))
    self.assertEqual(path_info.stat_entry.st_mode, 108)
    self.assertEqual(path_info.last_stat_entry_timestamp,
                     datetime("1988-01-01"))

  def testMultiWriteHistoryTwoPaths(self):
    datetime = rdfvalue.RDFDatetime.FromHumanReadable

    client_id = self.InitializeClient()

    path_info_foo = rdf_objects.PathInfo.OS(components=["foo"])
    path_info_bar = rdf_objects.PathInfo.OS(components=["bar"])
    self.db.WritePathInfos(client_id, [path_info_foo, path_info_bar])

    client_path_foo = db.ClientPath.OS(client_id, components=("foo",))
    client_path_foo_history = db.ClientPathHistory()
    client_path_foo_history.AddHashEntry(
        datetime("2010-10-10"), rdf_crypto.Hash(md5=b"foo"))

    client_path_bar = db.ClientPath.OS(client_id, components=("bar",))
    client_path_bar_history = db.ClientPathHistory()
    client_path_bar_history.AddHashEntry(
        datetime("2011-11-11"), rdf_crypto.Hash(md5=b"bar"))

    self.db.MultiWritePathHistory({
        client_path_foo: client_path_foo_history,
        client_path_bar: client_path_bar_history,
    })

    path_info = self.db.ReadPathInfo(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))
    self.assertEqual(path_info.hash_entry.md5, b"foo")
    self.assertEqual(path_info.last_hash_entry_timestamp,
                     datetime("2010-10-10"))

    path_info = self.db.ReadPathInfo(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("bar",))
    self.assertEqual(path_info.hash_entry.md5, b"bar")
    self.assertEqual(path_info.last_hash_entry_timestamp,
                     datetime("2011-11-11"))

  def testMultiWriteHistoryTwoClients(self):
    datetime = rdfvalue.RDFDatetime.FromHumanReadable

    client_a_id = self.InitializeClient()
    client_b_id = self.InitializeClient()

    path_info = rdf_objects.PathInfo.OS(components=["foo"])
    self.db.WritePathInfos(client_a_id, [path_info])
    self.db.WritePathInfos(client_b_id, [path_info])

    client_a_path = db.ClientPath.OS(client_a_id, components=("foo",))
    client_a_history = db.ClientPathHistory()
    client_a_history.AddStatEntry(
        datetime("2001-01-01"), rdf_client_fs.StatEntry(st_size=42))

    client_b_path = db.ClientPath.OS(client_b_id, components=("foo",))
    client_b_history = db.ClientPathHistory()
    client_b_history.AddStatEntry(
        datetime("2002-02-02"), rdf_client_fs.StatEntry(st_size=108))

    self.db.MultiWritePathHistory({
        client_a_path: client_a_history,
        client_b_path: client_b_history,
    })

    path_info = self.db.ReadPathInfo(
        client_a_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))
    self.assertEqual(path_info.stat_entry.st_size, 42)

    path_info = self.db.ReadPathInfo(
        client_b_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))
    self.assertEqual(path_info.stat_entry.st_size, 108)

  def testMultiWriteHistoryDoesNotAllowOverridingStat(self):
    datetime = rdfvalue.RDFDatetime.FromHumanReadable

    client_id = self.InitializeClient()

    path_info = rdf_objects.PathInfo.OS(components=("foo", "bar", "baz"))
    self.db.WritePathInfos(client_id, [path_info])

    client_path = db.ClientPath.OS(client_id, components=("foo", "bar", "baz"))

    client_path_history = db.ClientPathHistory()
    client_path_history.AddStatEntry(
        datetime("2001-01-01"), rdf_client_fs.StatEntry(st_size=42))

    self.db.MultiWritePathHistory({client_path: client_path_history})

    client_path_history = db.ClientPathHistory()
    client_path_history.AddStatEntry(
        datetime("2001-01-01"), rdf_client_fs.StatEntry(st_size=108))

    with self.assertRaises(db.Error):
      self.db.MultiWritePathHistory({client_path: client_path_history})

  def testMultiWriteHistoryDoesNotAllowOverridingHash(self):
    datetime = rdfvalue.RDFDatetime.FromHumanReadable

    client_id = self.InitializeClient()

    path_info = rdf_objects.PathInfo.OS(components=("foo", "bar", "baz"))
    self.db.WritePathInfos(client_id, [path_info])

    client_path = db.ClientPath.OS(client_id, components=("foo", "bar", "baz"))

    client_path_history = db.ClientPathHistory()
    client_path_history.AddHashEntry(
        datetime("2002-02-02"), rdf_crypto.Hash(md5=b"quux"))

    self.db.MultiWritePathHistory({client_path: client_path_history})

    client_path_history = db.ClientPathHistory()
    client_path_history.AddHashEntry(
        datetime("2002-02-02"), rdf_crypto.Hash(md5=b"norf"))

    with self.assertRaises(db.Error):
      self.db.MultiWritePathHistory({client_path: client_path_history})

  def testMultiWriteHistoryRaisesOnNonExistingPathsForStat(self):
    datetime = rdfvalue.RDFDatetime.FromHumanReadable

    client_id = self.InitializeClient()
    client_path = db.ClientPath.OS(client_id, components=("foo", "bar", "baz"))
    client_path_history = db.ClientPathHistory()
    client_path_history.AddStatEntry(
        datetime("2001-01-01"), rdf_client_fs.StatEntry(st_size=42))

    with self.assertRaises(db.AtLeastOneUnknownPathError):
      self.db.MultiWritePathHistory({client_path: client_path_history})

  def testMultiWriteHistoryRaisesOnNonExistingPathForHash(self):
    datetime = rdfvalue.RDFDatetime.FromHumanReadable

    client_id = self.InitializeClient()
    client_path = db.ClientPath.OS(client_id, components=("foo", "bar", "baz"))
    client_path_history = db.ClientPathHistory()
    client_path_history.AddHashEntry(
        datetime("2001-01-01"), rdf_crypto.Hash(md5=b"quux"))

    with self.assertRaises(db.AtLeastOneUnknownPathError):
      self.db.MultiWritePathHistory({client_path: client_path_history})

  def testReadPathInfosNonExistent(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(client_id, [
        rdf_objects.PathInfo.OS(components=["foo", "bar"]),
    ])

    results = self.db.ReadPathInfos(client_id, rdf_objects.PathInfo.PathType.OS,
                                    [
                                        ("foo", "bar"),
                                        ("foo", "baz"),
                                        ("quux", "norf"),
                                    ])
    self.assertLen(results, 3)
    self.assertIsNotNone(results[("foo", "bar")])
    self.assertIsNone(results[("foo", "baz")])
    self.assertIsNone(results[("quux", "norf")])

  def testReadPathInfoValidatesTimestamp(self):
    client_id = self.InitializeClient()

    with self.assertRaises(TypeError):
      self.db.ReadPathInfo(
          client_id,
          rdf_objects.PathInfo.PathType.REGISTRY,
          components=("foo", "bar", "baz"),
          timestamp=rdfvalue.Duration("10s"))

  def testReadPathInfoNonExistent(self):
    client_id = self.InitializeClient()

    with self.assertRaises(db.UnknownPathError) as ctx:
      self.db.ReadPathInfo(
          client_id,
          rdf_objects.PathInfo.PathType.OS,
          components=("foo", "bar", "baz"))

    self.assertEqual(ctx.exception.client_id, client_id)
    self.assertEqual(ctx.exception.path_type, rdf_objects.PathInfo.PathType.OS)
    self.assertEqual(ctx.exception.components, ("foo", "bar", "baz"))

  def testReadPathInfoTimestampStatEntry(self):
    client_id = self.InitializeClient()

    pathspec = rdf_paths.PathSpec(
        path="foo/bar/baz", pathtype=rdf_paths.PathSpec.PathType.OS)

    stat_entry = rdf_client_fs.StatEntry(pathspec=pathspec, st_size=42)
    self.db.WritePathInfos(client_id,
                           [rdf_objects.PathInfo.FromStatEntry(stat_entry)])
    timestamp_1 = rdfvalue.RDFDatetime.Now()

    stat_entry = rdf_client_fs.StatEntry(pathspec=pathspec, st_size=101)
    self.db.WritePathInfos(client_id,
                           [rdf_objects.PathInfo.FromStatEntry(stat_entry)])
    timestamp_2 = rdfvalue.RDFDatetime.Now()

    stat_entry = rdf_client_fs.StatEntry(pathspec=pathspec, st_size=1337)
    self.db.WritePathInfos(client_id,
                           [rdf_objects.PathInfo.FromStatEntry(stat_entry)])
    timestamp_3 = rdfvalue.RDFDatetime.Now()

    path_info_last = self.db.ReadPathInfo(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo", "bar", "baz"))
    self.assertEqual(path_info_last.stat_entry.st_size, 1337)
    self.assertEqual(path_info_last.components, ["foo", "bar", "baz"])

    path_info_1 = self.db.ReadPathInfo(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo", "bar", "baz"),
        timestamp=timestamp_1)
    self.assertEqual(path_info_1.stat_entry.st_size, 42)
    self.assertEqual(path_info_last.components, ["foo", "bar", "baz"])

    path_info_2 = self.db.ReadPathInfo(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo", "bar", "baz"),
        timestamp=timestamp_2)
    self.assertEqual(path_info_2.stat_entry.st_size, 101)
    self.assertEqual(path_info_last.components, ["foo", "bar", "baz"])

    path_info_3 = self.db.ReadPathInfo(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo", "bar", "baz"),
        timestamp=timestamp_3)
    self.assertEqual(path_info_3.stat_entry.st_size, 1337)
    self.assertEqual(path_info_last.components, ["foo", "bar", "baz"])

  def testReadPathInfoTimestampHashEntry(self):
    client_id = self.InitializeClient()

    path_info = rdf_objects.PathInfo.OS(components=["foo"])

    path_info.hash_entry = rdf_crypto.Hash(md5=b"bar")
    self.db.WritePathInfos(client_id, [path_info])
    bar_timestamp = rdfvalue.RDFDatetime.Now()

    path_info.hash_entry = rdf_crypto.Hash(md5=b"baz")
    self.db.WritePathInfos(client_id, [path_info])
    baz_timestamp = rdfvalue.RDFDatetime.Now()

    path_info.hash_entry = rdf_crypto.Hash(md5=b"quux")
    self.db.WritePathInfos(client_id, [path_info])
    quux_timestamp = rdfvalue.RDFDatetime.Now()

    bar_path_info = self.db.ReadPathInfo(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo",),
        timestamp=bar_timestamp)
    self.assertEqual(bar_path_info.hash_entry.md5, b"bar")

    baz_path_info = self.db.ReadPathInfo(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo",),
        timestamp=baz_timestamp)
    self.assertEqual(baz_path_info.hash_entry.md5, b"baz")

    quux_path_info = self.db.ReadPathInfo(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo",),
        timestamp=quux_timestamp)
    self.assertEqual(quux_path_info.hash_entry.md5, b"quux")

  def testReadPathInfosMany(self):
    client_id = self.InitializeClient()

    path_info_1 = rdf_objects.PathInfo.OS(components=["foo", "bar"])
    path_info_1.stat_entry.st_mode = 42
    path_info_1.hash_entry.md5 = b"foobar"

    path_info_2 = rdf_objects.PathInfo.OS(components=["baz", "quux", "norf"])
    path_info_2.hash_entry.sha256 = b"bazquuxnorf"

    path_info_3 = rdf_objects.PathInfo.OS(components=["blargh"], directory=True)
    path_info_3.stat_entry.st_size = 1337

    self.db.WritePathInfos(client_id, [path_info_1, path_info_2, path_info_3])

    results = self.db.ReadPathInfos(client_id, rdf_objects.PathInfo.PathType.OS,
                                    [
                                        ("foo", "bar"),
                                        ("baz", "quux", "norf"),
                                        ("blargh",),
                                    ])
    result_path_info_1 = results[("foo", "bar")]
    self.assertEqual(result_path_info_1.components, ["foo", "bar"])
    self.assertEqual(result_path_info_1.stat_entry.st_mode, 42)
    self.assertEqual(result_path_info_1.hash_entry.md5, b"foobar")

    result_path_info_2 = results[("baz", "quux", "norf")]
    self.assertEqual(result_path_info_2.components, ["baz", "quux", "norf"])
    self.assertEqual(result_path_info_2.hash_entry.sha256, b"bazquuxnorf")

    result_path_info_3 = results[("blargh",)]
    self.assertEqual(result_path_info_3.components, ["blargh"])
    self.assertEqual(result_path_info_3.stat_entry.st_size, 1337)
    self.assertEqual(result_path_info_3.directory, True)

  def testReadPathInfoTimestampStatAndHashEntry(self):
    client_id = self.InitializeClient()

    path_info = rdf_objects.PathInfo.OS(components=["foo"])

    path_info.stat_entry = rdf_client_fs.StatEntry(st_mode=42)
    path_info.hash_entry = None
    self.db.WritePathInfos(client_id, [path_info])
    timestamp_1 = rdfvalue.RDFDatetime.Now()

    path_info.stat_entry = None
    path_info.hash_entry = rdf_crypto.Hash(md5=b"quux")
    self.db.WritePathInfos(client_id, [path_info])
    timestamp_2 = rdfvalue.RDFDatetime.Now()

    path_info.stat_entry = rdf_client_fs.StatEntry(st_mode=1337)
    path_info.hash_entry = None
    self.db.WritePathInfos(client_id, [path_info])
    timestamp_3 = rdfvalue.RDFDatetime.Now()

    path_info.stat_entry = rdf_client_fs.StatEntry(st_mode=4815162342)
    path_info.hash_entry = rdf_crypto.Hash(md5=b"norf")
    self.db.WritePathInfos(client_id, [path_info])
    timestamp_4 = rdfvalue.RDFDatetime.Now()

    path_info_1 = self.db.ReadPathInfo(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo",),
        timestamp=timestamp_1)
    self.assertEqual(path_info_1.stat_entry.st_mode, 42)
    self.assertFalse(path_info_1.HasField("hash_entry"))

    path_info_2 = self.db.ReadPathInfo(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo",),
        timestamp=timestamp_2)
    self.assertEqual(path_info_2.stat_entry.st_mode, 42)
    self.assertEqual(path_info_2.hash_entry.md5, b"quux")

    path_info_3 = self.db.ReadPathInfo(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo",),
        timestamp=timestamp_3)
    self.assertEqual(path_info_3.stat_entry.st_mode, 1337)
    self.assertEqual(path_info_3.hash_entry.md5, b"quux")

    path_info_4 = self.db.ReadPathInfo(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo",),
        timestamp=timestamp_4)
    self.assertEqual(path_info_4.stat_entry.st_mode, 4815162342)
    self.assertEqual(path_info_4.hash_entry.md5, b"norf")

  def testReadPathInfoOlder(self):
    client_id = self.InitializeClient()

    path_info = rdf_objects.PathInfo.OS(components=["foo"])
    path_info.stat_entry.st_mode = 42
    path_info.hash_entry.md5 = b"foo"
    self.db.WritePathInfos(client_id, [path_info])

    path_info = rdf_objects.PathInfo.OS(components=["bar"])
    path_info.stat_entry.st_mode = 1337
    path_info.hash_entry.md5 = b"bar"
    self.db.WritePathInfos(client_id, [path_info])

    path_info = self.db.ReadPathInfo(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))
    self.assertEqual(path_info.stat_entry.st_mode, 42)
    self.assertEqual(path_info.hash_entry.md5, b"foo")

    path_info = self.db.ReadPathInfo(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("bar",))
    self.assertEqual(path_info.stat_entry.st_mode, 1337)
    self.assertEqual(path_info.hash_entry.md5, b"bar")

  def testListDescendentPathInfosEmptyResult(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(client_id,
                           [rdf_objects.PathInfo.OS(components=["foo"])])

    results = self.db.ListDescendentPathInfos(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))

    self.assertEmpty(results)

  def testListDescendentPathInfosSingleResult(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(client_id, [
        rdf_objects.PathInfo.OS(components=["foo", "bar"]),
    ])

    results = self.db.ListDescendentPathInfos(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))

    self.assertLen(results, 1)
    self.assertEqual(results[0].components, ("foo", "bar"))

  def testListDescendentPathInfosSingle(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(client_id, [
        rdf_objects.PathInfo.OS(components=["foo", "bar", "baz", "quux"]),
    ])

    results = self.db.ListDescendentPathInfos(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))

    self.assertLen(results, 3)
    self.assertEqual(results[0].components, ("foo", "bar"))
    self.assertEqual(results[1].components, ("foo", "bar", "baz"))
    self.assertEqual(results[2].components, ("foo", "bar", "baz", "quux"))

  def testListDescendentPathInfosBranching(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(client_id, [
        rdf_objects.PathInfo.OS(components=["foo", "bar", "quux"]),
        rdf_objects.PathInfo.OS(components=["foo", "baz"]),
    ])

    results = self.db.ListDescendentPathInfos(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))

    self.assertLen(results, 3)
    self.assertEqual(results[0].components, ("foo", "bar"))
    self.assertEqual(results[1].components, ("foo", "bar", "quux"))
    self.assertEqual(results[2].components, ("foo", "baz"))

  def testListDescendentPathInfosLimited(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(client_id, [
        rdf_objects.PathInfo.OS(components=["foo", "bar", "baz", "quux"]),
        rdf_objects.PathInfo.OS(components=["foo", "bar", "blargh"]),
        rdf_objects.PathInfo.OS(components=["foo", "norf", "thud", "plugh"]),
    ])

    results = self.db.ListDescendentPathInfos(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo",),
        max_depth=2)

    components = [tuple(path_info.components) for path_info in results]

    self.assertIn(("foo", "bar"), components)
    self.assertIn(("foo", "bar", "baz"), components)
    self.assertIn(("foo", "bar", "blargh"), components)

    self.assertNotIn(("foo", "bar", "baz", "quux"), components)
    self.assertNotIn(("foo", "norf", "thud", "plugh"), components)

  def testListDescendentPathInfosTypeSeparated(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(client_id, [
        rdf_objects.PathInfo.OS(components=["usr", "bin", "javac"]),
        rdf_objects.PathInfo.TSK(components=["usr", "bin", "gdb"]),
    ])

    os_results = self.db.ListDescendentPathInfos(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("usr", "bin"))
    self.assertLen(os_results, 1)
    self.assertEqual(os_results[0].components, ("usr", "bin", "javac"))

    tsk_results = self.db.ListDescendentPathInfos(
        client_id, rdf_objects.PathInfo.PathType.TSK, components=("usr", "bin"))
    self.assertLen(tsk_results, 1)
    self.assertEqual(tsk_results[0].components, ("usr", "bin", "gdb"))

  def testListDescendentPathInfosAll(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(client_id, [
        rdf_objects.PathInfo.OS(components=["foo", "bar"]),
        rdf_objects.PathInfo.OS(components=["baz", "quux"]),
    ])

    results = self.db.ListDescendentPathInfos(
        client_id, rdf_objects.PathInfo.PathType.OS, components=())

    self.assertEqual(results[0].components, ("baz",))
    self.assertEqual(results[1].components, ("baz", "quux"))
    self.assertEqual(results[2].components, ("foo",))
    self.assertEqual(results[3].components, ("foo", "bar"))

  def testListDescendentPathInfosLimitedDirectory(self):
    client_id = self.InitializeClient()

    path_info_1 = rdf_objects.PathInfo.OS(components=["foo", "bar", "baz"])
    path_info_1.stat_entry.st_mode = 108

    path_info_2 = rdf_objects.PathInfo.OS(components=["foo", "bar"])
    path_info_2.stat_entry.st_mode = 1337

    path_info_3 = rdf_objects.PathInfo.OS(components=["foo", "norf", "quux"])
    path_info_3.stat_entry.st_mode = 707

    self.db.WritePathInfos(client_id, [path_info_1, path_info_2, path_info_3])

    results = self.db.ListDescendentPathInfos(
        client_id, rdf_objects.PathInfo.PathType.OS, components=(), max_depth=2)

    self.assertLen(results, 3)
    self.assertEqual(results[0].components, ("foo",))
    self.assertEqual(results[1].components, ("foo", "bar"))
    self.assertEqual(results[2].components, ("foo", "norf"))
    self.assertEqual(results[1].stat_entry.st_mode, 1337)

  def testListDescendentPathInfosTimestampNow(self):
    client_id = self.InitializeClient()

    path_info = rdf_objects.PathInfo.OS(components=["foo", "bar", "baz"])
    path_info.stat_entry.st_size = 1337
    self.db.WritePathInfos(client_id, [path_info])

    results = self.db.ListDescendentPathInfos(
        client_id=client_id,
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=(),
        timestamp=rdfvalue.RDFDatetime.Now())

    self.assertLen(results, 3)
    self.assertEqual(results[0].components, ("foo",))
    self.assertEqual(results[1].components, ("foo", "bar"))
    self.assertEqual(results[2].components, ("foo", "bar", "baz"))
    self.assertEqual(results[2].stat_entry.st_size, 1337)

  def testListDescendentPathInfosTimestampMultiple(self):
    client_id = self.InitializeClient()

    timestamp_0 = rdfvalue.RDFDatetime.Now()

    path_info_1 = rdf_objects.PathInfo.OS(components=["foo", "bar", "baz"])
    path_info_1.stat_entry.st_size = 1
    self.db.WritePathInfos(client_id, [path_info_1])
    timestamp_1 = rdfvalue.RDFDatetime.Now()

    path_info_2 = rdf_objects.PathInfo.OS(components=["foo", "quux", "norf"])
    path_info_2.stat_entry.st_size = 2
    self.db.WritePathInfos(client_id, [path_info_2])
    timestamp_2 = rdfvalue.RDFDatetime.Now()

    path_info_3 = rdf_objects.PathInfo.OS(components=["foo", "quux", "thud"])
    path_info_3.stat_entry.st_size = 3
    self.db.WritePathInfos(client_id, [path_info_3])
    timestamp_3 = rdfvalue.RDFDatetime.Now()

    results_0 = self.db.ListDescendentPathInfos(
        client_id=client_id,
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=(),
        timestamp=timestamp_0)
    self.assertEmpty(results_0)

    results_1 = self.db.ListDescendentPathInfos(
        client_id=client_id,
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=(),
        timestamp=timestamp_1)
    self.assertLen(results_1, 3)
    self.assertEqual(results_1[0].components, ("foo",))
    self.assertEqual(results_1[1].components, ("foo", "bar"))
    self.assertEqual(results_1[2].components, ("foo", "bar", "baz"))

    results_2 = self.db.ListDescendentPathInfos(
        client_id=client_id,
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=(),
        timestamp=timestamp_2)
    self.assertLen(results_2, 5)
    self.assertEqual(results_2[0].components, ("foo",))
    self.assertEqual(results_2[1].components, ("foo", "bar"))
    self.assertEqual(results_2[2].components, ("foo", "bar", "baz"))
    self.assertEqual(results_2[3].components, ("foo", "quux"))
    self.assertEqual(results_2[4].components, ("foo", "quux", "norf"))

    results_3 = self.db.ListDescendentPathInfos(
        client_id=client_id,
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=(),
        timestamp=timestamp_3)
    self.assertLen(results_3, 6)
    self.assertEqual(results_3[0].components, ("foo",))
    self.assertEqual(results_3[1].components, ("foo", "bar"))
    self.assertEqual(results_3[2].components, ("foo", "bar", "baz"))
    self.assertEqual(results_3[3].components, ("foo", "quux"))
    self.assertEqual(results_3[4].components, ("foo", "quux", "norf"))
    self.assertEqual(results_3[5].components, ("foo", "quux", "thud"))

  def testListDescendentPathInfosTimestampStatValue(self):
    client_id = self.InitializeClient()

    timestamp_0 = rdfvalue.RDFDatetime.Now()

    path_info = rdf_objects.PathInfo.OS(components=("foo", "bar"))

    path_info.stat_entry.st_size = 1337
    self.db.WritePathInfos(client_id, [path_info])
    timestamp_1 = rdfvalue.RDFDatetime.Now()

    path_info.stat_entry.st_size = 42
    self.db.WritePathInfos(client_id, [path_info])
    timestamp_2 = rdfvalue.RDFDatetime.Now()

    results_0 = self.db.ListDescendentPathInfos(
        client_id=client_id,
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=("foo",),
        timestamp=timestamp_0)
    self.assertEmpty(results_0)

    results_1 = self.db.ListDescendentPathInfos(
        client_id=client_id,
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=("foo",),
        timestamp=timestamp_1)
    self.assertLen(results_1, 1)
    self.assertEqual(results_1[0].components, ("foo", "bar"))
    self.assertEqual(results_1[0].stat_entry.st_size, 1337)

    results_2 = self.db.ListDescendentPathInfos(
        client_id=client_id,
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=("foo",),
        timestamp=timestamp_2)
    self.assertLen(results_2, 1)
    self.assertEqual(results_2[0].components, ("foo", "bar"))
    self.assertEqual(results_2[0].stat_entry.st_size, 42)

  def testListDescendentPathInfosTimestampHashValue(self):
    client_id = self.InitializeClient()

    timestamp_0 = rdfvalue.RDFDatetime.Now()

    path_info = rdf_objects.PathInfo.OS(components=("foo",))

    path_info.hash_entry.md5 = b"quux"
    self.db.WritePathInfos(client_id, [path_info])
    timestamp_1 = rdfvalue.RDFDatetime.Now()

    path_info.hash_entry.md5 = b"norf"
    self.db.WritePathInfos(client_id, [path_info])
    timestamp_2 = rdfvalue.RDFDatetime.Now()

    results_0 = self.db.ListDescendentPathInfos(
        client_id=client_id,
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=(),
        timestamp=timestamp_0)
    self.assertEmpty(results_0)

    results_1 = self.db.ListDescendentPathInfos(
        client_id=client_id,
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=(),
        timestamp=timestamp_1)
    self.assertLen(results_1, 1)
    self.assertEqual(results_1[0].components, ("foo",))
    self.assertEqual(results_1[0].hash_entry.md5, b"quux")

    results_2 = self.db.ListDescendentPathInfos(
        client_id=client_id,
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=(),
        timestamp=timestamp_2)
    self.assertLen(results_2, 1)
    self.assertEqual(results_2[0].components, ("foo",))
    self.assertEqual(results_2[0].hash_entry.md5, b"norf")

  def testListChildPathInfosRoot(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(client_id, [
        rdf_objects.PathInfo.OS(components=["foo", "bar"]),
        rdf_objects.PathInfo.OS(components=["foo", "baz"]),
        rdf_objects.PathInfo.OS(components=["quux", "norf"]),
    ])

    results = self.db.ListChildPathInfos(
        client_id, rdf_objects.PathInfo.PathType.OS, components=())

    self.assertEqual(results[0].components, ("foo",))
    self.assertTrue(results[0].directory)
    self.assertEqual(results[1].components, ("quux",))
    self.assertTrue(results[1].directory)

  def testListChildPathInfosRootDeeper(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(client_id, [
        rdf_objects.PathInfo.OS(components=("foo", "bar", "baz")),
        rdf_objects.PathInfo.OS(components=("foo", "bar", "quux")),
        rdf_objects.PathInfo.OS(components=("foo", "bar", "norf", "thud")),
    ])

    results = self.db.ListChildPathInfos(
        client_id, rdf_objects.PathInfo.PathType.OS, components=())

    self.assertLen(results, 1)
    self.assertEqual(results[0].components, ("foo",))
    self.assertTrue(results[0].directory)

  def testListChildPathInfosDetails(self):
    client_id = self.InitializeClient()

    path_info = rdf_objects.PathInfo.OS(components=["foo", "bar"])
    path_info.stat_entry.st_size = 42
    self.db.WritePathInfos(client_id, [path_info])

    path_info = rdf_objects.PathInfo.OS(components=["foo", "baz"])
    path_info.hash_entry.md5 = b"quux"
    self.db.WritePathInfos(client_id, [path_info])

    results = self.db.ListChildPathInfos(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))
    self.assertEqual(results[0].components, ("foo", "bar"))
    self.assertEqual(results[0].stat_entry.st_size, 42)
    self.assertEqual(results[1].components, ("foo", "baz"))
    self.assertEqual(results[1].hash_entry.md5, b"quux")

  def testListChildPathInfosDeepSorted(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(client_id, [
        rdf_objects.PathInfo.OS(components=["foo", "bar", "baz", "quux"]),
        rdf_objects.PathInfo.OS(components=["foo", "bar", "baz", "norf"]),
        rdf_objects.PathInfo.OS(components=["foo", "bar", "baz", "thud"]),
    ])

    results = self.db.ListChildPathInfos(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo", "bar", "baz"))
    self.assertEqual(results[0].components, ("foo", "bar", "baz", "norf"))
    self.assertEqual(results[1].components, ("foo", "bar", "baz", "quux"))
    self.assertEqual(results[2].components, ("foo", "bar", "baz", "thud"))

  def testListChildPathInfosTimestamp(self):
    client_id = self.InitializeClient()

    timestamp_0 = rdfvalue.RDFDatetime.Now()

    path_info_1 = rdf_objects.PathInfo.OS(components=("foo", "bar"))
    path_info_1.stat_entry.st_size = 1
    self.db.WritePathInfos(client_id, [path_info_1])
    timestamp_1 = rdfvalue.RDFDatetime.Now()

    path_info_2 = rdf_objects.PathInfo.OS(components=("foo", "baz"))
    path_info_2.stat_entry.st_size = 2
    self.db.WritePathInfos(client_id, [path_info_2])
    timestamp_2 = rdfvalue.RDFDatetime.Now()

    results_0 = self.db.ListChildPathInfos(
        client_id=client_id,
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=("foo",),
        timestamp=timestamp_0)
    self.assertEmpty(results_0)

    results_1 = self.db.ListChildPathInfos(
        client_id=client_id,
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=("foo",),
        timestamp=timestamp_1)
    self.assertLen(results_1, 1)
    self.assertEqual(results_1[0].components, ("foo", "bar"))
    self.assertEqual(results_1[0].stat_entry.st_size, 1)

    results_2 = self.db.ListChildPathInfos(
        client_id=client_id,
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=("foo",),
        timestamp=timestamp_2)
    self.assertLen(results_2, 2)
    self.assertEqual(results_2[0].components, ("foo", "bar"))
    self.assertEqual(results_2[0].stat_entry.st_size, 1)
    self.assertEqual(results_2[1].components, ("foo", "baz"))
    self.assertEqual(results_2[1].stat_entry.st_size, 2)

  def testListChildPathInfosTimestampStatAndHashValue(self):
    client_id = self.InitializeClient()

    path_info = rdf_objects.PathInfo.OS(components=("foo", "bar", "baz"))
    path_info.stat_entry.st_size = 42
    path_info.hash_entry.sha256 = b"quux"
    self.db.WritePathInfos(client_id, [path_info])
    timestamp_1 = rdfvalue.RDFDatetime.Now()

    path_info = rdf_objects.PathInfo.OS(components=("foo", "bar", "baz"))
    path_info.stat_entry.st_size = 108
    path_info.hash_entry.sha256 = b"norf"
    self.db.WritePathInfos(client_id, [path_info])
    timestamp_2 = rdfvalue.RDFDatetime.Now()

    path_info = rdf_objects.PathInfo.OS(components=("foo", "bar", "baz"))
    path_info.stat_entry.st_size = 1337
    path_info.hash_entry.sha256 = b"thud"
    self.db.WritePathInfos(client_id, [path_info])
    timestamp_3 = rdfvalue.RDFDatetime.Now()

    results_1 = self.db.ListChildPathInfos(
        client_id=client_id,
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=("foo", "bar"),
        timestamp=timestamp_1)
    self.assertLen(results_1, 1)
    self.assertEqual(results_1[0].components, ("foo", "bar", "baz"))
    self.assertEqual(results_1[0].stat_entry.st_size, 42)
    self.assertEqual(results_1[0].hash_entry.sha256, b"quux")

    results_2 = self.db.ListChildPathInfos(
        client_id=client_id,
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=("foo", "bar"),
        timestamp=timestamp_2)
    self.assertLen(results_2, 1)
    self.assertEqual(results_2[0].components, ("foo", "bar", "baz"))
    self.assertEqual(results_2[0].stat_entry.st_size, 108)
    self.assertEqual(results_2[0].hash_entry.sha256, b"norf")

    results_3 = self.db.ListChildPathInfos(
        client_id=client_id,
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=("foo", "bar"),
        timestamp=timestamp_3)
    self.assertLen(results_3, 1)
    self.assertEqual(results_3[0].components, ("foo", "bar", "baz"))
    self.assertEqual(results_3[0].stat_entry.st_size, 1337)
    self.assertEqual(results_3[0].hash_entry.sha256, b"thud")

  def testReadPathInfosHistoriesEmpty(self):
    client_id = self.InitializeClient()
    result = self.db.ReadPathInfosHistories(
        client_id, rdf_objects.PathInfo.PathType.OS, [])
    self.assertEqual(result, {})

  def testReadPathInfosHistoriesDoesNotRaiseOnUnknownClient(self):
    results = self.db.ReadPathInfosHistories(
        "C.FFFF111122223333", rdf_objects.PathInfo.PathType.OS, [("foo",)])

    self.assertEqual(results[("foo",)], [])

  def testReadPathInfosHistoriesWithSingleFileWithSingleHistoryItem(self):
    datetime = rdfvalue.RDFDatetime.FromHumanReadable

    client_id = self.InitializeClient()

    path_info = rdf_objects.PathInfo.OS(components=["foo"])
    self.db.WritePathInfos(client_id, [path_info])

    client_path = db.ClientPath.OS(client_id, components=("foo",))
    client_path_history = db.ClientPathHistory()
    client_path_history.AddStatEntry(
        datetime("2000-01-01"), rdf_client_fs.StatEntry(st_size=42))
    client_path_history.AddHashEntry(
        datetime("2000-01-01"), rdf_crypto.Hash(md5=b"quux"))

    self.db.MultiWritePathHistory({client_path: client_path_history})

    path_infos = self.db.ReadPathInfosHistories(
        client_id, rdf_objects.PathInfo.PathType.OS, [("foo",)])
    self.assertLen(path_infos, 1)

    pi = path_infos[("foo",)]
    self.assertLen(pi, 1)
    self.assertEqual(pi[0].stat_entry.st_size, 42)
    self.assertEqual(pi[0].hash_entry.md5, b"quux")
    self.assertEqual(pi[0].timestamp, datetime("2000-01-01"))

  def testReadPathInfosHistoriesWithTwoFilesWithSingleHistoryItemEach(self):
    datetime = rdfvalue.RDFDatetime.FromHumanReadable

    client_id = self.InitializeClient()

    path_info_1 = rdf_objects.PathInfo.OS(components=["foo"])
    path_info_2 = rdf_objects.PathInfo.OS(components=["bar"])
    self.db.WritePathInfos(client_id, [path_info_1, path_info_2])

    client_path_1 = db.ClientPath.OS(client_id, components=("foo",))
    client_path_1_history = db.ClientPathHistory()
    client_path_1_history.AddStatEntry(
        datetime("1999-01-01"), rdf_client_fs.StatEntry(st_mode=1337))

    client_path_2 = db.ClientPath.OS(client_id, components=("bar",))
    client_path_2_history = db.ClientPathHistory()
    client_path_2_history.AddHashEntry(
        datetime("1988-01-01"), rdf_crypto.Hash(md5=b"quux"))

    self.db.MultiWritePathHistory({
        client_path_1: client_path_1_history,
        client_path_2: client_path_2_history,
    })

    path_infos = self.db.ReadPathInfosHistories(
        client_id, rdf_objects.PathInfo.PathType.OS, [("foo",), ("bar",)])
    self.assertLen(path_infos, 2)

    pi = path_infos[("bar",)]
    self.assertLen(pi, 1)

    self.assertEqual(pi[0].components, ("bar",))
    self.assertEqual(pi[0].hash_entry.md5, b"quux")
    self.assertEqual(pi[0].timestamp, datetime("1988-01-01"))

    pi = path_infos[("foo",)]
    self.assertLen(pi, 1)

    self.assertEqual(pi[0].components, ("foo",))
    self.assertEqual(pi[0].stat_entry.st_mode, 1337)
    self.assertEqual(pi[0].timestamp, datetime("1999-01-01"))

  def testReadPathInfosHistoriesWithTwoFilesWithTwoHistoryItems(self):
    datetime = rdfvalue.RDFDatetime.FromHumanReadable

    client_id = self.InitializeClient()

    path_info_1 = rdf_objects.PathInfo.OS(components=["foo"])
    path_info_2 = rdf_objects.PathInfo.OS(components=["bar"])
    self.db.WritePathInfos(client_id, [path_info_1, path_info_2])

    client_path_1 = db.ClientPath.OS(client_id, components=("foo",))
    client_path_1_history = db.ClientPathHistory()
    client_path_1_history.AddStatEntry(
        datetime("1999-01-01"), rdf_client_fs.StatEntry(st_mode=1337))
    client_path_1_history.AddStatEntry(
        datetime("1999-01-02"), rdf_client_fs.StatEntry(st_mode=1338))

    client_path_2 = db.ClientPath.OS(client_id, components=("bar",))
    client_path_2_history = db.ClientPathHistory()
    client_path_2_history.AddStatEntry(
        datetime("1988-01-01"), rdf_client_fs.StatEntry(st_mode=109))
    client_path_2_history.AddStatEntry(
        datetime("1988-01-02"), rdf_client_fs.StatEntry(st_mode=110))

    self.db.MultiWritePathHistory({
        client_path_1: client_path_1_history,
        client_path_2: client_path_2_history,
    })

    path_infos = self.db.ReadPathInfosHistories(
        client_id, rdf_objects.PathInfo.PathType.OS, [("foo",), ("bar",)])
    self.assertLen(path_infos, 2)

    pi = path_infos[("bar",)]
    self.assertLen(pi, 2)

    self.assertEqual(pi[0].components, ("bar",))
    self.assertEqual(pi[0].stat_entry.st_mode, 109)
    self.assertEqual(pi[0].timestamp, datetime("1988-01-01"))

    self.assertEqual(pi[1].components, ("bar",))
    self.assertEqual(pi[1].stat_entry.st_mode, 110)
    self.assertEqual(pi[1].timestamp, datetime("1988-01-02"))

    pi = path_infos[("foo",)]
    self.assertLen(pi, 2)

    self.assertEqual(pi[0].components, ("foo",))
    self.assertEqual(pi[0].stat_entry.st_mode, 1337)
    self.assertEqual(pi[0].timestamp, datetime("1999-01-01"))

    self.assertEqual(pi[1].components, ("foo",))
    self.assertEqual(pi[1].stat_entry.st_mode, 1338)
    self.assertEqual(pi[1].timestamp, datetime("1999-01-02"))

  def testInitPathInfosValidatesClient(self):
    client_id = "C.4815162342108ABC"

    with self.assertRaises(db.UnknownClientError) as ctx:
      path_info = rdf_objects.PathInfo.OS(components=(), directory=True)
      self.db.InitPathInfos(client_id, [path_info])

    self.assertEqual(ctx.exception.client_id, client_id)

  def testInitPathInfosEmpty(self):
    client_id = self.InitializeClient()

    self.db.InitPathInfos(client_id, [])

    for path_type in itervalues(rdf_objects.PathInfo.PathType.enum_dict):
      path_infos = self.db.ListDescendentPathInfos(client_id, path_type, ())
      self.assertEqual(path_infos, [])

  def testInitPathInfosWriteSingle(self):
    client_id = self.InitializeClient()

    path_info = rdf_objects.PathInfo.OS(components=("foo",), directory=True)
    self.db.InitPathInfos(client_id, [path_info])

    path_info = self.db.ReadPathInfo(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))
    self.assertEqual(path_info.components, ("foo",))
    self.assertTrue(path_info.directory)

  def testInitPathInfosWriteMany(self):
    client_id = self.InitializeClient()

    path_info_1 = rdf_objects.PathInfo.OS(components=("foo",), directory=False)
    path_info_2 = rdf_objects.PathInfo.OS(components=("bar",), directory=True)
    self.db.InitPathInfos(client_id, [path_info_1, path_info_2])

    path_info = self.db.ReadPathInfo(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))
    self.assertEqual(path_info.components, ("foo",))
    self.assertFalse(path_info.directory)

    path_info = self.db.ReadPathInfo(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("bar",))
    self.assertEqual(path_info.components, ("bar",))
    self.assertTrue(path_info.directory)

  def testInitPathInfosTree(self):
    client_id = self.InitializeClient()

    path_info = rdf_objects.PathInfo.OS(components=("foo", "bar", "baz"))
    self.db.InitPathInfos(client_id, [path_info])

    path_info = self.db.ReadPathInfo(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))
    self.assertEqual(path_info.components, ("foo",))
    self.assertTrue(path_info.directory)

    path_info = self.db.ReadPathInfo(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo", "bar"))
    self.assertEqual(path_info.components, ("foo", "bar"))
    self.assertTrue(path_info.directory)

    path_info = self.db.ReadPathInfo(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo", "bar", "baz"))
    self.assertEqual(path_info.components, ("foo", "bar", "baz"))
    self.assertFalse(path_info.directory)

  def testInitPathInfosClearsStatHistory(self):
    datetime = rdfvalue.RDFDatetime.FromHumanReadable

    client_id = self.InitializeClient()

    path_info = rdf_objects.PathInfo.OS(components=("foo",))
    self.db.WritePathInfos(client_id, [path_info])

    client_path = db.ClientPath.OS(client_id, components=("foo",))
    self.db.WritePathStatHistory(
        client_path, {
            datetime("2001-01-01"): rdf_client_fs.StatEntry(st_size=42),
            datetime("2002-02-02"): rdf_client_fs.StatEntry(st_size=108),
            datetime("2003-03-03"): rdf_client_fs.StatEntry(st_size=1337),
        })

    self.db.InitPathInfos(client_id, [path_info])

    history = self.db.ReadPathInfoHistory(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))
    self.assertEqual(history, [])

  def testInitPathInfosClearsHashHistory(self):
    datetime = rdfvalue.RDFDatetime.FromHumanReadable

    client_id = self.InitializeClient()

    path_info = rdf_objects.PathInfo.OS(components=("foo",))
    self.db.WritePathInfos(client_id, [path_info])

    client_path = db.ClientPath.OS(client_id, components=("foo",))
    self.db.WritePathHashHistory(
        client_path, {
            datetime("2011-01-01"): rdf_crypto.Hash(md5=b"quux"),
            datetime("2012-02-02"): rdf_crypto.Hash(md5=b"norf"),
            datetime("2013-03-03"): rdf_crypto.Hash(md5=b"thud"),
        })

    self.db.InitPathInfos(client_id, [path_info])

    history = self.db.ReadPathInfoHistory(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))
    self.assertEqual(history, [])

  def testInitPathInfosRetainsIndirectPathHistory(self):
    datetime = rdfvalue.RDFDatetime.FromHumanReadable

    client_id = self.InitializeClient()

    path_info = rdf_objects.PathInfo.OS(components=("foo", "bar"))
    self.db.WritePathInfos(client_id, [path_info])

    client_parent_path = db.ClientPath.OS(client_id, components=("foo",))
    self.db.WritePathStatHistory(
        client_parent_path, {
            datetime("2015-05-05"): rdf_client_fs.StatEntry(st_mode=1337),
            datetime("2016-06-06"): rdf_client_fs.StatEntry(st_mode=8888),
        })
    self.db.WritePathHashHistory(
        client_parent_path, {
            datetime("2016-06-06"): rdf_crypto.Hash(sha256=b"quux"),
            datetime("2017-07-07"): rdf_crypto.Hash(sha256=b"norf"),
        })

    self.db.InitPathInfos(client_id, [path_info])

    history = self.db.ReadPathInfoHistory(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))

    self.assertEqual(history[0].timestamp, datetime("2015-05-05"))
    self.assertEqual(history[0].stat_entry.st_mode, 1337)

    self.assertEqual(history[1].timestamp, datetime("2016-06-06"))
    self.assertEqual(history[1].stat_entry.st_mode, 8888)
    self.assertEqual(history[1].hash_entry.sha256, b"quux")

    self.assertEqual(history[2].timestamp, datetime("2017-07-07"))
    self.assertEqual(history[2].hash_entry.sha256, b"norf")

    parent_path_info = rdf_objects.PathInfo.OS(components=("foo",))
    self.db.InitPathInfos(client_id, [parent_path_info])

    history = self.db.ReadPathInfoHistory(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))
    self.assertEqual(history, [])

  def testMultiInitPathInfos(self):
    datetime = rdfvalue.RDFDatetime.FromHumanReadable

    client_a_id = self.InitializeClient()
    client_b_id = self.InitializeClient()

    path_info_a = rdf_objects.PathInfo.OS(components=("foo",))
    self.db.WritePathInfos(client_a_id, [path_info_a])

    client_path_a = db.ClientPath.OS(client_a_id, components=("foo",))
    self.db.WritePathStatHistory(
        client_path_a, {
            datetime("2000-01-01"): rdf_client_fs.StatEntry(st_size=1),
            datetime("2000-02-02"): rdf_client_fs.StatEntry(st_size=2),
        })

    path_info_b = rdf_objects.PathInfo.OS(components=("foo",))
    self.db.WritePathInfos(client_b_id, [path_info_b])

    client_path_b = db.ClientPath.OS(client_b_id, components=("foo",))
    self.db.WritePathHashHistory(
        client_path_b, {
            datetime("2001-01-01"): rdf_crypto.Hash(md5=b"quux"),
            datetime("2001-02-02"): rdf_crypto.Hash(md5=b"norf"),
        })

    path_info_a.stat_entry.st_mode = 1337
    path_info_b.hash_entry.sha256 = b"thud"
    self.db.MultiInitPathInfos({
        client_a_id: [path_info_a],
        client_b_id: [path_info_b],
    })

    history_a = self.db.ReadPathInfoHistory(
        client_a_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))
    self.assertLen(history_a, 1)
    self.assertEqual(history_a[0].stat_entry.st_mode, 1337)
    self.assertFalse(history_a[0].stat_entry.st_size)

    history_b = self.db.ReadPathInfoHistory(
        client_b_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))
    self.assertLen(history_b, 1)
    self.assertEqual(history_b[0].hash_entry.sha256, b"thud")
    self.assertFalse(history_b[0].hash_entry.md5)

  def testMultiInitPathInfosEmptyDoesNotThrow(self):
    self.db.MultiInitPathInfos({})

  def testMultiInitPathInfosNoPathsDoesNotThrow(self):
    client_a_id = self.InitializeClient()
    client_b_id = self.InitializeClient()

    self.db.MultiInitPathInfos({
        client_a_id: [],
        client_b_id: [],
    })

  def testClearPathHistoryEmpty(self):
    client_id = self.InitializeClient()

    path_info = rdf_objects.PathInfo.OS(components=("foo", "bar", "baz"))
    path_info.stat_entry.st_size = 42
    path_info.hash_entry.md5 = b"quux"
    self.db.WritePathInfos(client_id, [path_info])

    self.db.ClearPathHistory(client_id, [])

    history = self.db.ReadPathInfoHistory(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo", "bar", "baz"))
    self.assertLen(history, 1)
    self.assertEqual(history[0].stat_entry.st_size, 42)
    self.assertEqual(history[0].hash_entry.md5, b"quux")

  def testClearPathHistorySingle(self):
    client_id = self.InitializeClient()

    path_info_1 = rdf_objects.PathInfo.OS(components=("foo", "bar"))
    path_info_1.stat_entry.st_size = 42
    path_info_1.hash_entry.md5 = b"quux"

    path_info_2 = rdf_objects.PathInfo.OS(components=("foo", "baz"))
    path_info_2.stat_entry.st_size = 108
    path_info_2.hash_entry.md5 = b"norf"

    self.db.WritePathInfos(client_id, [path_info_1, path_info_2])

    self.db.ClearPathHistory(client_id, [path_info_1])

    history = self.db.ReadPathInfoHistory(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo", "bar"))
    self.assertEmpty(history)

    history = self.db.ReadPathInfoHistory(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo", "baz"))
    self.assertLen(history, 1)
    self.assertEqual(history[0].stat_entry.st_size, 108)
    self.assertEqual(history[0].hash_entry.md5, b"norf")

  def testClearPathHistoryManyRecords(self):
    datetime = rdfvalue.RDFDatetime.FromHumanReadable

    client_id = self.InitializeClient()

    path_info = rdf_objects.PathInfo.OS(components=("foo", "bar", "baz"))
    self.db.WritePathInfos(client_id, [path_info])

    client_path = db.ClientPath.OS(client_id, components=("foo", "bar", "baz"))
    self.db.WritePathStatHistory(
        client_path, {
            datetime("2001-01-01"): rdf_client_fs.StatEntry(st_size=42),
            datetime("2002-02-02"): rdf_client_fs.StatEntry(st_mode=1337),
            datetime("2003-03-03"): rdf_client_fs.StatEntry(st_size=108),
        })
    self.db.WritePathHashHistory(
        client_path, {
            datetime("2003-03-03"): rdf_crypto.Hash(md5=b"quux"),
            datetime("2004-04-04"): rdf_crypto.Hash(md5=b"norf"),
            datetime("2005-05-05"): rdf_crypto.Hash(md5=b"thud"),
        })

    self.db.ClearPathHistory(client_id, [path_info])

    history = self.db.ReadPathInfoHistory(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo", "bar", "baz"))
    self.assertEmpty(history)

  def testClearPathHistoryOnlyDirect(self):
    client_id = self.InitializeClient()

    path_info_1 = rdf_objects.PathInfo.OS(components=("foo",))
    path_info_1.stat_entry.st_size = 1

    path_info_2 = rdf_objects.PathInfo.OS(components=("foo", "bar"))
    path_info_2.stat_entry.st_size = 2

    path_info_3 = rdf_objects.PathInfo.OS(components=("foo", "bar", "baz"))
    path_info_3.stat_entry.st_size = 3

    self.db.WritePathInfos(client_id, [path_info_1, path_info_2, path_info_3])

    self.db.ClearPathHistory(client_id, [path_info_2])

    history_1 = self.db.ReadPathInfoHistory(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))
    self.assertLen(history_1, 1)
    self.assertEqual(history_1[0].stat_entry.st_size, 1)

    history_2 = self.db.ReadPathInfoHistory(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo", "bar"))
    self.assertEmpty(history_2)

    history_3 = self.db.ReadPathInfoHistory(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo", "bar", "baz"))
    self.assertLen(history_3, 1)
    self.assertEqual(history_3[0].stat_entry.st_size, 3)

  def testMultiClearPathHistoryEmptyDoesNotRaise(self):
    self.db.MultiClearPathHistory({})

  def testMultiClearPathHistoryNoPathsDoesNotRaise(self):
    client_a_id = self.InitializeClient()
    client_b_id = self.InitializeClient()

    path_info = rdf_objects.PathInfo.OS(components=("foo", "bar"))
    path_info.stat_entry.st_size = 42
    self.db.WritePathInfos(client_a_id, [path_info])

    path_info = rdf_objects.PathInfo.OS(components=("foo", "baz"))
    path_info.hash_entry.md5 = b"quux"
    self.db.WritePathInfos(client_b_id, [path_info])

    self.db.MultiClearPathHistory({
        client_a_id: [],
        client_b_id: [],
    })

    history_a = self.db.ReadPathInfoHistory(
        client_a_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo", "bar"))
    self.assertLen(history_a, 1)
    self.assertEqual(history_a[0].stat_entry.st_size, 42)

    history_b = self.db.ReadPathInfoHistory(
        client_b_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo", "baz"))
    self.assertLen(history_b, 1)
    self.assertEqual(history_b[0].hash_entry.md5, b"quux")

    self.db.MultiClearPathHistory({
        client_a_id: [],
        client_b_id: [path_info],
    })

    history_a = self.db.ReadPathInfoHistory(
        client_a_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo", "bar"))
    self.assertLen(history_a, 1)
    self.assertEqual(history_a[0].stat_entry.st_size, 42)

    history_b = self.db.ReadPathInfoHistory(
        client_b_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo", "baz"))
    self.assertEmpty(history_b)

  def testMultiClearPathHistoryClearsMultipleHistories(self):
    datetime = rdfvalue.RDFDatetime.FromHumanReadable

    client_a_id = self.InitializeClient()
    client_b_id = self.InitializeClient()

    path_info_a = rdf_objects.PathInfo.OS(components=("foo", "bar"))
    path_info_a.stat_entry.st_mode = 1337
    self.db.WritePathInfos(client_a_id, [path_info_a])

    path_info_b_1 = rdf_objects.PathInfo.TSK(components=("foo", "baz"))
    self.db.WritePathInfos(client_b_id, [path_info_b_1])

    client_path_b_1 = db.ClientPath.TSK(client_b_id, components=("foo", "baz"))
    self.db.WritePathHashHistory(
        client_path_b_1, {
            datetime("2001-01-01"): rdf_crypto.Hash(md5=b"quux"),
            datetime("2002-02-02"): rdf_crypto.Hash(md5=b"norf"),
            datetime("2003-03-03"): rdf_crypto.Hash(sha256=b"thud"),
        })

    path_info_b_2 = rdf_objects.PathInfo.OS(components=("foo", "baz"))
    self.db.WritePathInfos(client_b_id, [path_info_b_2])

    client_path_b_2 = db.ClientPath.OS(client_b_id, components=("foo", "baz"))
    self.db.WritePathStatHistory(
        client_path_b_2, {
            datetime("2001-02-02"): rdf_client_fs.StatEntry(st_size=2),
            datetime("2003-03-03"): rdf_client_fs.StatEntry(st_size=3),
            datetime("2005-05-05"): rdf_client_fs.StatEntry(st_size=5),
            datetime("2007-07-07"): rdf_client_fs.StatEntry(st_size=7),
        })

    self.db.MultiClearPathHistory({
        client_a_id: [path_info_a],
        client_b_id: [path_info_b_1, path_info_b_2],
    })

    history_a = self.db.ReadPathInfoHistory(
        client_a_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo", "bar"))
    self.assertEmpty(history_a)

    history_b_1 = self.db.ReadPathInfoHistory(
        client_b_id,
        rdf_objects.PathInfo.PathType.TSK,
        components=("foo", "baz"))
    self.assertEmpty(history_b_1)

    history_b_2 = self.db.ReadPathInfoHistory(
        client_b_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo", "baz"))
    self.assertEmpty(history_b_2)

  def _WriteBlobReferences(self):
    blob_ref_1 = rdf_objects.BlobReference(
        offset=0, size=42, blob_id=rdf_objects.BlobID(b"01234567" * 4))
    blob_ref_2 = rdf_objects.BlobReference(
        offset=42, size=42, blob_id=rdf_objects.BlobID(b"01234568" * 4))
    hash_id_1 = rdf_objects.SHA256HashID(b"0a1b2c3d" * 4)
    hash_id_2 = rdf_objects.SHA256HashID(b"0a1b2c3e" * 4)
    data = {
        hash_id_1: [blob_ref_1],
        hash_id_2: [blob_ref_1, blob_ref_2],
    }
    self.db.WriteHashBlobReferences(data)

    return hash_id_1, hash_id_2

  def testReadLatestPathInfosReturnsNothingForNonExistingPaths(self):
    client_a_id = self.InitializeClient()
    client_b_id = self.InitializeClient()

    path_1 = db.ClientPath.OS(client_a_id, components=("foo", "baz"))
    path_2 = db.ClientPath.TSK(client_b_id, components=("foo", "baz"))

    results = self.db.ReadLatestPathInfosWithHashBlobReferences(
        [path_1, path_2])
    self.assertEqual(results, {path_1: None, path_2: None})

  def testReadLatestPathInfosReturnsNothingWhenNoFilesCollected(self):
    client_a_id = self.InitializeClient()
    client_b_id = self.InitializeClient()

    path_info_1 = rdf_objects.PathInfo.OS(components=("foo", "bar"))
    self.db.WritePathInfos(client_a_id, [path_info_1])
    path_info_2 = rdf_objects.PathInfo.TSK(components=("foo", "baz"))
    self.db.WritePathInfos(client_b_id, [path_info_2])

    path_1 = db.ClientPath.OS(client_a_id, components=("foo", "bar"))
    path_2 = db.ClientPath.TSK(client_b_id, components=("foo", "baz"))

    results = self.db.ReadLatestPathInfosWithHashBlobReferences(
        [path_1, path_2])
    self.assertEqual(results, {path_1: None, path_2: None})

  def testReadLatestPathInfosFindsTwoCollectedFilesWhenTheyAreTheOnlyEntries(
      self):
    client_a_id = self.InitializeClient()
    client_b_id = self.InitializeClient()
    hash_id_1, hash_id_2 = self._WriteBlobReferences()

    path_info_1 = rdf_objects.PathInfo.OS(components=("foo", "bar"))
    path_info_1.hash_entry.sha256 = hash_id_1.AsBytes()
    self.db.WritePathInfos(client_a_id, [path_info_1])
    path_info_2 = rdf_objects.PathInfo.TSK(components=("foo", "baz"))
    path_info_2.hash_entry.sha256 = hash_id_2.AsBytes()
    self.db.WritePathInfos(client_b_id, [path_info_2])

    path_1 = db.ClientPath.OS(client_a_id, components=("foo", "bar"))
    path_2 = db.ClientPath.TSK(client_b_id, components=("foo", "baz"))

    results = self.db.ReadLatestPathInfosWithHashBlobReferences(
        [path_1, path_2])
    self.assertCountEqual(results.keys(), [path_1, path_2])
    self.assertEqual(results[path_1].hash_entry, path_info_1.hash_entry)
    self.assertEqual(results[path_2].hash_entry, path_info_2.hash_entry)
    self.assertTrue(results[path_1].timestamp)
    self.assertTrue(results[path_2].timestamp)

  def testReadLatestPathInfosCorrectlyFindsCollectedFileWithNonLatestEntry(
      self):
    client_id = self.InitializeClient()
    hash_id, _ = self._WriteBlobReferences()

    path_info_1 = rdf_objects.PathInfo.OS(components=("foo", "bar"))
    path_info_1.hash_entry.sha256 = hash_id.AsBytes()
    self.db.WritePathInfos(client_id, [path_info_1])

    path_info_2 = rdf_objects.PathInfo.OS(components=("foo", "bar"))
    self.db.WritePathInfos(client_id, [path_info_2])

    path = db.ClientPath.OS(client_id, components=("foo", "bar"))
    results = self.db.ReadLatestPathInfosWithHashBlobReferences([path])

    self.assertCountEqual(results.keys(), [path])
    self.assertEqual(results[path].hash_entry, path_info_1.hash_entry)
    self.assertTrue(results[path].timestamp)

  def testReadLatestPathInfosCorrectlyFindsLatestOfTwoCollectedFiles(self):
    client_id = self.InitializeClient()
    hash_id_1, hash_id_2 = self._WriteBlobReferences()

    path_info_1 = rdf_objects.PathInfo.OS(components=("foo", "bar"))
    path_info_1.hash_entry.sha256 = hash_id_1.AsBytes()
    self.db.WritePathInfos(client_id, [path_info_1])

    path_info_2 = rdf_objects.PathInfo.OS(components=("foo", "bar"))
    path_info_2.hash_entry.sha256 = hash_id_2.AsBytes()
    self.db.WritePathInfos(client_id, [path_info_2])

    path = db.ClientPath.OS(client_id, components=("foo", "bar"))
    results = self.db.ReadLatestPathInfosWithHashBlobReferences([path])
    self.assertCountEqual(results.keys(), [path])
    self.assertEqual(results[path].hash_entry, path_info_2.hash_entry)
    self.assertTrue(results[path].timestamp)

  def testReadLatestPathInfosCorrectlyFindsLatestCollectedFileBeforeTimestamp(
      self):
    client_id = self.InitializeClient()
    hash_id_1, hash_id_2 = self._WriteBlobReferences()

    path_info_1 = rdf_objects.PathInfo.OS(components=("foo", "bar"))
    path_info_1.hash_entry.sha256 = hash_id_1.AsBytes()
    self.db.WritePathInfos(client_id, [path_info_1])

    time_checkpoint = rdfvalue.RDFDatetime.Now()

    path_info_2 = rdf_objects.PathInfo.OS(components=("foo", "bar"))
    path_info_2.hash_entry.sha256 = hash_id_2.AsBytes()
    self.db.WritePathInfos(client_id, [path_info_2])

    path = db.ClientPath.OS(client_id, components=("foo", "bar"))
    results = self.db.ReadLatestPathInfosWithHashBlobReferences(
        [path], max_timestamp=time_checkpoint)
    self.assertCountEqual(results.keys(), [path])
    self.assertEqual(results[path].hash_entry, path_info_1.hash_entry)
    self.assertTrue(results[path].timestamp)

  def testReadLatestPathInfosIncludesStatEntryIfThereIsOneWithSameTimestamp(
      self):
    client_id = self.InitializeClient()
    hash_id, _ = self._WriteBlobReferences()

    path_info = rdf_objects.PathInfo.OS(components=("foo", "bar"))
    path_info.stat_entry = rdf_client_fs.StatEntry(st_mode=42)
    path_info.hash_entry.sha256 = hash_id.AsBytes()
    self.db.WritePathInfos(client_id, [path_info])

    path = db.ClientPath.OS(client_id, components=("foo", "bar"))
    results = self.db.ReadLatestPathInfosWithHashBlobReferences([path])

    self.assertCountEqual(results.keys(), [path])
    self.assertEqual(results[path].stat_entry, path_info.stat_entry)
    self.assertEqual(results[path].hash_entry, path_info.hash_entry)
    self.assertTrue(results[path].timestamp)
