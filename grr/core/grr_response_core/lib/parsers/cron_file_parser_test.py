#!/usr/bin/env python
"""Tests for grr.parsers.cron_file_parser."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os


from grr_response_core.lib import flags
from grr_response_core.lib.parsers import cron_file_parser
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr.test_lib import test_lib


class TestCronTabParsing(test_lib.GRRBaseTest):
  """Test parsing of cron files."""

  def testCronTabParser(self):
    """Ensure we can extract jobs from a crontab file."""
    parser = cron_file_parser.CronTabParser()
    results = []

    path = os.path.join(self.base_path, "parser_test", "crontab")
    plist_file = open(path, "rb")
    stat = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(
            path=path, pathtype=rdf_paths.PathSpec.PathType.OS),
        st_mode=16877)
    results.extend(list(parser.Parse(stat, plist_file, None)))

    self.assertLen(results, 1)

    for result in results:
      self.assertEqual(result.jobs[0].minute, "1")
      self.assertEqual(result.jobs[0].hour, "2")
      self.assertEqual(result.jobs[0].dayofmonth, "3")
      self.assertEqual(result.jobs[0].month, "4")
      self.assertEqual(result.jobs[0].dayofweek, "5")
      self.assertEqual(result.jobs[0].command, "/usr/bin/echo \"test\"")


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  flags.StartMain(main)
