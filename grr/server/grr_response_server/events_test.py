#!/usr/bin/env python
"""Tests for the event publishing system."""


from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import paths as rdf_paths
from grr.server.grr_response_server import events
from grr.server.grr_response_server import maintenance_utils
from grr.server.grr_response_server.flows.general import audit
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib
from grr.test_lib import worker_test_lib


class TestListener(events.EventListener):  # pylint: disable=unused-variable
  EVENTS = ["TestEvent"]

  received_events = []

  def ProcessMessages(self, msgs=None, token=None):
    # Store the results for later inspection.
    self.__class__.received_events.extend(msgs)


class EventsTest(flow_test_lib.FlowTestsBaseclass):

  def testEventNotification(self):
    """Test that events are sent to listeners."""
    TestListener.received_events = []

    event = rdf_flows.GrrMessage(
        session_id=rdfvalue.SessionID(flow_name="SomeFlow"),
        name="test message",
        payload=rdf_paths.PathSpec(path="foobar", pathtype="TSK"),
        source="aff4:/C.0000000000000001",
        auth_state="AUTHENTICATED")

    events.Events.PublishEvent("TestEvent", event, token=self.token)

    # Make sure the source is correctly propagated.
    self.assertEqual(TestListener.received_events[0], event)

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
