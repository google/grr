#!/usr/bin/env python
"""Tests for grr.lib.rdfvalues.checks."""
import os
import yaml

from grr.lib import config_lib
from grr.lib import test_lib
from grr.lib.checks import checks as checks_lib
from grr.lib.checks import filters
from grr.lib.rdfvalues import anomaly
from grr.lib.rdfvalues import checks
from grr.parsers import linux_cmd_parser
from grr.parsers import wmi_parser


CONFIGS = os.path.join(config_lib.CONFIG["Test.data_dir"], "checks")
TRIGGER_1 = ("SoftwarePackage", "Linux", None, None)
TRIGGER_2 = ("WMIInstalledSoftware", "Windows", None, None)
TRIGGER_3 = ("SoftwarePackage", None, None, "foo")

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


class ProbeTest(test_lib.GRRBaseTest):
  """Test 'Probe' operations."""

  configs = {}

  def setUp(self, **kwargs):
    super(ProbeTest, self).setUp(**kwargs)
    if not self.configs:
      config_file = os.path.join(CONFIGS, "probes.yaml")
      with open(config_file) as data:
        for cfg in yaml.safe_load_all(data):
          name = cfg.get("name")
          probe_cfg = cfg.get("probe", [{}])
          self.configs[name] = probe_cfg[0]

  def Init(self, name, artifact, handler_class):
    """Helper method to verify that the Probe sets up the right handler."""
    cfg = self.configs.get(name)
    probe = checks.Probe(**cfg)
    self.assertEqual(artifact, probe.artifact)
    self.assertIsInstance(probe.handler, handler_class)
    self.assertIsInstance(probe.matcher, checks_lib.Matcher)

  def testInitialize(self):
    """Tests the input/output sequence validation."""
    self.Init("NO-FILTER", "DpkgDb", filters.NoOpHandler)
    self.Init("SERIAL", "DpkgDb", filters.SerialHandler)
    self.Init("PARALLEL", "DpkgDb", filters.ParallelHandler)
    self.Init("BASELINE", "DpkgDb", filters.SerialHandler)

  def testParse(self):
    """Host data should be passed to filters, results should be returned."""
    pass

  def testParseWithBaseline(self):
    pass

  def testValidate(self):
    cfg = self.configs.get("NO-ARTIFACT")
    self.assertRaises(filters.DefinitionError, checks.Probe, cfg)


class MethodTest(test_lib.GRRBaseTest):
  """Test 'Method' operations."""

  configs = {}

  def setUp(self, **kwargs):
    super(MethodTest, self).setUp(**kwargs)
    if not self.configs:
      config_file = os.path.join(CONFIGS, "sw.yaml")
      with open(config_file) as data:
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


class CheckTest(test_lib.GRRBaseTest):
  """Test 'Check' operations."""

  cfg = {}

  def setUp(self, **kwargs):
    super(CheckTest, self).setUp(**kwargs)
    if not self.cfg:
      config_file = os.path.join(CONFIGS, "sw.yaml")
      with open(config_file) as data:
        self.cfg = yaml.safe_load(data)
      self.host_data = {"SoftwarePackage": DPKG_SW,
                        "WMIInstalledSoftware": WMI_SW}

  def testInitializeCheck(self):
    chk = checks.Check(**self.cfg)
    self.assertEqual("SW-CHECK", chk.check_id)
    self.assertItemsEqual(["ANY"], [str(c) for c in chk.match])

  def testGenerateTriggerMap(self):
    chk = checks.Check(**self.cfg)
    expect = [TRIGGER_1, TRIGGER_3]
    result = [c.attr for c in chk.triggers.Search("SoftwarePackage")]
    self.assertItemsEqual(expect, result)
    expect = [TRIGGER_2]
    result = [c.attr for c in chk.triggers.Search("WMIInstalledSoftware")]
    self.assertItemsEqual(expect, result)

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


class CheckResultsTest(test_lib.GRRBaseTest):
  """Test 'CheckResult' operations."""

  def testExtendAnomalies(self):
    anomaly1 = {"finding": ["Adware 2.1.1 is installed"],
                "explanation": "Found: Malicious software.",
                "type": 1}
    anomaly2 = {"finding": ["Java 6.0.240 is installed"],
                "explanation": "Found: Old Java installation.",
                "type": 1}
    result = checks.CheckResult(check_id="SW-CHECK",
                                anomaly=anomaly.Anomaly(**anomaly1))
    other = checks.CheckResult(check_id="SW-CHECK",
                               anomaly=anomaly.Anomaly(**anomaly2))
    result.ExtendAnomalies(other)
    expect = {"check_id": "SW-CHECK", "anomaly": [anomaly1, anomaly2]}
    self.assertDictEqual(expect, result.ToPrimitiveDict())


class HintDefinitionTests(test_lib.GRRBaseTest):
  """Test 'Hint' operations."""

  configs = {}

  def setUp(self, **kwargs):
    super(HintDefinitionTests, self).setUp(**kwargs)
    if not self.configs:
      config_file = os.path.join(CONFIGS, "sw.yaml")
      with open(config_file) as data:
        cfg = yaml.safe_load(data)
    chk = checks.Check(**cfg)
    self.lin_method, self.win_method, self.foo_method = list(chk.method)

  def testInheritHintConfig(self):
    lin_problem = "l337 software installed"
    lin_format = "{{ name }} {{ version }} is installed"
    # Methods should not have a hint template.
    self.assertEqual(lin_problem, self.lin_method.hint.problem)
    self.assertFalse(self.lin_method.hint.hinter.template)
    # Formatting should be present in probes, if defined.
    for probe in self.lin_method.probe:
      self.assertEqual(lin_problem, probe.hint.problem)
      self.assertEqual(lin_format, probe.hint.format)

    foo_problem = "Sudo not installed"
    # Methods should not have a hint template.
    self.assertEqual(foo_problem, self.foo_method.hint.problem)
    self.assertFalse(self.foo_method.hint.hinter.template)
    # Formatting should be missing in probes, if undefined.
    for probe in self.foo_method.probe:
      self.assertEqual(foo_problem, probe.hint.problem)
      self.assertFalse(probe.hint.format)

  def testOverlayHintConfig(self):
    generic_problem = "Malicious software."
    java_problem = "Old Java installation."
    generic_format = "{{ name }} {{ version }} is installed"
    # Methods should not have a hint template.
    self.assertEqual(generic_problem, self.win_method.hint.problem)
    self.assertFalse(self.win_method.hint.hinter.template)
    # Formatting should be present in probes.
    probe_1, probe_2 = list(self.win_method.probe)
    self.assertEqual(java_problem, probe_1.hint.problem)
    self.assertEqual(generic_format, probe_1.hint.format)
    self.assertEqual(generic_problem, probe_2.hint.problem)
    self.assertEqual(generic_format, probe_2.hint.format)


