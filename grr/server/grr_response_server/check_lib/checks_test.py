#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for checks."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os


from future.utils import iterkeys
import yaml

from grr_response_core import config
from grr_response_core.lib import flags
from grr_response_core.lib.parsers import config_file as config_file_parsers
from grr_response_core.lib.parsers import linux_cmd_parser
from grr_response_core.lib.parsers import wmi_parser
from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_server.check_lib import checks
from grr_response_server.check_lib import checks_test_lib
from grr_response_server.check_lib import filters
from grr.test_lib import test_lib

CHECKS_DIR = os.path.join(config.CONFIG["Test.data_dir"], "checks")
TRIGGER_1 = ("DebianPackagesStatus", "Linux", None, None)
TRIGGER_2 = ("WMIInstalledSoftware", "Windows", None, None)
TRIGGER_3 = ("DebianPackagesStatus", None, None, "foo")

DPKG_SW = []
WMI_SW = []
SSHD_CFG = []


def GetDPKGData():
  if DPKG_SW:
    return DPKG_SW

  # Load some dpkg data
  parser = linux_cmd_parser.DpkgCmdParser()
  test_data = os.path.join(CHECKS_DIR, "data/dpkg.out")
  with open(test_data, "rb") as f:
    DPKG_SW.extend(
        parser.Parse("/usr/bin/dpkg", ["-l"], f.read(), "", 0, 5, None))
  return DPKG_SW


def GetWMIData():
  if WMI_SW:
    return WMI_SW

  # Load some wmi data
  parser = wmi_parser.WMIInstalledSoftwareParser()
  test_data = os.path.join(CHECKS_DIR, "data/wmi_sw.yaml")
  with open(test_data, "rb") as f:
    wmi = yaml.safe_load(f)
    for sw in wmi:
      WMI_SW.extend(parser.Parse(sw))

  return WMI_SW


def GetSSHDConfig():
  if SSHD_CFG:
    return SSHD_CFG

  # Load an sshd config
  parser = config_file_parsers.SshdConfigParser()
  test_data = os.path.join(config.CONFIG["Test.data_dir"],
                           "VFSFixture/etc/ssh/sshd_config")
  with open(test_data, "rb") as f:
    SSHD_CFG.extend(parser.Parse(None, f, None))
  return SSHD_CFG


class MatchMethodTests(test_lib.GRRBaseTest):
  """Test match method selection and comparisons."""

  def setUp(self):
    super(MatchMethodTests, self).setUp()
    self.none = []
    self.one = [1]
    self.some = [1, 2, 3]
    self.baselines = [self.none, self.one, self.some]
    self.hint = checks.Hint()

  def testCheckNone(self):
    """NONE returns an anomaly if there are no results."""
    matcher = checks.Matcher(["NONE"], self.hint)
    for baseline in self.baselines:
      self.assertIsInstance(
          matcher.Detect(baseline, self.none), checks.CheckResult)
      for result in [self.one, self.some]:
        self.assertFalse(matcher.Detect(baseline, result))

  def testCheckOne(self):
    """ONE operations should return anomalies if there is not one result."""
    matcher = checks.Matcher(["ONE"], self.hint)
    for baseline in self.baselines:
      self.assertIsInstance(
          matcher.Detect(baseline, self.one), checks.CheckResult)
      for result in [self.none, self.some]:
        self.assertFalse(matcher.Detect(baseline, result))

  def testCheckSome(self):
    """SOME operations should return anomalies if there is >1 result."""
    matcher = checks.Matcher(["SOME"], self.hint)
    for baseline in self.baselines:
      self.assertIsInstance(
          matcher.Detect(baseline, self.some), checks.CheckResult)
      for result in [self.none, self.one]:
        self.assertFalse(matcher.Detect(baseline, result))

  def testCheckAny(self):
    """ANY operations should not return anomalies if there are results."""
    matcher = checks.Matcher(["ANY"], self.hint)
    for baseline in self.baselines:
      for result in [self.one, self.some]:
        self.assertIsInstance(
            matcher.Detect(baseline, result), checks.CheckResult)
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
      self.assertIsInstance(matcher.Detect(base, result), checks.CheckResult)
    for base, result in not_detect:
      self.assertFalse(matcher.Detect(base, result))
    for base, result in will_raise:
      self.assertRaises(checks.ProcessingError, matcher.Detect, base, result)

  def testMultipleMatch(self):
    """Checks with multiple match methods emit results if any methods fire."""
    matcher = checks.Matcher(["NONE", "ONE"], self.hint)
    for baseline in self.baselines:
      for result in [self.none, self.one]:
        self.assertIsInstance(
            matcher.Detect(baseline, result), checks.CheckResult)
      self.assertFalse(matcher.Detect(baseline, self.some))


