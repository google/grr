#!/usr/bin/env python
"""Test for the flow state class."""



from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import flows
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

    state.Register("context", flows.DataObject())
    state.context.testcontext = 50
    s = state.SerializeToString()

    new_state = rdfvalue.FlowState()
    new_state.ParseFromString(s)

    self.assertEqual(new_state.teststate, 100)
    self.assertEqual(new_state.context.testcontext, 50)

    # context and teststate
    self.assertEqual(len(new_state), 2)
    self.assertEqual(len(new_state.context), 1)

  def testBadPickle(self):
    """Test that we can recover some of the bad pickle."""
    state = rdfvalue.FlowState()
    # Store an instance of a RDFURN here.
    state.Register("urn", rdfvalue.RDFURN("aff4:/"))

    serialized = state.SerializeToString()

    # Substitute the class with something entirely different.
    with utils.Stubber(rdfvalue, "RDFURN", None):
      # We now should not be able to restore the state normally since we can not
      # find the RDFURN instance.
      result = rdfvalue.FlowState(serialized)

      # The pickle error should be available here.
      self.assertTrue(isinstance(result.errors, TypeError))

      # The bad field should be replaced with an UnknownObject instance.
      self.assertTrue(isinstance(result.urn, flows.UnknownObject))

      # Missing attribute is a different kind of error, but this is still
      # trapped.
      del rdfvalue.RDFURN

      result = rdfvalue.FlowState(serialized)
      self.assertTrue(isinstance(result.errors, AttributeError))
      self.assertTrue(isinstance(result.urn, flows.UnknownObject))
