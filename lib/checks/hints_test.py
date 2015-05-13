#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for checks."""
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.checks import hints


class HintsTests(test_lib.GRRBaseTest):
  """Test hint operations."""

  def testCheckOverlay(self):
    """Overlay(hint1, hint2) should populate hint2 with the values of hint1."""
    # Fully populated hint.
    full = {"problem": "Terminator needs trousers.",
            "fix": "Give me your clothes.",
            "format": "{mission}, {target}",
            "summary": "I'll be back."}
    # Partial hint
    partial = {"problem": "Terminator needs to go shopping.",
               "fix": "Phased plasma rifle in the 40-watt range.",
               "format": "",
               "summary": ""}
    # Partial overlaid with full.
    overlay = {"problem": "Terminator needs to go shopping.",
               "fix": "Phased plasma rifle in the 40-watt range.",
               "format": "{mission}, {target}",
               "summary": "I'll be back."}
    # Empty hint.
    empty = {"problem": "", "fix": "", "format": "", "summary": ""}

    # Empty hint should not clobber populated hint.
    starts_full = full.copy()
    starts_empty = empty.copy()
    hints.Overlay(starts_full, starts_empty)
    self.assertDictEqual(full, starts_full)
    self.assertDictEqual(empty, starts_empty)
    # Populate empty hint from partially populated hint.
    starts_partial = partial.copy()
    starts_empty = empty.copy()
    hints.Overlay(starts_empty, starts_partial)
    self.assertDictEqual(partial, starts_partial)
    self.assertDictEqual(partial, starts_empty)
    # Overlay the full and partial hints to get the hybrid.
    starts_full = full.copy()
    starts_partial = partial.copy()
    hints.Overlay(starts_partial, starts_full)
    self.assertDictEqual(full, starts_full)
    self.assertDictEqual(overlay, starts_partial)

  def testRdfFormatter(self):
    """Hints format RDF values with arbitrary values and attributes."""
    # Create a complex RDF value
    rdf = rdfvalue.ClientSummary()
    rdf.system_info.system = "Linux"
    rdf.system_info.node = "coreai.skynet.com"
    # Users (repeated)
    rdf.users = [rdfvalue.User(username=u) for u in ("root", "jconnor")]
    # Interface (nested, repeated)
    addresses = [rdfvalue.NetworkAddress(human_readable=a) for a in (
        "1.1.1.1", "2.2.2.2", "3.3.3.3")]
    eth0 = rdfvalue.Interface(ifname="eth0", addresses=addresses[:2])
    ppp0 = rdfvalue.Interface(ifname="ppp0", addresses=addresses[2])
    rdf.interfaces = [eth0, ppp0]

    template = ("{system_info.system} {users.username} {interfaces.ifname} "
                "{interfaces.addresses.human_readable}")
    hinter = hints.Hinter(template=template)
    expected = "Linux root,jconnor eth0,ppp0 1.1.1.1,2.2.2.2,3.3.3.3"
    result = hinter.Render(rdf)
    self.assertEqual(expected, result)

  def testRdfFormatterHandlesKeyValuePair(self):
    """rdfvalue.KeyValue items need special handling to expand k and v."""
    key = rdfvalue.DataBlob().SetValue("skynet")
    value = rdfvalue.DataBlob().SetValue([1997])
    rdf = rdfvalue.KeyValue(k=key, v=value)
    template = "{k}: {v}"
    hinter = hints.Hinter(template=template)
    expected = "skynet: 1997"
    result = hinter.Render(rdf)
    self.assertEqual(expected, result)

  def testRdfFormatterFanOut(self):
    rdf = rdfvalue.Dict()
    user1 = rdfvalue.KnowledgeBaseUser(username="drexler")
    user2 = rdfvalue.KnowledgeBaseUser(username="joy")
    rdf["cataclysm"] = "GreyGoo"
    rdf["thinkers"] = [user1, user2]
    rdf["reference"] = {"ecophage": ["bots", ["nanobots", ["picobots"]]],
                        "doomsday": {"books": ["cats cradle", "prey"]}}
    template = ("{cataclysm}; {thinkers.username}; {reference.ecophage}; "
                "{reference.doomsday}")
    hinter = hints.Hinter(template=template)
    expected = ("GreyGoo; drexler,joy; bots,nanobots,picobots; "
                "books:cats cradle,prey")
    result = hinter.Render(rdf)
    self.assertEqual(expected, result)


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