class CheckLoaderTests(test_lib.GRRBaseTest):
  """Check definitions can be loaded."""

  def testLoadToDict(self):
    result = checks.LoadConfigsFromFile(os.path.join(CHECKS_DIR, "sshd.yaml"))
    self.assertCountEqual(["SSHD-CHECK", "SSHD-PERMS"], result)
    # Start with basic check attributes.
    result_check = result["SSHD-CHECK"]
    self.assertEqual("SSHD-CHECK", result_check["check_id"])
    self.assertEqual("NONE", result_check["match"])
    # Now dive into the method.
    result_method = result_check["method"][0]
    self.assertEqual({"os": ["Linux", "Darwin"]}, result_method["target"])
    self.assertEqual(["ANY"], result_method["match"])
    expect_hint = {
        "problem": "Sshd allows protocol 1.",
        "format": "Configured protocols: {config.protocol}"
    }
    self.assertDictEqual(expect_hint, result_method["hint"])
    # Now dive into the probe.
    result_probe = result_method["probe"][0]
    self.assertEqual("SshdConfigFile", result_probe["artifact"])
    self.assertEqual(["ANY"], result_probe["match"])
    # Now dive into the filters.
    expect_filters = {
        "type": "ObjectFilter",
        "expression": "config.protocol contains 1"
    }
    result_filters = result_probe["filters"][0]
    self.assertDictEqual(expect_filters, result_filters)
    # Make sure any specified probe context is set.
    result_check = result["SSHD-PERMS"]
    probe = result_check["method"][0]["probe"][0]
    result_context = str(probe["result_context"])
    self.assertCountEqual("RAW", result_context)

  def testLoadFromFiles(self):
    check_defs = [os.path.join(CHECKS_DIR, "sshd.yaml")]
    checks.LoadChecksFromFiles(check_defs)
    self.assertTrue(checks.CheckRegistry.checks.get("SSHD-CHECK"))


