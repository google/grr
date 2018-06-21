#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

from grr.lib import rdfvalue
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import objects
from grr.lib.rdfvalues import paths as rdf_paths
from grr.server.grr_response_server import db


class DatabaseTestPathsMixin(object):
  """An abstract class for testing db.Database implementations.

  This mixin adds methods to test the handling of GRR path data.
  """

  def testWritePathInfosValidatesClientId(self):
    path = ["usr", "local"]

    with self.assertRaises(ValueError):
      self.db.WritePathInfos("", [objects.PathInfo.OS(components=path)])

  def testWritePathInfosValidatesPathType(self):
    path = ["usr", "local"]
    client_id = "C.bbbbbbbbbbbbbbbb"

    with self.assertRaises(ValueError):
      self.db.WritePathInfos(client_id, [objects.PathInfo(components=path)])

  def testWritePathInfosValidatesClient(self):
    client_id = "C.0123456789012345"

    with self.assertRaises(db.UnknownClientError) as context:
      self.db.WritePathInfos(
          client_id, [objects.PathInfo.OS(components=[], directory=True)])

    self.assertEqual(context.exception.client_id, client_id)

  def testWritePathInfosValidateConflictingWrites(self):
    client_id = self.InitializeClient()

    with self.assertRaises(ValueError):
      self.db.WritePathInfos(client_id, [
          objects.PathInfo.OS(components=["foo", "bar"], directory=False),
          objects.PathInfo.OS(components=["foo", "bar"], directory=True),
      ])

  def testWritePathInfosMetadata(self):
    client_id = self.InitializeClient()

    now = rdfvalue.RDFDatetime.Now()

    self.db.WritePathInfos(
        client_id,
        [objects.PathInfo.TSK(components=["foo", "bar"], directory=True)])

    results = self.db.FindPathInfosByPathIDs(client_id,
                                             objects.PathInfo.PathType.TSK,
                                             [objects.PathID(["foo", "bar"])])

    result_path_info = results[objects.PathID(["foo", "bar"])]
    self.assertEqual(result_path_info.path_type, objects.PathInfo.PathType.TSK)
    self.assertEqual(result_path_info.components, ["foo", "bar"])
    self.assertEqual(result_path_info.directory, True)
    self.assertGreater(result_path_info.last_path_history_timestamp, now)

  def testWritePathInfosStatEntry(self):
    client_id = self.InitializeClient()

    stat_entry = rdf_client.StatEntry()
    stat_entry.pathspec.path = "foo/bar"
    stat_entry.pathspec.pathtype = rdf_paths.PathSpec.PathType.OS
    stat_entry.st_mode = 1337
    stat_entry.st_mtime = 108
    stat_entry.st_atime = 4815162342

    path_info = objects.PathInfo.FromStatEntry(stat_entry)
    self.db.WritePathInfos(client_id, [path_info])

    results = self.db.FindPathInfosByPathIDs(client_id,
                                             objects.PathInfo.PathType.OS, [
                                                 objects.PathID([]),
                                                 objects.PathID(["foo"]),
                                                 objects.PathID(["foo", "bar"]),
                                             ])

    root_path_info = results[objects.PathID([])]
    self.assertFalse(root_path_info.HasField("stat_entry"))

    foo_path_info = results[objects.PathID(["foo"])]
    self.assertFalse(foo_path_info.HasField("stat_entry"))

    foobar_path_info = results[objects.PathID(["foo", "bar"])]
    self.assertTrue(foobar_path_info.HasField("stat_entry"))
    self.assertEqual(foobar_path_info.stat_entry.st_mode, 1337)
    self.assertEqual(foobar_path_info.stat_entry.st_mtime, 108)
    self.assertEqual(foobar_path_info.stat_entry.st_atime, 4815162342)

  def testWritePathInfosExpansion(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(
        client_id, [
            objects.PathInfo.OS(components=["foo", "bar", "baz"]),
        ])

    results = self.db.FindPathInfosByPathIDs(
        client_id, objects.PathInfo.PathType.OS, [
            objects.PathID(["foo"]),
            objects.PathID(["foo", "bar"]),
            objects.PathID(["foo", "bar", "baz"]),
        ])

    self.assertEqual(len(results), 3)

    foo = results[objects.PathID(["foo"])]
    self.assertEqual(foo.components, ["foo"])
    self.assertTrue(foo.directory)

    foobar = results[objects.PathID(["foo", "bar"])]
    self.assertEqual(foobar.components, ["foo", "bar"])
    self.assertTrue(foobar.directory)

    foobarbaz = results[objects.PathID(["foo", "bar", "baz"])]
    self.assertEqual(foobarbaz.components, ["foo", "bar", "baz"])
    self.assertFalse(foobarbaz.directory)

  def testWritePathInfosTypeSeparated(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(client_id, [
        objects.PathInfo.OS(components=["foo"], directory=True),
        objects.PathInfo.TSK(components=["foo"], directory=False),
    ])

    os_results = self.db.FindPathInfosByPathIDs(
        client_id, objects.PathInfo.PathType.OS, [objects.PathID(["foo"])])
    self.assertEqual(len(os_results), 1)
    self.assertTrue(os_results[objects.PathID(["foo"])].directory)

    tsk_results = self.db.FindPathInfosByPathIDs(
        client_id, objects.PathInfo.PathType.TSK, [objects.PathID(["foo"])])
    self.assertEqual(len(tsk_results), 1)
    self.assertFalse(tsk_results[objects.PathID(["foo"])].directory)

  def testWritePathInfosUpdates(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(client_id, [
        objects.PathInfo.OS(components=["foo", "bar", "baz"], directory=False),
    ])

    now = rdfvalue.RDFDatetime.Now()

    self.db.WritePathInfos(client_id, [
        objects.PathInfo.OS(components=["foo", "bar", "baz"], directory=True),
    ])

    results = self.db.FindPathInfosByPathIDs(
        client_id, objects.PathInfo.PathType.OS, [
            objects.PathID(["foo", "bar", "baz"]),
        ])

    result_path_info = results[objects.PathID(["foo", "bar", "baz"])]
    self.assertGreater(result_path_info.last_path_history_timestamp, now)
    self.assertTrue(result_path_info.directory)

  def testWritePathInfosUpdatesAncestors(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(client_id, [
        objects.PathInfo.OS(components=["foo"], directory=False),
    ])
    self.db.WritePathInfos(
        client_id, [
            objects.PathInfo.OS(components=["foo", "bar"]),
        ])

    results = self.db.FindPathInfosByPathIDs(
        client_id, objects.PathInfo.PathType.OS, [objects.PathID(["foo"])])

    self.assertEqual(len(results), 1)
    self.assertTrue(results[objects.PathID(["foo"])].directory)

  def testWritePathInfosDuplicatedData(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(
        client_id, [
            objects.PathInfo.OS(components=["foo", "bar"]),
        ])
    self.db.WritePathInfos(
        client_id, [
            objects.PathInfo.OS(components=["foo", "bar"]),
        ])

    results = self.db.FindPathInfosByPathIDs(client_id,
                                             objects.PathInfo.PathType.OS,
                                             [objects.PathID(["foo", "bar"])])
    self.assertEqual(len(results), 1)

    result_path_info = results[objects.PathID(["foo", "bar"])]
    self.assertEqual(result_path_info.components, ["foo", "bar"])
    self.assertEqual(result_path_info.directory, False)

  def testFindPathInfosByPathIDsNonExistent(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(
        client_id, [
            objects.PathInfo.OS(components=["foo", "bar"]),
        ])

    results = self.db.FindPathInfosByPathIDs(
        client_id, objects.PathInfo.PathType.OS, [
            objects.PathID(["foo", "bar"]),
            objects.PathID(["foo", "baz"]),
            objects.PathID(["quux", "norf"])
        ])
    self.assertEqual(len(results), 3)
    self.assertIsNotNone(results[objects.PathID(["foo", "bar"])])
    self.assertIsNone(results[objects.PathID(["foo", "baz"])])
    self.assertIsNone(results[objects.PathID(["quux", "norf"])])

  def testFindPathInfoByPathIDValidatesTimestamp(self):
    client_id = self.InitializeClient()
    path_id = objects.PathID(["foo", "bar", "baz"])

    with self.assertRaises(TypeError):
      self.db.FindPathInfoByPathID(
          client_id,
          objects.PathInfo.PathType.REGISTRY,
          path_id,
          timestamp=rdfvalue.Duration("10s"))

  def testFindPathInfoByPathIDNonExistent(self):
    client_id = self.InitializeClient()
    path_id = objects.PathID(["foo", "bar", "baz"])

    with self.assertRaises(db.UnknownPathError):
      self.db.FindPathInfoByPathID(client_id, objects.PathInfo.PathType.OS,
                                   path_id)

  def testFindPathInfoByPathIDTimestamp(self):
    client_id = self.InitializeClient()

    pathspec = rdf_paths.PathSpec(
        path="foo/bar/baz", pathtype=rdf_paths.PathSpec.PathType.OS)

    stat_entry = rdf_client.StatEntry(pathspec=pathspec, st_size=42)
    self.db.WritePathInfos(client_id,
                           [objects.PathInfo.FromStatEntry(stat_entry)])
    timestamp_1 = rdfvalue.RDFDatetime.Now()

    stat_entry = rdf_client.StatEntry(pathspec=pathspec, st_size=101)
    self.db.WritePathInfos(client_id,
                           [objects.PathInfo.FromStatEntry(stat_entry)])
    timestamp_2 = rdfvalue.RDFDatetime.Now()

    stat_entry = rdf_client.StatEntry(pathspec=pathspec, st_size=1337)
    self.db.WritePathInfos(client_id,
                           [objects.PathInfo.FromStatEntry(stat_entry)])
    timestamp_3 = rdfvalue.RDFDatetime.Now()

    path_id = objects.PathID(["foo", "bar", "baz"])

    path_info_last = self.db.FindPathInfoByPathID(
        client_id, objects.PathInfo.PathType.OS, path_id)
    self.assertEqual(path_info_last.stat_entry.st_size, 1337)
    self.assertEqual(path_info_last.components, ["foo", "bar", "baz"])

    path_info_1 = self.db.FindPathInfoByPathID(
        client_id, objects.PathInfo.PathType.OS, path_id, timestamp=timestamp_1)
    self.assertEqual(path_info_1.stat_entry.st_size, 42)
    self.assertEqual(path_info_last.components, ["foo", "bar", "baz"])

    path_info_2 = self.db.FindPathInfoByPathID(
        client_id, objects.PathInfo.PathType.OS, path_id, timestamp=timestamp_2)
    self.assertEqual(path_info_2.stat_entry.st_size, 101)
    self.assertEqual(path_info_last.components, ["foo", "bar", "baz"])

    path_info_3 = self.db.FindPathInfoByPathID(
        client_id, objects.PathInfo.PathType.OS, path_id, timestamp=timestamp_3)
    self.assertEqual(path_info_3.stat_entry.st_size, 1337)
    self.assertEqual(path_info_last.components, ["foo", "bar", "baz"])

  def testFindDescendentPathIDsEmptyResult(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(client_id, [objects.PathInfo.OS(components=["foo"])])

    results = self.db.FindDescendentPathIDs(client_id,
                                            objects.PathInfo.PathType.OS,
                                            objects.PathID(["foo"]))
    self.assertItemsEqual(results, [])

  def testFindDescendentPathIDsSingleResult(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(
        client_id, [
            objects.PathInfo.OS(components=["foo", "bar"]),
        ])

    results = self.db.FindDescendentPathIDs(client_id,
                                            objects.PathInfo.PathType.OS,
                                            objects.PathID(["foo"]))

    self.assertItemsEqual(results, [objects.PathID(["foo", "bar"])])

  def testFindDescendentPathIDsSingle(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(
        client_id, [
            objects.PathInfo.OS(components=["foo", "bar", "baz", "quux"]),
        ])

    results = self.db.FindDescendentPathIDs(client_id,
                                            objects.PathInfo.PathType.OS,
                                            objects.PathID(["foo"]))

    self.assertItemsEqual(results, [
        objects.PathID(["foo", "bar"]),
        objects.PathID(["foo", "bar", "baz"]),
        objects.PathID(["foo", "bar", "baz", "quux"]),
    ])

  def testFindDescendentPathIDsBranching(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(
        client_id, [
            objects.PathInfo.OS(components=["foo", "bar", "quux"]),
            objects.PathInfo.OS(components=["foo", "baz"]),
        ])

    results = self.db.FindDescendentPathIDs(client_id,
                                            objects.PathInfo.PathType.OS,
                                            objects.PathID(["foo"]))

    self.assertItemsEqual(results, [
        objects.PathID(["foo", "bar"]),
        objects.PathID(["foo", "bar", "quux"]),
        objects.PathID(["foo", "baz"]),
    ])

  def testFindDescendentPathIDsLimited(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(
        client_id, [
            objects.PathInfo.OS(components=["foo", "bar", "baz", "quux"]),
            objects.PathInfo.OS(components=["foo", "bar", "blargh"]),
            objects.PathInfo.OS(components=["foo", "norf", "thud", "plugh"]),
        ])

    results = self.db.FindDescendentPathIDs(
        client_id,
        objects.PathInfo.PathType.OS,
        objects.PathID(["foo"]),
        max_depth=2)

    self.assertIn(objects.PathID(["foo", "bar"]), results)
    self.assertIn(objects.PathID(["foo", "bar", "baz"]), results)
    self.assertIn(objects.PathID(["foo", "bar", "blargh"]), results)
    self.assertIn(objects.PathID(["foo", "norf", "thud"]), results)

    self.assertNotIn(objects.PathID(["foo", "bar", "baz", "quux"]), results)
    self.assertNotIn(objects.PathID(["foo", "norf", "thud", "plugh"]), results)

  def testFindDescendentPathIDsTypeSeparated(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(
        client_id, [
            objects.PathInfo.OS(components=["usr", "bin", "javac"]),
            objects.PathInfo.TSK(components=["usr", "bin", "gdb"]),
        ])

    os_results = self.db.FindDescendentPathIDs(client_id,
                                               objects.PathInfo.PathType.OS,
                                               objects.PathID(["usr", "bin"]))
    self.assertEqual(os_results, {objects.PathID(["usr", "bin", "javac"])})

    tsk_results = self.db.FindDescendentPathIDs(client_id,
                                                objects.PathInfo.PathType.TSK,
                                                objects.PathID(["usr", "bin"]))
    self.assertEqual(tsk_results, {objects.PathID(["usr", "bin", "gdb"])})

  def testFindDescendentPathIDsAll(self):
    client_id = self.InitializeClient()

    self.db.WritePathInfos(
        client_id, [
            objects.PathInfo.OS(components=["foo", "bar"]),
            objects.PathInfo.OS(components=["baz", "quux"]),
        ])

    results = self.db.FindDescendentPathIDs(client_id,
                                            objects.PathInfo.PathType.OS,
                                            objects.PathID([]))
    self.assertItemsEqual(results, [
        objects.PathID(["foo"]),
        objects.PathID(["foo", "bar"]),
        objects.PathID(["baz"]),
        objects.PathID(["baz", "quux"]),
    ])
