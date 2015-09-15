#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for SSHd state checks."""


from grr.lib import flags
from grr.lib import test_lib
from grr.lib.checks import checks_test_lib
from grr.parsers import config_file


class SshdCheckTests(checks_test_lib.HostCheckTest):
  """Test the sshd checks."""

  @classmethod
  def setUpClass(cls):
    cls.LoadCheck("sshd.yaml")
    cls.parser = config_file.SshdConfigParser()

  def testProtocolFail(self):
    chk_id = "CIS-SSH-PROTOCOL"

    test_data = {"/etc/ssh/sshd_config":
                 "# Comment line\nProtocol 2,1"}
    host_data = self.GenFileData("SshdConfigFile", test_data, self.parser)
    results = self.RunChecks(host_data)
    sym = "Found: Sshd configuration supports protocol 1."
    found = ["Protocol = 2,1"]
    self.assertCheckDetectedAnom(chk_id, results, sym, found)

  def testPermitRootLoginFail(self):
    chk_id = "CIS-SSH-PERMIT-ROOT-LOGIN"

    test_data = {"/etc/ssh/sshd_config":
                 "PermitRootLogin without-password"}
    host_data = self.GenFileData("SshdConfigFile", test_data, self.parser)
    results = self.RunChecks(host_data)
    sym = "Found: Sshd configuration permits direct root login."
    found = ["PermitRootLogin = without-password"]
    self.assertCheckDetectedAnom(chk_id, results, sym, found)

  def testPermitRootLoginSucceed(self):
    chk_id = "CIS-SSH-PERMIT-ROOT-LOGIN"

    test_data = {"/etc/ssh/sshd_config":
                 "PermitRootLogin no"}
    host_data = self.GenFileData("SshdConfigFile", test_data, self.parser)
    results = self.RunChecks(host_data)
    self.assertCheckUndetected(chk_id, results)

  def testPubKeyAllowedSucceed(self):
    chk_id = "SSH-PUB-KEY-AUTHENTICATION"

    # DSAAuthentication is an alias for PubKeyAuthentication.
    # sshd uses the first configuration value, if repeated.
    test_data = {"/etc/ssh/sshd_config":
                 "DSAAuthentication no\nPubKeyAuthentication yes"}
    host_data = self.GenFileData("SshdConfigFile", test_data, self.parser)
    results = self.RunChecks(host_data)
    self.assertCheckUndetected(chk_id, results)

  def testPubKeyAllowedFail(self):
    chk_id = "SSH-PUB-KEY-AUTHENTICATION"

    test_data = {"/etc/ssh/sshd_config":
                 "PubKeyAuthentication yes"}
    host_data = self.GenFileData("SshdConfigFile", test_data, self.parser)
    results = self.RunChecks(host_data)
    sym = "Found: Sshd configuration allows public key authentication."
    found = ["PubkeyAuthentication (or DSAAuthentication) = True"]
    self.assertCheckDetectedAnom(chk_id, results, sym, found)


def main(argv):
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)

