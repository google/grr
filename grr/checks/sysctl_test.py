#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for sysctl checks."""

from grr.lib import flags
from grr.lib import test_lib
from grr.lib.checks import checks_test_lib
from grr.parsers import linux_sysctl_parser


class SysctlTests(checks_test_lib.HostCheckTest):

  @classmethod
  def setUpClass(cls):
    cls.LoadCheck("sysctl.yaml")
    cls.parser = linux_sysctl_parser.ProcSysParser()

  def testRPFilter(self):
    """Ensure rp_filter is set to Strict mode.

    rp_filter may be set to three values:
      0 - Disabled
      1 - Strict Reverse Path
      2 - Loose Reverse Path

    See https://www.kernel.org/doc/Documentation/networking/ip-sysctl.txt
    """

    chk_id = "CIS-NET-RP-FILTER"
    test_data = {"/proc/sys/net/ipv4/conf/default/rp_filter": "2"}
    host_data = self.GenFileData("LinuxProcSysHardeningSettings", test_data,
                                 self.parser)
    results = self.RunChecks(host_data)
    sym = "Found: System does not perform path filtering."
    found = ["net_ipv4_conf_default_rp_filter: 2"]
    self.assertCheckDetectedAnom(chk_id, results, sym, found)

    test_data = {"/proc/sys/net/ipv4/conf/default/rp_filter": "1"}
    host_data = self.GenFileData("LinuxProcSysHardeningSettings", test_data,
                                 self.parser)
    results = self.RunChecks(host_data)
    self.assertCheckUndetected(chk_id, results)


def main(argv):
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
