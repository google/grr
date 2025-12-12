#!/usr/bin/env python
from absl import app
from absl.testing import absltest

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import memory as rdf_memory
from grr_response_proto import export_pb2
from grr_response_proto import flows_pb2
from grr_response_proto import sysinfo_pb2
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
        ctime=1333718907167083,
    )
    return rdf_memory.YaraProcessScanMatch(
        process=process, match=match, scan_time_us=42, **kwargs
    )

  def testExportsSingleMatchCorrectly(self):
    sample = self.GenerateSample([
        rdf_memory.YaraMatch(
            rule_name="foo",
            string_matches=[
                rdf_memory.YaraStringMatch(
                    string_id="bar", offset=5, context=b"blahcontextblah"
                )
            ],
        )
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
    self.assertEqual(converted[0].context, b"blahcontextblah")

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
            ],
        ),
        rdf_memory.YaraMatch(
            rule_name="foo2",
            string_matches=[
                rdf_memory.YaraStringMatch(string_id="bar3", offset=15),
            ],
        ),
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


class YaraProcessScanMatchConverterProtoTest(absltest.TestCase):
  """Tests for YaraProcessScanMatchConverterProto."""

  def setUp(self):
    super().setUp()
    self.client_id = "C.1234567890123456"
    self.metadata_proto = export_pb2.ExportedMetadata(
        client_urn=rdf_client.ClientURN(self.client_id).SerializeToWireFormat(),
        client_id=self.client_id,
    )

  def testExportsSingleMatchCorrectly(self):
    sample = flows_pb2.YaraProcessScanMatch(
        process=sysinfo_pb2.Process(
            pid=2,
            ppid=1,
            cmdline=["cmd.exe"],
            exe="c:\\windows\\cmd.exe",
            ctime=1333718907167083,
        ),
        scan_time_us=42,
        match=[
            flows_pb2.YaraMatch(
                rule_name="foo",
                string_matches=[
                    flows_pb2.YaraStringMatch(
                        string_id="bar", offset=5, context=b"blahcontextblah"
                    )
                ],
            )
        ],
    )

    converter = memory.YaraProcessScanMatchConverterProto()
    converted = list(converter.Convert(self.metadata_proto, sample))

    self.assertLen(converted, 1)

    self.assertIsInstance(converted[0], export_pb2.ExportedYaraProcessScanMatch)
    self.assertEqual(converted[0].metadata, self.metadata_proto)
    self.assertEqual(converted[0].process.pid, 2)
    self.assertEqual(converted[0].process.ppid, 1)
    self.assertEqual(converted[0].process.cmdline, "cmd.exe")
    self.assertEqual(converted[0].process.exe, "c:\\windows\\cmd.exe")
    self.assertEqual(converted[0].process.ctime, 1333718907167083)
    self.assertEqual(converted[0].rule_name, "foo")
    self.assertEqual(converted[0].process_scan_time_us, 42)
    self.assertEqual(converted[0].string_id, "bar")
    self.assertEqual(converted[0].offset, 5)
    self.assertEqual(converted[0].context, b"blahcontextblah")

  def testExportsOneYaraMatchForEmptyYaraMatch(self):
    sample = flows_pb2.YaraProcessScanMatch(
        process=sysinfo_pb2.Process(
            pid=2,
            ppid=1,
            cmdline=["cmd.exe"],
            exe="c:\\windows\\cmd.exe",
            ctime=1333718907167083,
        ),
        scan_time_us=42,
    )

    converter = memory.YaraProcessScanMatchConverterProto()
    converted = list(converter.Convert(self.metadata_proto, sample))

    self.assertLen(converted, 1)
    self.assertEqual(converted[0].process_scan_time_us, 42)
    self.assertEqual(converted[0].process.pid, 2)

  def testExportsOneYaraMatchForEmptyYaraStringMatch(self):
    sample = flows_pb2.YaraProcessScanMatch(
        process=sysinfo_pb2.Process(
            pid=2,
            ppid=1,
            cmdline=["cmd.exe"],
            exe="c:\\windows\\cmd.exe",
            ctime=1333718907167083,
        ),
        scan_time_us=43,
        match=[flows_pb2.YaraMatch(rule_name="foo")],
    )

    converter = memory.YaraProcessScanMatchConverterProto()
    converted = list(converter.Convert(self.metadata_proto, sample))

    self.assertLen(converted, 1)
    self.assertEqual(converted[0].process_scan_time_us, 43)
    self.assertEqual(converted[0].rule_name, "foo")
    self.assertEqual(converted[0].process.pid, 2)

  def testExportsOneYaraMatchPerYaraStringMatch(self):
    sample = flows_pb2.YaraProcessScanMatch(
        process=sysinfo_pb2.Process(
            pid=2,
            ppid=1,
            cmdline=["cmd.exe"],
            exe="c:\\windows\\cmd.exe",
            ctime=1333718907167083,
        ),
        scan_time_us=44,
        match=[
            flows_pb2.YaraMatch(
                rule_name="foo1",
                string_matches=[
                    flows_pb2.YaraStringMatch(string_id="bar1", offset=5),
                    flows_pb2.YaraStringMatch(string_id="bar2", offset=10),
                ],
            ),
            flows_pb2.YaraMatch(
                rule_name="foo2",
                string_matches=[
                    flows_pb2.YaraStringMatch(string_id="bar3", offset=15),
                ],
            ),
        ],
    )

    converter = memory.YaraProcessScanMatchConverterProto()
    converted = list(converter.Convert(self.metadata_proto, sample))

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
        ctime=1333718907167083,
    )
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


class ProcessMemoryErrorConverterProtoTest(absltest.TestCase):
  """Tests for ProcessMemoryErrorConverterProto."""

  def setUp(self):
    super().setUp()
    self.client_id = "C.1234567890123456"
    self.metadata_proto = export_pb2.ExportedMetadata(
        client_urn=rdf_client.ClientURN(self.client_id).SerializeToWireFormat(),
        client_id=self.client_id,
    )

  def testExportsErrorCorrectly(self):
    sample = flows_pb2.ProcessMemoryError(
        process=sysinfo_pb2.Process(
            pid=2,
            ppid=1,
            cmdline=["cmd.exe"],
            exe="c:\\windows\\cmd.exe",
            ctime=1333718907167083,
        ),
        error="foo bar",
    )

    converter = memory.ProcessMemoryErrorConverterProto()
    converted = list(converter.Convert(self.metadata_proto, sample))

    self.assertLen(converted, 1)
    self.assertIsInstance(converted[0], export_pb2.ExportedProcessMemoryError)
    self.assertEqual(converted[0].metadata, self.metadata_proto)
    self.assertEqual(converted[0].process.cmdline, "cmd.exe")
    self.assertEqual(converted[0].error, "foo bar")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
