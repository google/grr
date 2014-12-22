#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for checks."""
from grr.lib import flags
from grr.lib import test_lib
from grr.lib.checks import hints


class Terminator(object):
  """Simple stub of RDF data."""

  def __init__(self, tasking):
    self.target = tasking.get("target")
    self.mission = tasking.get("mission")

  def AsDict(self):
    return {"target": self.target, "mission": self.mission}

  def __str__(self):
    return "target:%s mission:%s" % (self.target, self.mission)


class HintsTests(test_lib.GRRBaseTest):
  """Test hint operations."""

  def setUp(self):
    super(HintsTests, self).setUp()
    # Fully populated hint.
    self.full = {"problem": "Terminator needs trousers.",
                 "fix": "Give me your clothes.",
                 "format": "{mission}, {target}",
                 "summary": "I'll be back."}
    # Partial hint
    self.partial = {"problem": "Terminator needs to go shopping.",
                    "fix": "Phased plasma rifle in the 40-watt range.",
                    "format": "",
                    "summary": ""}
    # Partial overlaid with full.
    self.overlay = {"problem": "Terminator needs to go shopping.",
                    "fix": "Phased plasma rifle in the 40-watt range.",
                    "format": "{mission}, {target}",
                    "summary": "I'll be back."}
    # Empty hint.
    self.empty = {"problem": "", "fix": "", "format": "", "summary": ""}

  def testCheckOverlay(self):
    """Overlay(hint1, hint2) should populate hint2 with the values of hint1."""
    # Empty hint should not clobber populated hint.
    starts_full = self.full.copy()
    starts_empty = self.empty.copy()
    hints.Overlay(starts_full, starts_empty)
    self.assertDictEqual(self.full, starts_full)
    self.assertDictEqual(self.empty, starts_empty)
    # Populate empty hint from partially populated hint.
    starts_partial = self.partial.copy()
    starts_empty = self.empty.copy()
    hints.Overlay(starts_empty, starts_partial)
    self.assertDictEqual(self.partial, starts_partial)
    self.assertDictEqual(self.partial, starts_empty)
    # Overlay the full and partial hints to get the hybrid.
    starts_full = self.full.copy()
    starts_partial = self.partial.copy()
    hints.Overlay(starts_partial, starts_full)
    self.assertDictEqual(self.full, starts_full)
    self.assertDictEqual(self.overlay, starts_partial)

  def testProcessRdfData(self):
    arnie = Terminator({"mission": "Protect", "target": "John Connor"})
    t800 = Terminator({"mission": "Terminate", "target": "Sarah Connor"})
    # This Hinter doesn't modify the default string output of an rdfvalue.
    unformatted = hints.Hinter()
    self.assertEqual(unformatted.Render(t800),
                     "target:Sarah Connor mission:Terminate")
    self.assertEqual(unformatted.Render(arnie),
                     "target:John Connor mission:Protect")
    # This Hinter uses python format to specify presentation.
    formatted = hints.Hinter(template="{mission}, {target}")
    self.assertEqual(formatted.Render(t800), "Terminate, Sarah Connor")
    self.assertEqual(formatted.Render(arnie), "Protect, John Connor")


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
