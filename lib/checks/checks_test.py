#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for checks."""
import os

import yaml

from grr.lib import config_lib
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.checks import checks
from grr.lib.checks import checks_test_lib
from grr.lib.rdfvalues import checks as checks_rdf
from grr.parsers import config_file
from grr.parsers import linux_cmd_parser
from grr.parsers import wmi_parser


CHECKS_DIR = os.path.join(config_lib.CONFIG["Test.data_dir"], "checks")

# Load some dpkg data
parser = linux_cmd_parser.DpkgCmdParser()
test_data = os.path.join(config_lib.CONFIG["Test.data_dir"], "dpkg.out")
with open(test_data) as f:
  DPKG_SW = list(parser.Parse(
      "/usr/bin/dpkg", ["-l"], f.read(), "", 0, 5, None))

# Load some wmi data
parser = wmi_parser.WMIInstalledSoftwareParser()
test_data = os.path.join(config_lib.CONFIG["Test.data_dir"], "wmi_sw.yaml")
WMI_SW = []
with open(test_data) as f:
  wmi = yaml.safe_load(f)
  for sw in wmi:
    WMI_SW.extend(parser.Parse(None, sw, None))

# Load an sshd config
parser = config_file.SshdConfigParser()
test_data = os.path.join(config_lib.CONFIG["Test.data_dir"], "sshd_config")
with open(test_data) as f:
  SSHD_CFG = list(parser.Parse(None, f, None))


def _LoadCheck(cfg_file, check_id):
  configs = checks.LoadConfigsFromFile(os.path.join(CHECKS_DIR, cfg_file))
  cfg = configs.get(check_id)
  return checks_rdf.Check(**cfg)


class MatchMethodTests(test_lib.GRRBaseTest):
  """Test match method selection and comparisons."""

  def setUp(self):
    super(MatchMethodTests, self).setUp()
    self.none = []
    self.one = [1]
    self.some = [1, 2, 3]
    self.baselines = [self.none, self.one, self.some]
    self.hint = checks_rdf.Hint()

  def testCheckNone(self):
    """NONE returns an anomaly if there are no results."""
    matcher = checks.Matcher(["NONE"], self.hint)
    for baseline in self.baselines:
      self.assertIsInstance(matcher.Detect(baseline, self.none),
                            rdfvalue.CheckResult)
      for result in [self.one, self.some]:
        self.assertFalse(matcher.Detect(baseline, result))

  def testCheckOne(self):
    """ONE operations should return anomalies if there is not one result."""
    matcher = checks.Matcher(["ONE"], self.hint)
    for baseline in self.baselines:
      self.assertIsInstance(matcher.Detect(baseline, self.one),
                            rdfvalue.CheckResult)
      for result in [self.none, self.some]:
        self.assertFalse(matcher.Detect(baseline, result))

  def testCheckSome(self):
    """SOME operations should return anomalies if there is >1 result."""
    matcher = checks.Matcher(["SOME"], self.hint)
    for baseline in self.baselines:
      self.assertIsInstance(matcher.Detect(baseline, self.some),
                            rdfvalue.CheckResult)
      for result in [self.none, self.one]:
        self.assertFalse(matcher.Detect(baseline, result))

  def testCheckAny(self):
    """ANY operations should not return anomalies if there are results."""
    matcher = checks.Matcher(["ANY"], self.hint)
    for baseline in self.baselines:
      for result in [self.one, self.some]:
        self.assertIsInstance(matcher.Detect(baseline, result),
                              rdfvalue.CheckResult)
      self.assertFalse(matcher.Detect(baseline, self.none))

  def testCheckAll(self):
    """ALL operations return anomalies if input and result counts differ."""
    matcher = checks.Matcher(["ALL"], self.hint)
    will_detect = [(self.one, self.one), (self.some, self.some)]
    not_detect = [(self.none, self.none), (self.some, self.one),
                  (self.some, self.none)]
    will_raise = [(self.none, self.one), (self.one, self.some),
                  (self.none, self.some)]
    for base, result in will_detect:
      self.assertIsInstance(matcher.Detect(base, result), rdfvalue.CheckResult)
    for base, result in not_detect:
      self.assertFalse(matcher.Detect(base, result))
    for base, result in will_raise:
      self.assertRaises(checks.ProcessingError, matcher.Detect, base, result)

  def testMultipleMatch(self):
    """Checks with multiple match methods emit results if any methods fire."""
    matcher = checks.Matcher(["NONE", "ONE"], self.hint)
    for baseline in self.baselines:
      for result in [self.none, self.one]:
        self.assertIsInstance(matcher.Detect(baseline, result),
                              rdfvalue.CheckResult)
      self.assertFalse(matcher.Detect(baseline, self.some))


