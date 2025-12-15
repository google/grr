#!/usr/bin/env python
from absl import app
from absl.testing import absltest

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import cronjobs as rdf_cronjobs
from grr_response_proto import export_pb2
from grr_response_proto import sysinfo_pb2
from grr_response_server.export_converters import base
from grr_response_server.export_converters import cron_tab_file
from grr.test_lib import export_test_lib
from grr.test_lib import test_lib


class CronTabFileConverterTest(export_test_lib.ExportTestBase):
  """Tests for CronTabFile converter."""

  def testExportsFileWithTwoEntries(self):
    sample = rdf_cronjobs.CronTabFile(
        path="/etc/foo.cron",
        jobs=[
            rdf_cronjobs.CronTabEntry(
                minute="1",
                hour="2",
                dayofmonth="3",
                month="4",
                dayofweek="1",
                command="bash",
                comment="foo",
            ),
            rdf_cronjobs.CronTabEntry(
                minute="aa",
                hour="bb",
                dayofmonth="cc",
                month="dd",
                dayofweek="ee",
                command="ps",
                comment="some",
            ),
        ],
    )

    converter = cron_tab_file.CronTabFileConverter()
    converted = list(
        converter.Convert(base.ExportedMetadata(self.metadata), sample)
    )

    self.assertLen(converted, 2)
    self.assertIsInstance(converted[0], cron_tab_file.ExportedCronTabEntry)

    self.assertEqual(converted[0].metadata, self.metadata)
    self.assertEqual(converted[0].cron_file_path, "/etc/foo.cron")
    self.assertEqual(converted[0].minute, "1")
    self.assertEqual(converted[0].hour, "2")
    self.assertEqual(converted[0].dayofmonth, "3")
    self.assertEqual(converted[0].month, "4")
    self.assertEqual(converted[0].dayofweek, "1")
    self.assertEqual(converted[0].command, "bash")
    self.assertEqual(converted[0].comment, "foo")

    self.assertEqual(converted[1].metadata, self.metadata)
    self.assertEqual(converted[1].cron_file_path, "/etc/foo.cron")
    self.assertEqual(converted[1].minute, "aa")
    self.assertEqual(converted[1].hour, "bb")
    self.assertEqual(converted[1].dayofmonth, "cc")
    self.assertEqual(converted[1].month, "dd")
    self.assertEqual(converted[1].dayofweek, "ee")
    self.assertEqual(converted[1].command, "ps")
    self.assertEqual(converted[1].comment, "some")


class CronTabFileToExportedCronTabEntryProtoTest(absltest.TestCase):
  """Tests for CronTabFileToExportedCronTabEntryProto."""

  def setUp(self):
    super().setUp()
    self.client_id = "C.1234567890123456"
    self.metadata_proto = export_pb2.ExportedMetadata(
        client_urn=rdf_client.ClientURN(self.client_id).SerializeToWireFormat(),
        client_id=self.client_id,
    )

  def testExportsFileWithTwoEntries(self):
    sample = sysinfo_pb2.CronTabFile(
        path="/etc/foo.cron",
        jobs=[
            sysinfo_pb2.CronTabEntry(
                minute="1",
                hour="2",
                dayofmonth="3",
                month="4",
                dayofweek="1",
                command="bash",
                comment="foo",
            ),
            sysinfo_pb2.CronTabEntry(
                minute="aa",
                hour="bb",
                dayofmonth="cc",
                month="dd",
                dayofweek="ee",
                command="ps",
                comment="some",
            ),
        ],
    )

    converter = cron_tab_file.CronTabFileToExportedCronTabEntryProto()
    converted = list(converter.Convert(self.metadata_proto, sample))

    self.assertLen(converted, 2)
    self.assertIsInstance(converted[0], export_pb2.ExportedCronTabEntry)

    self.assertEqual(converted[0].metadata, self.metadata_proto)
    self.assertEqual(converted[0].cron_file_path, "/etc/foo.cron")
    self.assertEqual(converted[0].minute, "1")
    self.assertEqual(converted[0].hour, "2")
    self.assertEqual(converted[0].dayofmonth, "3")
    self.assertEqual(converted[0].month, "4")
    self.assertEqual(converted[0].dayofweek, "1")
    self.assertEqual(converted[0].command, "bash")
    self.assertEqual(converted[0].comment, "foo")

    self.assertEqual(converted[1].metadata, self.metadata_proto)
    self.assertEqual(converted[1].cron_file_path, "/etc/foo.cron")
    self.assertEqual(converted[1].minute, "aa")
    self.assertEqual(converted[1].hour, "bb")
    self.assertEqual(converted[1].dayofmonth, "cc")
    self.assertEqual(converted[1].month, "dd")
    self.assertEqual(converted[1].dayofweek, "ee")
    self.assertEqual(converted[1].command, "ps")
    self.assertEqual(converted[1].comment, "some")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
