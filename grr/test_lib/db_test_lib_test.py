#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import unicode_literals


from grr_response_core.lib import flags
from grr_response_server import data_store
from grr.test_lib import db_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class DualDBTestDecoratorTest(test_lib.GRRBaseTest):
  """Test DualDBTest decorator."""

  def _IsDBTest(self):
    return self.__class__.__name__.endswith("_RelationalDBEnabled")

  def _Description(self):
    if self._IsDBTest():
      return "RelationalDB enabled"
    else:
      return "RelationalDB disabled"

  def testRelationalDBReadEnabled(self):
    result = data_store.RelationalDBReadEnabled()
    self.assertEqual(
        result, self._IsDBTest(), "RelationalDBReadEnabled() is %s for %s" %
        (result, self._Description()))

  def testRelationalDBFlowsAlwaysDisabled(self):
    result = data_store.RelationalDBFlowsEnabled()
    self.assertFalse(
        result, "RelationalDBFlowsEnabled() is %s for %s" %
        (result, self._Description()))


@db_test_lib.DualFlowTest
class DualFlowTestDecoratorTest(test_lib.GRRBaseTest):
  """Test DualDBTest decorator."""

  def _IsDBTest(self):
    return self.__class__.__name__.endswith("_RelationalFlowsEnabled")

  def _Description(self):
    if self._IsDBTest():
      return "RelationalFlows enabled"
    else:
      return "RelationalFlows disabled"

  def testRelationalDBReadEnabled(self):
    result = data_store.RelationalDBReadEnabled()
    self.assertEqual(
        result, self._IsDBTest(), "RelationalDBReadEnabled() is %s for %s" %
        (result, self._Description()))

  def testRelationalDBFlowsEnabled(self):
    result = data_store.RelationalDBFlowsEnabled()
    self.assertEqual(
        result, self._IsDBTest(), "RelationalDBFlowsEnabled() is %s for %s" %
        (result, self._Description()))


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
