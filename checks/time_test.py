#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the time synchronization state checks."""

from grr.lib import flags
from grr.lib import test_lib
from grr.lib.checks import checks_test_lib
from grr.parsers import config_file


class TimeSyncTests(checks_test_lib.HostCheckTest):

  checks_loaded = False

  def setUp(self, *args, **kwargs):
    super(TimeSyncTests, self).setUp(*args, **kwargs)
    if not self.checks_loaded:
      self.LoadCheck("time.yaml")
      self.checks_loaded = True

  def testTimeSyncBoot(self):
    """Test we handle the cases for when a time service is started at boot."""

    exp = ("Missing attribute: No time synchronization service is started "
           "at boot time.")
    found = ["Expected state was not found"]
    bad = []
    good = ["/etc/rc2.d/S07ntp"]

    # The failure cases. I.e. No startup file for a time service.

    self.assertCheckDetectedAnom("TIME-SYNC-BOOT",
                                 self.RunChecks(self.GenSysVInitData(bad)),
                                 exp, found)
    # Now the successful cases.
    self.assertCheckUndetected("TIME-SYNC-BOOT",
                               self.RunChecks(self.GenSysVInitData(good)))

  def testTimeSyncRunning(self):
    """Test we handle the cases for when a time service is running or not."""

    found = ["Expected state was not found"]
    bad = [("foo", 233, ["/usr/local/foo", "-flags"])]
    good = [("ntpd", 42, ["/usr/sbin/ntpd", "-p", "/var/run/ntpd.pid",
                          "-g", "-u", "117:125"])]

    # Check for when it is not running.

    self.assertCheckDetectedAnom(
        "TIME-SYNC-RUNNING", self.RunChecks(self.GenProcessData(bad)),
        "Missing attribute: A time synchronization service is not running.",
        found)
    # Now check for when it is.
    self.assertCheckUndetected("TIME-SYNC-RUNNING",
                               self.RunChecks(self.GenProcessData(good)))

  def testNtpDoesntAllowOpenQueries(self):
    """Test for checking we don't allow queries by default."""
    good_config = {"/etc/ntp.conf": """
        restrict default nomodify noquery nopeer
        """}
    bad_config = {"/etc/ntp.conf": """
        restrict default nomodify nopeer
        """}
    bad_default_config = {"/etc/ntp.conf": """
        """}

    # A good config should pass.
    self.assertCheckUndetected(
        "TIME-NTP-VULN-2014-12",
        self.RunChecks(self.GenFileData("NtpConfFile", good_config,
                                        parser=config_file.NtpdParser)))
    # A bad one should detect a problem.
    found = ["Expected state was not found"]
    exp = ("Missing attribute: ntpd.conf is configured or defaults to open "
           "queries. Can allow DDoS.")
    self.assertCheckDetectedAnom(
        "TIME-NTP-VULN-2014-12",
        self.RunChecks(self.GenFileData("NtpConfFile", bad_config,
                                        parser=config_file.NtpdParser)),
        exp, found)
    # And as the default is to be queryable, check we detect an empty config.
    self.assertCheckDetectedAnom(
        "TIME-NTP-VULN-2014-12",
        self.RunChecks(self.GenFileData("NtpConfFile", bad_default_config,
                                        parser=config_file.NtpdParser)),
        exp, found)

  def testNtpHasMonitorDisabled(self):
    """Test for checking that monitor is disabled."""
    good_config = {"/etc/ntp.conf": """
        disable monitor
        """}
    good_tricky_config = {"/etc/ntp.conf": """
        disable monitor auth
        enable kernel monitor auth
        disable kernel monitor
        """}
    bad_config = {"/etc/ntp.conf": """
        enable monitor
        """}
    bad_default_config = {"/etc/ntp.conf": """
        """}
    bad_tricky_config = {"/etc/ntp.conf": """
        enable kernel monitor auth
        disable monitor auth
        enable kernel monitor
        """}
    found = ["ntpd.conf has monitor flag set to True."]
    exp = ("Found: ntpd.conf is configured to allow monlist NTP reflection "
           "attacks.")

    self.assertCheckUndetected(
        "TIME-NTP-REFLECTION",
        self.RunChecks(self.GenFileData("NtpConfFile", good_config,
                                        parser=config_file.NtpdParser)))

    self.assertCheckUndetected(
        "TIME-NTP-REFLECTION",
        self.RunChecks(self.GenFileData("NtpConfFile", good_tricky_config,
                                        parser=config_file.NtpdParser)))

    self.assertCheckDetectedAnom(
        "TIME-NTP-REFLECTION",
        self.RunChecks(self.GenFileData("NtpConfFile", bad_config,
                                        parser=config_file.NtpdParser)),
        exp, found)

    self.assertCheckDetectedAnom(
        "TIME-NTP-REFLECTION",
        self.RunChecks(self.GenFileData("NtpConfFile", bad_default_config,
                                        parser=config_file.NtpdParser)),
        exp, found)

    self.assertCheckDetectedAnom(
        "TIME-NTP-REFLECTION",
        self.RunChecks(self.GenFileData("NtpConfFile", bad_tricky_config,
                                        parser=config_file.NtpdParser)),
        exp, found)


def main(argv):
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
