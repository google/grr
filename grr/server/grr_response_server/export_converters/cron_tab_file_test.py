#!/usr/bin/env python
from absl import app

from grr_response_core.lib.rdfvalues import cronjobs as rdf_cronjobs
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


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
