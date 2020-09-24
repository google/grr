#!/usr/bin/env python
# Lint as: python3
"""Tests for grr.lib.output_plugin."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io

from absl import app

from grr_response_core.lib import rdfvalue
from grr_response_server import export
from grr_response_server.output_plugins import test_plugins
from grr.test_lib import test_lib


class DummySrcValue1(rdfvalue.RDFString):
  pass


class DummySrcValue2(rdfvalue.RDFString):
  pass


class DummyOutValue1(rdfvalue.RDFString):
  pass


class DummyOutValue2(rdfvalue.RDFString):
  pass


class TestConverter1(export.ExportConverter):
  input_rdf_type = DummySrcValue1

  def Convert(self, metadata, value):
    return [DummyOutValue1("exp-" + str(value))]


class TestConverter2(export.ExportConverter):
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

  def testWorksCorrectlyWithOneSourceValueAndOneExportedValue(self):
    lines = self.ProcessValuesToLines({DummySrcValue1: [DummySrcValue1("foo")]})
    self.assertListEqual(lines, [
        "Start",
        "Original: DummySrcValue1",
        "Exported value: exp-foo",
        "Finish"
    ])  # pyformat: disable

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
