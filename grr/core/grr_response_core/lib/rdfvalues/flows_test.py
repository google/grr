#!/usr/bin/env python
"""Test for the flow state class."""


from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import test_base as rdf_test_base
from grr.test_lib import test_lib


class SessionIDTest(rdf_test_base.RDFValueTestMixin, test_lib.GRRBaseTest):
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


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
