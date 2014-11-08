#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for checks."""
from grr.lib import flags
from grr.lib import test_lib
from grr.lib.checks import hints


# http://en.wikipedia.org/wiki/Paranoia_(role-playing_game)


class Troubleshooter(object):
  """Simple stub of RDF data."""

  def __init__(self, allegiance):
    self.commie = allegiance.get("commie")
    self.mutant = allegiance.get("mutant")

  def AsDict(self):
    return {"commie": self.commie, "mutant": self.mutant}

  def __str__(self):
    return "commie:%s mutant:%s" % (self.commie, self.mutant)


class HintsTests(test_lib.GRRBaseTest):
  """Test hint operations."""

  def setUp(self):
    super(HintsTests, self).setUp()
    # Fully populated hint.
    self.full = {"problem": "Commies and mutants are enemies of The Computer.",
                 "fix": "Assign Troubleshooters.",
                 "format": "{{ mutant }}, {{ commie }}",
                 "summary": "Traitor found."}
    # Partial hint
    self.partial = {"problem": "Troubleshooter clone is a Traitor.",
                    "fix": "Terminate clone.",
                    "format": "",
                    "summary": ""}
    # Partial overlaid with full.
    self.overlay = {"problem": "Troubleshooter clone is a Traitor.",
                    "fix": "Terminate clone.",
                    "format": "{{ mutant }}, {{ commie }}",
                    "summary": "Traitor found."}
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
    roy_g_biv = Troubleshooter({"mutant": "Machine Empathy",
                                "commie": "Computer Phreaks"})
    rik_r_oll = Troubleshooter({"mutant": "Ventriloquist",
                                "commie": "Romantics"})
    # This Hinter doesn't modify the default string output of an rdfvalue.
    unformatted = hints.Hinter()
    self.assertEqual(unformatted.Render(rik_r_oll),
                     "commie:Romantics mutant:Ventriloquist")
    self.assertEqual(unformatted.Render(roy_g_biv),
                     "commie:Computer Phreaks mutant:Machine Empathy")
    # This Hinter uses a django template to specify presentation.
    formatted = hints.Hinter(template="{{ mutant }}, {{ commie }}")
    self.assertEqual(formatted.Render(rik_r_oll),
                     "Ventriloquist, Romantics")
    self.assertEqual(formatted.Render(roy_g_biv),
                     "Machine Empathy, Computer Phreaks")


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
