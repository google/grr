#!/usr/bin/env python
"""Tests for the worker."""


import time

# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flags
from grr.lib import flow
from grr.lib import queue_manager
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import worker


# A global collector for test results
RESULTS = []


class WorkerSendingTestFlow(flow.GRRFlow):
  """Tests that sent messages are correctly collected."""

  @flow.StateHandler(next_state="Incoming")
  def Start(self):
    for i in range(10):
      self.CallClient("Test",
                      rdfvalue.DataBlob(string="test%s" % i),
                      data=str(i),
                      next_state="Incoming")

  @flow.StateHandler(auth_required=False)
  def Incoming(self, responses):
    # Add a delay here to catch thread races.
    time.sleep(0.2)
    # We push the result into a global array so we can examine it
    # better.
    for response in responses:
      RESULTS.append(response.string)


class WorkerSendingTestFlow2(WorkerSendingTestFlow):
  """Only send a single request."""

  @flow.StateHandler(next_state="Incoming")
  def Start(self):
    i = 1
    self.CallClient("Test",
                    rdfvalue.DataBlob(string="test%s" % i),
                    data=str(i),
                    next_state="Incoming")


class WorkerSendingWKTestFlow(flow.WellKnownFlow):

  well_known_session_id = rdfvalue.SessionID(
      "aff4:/flows/WorkerSendingWKTestFlow")

  def ProcessMessage(self, message):
    RESULTS.append(message)


