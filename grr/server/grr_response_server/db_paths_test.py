#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

from grr.lib import rdfvalue
from grr.lib.rdfvalues import objects


class DatabaseTestPathsMixin(object):
  """An abstract class for testing db.Database implementations.

  This mixin adds methods to test the handling of GRR path data.
  """

  def testWritePathInfosRawValidates(self):
    path = ["usr", "local"]
    client_id = "C.bbbbbbbbbbbbbbbb"
    # Not a valid client_id
    with self.assertRaises(ValueError):
      self.db.WritePathInfosRaw("", [objects.PathInfo.OS(components=path)])
    # Missing path_type.
    with self.assertRaises(ValueError):
      self.db.WritePathInfosRaw(client_id, [objects.PathInfo(components=path)])

  def testWritePathInfosMetadata(self):
    client_id = "C.0123456789012345"
    datetime = rdfvalue.RDFDatetime.FromHumanReadable

    self.db.WritePathInfos(client_id, [
        objects.PathInfo.TSK(
            components=["foo", "bar"],
            directory=True,
            last_path_history_timestamp=datetime("2000-01-01")),
    ])

    results = self.db.FindPathInfosByPathIDs(client_id,
                                             objects.PathInfo.PathType.TSK,
                                             [objects.PathID(["foo", "bar"])])

    result_path_info = results[objects.PathID(["foo", "bar"])]
    self.assertEqual(result_path_info.path_type, objects.PathInfo.PathType.TSK)
    self.assertEqual(result_path_info.components, ["foo", "bar"])
    self.assertEqual(result_path_info.directory, True)
    self.assertEqual(result_path_info.last_path_history_timestamp,
                     datetime("2000-01-01"))

  def testWritePathInfosExpansion(self):
    client_id = "C.0123456789012345"
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

    self.assertEqual(
        results, {
            objects.PathID(["foo"]):
                objects.PathInfo.OS(components=["foo"], directory=True),
            objects.PathID(["foo", "bar"]):
                objects.PathInfo.OS(components=["foo", "bar"], directory=True),
            objects.PathID(["foo", "bar", "baz"]):
                objects.PathInfo.OS(components=["foo", "bar", "baz"]),
        })

  def testWritePathInfosTypeSeparated(self):
    client_id = "C.0123456789012345"
    datetime = rdfvalue.RDFDatetime.FromHumanReadable

    self.db.WritePathInfos(client_id, [
        objects.PathInfo.OS(
            components=["foo"],
            last_path_history_timestamp=datetime("2005-05-05")),
        objects.PathInfo.TSK(
            components=["foo"],
            last_path_history_timestamp=datetime("2008-08-08")),
    ])

    os_results = self.db.FindPathInfosByPathIDs(
        client_id, objects.PathInfo.PathType.OS, [objects.PathID(["foo"])])
    self.assertEqual(len(os_results), 1)
    self.assertEqual(
        os_results[objects.PathID(["foo"])].last_path_history_timestamp,
        datetime("2005-05-05"))

    tsk_results = self.db.FindPathInfosByPathIDs(
        client_id, objects.PathInfo.PathType.TSK, [objects.PathID(["foo"])])
    self.assertEqual(len(tsk_results), 1)
    self.assertEqual(
        tsk_results[objects.PathID(["foo"])].last_path_history_timestamp,
        datetime("2008-08-08"))

  def testWritePathInfosUpdates(self):
    client_id = "C.0123456789012345"
    datetime = rdfvalue.RDFDatetime.FromHumanReadable

    self.db.WritePathInfos(client_id, [
        objects.PathInfo.OS(
            components=["foo", "bar", "baz"],
            last_path_history_timestamp=datetime("2018-01-01")),
    ])
    self.db.WritePathInfos(client_id, [
        objects.PathInfo.OS(
            components=["foo", "bar", "baz"],
            last_path_history_timestamp=datetime("2018-06-01")),
    ])

    results = self.db.FindPathInfosByPathIDs(
        client_id, objects.PathInfo.PathType.OS, [
            objects.PathID(["foo", "bar", "baz"]),
        ])

    result_path_info = results[objects.PathID(["foo", "bar", "baz"])]
    self.assertEqual(result_path_info.last_path_history_timestamp,
                     datetime("2018-06-01"))

  def testWritePathInfosUpdatesAncestors(self):
    client_id = "C.0123456789012345"

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

  def testFindDescendentPathIDsSingle(self):
    client_id = "C.0123456789012345"
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
    client_id = "C.0123456789012345"
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
    client_id = "C.0123456789012345"
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
    client_id = "C.0123456789012345"
    self.db.WritePathInfos(
        client_id, [
            objects.PathInfo.OS(components=["usr", "bin", "javac"]),
            objects.PathInfo.TSK(components=["usr", "bin", "gdb"]),
        ])

    os_results = self.db.FindDescendentPathIDs(client_id,
                                               objects.PathInfo.PathType.OS,
                                               objects.PathID(["usr", "bin"]))
    self.assertEqual(os_results, [objects.PathID(["usr", "bin", "javac"])])

    tsk_results = self.db.FindDescendentPathIDs(client_id,
                                                objects.PathInfo.PathType.TSK,
                                                objects.PathID(["usr", "bin"]))
    self.assertEqual(tsk_results, [objects.PathID(["usr", "bin", "gdb"])])

  def testFindDescendentPathIDsAll(self):
    client_id = "C.0123456789012345"
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
