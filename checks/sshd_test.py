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

  def testAuthorizedKeysCommandSucceed(self):
    chk_id = "SSH-AUTHORIZED-KEYS"

    test_data = {"/etc/ssh/sshd_config": ""}
    host_data = self.GenFileData("SshdConfigFile", test_data, self.parser)
    results = self.RunChecks(host_data)
    self.assertCheckUndetected(chk_id, results)
    test_data = {"/etc/ssh/sshd_config": "AuthorizedKeysCommand none"}
    host_data = self.GenFileData("SshdConfigFile", test_data, self.parser)
    results = self.RunChecks(host_data)
    self.assertCheckUndetected(chk_id, results)

  def testAuthorizedKeysCommandFail(self):
    chk_id = "SSH-AUTHORIZED-KEYS"

    test_data = {"/etc/ssh/sshd_config":
                 "AuthorizedKeysCommand \"/bin/pubkey-helper -s %u\""}
    host_data = self.GenFileData("SshdConfigFile", test_data, self.parser)
    results = self.RunChecks(host_data)
    sym = "Found: Sshd configuration sets an authorized key command."
    found = ["AuthorizedKeysCommand = \"/bin/pubkey-helper -s %u\""]
    self.assertCheckDetectedAnom(chk_id, results, sym, found)

  def testAuthorizedKeysFileSucceed(self):
    chk_id = "SSH-AUTHORIZED-KEYS"

    test_data = {"/etc/ssh/sshd_config":
                 "AuthorizedKeysFile none"}
    host_data = self.GenFileData("SshdConfigFile", test_data, self.parser)
    results = self.RunChecks(host_data)
    self.assertCheckUndetected(chk_id, results)

  def testAuthorizedKeysFileFail(self):
    chk_id = "SSH-AUTHORIZED-KEYS"

    test_data = {"/etc/ssh/sshd_config":
                 "AuthorizedKeysFile none /etc/ssh_keys"}
    host_data = self.GenFileData("SshdConfigFile", test_data, self.parser)
    results = self.RunChecks(host_data)
    sym = "Found: Sshd configuration sets an authorized key file."
    found = ["AuthorizedKeysFile = /etc/ssh_keys"]
    self.assertCheckDetectedAnom(chk_id, results, sym, found)


def main(argv):
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)

