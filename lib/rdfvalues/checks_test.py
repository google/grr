#!/usr/bin/env python
"""Tests for grr.lib.rdfvalues.checks."""
import os
import yaml

from grr.lib import config_lib
from grr.lib import test_lib
from grr.lib.checks import checks as checks_lib
from grr.lib.checks import filters
from grr.lib.rdfvalues import checks


CONFIGS = os.path.join(config_lib.CONFIG["Test.data_dir"], "checks")
TRIGGER_1 = ("SoftwarePackage", "Linux", None, None)
TRIGGER_2 = ("WMIInstalledSoftware", "Windows", None, None)
TRIGGER_3 = ("SoftwarePackage", None, None, "foo")


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

  def testHintGeneration(self):
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

  def testParse(self):
    pass

  def testValidate(self):
    pass