class CheckLoaderTests(test_lib.GRRBaseTest):
  """Check definitions can be loaded."""

  def testLoadToDict(self):
    expect = {
        "SSHD-CHECK": {
            "check_id": "SSHD-CHECK",
            "method": [{
                "probe": [{"artifact": "SshdConfigFile", "match": ["ANY"],
                           "filters": [
                               {"type": "ObjectFilter",
                                "expression": "config.protocol contains 1"}]}],
                "target": {"os": ["Linux", "Darwin"]},
                "match": ["ANY"],
                "hint": {"problem": "Sshd allows protocol 1.",
                         "summary": "sshd parameter",
                         "format": "Configured protocols: {config.protocol}"}}],
            "match": "NONE"}}

    result = checks.LoadConfigsFromFile(os.path.join(CHECKS_DIR, "sshd.yaml"))
    self.assertEqual(expect.keys(), result.keys())
    # Start with basic check attributes.
    expect_check = expect["SSHD-CHECK"]
    result_check = result["SSHD-CHECK"]
    self.assertEqual(expect_check["check_id"], result_check["check_id"])
    self.assertEqual(expect_check["match"], result_check["match"])
    # Now dive into the method.
    expect_method = expect_check["method"][0]
    result_method = result_check["method"][0]
    self.assertEqual(expect_method["target"], result_method["target"])
    self.assertEqual(expect_method["match"], result_method["match"])
    self.assertDictEqual(expect_method["hint"], result_method["hint"])
    # Now dive into the probe.
    expect_probe = expect_method["probe"][0]
    result_probe = result_method["probe"][0]
    self.assertEqual(expect_probe["artifact"], result_probe["artifact"])
    self.assertEqual(expect_probe["match"], result_probe["match"])
    # Now dive into the filters.
    expect_filters = expect_probe["filters"][0]
    result_filters = result_probe["filters"][0]
    self.assertDictEqual(expect_filters, result_filters)

  def testLoadFromFiles(self):
    check_defs = [os.path.join(CHECKS_DIR, "sshd.yaml")]
    checks.LoadChecksFromFiles(check_defs)
    self.assertTrue(checks.CheckRegistry.checks.get("SSHD-CHECK"))


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
    self.kb = rdfvalue.KnowledgeBase()
    self.kb.hostname = "test.example.com"
    self.host_data = {"KnowledgeBase": self.kb,
                      "WMIInstalledSoftware": WMI_SW,
                      "DebianPackagesStatus": DPKG_SW,
                      "SshdConfigFile": SSHD_CFG}

  def testRegisterChecks(self):
    """Defined checks are present in the check registry."""
    self.assertEqual(self.sw_chk, checks.CheckRegistry.checks["SW-CHECK"])
    self.assertEqual(self.sshd_chk, checks.CheckRegistry.checks["SSHD-CHECK"])

  def testMapChecksToTriggers(self):
    """Checks are identified and run when their prerequisites are met."""
    expect = ["SW-CHECK"]
    result = checks.CheckRegistry.FindChecks(
        artifact="WMIInstalledSoftware", os="Windows")
    self.assertItemsEqual(expect, result)
    result = checks.CheckRegistry.FindChecks(
        artifact="DebianPackagesStatus", os="Linux")
    self.assertItemsEqual(expect, result)
    result = checks.CheckRegistry.FindChecks(
        artifact="DebianPackagesStatus", labels="foo")
    self.assertItemsEqual(expect, result)

    expect = ["SSHD-CHECK"]
    result = checks.CheckRegistry.FindChecks(artifact="SshdConfigFile",
                                             os="Darwin")
    self.assertItemsEqual(expect, result)
    result = checks.CheckRegistry.FindChecks(artifact="SshdConfigFile",
                                             os="Linux")
    self.assertItemsEqual(expect, result)

    # All sshd config checks specify an OS, so should get no results.
    expect = []
    result = checks.CheckRegistry.FindChecks(artifact="SshdConfigFile")
    self.assertItemsEqual(expect, result)
    result = checks.CheckRegistry.FindChecks(
        artifact="SshdConfigFile", os="Windows")
    self.assertItemsEqual(expect, result)

  def testMapArtifactsToTriggers(self):
    """Identify the artifacts that should be collected based on criteria."""
    expect = ["DebianPackagesStatus", "SshdConfigFile"]
    result = checks.CheckRegistry.SelectArtifacts(os="Linux")
    self.assertItemsEqual(expect, result)

    expect = ["WMIInstalledSoftware"]
    result = checks.CheckRegistry.SelectArtifacts(os="Windows")
    self.assertItemsEqual(expect, result)

    expect = ["DebianPackagesStatus"]
    result = checks.CheckRegistry.SelectArtifacts(
        os=None, cpe=None, labels="foo")
    self.assertItemsEqual(expect, result)


