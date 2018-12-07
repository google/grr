#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Contains tests for api_call_handler_utils."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from builtins import range  # pylint: disable=redefined-builtin

from grr_response_core.lib import flags

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import data_store
from grr_response_server import sequential_collection
from grr_response_server.gui import api_call_handler_utils
from grr.test_lib import test_lib


class FilterCollectionTest(test_lib.GRRBaseTest):
  """Test for FilterCollection."""

  def setUp(self):
    super(FilterCollectionTest, self).setUp()

    self.fd = sequential_collection.GeneralIndexedCollection(
        rdfvalue.RDFURN("aff4:/tmp/foo/bar"))
    with data_store.DB.GetMutationPool() as pool:
      for i in range(10):
        self.fd.Add(
            rdf_paths.PathSpec(path="/var/os/tmp-%d" % i, pathtype="OS"),
            mutation_pool=pool)

  def testFiltersByOffsetAndCount(self):
    data = api_call_handler_utils.FilterCollection(self.fd, 2, 5, None)
    self.assertLen(data, 5)
    self.assertEqual(data[0].path, "/var/os/tmp-2")
    self.assertEqual(data[-1].path, "/var/os/tmp-6")

  def testIngoresTooBigCount(self):
    data = api_call_handler_utils.FilterCollection(self.fd, 0, 50, None)
    self.assertLen(data, 10)
    self.assertEqual(data[0].path, "/var/os/tmp-0")
    self.assertEqual(data[-1].path, "/var/os/tmp-9")

  def testRaisesOnNegativeOffset(self):
    with self.assertRaises(ValueError):
      api_call_handler_utils.FilterCollection(self.fd, -10, 0, None)

  def testRaisesOnNegativeCount(self):
    with self.assertRaises(ValueError):
      api_call_handler_utils.FilterCollection(self.fd, 0, -10, None)

  def testFiltersByFilterString(self):
    data = api_call_handler_utils.FilterCollection(self.fd, 0, 0, "tmp-8")
    self.assertLen(data, 1)
    self.assertEqual(data[0].path, "/var/os/tmp-8")


class FilterListTest(test_lib.GRRBaseTest):
  """Test for FilterList."""

  def setUp(self):
    super(FilterListTest, self).setUp()

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
  flags.StartMain(main)
