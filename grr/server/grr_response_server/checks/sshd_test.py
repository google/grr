#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for SSHd state checks."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags
from grr_response_core.lib.parsers import config_file
from grr_response_server.check_lib import checks_test_lib
from grr.test_lib import test_lib


class SshdCheckTests(checks_test_lib.HostCheckTest):
  """Test the sshd checks."""

  @classmethod
  def setUpClass(cls):
    super(SshdCheckTests, cls).setUpClass()

    cls.LoadCheck("sshd.yaml")
    cls.parser = config_file.SshdConfigParser()

  def testProtocolFail(self):
    chk_id = "CIS-SSH-PROTOCOL"

    test_data = {"/etc/ssh/sshd_config": "# Comment line\nProtocol 2,1"}
    host_data = self.GenFileData("SshdConfigFile", test_data, self.parser)
    results = self.RunChecks(host_data)
    sym = "Found: Sshd configuration supports protocol 1."
    found = ["Protocol = 2,1"]
    self.assertCheckDetectedAnom(chk_id, results, sym, found)

  def testPermitRootLoginFail(self):
    chk_id = "CIS-SSH-PERMIT-ROOT-LOGIN"

    test_data = {"/etc/ssh/sshd_config": "PermitRootLogin without-password"}
    host_data = self.GenFileData("SshdConfigFile", test_data, self.parser)
    results = self.RunChecks(host_data)
    sym = "Found: Sshd configuration permits direct root login."
    found = ["PermitRootLogin = without-password"]
    self.assertCheckDetectedAnom(chk_id, results, sym, found)

  def testPermitRootLoginSucceed(self):
    chk_id = "CIS-SSH-PERMIT-ROOT-LOGIN"

    test_data = {"/etc/ssh/sshd_config": "PermitRootLogin no"}
    host_data = self.GenFileData("SshdConfigFile", test_data, self.parser)
    results = self.RunChecks(host_data)
    self.assertCheckUndetected(chk_id, results)

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

    test_data = {
        "/etc/ssh/sshd_config":
            "AuthorizedKeysCommand \"/bin/pubkey-helper -s %u\""
    }
    host_data = self.GenFileData("SshdConfigFile", test_data, self.parser)
    results = self.RunChecks(host_data)
    sym = "Found: Sshd configuration sets an authorized key command."
    found = ["AuthorizedKeysCommand = \"/bin/pubkey-helper -s %u\""]
    self.assertCheckDetectedAnom(chk_id, results, sym, found)

  def testAuthorizedKeysFileSucceed(self):
    chk_id = "SSH-AUTHORIZED-KEYS"

    test_data = {"/etc/ssh/sshd_config": "AuthorizedKeysFile none"}
    host_data = self.GenFileData("SshdConfigFile", test_data, self.parser)
    results = self.RunChecks(host_data)
    self.assertCheckUndetected(chk_id, results)

  def testAuthorizedKeysFileFail(self):
    chk_id = "SSH-AUTHORIZED-KEYS"

    test_data = {
        "/etc/ssh/sshd_config": "AuthorizedKeysFile none /etc/ssh_keys"
    }
    host_data = self.GenFileData("SshdConfigFile", test_data, self.parser)
    results = self.RunChecks(host_data)
    sym = "Found: Sshd configuration sets an authorized key file."
    found = ["AuthorizedKeysFile = /etc/ssh_keys"]
    self.assertCheckDetectedAnom(chk_id, results, sym, found)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
