#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for triggers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import flags
from grr_response_server.check_lib import triggers
from grr.test_lib import test_lib

target_1 = triggers.Target({})
target_2 = triggers.Target(
    os=["TermOS"], cpe=["cpe:/o:cyberdyne:termos"], label=["t800", "t1000"])
bad_ai = ("BadAI", None, None, None)
good_ai = ("GoodAI", None, None, None)
termos = ("BadAI", "TermOS", "cpe:/o:cyberdyne:termos")
t800 = ("BadAI", "TermOS", "cpe:/o:cyberdyne:termos", "t800")
t1000 = ("BadAI", "TermOS", "cpe:/o:cyberdyne:termos", "t1000")


class ConditionTest(test_lib.GRRBaseTest):
  """Test trigger selection methods."""

  def testConditionRequiresArtifact(self):
    self.assertRaises(triggers.DefinitionError, triggers.Condition, None)
    self.assertRaises(triggers.DefinitionError, triggers.Condition, None,
                      "TermOS", "cpe:/o:cyberdyne:termos", "t800")

  def testConditionIsHashable(self):
    c1 = triggers.Condition(*termos)
    c2 = triggers.Condition(*t800)
    results = set([c1, c2, c1, c1, c1, c2])
    self.assertLen(results, 2)
    self.assertCountEqual(set([c1, c2]), results)

  def testConditionMatch(self):
    # More general terms include more specific results.
    cond = triggers.Condition(*termos)
    self.assertTrue(cond.Match(*termos))
    self.assertTrue(cond.Match(*t800))
    self.assertTrue(cond.Match(*t1000))
    # More specific terms omit non-matching and more general ones.
    cond = triggers.Condition(*t800)
    self.assertTrue(cond.Match(*t800))
    self.assertFalse(cond.Match(*t1000))
    self.assertFalse(cond.Match(*termos))


class TriggersTest(test_lib.GRRBaseTest):
  """Test trigger collection methods."""

  def testTriggersRequireArtifact(self):
    t = triggers.Triggers()
    self.assertRaises(triggers.DefinitionError, t.Add)
    self.assertRaises(triggers.DefinitionError, t.Add, None, target_1)

  def testTriggersMatchConditions(self):
    t = triggers.Triggers()
    t.Add("GoodAI", target_1)
    # Get no results if host data doesn't match. TermOS is too general.
    self.assertFalse(t.Match(*termos))
    # Get results if host data is as/more specific than the trigger.
    t.Add("BadAI", target_2)
    self.assertTrue(t.Match(*t800))
    # Adding a BadAI artifact target means any TermOS system should fire.
    t.Add("BadAI", target_1)
    self.assertTrue(t.Match(*termos))

  def testTriggersSearchConditions(self):
    t = triggers.Triggers()
    t.Add("GoodAI", target_1)
    t.Add("BadAI", target_2)
    # Searches return no results if query data doesn't match.
    self.assertEqual([],
                     t.Search(
                         artifact="GoodAI", os_name="TermOS", label="t1000"))
    # Searches return results if query data matches.
    self.assertEqual([good_ai], [c.attr for c in t.Search(artifact="GoodAI")])
    self.assertCountEqual([t800, t1000],
                          [c.attr for c in t.Search(artifact="BadAI")])

  def testTriggerRegistry(self):
    t = triggers.Triggers()
    callback_1 = lambda: 1
    callback_2 = lambda: 2
    callback_3 = lambda: 3
    t.Add("GoodAI", target_1, callback_1)
    t.Add("BadAI", target_2, callback_2)
    self.assertCountEqual([], t.Calls([bad_ai]))
    self.assertCountEqual([callback_1], t.Calls([good_ai]))
    self.assertCountEqual([callback_2], t.Calls([t800]))
    self.assertCountEqual([callback_2], t.Calls([t1000]))
    meta_t = triggers.Triggers()
    meta_t.Update(t, callback_3)
    self.assertCountEqual([], meta_t.Calls([bad_ai]))
    self.assertCountEqual([callback_3], meta_t.Calls([good_ai]))
    self.assertCountEqual([callback_3], meta_t.Calls([t800]))
    self.assertCountEqual([callback_3], meta_t.Calls([t1000]))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
