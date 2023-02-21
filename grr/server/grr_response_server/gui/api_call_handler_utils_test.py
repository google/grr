#!/usr/bin/env python
"""Contains tests for api_call_handler_utils."""

from absl import app

from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server.gui import api_call_handler_utils
from grr.test_lib import test_lib


class FilterListTest(test_lib.GRRBaseTest):
  """Test for FilterList."""

  def setUp(self):
    super().setUp()

    self.l = []
    for i in range(10):
      self.l.append(
          rdf_paths.PathSpec(path="/var/os/tmp-%d" % i, pathtype="OS"))

  def testFiltersByOffsetAndCount(self):
    data = api_call_handler_utils.FilterList(self.l, 2, 5, None)
    self.assertLen(data, 5)
    self.assertEqual(data[0].path, "/var/os/tmp-2")
    self.assertEqual(data[-1].path, "/var/os/tmp-6")

  def testIngoresTooBigCount(self):
    data = api_call_handler_utils.FilterList(self.l, 0, 50, None)
    self.assertLen(data, 10)
    self.assertEqual(data[0].path, "/var/os/tmp-0")
    self.assertEqual(data[-1].path, "/var/os/tmp-9")

  def testRaisesOnNegativeOffset(self):
    with self.assertRaises(ValueError):
      api_call_handler_utils.FilterList(self.l, -10, 0, None)

  def testRaisesOnNegativeCount(self):
    with self.assertRaises(ValueError):
      api_call_handler_utils.FilterList(self.l, 0, -10, None)

  def testFiltersByFilterString(self):
    data = api_call_handler_utils.FilterList(self.l, 0, 0, "tmp-8")
    self.assertLen(data, 1)
    self.assertEqual(data[0].path, "/var/os/tmp-8")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
