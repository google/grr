#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for checks."""
import os

from grr.lib import config_lib
from grr.lib import flags
from grr.lib import test_lib
from grr.lib.checks import checks
from grr.lib.rdfvalues import checks as checks_rdf


CHECKS_DIR = os.path.join(config_lib.CONFIG["Test.data_dir"], "checks")


def _LoadCheck(cfg_file, check_id):
  configs = checks.LoadConfigsFromFile(os.path.join(CHECKS_DIR, cfg_file))
  cfg = configs.get(check_id)
  return checks_rdf.Check(**cfg)


class CheckRegistryTests(test_lib.GRRBaseTest):

  sw_chk = None
  sshd_chk = None

  def setUp(self):
    super(CheckRegistryTests, self).setUp()
    if self.sw_chk is None:
      self.sw_chk = _LoadCheck("sw.yaml", "SW-CHECK")
      checks.CheckRegistry.RegisterCheck(check=self.sw_chk,
                                         source="dpkg.out",
                                         overwrite_if_exists=True)
    if self.sshd_chk is None:
      self.sshd_chk = _LoadCheck("sshd.yaml", "SSHD-CHECK")
      checks.CheckRegistry.RegisterCheck(check=self.sshd_chk,
                                         source="sshd_config",
                                         overwrite_if_exists=True)

  def testRegisterChecks(self):
    self.assertEqual(self.sw_chk, checks.CheckRegistry.checks["SW-CHECK"])
    self.assertEqual(self.sshd_chk, checks.CheckRegistry.checks["SSHD-CHECK"])

  def testMapChecksToTriggers(self):
    expect = ["SW-CHECK"]
    result = checks.CheckRegistry.FindChecks(
        artifact="WMIInstalledSoftware", os="Windows")
    self.assertItemsEqual(expect, result)
    result = checks.CheckRegistry.FindChecks(
        artifact="SoftwarePackage", os="Linux")
    self.assertItemsEqual(expect, result)
    result = checks.CheckRegistry.FindChecks(
        artifact="SoftwarePackage", labels="foo")
    self.assertItemsEqual(expect, result)

    expect = ["SSHD-CHECK"]
    result = checks.CheckRegistry.FindChecks(artifact="SshdConfig", os="OSX")
    self.assertItemsEqual(expect, result)
    result = checks.CheckRegistry.FindChecks(artifact="SshdConfig", os="Linux")
    self.assertItemsEqual(expect, result)

    # All sshd config checks specify an OS, so should get no results.
    expect = []
    result = checks.CheckRegistry.FindChecks(artifact="SshdConfig")
    self.assertItemsEqual(expect, result)
    result = checks.CheckRegistry.FindChecks(
        artifact="SshdConfig", os="Windows")
    self.assertItemsEqual(expect, result)

  def testMapArtifactsToTriggers(self):
    expect = ["SoftwarePackage", "SshdConfig"]
    result = checks.CheckRegistry.SelectArtifacts(os="Linux")
    self.assertItemsEqual(expect, result)

    expect = ["WMIInstalledSoftware"]
    result = checks.CheckRegistry.SelectArtifacts(os="Windows")
    self.assertItemsEqual(expect, result)

    expect = ["SoftwarePackage"]
    result = checks.CheckRegistry.SelectArtifacts(
        os=None, cpe=None, labels="foo")
    self.assertItemsEqual(expect, result)


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
