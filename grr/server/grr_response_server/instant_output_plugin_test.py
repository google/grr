#!/usr/bin/env python
"""Tests for grr.lib.output_plugin."""

import io

from absl import app

from grr_response_core.lib import rdfvalue
from grr_response_server.export_converters import base
from grr_response_server.output_plugins import test_plugins
from grr.test_lib import export_test_lib
from grr.test_lib import test_lib


class DummySrcValue1(rdfvalue.RDFString):
  pass


class DummySrcValue2(rdfvalue.RDFString):
  pass


class DummyOutValue1(rdfvalue.RDFString):
  pass


class DummyOutValue2(rdfvalue.RDFString):
  pass


class TestConverter1(base.ExportConverter):
  input_rdf_type = DummySrcValue1

  def Convert(self, metadata, value):
    return [DummyOutValue1("exp-" + str(value))]


class TestConverter2(base.ExportConverter):
  input_rdf_type = DummySrcValue2

  def Convert(self, metadata, value):
    _ = metadata
    return [
        DummyOutValue1("exp1-" + str(value)),
        DummyOutValue2("exp2-" + str(value))
    ]


class InstantOutputPluginWithExportConversionTest(
    test_plugins.InstantOutputPluginTestBase):
  """Tests for InstantOutputPluginWithExportConversion."""

  plugin_cls = test_plugins.TestInstantOutputPluginWithExportConverstion

  def ProcessValuesToLines(self, values_by_cls):
    fd_name = self.ProcessValues(values_by_cls)
    with io.open(fd_name, mode="r", encoding="utf-8") as fd:
      return fd.read().split("\n")

  @export_test_lib.WithAllExportConverters
  @export_test_lib.WithExportConverter(TestConverter1)
  @export_test_lib.WithExportConverter(TestConverter2)
  def testWorksCorrectlyWithOneSourceValueAndOneExportedValue(self):
    lines = self.ProcessValuesToLines({DummySrcValue1: [DummySrcValue1("foo")]})
    self.assertListEqual(lines, [
        "Start",
        "Original: DummySrcValue1",
        "Exported value: exp-foo",
        "Finish"
    ])  # pyformat: disable

  @export_test_lib.WithAllExportConverters
  @export_test_lib.WithExportConverter(TestConverter1)
  @export_test_lib.WithExportConverter(TestConverter2)
  def testWorksCorrectlyWithOneSourceValueAndTwoExportedValues(self):
    lines = self.ProcessValuesToLines({DummySrcValue2: [DummySrcValue2("foo")]})
    self.assertListEqual(lines, [
        "Start",
        "Original: DummySrcValue2",
        "Exported value: exp1-foo",
        "Original: DummySrcValue2",
        "Exported value: exp2-foo",
        "Finish"
    ])  # pyformat: disable

  @export_test_lib.WithAllExportConverters
  @export_test_lib.WithExportConverter(TestConverter1)
  @export_test_lib.WithExportConverter(TestConverter2)
  def testWorksCorrectlyWithTwoSourceValueAndTwoExportedValuesEach(self):
    lines = self.ProcessValuesToLines(
        {DummySrcValue2: [DummySrcValue2("foo"),
                          DummySrcValue2("bar")]})
    self.assertListEqual(lines, [
        "Start",
        "Original: DummySrcValue2",
        "Exported value: exp1-foo",
        "Exported value: exp1-bar",
        "Original: DummySrcValue2",
        "Exported value: exp2-foo",
        "Exported value: exp2-bar",
        "Finish"
    ])  # pyformat: disable

  @export_test_lib.WithAllExportConverters
  @export_test_lib.WithExportConverter(TestConverter1)
  @export_test_lib.WithExportConverter(TestConverter2)
  def testWorksCorrectlyWithTwoDifferentTypesOfSourceValues(self):
    lines = self.ProcessValuesToLines({
        DummySrcValue1: [DummySrcValue1("foo")],
        DummySrcValue2: [DummySrcValue2("bar")],
    })
    self.assertListEqual(lines, [
        "Start",
        "Original: DummySrcValue1",
        "Exported value: exp-foo",
        "Original: DummySrcValue2",
        "Exported value: exp1-bar",
        "Original: DummySrcValue2",
        "Exported value: exp2-bar",
        "Finish"
    ])  # pyformat: disable


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