class CheckRegistryTests(test_lib.GRRBaseTest):

  sw_chk = None
  sshd_chk = None
  sshd_perms = None

  def _LoadCheck(self, cfg_file, check_id):
    configs = checks.LoadConfigsFromFile(os.path.join(CHECKS_DIR, cfg_file))
    cfg = configs.get(check_id)
    return checks.Check(**cfg)

  def setUp(self):
    super(CheckRegistryTests, self).setUp()
    if self.sw_chk is None:
      self.sw_chk = self._LoadCheck("sw.yaml", "SW-CHECK")
      checks.CheckRegistry.RegisterCheck(
          check=self.sw_chk, source="dpkg.out", overwrite_if_exists=True)
    if self.sshd_chk is None:
      self.sshd_chk = self._LoadCheck("sshd.yaml", "SSHD-CHECK")
      checks.CheckRegistry.RegisterCheck(
          check=self.sshd_chk, source="sshd_config", overwrite_if_exists=True)
    if self.sshd_perms is None:
      self.sshd_perms = self._LoadCheck("sshd.yaml", "SSHD-PERMS")
      checks.CheckRegistry.RegisterCheck(
          check=self.sshd_perms, source="sshd_config", overwrite_if_exists=True)
    self.kb = rdf_client.KnowledgeBase()
    self.kb.fqdn = "test.example.com"
    self.host_data = {
        "KnowledgeBase": self.kb,
        "WMIInstalledSoftware": GetWMIData(),
        "DebianPackagesStatus": GetDPKGData(),
        "SshdConfigFile": GetSSHDConfig()
    }

  def testRegisterChecks(self):
    """Defined checks are present in the check registry."""
    self.assertEqual(self.sw_chk, checks.CheckRegistry.checks["SW-CHECK"])
    self.assertEqual(self.sshd_chk, checks.CheckRegistry.checks["SSHD-CHECK"])
    self.assertEqual(self.sshd_perms, checks.CheckRegistry.checks["SSHD-PERMS"])

  def testMapChecksToTriggers(self):
    """Checks are identified and run when their prerequisites are met."""
    expect = ["SW-CHECK"]
    result = checks.CheckRegistry.FindChecks(
        artifact="WMIInstalledSoftware", os_name="Windows")
    self.assertCountEqual(expect, result)
    result = checks.CheckRegistry.FindChecks(
        artifact="DebianPackagesStatus", os_name="Linux")
    self.assertCountEqual(expect, result)
    result = checks.CheckRegistry.FindChecks(
        artifact="DebianPackagesStatus", labels="foo")
    self.assertCountEqual(expect, result)

    self.assertIn(
        "SSHD-CHECK",
        checks.CheckRegistry.FindChecks(
            artifact="SshdConfigFile", os_name="Darwin"))

    self.assertIn(
        "SSHD-CHECK",
        checks.CheckRegistry.FindChecks(
            artifact="SshdConfigFile", os_name="Linux"))

    # All sshd config checks specify an OS, so should get no results.
    self.assertEmpty(checks.CheckRegistry.FindChecks(artifact="SshdConfigFile"))
    self.assertEmpty(
        checks.CheckRegistry.FindChecks(
            artifact="SshdConfigFile", os_name="Windows"))

  def testRestrictChecksFiltersCheckOptions(self):
    result = set(
        checks.CheckRegistry.FindChecks(
            artifact="SshdConfigFile",
            os_name="Linux",
            restrict_checks=["SSHD-CHECK"]))
    self.assertCountEqual(["SSHD-CHECK"], result)
    result = set(
        checks.CheckRegistry.FindChecks(
            artifact="SshdConfigFile",
            os_name="Linux",
            restrict_checks=["SW_CHECK"]))
    self.assertFalse(result)

  def testMapArtifactsToTriggers(self):
    """Identify the artifacts that should be collected based on criteria."""
    # Test whether all expected checks were mapped.
    self.assertContainsSubset(
        ["DebianPackagesStatus", "SshdConfigFile"],
        checks.CheckRegistry.SelectArtifacts(os_name="Linux"))

    self.assertIn("WMIInstalledSoftware",
                  checks.CheckRegistry.SelectArtifacts(os_name="Windows"))

    self.assertIn(
        "DebianPackagesStatus",
        checks.CheckRegistry.SelectArtifacts(
            os_name=None, cpe=None, labels="foo"))

    self.assertIn(
        "DebianPackagesStatus",
        checks.CheckRegistry.SelectArtifacts(
            os_name="Linux", restrict_checks=["SW-CHECK"]))


