#!/usr/bin/env python
"""Test for the flow state class."""



from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import test_base


class FlowStateTest(test_base.RDFValueTestCase):

  rdfvalue_class = rdf_flows.FlowState

  def GenerateSample(self, number=0):
    res = rdf_flows.FlowState()
    res.Register("number", number)
    return res

  def testComparisons(self):
    """Checks that object comparisons work."""
    sample1 = self.GenerateSample(1)

    self.assertTrue(sample1 == self.GenerateSample(1))
    self.assertFalse(sample1 == self.GenerateSample(2))
    self.assertTrue(sample1 != self.GenerateSample(2))

  def testFlowState(self):
    state = rdf_flows.FlowState()
    state.Register("teststate", 1)
    state.teststate = 100

    state.Register("context", utils.DataObject())
    state.context.testcontext = 50
    s = state.SerializeToString()

    new_state = rdf_flows.FlowState()
    new_state.ParseFromString(s)

    self.assertEqual(new_state.teststate, 100)
    self.assertEqual(new_state.context.testcontext, 50)

    # context and teststate
    self.assertEqual(len(new_state), 2)
    self.assertEqual(len(new_state.context), 1)

  def testBadPickle(self):
    """Test that we can recover some of the bad pickle."""
    state = rdf_flows.FlowState()
    # Store an instance of a RDFURN here.
    state.Register("urn", rdfvalue.RDFURN("aff4:/"))

    serialized = state.SerializeToString()

    # Substitute the class with something entirely different.
    with utils.Stubber(rdfvalue, "RDFURN", None):
      # We now should not be able to restore the state normally since we can not
      # find the RDFURN instance.
      result = rdf_flows.FlowState(serialized)

      # The pickle error should be available here.
      self.assertTrue(isinstance(result.errors, TypeError))

      # The bad field should be replaced with an UnknownObject instance.
      self.assertTrue(isinstance(result.urn, rdf_flows.UnknownObject))

      # Missing attribute is a different kind of error, but this is still
      # trapped.
      del rdfvalue.RDFURN

      result = rdf_flows.FlowState(serialized)
      self.assertTrue(isinstance(result.errors, AttributeError))
      self.assertTrue(isinstance(result.urn, rdf_flows.UnknownObject))


class SessionIDTest(test_base.RDFValueTestCase):
  """Test SessionID."""

  rdfvalue_class = rdfvalue.SessionID

  def GenerateSample(self, number=0):
    id_str = "%08X" % (number % 2**32)
    return rdfvalue.SessionID(flow_name=id_str)

  def testSessionIDValidation(self):
    rdfvalue.SessionID(rdfvalue.RDFURN("aff4:/flows/A:12345678"))
    rdfvalue.SessionID(rdfvalue.RDFURN("aff4:/flows/A:TransferStore"))
    rdfvalue.SessionID(rdfvalue.RDFURN("aff4:/flows/DEBUG-user1:12345678"))
    rdfvalue.SessionID(rdfvalue.RDFURN("aff4:/flows/DEBUG-user1:12345678:hunt"))

  def testQueueGetterReturnsCorrectValues(self):
    s = rdfvalue.SessionID("A:12345678")
    self.assertEqual(s.Queue(), "A")

    s = rdfvalue.SessionID("DEBUG-user1:12345678:hunt")
    self.assertEqual(s.Queue(), "DEBUG-user1")

  def testFlowNameGetterReturnsCorrectValues(self):
    s = rdfvalue.SessionID("A:12345678")
    self.assertEqual(s.FlowName(), "12345678")

    s = rdfvalue.SessionID("DEBUG-user1:12345678:hunt")
    self.assertEqual(s.FlowName(), "12345678:hunt")

  def testBadStructure(self):
    self.assertRaises(rdfvalue.InitializeError, rdfvalue.SessionID,
                      rdfvalue.RDFURN("aff4:/flows/A:123456:1:"))
    self.assertRaises(rdfvalue.InitializeError, rdfvalue.SessionID,
                      rdfvalue.RDFURN("aff4:/flows/A:123456::"))
    self.assertRaises(rdfvalue.InitializeError, rdfvalue.SessionID,
                      rdfvalue.RDFURN("aff4:/flows/A:123456:"))
    self.assertRaises(rdfvalue.InitializeError, rdfvalue.SessionID,
                      rdfvalue.RDFURN("aff4:/flows/A:"))
    self.assertRaises(rdfvalue.InitializeError, rdfvalue.SessionID,
                      rdfvalue.RDFURN("aff4:/flows/:"))

  def testBadQueue(self):
    self.assertRaises(rdfvalue.InitializeError, rdfvalue.SessionID,
                      rdfvalue.RDFURN("aff4:/flows/A%b:12345678"))

  def testBadFlowID(self):
    self.assertRaises(rdfvalue.InitializeError, rdfvalue.SessionID,
                      rdfvalue.RDFURN("aff4:/flows/A:1234567G%sdf"))
