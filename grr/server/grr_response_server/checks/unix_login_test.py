#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for service state checks."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags
from grr_response_core.lib.parsers import linux_file_parser
from grr_response_server.check_lib import checks_test_lib
from grr.test_lib import test_lib


class LoginPolicyConfigurationTests(checks_test_lib.HostCheckTest):

  results = None

  @classmethod
  def setUpClass(cls):
    super(LoginPolicyConfigurationTests, cls).setUpClass()

    cls.LoadCheck("unix_login.yaml")

  def setUp(self, *args, **kwargs):
    super(LoginPolicyConfigurationTests, self).setUp(*args, **kwargs)
    if not LoginPolicyConfigurationTests.results:
      LoginPolicyConfigurationTests.results = self._GenResults()

  def _GenResults(self):
    parser = linux_file_parser.LinuxSystemPasswdParser()
    if self.results is None:
      host_data = self.SetKnowledgeBase()
      login = {
          "/etc/passwd":
              """
              nopasswd:x:1000:1000::/home/nopasswd:/bin/bash
              md5:x:1001:1001::/home/md5:/bin/bash
              undying:x:1002:1002::/home/undying:/bin/bash
              disabled:x:1003:1003::/home/disabled:/bin/bash
              +nisuser:acr.7pt3dpA5s::::::/bin/zsh""",
          "/etc/shadow":
              """
              nopasswd::16000:0:365:7:::
              md5:$1$rootrootrootrootrootro:16000:0:365:7:::
              undying:$6$saltsalt${0}:16000:0:99999:7:::
              disabled:!:16000:0:99999:7:::""".format("r" * 86),
          "/etc/group":
              """
              nopasswd:x:1000:nopasswd
              +:::
              md5:x:1001:md5
              undying:x:1002:undying
              disabled:x:1003:disabled""",
          "/etc/gshadow":
              """
              nopasswd:::nopasswd
              md5:::md5
              undying:::undying
              disabled:::disabled"""
      }
      modes = {
          "/etc/passwd": {
              "st_mode": 0o100666
          },  # Bad write perm.
          "/etc/group": {
              "st_uid": 1
          },  # Bad owner.
          "/etc/shadow": {
              "st_mode": 0o100444
          },  # Bad read perm.
          "/etc/gshadow": {
              "st_gid": 1,
              "st_mode": 0o100400
          }
      }  # Bad group.
      host_data = self.GenFileData("LoginPolicyConfiguration", login, parser,
                                   modes)
      return self.RunChecks(host_data)

  def testPasswdHash(self):
    chk_id = "CIS-LOGIN-UNIX-HASH"
    sym = "Found: Insecure password hash method."
    found = ["password for +nisuser uses DES", "password for md5 uses MD5"]
    self.assertCheckDetectedAnom(chk_id, self.results, sym, found)

  def testEmptyPasswordCheck(self):
    chk_id = "CIS-LOGIN-UNIX-EMPTY"
    sym = "Found: Empty password string."
    found = ["password for nopasswd in SHADOW is empty."]
    self.assertCheckDetectedAnom(chk_id, self.results, sym, found)

  def testPasswdMaxageCheck(self):
    chk_id = "CIS-LOGIN-UNIX-SHADOW-MAXAGE"
    sym = "Found: Weak password aging settings in /etc/shadow."
    found = ["Weak password aging for undying in SHADOW."]
    self.assertCheckDetectedAnom(chk_id, self.results, sym, found)

  def testNisPasswordCheck(self):
    chk_id = "CIS-LOGIN-UNIX-NIS-MARKER"
    sym = "Found: NIS entries present."
    found = [
        "Group entry + is a NIS account marker.",
        "User account +nisuser is a NIS account marker."
    ]
    self.assertCheckDetectedAnom(chk_id, self.results, sym, found)

  def testDetectWeakPermissions(self):
    chk_id = "CIS-LOGIN-UNIX-WRITABLE"
    sym = "Found: System account files can be modified by non-privileged users."
    found = [
        "/etc/group: user: 1, group: 0, mode: -rw-r--r--",
        "/etc/passwd: user: 0, group: 0, mode: -rw-rw-rw-"
    ]
    self.assertCheckDetectedAnom(chk_id, self.results, sym, found)

  def testDetectShadowReadable(self):
    chk_id = "CIS-LOGIN-UNIX-SHADOW-PERMS"
    sym = "Found: Incorrect shadow file permissions."
    found = [
        "/etc/gshadow: user: 0, group: 1, mode: -r--------",
        "/etc/shadow: user: 0, group: 0, mode: -r--r--r--"
    ]
    self.assertCheckDetectedAnom(chk_id, self.results, sym, found)

  def testReportDetectedAnomalies(self):
    chk_id = "CIS-LOGIN-UNIX-INCONSISTENCIES"
    sym = "Found: System account entries are anomalous."
    found = [
        "Mismatched group and gshadow files.",
        "Mismatched passwd and shadow files."
    ]
    self.assertCheckDetectedAnom(chk_id, self.results, sym, found)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
