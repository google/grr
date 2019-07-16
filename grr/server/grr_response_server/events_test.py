#!/usr/bin/env python
"""Tests for the event publishing system."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import events
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


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


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
