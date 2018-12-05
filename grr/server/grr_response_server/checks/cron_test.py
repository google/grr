#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for cron checks."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from builtins import zip  # pylint: disable=redefined-builtin

from grr_response_core.lib import flags
from grr_response_core.lib.parsers import config_file
from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr_response_server.check_lib import checks
from grr_response_server.check_lib import checks_test_lib
from grr.test_lib import test_lib


class CronCheckTests(checks_test_lib.HostCheckTest):

  @classmethod
  def setUpClass(cls):
    super(CronCheckTests, cls).setUpClass()

    cls.LoadCheck("cron.yaml")

  def _CheckMultipleSymPerCheck(self, check_id, results, sym_list, found_list):
    """Ensure results for a check containing multiple symptoms match."""
    anom = []
    for sym, found in zip(sym_list, found_list):
      anom.append(
          rdf_anomaly.Anomaly(
              symptom=sym, finding=found, type="ANALYSIS_ANOMALY"))
    expected = checks.CheckResult(check_id=check_id, anomaly=anom)
    self.assertResultEqual(expected, results[check_id])

  def testCronPermisionsCheck(self):
    """Ensure cron permissions check detects files modifiable by non-root."""
    check_id = "CIS-CRON-PERMISSIONS"

    artifact_crontab = "AllLinuxScheduleFiles"
    data_crontab = [
        self.CreateStat("/etc/cron.d", 0, 0, 0o0040640),
        self.CreateStat("/etc/cron.daily/test1", 0, 60, 0o0100660),
        self.CreateStat("/etc/cron.daily/test2", 50, 0, 0o0100444),
        self.CreateStat("/var/spool/cron/cronfile", 0, 0, 0o0100640),
        self.CreateStat("/etc/cron.d/cronfile2", 0, 0, 0o0100664)
    ]

    sym_crontab = ("Found: System crontabs can be modified by non-privileged "
                   "users.")
    found_crontab = [("/etc/cron.daily/test1 user: 0, group: 60, "
                      "mode: -rw-rw----"),
                     ("/etc/cron.daily/test2 user: 50, group: 0, "
                      "mode: -r--r--r--")]

    artifact_allow_deny = "CronAtAllowDenyFiles"
    data_allow_deny = [
        self.CreateStat("/etc/cron.allow", 5, 0, 0o0100640),
        self.CreateStat("/etc/cron.deny", 0, 60, 0o0100640),
        self.CreateStat("/etc/at.allow", 0, 0, 0o0100440),
        self.CreateStat("/etc/at.deny", 0, 0, 0o0100666)
    ]

    sym_allow_deny = ("Found: System cron or at allow/deny files can be "
                      "modified by non-privileged users.")
    found_allow_deny = [
        "/etc/cron.allow user: 5, group: 0, mode: -rw-r-----",
        "/etc/at.deny user: 0, group: 0, mode: -rw-rw-rw-"
    ]

    # Run checks only with results from only one artifact each
    results = self.GenResults([artifact_crontab], [data_crontab])
    self.assertCheckDetectedAnom(check_id, results, sym_crontab, found_crontab)

    results = self.GenResults([artifact_allow_deny], [data_allow_deny])
    self.assertCheckDetectedAnom(check_id, results, sym_allow_deny,
                                 found_allow_deny)

    # Run checks with results from both artifacts
    results = self.GenResults([artifact_crontab, artifact_allow_deny],
                              [data_crontab, data_allow_deny])
    self._CheckMultipleSymPerCheck(check_id, results,
                                   [sym_crontab, sym_allow_deny],
                                   [found_crontab, found_allow_deny])

  def testCronAllowDoesNotExistCheck(self):
    """Ensure check detects if /etc/(at|cron).allow doesn't exist."""
    check_id = "CIS-AT-CRON-ALLOW-DOES-NOT-EXIST"

    artifact = "CronAtAllowDenyFiles"
    # both files exist in this data
    data1 = [
        self.CreateStat("/etc/cron.allow", 0, 0, 0o0100640),
        self.CreateStat("/etc/crondallow", 200, 60, 0o0100640),
        self.CreateStat("/etc/at.allow", 0, 0, 0o0100640),
        self.CreateStat("/etc/mo/cron.allow", 300, 70, 0o0100640),
        self.CreateStat("/root/at.allow", 400, 70, 0o0100640)
    ]

    # only one file exists in this data
    data2 = [
        self.CreateStat("/etc/at.allow", 0, 0, 0o0100640),
        self.CreateStat("/etc/cronMallow", 200, 60, 0o0100640),
        self.CreateStat("/etc/cron/cron.allow", 300, 70, 0o0100640),
        self.CreateStat("/home/user1/at.allow", 400, 70, 0o0100640)
    ]

    # neither file exists in this data
    data3 = [
        self.CreateStat("/etc/random/at.allow", 0, 0, 0o0100640),
        self.CreateStat("/etc/cronZallow", 200, 60, 0o0100640),
        self.CreateStat("/etc/cron/cron.allow", 300, 70, 0o0100640),
        self.CreateStat("/home/user1/at.allow", 400, 70, 0o0100640)
    ]

    sym_cron_allow = ("Missing attribute: /etc/cron.allow does not exist "
                      "on the system.")
    sym_at_allow = ("Missing attribute: /etc/at.allow does not exist "
                    "on the system.")

    found = ["Expected state was not found"]

    # check with both files existing - no hits
    results = self.GenResults([artifact], [data1])
    self.assertCheckUndetected(check_id, results)

    # check with only one file existing - one hit
    results = self.GenResults([artifact], [data2])
    self.assertCheckDetectedAnom(check_id, results, sym_cron_allow, found)

    # check when both files don't exist - two hits
    results = self.GenResults([artifact], [data3])
    self._CheckMultipleSymPerCheck(
        check_id, results, [sym_cron_allow, sym_at_allow], [found, found])

    # Provide empty host data - check both files don't exist - two hits
    results = self.GenResults([artifact], [None])
    self._CheckMultipleSymPerCheck(
        check_id, results, [sym_cron_allow, sym_at_allow], [found, found])

  def testCronDenyExistCheck(self):
    """Ensure cron/at deny check detects if /etc/(at|cron).deny exists."""
    check_id = "CIS-AT-CRON-DENY-EXISTS"

    artifact = "CronAtAllowDenyFiles"
    # both files exist in this data
    data1 = [
        self.CreateStat("/etc/cron.deny", 0, 0, 0o0100640),
        self.CreateStat("/etc/cronTdeny", 200, 60, 0o0100640),
        self.CreateStat("/etc/at.deny", 0, 0, 0o0100640),
        self.CreateStat("/etc/hi/cron.deny", 300, 70, 0o0100640),
        self.CreateStat("/root/at.deny", 400, 70, 0o0100640)
    ]

    # only one file exists in this data
    data2 = [
        self.CreateStat("/etc/at.deny", 0, 0, 0o0100640),
        self.CreateStat("/etc/cronDdeny", 200, 60, 0o0100640),
        self.CreateStat("/etc/cron/cron.deny", 300, 70, 0o0100640),
        self.CreateStat("/home/user1/at.deny", 400, 70, 0o0100640)
    ]

    # neither file exists in this data
    data3 = [
        self.CreateStat("/etc/random/at.deny", 0, 0, 0o0100640),
        self.CreateStat("/etc/cronDdeny", 200, 60, 0o0100640),
        self.CreateStat("/etc/cron/cron.deny", 300, 70, 0o0100640),
        self.CreateStat("/home/user1/at.deny", 400, 70, 0o0100640)
    ]

    sym_cron_deny = "Found: /etc/cron.deny exists on the system."
    sym_at_deny = "Found: /etc/at.deny exists on the system."

    found_cron_deny = ["/etc/cron.deny user: 0, group: 0, mode: -rw-r-----"]
    found_at_deny = ["/etc/at.deny user: 0, group: 0, mode: -rw-r-----"]

    # check when both files exists
    results = self.GenResults([artifact], [data1])
    self._CheckMultipleSymPerCheck(check_id, results,
                                   [sym_cron_deny, sym_at_deny],
                                   [found_cron_deny, found_at_deny])

    # check with only one file existing - one hit
    results = self.GenResults([artifact], [data2])
    self.assertCheckDetectedAnom(check_id, results, sym_at_deny, found_at_deny)

    # check with both file not existing - no hits
    results = self.GenResults([artifact], [data3])
    self.assertCheckUndetected(check_id, results)

  def testCronAllowOnlyContainsRoot(self):
    """Ensure cron/at allow only contains "root"."""
    check_id = "CIS-CRON-AT-ALLOW-ONLY-CONTAINS-ROOT"
    artifact = "CronAtAllowDenyFiles"
    sym = ("Found: at.allow or cron.allow contains non-root users or does "
           "not contain root.")
    parser = config_file.CronAtAllowDenyParser()

    data = {
        "/etc/at.allow": u"root",
        "/etc/cron.allow": u"user1",
        "/etc/at.deny": u"blah\nblah blah"
    }
    found = ["/etc/cron.allow: user1"]

    results = self.GenResults([artifact], [data], [parser])
    self.assertCheckDetectedAnom(check_id, results, sym, found)

    data = {"/etc/at.allow": u"", "/etc/cron.allow": u"root"}
    found = ["/etc/at.allow:"]

    results = self.GenResults([artifact], [data], [parser])
    self.assertCheckDetectedAnom(check_id, results, sym, found)

    data = {"/etc/at.allow": u"", "/etc/cron.allow": u""}
    found = ["/etc/at.allow:", "/etc/cron.allow:"]

    results = self.GenResults([artifact], [data], [parser])
    self.assertCheckDetectedAnom(check_id, results, sym, found)

    data = {"/etc/at.allow": u"root", "/etc/cron.allow": u"root"}

    results = self.GenResults([artifact], [data], [parser])
    self.assertCheckUndetected(check_id, results)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
