#!/usr/bin/env python
from absl import app

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import memory as rdf_memory
from grr_response_server.export_converters import memory
from grr.test_lib import export_test_lib
from grr.test_lib import test_lib


class YaraProcessScanMatchConverterTest(export_test_lib.ExportTestBase):
  """Tests for YaraProcessScanMatchConverter."""

  def GenerateSample(self, match, **kwargs):
    process = rdf_client.Process(
        pid=2,
        ppid=1,
        cmdline=["cmd.exe"],
        exe="c:\\windows\\cmd.exe",
        ctime=1333718907167083)
    return rdf_memory.YaraProcessScanMatch(
        process=process, match=match, scan_time_us=42, **kwargs)

  def testExportsSingleMatchCorrectly(self):
    sample = self.GenerateSample([
        rdf_memory.YaraMatch(
            rule_name="foo",
            string_matches=[
                rdf_memory.YaraStringMatch(string_id="bar", offset=5)
            ])
    ])

    converter = memory.YaraProcessScanMatchConverter()
    converted = list(converter.Convert(self.metadata, sample))

    self.assertLen(converted, 1)

    self.assertIsInstance(converted[0], memory.ExportedYaraProcessScanMatch)
    self.assertEqual(converted[0].metadata, self.metadata)
    self.assertEqual(converted[0].process.pid, 2)
    self.assertEqual(converted[0].process.ppid, 1)
    self.assertEqual(converted[0].process.cmdline, "cmd.exe")
    self.assertEqual(converted[0].process.exe, "c:\\windows\\cmd.exe")
    self.assertEqual(converted[0].process.ctime, 1333718907167083)
    self.assertEqual(converted[0].rule_name, "foo")
    self.assertEqual(converted[0].process_scan_time_us, 42)
    self.assertEqual(converted[0].string_id, "bar")
    self.assertEqual(converted[0].offset, 5)

  def testExportsOneYaraMatchForEmptyYaraMatch(self):
    sample = self.GenerateSample([])

    converter = memory.YaraProcessScanMatchConverter()
    converted = list(converter.Convert(self.metadata, sample))

    self.assertLen(converted, 1)
    self.assertEqual(converted[0].process_scan_time_us, 42)
    self.assertEqual(converted[0].process.pid, 2)

  def testExportsOneYaraMatchForEmptyYaraStringMatch(self):
    sample = self.GenerateSample([
        rdf_memory.YaraMatch(rule_name="foo"),
    ])

    converter = memory.YaraProcessScanMatchConverter()
    converted = list(converter.Convert(self.metadata, sample))

    self.assertLen(converted, 1)
    self.assertEqual(converted[0].process_scan_time_us, 42)
    self.assertEqual(converted[0].rule_name, "foo")
    self.assertEqual(converted[0].process.pid, 2)

  def testExportsOneYaraMatchPerYaraStringMatch(self):
    sample = self.GenerateSample([
        rdf_memory.YaraMatch(
            rule_name="foo1",
            string_matches=[
                rdf_memory.YaraStringMatch(string_id="bar1", offset=5),
                rdf_memory.YaraStringMatch(string_id="bar2", offset=10),
            ]),
        rdf_memory.YaraMatch(
            rule_name="foo2",
            string_matches=[
                rdf_memory.YaraStringMatch(string_id="bar3", offset=15),
            ]),
    ])

    converter = memory.YaraProcessScanMatchConverter()
    converted = list(converter.Convert(self.metadata, sample))

    self.assertLen(converted, 3)

    self.assertEqual(converted[0].rule_name, "foo1")
    self.assertEqual(converted[0].process.pid, 2)
    self.assertEqual(converted[0].string_id, "bar1")
    self.assertEqual(converted[0].offset, 5)

    self.assertEqual(converted[1].rule_name, "foo1")
    self.assertEqual(converted[1].process.pid, 2)
    self.assertEqual(converted[1].string_id, "bar2")
    self.assertEqual(converted[1].offset, 10)

    self.assertEqual(converted[2].rule_name, "foo2")
    self.assertEqual(converted[2].process.pid, 2)
    self.assertEqual(converted[2].string_id, "bar3")
    self.assertEqual(converted[2].offset, 15)


class YaraProcessMemoryErrorConverterTest(export_test_lib.ExportTestBase):
  """Tests for ProcessMemoryError."""

  def _GenerateSample(self, **kwargs):
    process = rdf_client.Process(
        pid=2,
        ppid=1,
        cmdline=["cmd.exe"],
        exe="c:\\windows\\cmd.exe",
        ctime=1333718907167083)
    return rdf_memory.ProcessMemoryError(process=process, **kwargs)

  def testExportsErrorCorrectly(self):
    sample = self._GenerateSample(error="foo bar")

    converter = memory.ProcessMemoryErrorConverter()
    converted = list(converter.Convert(self.metadata, sample))

    self.assertLen(converted, 1)
    self.assertIsInstance(converted[0], memory.ExportedProcessMemoryError)
    self.assertEqual(converted[0].metadata, self.metadata)
    self.assertEqual(converted[0].process.cmdline, "cmd.exe")
    self.assertEqual(converted[0].error, "foo bar")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
