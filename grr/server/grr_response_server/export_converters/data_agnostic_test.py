#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Tests for export converters."""

from absl import app

from grr_response_core.lib import rdfvalue
from grr_response_server.export_converters import base
from grr_response_server.export_converters import data_agnostic
from grr.test_lib import export_test_lib
from grr.test_lib import test_lib


class DataAgnosticExportConverterTest(export_test_lib.ExportTestBase):
  """Tests for DataAgnosticExportConverter."""

  def ConvertOriginalValue(self, original_value):
    converted_values = list(data_agnostic.DataAgnosticExportConverter().Convert(
        base.ExportedMetadata(source_urn=rdfvalue.RDFURN("aff4:/foo")),
        original_value))
    self.assertLen(converted_values, 1)
    return converted_values[0]

  def testAddsMetadataAndIgnoresRepeatedAndMessagesFields(self):
    original_value = export_test_lib.DataAgnosticConverterTestValue()
    converted_value = self.ConvertOriginalValue(original_value)

    # No 'metadata' field in the original value.
    self.assertCountEqual([t.name for t in original_value.type_infos], [
        "string_value", "int_value", "bool_value", "repeated_string_value",
        "message_value", "enum_value", "another_enum_value", "urn_value",
        "datetime_value"
    ])
    # But there's one in the converted value.
    self.assertCountEqual([t.name for t in converted_value.type_infos], [
        "metadata", "string_value", "int_value", "bool_value", "enum_value",
        "another_enum_value", "urn_value", "datetime_value"
    ])

    # Metadata value is correctly initialized from user-supplied metadata.
    self.assertEqual(converted_value.metadata.source_urn,
                     rdfvalue.RDFURN("aff4:/foo"))

  def testIgnoresPredefinedMetadataField(self):
    original_value = export_test_lib.DataAgnosticConverterTestValueWithMetadata(
        metadata=42, value="value")
    converted_value = self.ConvertOriginalValue(original_value)

    self.assertCountEqual([t.name for t in converted_value.type_infos],
                          ["metadata", "value"])
    self.assertEqual(converted_value.metadata.source_urn,
                     rdfvalue.RDFURN("aff4:/foo"))
    self.assertEqual(converted_value.value, "value")

  def testProcessesPrimitiveTypesCorrectly(self):
    original_value = export_test_lib.DataAgnosticConverterTestValue(
        string_value="string value",
        int_value=42,
        bool_value=True,
        enum_value=export_test_lib.DataAgnosticConverterTestValue.EnumOption
        .OPTION_2,
        urn_value=rdfvalue.RDFURN("aff4:/bar"),
        datetime_value=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42))
    converted_value = self.ConvertOriginalValue(original_value)

    self.assertEqual(converted_value.string_value.__class__,
                     original_value.string_value.__class__)
    self.assertEqual(converted_value.string_value, "string value")

    self.assertEqual(converted_value.int_value.__class__,
                     original_value.int_value.__class__)
    self.assertEqual(converted_value.int_value, 42)

    self.assertEqual(converted_value.bool_value.__class__,
                     original_value.bool_value.__class__)
    self.assertEqual(converted_value.bool_value, True)

    self.assertEqual(converted_value.enum_value.__class__,
                     original_value.enum_value.__class__)
    self.assertEqual(converted_value.enum_value,
                     converted_value.EnumOption.OPTION_2)

    self.assertIsInstance(converted_value.urn_value, rdfvalue.RDFURN)
    self.assertEqual(converted_value.urn_value, rdfvalue.RDFURN("aff4:/bar"))

    self.assertIsInstance(converted_value.datetime_value, rdfvalue.RDFDatetime)
    self.assertEqual(converted_value.datetime_value,
                     rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42))

  def testConvertedValuesCanBeSerializedAndDeserialized(self):
    original_value = export_test_lib.DataAgnosticConverterTestValue(
        string_value="string value",
        int_value=42,
        bool_value=True,
        enum_value=export_test_lib.DataAgnosticConverterTestValue.EnumOption
        .OPTION_2,
        urn_value=rdfvalue.RDFURN("aff4:/bar"),
        datetime_value=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42))
    converted_value = self.ConvertOriginalValue(original_value)

    serialized = converted_value.SerializeToBytes()
    deserialized = converted_value.__class__.FromSerializedBytes(serialized)

    self.assertEqual(converted_value, deserialized)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
