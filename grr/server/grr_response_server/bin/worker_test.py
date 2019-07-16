#!/usr/bin/env python
"""Tests for the worker."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import threading

from absl import app
import mock

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_stats as rdf_client_stats
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_server import data_store
from grr_response_server import foreman
from grr_response_server import worker_lib
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class GrrWorkerTest(flow_test_lib.FlowTestsBaseclass):
  """Tests the GRR Worker."""

  def _TestWorker(self):
    worker = worker_lib.GRRWorker()
    self.addCleanup(worker.Shutdown)
    return worker

  def testMessageHandlers(self):
    worker_obj = self._TestWorker()

    client_id = self.SetupClient(100)

    done = threading.Event()

    def handle(l):
      worker_obj._ProcessMessageHandlerRequests(l)
      done.set()

    data_store.REL_DB.RegisterMessageHandler(
        handle, worker_obj.message_handler_lease_time, limit=1000)

    data_store.REL_DB.WriteMessageHandlerRequests([
        rdf_objects.MessageHandlerRequest(
            client_id=client_id,
            handler_name="StatsHandler",
            request_id=12345,
            request=rdf_client_stats.ClientStats(RSS_size=1234))
    ])

    self.assertTrue(done.wait(10))

    results = data_store.REL_DB.ReadClientStats(
        client_id=client_id,
        min_timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0),
        max_timestamp=rdfvalue.RDFDatetime.Now())
    self.assertLen(results, 1)
    stats = results[0]

    self.assertEqual(stats.RSS_size, 1234)

    data_store.REL_DB.UnregisterMessageHandler(timeout=60)

    # Make sure there are no leftover requests.
    self.assertEqual(data_store.REL_DB.ReadMessageHandlerRequests(), [])

  def testCPULimitForFlows(self):
    """This tests that the client actions are limited properly."""
    client_id = self.SetupClient(0)

    client_mock = action_mocks.CPULimitClientMock(
        user_cpu_usage=[10], system_cpu_usage=[10], network_usage=[1000])

    flow_test_lib.TestFlowHelper(
        flow_test_lib.CPULimitFlow.__name__,
        client_mock,
        token=self.token,
        client_id=client_id,
        cpu_limit=1000,
        network_bytes_limit=10000)

    self.assertEqual(client_mock.storage["cpulimit"], [1000, 980, 960])
    self.assertEqual(client_mock.storage["networklimit"], [10000, 9000, 8000])

  def _Process(self, client_mocks, worker_obj):
    while True:
      client_msgs_processed = 0
      for client_mock in client_mocks:
        client_msgs_processed += client_mock.Next()
      with test_lib.SuppressLogs():
        worker_msgs_processed = worker_obj.RunOnce()
        worker_obj.thread_pool.Join()
      if not client_msgs_processed and not worker_msgs_processed:
        break

  def testForemanMessageHandler(self):
    with mock.patch.object(foreman.Foreman, "AssignTasksToClient") as instr:
      worker_obj = self._TestWorker()

      # Send a message to the Foreman.
      client_id = "C.1100110011001100"

      data_store.REL_DB.WriteMessageHandlerRequests([
          rdf_objects.MessageHandlerRequest(
              client_id=client_id,
              handler_name="ForemanHandler",
              request_id=12345,
              request=rdf_protodict.DataBlob())
      ])

      done = threading.Event()

      def handle(l):
        worker_obj._ProcessMessageHandlerRequests(l)
        done.set()

      data_store.REL_DB.RegisterMessageHandler(
          handle, worker_obj.message_handler_lease_time, limit=1000)
      try:
        self.assertTrue(done.wait(10))

        # Make sure there are no leftover requests.
        self.assertEqual(data_store.REL_DB.ReadMessageHandlerRequests(), [])

        instr.assert_called_once_with(client_id)
      finally:
        data_store.REL_DB.UnregisterMessageHandler(timeout=60)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
