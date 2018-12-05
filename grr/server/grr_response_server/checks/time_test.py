#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the time synchronization state checks."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags
from grr_response_core.lib.parsers import config_file
from grr_response_server.check_lib import checks_test_lib
from grr.test_lib import test_lib


class TimeSyncTests(checks_test_lib.HostCheckTest):

  checks_loaded = False

  def setUp(self, *args, **kwargs):
    super(TimeSyncTests, self).setUp(*args, **kwargs)
    if not self.checks_loaded:
      self.LoadCheck("time.yaml")
      self.checks_loaded = True

  def testTimeSyncBoot(self):
    """Test we handle the cases for when a time service is started at boot."""

    sym = ("Missing attribute: No time synchronization service is started "
           "at boot time.")
    found = ["Expected state was not found"]
    bad = []
    good = ["/etc/rc2.d/S07ntp"]

    # The failure cases. I.e. No startup file for a time service.
    results = self.RunChecks(self.GenSysVInitData(bad))
    self.assertCheckDetectedAnom("TIME-SYNC-BOOT", results, sym, found)

    # Now the successful cases.
    results = self.RunChecks(self.GenSysVInitData(good))
    self.assertCheckUndetected("TIME-SYNC-BOOT", results)

  def testTimeSyncRunning(self):
    """Test we handle the cases for when a time service is running or not."""

    found = ["Expected state was not found"]
    bad = [("foo", 233, ["/usr/local/foo", "-flags"])]
    good = [("ntpd", 42, [
        "/usr/sbin/ntpd", "-p", "/var/run/ntpd.pid", "-g", "-u", "117:125"
    ])]

    # Check for when it is not running.

    self.assertCheckDetectedAnom(
        "TIME-SYNC-RUNNING",
        self.RunChecks(self.GenProcessData(bad)),
        "Missing attribute: A time synchronization service is not running.",
        found)
    # Now check for when it is.
    self.assertCheckUndetected("TIME-SYNC-RUNNING",
                               self.RunChecks(self.GenProcessData(good)))

  def testNtpDoesntAllowOpenQueries(self):
    """Test for checking we don't allow queries by default."""
    parser = config_file.NtpdParser()

    check_id = "TIME-NTP-NO-OPEN-QUERIES"
    artifact_id = "NtpConfFile"
    good_config = {
        "/etc/ntp.conf":
            """
        restrict default nomodify noquery nopeer
        """
    }
    bad_config = {
        "/etc/ntp.conf":
            """
        restrict default nomodify nopeer
        """
    }
    bad_default_config = {"/etc/ntp.conf": """
        """}

    # A good config should pass.
    results = self.RunChecks(
        self.GenFileData("NtpConfFile", good_config, parser))
    self.assertCheckUndetected(check_id, results)

    found = ["Expected state was not found"]
    sym = ("Missing attribute: ntpd.conf is configured or defaults to open "
           "queries. Can allow DDoS. This configuration is an on-going "
           "recommendation following the Ntp December 2014 Vulnerability "
           "notice. (http://support.ntp.org/bin/view/Main/SecurityNotice)")
    # A bad one should detect a problem.
    results = self.RunChecks(self.GenFileData(artifact_id, bad_config, parser))
    self.assertCheckDetectedAnom(check_id, results, sym, found)

    # And as the default is to be queryable, check we detect an empty config.
    results = self.RunChecks(
        self.GenFileData(artifact_id, bad_default_config, parser))
    self.assertCheckDetectedAnom(check_id, results, sym, found)

  def testNtpHasMonitorDisabled(self):
    """Test for checking that monitor is disabled."""
    parser = config_file.NtpdParser()

    check_id = "TIME-NTP-REFLECTION"
    artifact_id = "NtpConfFile"
    good_config = {"/etc/ntp.conf": """
        disable monitor
        """}
    good_tricky_config = {
        "/etc/ntp.conf":
            """
        disable monitor auth
        enable kernel monitor auth
        disable kernel monitor
        """
    }
    bad_config = {"/etc/ntp.conf": """
        enable monitor
        """}
    bad_default_config = {"/etc/ntp.conf": """
        """}
    bad_tricky_config = {
        "/etc/ntp.conf":
            """
        enable kernel monitor auth
        disable monitor auth
        enable kernel monitor
        """
    }
    found = ["ntpd.conf has monitor flag set to True."]
    sym = ("Found: ntpd.conf is configured to allow monlist NTP reflection "
           "attacks.")

    results = self.RunChecks(self.GenFileData(artifact_id, good_config, parser))
    self.assertCheckUndetected(check_id, results)

    results = self.RunChecks(
        self.GenFileData(artifact_id, good_tricky_config, parser))
    self.assertCheckUndetected(check_id, results)

    results = self.RunChecks(self.GenFileData(artifact_id, bad_config, parser))
    self.assertCheckDetectedAnom(check_id, results, sym, found)

    results = self.RunChecks(
        self.GenFileData(artifact_id, bad_default_config, parser))
    self.assertCheckDetectedAnom(check_id, results, sym, found)

    results = self.RunChecks(
        self.GenFileData(artifact_id, bad_tricky_config, parser))
    self.assertCheckDetectedAnom(check_id, results, sym, found)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
