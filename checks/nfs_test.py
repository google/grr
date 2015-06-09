#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for nfs export checks."""

from grr.lib import flags
from grr.lib import test_lib
from grr.lib.checks import checks_test_lib
from grr.parsers import config_file


class NfsExportsTests(checks_test_lib.HostCheckTest):

  def testNfsExportsCheck(self):
    """Ensure NFS export checks work as expected."""
    check_id = "CCE-4350-5"
    self.LoadCheck("nfs.yaml")

    host_data = self.SetKnowledgeBase()
    parser = config_file.NfsExportsParser()
    with open(self.TestDataPath("exports")) as export_fd:
      parsed = list(parser.Parse(None, export_fd, None))
      host_data["NfsExportsFile"] = self.SetArtifactData(parsed=parsed)

    results = self.RunChecks(host_data)
    exp = "Found: Default r/w NFS exports are too permissive."
    found = ["/path/to/foo: defaults:rw,sync hosts:host1,host2 options:ro",
             ("/path/to/bar: defaults:rw hosts:*.example.org,192.168.1.0/24 "
              "options:all_squash,ro")]

    self.assertCheckDetectedAnom(check_id, results, exp, found)


def main(argv):
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
