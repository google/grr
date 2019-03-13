#!/usr/bin/env python
"""E2E tests for the osquery flow."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_test.end_to_end_tests import test_base


class TestOsquery(test_base.EndToEndTest):
  """Class with generic osquery tests runnable on every platform."""

  MANUAL = True
  platforms = test_base.EndToEndTest.Platform.ALL

  def testOsVersion(self):
    args = self.grr_api.types.CreateFlowArgs("OsqueryFlow")
    args.query = """SELECT name FROM os_version;"""
    args.ignore_stderr_errors = True  # Windows client prints spurious warnings.

    flow = self.RunFlowAndWait("OsqueryFlow", args=args)
    results = list(flow.ListResults())

    self.assertLen(results, 1)

    table = results[0].payload.table
    self.assertEqual(table.query, args.query)
    self.assertLen(table.header.columns, 1)
    self.assertEqual(table.header.columns[0].name, "name")
    self.assertLen(table.rows, 1)
    self.assertLen(table.rows[0].values, 1)

    os_name = table.rows[0].values[0]
    if self.platform == test_base.EndToEndTest.Platform.DARWIN:
      self.assertEqual(os_name, "Mac OS X")
    elif self.platform == test_base.EndToEndTest.Platform.LINUX:
      # e.g. for Debian it is 'Debian GNU/Linux'.
      self.assertIn("Linux", os_name)
    elif self.platform == test_base.EndToEndTest.Platform.WINDOWS:
      # e.g. 'Microsoft Windows 10 Enterprise'
      self.assertIn("Windows", os_name)
    else:
      self.fail("Unexpected platform: {}".format(self.platform))

  def testProcesses(self):
    args = self.grr_api.types.CreateFlowArgs("OsqueryFlow")
    args.query = """
    SELECT path
      FROM osquery_info JOIN processes
        ON osquery_info.pid = processes.pid;
    """
    args.ignore_stderr_errors = True  # Windows client prints spurious warnings.

    flow = self.RunFlowAndWait("OsqueryFlow", args=args)
    results = list(flow.ListResults())

    self.assertLen(results, 1)

    table = results[0].payload.table
    self.assertEqual(table.query, args.query)
    self.assertLen(table.header.columns, 1)
    self.assertEqual(table.header.columns[0].name, "path")
    self.assertLen(table.rows, 1)
    self.assertLen(table.rows[0].values, 1)

    # We are not sure about the path, but the executable should contain name
    # `osquery.exe` (e.g. on Windows we use `osqueryd` but on Linux and macOS we
    # use `osqueryi`.
    path = table.rows[0].values[0]
    self.assertIn("osquery", path)
