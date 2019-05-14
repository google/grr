#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import hashlib

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server.databases import db
from grr_response_server.databases import db_test_utils
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
    client_id = db_test_utils.InitializeClient(self.db)

    with self.assertRaises(ValueError):
      self.db.WritePathInfos(client_id, [
          rdf_objects.PathInfo.OS(components=["foo", "bar"], directory=False),
          rdf_objects.PathInfo.OS(components=["foo", "bar"], directory=True),
      ])

  def testWritePathInfosMetadata(self):
    client_id = db_test_utils.InitializeClient(self.db)

    self.db.WritePathInfos(
        client_id,
        [rdf_objects.PathInfo.TSK(components=["foo", "bar"], directory=True)])

    results = self.db.ReadPathInfos(client_id,
                                    rdf_objects.PathInfo.PathType.TSK,
                                    [("foo", "bar")])

    result_path_info = results[("foo", "bar")]
    self.assertEqual(result_path_info.path_type,
                     rdf_objects.PathInfo.PathType.TSK)
    self.assertEqual(result_path_info.components, ["foo", "bar"])
    self.assertEqual(result_path_info.directory, True)

  def testWritePathInfosMetadataTimestampUpdate(self):
    now = rdfvalue.RDFDatetime.Now

    client_id = db_test_utils.InitializeClient(self.db)

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

    hash_entry = rdf_crypto.Hash(sha256=b"foo")
    self.db.WritePathInfos(
        client_id,
        [rdf_objects.PathInfo.OS(components=["foo"], hash_entry=hash_entry)])

    result = self.db.ReadPathInfo(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))
    self.assertEqual(result.components, ["foo"])
    self.assertEqual(result.hash_entry.sha256, b"foo")
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
    self.assertEqual(result.hash_entry.sha256, b"foo")
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
    client_id = db_test_utils.InitializeClient(self.db)

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
    client_id = db_test_utils.InitializeClient(self.db)

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

  def testWritePathInfosValidatesHashEntry(self):
    client_id = db_test_utils.InitializeClient(self.db)

    hash_entry = rdf_crypto.Hash()
    hash_entry.md5 = hashlib.md5("foo").digest()
    hash_entry.sha1 = hashlib.sha1("bar").digest()

    path_info = rdf_objects.PathInfo.OS(
        components=("foo", "bar", "baz"), hash_entry=hash_entry)

    with self.assertRaises(ValueError):
      self.db.WritePathInfos(client_id, [path_info])

  def testWriteMultiplePathInfosHashEntry(self):
    client_id = db_test_utils.InitializeClient(self.db)

    names = ["asd", "Qwe", "foo", "bar", "baz"]
    path_infos = []
    for name in names:
      hash_entry = rdf_crypto.Hash()
      hash_entry.sha256 = hashlib.sha256(name).digest()
      hash_entry.md5 = hashlib.md5(name).digest()
      hash_entry.num_bytes = len(name)

      path_infos.append(
          rdf_objects.PathInfo.OS(
              components=["foo", "bar", "baz", name], hash_entry=hash_entry))

    self.db.WritePathInfos(client_id, path_infos)

    for name in names:
      result = self.db.ReadPathInfo(
          client_id,
          rdf_objects.PathInfo.PathType.OS,
          components=("foo", "bar", "baz", name))

      self.assertEqual(result.components, ["foo", "bar", "baz", name])
      self.assertTrue(result.HasField("hash_entry"))
      self.assertFalse(result.HasField("stat_entry"))
      self.assertEqual(result.hash_entry.sha256, hashlib.sha256(name).digest())
      self.assertEqual(result.hash_entry.md5, hashlib.md5(name).digest())
      self.assertEqual(result.hash_entry.num_bytes, len(name))

  def testWritePathInfosHashAndStatEntry(self):
    client_id = db_test_utils.InitializeClient(self.db)

    stat_entry = rdf_client_fs.StatEntry(st_mode=1337)
    hash_entry = rdf_crypto.Hash(sha256=hashlib.sha256("foo").digest())

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
    client_id = db_test_utils.InitializeClient(self.db)

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
    client_id = db_test_utils.InitializeClient(self.db)

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
    client_id = db_test_utils.InitializeClient(self.db)

    self.db.WritePathInfos(client_id, [
        rdf_objects.PathInfo.OS(components=["foo"], directory=True),
        rdf_objects.PathInfo.TSK(components=["foo"], directory=False),
    ])

    os_results = self.db.ReadPathInfos(client_id,
                                       rdf_objects.PathInfo.PathType.OS,
                                       [("foo",)])
    self.assertLen(os_results, 1)
    self.assertTrue(os_results[("foo",)].directory)

    tsk_results = self.db.ReadPathInfos(client_id,
                                        rdf_objects.PathInfo.PathType.TSK,
                                        [("foo",)])
    self.assertLen(tsk_results, 1)
    self.assertFalse(tsk_results[("foo",)].directory)

  def testWritePathInfosUpdates(self):
    client_id = db_test_utils.InitializeClient(self.db)

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
    client_id = db_test_utils.InitializeClient(self.db)

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
    client_id = db_test_utils.InitializeClient(self.db)

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
    client_id = db_test_utils.InitializeClient(self.db)

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
    client_a_id = db_test_utils.InitializeClient(self.db)
    client_b_id = db_test_utils.InitializeClient(self.db)

    path_info_a_1 = rdf_objects.PathInfo.OS(components=["foo", "bar"])
    path_info_a_1.stat_entry.st_size = 42

    path_info_a_2 = rdf_objects.PathInfo.OS(components=["foo", "baz"])
    path_info_a_2.hash_entry.md5 = b"aaa"
    path_info_a_2.hash_entry.sha256 = b"ccc"

    path_info_b_1 = rdf_objects.PathInfo.TSK(components=["norf", "thud"])
    path_info_b_1.hash_entry.sha1 = b"ddd"
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
    self.assertEqual(path_infos_a[("foo", "baz")].hash_entry.sha256, b"ccc")

    path_infos_b = self.db.ReadPathInfos(client_b_id,
                                         rdf_objects.PathInfo.PathType.TSK, [
                                             ("norf", "thud"),
                                             ("quux", "blargh"),
                                         ])
    self.assertEqual(path_infos_b[("norf", "thud")].hash_entry.sha1, b"ddd")
    self.assertEqual(path_infos_b[("norf", "thud")].hash_entry.sha256, b"bbb")
    self.assertEqual(path_infos_b[("quux", "blargh")].stat_entry.st_mode, 1337)

  def testReadPathInfosEmptyComponentsList(self):
    client_id = db_test_utils.InitializeClient(self.db)
    results = self.db.ReadPathInfos(client_id, rdf_objects.PathInfo.PathType.OS,
                                    [])
    self.assertEqual(results, {})

  def testReadPathInfosNonExistent(self):
    client_id = db_test_utils.InitializeClient(self.db)

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
    client_id = db_test_utils.InitializeClient(self.db)

    with self.assertRaises(TypeError):
      self.db.ReadPathInfo(
          client_id,
          rdf_objects.PathInfo.PathType.REGISTRY,
          components=("foo", "bar", "baz"),
          timestamp=rdfvalue.Duration("10s"))

  def testReadPathInfoNonExistent(self):
    client_id = db_test_utils.InitializeClient(self.db)

    with self.assertRaises(db.UnknownPathError) as ctx:
      self.db.ReadPathInfo(
          client_id,
          rdf_objects.PathInfo.PathType.OS,
          components=("foo", "bar", "baz"))

    self.assertEqual(ctx.exception.client_id, client_id)
    self.assertEqual(ctx.exception.path_type, rdf_objects.PathInfo.PathType.OS)
    self.assertEqual(ctx.exception.components, ("foo", "bar", "baz"))

  def testReadPathInfoTimestampStatEntry(self):
    client_id = db_test_utils.InitializeClient(self.db)

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
    client_id = db_test_utils.InitializeClient(self.db)

    path_info = rdf_objects.PathInfo.OS(components=["foo"])

    path_info.hash_entry = rdf_crypto.Hash(sha256=b"bar")
    self.db.WritePathInfos(client_id, [path_info])
    bar_timestamp = rdfvalue.RDFDatetime.Now()

    path_info.hash_entry = rdf_crypto.Hash(sha256=b"baz")
    self.db.WritePathInfos(client_id, [path_info])
    baz_timestamp = rdfvalue.RDFDatetime.Now()

    path_info.hash_entry = rdf_crypto.Hash(sha256=b"quux")
    self.db.WritePathInfos(client_id, [path_info])
    quux_timestamp = rdfvalue.RDFDatetime.Now()

    bar_path_info = self.db.ReadPathInfo(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo",),
        timestamp=bar_timestamp)
    self.assertEqual(bar_path_info.hash_entry.sha256, b"bar")

    baz_path_info = self.db.ReadPathInfo(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo",),
        timestamp=baz_timestamp)
    self.assertEqual(baz_path_info.hash_entry.sha256, b"baz")

    quux_path_info = self.db.ReadPathInfo(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo",),
        timestamp=quux_timestamp)
    self.assertEqual(quux_path_info.hash_entry.sha256, b"quux")

  def testReadPathInfosMany(self):
    client_id = db_test_utils.InitializeClient(self.db)

    path_info_1 = rdf_objects.PathInfo.OS(components=["foo", "bar"])
    path_info_1.stat_entry.st_mode = 42
    path_info_1.hash_entry.md5 = b"foo"
    path_info_1.hash_entry.sha256 = b"bar"

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
    self.assertEqual(result_path_info_1.hash_entry.md5, b"foo")
    self.assertEqual(result_path_info_1.hash_entry.sha256, b"bar")

    result_path_info_2 = results[("baz", "quux", "norf")]
    self.assertEqual(result_path_info_2.components, ["baz", "quux", "norf"])
    self.assertEqual(result_path_info_2.hash_entry.sha256, b"bazquuxnorf")

    result_path_info_3 = results[("blargh",)]
    self.assertEqual(result_path_info_3.components, ["blargh"])
    self.assertEqual(result_path_info_3.stat_entry.st_size, 1337)
    self.assertEqual(result_path_info_3.directory, True)

  def testReadPathInfoTimestampStatAndHashEntry(self):
    client_id = db_test_utils.InitializeClient(self.db)

    path_info = rdf_objects.PathInfo.OS(components=["foo"])

    path_info.stat_entry = rdf_client_fs.StatEntry(st_mode=42)
    path_info.hash_entry = None
    self.db.WritePathInfos(client_id, [path_info])
    timestamp_1 = rdfvalue.RDFDatetime.Now()

    path_info.stat_entry = None
    path_info.hash_entry = rdf_crypto.Hash(sha256=b"quux")
    self.db.WritePathInfos(client_id, [path_info])
    timestamp_2 = rdfvalue.RDFDatetime.Now()

    path_info.stat_entry = rdf_client_fs.StatEntry(st_mode=1337)
    path_info.hash_entry = None
    self.db.WritePathInfos(client_id, [path_info])
    timestamp_3 = rdfvalue.RDFDatetime.Now()

    path_info.stat_entry = rdf_client_fs.StatEntry(st_mode=4815162342)
    path_info.hash_entry = rdf_crypto.Hash(sha256=b"norf")
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
    self.assertEqual(path_info_2.hash_entry.sha256, b"quux")

    path_info_3 = self.db.ReadPathInfo(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo",),
        timestamp=timestamp_3)
    self.assertEqual(path_info_3.stat_entry.st_mode, 1337)
    self.assertEqual(path_info_3.hash_entry.sha256, b"quux")

    path_info_4 = self.db.ReadPathInfo(
        client_id,
        rdf_objects.PathInfo.PathType.OS,
        components=("foo",),
        timestamp=timestamp_4)
    self.assertEqual(path_info_4.stat_entry.st_mode, 4815162342)
    self.assertEqual(path_info_4.hash_entry.sha256, b"norf")

  def testReadPathInfoOlder(self):
    client_id = db_test_utils.InitializeClient(self.db)

    path_info = rdf_objects.PathInfo.OS(components=["foo"])
    path_info.stat_entry.st_mode = 42
    path_info.hash_entry.sha256 = b"foo"
    self.db.WritePathInfos(client_id, [path_info])

    path_info = rdf_objects.PathInfo.OS(components=["bar"])
    path_info.stat_entry.st_mode = 1337
    path_info.hash_entry.sha256 = b"bar"
    self.db.WritePathInfos(client_id, [path_info])

    path_info = self.db.ReadPathInfo(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))
    self.assertEqual(path_info.stat_entry.st_mode, 42)
    self.assertEqual(path_info.hash_entry.sha256, b"foo")

    path_info = self.db.ReadPathInfo(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("bar",))
    self.assertEqual(path_info.stat_entry.st_mode, 1337)
    self.assertEqual(path_info.hash_entry.sha256, b"bar")

  def testListDescendentPathInfosEmptyResult(self):
    client_id = db_test_utils.InitializeClient(self.db)

    self.db.WritePathInfos(client_id,
                           [rdf_objects.PathInfo.OS(components=["foo"])])

    results = self.db.ListDescendentPathInfos(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))

    self.assertEmpty(results)

  def testListDescendentPathInfosSingleResult(self):
    client_id = db_test_utils.InitializeClient(self.db)

    self.db.WritePathInfos(client_id, [
        rdf_objects.PathInfo.OS(components=["foo", "bar"]),
    ])

    results = self.db.ListDescendentPathInfos(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))

    self.assertLen(results, 1)
    self.assertEqual(results[0].components, ("foo", "bar"))

  def testListDescendentPathInfosSingle(self):
    client_id = db_test_utils.InitializeClient(self.db)

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
    client_id = db_test_utils.InitializeClient(self.db)

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
    client_id = db_test_utils.InitializeClient(self.db)

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
    client_id = db_test_utils.InitializeClient(self.db)

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
    client_id = db_test_utils.InitializeClient(self.db)

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
    client_id = db_test_utils.InitializeClient(self.db)

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

  def testListDescendentPathInfosDepthZero(self):
    client_id = db_test_utils.InitializeClient(self.db)

    path_info_1 = rdf_objects.PathInfo.OS(components=("foo",))
    path_info_2 = rdf_objects.PathInfo.OS(components=("foo", "bar"))
    path_info_3 = rdf_objects.PathInfo.OS(components=("baz",))

    self.db.WritePathInfos(client_id, [path_info_1, path_info_2, path_info_3])

    results = self.db.ListDescendentPathInfos(
        client_id=client_id,
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=(),
        max_depth=0)
    self.assertEmpty(results)

  def testListDescendentPathInfosTimestampNow(self):
    client_id = db_test_utils.InitializeClient(self.db)

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
    client_id = db_test_utils.InitializeClient(self.db)

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
    client_id = db_test_utils.InitializeClient(self.db)

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
    client_id = db_test_utils.InitializeClient(self.db)

    timestamp_0 = rdfvalue.RDFDatetime.Now()

    path_info = rdf_objects.PathInfo.OS(components=("foo",))

    path_info.hash_entry.md5 = b"quux"
    path_info.hash_entry.sha256 = b"thud"
    self.db.WritePathInfos(client_id, [path_info])
    timestamp_1 = rdfvalue.RDFDatetime.Now()

    path_info.hash_entry.md5 = b"norf"
    path_info.hash_entry.sha256 = b"blargh"
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
    self.assertEqual(results_1[0].hash_entry.sha256, b"thud")

    results_2 = self.db.ListDescendentPathInfos(
        client_id=client_id,
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=(),
        timestamp=timestamp_2)
    self.assertLen(results_2, 1)
    self.assertEqual(results_2[0].components, ("foo",))
    self.assertEqual(results_2[0].hash_entry.md5, b"norf")
    self.assertEqual(results_2[0].hash_entry.sha256, b"blargh")

  def testListDescendentPathInfosWildcards(self):
    client_id = db_test_utils.InitializeClient(self.db)

    self.db.WritePathInfos(client_id, [
        rdf_objects.PathInfo.OS(components=("foo", "quux")),
        rdf_objects.PathInfo.OS(components=("bar", "norf")),
        rdf_objects.PathInfo.OS(components=("___", "thud")),
        rdf_objects.PathInfo.OS(components=("%%%", "ztesch")),
    ])

    results = self.db.ListDescendentPathInfos(
        client_id=client_id,
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=("___",))
    self.assertLen(results, 1)
    self.assertEqual(results[0].components, ("___", "thud"))

    results = self.db.ListDescendentPathInfos(
        client_id=client_id,
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=("%%%",))
    self.assertLen(results, 1)
    self.assertEqual(results[0].components, ("%%%", "ztesch"))

  def testListDescendentPathInfosManyWildcards(self):
    client_id = db_test_utils.InitializeClient(self.db)

    self.db.WritePathInfos(client_id, [
        rdf_objects.PathInfo.OS(components=("%", "%%", "%%%")),
        rdf_objects.PathInfo.OS(components=("%", "%%%", "%")),
        rdf_objects.PathInfo.OS(components=("%%", "%", "%%%")),
        rdf_objects.PathInfo.OS(components=("%%", "%%%", "%")),
        rdf_objects.PathInfo.OS(components=("%%%", "%%", "%%")),
        rdf_objects.PathInfo.OS(components=("__", "%%", "__")),
    ])

    results = self.db.ListDescendentPathInfos(
        client_id=client_id,
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=("%",))

    self.assertLen(results, 4)
    self.assertEqual(results[0].components, ("%", "%%"))
    self.assertEqual(results[1].components, ("%", "%%", "%%%"))
    self.assertEqual(results[2].components, ("%", "%%%"))
    self.assertEqual(results[3].components, ("%", "%%%", "%"))

    results = self.db.ListDescendentPathInfos(
        client_id=client_id,
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=("%%",))

    self.assertLen(results, 4)
    self.assertEqual(results[0].components, ("%%", "%"))
    self.assertEqual(results[1].components, ("%%", "%", "%%%"))
    self.assertEqual(results[2].components, ("%%", "%%%"))
    self.assertEqual(results[3].components, ("%%", "%%%", "%"))

    results = self.db.ListDescendentPathInfos(
        client_id=client_id,
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=("__",))

    self.assertLen(results, 2)
    self.assertEqual(results[0].components, ("__", "%%"))
    self.assertEqual(results[1].components, ("__", "%%", "__"))

  def testListDescendentPathInfosWildcardsWithMaxDepth(self):
    client_id = db_test_utils.InitializeClient(self.db)

    self.db.WritePathInfos(client_id, [
        rdf_objects.PathInfo.OS(components=("%", "%%foo", "%%%bar", "%%%%")),
        rdf_objects.PathInfo.OS(components=("%", "%%foo", "%%%baz", "%%%%")),
        rdf_objects.PathInfo.OS(components=("%", "%%quux", "%%%norf", "%%%%")),
        rdf_objects.PathInfo.OS(components=("%", "%%quux", "%%%thud", "%%%%")),
        rdf_objects.PathInfo.OS(components=("%%", "%%bar", "%%%quux")),
        rdf_objects.PathInfo.OS(components=("%%", "%%baz", "%%%norf")),
        rdf_objects.PathInfo.OS(components=("__", "__bar__", "__quux__")),
        rdf_objects.PathInfo.OS(components=("__", "__baz__", "__norf__")),
        rdf_objects.PathInfo.OS(components=("blargh",)),
        rdf_objects.PathInfo.OS(components=("ztesch",)),
    ])

    results = self.db.ListDescendentPathInfos(
        client_id=client_id,
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=("%",),
        max_depth=2)

    self.assertLen(results, 6)
    self.assertEqual(results[0].components, ("%", "%%foo"))
    self.assertEqual(results[1].components, ("%", "%%foo", "%%%bar"))
    self.assertEqual(results[2].components, ("%", "%%foo", "%%%baz"))
    self.assertEqual(results[3].components, ("%", "%%quux"))
    self.assertEqual(results[4].components, ("%", "%%quux", "%%%norf"))
    self.assertEqual(results[5].components, ("%", "%%quux", "%%%thud"))

    results = self.db.ListDescendentPathInfos(
        client_id=client_id,
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=("%%",),
        max_depth=1)
    self.assertLen(results, 2)
    self.assertEqual(results[0].components, ("%%", "%%bar"))
    self.assertEqual(results[1].components, ("%%", "%%baz"))

    results = self.db.ListDescendentPathInfos(
        client_id=client_id,
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=("__",),
        max_depth=1)
    self.assertLen(results, 2)
    self.assertEqual(results[0].components, ("__", "__bar__"))
    self.assertEqual(results[1].components, ("__", "__baz__"))

  def testListChildPathInfosRoot(self):
    client_id = db_test_utils.InitializeClient(self.db)

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
    client_id = db_test_utils.InitializeClient(self.db)

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
    client_id = db_test_utils.InitializeClient(self.db)

    path_info = rdf_objects.PathInfo.OS(components=["foo", "bar"])
    path_info.stat_entry.st_size = 42
    self.db.WritePathInfos(client_id, [path_info])

    path_info = rdf_objects.PathInfo.OS(components=["foo", "baz"])
    path_info.hash_entry.md5 = b"quux"
    path_info.hash_entry.sha256 = b"norf"
    self.db.WritePathInfos(client_id, [path_info])

    results = self.db.ListChildPathInfos(
        client_id, rdf_objects.PathInfo.PathType.OS, components=("foo",))
    self.assertEqual(results[0].components, ("foo", "bar"))
    self.assertEqual(results[0].stat_entry.st_size, 42)
    self.assertEqual(results[1].components, ("foo", "baz"))
    self.assertEqual(results[1].hash_entry.md5, b"quux")
    self.assertEqual(results[1].hash_entry.sha256, b"norf")

  def testListChildPathInfosDeepSorted(self):
    client_id = db_test_utils.InitializeClient(self.db)

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
    client_id = db_test_utils.InitializeClient(self.db)

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
    client_id = db_test_utils.InitializeClient(self.db)

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
    client_id = db_test_utils.InitializeClient(self.db)
    result = self.db.ReadPathInfosHistories(client_id,
                                            rdf_objects.PathInfo.PathType.OS,
                                            [])
    self.assertEqual(result, {})

  def testReadPathInfosHistoriesDoesNotRaiseOnUnknownClient(self):
    results = self.db.ReadPathInfosHistories("C.FFFF111122223333",
                                             rdf_objects.PathInfo.PathType.OS,
                                             [("foo",)])

    self.assertEqual(results[("foo",)], [])

  def testReadPathInfosHistoriesWithSingleFileWithSingleHistoryItem(self):
    client_id = db_test_utils.InitializeClient(self.db)

    path_info = rdf_objects.PathInfo.OS(components=["foo"])

    path_info.stat_entry.st_size = 42
    path_info.hash_entry.sha256 = b"quux"

    then = rdfvalue.RDFDatetime.Now()
    self.db.WritePathInfos(client_id, [path_info])
    now = rdfvalue.RDFDatetime

    path_infos = self.db.ReadPathInfosHistories(
        client_id, rdf_objects.PathInfo.PathType.OS, [("foo",)])
    self.assertLen(path_infos, 1)

    pi = path_infos[("foo",)]
    self.assertLen(pi, 1)
    self.assertEqual(pi[0].stat_entry.st_size, 42)
    self.assertEqual(pi[0].hash_entry.sha256, b"quux")
    self.assertBetween(pi[0].timestamp, then, now)

  def testReadPathInfosHistoriesWithTwoFilesWithSingleHistoryItemEach(self):
    client_id = db_test_utils.InitializeClient(self.db)

    path_info_1 = rdf_objects.PathInfo.OS(components=["foo"])
    path_info_1.stat_entry.st_mode = 1337

    path_info_2 = rdf_objects.PathInfo.OS(components=["bar"])
    path_info_2.hash_entry.sha256 = b"quux"

    then = rdfvalue.RDFDatetime.Now()
    self.db.WritePathInfos(client_id, [path_info_1, path_info_2])
    now = rdfvalue.RDFDatetime.Now()

    path_infos = self.db.ReadPathInfosHistories(
        client_id, rdf_objects.PathInfo.PathType.OS, [("foo",), ("bar",)])
    self.assertLen(path_infos, 2)

    pi = path_infos[("bar",)]
    self.assertLen(pi, 1)

    self.assertEqual(pi[0].components, ("bar",))
    self.assertEqual(pi[0].hash_entry.sha256, b"quux")
    self.assertBetween(pi[0].timestamp, then, now)

    pi = path_infos[("foo",)]
    self.assertLen(pi, 1)

    self.assertEqual(pi[0].components, ("foo",))
    self.assertEqual(pi[0].stat_entry.st_mode, 1337)
    self.assertBetween(pi[0].timestamp, then, now)

  def testReadPathInfosHistoriesWithTwoFilesWithTwoHistoryItems(self):
    client_id = db_test_utils.InitializeClient(self.db)

    path_info_1 = rdf_objects.PathInfo.OS(components=["foo"])
    path_info_2 = rdf_objects.PathInfo.OS(components=["bar"])

    timestamp_1 = rdfvalue.RDFDatetime.Now()

    path_info_1.stat_entry.st_mode = 1337
    self.db.WritePathInfos(client_id, [path_info_1])

    timestamp_2 = rdfvalue.RDFDatetime.Now()

    path_info_1.stat_entry.st_mode = 1338
    self.db.WritePathInfos(client_id, [path_info_1])

    timestamp_3 = rdfvalue.RDFDatetime.Now()

    path_info_2.stat_entry.st_mode = 109
    self.db.WritePathInfos(client_id, [path_info_2])

    timestamp_4 = rdfvalue.RDFDatetime.Now()

    path_info_2.stat_entry.st_mode = 110
    self.db.WritePathInfos(client_id, [path_info_2])

    timestamp_5 = rdfvalue.RDFDatetime.Now()

    path_infos = self.db.ReadPathInfosHistories(
        client_id, rdf_objects.PathInfo.PathType.OS, [("foo",), ("bar",)])
    self.assertLen(path_infos, 2)

    pi = path_infos[("bar",)]
    self.assertLen(pi, 2)

    self.assertEqual(pi[0].components, ("bar",))
    self.assertEqual(pi[0].stat_entry.st_mode, 109)
    self.assertBetween(pi[0].timestamp, timestamp_3, timestamp_4)

    self.assertEqual(pi[1].components, ("bar",))
    self.assertEqual(pi[1].stat_entry.st_mode, 110)
    self.assertBetween(pi[1].timestamp, timestamp_4, timestamp_5)

    pi = path_infos[("foo",)]
    self.assertLen(pi, 2)

    self.assertEqual(pi[0].components, ("foo",))
    self.assertEqual(pi[0].stat_entry.st_mode, 1337)
    self.assertBetween(pi[0].timestamp, timestamp_1, timestamp_2)

    self.assertEqual(pi[1].components, ("foo",))
    self.assertEqual(pi[1].stat_entry.st_mode, 1338)
    self.assertBetween(pi[1].timestamp, timestamp_2, timestamp_3)

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
    client_a_id = db_test_utils.InitializeClient(self.db)
    client_b_id = db_test_utils.InitializeClient(self.db)

    path_1 = db.ClientPath.OS(client_a_id, components=("foo", "baz"))
    path_2 = db.ClientPath.TSK(client_b_id, components=("foo", "baz"))

    results = self.db.ReadLatestPathInfosWithHashBlobReferences(
        [path_1, path_2])
    self.assertEqual(results, {path_1: None, path_2: None})

  def testReadLatestPathInfosReturnsNothingWhenNoFilesCollected(self):
    client_a_id = db_test_utils.InitializeClient(self.db)
    client_b_id = db_test_utils.InitializeClient(self.db)

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
    client_a_id = db_test_utils.InitializeClient(self.db)
    client_b_id = db_test_utils.InitializeClient(self.db)
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
    client_id = db_test_utils.InitializeClient(self.db)
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
    client_id = db_test_utils.InitializeClient(self.db)
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
    client_id = db_test_utils.InitializeClient(self.db)
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
    client_id = db_test_utils.InitializeClient(self.db)
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

  def testWriteLongPathInfosWithCommonPrefix(self):
    client_id = db_test_utils.InitializeClient(self.db)

    prefix = ("foobarbaz",) * 303
    quux_components = prefix + ("quux",)
    norf_components = prefix + ("norf",)

    self.db.WritePathInfos(client_id, [
        rdf_objects.PathInfo.OS(components=quux_components),
        rdf_objects.PathInfo.OS(components=norf_components),
    ])

    quux_path_info = self.db.ReadPathInfo(
        client_id=client_id,
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=quux_components)
    self.assertEqual(quux_path_info.components, quux_components)

    norf_path_info = self.db.ReadPathInfo(
        client_id=client_id,
        path_type=rdf_objects.PathInfo.PathType.OS,
        components=norf_components)
    self.assertEqual(norf_path_info.components, norf_components)


# This file is a test library and thus does not require a __main__ block.
