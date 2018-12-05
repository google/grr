#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for nfs export checks."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io


from grr_response_core.lib import flags
from grr_response_core.lib.parsers import config_file
from grr_response_server.check_lib import checks_test_lib
from grr.test_lib import test_lib


class NfsExportsTests(checks_test_lib.HostCheckTest):

  results = None

  @classmethod
  def setUpClass(cls):
    super(NfsExportsTests, cls).setUpClass()

    cls.LoadCheck("nfs.yaml")

  def setUp(self, *args, **kwargs):
    super(NfsExportsTests, self).setUp(*args, **kwargs)
    if not NfsExportsTests.results:
      parser = config_file.NfsExportsParser()
      host_data = self.SetKnowledgeBase()
      with io.open(self.TestDataPath("exports"), "rb") as export_fd:
        parsed = list(parser.Parse(None, export_fd, None))
        host_data["NfsExportsFile"] = self.SetArtifactData(parsed=parsed)
      NfsExportsTests.results = self.RunChecks(host_data)

  def testNfsExportsCheck(self):
    """Ensure NFS export checks work as expected."""
    check_id = "CCE-4350-5"
    sym = "Found: Default r/w NFS exports are too permissive."
    found = [("/path/to/foo: defaults:rw,sync,no_root_squash "
              "hosts:host1,host2 options:ro,sec=sys"),
             ("/path/to/bar: defaults:rw hosts:*.example.org,192.168.1.0/24 "
              "options:all_squash,ro")]
    self.assertCheckDetectedAnom(check_id, self.results, sym, found)

    sym = "Found: Wildcard clients with r/w NFS exports are too permissive."
    found = ["hosts:*.example.org options:rw"]
    self.assertCheckDetectedAnom(check_id, self.results, sym, found)

  def testNfsRootSquashCheck(self):
    check_id = "CCE-4544-3"
    sym = "Found: NFS defaults allow access to the share as root."
    found = [("/path/to/foo: defaults:rw,sync,no_root_squash "
              "hosts:host1,host2 options:ro")]
    self.assertCheckDetectedAnom(check_id, self.results, sym, found)

  def testNfsAuthCheck(self):
    check_id = "CCE-5669-7"
    sym = "Found: NFS shares use no/weak authentication methods."
    found = [
        "/path/to/foo: defaults:rw,sync,no_root_squash options:ro,sec=sys",
        "/path/to/bad: defaults:sec=none options:rw"
    ]
    self.assertCheckDetectedAnom(check_id, self.results, sym, found)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