class ProcessHostDataTests(checks_test_lib.HostCheckTest):

  def setUp(self):
    super(ProcessHostDataTests, self).setUp()
    registered = set(iterkeys(checks.CheckRegistry.checks))
    if "SW-CHECK" not in registered:
      checks.LoadChecksFromFiles([os.path.join(CHECKS_DIR, "sw.yaml")])
    if "SSHD-CHECK" not in registered:
      checks.LoadChecksFromFiles([os.path.join(CHECKS_DIR, "sshd.yaml")])
    self.netcat = checks.CheckResult(
        check_id="SW-CHECK",
        anomaly=[
            rdf_anomaly.Anomaly(
                finding=["netcat-traditional 1.10-40 is installed"],
                symptom="Found: l337 software installed",
                type="ANALYSIS_ANOMALY")
        ])
    self.sshd = checks.CheckResult(
        check_id="SSHD-CHECK",
        anomaly=[
            rdf_anomaly.Anomaly(
                finding=["Configured protocols: 2,1"],
                symptom="Found: Sshd allows protocol 1.",
                type="ANALYSIS_ANOMALY")
        ])
    self.windows = checks.CheckResult(
        check_id="SW-CHECK",
        anomaly=[
            rdf_anomaly.Anomaly(
                finding=["Java 6.0.240 is installed"],
                symptom="Found: Old Java installation.",
                type="ANALYSIS_ANOMALY"),
            rdf_anomaly.Anomaly(
                finding=["Adware 2.1.1 is installed"],
                symptom="Found: Malicious software.",
                type="ANALYSIS_ANOMALY")
        ])

    self.data = {
        "WMIInstalledSoftware": self.SetArtifactData(parsed=GetWMIData()),
        "DebianPackagesStatus": self.SetArtifactData(parsed=GetDPKGData()),
        "SshdConfigFile": self.SetArtifactData(parsed=GetSSHDConfig())
    }

  def testProcessLinuxHost(self):
    """Checks detect issues and return anomalies as check results."""
    host_data = self.SetKnowledgeBase("host.example.org", "Linux", self.data)
    results = self.RunChecks(host_data)
    self.assertRanChecks(["SW-CHECK", "SSHD-CHECK"], results)
    self.assertResultEqual(self.netcat, results["SW-CHECK"])
    self.assertResultEqual(self.sshd, results["SSHD-CHECK"])

  def testProcessLinuxRestrictChecks(self):
    """Checks detect issues and return anomalies as check results."""
    host_data = self.SetKnowledgeBase("host.example.org", "Linux", self.data)
    results = self.RunChecks(host_data, restrict_checks=["SW-CHECK"])
    self.assertRanChecks(["SW-CHECK"], results)
    self.assertResultEqual(self.netcat, results["SW-CHECK"])

  def testProcessWindowsHost(self):
    host_data = self.SetKnowledgeBase("host.example.org", "Windows", self.data)
    results = self.RunChecks(host_data)
    self.assertRanChecks(["SW-CHECK"], results)
    self.assertResultEqual(self.windows, results["SW-CHECK"])

  def testProcessDarwinHost(self):
    host_data = self.SetKnowledgeBase("host.example.org", "Darwin", self.data)
    results = self.RunChecks(host_data)
    self.assertRanChecks(["SSHD-CHECK"], results)
    self.assertResultEqual(self.sshd, results["SSHD-CHECK"])


class ChecksTestBase(test_lib.GRRBaseTest):
  pass


class FilterTests(ChecksTestBase):
  """Test 'Filter' setup and operations."""

  def setUp(self, *args, **kwargs):
    super(FilterTests, self).setUp(*args, **kwargs)
    filters.Filter.filters = {}

  def tearDown(self, *args, **kwargs):
    filters.Filter.filters = {}
    super(FilterTests, self).tearDown(*args, **kwargs)

  def testNonexistentFilterIsError(self):
    self.assertRaises(filters.DefinitionError, checks.Filter, type="NoFilter")

  def testAddFilters(self):
    base_filt = checks.Filter(type="Filter", expression="do nothing")
    self.assertIsInstance(base_filt._filter, filters.Filter)
    obj_filt = checks.Filter(type="ObjectFilter", expression="test is 'ok'")
    self.assertIsInstance(obj_filt._filter, filters.ObjectFilter)
    rdf_filt = checks.Filter(
        type="RDFFilter", expression="AttributedDict,SSHConfig")
    self.assertIsInstance(rdf_filt._filter, filters.RDFFilter)


