#!/usr/bin/env python
# Lint as: python3
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app
from absl.testing import absltest

from grr_response_server.databases import db_flows_test
from grr_response_server.databases import mysql_test
from grr.test_lib import test_lib


class MysqlFlowTest(db_flows_test.DatabaseTestFlowMixin,
                    mysql_test.MysqlTestBase, absltest.TestCase):

  def testListScheduledFlowsInitiallyEmpty(self):
    pass  # TODO: Implement scheduling of flows pre-approval.

  def testWriteScheduledFlow(self):
    pass  # TODO: Implement scheduling of flows pre-approval.

  def testListScheduledFlowsFiltersCorrectly(self):
    pass  # TODO: Implement scheduling of flows pre-approval.

  def testWriteScheduledFlowRaisesForUnknownClient(self):
    pass  # TODO: Implement scheduling of flows pre-approval.

  def testWriteScheduledFlowRaisesForUnknownUser(self):
    pass  # TODO: Implement scheduling of flows pre-approval.

  def testDeleteScheduledFlowRemovesScheduledFlow(self):
    pass  # TODO: Implement scheduling of flows pre-approval.

  def testDeleteScheduledFlowRaisesForUnknownScheduledFlow(self):
    pass  # TODO: Implement scheduling of flows pre-approval.

  def testDeleteUserDeletesScheduledFlows(self):
    pass  # TODO: Implement scheduling of flows pre-approval.


if __name__ == "__main__":
  app.run(test_lib.main)
