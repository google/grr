#!/usr/bin/env python
"""Test the usage reporting statistics."""


from grr.lib import events
from grr.lib import rdfvalue
from grr.lib import test_lib


def PopulateData(token=None):
  """Populates some usage information into the data store."""

  flows = ["ListDirectory", "GetFile", "Flow1", "KillFlow", "Interrogate"]

  def SimulateUserActivity(username, client_id, timestamp, num=10):
    for flow_name in flows[:num]:
      event = events.AuditEvent(
          user=username,
          action="RUN_FLOW",
          flow_name=flow_name,
          client=client_id,
          age=timestamp)

      events.Events.PublishEvent("Audit", event, token=token)

  now = int(rdfvalue.RDFDatetime().Now())
  week_duration = 7 * 24 * 60 * 60 * 1e6

  SimulateUserActivity("test", "C.0000000000000001", now)
  SimulateUserActivity("test", "C.0000000000000002", now)
  SimulateUserActivity("admin", "C.0000000000000001", now)
  SimulateUserActivity("user", "C.0000000000000003", now)

  SimulateUserActivity("test", "C.0000000000000001", now - week_duration)
  SimulateUserActivity("admin", "C.0000000000000001", now - week_duration)

  SimulateUserActivity("user", "C.0000000000000001", now - 2 * week_duration)
  SimulateUserActivity("admin", "C.0000000000000001", now - 2 * week_duration)

  test_lib.MockWorker(token=token).Simulate()
