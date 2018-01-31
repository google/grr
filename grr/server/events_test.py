#!/usr/bin/env python
"""Tests for the event publishing system."""


from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import paths as rdf_paths
from grr.server import events
from grr.server import flow
from grr.server import maintenance_utils
from grr.server.flows.general import audit
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib
from grr.test_lib import worker_test_lib


class NoClientListener(flow.EventListener):  # pylint: disable=unused-variable
  well_known_session_id = rdfvalue.SessionID(flow_name="test2")
  EVENTS = ["TestEvent"]

  received_events = []

  @flow.EventHandler(auth_required=True)
  def ProcessMessage(self, message=None, event=None):
    # Store the results for later inspection.
    self.__class__.received_events.append((message, event))


class ClientListener(flow.EventListener):
  well_known_session_id = rdfvalue.SessionID(flow_name="test3")
  EVENTS = ["TestEvent"]

  received_events = []

  @flow.EventHandler(auth_required=True, allow_client_access=True)
  def ProcessMessage(self, message=None, event=None):
    # Store the results for later inspection.
    self.__class__.received_events.append((message, event))


class FlowDoneListener(flow.EventListener):
  well_known_session_id = rdfvalue.SessionID(
      queue=rdfvalue.RDFURN("EV"), flow_name="FlowDone")
  EVENTS = ["Not used"]
  received_events = []

  @flow.EventHandler(auth_required=True)
  def ProcessMessage(self, message=None, event=None):
    _ = event
    # Store the results for later inspection.
    FlowDoneListener.received_events.append(message)


class EventsTest(flow_test_lib.FlowTestsBaseclass):

  def testClientEventNotification(self):
    """Make sure that client events handled securely."""
    ClientListener.received_events = []
    NoClientListener.received_events = []

    event = rdf_flows.GrrMessage(
        source="C.1395c448a443c7d9",
        auth_state=rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED)

    event.payload = rdf_paths.PathSpec(path="foobar")

    events.Events.PublishEvent("TestEvent", event, token=self.token)
    worker_test_lib.MockWorker(token=self.token).Simulate()

    # The same event should be sent to both listeners, but only the listener
    # which accepts client messages should register it.
    self.assertRDFValuesEqual(ClientListener.received_events[0][0].payload,
                              event.payload)
    self.assertEqual(NoClientListener.received_events, [])

  def testFlowNotification(self):
    FlowDoneListener.received_events = []

    # Run the flow in the simulated way
    client_mock = action_mocks.ActionMock()
    for _ in flow_test_lib.TestFlowHelper(
        flow_test_lib.DummyLogFlow.__name__,
        client_mock,
        client_id=test_lib.TEST_CLIENT_ID,
        notification_urn=rdfvalue.SessionID(
            queue=rdfvalue.RDFURN("EV"), flow_name="FlowDone"),
        token=self.token):
      pass

    # The event goes to an external queue so we need another worker.
    worker = worker_test_lib.MockWorker(
        queues=[rdfvalue.RDFURN("EV")], token=self.token)
    worker.Simulate()

    self.assertEqual(len(FlowDoneListener.received_events), 1)

    flow_event = FlowDoneListener.received_events[0].payload
    self.assertEqual(flow_event.flow_name, flow_test_lib.DummyLogFlow.__name__)
    self.assertEqual(flow_event.client_id, "aff4:/C.1000000000000000")
    self.assertEqual(flow_event.status, rdf_flows.FlowNotification.Status.OK)

  def testEventNotification(self):
    """Test that events are sent to listeners."""
    NoClientListener.received_events = []
    worker = worker_test_lib.MockWorker(token=self.token)

    event = rdf_flows.GrrMessage(
        session_id=rdfvalue.SessionID(flow_name="SomeFlow"),
        name="test message",
        payload=rdf_paths.PathSpec(path="foobar", pathtype="TSK"),
        source="aff4:/C.0000000000000001",
        auth_state="AUTHENTICATED")

    # Not allowed to publish a message from a client..
    events.Events.PublishEvent("TestEvent", event, token=self.token)
    worker.Simulate()

    self.assertEqual(NoClientListener.received_events, [])

    event.source = "Source"

    # First make the message unauthenticated.
    event.auth_state = rdf_flows.GrrMessage.AuthorizationState.UNAUTHENTICATED

    # Publish the event.
    events.Events.PublishEvent("TestEvent", event, token=self.token)
    worker.Simulate()

    # This should not work - the unauthenticated message is dropped.
    self.assertEqual(NoClientListener.received_events, [])

    # Now make the message authenticated.
    event.auth_state = rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED

    # Publish the event.
    events.Events.PublishEvent("TestEvent", event, token=self.token)
    worker.Simulate()

    # This should now work:
    self.assertEqual(len(NoClientListener.received_events), 1)

    # Make sure the source is correctly propagated.
    self.assertEqual(NoClientListener.received_events[0][0].source,
                     "aff4:/Source")
    self.assertEqual(NoClientListener.received_events[0][1].path, "foobar")

    NoClientListener.received_events = []
    # Now schedule ten events at the same time.
    for i in xrange(10):
      event.source = "Source%d" % i
      events.Events.PublishEvent("TestEvent", event, token=self.token)

    worker.Simulate()

    self.assertEqual(len(NoClientListener.received_events), 10)

    # Events do not have to be delivered in order so we sort them here for
    # comparison.
    NoClientListener.received_events.sort(key=lambda x: x[0].source)
    for i in range(10):
      self.assertEqual(NoClientListener.received_events[i][0].source,
                       "aff4:/Source%d" % i)
      self.assertEqual(NoClientListener.received_events[i][1].path, "foobar")

  def testUserModificationAudit(self):
    worker = worker_test_lib.MockWorker(token=self.token)
    token = self.GenerateToken(username="usermodtest", reason="reason")

    maintenance_utils.AddUser(
        "testuser", password="xxx", labels=["admin"], token=token)
    worker.Simulate()

    maintenance_utils.UpdateUser(
        "testuser", "xxx", delete_labels=["admin"], token=token)
    worker.Simulate()

    maintenance_utils.DeleteUser("testuser", token=token)
    worker.Simulate()

    log_entries = []
    for log in audit.AllAuditLogs(token=self.token):
      log_entries.extend(log)

    self.assertEqual(len(log_entries), 3)

    self.assertEqual(log_entries[0].action, "USER_ADD")
    self.assertEqual(log_entries[0].urn, "aff4:/users/testuser")
    self.assertEqual(log_entries[0].user, "usermodtest")

    self.assertEqual(log_entries[1].action, "USER_UPDATE")
    self.assertEqual(log_entries[1].urn, "aff4:/users/testuser")
    self.assertEqual(log_entries[1].user, "usermodtest")

    self.assertEqual(log_entries[2].action, "USER_DELETE")
    self.assertEqual(log_entries[2].urn, "aff4:/users/testuser")
    self.assertEqual(log_entries[2].user, "usermodtest")


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
