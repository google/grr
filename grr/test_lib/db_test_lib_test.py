#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from absl import app

from grr_response_core.lib.util import compatibility
from grr_response_server import data_store
from grr.test_lib import db_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class DualDBTestDecoratorTest(test_lib.GRRBaseTest):
  """Test DualDBTest decorator."""

  def _IsDBTest(self):
    name = compatibility.GetName(self.__class__)
    return name.endswith("_RelationalDBEnabled")

  def testRelationalDBEnabled(self):
    result = data_store.RelationalDBEnabled()
    expected = self._IsDBTest()
    self.assertEqual(
        result, expected, "RelationalDBEnabled() is %s for %s" %
        (result, compatibility.GetName(self.__class__)))


if __name__ == "__main__":
  app.run(test_lib.main)
