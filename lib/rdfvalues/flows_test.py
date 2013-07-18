#!/usr/bin/env python
"""Test for the flow state class."""



from grr.lib import rdfvalue
from grr.lib.rdfvalues import test_base


class FlowStateTest(test_base.RDFValueTestCase):

  rdfvalue_class = rdfvalue.FlowState

  def GenerateSample(self, number=0):
    res = rdfvalue.FlowState()
    res.Register("number", number)
    return res

  def testComparisons(self):
    """Checks that object comparisons work."""
    sample1 = self.GenerateSample(1)

    self.assertTrue(sample1 == self.GenerateSample(1))
    self.assertFalse(sample1 == self.GenerateSample(2))
    self.assertTrue(sample1 != self.GenerateSample(2))

  def testFlowState(self):
    state = rdfvalue.FlowState()
    state.Register("teststate", 1)
    state.teststate = 100
    state.context.testcontext = 50
    s = state.SerializeToString()

    new_state = rdfvalue.FlowState()
    new_state.ParseFromString(s)

    self.assertEqual(new_state.teststate, 100)
    self.assertEqual(new_state.context.testcontext, 50)

    # context and teststate
    self.assertEqual(len(new_state), 2)
    self.assertEqual(len(new_state.context), 1)
