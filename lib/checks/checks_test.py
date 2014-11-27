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
                      "SoftwarePackage": DPKG_SW,
                      "SshdConfig": SSHD_CFG}

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
    """Identify the artifacts that should be collected based on criteria."""
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

  def testProcessHostData(self):
    """Checks detect issues and return anomalies as check results."""
    netcat = {"check_id": u"SW-CHECK",
              "anomaly": [{
                  "finding": [u"netcat-traditional 1.10-40 is installed"],
                  "explanation": u"Found: l337 software installed",
                  "type": "ANALYSIS_ANOMALY"}]}
    sshd = {"check_id": u"SSHD-CHECK",
            "anomaly": [{
                "finding": [u"Configured protocols: [2, 1]"],
                "explanation": u"Found: Sshd allows protocol 1.",
                "type": "ANALYSIS_ANOMALY"}]}
    windows = {"check_id": u"SW-CHECK",
               "anomaly": [{"finding": [u"Adware 2.1.1 is installed"],
                            "explanation": u"Found: Malicious software.",
                            "type": "ANALYSIS_ANOMALY"},
                           {"finding": [u"Java 6.0.240 is installed"],
                            "explanation": u"Found: Old Java installation.",
                            "type": "ANALYSIS_ANOMALY"}]}

    self.kb.os = "Linux"
    results = [r for r in checks.CheckHost(self.host_data)]
    results = {r.check_id: r.ToPrimitiveDict() for r in results}
    self.assertItemsEqual(["SW-CHECK", "SSHD-CHECK"], results.keys())
    self.assertEqual(netcat, results["SW-CHECK"])
    self.assertEqual(sshd, results["SSHD-CHECK"])

    # Windows checks return multiple anomalies, ensure that all are correct.
    # Need to specify individual entries to accommodate variable dictionary
    # ordering effects.
    self.kb.os = "Windows"
    results = [r for r in checks.CheckHost(self.host_data)]
    results = {r.check_id: r.ToPrimitiveDict() for r in results}
    self.assertItemsEqual(["SW-CHECK"], results.keys())
    result = results["SW-CHECK"]
    anomalies = result["anomaly"]
    expected_anomalies = windows["anomaly"]
    self.assertEqual(2, len(anomalies))
    for expected in expected_anomalies:
      self.assertTrue(expected in anomalies)

    self.kb.os = "OSX"
    results = [r for r in checks.CheckHost(self.host_data)]
    results = {r.check_id: r.ToPrimitiveDict() for r in results}
    self.assertItemsEqual(["SSHD-CHECK"], results.keys())
    self.assertDictEqual(sshd, results["SSHD-CHECK"])


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