class GrrWorkerTest(test_lib.FlowTestsBaseclass):
  """Tests the GRR Worker."""

  def SendResponse(self, session_id, data, client_id=None, well_known=False):
    if not isinstance(data, rdfvalue.RDFValue):
      data = rdfvalue.DataBlob(string=data)
    if well_known:
      request_id, response_id = 0, 12345
    else:
      request_id, response_id = 1, 1
    with queue_manager.QueueManager(token=self.token) as flow_manager:
      flow_manager.QueueResponse(session_id, rdfvalue.GrrMessage(
          source=client_id,
          session_id=session_id,
          payload=data,
          request_id=request_id,
          response_id=response_id))
      if not well_known:
        # For normal flows we have to send a status as well.
        flow_manager.QueueResponse(session_id, rdfvalue.GrrMessage(
            source=client_id,
            session_id=session_id,
            payload=rdfvalue.GrrStatus(
                status=rdfvalue.GrrStatus.ReturnedStatus.OK),
            request_id=request_id, response_id=response_id+1,
            type=rdfvalue.GrrMessage.Type.STATUS))

    # Signal on the worker queue that this flow is ready.
    data_store.DB.Set(worker.DEFAULT_WORKER_QUEUE,
                      "task:%s" % session_id, "X", token=self.token)

  def testProcessMessages(self):
    """Test processing of several inbound messages."""
    worker_obj = worker.GRRWorker(worker.DEFAULT_WORKER_QUEUE,
                                  token=self.token)

    # Create a couple of flows
    flow_obj = self.FlowSetup("WorkerSendingTestFlow")
    session_id_1 = flow_obj.session_id
    flow_obj.Close()

    flow_obj = self.FlowSetup("WorkerSendingTestFlow2")
    session_id_2 = flow_obj.session_id
    flow_obj.Close()

    manager = queue_manager.QueueManager(token=self.token)
    # Check that client queue has messages
    tasks_on_client_queue = manager.Query(self.client_id.Queue(), 100)

    # should have 10 requests from WorkerSendingTestFlow and 1 from
    # SendingTestFlow2
    self.assertEqual(len(tasks_on_client_queue), 11)

    # Send each of the flows a repeated message
    self.SendResponse(session_id_1, "Hello1")
    self.SendResponse(session_id_2, "Hello2")
    self.SendResponse(session_id_1, "Hello1")
    self.SendResponse(session_id_2, "Hello2")

    # Clear the results global
    del RESULTS[:]

    # Process all messages
    worker_obj.RunOnce()

    worker_obj.thread_pool.Join()

    # Ensure both requests ran exactly once
    RESULTS.sort()
    self.assertEqual(2, len(RESULTS))
    self.assertEqual("Hello1", RESULTS[0])
    self.assertEqual("Hello2", RESULTS[1])

    # Check that client queue is cleared - should have 2 less messages (since
    # two were completed).
    tasks_on_client_queue = manager.Query(self.client_id.Queue(), 100)

    self.assertEqual(len(tasks_on_client_queue), 9)

    # Ensure that processed requests are removed from state subject
    self.assertEqual((None, 0), data_store.DB.Resolve(
        session_id_1.Add("state"),
        manager.FLOW_REQUEST_TEMPLATE % 1,
        token=self.token))

    flow_obj = aff4.FACTORY.Open(session_id_1, token=self.token)
    self.assertTrue(flow_obj.state.context.state !=
                    rdfvalue.Flow.State.TERMINATED)
    flow_obj = aff4.FACTORY.Open(session_id_2, token=self.token)
    self.assertTrue(flow_obj.state.context.state ==
                    rdfvalue.Flow.State.TERMINATED)

  def testProcessMessagesWellKnown(self):
    worker_obj = worker.GRRWorker(worker.DEFAULT_WORKER_QUEUE,
                                  token=self.token)

    # Send a message to a WellKnownFlow - ClientStatsAuto.
    client_id = rdfvalue.ClientURN("C.1100110011001100")
    self.SendResponse(rdfvalue.SessionID("aff4:/flows/W:Stats"),
                      data=rdfvalue.ClientStats(RSS_size=1234),
                      client_id=client_id, well_known=True)

    # Process all messages
    worker_obj.RunOnce()
    worker_obj.thread_pool.Join()

    client = aff4.FACTORY.Open(client_id.Add("stats"), token=self.token)
    stats = client.Get(client.Schema.STATS)
    self.assertEqual(stats.RSS_size, 1234)

    # Make sure no notifications have been sent.
    user = aff4.FACTORY.Open("aff4:/users/%s" % self.token.username,
                             token=self.token)
    notifications = user.Get(user.Schema.PENDING_NOTIFICATIONS)
    self.assertIsNone(notifications)

  def CheckNotificationsDisappear(self, session_id):
    worker_obj = worker.GRRWorker(worker.DEFAULT_WORKER_QUEUE,
                                  token=self.token)
    manager = queue_manager.QueueManager(token=self.token)
    manager.NotifyQueue(session_id)

    sessions = manager.GetSessionsFromQueue(worker.DEFAULT_WORKER_QUEUE)
    # Check the notification is there.
    self.assertEqual(len(sessions), 1)
    self.assertEqual(sessions[0], session_id)

    # Process all messages
    worker_obj.RunOnce()
    worker_obj.thread_pool.Join()

    sessions = manager.GetSessionsFromQueue(worker.DEFAULT_WORKER_QUEUE)
    # Check the notification is now gone.
    self.assertEqual(len(sessions), 0)

  def testWorkerDeletesNotificationsForBrokenObjects(self):
    # Test notifications for objects that don't exist.
    session_id = rdfvalue.SessionID("aff4:/flows/W:123456")

    self.CheckNotificationsDisappear(session_id)

    # Now check objects that are actually broken.

    # Start a new flow.
    session_id = flow.GRRFlow.StartFlow(flow_name="WorkerSendingTestFlow",
                                        client_id=self.client_id,
                                        token=self.token)
    # Overwrite the type of the object such that opening it will now fail.
    data_store.DB.Set(session_id, "aff4:type", "DeprecatedClass",
                      token=self.token)

    # Starting a new flow schedules notifications for the worker already but
    # this test actually checks that there are none. Thus, we have to delete
    # them or the test fails.
    data_store.DB.DeleteSubject(worker.DEFAULT_WORKER_QUEUE, token=self.token)

    # Check it really does.
    with self.assertRaises(aff4.InstanciationError):
      aff4.FACTORY.Open(session_id, token=self.token)

    self.CheckNotificationsDisappear(session_id)


def main(_):
  test_lib.main()

if __name__ == "__main__":
  flags.StartMain(main)
