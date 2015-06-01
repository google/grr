#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for service state checks."""
import StringIO


from grr.lib import flags
from grr.lib import test_lib
from grr.lib.checks import checks_test_lib
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.parsers import linux_file_parser


class LoginPolicyConfigurationTests(checks_test_lib.HostCheckTest):

  check_loaded = False
  results = None

  def setUp(self, *args, **kwargs):
    super(LoginPolicyConfigurationTests, self).setUp(*args, **kwargs)
    if not self.check_loaded:
      self.check_loaded = self.LoadCheck("unix_login.yaml")
    # Create some host_data..
    if not self.results:
      self.results = self._GenResults()

  def _GenResults(self):
    if self.results is None:
      host_data = self.SetKnowledgeBase()
      login = {
          "/etc/passwd": """
              nopasswd:x:1000:1000::/home/nopasswd:/bin/bash
              md5:x:1001:1001::/home/md5:/bin/bash
              undying:x:1002:1002::/home/undying:/bin/bash
              +nisuser:acr.7pt3dpA5s::::::/bin/zsh""",
          "/etc/shadow": """
              nopasswd::16000:0:365:7:::
              md5:$1$rootrootrootrootrootro:16000:0:365:7:::
              undying:$6$saltsalt${0}:16000:0:99999:7:::""".format("r" * 86),
          "/etc/group": """
              nopasswd:x:1000:nopasswd
              +:::
              md5:x:1001:md5
              undying:x:1002:undying""",
          "/etc/gshadow": """
              nopasswd:::nopasswd
              md5:::md5
              undying:::undying"""}
      stats = []
      files = []
      for path, lines in login.items():
        p = rdf_paths.PathSpec(path=path)
        stats.append(rdf_client.StatEntry(pathspec=p))
        files.append(StringIO.StringIO(lines))
      parser = linux_file_parser.LinuxSystemPasswdParser()
      rdfs = list(parser.ParseMultiple(stats, files, None))
      host_data["LoginPolicyConfiguration"] = rdfs
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
    found = ["Group entry + is a NIS account marker."]
    self.assertCheckDetectedAnom(chk_id, self.results, exp, found)
    exp = "Found: NIS entries present."
    found = ["User account +nisuser is a NIS account marker."]
    self.assertCheckDetectedAnom(chk_id, self.results, exp, found)


def main(argv):
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
