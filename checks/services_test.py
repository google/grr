#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for service state checks."""

from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.checks import checks_test_lib
from grr.parsers import linux_service_parser
from grr.parsers import linux_service_parser_test


class XinetdServiceStateTests(checks_test_lib.HostCheckTest):

  check_loaded = False
  parser = None

  def setUp(self, *args, **kwargs):
    super(XinetdServiceStateTests, self).setUp(*args, **kwargs)
    if not self.check_loaded:
      self.check_loaded = self.LoadCheck("services.yaml")
    if not self.parser:
      self.parser = linux_service_parser.LinuxXinetdParser().ParseMultiple

  def RunXinetdCheck(self, chk_id, svc, disabled, exp, found):
    host_data = self.SetKnowledgeBase()
    cfgs = linux_service_parser_test.GenXinetd(svc, disabled)
    stats, files = linux_service_parser_test.GenTestData(cfgs, cfgs.values())
    host_data["LinuxServices"] = list(self.parser(stats, files, None))
    results = self.RunChecks(host_data)
    self.assertCheckDetectedAnom(chk_id, results, exp, found)

  def testEmptyXinetdCheck(self):
    chk_id = "CIS-INETD-WITH-NO-SERVICES"
    exp = "Missing attribute: xinetd running with no xinetd-managed services."
    found = []
    self.RunXinetdCheck(chk_id, "finger", "yes", exp, found)

  def testLegacyXinetdServicesCheck(self):
    chk_id = "CIS-SERVICE-LEGACY-SERVICE-ENABLED"
    exp = "Found: Legacy services are running."
    found = ["telnet is started by XINETD"]
    self.RunXinetdCheck(chk_id, "telnet", "no", exp, found)

  def testUnwantedServicesCheck(self):
    chk_id = "CIS-SERVICE-SHOULD-NOT-RUN"
    exp = "Found: Remote administration services are running."
    found = ["webmin is started by XINETD"]
    self.RunXinetdCheck(chk_id, "webmin", "no", exp, found)


class ListeningServiceTests(checks_test_lib.HostCheckTest):

  check_loaded = False

  def setUp(self, *args, **kwargs):
    super(ListeningServiceTests, self).setUp(*args, **kwargs)
    if not self.check_loaded:
      self.check_loaded = self.LoadCheck("services.yaml")

  def GenHostData(self):
    # Create some host_data..
    host_data = self.SetKnowledgeBase()
    loop4 = self.AddListener("127.0.0.1", 6000)
    loop6 = self.AddListener("::1", 6000, "INET6")
    ext4 = self.AddListener("10.1.1.1", 6000)
    ext6 = self.AddListener("fc00::1", 6000, "INET6")
    x11 = rdfvalue.Process(name="x11", pid=1233, connections=[loop4, loop6])
    xorg = rdfvalue.Process(name="xorg", pid=1234,
                            connections=[loop4, loop6, ext4, ext6])
    sshd = rdfvalue.Process(name="sshd", pid=1235,
                            connections=[loop4, loop6, ext4, ext6])
    host_data["ListProcessesGrr"] = [x11, xorg, sshd]
    return host_data

  def testFindListeningServicesCheck(self):
    chk_id = "CIS-SERVICE-SHOULD-NOT-LISTEN"
    exp = "Found: Insecure services are accessible over the network."
    found = ["xorg (pid 1234) listens on 127.0.0.1,::1,10.1.1.1,fc00::1"]
    host_data = self.GenHostData()
    results = self.RunChecks(host_data)
    self.assertCheckDetectedAnom(chk_id, results, exp, found)


def main(argv):
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)

