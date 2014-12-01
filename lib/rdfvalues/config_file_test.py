#!/usr/bin/env python
"""Tests for grr.lib.rdfvalues.config_files."""
from grr.lib import rdfvalue
from grr.lib.rdfvalues import config_file
from grr.lib.rdfvalues import test_base


class ConfigFileTest(test_base.RDFValueTestCase):
  """Test ConfigFile operations."""

  rdfvalue_class = rdfvalue.Config

  def GenerateSample(self, number=0):
    return rdfvalue.Config({"number": number})

  def testInitialize(self):
    arnie = {"target": "Sarah Connor", "mission": "Protect"}
    t800 = {"target": "Sarah Connor", "mission": "Terminate"}
    terminator = config_file.Config(arnie)
    self.assertIsInstance(terminator.settings, rdfvalue.Dict)
    self.assertEquals(terminator.settings.GetItem("target"), "Sarah Connor")
    self.assertEquals(terminator.settings.GetItem("mission"), "Protect")
    terminator = config_file.Config(**t800)
    self.assertEquals(terminator.settings.GetItem("target"), "Sarah Connor")
    self.assertEquals(terminator.settings.GetItem("mission"), "Terminate")
    # We don't want a conflicted Terminator
    self.assertRaises(ValueError, config_file.Config, t800, mission="Protect")

  def testConfigSettingsAreAttr(self):
    t800 = {"target": "Sarah Connor", "mission": "Terminate"}
    terminator = config_file.Config(t800)
    self.assertEquals(terminator.target, "Sarah Connor")
    self.assertEquals(terminator.mission, "Terminate")
