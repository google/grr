#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for rsyslog state checks."""


from grr.lib import flags
from grr.lib import test_lib
from grr.lib.checks import checks_test_lib
from grr.lib.rdfvalues import client as rdf_client
from grr.parsers import config_file


class RsyslogCheckTests(checks_test_lib.HostCheckTest):
  """Test the rsyslog checks."""

  check_loaded = False
  parser = None

  def setUp(self, *args, **kwargs):
    super(RsyslogCheckTests, self).setUp(*args, **kwargs)
    if not self.check_loaded:
      self.check_loaded = self.LoadCheck("rsyslog.yaml")
    if not self.parser:
      self.parser = config_file.RsyslogParser()

  def testLoggingAuthRemoteOK(self):
    chk_id = "CIS-LOGGING-AUTH-REMOTE"

    test_data = {"/etc/rsyslog.conf":
                 "*.* @@tcp.example.com.:514;RSYSLOG_ForwardFormat"}
    host_data = self.GetParsedMultiFile("LinuxRsyslogConfigs", test_data,
                                        self.parser)
    results = self.RunChecks(host_data)
    self.assertCheckUndetected(chk_id, results)

  def testLoggingAuthRemoteFail(self):
    chk_id = "CIS-LOGGING-AUTH-REMOTE"

    test_data = {"/etc/rsyslog.conf": "*.* /var/log/messages"}
    host_data = self.GetParsedMultiFile("LinuxRsyslogConfigs", test_data,
                                        self.parser)
    exp = "Missing attribute: No remote destination for auth logs."
    results = self.RunChecks(host_data)
    self.assertCheckDetectedAnom(chk_id, results, exp, [])

  def testLoggingFilePermissions(self):
    chk_id = "CIS-LOGGING-FILE-PERMISSIONS"

    ro = rdf_client.StatEntry(st_uid=0, st_gid=0, st_mode=0100640)
    ro.pathspec.path = "/test/ro"
    ro.pathspec.pathtype = "OS"
    rw = rdf_client.StatEntry(st_uid=0, st_gid=0, st_mode=0100666)
    rw.pathspec.path = "/test/rw"
    rw.pathspec.pathtype = "OS"

    host_data = self.SetKnowledgeBase()
    host_data["LinuxRsyslogConfigs"] = self.SetArtifactData(raw=[ro, rw])
    exp = "Found: Log configurations can be modified by non-privileged users."
    found = ["/test/rw user: 0, group: 0, mode: -rw-rw-rw-"]
    results = self.RunChecks(host_data)
    self.assertCheckDetectedAnom(chk_id, results, exp, found)


def main(argv):
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)

