#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the PAM config checks."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags
from grr_response_core.lib.parsers import linux_pam_parser
from grr_response_server.check_lib import checks_test_lib
from grr.test_lib import test_lib


class PamConfigTests(checks_test_lib.HostCheckTest):

  @classmethod
  def setUpClass(cls):
    super(PamConfigTests, cls).setUpClass()

    cls.LoadCheck("pam.yaml")
    cls.parser = linux_pam_parser.PAMParser()

  def testPamSshAccess(self):
    """Test we handle when PAM ssh service doesn't require an account."""

    good1_contents = "account required pam_access.so\n"
    good2_contents = "account required /lib/security/pam_access.so foo\n"
    good3_contents = "account required /lib64/security/pam_access.so f b\n"
    bad_contents = "account required test.so\n"
    pam_good1 = {"/etc/pam.d/ssh": good1_contents}
    pam_good2 = {"/etc/pam.d/ssh": good2_contents}
    pam_good3 = {"/etc/pam.d/ssh": good3_contents}
    pam_bad = {"/etc/pam.d/ssh": bad_contents}
    sym = "Missing attribute: PAM ssh service must require an account."
    found = ["Expected state was not found"]
    results = self.RunChecks(
        self.GenFileData("PamConfig", pam_bad, parser=self.parser))
    self.assertCheckDetectedAnom("PAM-SSH-PAMACCESS", results, sym, found)
    # Now the successful cases.
    results = self.RunChecks(
        self.GenFileData("PamConfig", pam_good1, parser=self.parser))
    self.assertCheckUndetected("PAM-SSH-PAMACCESS", results)
    results = self.RunChecks(
        self.GenFileData("PamConfig", pam_good2, parser=self.parser))
    self.assertCheckUndetected("PAM-SSH-PAMACCESS", results)
    results = self.RunChecks(
        self.GenFileData("PamConfig", pam_good3, parser=self.parser))
    self.assertCheckUndetected("PAM-SSH-PAMACCESS", results)

  def testPamSshUnconditionalPermit(self):
    """Test we find when PAM ssh service allows an unconditional auth permit."""
    good_contents = "auth done pam_deny.so\n"
    bad_contents = "auth done pam_permit.so\n"
    pam_good = {"/etc/pam.d/ssh": good_contents}
    pam_bad = {"/etc/pam.d/ssh": bad_contents}
    # Check the detection case.
    sym = "Found: PAM ssh service has unconditional authentication."
    found = ["In service 'ssh': auth done pam_permit.so"]
    results = self.RunChecks(
        self.GenFileData("PamConfig", pam_bad, parser=self.parser))
    self.assertCheckDetectedAnom("PAM-SSH-UNCONDITIONAL-PERMIT", results, sym,
                                 found)
    # Now the pass case.
    results = self.RunChecks(
        self.GenFileData("PamConfig", pam_good, parser=self.parser))
    self.assertCheckUndetected("PAM-SSH-UNCONDITIONAL-PERMIT", results)

  def testPamSshDefaultDeniesAuth(self):
    """Test we detect when PAM ssh service doesn't deny auth by default."""
    good1_contents = "auth required pam_deny.so\n"
    good2_contents = ("auth [success=ok new_authtok_reqd=ok default=die] "
                      "pam_unix.so try_first_pass\n")
    bad_contents = "auth required pam_foobar.so\n"
    pam_good1 = {"/etc/pam.d/ssh": good1_contents}
    pam_good2 = {"/etc/pam.d/ssh": good2_contents}
    pam_bad = {"/etc/pam.d/ssh": bad_contents}
    # Check the detection case.
    sym = "Missing attribute: PAM ssh service must default to denying auth."
    found = ["Expected state was not found"]
    results = self.RunChecks(
        self.GenFileData("PamConfig", pam_bad, parser=self.parser))
    self.assertCheckDetectedAnom("PAM-SSH-DEFAULT-DENIES-AUTH", results, sym,
                                 found)
    # Now the pass cases.
    results = self.RunChecks(
        self.GenFileData("PamConfig", pam_good1, parser=self.parser))
    self.assertCheckUndetected("PAM-SSH-DEFAULT-DENIES-AUTH", results)
    results = self.RunChecks(
        self.GenFileData("PamConfig", pam_good2, parser=self.parser))
    self.assertCheckUndetected("PAM-SSH-DEFAULT-DENIES-AUTH", results)

  def testPamSshNoNullPasswords(self):
    """Test we find when PAM ssh service allows an unconditional auth permit."""
    good_contents = "password sufficient pam_unix.so\n"
    bad_contents = "password requisite /lib/security/pam_unix.so nullok\n"
    pam_good = {"/etc/pam.d/ssh": good_contents}
    pam_bad = {"/etc/pam.d/ssh": bad_contents}
    # Check the detection case.
    sym = "Found: PAM ssh service allows unix null password accounts to login."
    found = [
        "In service 'ssh': password requisite /lib/security/pam_unix.so "
        "nullok"
    ]
    results = self.RunChecks(
        self.GenFileData("PamConfig", pam_bad, parser=self.parser))
    self.assertCheckDetectedAnom("PAM-SSH-NO-NULL-PASSWORDS", results, sym,
                                 found)
    # Now the pass case.
    results = self.RunChecks(
        self.GenFileData("PamConfig", pam_good, parser=self.parser))
    self.assertCheckUndetected("PAM-SSH-NO-NULL-PASSWORDS", results)

  def testPamSecureDefaults(self):
    """Test we detect when PAM ssh service doesn't deny auth by default."""
    good_contents = """
        auth required pam_deny.so foobar
        password sufficient /lib64/security/pam_warn.so
        session requisite /lib/security/pam_deny.so
        """
    bad_contents = good_contents + """
        auth required pam_permit.so
        password done pam_foobar.so test args
        """
    pam_good = {"/etc/pam.d/other": good_contents}
    pam_bad = {"/etc/pam.d/other": bad_contents}
    # Check the detection case.
    sym = ("Found: PAM 'other'(the default) config should only be "
           "used for denying/logging access.")
    found = [
        "In service 'other': auth required pam_permit.so",
        "In service 'other': password done pam_foobar.so test args"
    ]
    results = self.RunChecks(
        self.GenFileData("PamConfig", pam_bad, parser=self.parser))
    self.assertCheckDetectedAnom("PAM-SECURE-DEFAULTS", results, sym, found)
    # Now the pass cases.
    results = self.RunChecks(
        self.GenFileData("PamConfig", pam_good, parser=self.parser))
    self.assertCheckUndetected("PAM-SECURE-DEFAULTS", results)

  def testPamExternalConfigs(self):
    """Test we detect when PAM ssh service doesn't deny auth by default."""
    pam_good = {"/etc/pam.d/ssh": "auth include other", "/etc/pam.d/other": ""}
    pam_bad = {
        "/etc/pam.d/ssh": "auth include non-existant",
        "/etc/pam.d/other": "password include /tmp/non-existant"
    }
    # Check the detection case.
    sym = "Found: PAM configuration refers to files outside of /etc/pam.d."
    found = [
        "/etc/pam.d/ssh -> /etc/pam.d/non-existant",
        "/etc/pam.d/other -> /tmp/non-existant"
    ]
    results = self.RunChecks(
        self.GenFileData("PamConfig", pam_bad, parser=self.parser))
    self.assertCheckDetectedAnom("PAM-EXTERNAL-CONFIG", results, sym, found)
    # Now the pass cases.
    results = self.RunChecks(
        self.GenFileData("PamConfig", pam_good, parser=self.parser))
    self.assertCheckUndetected("PAM-SECURE-DEFAULTS", results)

  def testPamConfigPermissions(self):
    """Ensure check detects Pam config files that non-root users can edit."""

    data = [
        self.CreateStat("/etc/pam.d/hit-123", 50, 0, 0o0100640),
        self.CreateStat("/etc/pam.d/hit-234", 0, 60, 0o0040777),
        self.CreateStat("/etc/pam.d/no-hit-123", 0, 6000, 0o0100440),
        self.CreateStat("/etc/pam.d/no-hit-234", 0, 0, 0o0100640),
        self.CreateStat("/etc/pam.d/hit-345", 70, 0, 0o0100660)
    ]

    results = self.GenResults(["LinuxPamConfigs"], [data])

    check_id = "PAM-CONFIG-FILES-WRITABLE-BY-NON-ROOT-USER"
    sym = ("Found: Files or folders in Pam configuration can be modified by "
           "non-privileged users.")
    found = [
        "/etc/pam.d/hit-123 user: 50, group: 0, mode: -rw-r-----",
        "/etc/pam.d/hit-234 user: 0, group: 60, mode: drwxrwxrwx",
        "/etc/pam.d/hit-345 user: 70, group: 0, mode: -rw-rw----",
    ]

    self.assertCheckDetectedAnom(check_id, results, sym, found)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
