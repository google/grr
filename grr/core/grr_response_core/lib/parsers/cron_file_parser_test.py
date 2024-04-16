#!/usr/bin/env python
"""Tests for grr.parsers.cron_file_parser."""

import os

from absl import app

from grr_response_core.lib.parsers import cron_file_parser
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
    pathspec = rdf_paths.PathSpec.OS(path=path)
    results.extend(list(parser.ParseFile(None, pathspec, plist_file)))

    self.assertLen(results, 1)

    for result in results:
      self.assertEqual(result.jobs[0].minute, "1")
      self.assertEqual(result.jobs[0].hour, "2")
      self.assertEqual(result.jobs[0].dayofmonth, "3")
      self.assertEqual(result.jobs[0].month, "4")
      self.assertEqual(result.jobs[0].dayofweek, "5")
      self.assertEqual(result.jobs[0].command, '/usr/bin/echo "test"')


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  app.run(main)
