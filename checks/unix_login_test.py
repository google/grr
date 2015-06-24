#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for service state checks."""
import StringIO


from grr.lib import flags
from grr.lib import test_lib
from grr.lib.checks import checks_test_lib
from grr.lib.rdfvalues import anomaly as rdf_anomaly
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.parsers import linux_file_parser


class LoginPolicyConfigurationTests(checks_test_lib.HostCheckTest):

  results = None

  @classmethod
  def setUpClass(cls):
    cls.LoadCheck("unix_login.yaml")

  def setUp(self, *args, **kwargs):
    super(LoginPolicyConfigurationTests, self).setUp(*args, **kwargs)
    if not LoginPolicyConfigurationTests.results:
      LoginPolicyConfigurationTests.results = self._GenResults()

  def _GenResults(self):
    host_data = self.SetKnowledgeBase()
    login = {
        "/etc/passwd": """
            nopasswd:x:1000:1000::/home/nopasswd:/bin/bash
            md5:x:1001:1001::/home/md5:/bin/bash
            undying:x:1002:1002::/home/undying:/bin/bash
            disabled:x:1003:1003::/home/disabled:/bin/bash
            +nisuser:acr.7pt3dpA5s::::::/bin/zsh""",
        "/etc/shadow": """
            nopasswd::16000:0:365:7:::
            md5:$1$rootrootrootrootrootro:16000::::::
            undying:$6$saltsalt${0}:16000:0:99999:7:::
            disabled:!:16000:0:99999:7:::""".format("r" * 86),
        "/etc/group": """
            nopasswd:x:1000:nopasswd
            +:::
            md5:x:1001:md5
            undying:x:1002:undying
            disabled:x:1003:disabled""",
        "/etc/gshadow": """
            nopasswd:::nopasswd
            md5:::md5
            undying:::undying
            disabled:::disabled"""}
    perms = {"/etc/passwd": (0, 0, 0o100666),   # Anomalous write perm.
             "/etc/group": (1, 0, 0o100644),    # Anomalous owner.
             "/etc/shadow": (0, 0, 0o100444),   # Anomalous read perm.
             "/etc/gshadow": (0, 1, 0o100400)}  # Anomalous group.
    stats = []
    files = []
    for path, lines in login.items():
      p = rdf_paths.PathSpec(path=path, pathtype="OS")
      st_uid, st_gid, st_mode = perms.get(path)
      stats.append(rdf_client.StatEntry(
          pathspec=p, st_uid=st_uid, st_gid=st_gid, st_mode=st_mode))
      files.append(StringIO.StringIO(lines))
    parser = linux_file_parser.LinuxSystemPasswdParser()
    rdfs = list(parser.ParseMultiple(stats, files, None))
    host_data["LoginPolicyConfiguration"] = self.SetArtifactData(
        anomaly=[a for a in rdfs if isinstance(a, rdf_anomaly.Anomaly)],
        parsed=[r for r in rdfs if not isinstance(r, rdf_anomaly.Anomaly)],
        raw=stats)
    return self.RunChecks(host_data)

  def testPasswdHash(self):
    chk_id = "CIS-LOGIN-UNIX-HASH"
    exp = "Found: Insecure password hash method."
    found = ["password for +nisuser uses DES",
             "password for md5 uses MD5"]
    self.assertCheckDetectedAnom(chk_id, self.results, exp, found)

  def testEmptyPasswordCheck(self):
    chk_id = "CIS-LOGIN-UNIX-EMPTY"
    exp = "Found: Empty password string."
    found = ["password for nopasswd in SHADOW is empty."]
    self.assertCheckDetectedAnom(chk_id, self.results, exp, found)

  def testPasswdMaxageCheck(self):
    chk_id = "CIS-LOGIN-UNIX-SHADOW-MAXAGE"
    exp = "Found: Weak password aging settings in /etc/shadow."
    found = ["Weak password aging for undying in SHADOW."]
    self.assertCheckDetectedAnom(chk_id, self.results, exp, found)

  def testNisPasswordCheck(self):
    chk_id = "CIS-LOGIN-UNIX-NIS-MARKER"
    exp = "Found: NIS entries present."
    found = ["Group entry + is a NIS account marker.",
             "User account +nisuser is a NIS account marker."]
    self.assertCheckDetectedAnom(chk_id, self.results, exp, found)

  def testDetectWeakPermissions(self):
    chk_id = "CIS-LOGIN-UNIX-WRITABLE"
    exp = "Found: System account files can be modified by non-privileged users."
    found = ["/etc/group: user: 1, group: 0, mode: -rw-r--r--",
             "/etc/passwd: user: 0, group: 0, mode: -rw-rw-rw-"]
    self.assertCheckDetectedAnom(chk_id, self.results, exp, found)

  def testDetectShadowReadable(self):
    chk_id = "CIS-LOGIN-UNIX-SHADOW-PERMS"
    exp = "Found: Incorrect shadow file permissions."
    found = ["/etc/gshadow: user: 0, group: 1, mode: -r--------",
             "/etc/shadow: user: 0, group: 0, mode: -r--r--r--"]
    self.assertCheckDetectedAnom(chk_id, self.results, exp, found)

  def testReportDetectedAnomalies(self):
    chk_id = "CIS-LOGIN-UNIX-INCONSISTENCIES"
    exp = "Found: System account entries are anomalous."
    found = ["Mismatched group and gshadow files.",
             "Mismatched passwd and shadow files."]
    self.assertCheckDetectedAnom(chk_id, self.results, exp, found)


def main(argv):
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
