#!/usr/bin/env python
"""Tests for the event publishing system."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_api_client import api
from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import events
from grr_response_server.bin import api_shell_raw_access_lib
from grr_response_server.flows.general import audit
from grr_response_server.gui.api_plugins import user as api_user
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

    grr_api = api.GrrApi(
        connector=api_shell_raw_access_lib.RawConnector(
            token=token, page_size=10))
    grr_user = grr_api.root.CreateGrrUser(
        "testuser",
        password="xxx",
        user_type=int(api_user.ApiGrrUser.UserType.USER_TYPE_ADMIN))
    worker.Simulate()

    grr_user.Modify(
        password="xxx",
        user_type=int(api_user.ApiGrrUser.UserType.USER_TYPE_STANDARD))
    worker.Simulate()

    grr_user.Delete()
    worker.Simulate()

    log_entries = []
    for log in audit._AllLegacyAuditLogs(token=self.token):
      log_entries.extend(log)

    self.assertLen(log_entries, 3)

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