class ProbeTest(ChecksTestBase):
  """Test 'Probe' operations."""

  configs = {}

  def setUp(self, **kwargs):
    super(ProbeTest, self).setUp(**kwargs)
    if not self.configs:
      config_file = os.path.join(CHECKS_DIR, "probes.yaml")
      with open(config_file, "rb") as data:
        for cfg in yaml.safe_load_all(data):
          name = cfg.get("name")
          probe_cfg = cfg.get("probe", [{}])
          self.configs[name] = probe_cfg[0]

  def Init(self, name, artifact, handler_class, result_context):
    """Helper method to verify that the Probe sets up the right handler."""
    cfg = self.configs.get(name)
    probe = checks.Probe(**cfg)
    self.assertEqual(artifact, probe.artifact)
    self.assertIsInstance(probe.handler, handler_class)
    self.assertIsInstance(probe.matcher, checks.Matcher)
    self.assertCountEqual(result_context, str(probe.result_context))

  def testInitialize(self):
    """Tests the input/output sequence validation."""
    self.Init("NO-FILTER", "DpkgDb", filters.NoOpHandler, "PARSER")
    self.Init("ANOM-CONTEXT", "DpkgDb", filters.NoOpHandler, "ANOMALY")
    self.Init("SERIAL", "DpkgDb", filters.SerialHandler, "PARSER")
    self.Init("PARALLEL", "DpkgDb", filters.ParallelHandler, "PARSER")
    self.Init("BASELINE", "DpkgDb", filters.SerialHandler, "PARSER")

  def testParse(self):
    """Host data should be passed to filters, results should be returned."""
    pass

  def testParseWithBaseline(self):
    pass

  def testValidate(self):
    cfg = self.configs.get("NO-ARTIFACT")
    self.assertRaises(filters.DefinitionError, checks.Probe, cfg)


class MethodTest(ChecksTestBase):
  """Test 'Method' operations."""

  configs = {}

  def setUp(self, **kwargs):
    super(MethodTest, self).setUp(**kwargs)
    if not self.configs:
      config_file = os.path.join(CHECKS_DIR, "sw.yaml")
      with open(config_file, "rb") as data:
        check_def = yaml.safe_load(data)
        self.configs = check_def["method"]

  def testMethodRegistersTriggers(self):
    m_1, m_2, m_3 = [checks.Method(**cfg) for cfg in self.configs]
    expect_1 = [TRIGGER_1]
    result_1 = [c.attr for c in m_1.triggers.conditions]
    self.assertEqual(expect_1, result_1)
    expect_2 = [TRIGGER_2]
    result_2 = [c.attr for c in m_2.triggers.conditions]
    self.assertEqual(expect_2, result_2)
    expect_3 = [TRIGGER_3]
    result_3 = [c.attr for c in m_3.triggers.conditions]
    self.assertEqual(expect_3, result_3)

  def testMethodRoutesDataToProbes(self):
    pass

  def testValidate(self):
    pass


class CheckTest(ChecksTestBase):
  """Test 'Check' operations."""

  cfg = {}

  def setUp(self, **kwargs):
    super(CheckTest, self).setUp(**kwargs)
    if not self.cfg:
      config_file = os.path.join(CHECKS_DIR, "sw.yaml")
      with open(config_file, "rb") as data:
        self.cfg = yaml.safe_load(data)
      self.host_data = {
          "DebianPackagesStatus": {
              "ANOMALY": [],
              "PARSER": GetDPKGData(),
              "RAW": []
          },
          "WMIInstalledSoftware": {
              "ANOMALY": [],
              "PARSER": GetWMIData(),
              "RAW": []
          }
      }

  def testInitializeCheck(self):
    chk = checks.Check(**self.cfg)
    self.assertEqual("SW-CHECK", chk.check_id)
    self.assertCountEqual(["ANY"], [str(c) for c in chk.match])

  def testGenerateTriggerMap(self):
    chk = checks.Check(**self.cfg)
    expect = [TRIGGER_1, TRIGGER_3]
    result = [c.attr for c in chk.triggers.Search("DebianPackagesStatus")]
    self.assertCountEqual(expect, result)
    expect = [TRIGGER_2]
    result = [c.attr for c in chk.triggers.Search("WMIInstalledSoftware")]
    self.assertCountEqual(expect, result)

  def testParseCheckFromConfig(self):
    chk = checks.Check(**self.cfg)
    # Triggers 1 (linux packages) & 2 (windows software) should return results.
    # Trigger 3 should not return results as no host data has the label 'foo'.
    result_1 = chk.Parse([TRIGGER_1], self.host_data)
    result_2 = chk.Parse([TRIGGER_2], self.host_data)
    result_3 = chk.Parse([TRIGGER_3], self.host_data)
    self.assertTrue(result_1)
    self.assertTrue(result_2)
    self.assertFalse(result_3)

  def testValidate(self):
    pass