class ProcessHostDataTests(checks_test_lib.HostCheckTest):

  def setUp(self):
    super(ProcessHostDataTests, self).setUp()
    self.netcat = rdfvalue.CheckResult(
        check_id="SW-CHECK",
        anomaly=[
            rdfvalue.Anomaly(
                finding=["netcat-traditional 1.10-40 is installed"],
                explanation="Found: l337 software installed",
                type="ANALYSIS_ANOMALY")])
    self.sshd = rdfvalue.CheckResult(
        check_id="SSHD-CHECK",
        anomaly=[
            rdfvalue.Anomaly(
                finding=["Configured protocols: [2, 1]"],
                explanation="Found: Sshd allows protocol 1.",
                type="ANALYSIS_ANOMALY")])
    self.windows = rdfvalue.CheckResult(
        check_id="SW-CHECK",
        anomaly=[
            rdfvalue.Anomaly(
                finding=["Java 6.0.240 is installed"],
                explanation="Found: Old Java installation.",
                type="ANALYSIS_ANOMALY"),
            rdfvalue.Anomaly(
                finding=["Adware 2.1.1 is installed"],
                explanation="Found: Malicious software.",
                type="ANALYSIS_ANOMALY")])

    self.host_data = {"WMIInstalledSoftware": WMI_SW,
                      "DebianPackagesStatus": DPKG_SW,
                      "SshdConfigFile": SSHD_CFG}

  def testProcessLinuxHost(self):
    """Checks detect issues and return anomalies as check results."""
    self.SetKnowledgeBase("host.example.org", "Linux", self.host_data)
    results = self.RunChecks(self.host_data)
    self.assertRanChecks(["SW-CHECK", "SSHD-CHECK"], results)
    self.assertResultEqual(self.netcat, results["SW-CHECK"])
    self.assertResultEqual(self.sshd, results["SSHD-CHECK"])

  def testProcessWindowsHost(self):
    self.SetKnowledgeBase("host.example.org", "Windows", self.host_data)
    results = self.RunChecks(self.host_data)
    self.assertRanChecks(["SW-CHECK"], results)
    self.assertResultEqual(self.windows, results["SW-CHECK"])

  def testProcessDarwinHost(self):
    self.SetKnowledgeBase("host.example.org", "Darwin", self.host_data)
    results = self.RunChecks(self.host_data)
    self.assertRanChecks(["SSHD-CHECK"], results)
    self.assertResultEqual(self.sshd, results["SSHD-CHECK"])


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
