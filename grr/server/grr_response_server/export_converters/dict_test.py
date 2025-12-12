#!/usr/bin/env python
"""Tests for dict export converters."""

from absl.testing import absltest

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_proto import export_pb2
from grr_response_proto import jobs_pb2
from grr_response_server.export_converters import dict as dict_converter


class DictToExportedDictItemsConverterProtoTest(absltest.TestCase):
  """Tests for DictToExportedDictItemsConverterProto."""

  def setUp(self):
    super().setUp()
    self.converter = dict_converter.DictToExportedDictItemsConverterProto()
    self.client_id = "C.1234567890123456"
    self.metadata_proto = export_pb2.ExportedMetadata(
        client_urn=rdf_client.ClientURN(self.client_id).SerializeToWireFormat(),
        client_id=self.client_id,
    )

  def testConvertsDictWithPrimitiveValues(self):
    source = jobs_pb2.Dict(
        dat=[
            jobs_pb2.KeyValue(
                k=jobs_pb2.DataBlob(string="foo"),
                v=jobs_pb2.DataBlob(string="bar"),
            ),
            jobs_pb2.KeyValue(
                k=jobs_pb2.DataBlob(string="bar"),
                v=jobs_pb2.DataBlob(integer=42),
            ),
        ]
    )

    converted = list(self.converter.Convert(self.metadata_proto, source))

    self.assertLen(converted, 2)

    # Output should be stable sorted by dict's keys.
    self.assertEqual(converted[0].key, "bar")
    self.assertEqual(converted[0].value, "42")
    self.assertEqual(converted[1].key, "foo")
    self.assertEqual(converted[1].value, "bar")

  def testConvertsDictWithNestedDict(self):
    source = jobs_pb2.Dict(
        dat=[
            jobs_pb2.KeyValue(
                k=jobs_pb2.DataBlob(string="nested_dict"),
                v=jobs_pb2.DataBlob(
                    dict=jobs_pb2.Dict(
                        dat=[
                            jobs_pb2.KeyValue(
                                k=jobs_pb2.DataBlob(string="a"),
                                v=jobs_pb2.DataBlob(integer=42),
                            ),
                            jobs_pb2.KeyValue(
                                k=jobs_pb2.DataBlob(string="b"),
                                v=jobs_pb2.DataBlob(integer=43),
                            ),
                        ]
                    )
                ),
            ),
        ]
    )

    converted = list(self.converter.Convert(self.metadata_proto, source))

    self.assertLen(converted, 2)
    self.assertEqual(converted[0].key, "nested_dict.a")
    self.assertEqual(converted[0].value, "42")
    self.assertEqual(converted[1].key, "nested_dict.b")
    self.assertEqual(converted[1].value, "43")

  def testConvertsDictWithNestedSet(self):
    source = jobs_pb2.Dict(
        dat=[
            jobs_pb2.KeyValue(
                k=jobs_pb2.DataBlob(string="foo"),
                v=jobs_pb2.DataBlob(string="bar"),
            ),
            jobs_pb2.KeyValue(
                k=jobs_pb2.DataBlob(string="a_set"),
                v=jobs_pb2.DataBlob(
                    set=jobs_pb2.BlobArray(
                        content=[
                            jobs_pb2.DataBlob(integer=43),
                            jobs_pb2.DataBlob(integer=42),
                            jobs_pb2.DataBlob(integer=44),
                        ]
                    )
                ),
            ),
        ]
    )

    converted = list(self.converter.Convert(self.metadata_proto, source))

    self.assertLen(converted, 4)

    # Output should be stable sorted by dict's keys.
    # Set items are sorted.
    self.assertEqual(converted[0].key, "a_set[0]")
    self.assertEqual(converted[0].value, "42")
    self.assertEqual(converted[1].key, "a_set[1]")
    self.assertEqual(converted[1].value, "43")
    self.assertEqual(converted[2].key, "a_set[2]")
    self.assertEqual(converted[2].value, "44")
    self.assertEqual(converted[3].key, "foo")
    self.assertEqual(converted[3].value, "bar")

  def testConvertsDictWithNestedList(self):
    source = jobs_pb2.Dict(
        dat=[
            jobs_pb2.KeyValue(
                k=jobs_pb2.DataBlob(string="foo"),
                v=jobs_pb2.DataBlob(string="bar"),
            ),
            jobs_pb2.KeyValue(
                k=jobs_pb2.DataBlob(string="a_list"),
                v=jobs_pb2.DataBlob(
                    list=jobs_pb2.BlobArray(
                        content=[
                            jobs_pb2.DataBlob(integer=43),
                            jobs_pb2.DataBlob(integer=42),
                            jobs_pb2.DataBlob(integer=44),
                        ]
                    )
                ),
            ),
        ]
    )

    converted = list(self.converter.Convert(self.metadata_proto, source))

    self.assertLen(converted, 4)

    # Output should be stable sorted by dict's keys.
    # List items are NOT sorted.
    self.assertEqual(converted[0].key, "a_list[0]")
    self.assertEqual(converted[0].value, "43")
    self.assertEqual(converted[1].key, "a_list[1]")
    self.assertEqual(converted[1].value, "42")
    self.assertEqual(converted[2].key, "a_list[2]")
    self.assertEqual(converted[2].value, "44")
    self.assertEqual(converted[3].key, "foo")
    self.assertEqual(converted[3].value, "bar")

  def testConvertsDictWithNestedTuple(self):
    source = jobs_pb2.Dict(
        dat=[
            jobs_pb2.KeyValue(
                k=jobs_pb2.DataBlob(string="foo"),
                v=jobs_pb2.DataBlob(string="bar"),
            ),
            jobs_pb2.KeyValue(
                k=jobs_pb2.DataBlob(string="a_tuple"),
                v=jobs_pb2.DataBlob(
                    # There's no "tuple" type in the source proto - it's
                    # represented as a list.
                    list=jobs_pb2.BlobArray(
                        content=[
                            jobs_pb2.DataBlob(integer=43),
                            jobs_pb2.DataBlob(integer=42),
                            jobs_pb2.DataBlob(integer=44),
                        ]
                    )
                ),
            ),
        ]
    )

    converted = list(self.converter.Convert(self.metadata_proto, source))

    self.assertLen(converted, 4)

    # Output should be stable sorted by dict's keys.
    # Tuple items are NOT sorted.
    self.assertEqual(converted[0].key, "a_tuple[0]")
    self.assertEqual(converted[0].value, "43")
    self.assertEqual(converted[1].key, "a_tuple[1]")
    self.assertEqual(converted[1].value, "42")
    self.assertEqual(converted[2].key, "a_tuple[2]")
    self.assertEqual(converted[2].value, "44")
    self.assertEqual(converted[3].key, "foo")
    self.assertEqual(converted[3].value, "bar")

  def testConvertsDictWithMixedKeyTypes(self):
    source = jobs_pb2.Dict(
        dat=[
            jobs_pb2.KeyValue(
                k=jobs_pb2.DataBlob(string="foo"),
                v=jobs_pb2.DataBlob(string="bar"),
            ),
            jobs_pb2.KeyValue(
                k=jobs_pb2.DataBlob(integer=1),
                v=jobs_pb2.DataBlob(integer=42),
            ),
        ]
    )

    converted = list(self.converter.Convert(self.metadata_proto, source))

    self.assertLen(converted, 2)

    # Output should be stable sorted by dict's keys as strings.
    self.assertEqual(converted[0].key, "1")
    self.assertEqual(converted[0].value, "42")
    self.assertEqual(converted[1].key, "foo")
    self.assertEqual(converted[1].value, "bar")

  def testConvertsDictWithNestedDictAndIterables(self):
    source = jobs_pb2.Dict(
        dat=[
            jobs_pb2.KeyValue(
                k=jobs_pb2.DataBlob(string="foo"),
                v=jobs_pb2.DataBlob(string="bar"),
            ),
            jobs_pb2.KeyValue(
                k=jobs_pb2.DataBlob(string="bar"),
                v=jobs_pb2.DataBlob(
                    dict=jobs_pb2.Dict(
                        dat=[
                            jobs_pb2.KeyValue(
                                k=jobs_pb2.DataBlob(string="a"),
                                v=jobs_pb2.DataBlob(
                                    dict=jobs_pb2.Dict(
                                        dat=[
                                            jobs_pb2.KeyValue(
                                                k=jobs_pb2.DataBlob(string="c"),
                                                v=jobs_pb2.DataBlob(
                                                    list=jobs_pb2.BlobArray(
                                                        content=[
                                                            jobs_pb2.DataBlob(
                                                                integer=42
                                                            ),
                                                            jobs_pb2.DataBlob(
                                                                integer=43
                                                            ),
                                                            jobs_pb2.DataBlob(
                                                                integer=44
                                                            ),
                                                            jobs_pb2.DataBlob(
                                                                dict=jobs_pb2.Dict(
                                                                    dat=[
                                                                        jobs_pb2.KeyValue(
                                                                            k=jobs_pb2.DataBlob(
                                                                                string="x"
                                                                            ),
                                                                            v=jobs_pb2.DataBlob(
                                                                                string="y"
                                                                            ),
                                                                        )
                                                                    ]
                                                                )
                                                            ),
                                                        ]
                                                    )
                                                ),
                                            ),
                                            jobs_pb2.KeyValue(
                                                k=jobs_pb2.DataBlob(string="d"),
                                                v=jobs_pb2.DataBlob(
                                                    string="oh"
                                                ),
                                            ),
                                        ]
                                    )
                                ),
                            ),
                            jobs_pb2.KeyValue(
                                k=jobs_pb2.DataBlob(string="b"),
                                v=jobs_pb2.DataBlob(integer=43),
                            ),
                        ]
                    )
                ),
            ),
        ]
    )

    converted = list(self.converter.Convert(self.metadata_proto, source))

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


if __name__ == "__main__":
  absltest.main()
