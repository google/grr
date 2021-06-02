#!/usr/bin/env python
"""Integration tests for the timline API."""
import io

from absl import app

from grr_response_core.lib.rdfvalues import timeline as rdf_timeline
from grr_response_server import data_store
from grr_response_server.databases import db_test_utils
from grr_response_server.gui import api_integration_test_lib
from grr.test_lib import test_lib
from grr.test_lib import timeline_test_lib


class TimelineTest(api_integration_test_lib.ApiIntegrationTest):

  def testGetCollectedTimelineBody(self):
    entry = rdf_timeline.TimelineEntry()
    entry.path = "/foo/bar/baz".encode("utf-8")

    client_id = db_test_utils.InitializeClient(data_store.REL_DB)
    flow_id = timeline_test_lib.WriteTimeline(client_id, [entry])

    data = io.BytesIO()

    flow = self.api.Client(client_id).Flow(flow_id)
    flow.GetCollectedTimelineBody().WriteToStream(data)  # pytype: disable=wrong-arg-types

    content = data.getvalue().decode("utf-8")
    self.assertIn("|/foo/bar/baz|", content)

  def testGetCollectedTimelineBodyBackslashEscape(self):
    entry = rdf_timeline.TimelineEntry()
    entry.path = "C:\\Windows\\system32\\notepad.exe".encode("utf-8")

    client_id = db_test_utils.InitializeClient(data_store.REL_DB)
    flow_id = timeline_test_lib.WriteTimeline(client_id, [entry])

    data = io.BytesIO()

    flow = self.api.Client(client_id).Flow(flow_id)
    flow.GetCollectedTimelineBody(backslash_escape=True).WriteToStream(data)

    content = data.getvalue().decode("utf-8")
    self.assertIn("|C:\\\\Windows\\\\system32\\\\notepad.exe|", content)

  def testGetCollectedTimelineBodyCarriageReturnEscape(self):
    entry = rdf_timeline.TimelineEntry()
    entry.path = "/foo\rbar/baz\r\r\rquux".encode("utf-8")

    client_id = db_test_utils.InitializeClient(data_store.REL_DB)
    flow_id = timeline_test_lib.WriteTimeline(client_id, [entry])

    flow = self.api.Client(client_id).Flow(flow_id)
    chunks = flow.GetCollectedTimelineBody(carriage_return_escape=True)

    data = io.BytesIO()
    chunks.WriteToStream(data)

    content = data.getvalue().decode("utf-8")
    self.assertIn("|/foo\\rbar/baz\\r\\r\\rquux|", content)

  def testGetCollectedTimelineBodyNonPrintableEscape(self):
    entry = rdf_timeline.TimelineEntry()
    entry.path = b"/f\x00b\x0ar\x1baz"

    client_id = db_test_utils.InitializeClient(data_store.REL_DB)
    flow_id = timeline_test_lib.WriteTimeline(client_id, [entry])

    flow = self.api.Client(client_id).Flow(flow_id)
    chunks = flow.GetCollectedTimelineBody(non_printable_escape=True)

    data = io.BytesIO()
    chunks.WriteToStream(data)

    content = data.getvalue().decode("utf-8")
    self.assertIn(r"|/f\x00b\x0ar\x1baz|", content)


if __name__ == "__main__":
  app.run(test_lib.main)
