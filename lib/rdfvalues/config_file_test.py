#!/usr/bin/env python
"""Tests for grr.lib.rdfvalues.config_files."""
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.rdfvalues import config_file


class ConfigFileTest(test_lib.GRRBaseTest):
  """Test ConfigFile operations."""

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




