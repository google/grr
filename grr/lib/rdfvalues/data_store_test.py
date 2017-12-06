#!/usr/bin/env python
"""Remote datastore-related rdfvalues tests."""


from grr.lib import flags
from grr.lib.rdfvalues import data_store

from grr.lib.rdfvalues import test_base
from grr.test_lib import test_lib


class ResultSetTest(test_base.RDFValueTestMixin, test_lib.GRRBaseTest):
  """Tests for ResultSet."""

  rdfvalue_class = data_store.ResultSet

  def GenerateSample(self, number=0):
    return data_store.ResultSet(payload=[number])

  def testWorksCorrectlyWithMalformedUnicodeStrings(self):
    result_set = data_store.ResultSet()

    # This triggets the setter
    result_set.payload = [u"\udc7c"]
    # This triggets the getter
    self.assertEqual(result_set.payload, [u"\udc7c"])

  def testWorksCorrectlyWithControlCharactersAndQuotes(self):
    result_set = data_store.ResultSet()

    # This triggets the setter
    result_set.payload = [u"\n\t\"'"]
    # This triggets the getter
    self.assertEqual(result_set.payload, [u"\n\t\"'"])


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
