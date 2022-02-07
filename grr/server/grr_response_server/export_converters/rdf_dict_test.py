#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Tests for export converters."""

from absl import app

from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_server.export_converters import rdf_dict
from grr.test_lib import export_test_lib
from grr.test_lib import test_lib


class DictToExportedDictItemsConverterTest(export_test_lib.ExportTestBase):
  """Tests for DictToExportedDictItemsConverter."""

  def setUp(self):
    super().setUp()
    self.converter = rdf_dict.DictToExportedDictItemsConverter()

  def testConvertsDictWithPrimitiveValues(self):
    source = rdf_protodict.Dict()
    source["foo"] = "bar"
    source["bar"] = 42

    # Serialize/unserialize to make sure we deal with the object that is
    # similar to what we may get from the datastore.
    source = rdf_protodict.Dict.FromSerializedBytes(source.SerializeToBytes())

    converted = list(self.converter.Convert(self.metadata, source))

    self.assertLen(converted, 2)

    # Output should be stable sorted by dict's keys.
    self.assertEqual(converted[0].key, "bar")
    self.assertEqual(converted[0].value, "42")
    self.assertEqual(converted[1].key, "foo")
    self.assertEqual(converted[1].value, "bar")

  def testConvertsDictWithNestedSetListOrTuple(self):
    # Note that set's contents will be sorted on export.
    variants = [set([43, 42, 44]), (42, 43, 44), [42, 43, 44]]

    for variant in variants:
      source = rdf_protodict.Dict()
      source["foo"] = "bar"
      source["bar"] = variant

      # Serialize/unserialize to make sure we deal with the object that is
      # similar to what we may get from the datastore.
      source = rdf_protodict.Dict.FromSerializedBytes(source.SerializeToBytes())

      converted = list(self.converter.Convert(self.metadata, source))

      self.assertLen(converted, 4)
      self.assertEqual(converted[0].key, "bar[0]")
      self.assertEqual(converted[0].value, "42")
      self.assertEqual(converted[1].key, "bar[1]")
      self.assertEqual(converted[1].value, "43")
      self.assertEqual(converted[2].key, "bar[2]")
      self.assertEqual(converted[2].value, "44")
      self.assertEqual(converted[3].key, "foo")
      self.assertEqual(converted[3].value, "bar")

  def testConvertsDictWithNestedDict(self):
    source = rdf_protodict.Dict()
    source["foo"] = "bar"
    source["bar"] = {"a": 42, "b": 43}

    # Serialize/unserialize to make sure we deal with the object that is
    # similar to what we may get from the datastore.
    source = rdf_protodict.Dict.FromSerializedBytes(source.SerializeToBytes())

    converted = list(self.converter.Convert(self.metadata, source))

    self.assertLen(converted, 3)

    # Output should be stable sorted by dict's keys.
    self.assertEqual(converted[0].key, "bar.a")
    self.assertEqual(converted[0].value, "42")
    self.assertEqual(converted[1].key, "bar.b")
    self.assertEqual(converted[1].value, "43")
    self.assertEqual(converted[2].key, "foo")
    self.assertEqual(converted[2].value, "bar")

  def testConvertsDictWithNestedDictAndIterables(self):
    source = rdf_protodict.Dict()
    source["foo"] = "bar"
    # pyformat: disable
    source["bar"] = {
        "a": {
            "c": [42, 43, 44, {"x": "y"}],
            "d": "oh"
        },
        "b": 43
    }
    # pyformat: enable

    # Serialize/unserialize to make sure we deal with the object that is
    # similar to what we may get from the datastore.
    source = rdf_protodict.Dict.FromSerializedBytes(source.SerializeToBytes())

    converted = list(self.converter.Convert(self.metadata, source))

    self.assertLen(converted, 7)

    # Output should be stable sorted by dict's keys.
    self.assertEqual(converted[0].key, "bar.a.c[0]")
    self.assertEqual(converted[0].value, "42")
    self.assertEqual(converted[1].key, "bar.a.c[1]")
    self.assertEqual(converted[1].value, "43")
    self.assertEqual(converted[2].key, "bar.a.c[2]")
    self.assertEqual(converted[2].value, "44")
    self.assertEqual(converted[3].key, "bar.a.c[3].x")
    self.assertEqual(converted[3].value, "y")
    self.assertEqual(converted[4].key, "bar.a.d")
    self.assertEqual(converted[4].value, "oh")
    self.assertEqual(converted[5].key, "bar.b")
    self.assertEqual(converted[5].value, "43")
    self.assertEqual(converted[6].key, "foo")
    self.assertEqual(converted[6].value, "bar")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
