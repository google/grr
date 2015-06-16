#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for cron checks."""
import itertools
import StringIO


from grr.lib import flags
from grr.lib import test_lib
from grr.lib.checks import checks
from grr.lib.checks import checks_test_lib
from grr.lib.rdfvalues import anomaly as rdf_anomaly
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.parsers import config_file


class CronCheckTests(checks_test_lib.HostCheckTest):

  def _CreateStat(self, path, uid, gid, mode):
    """Given path, uid, gid and file mode, this returns a StatEntry."""
    pathspec = rdf_paths.PathSpec(path=path, pathtype="OS")
    return rdf_client.StatEntry(pathspec=pathspec, st_uid=uid, st_gid=gid,
                                st_mode=mode)

  # TODO(user): remove this function and integrate parser_list = None into
  # GenResults in checks_test_lib.py after cl/95605337 is finalised
  def _GenResults(self, artifact_list, stats_list,
                  parsed_list=None, anomaly_list=None):
    """Runs checks on a list of artifacts, stats, parsed rdfs and anomalies.

    With a sample input where artifact_list = [artifact1, artifact2] and
    stats_list=[[StatEntry1, StatEntry2], [StatEntry3]]. This will first add
    all the artifacts to host_data:
      1) host_data[artifact1] = SetArtifactData(raw=[StatEntry1, StatEntry2])
      1) host_data[artifact2] = SetArtifactData(raw=[StatEntry3])
    Then it will run a check with the loaded checks against host_data and
    return the results.

    Args:
      artifact_list: a list of artifacts to be added to host_data
      stats_list: a list of lists containing StatEntry of files
      parsed_list: a list of lists containing parsed results of the respective
                   files located in stats_list
      anomaly_list: a list of lists containing anomalous results found in files
                    while parsing for parsed_list

    Returns:
      CheckResult containing findings from loaded check against host_data
    """
    if parsed_list is None:
      parsed_list = []
    if anomaly_list is None:
      anomaly_list = []

    self.LoadCheck("cron.yaml")
    host_data = self.SetKnowledgeBase()
    for artifact, stats, parsed, anomaly in itertools.izip_longest(
        artifact_list, stats_list, parsed_list, anomaly_list, fillvalue=[]):

      host_data[artifact] = self.SetArtifactData(parsed=parsed, raw=stats,
                                                 anomaly=anomaly)
    return self.RunChecks(host_data)

  def _CheckResult(self, check_id, results, exp_list, found_list):
    """Ensure results for a check match list of explanations & findings."""
    anom = []
    for exp, found in zip(exp_list, found_list):
      anom.append(rdf_anomaly.Anomaly(explanation=exp, finding=found,
                                      type="ANALYSIS_ANOMALY"))
    expected = checks.CheckResult(check_id=check_id, anomaly=anom)
    self.assertResultEqual(expected, results[check_id])

  def testCronPermisionsCheck(self):
    """Ensure cron permissions check detects files modifiable by non-root."""
    check_id = "CIS-CRON-PERMISSIONS"

    artifact_crontab = "AllLinuxScheduleFiles"
    data_crontab = [self._CreateStat("/etc/cron.d", 0, 0, 0o0040640),
                    self._CreateStat("/etc/cron.daily/test1", 0, 60, 0o0100660),
                    self._CreateStat("/etc/cron.daily/test2", 50, 0, 0o0100444),
                    self._CreateStat("/var/spool/cron/cronfile", 0, 0,
                                     0o0100640),
                    self._CreateStat("/etc/cron.d/cronfile2", 0, 0, 0o0100664)]

    exp_crontab = ("Found: System crontabs can be modified by non-privileged "
                   "users.")
    found_crontab = [("/etc/cron.daily/test1 user: 0, group: 60, "
                      "mode: -rw-rw----\n"),
                     ("/etc/cron.daily/test2 user: 50, group: 0, "
                      "mode: -r--r--r--\n")]

    artifact_allow_deny = "CronAtAllowDenyFiles"
    data_allow_deny = [self._CreateStat("/etc/cron.allow", 5, 0, 0o0100640),
                       self._CreateStat("/etc/cron.deny", 0, 60, 0o0100640),
                       self._CreateStat("/etc/at.allow", 0, 0, 0o0100440),
                       self._CreateStat("/etc/at.deny", 0, 0, 0o0100666)]

    exp_allow_deny = ("Found: System cron or at allow/deny files can be "
                      "modified by non-privileged users.\n")
    found_allow_deny = ["/etc/cron.allow user: 5, group: 0, mode: -rw-r-----\n",
                        "/etc/at.deny user: 0, group: 0, mode: -rw-rw-rw-\n"]

    # Run checks only with results from only one artifact each
    results = self._GenResults([artifact_crontab], [data_crontab])
    self._CheckResult(check_id, results, [exp_crontab], [found_crontab])

    results = self._GenResults([artifact_allow_deny], [data_allow_deny])
    self._CheckResult(check_id, results, [exp_allow_deny], [found_allow_deny])

    # Run checks with results from both artifacts
    results = self._GenResults([artifact_crontab, artifact_allow_deny],
                               [data_crontab, data_allow_deny])
    self._CheckResult(check_id, results, [exp_crontab, exp_allow_deny],
                      [found_crontab, found_allow_deny])

  def testCronAllowDoesNotExistCheck(self):
    """Ensure check detects if /etc/(at|cron).allow doesn't exist."""
    check_id = "CIS-AT-CRON-ALLOW-DOES-NOT-EXIST"

    artifact = "CronAtAllowDenyFiles"
    # both files exist in this data
    data1 = [self._CreateStat("/etc/cron.allow", 0, 0, 0o0100640),
             self._CreateStat("/etc/crondallow", 200, 60, 0o0100640),
             self._CreateStat("/etc/at.allow", 0, 0, 0o0100640),
             self._CreateStat("/etc/mo/cron.allow", 300, 70, 0o0100640),
             self._CreateStat("/root/at.allow", 400, 70, 0o0100640)]

    # only one file exists in this data
    data2 = [self._CreateStat("/etc/at.allow", 0, 0, 0o0100640),
             self._CreateStat("/etc/cronMallow", 200, 60, 0o0100640),
             self._CreateStat("/etc/cron/cron.allow", 300, 70, 0o0100640),
             self._CreateStat("/home/user1/at.allow", 400, 70, 0o0100640)]

    # neither file exists in this data
    data3 = [self._CreateStat("/etc/random/at.allow", 0, 0, 0o0100640),
             self._CreateStat("/etc/cronZallow", 200, 60, 0o0100640),
             self._CreateStat("/etc/cron/cron.allow", 300, 70, 0o0100640),
             self._CreateStat("/home/user1/at.allow", 400, 70, 0o0100640)]

    exp_cron_allow = ("Missing attribute: /etc/cron.allow does not exist "
                      "on the system.")
    exp_at_allow = ("Missing attribute: /etc/at.allow does not exist "
                    "on the system.")

    found = ["Expected state was not found"]

    # check with both files existing - no hits
    results = self._GenResults([artifact], [data1])
    self.assertCheckUndetected(check_id, results)

    # check with only one file existing - one hit
    results = self._GenResults([artifact], [data2])
    self._CheckResult(check_id, results, [exp_cron_allow], [found])

    # check when both files don't exist - two hits
    results = self._GenResults([artifact], [data3])
    self._CheckResult(check_id, results, [exp_cron_allow, exp_at_allow],
                      [found, found])

    # Provide empty host data - check both files don't exist - two hits
    results = self._GenResults([artifact], [])
    self._CheckResult(check_id, results, [exp_cron_allow, exp_at_allow],
                      [found, found])

  def testCronDenyExistCheck(self):
    """Ensure cron/at deny check detects if /etc/(at|cron).deny exists."""
    check_id = "CIS-AT-CRON-DENY-EXISTS"

    artifact = "CronAtAllowDenyFiles"
    # both files exist in this data
    data1 = [self._CreateStat("/etc/cron.deny", 0, 0, 0o0100640),
             self._CreateStat("/etc/cronTdeny", 200, 60, 0o0100640),
             self._CreateStat("/etc/at.deny", 0, 0, 0o0100640),
             self._CreateStat("/etc/hi/cron.deny", 300, 70, 0o0100640),
             self._CreateStat("/root/at.deny", 400, 70, 0o0100640)]

    # only one file exists in this data
    data2 = [self._CreateStat("/etc/at.deny", 0, 0, 0o0100640),
             self._CreateStat("/etc/cronDdeny", 200, 60, 0o0100640),
             self._CreateStat("/etc/cron/cron.deny", 300, 70, 0o0100640),
             self._CreateStat("/home/user1/at.deny", 400, 70, 0o0100640)]

    # neither file exists in this data
    data3 = [self._CreateStat("/etc/random/at.deny", 0, 0, 0o0100640),
             self._CreateStat("/etc/cronDdeny", 200, 60, 0o0100640),
             self._CreateStat("/etc/cron/cron.deny", 300, 70, 0o0100640),
             self._CreateStat("/home/user1/at.deny", 400, 70, 0o0100640)]

    exp_cron_deny = "Found: /etc/cron.deny exists on the system."
    exp_at_deny = "Found: /etc/at.deny exists on the system."

    found_cron_deny = ["/etc/cron.deny user: 0, group: 0, mode: -rw-r-----\n"]
    found_at_deny = ["/etc/at.deny user: 0, group: 0, mode: -rw-r-----\n"]

    # check when both files exists
    results = self._GenResults([artifact], [data1])
    self._CheckResult(check_id, results, [exp_cron_deny, exp_at_deny],
                      [found_cron_deny, found_at_deny])

    # check with only one file existing - one hit
    results = self._GenResults([artifact], [data2])
    self._CheckResult(check_id, results, [exp_at_deny], [found_at_deny])

    # check with both file not existing - no hits
    results = self._GenResults([artifact], [data3])
    self.assertCheckUndetected(check_id, results)

  def _GenResultsForCronAtAllowParser(self, artifact, data):
    """Run CronAtAllowDenyParser on data, then _GenResults on that."""
    stats = []
    rdfs = []
    parser = config_file.CronAtAllowDenyParser()
    for path, lines in data.items():
      stat = self._CreateStat(path, 0, 0, 0o0100640)
      stats.append(stat)
      file_obj = StringIO.StringIO(lines)
      rdfs.extend(list(parser.Parse(stat, file_obj, None)))
    anomaly = [a for a in rdfs if isinstance(a, rdf_anomaly.Anomaly)]
    parsed = [a for a in rdfs if not isinstance(a, rdf_anomaly.Anomaly)]
    return self._GenResults([artifact], [stats], [parsed], [anomaly])

  def testCronAllowOnlyContainsRoot(self):
    """Ensure cron/at allow only contains "root"."""
    check_id = "CIS-CRON-AT-ALLOW-ONLY-CONTAINS-ROOT"
    artifact = "CronAtAllowDenyFiles"
    exp = ("Found: at.allow or cron.allow contains non-root users or does "
           "not contain root.\n")

    data = {"/etc/at.allow": "root",
            "/etc/cron.allow": "user1",
            "/etc/at.deny": "blah\nblah blah"}
    found = ["/etc/cron.allow: user1"]

    results = self._GenResultsForCronAtAllowParser(artifact, data)
    self._CheckResult(check_id, results, [exp], [found])

    data = {"/etc/at.allow": "",
            "/etc/cron.allow": "root"}
    found = ["/etc/at.allow: "]

    results = self._GenResultsForCronAtAllowParser(artifact, data)
    self._CheckResult(check_id, results, [exp], [found])

    data = {"/etc/at.allow": "",
            "/etc/cron.allow": ""}
    found = ["/etc/at.allow: ",
             "/etc/cron.allow: "]

    results = self._GenResultsForCronAtAllowParser(artifact, data)
    self._CheckResult(check_id, results, [exp], [found])

    data = {"/etc/at.allow": "root",
            "/etc/cron.allow": "root"}

    results = self._GenResultsForCronAtAllowParser(artifact, data)
    self.assertCheckUndetected(check_id, results)


def main(argv):
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)

