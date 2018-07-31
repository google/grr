#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

import hashlib

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
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

    self.db.WritePathInfos(
        client_id, [rdf_objects.PathInfo.OS(components=["foo"])])

    result = self.db.ReadPathInfo(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))
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

    stat_entry = rdf_client.StatEntry()
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

    stat_entry = rdf_client.StatEntry(st_mode=1337)
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

    self.db.WritePathInfos(
        client_id, [
            rdf_objects.PathInfo.OS(components=["foo", "bar", "baz"]),
        ])

    results = self.db.ReadPathInfos(client_id, rdf_objects.PathInfo.PathType.OS,
                                    [
                                        ("foo",),
                                        ("foo", "bar"),
                                        ("foo", "bar", "baz"),
                                    ])

    self.assertEqual(len(results), 3)

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
    self.assertEqual(len(os_results), 1)
    self.assertTrue(os_results[("foo",)].directory)

    tsk_results = self.db.ReadPathInfos(
        client_id, rdf_objects.PathInfo.PathType.TSK, [("foo",)])
    self.assertEqual(len(tsk_results), 1)
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
    self.db.WritePathInfos(
        client_id, [
            rdf_objects.PathInfo.OS(components=["foo", "bar"]),
        ])

    results = self.db.ReadPathInfos(client_id, rdf_objects.PathInfo.PathType.OS,
                                    [("foo",)])

    self.assertEqual(len(results), 1)
    self.assertTrue(results[("foo",)].directory)

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

    results = self.db.ReadPathInfos(client_id, rdf_objects.PathInfo.PathType.OS,
                                    [("foo", "bar")])
    self.assertEqual(len(results), 1)

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
    self.db.WritePathHashHistory(client_id, path_info, hash_entries)

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
    self.db.MultiWritePathHistory(client_id, {}, {})  # Should not rise.

  def testMultiWriteHistoryStatAndHash(self):
    client_id = self.InitializeClient()

    path_info = rdf_objects.PathInfo.OS(components=["foo"])
    path_info.timestamp = rdfvalue.RDFDatetime.FromHumanReadable("2000-01-01")

    self.db.WritePathInfos(client_id, [path_info])

    stat_entries = {path_info: rdf_client.StatEntry(st_size=42)}
    hash_entries = {path_info: rdf_crypto.Hash(md5=b"quux")}

    self.db.MultiWritePathHistory(client_id, stat_entries, hash_entries)

    result_path_info = self.db.ReadPathInfo(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))
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

    path_info = self.db.ReadPathInfo(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))
    self.assertEqual(path_info.stat_entry.st_mode, 1337)
    self.assertEqual(path_info.last_stat_entry_timestamp,
                     rdfvalue.RDFDatetime.FromHumanReadable("1999-01-01"))

    path_info = self.db.ReadPathInfo(
        client_id, rdf_objects.PathInfo.PathType.TSK, components=("bar",))
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

    path_info = self.db.ReadPathInfo(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))
    self.assertEqual(path_info.hash_entry.md5, b"foo")
    self.assertEqual(path_info.last_hash_entry_timestamp,
                     rdfvalue.RDFDatetime.FromHumanReadable("2010-10-10"))

    path_info = self.db.ReadPathInfo(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("bar",))
    self.assertEqual(path_info.hash_entry.md5, b"bar")
    self.assertEqual(path_info.last_hash_entry_timestamp,
                     rdfvalue.RDFDatetime.FromHumanReadable("2011-11-11"))

  def testMultiWriteHistoryDoesNotAllowOverridingStat(self):
    datetime = rdfvalue.RDFDatetime.FromHumanReadable

    client_id = self.InitializeClient()

    path_info = rdf_objects.PathInfo.OS(components=("foo", "bar", "baz"))
    self.db.WritePathInfos(client_id, path_info)

    path_info.timestamp = datetime("2001-01-01")
    stat_entry = rdf_client.StatEntry(st_size=42)
    self.db.MultiWritePathHistory(client_id, {path_info: stat_entry}, {})

    with self.assertRaises(db.Error):
      stat_entry = rdf_client.StatEntry(st_size=108)
      self.db.MultiWritePathHistory(client_id, {path_info: stat_entry}, {})

  def testMultiWriteHistoryDoesNotAllowOverridingHash(self):
    datetime = rdfvalue.RDFDatetime.FromHumanReadable

    client_id = self.InitializeClient()

    path_info = rdf_objects.PathInfo.OS(components=("foo", "bar", "baz"))
    self.db.WritePathInfos(client_id, path_info)

    path_info.timestamp = datetime("2002-02-02")
    hash_entry = rdf_crypto.Hash(md5=b"quux")
    self.db.MultiWritePathHistory(client_id, {}, {path_info: hash_entry})

    with self.assertRaises(db.Error):
      hash_entry = rdf_crypto.Hash(sha256=b"norf")
      self.db.MultiWritePathHistory(client_id, {}, {path_info: hash_entry})

  def testReadPathInfosNonExistent(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(
        client_id, [
            rdf_objects.PathInfo.OS(components=["foo", "bar"]),
        ])

    results = self.db.ReadPathInfos(client_id, rdf_objects.PathInfo.PathType.OS,
                                    [
                                        ("foo", "bar"),
                                        ("foo", "baz"),
                                        ("quux", "norf"),
                                    ])
    self.assertEqual(len(results), 3)
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

    self.db.WritePathInfos(
        client_id, [rdf_objects.PathInfo.OS(components=["foo"])])

    results = self.db.ListDescendentPathInfos(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))

    self.assertEqual(len(results), 0)

  def testListDescendentPathInfosSingleResult(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(
        client_id, [
            rdf_objects.PathInfo.OS(components=["foo", "bar"]),
        ])

    results = self.db.ListDescendentPathInfos(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))

    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].components, ("foo", "bar"))

  def testListDescendentPathInfosSingle(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(
        client_id, [
            rdf_objects.PathInfo.OS(components=["foo", "bar", "baz", "quux"]),
        ])

    results = self.db.ListDescendentPathInfos(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))

    self.assertEqual(len(results), 3)
    self.assertEqual(results[0].components, ("foo", "bar"))
    self.assertEqual(results[1].components, ("foo", "bar", "baz"))
    self.assertEqual(results[2].components, ("foo", "bar", "baz", "quux"))

  def testListDescendentPathInfosBranching(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(
        client_id, [
            rdf_objects.PathInfo.OS(components=["foo", "bar", "quux"]),
            rdf_objects.PathInfo.OS(components=["foo", "baz"]),
        ])

    results = self.db.ListDescendentPathInfos(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))

    self.assertEqual(len(results), 3)
    self.assertEqual(results[0].components, ("foo", "bar"))
    self.assertEqual(results[1].components, ("foo", "bar", "quux"))
    self.assertEqual(results[2].components, ("foo", "baz"))

  def testListDescendentPathInfosLimited(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(
        client_id, [
            rdf_objects.PathInfo.OS(components=["foo", "bar", "baz", "quux"]),
            rdf_objects.PathInfo.OS(components=["foo", "bar", "blargh"]),
            rdf_objects.PathInfo.OS(
                components=["foo", "norf", "thud", "plugh"]),
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

    self.db.WritePathInfos(
        client_id, [
            rdf_objects.PathInfo.OS(components=["usr", "bin", "javac"]),
            rdf_objects.PathInfo.TSK(components=["usr", "bin", "gdb"]),
        ])

    os_results = self.db.ListDescendentPathInfos(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("usr", "bin"))
    self.assertEqual(len(os_results), 1)
    self.assertEqual(os_results[0].components, ("usr", "bin", "javac"))

    tsk_results = self.db.ListDescendentPathInfos(
        client_id, rdf_objects.PathInfo.PathType.TSK, components=("usr", "bin"))
    self.assertEqual(len(tsk_results), 1)
    self.assertEqual(tsk_results[0].components, ("usr", "bin", "gdb"))

  def testListDescendentPathInfosAll(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(
        client_id, [
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

    self.assertEqual(len(results), 3)
    self.assertEqual(results[0].components, ("foo",))
    self.assertEqual(results[1].components, ("foo", "bar"))
    self.assertEqual(results[2].components, ("foo", "norf"))
    self.assertEqual(results[1].stat_entry.st_mode, 1337)

  def testListChildPathInfosRoot(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(
        client_id, [
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

    self.db.WritePathInfos(
        client_id, [
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
    client_id = self.InitializeClient()

    path_info = rdf_objects.PathInfo.OS(components=["foo"])
    path_info.timestamp = rdfvalue.RDFDatetime.FromHumanReadable("2000-01-01")

    self.db.WritePathInfos(client_id, [path_info])

    stat_entries = {path_info: rdf_client.StatEntry(st_size=42)}
    hash_entries = {path_info: rdf_crypto.Hash(md5=b"quux")}

    self.db.MultiWritePathHistory(client_id, stat_entries, hash_entries)

    path_infos = self.db.ReadPathInfosHistories(
        client_id, rdf_objects.PathInfo.PathType.OS, [("foo",)])
    self.assertEqual(len(path_infos), 1)

    pi = path_infos[("foo",)]
    self.assertEqual(len(pi), 1)
    self.assertEqual(pi[0].stat_entry.st_size, 42)
    self.assertEqual(pi[0].hash_entry.md5, b"quux")
    self.assertEqual(pi[0].timestamp,
                     rdfvalue.RDFDatetime.FromHumanReadable("2000-01-01"))

  def testReadPathInfosHistoriesWithTwoFilesWithSingleHistoryItemEach(self):
    client_id = self.InitializeClient()

    path_info_1 = rdf_objects.PathInfo.OS(components=["foo"])
    path_info_1.timestamp = rdfvalue.RDFDatetime.FromHumanReadable("1999-01-01")

    path_info_2 = rdf_objects.PathInfo.OS(components=["bar"])
    path_info_2.timestamp = rdfvalue.RDFDatetime.FromHumanReadable("1988-01-01")

    self.db.WritePathInfos(client_id, [path_info_1, path_info_2])

    stat_entries = {
        path_info_1: rdf_client.StatEntry(st_mode=1337),
    }
    hash_entries = {path_info_2: rdf_crypto.Hash(md5=b"quux")}
    self.db.MultiWritePathHistory(client_id, stat_entries, hash_entries)

    path_infos = self.db.ReadPathInfosHistories(
        client_id, rdf_objects.PathInfo.PathType.OS, [("foo",), ("bar",)])
    self.assertEqual(len(path_infos), 2)

    pi = path_infos[("bar",)]
    self.assertEqual(len(pi), 1)

    self.assertEqual(pi[0].components, ("bar",))
    self.assertEqual(pi[0].hash_entry.md5, b"quux")
    self.assertEqual(pi[0].timestamp,
                     rdfvalue.RDFDatetime.FromHumanReadable("1988-01-01"))

    pi = path_infos[("foo",)]
    self.assertEqual(len(pi), 1)

    self.assertEqual(pi[0].components, ("foo",))
    self.assertEqual(pi[0].stat_entry.st_mode, 1337)
    self.assertEqual(pi[0].timestamp,
                     rdfvalue.RDFDatetime.FromHumanReadable("1999-01-01"))

  def testReatPathInfosHistoriesWithTwoFilesWithTwoHistoryItems(self):
    client_id = self.InitializeClient()

    path_info_1_a = rdf_objects.PathInfo.OS(components=["foo"])
    path_info_1_a.timestamp = rdfvalue.RDFDatetime.FromHumanReadable(
        "1999-01-01")

    path_info_1_b = rdf_objects.PathInfo.OS(components=["foo"])
    path_info_1_b.timestamp = rdfvalue.RDFDatetime.FromHumanReadable(
        "1999-01-02")

    path_info_2_a = rdf_objects.PathInfo.OS(components=["bar"])
    path_info_2_a.timestamp = rdfvalue.RDFDatetime.FromHumanReadable(
        "1988-01-01")

    path_info_2_b = rdf_objects.PathInfo.OS(components=["bar"])
    path_info_2_b.timestamp = rdfvalue.RDFDatetime.FromHumanReadable(
        "1988-01-02")

    self.db.WritePathInfos(client_id, [path_info_1_a, path_info_2_a])

    stat_entries = {
        path_info_1_a: rdf_client.StatEntry(st_mode=1337),
        path_info_1_b: rdf_client.StatEntry(st_mode=1338),
        path_info_2_a: rdf_client.StatEntry(st_mode=109),
        path_info_2_b: rdf_client.StatEntry(st_mode=110),
    }
    self.db.MultiWritePathHistory(client_id, stat_entries, {})

    path_infos = self.db.ReadPathInfosHistories(
        client_id, rdf_objects.PathInfo.PathType.OS, [("foo",), ("bar",)])
    self.assertEqual(len(path_infos), 2)

    pi = path_infos[("bar",)]
    self.assertEqual(len(pi), 2)

    self.assertEqual(pi[0].components, ("bar",))
    self.assertEqual(pi[0].stat_entry.st_mode, 109)
    self.assertEqual(pi[0].timestamp,
                     rdfvalue.RDFDatetime.FromHumanReadable("1988-01-01"))

    self.assertEqual(pi[1].components, ("bar",))
    self.assertEqual(pi[1].stat_entry.st_mode, 110)
    self.assertEqual(pi[1].timestamp,
                     rdfvalue.RDFDatetime.FromHumanReadable("1988-01-02"))

    pi = path_infos[("foo",)]
    self.assertEqual(len(pi), 2)

    self.assertEqual(pi[0].components, ("foo",))
    self.assertEqual(pi[0].stat_entry.st_mode, 1337)
    self.assertEqual(pi[0].timestamp,
                     rdfvalue.RDFDatetime.FromHumanReadable("1999-01-01"))

    self.assertEqual(pi[1].components, ("foo",))
    self.assertEqual(pi[1].stat_entry.st_mode, 1338)
    self.assertEqual(pi[1].timestamp,
                     rdfvalue.RDFDatetime.FromHumanReadable("1999-01-02"))
