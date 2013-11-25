#!/usr/bin/env python
"""Remote datastore-related rdfvalues tests."""



from grr.lib import rdfvalue
from grr.lib.rdfvalues import test_base


class ResultSetTest(test_base.RDFValueTestCase):
  """Tests for ResultSet."""

  rdfvalue_class = rdfvalue.ResultSet

  def GenerateSample(self, number=0):
    return rdfvalue.ResultSet(payload=[number])

  def testWorksCorrectlyWithMalformedUnicodeStrings(self):
    result_set = rdfvalue.ResultSet()

    # This triggets the setter
    result_set.payload = [u"\udc7c"]
    # This triggets the getter
    self.assertEqual(result_set.payload, [u"\udc7c"])

  def testWorksCorrectlyWithControlCharactersAndQuotes(self):
    result_set = rdfvalue.ResultSet()

    # This triggets the setter
    result_set.payload = [u"\n\t\"'"]
    # This triggets the getter
    self.assertEqual(result_set.payload, [u"\n\t\"'"])
