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
    # Not a valid client_id
    with self.assertRaises(ValueError):
      self.db.WritePathInfosRaw("", [objects.PathInfo(path)])

  def testWritePathInfos(self):
    path_1 = ["usr", "bin", "javac"]
    path_2 = ["usr", "bin", "gdb"]
    client_id = "C.bbbbbbbbbbbbbbbb"

    self.db.WritePathInfos(client_id, [
        objects.PathInfo(
            components=path_1,
            last_path_history_timestamp=rdfvalue.RDFDatetime.FromHumanReadable(
                "2017-01-01")),
        objects.PathInfo(
            components=path_2,
            last_path_history_timestamp=rdfvalue.RDFDatetime.FromHumanReadable(
                "2017-01-02")),
    ])
    # In addition to the 2 paths we put, we should also find the 2 shared parent
    # directories.
    results = self.db.FindPathInfosByPathIDs(
        client_id,
        map(objects.PathInfo.MakePathID,
            [path_1, path_2, ["usr"], ["usr", "bin"]]))
    self.assertEqual(
        results, {
            objects.PathInfo.MakePathID(path_1):
                objects.PathInfo(
                    components=path_1,
                    last_path_history_timestamp=rdfvalue.RDFDatetime.
                    FromHumanReadable("2017-01-01")),
            objects.PathInfo.MakePathID(path_2):
                objects.PathInfo(
                    components=path_2,
                    last_path_history_timestamp=rdfvalue.RDFDatetime.
                    FromHumanReadable("2017-01-02")),
            objects.PathInfo.MakePathID(["usr"]):
                objects.PathInfo(components=["usr"], directory=True),
            objects.PathInfo.MakePathID(["usr", "bin"]):
                objects.PathInfo(components=["usr", "bin"], directory=True),
        })

  def testFindDescendentPathIDs(self):
    path_1 = [
        "usr", "lib", "lightning", "chrome", "calendar-en-US", "locale",
        "en-US", "calendar", "calendar-occurrence-prompt.properties"
    ]
    path_2 = [
        "usr", "lib", "lightning", "chrome", "calendar", "content", "calendar",
        "calendar-creation.js"
    ]
    client_id = "C.bbbbbbbbbbbbbbbb"
    self.db.WritePathInfos(
        client_id, [
            objects.PathInfo(components=path_1),
            objects.PathInfo(components=path_2)
        ])
    # Read everything.
    results = self.db.FindDescendentPathIDs(
        client_id, objects.PathInfo.MakePathID(["usr", "lib", "lightning"]))
    results_set = set(results)
    self.assertEqual(len(results), len(results_set))
    self.assertIn(objects.PathInfo.MakePathID(path_1), results_set)
    self.assertIn(objects.PathInfo.MakePathID(path_2), results_set)
    self.assertNotIn(
        objects.PathInfo.MakePathID(["usr", "lib", "lightning"]), results_set)
    self.assertIn(
        objects.PathInfo.MakePathID(["usr", "lib", "lightning", "chrome"]),
        results_set)

    # Read 2 levels.
    results = self.db.FindDescendentPathIDs(
        client_id,
        objects.PathInfo.MakePathID(["usr", "lib", "lightning"]),
        max_depth=2)
    results_set = set(results)
    self.assertEqual(len(results), len(results_set))
    # Our leaf nodes shouldn't be there, they are too deep.
    self.assertNotIn(objects.PathInfo.MakePathID(path_1), results_set)
    self.assertNotIn(objects.PathInfo.MakePathID(path_2), results_set)
    # We don't expect start point to be included.
    self.assertNotIn(
        objects.PathInfo.MakePathID(["usr", "lib", "lightning"]), results_set)
    # We do expect 2 layers, but no more.
    self.assertIn(
        objects.PathInfo.MakePathID(["usr", "lib", "lightning", "chrome"]),
        results_set)
    self.assertIn(
        objects.PathInfo.MakePathID(
            ["usr", "lib", "lightning", "chrome", "calendar"]), results_set)
    self.assertNotIn(
        objects.PathInfo.MakePathID(
            ["usr", "lib", "lightning", "chrome", "calendar", "content"]),
        results_set)
