#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for nfs export checks."""

from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.checks import checks_test_lib
from grr.parsers import config_file


class NfsExportsTests(checks_test_lib.HostCheckTest):

  def testNfsExportsCheck(self):
    """Ensure NFS export checks work as expected."""
    self.LoadCheck("nfs.yaml")

    # Create some host_data..
    host_data = {}
    self.SetKnowledgeBase("test.example.com", "Linux", host_data)

    parser = config_file.NfsExportsParser()

    with open(self.TestDataPath("exports")) as export_fd:
      host_data["NfsExportsFile"] = list(parser.Parse(None, export_fd, None))
    results = self.RunChecks(host_data)
    anom = rdfvalue.Anomaly(
        explanation="Found: Default r/w NFS exports are too permissive.",
        finding=["/path/to/foo: defaults:rw,sync hosts:host1,host2 options:ro",
                 ("/path/to/bar: defaults:rw "
                  "hosts:*.example.org,192.168.1.0/24 "
                  "options:all_squash,ro")],
        type="ANALYSIS_ANOMALY")
    expected = rdfvalue.CheckResult(check_id="CCE-4350-5", anomaly=anom)
    self.assertResultEqual(expected, results["CCE-4350-5"])


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)