class CheckResultsTest(ChecksTestBase):
  """Test 'CheckResult' operations."""

  def testExtendAnomalies(self):
    anomaly1 = {
        "finding": ["Adware 2.1.1 is installed"],
        "symptom": "Found: Malicious software.",
        "explanation": "Remove software.",
        "type": "ANALYSIS_ANOMALY"
    }
    anomaly2 = {
        "finding": ["Java 6.0.240 is installed"],
        "symptom": "Found: Old Java installation.",
        "explanation": "Update Java.",
        "type": "ANALYSIS_ANOMALY"
    }
    result = checks.CheckResult(
        check_id="SW-CHECK", anomaly=[rdf_anomaly.Anomaly(**anomaly1)])
    other = checks.CheckResult(
        check_id="SW-CHECK", anomaly=[rdf_anomaly.Anomaly(**anomaly2)])
    result.ExtendAnomalies([other])
    expect = {"check_id": "SW-CHECK", "anomaly": [anomaly1, anomaly2]}
    self.assertDictEqual(expect, result.ToPrimitiveDict())


class HintDefinitionTests(ChecksTestBase):
  """Test 'Hint' operations."""

  configs = {}

  def setUp(self, **kwargs):
    super(HintDefinitionTests, self).setUp(**kwargs)
    if not self.configs:
      config_file = os.path.join(CHECKS_DIR, "sw.yaml")
      with open(config_file, "rb") as data:
        cfg = yaml.safe_load(data)
    chk = checks.Check(**cfg)
    self.lin_method, self.win_method, self.foo_method = list(chk.method)

  def testInheritHintConfig(self):
    # Adding newlines to ensure they get stripped (can happen when reading from
    # YAML).
    lin_problem = "l337 software installed\n"
    lin_format = "{name} {version} is installed\n"
    # Methods should not have a hint template.
    self.assertEqual(lin_problem.strip(), self.lin_method.hint.problem)
    self.assertFalse(self.lin_method.hint.hinter.template)
    # Formatting should be present in probes, if defined.
    for probe in self.lin_method.probe:
      self.assertEqual(lin_problem.strip(), probe.hint.problem)
      self.assertEqual(lin_format.strip(), probe.hint.format)

    foo_problem = "Sudo not installed\n"
    # Methods should not have a hint template.
    self.assertEqual(foo_problem.strip(), self.foo_method.hint.problem)
    self.assertFalse(self.foo_method.hint.hinter.template)
    # Formatting should be missing in probes, if undefined.
    for probe in self.foo_method.probe:
      self.assertEqual(foo_problem.strip(), probe.hint.problem)
      self.assertFalse(probe.hint.format)

  def testOverlayHintConfig(self):
    # Adding newlines to ensure they get stripped (can happen when reading from
    # YAML).
    generic_problem = "Malicious software.\n"
    java_problem = "Old Java installation.\n"
    generic_format = "{name} {version} is installed\n"
    # Methods should not have a hint template.
    self.assertEqual(generic_problem.strip(), self.win_method.hint.problem)
    self.assertFalse(self.win_method.hint.hinter.template)
    # Formatting should be present in probes.
    probe_1, probe_2 = list(self.win_method.probe)
    self.assertEqual(java_problem.strip(), probe_1.hint.problem)
    self.assertEqual(generic_format.strip(), probe_1.hint.format)
    self.assertEqual(generic_problem.strip(), probe_2.hint.problem)
    self.assertEqual(generic_format.strip(), probe_2.hint.format)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
