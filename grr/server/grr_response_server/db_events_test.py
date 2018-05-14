#!/usr/bin/env python
from grr.lib import rdfvalue
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import events as rdf_events


class DatabaseEventsTestMixin(object):

  def testWriteAuditEventFieldSerialization(self):
    client_urn = rdf_client.ClientURN("C.4815162342000000")

    event = rdf_events.AuditEvent(
        action=rdf_events.AuditEvent.Action.RUN_FLOW,
        user="quux",
        flow_name="foo",
        flow_args="bar",
        client=client_urn,
        urn=client_urn.Add("flows").Add("108"),
        description="lorem ipsum")

    self.db.WriteAuditEvent(event)

    log = self.db.ReadAllAuditEvents()
    self.assertEqual(len(log), 1)
    self.assertEqual(log[0].action, rdf_events.AuditEvent.Action.RUN_FLOW)
    self.assertEqual(log[0].user, "quux")
    self.assertEqual(log[0].flow_name, "foo")
    self.assertEqual(log[0].flow_args, "bar")
    self.assertEqual(log[0].client, client_urn)
    self.assertEqual(log[0].urn, client_urn.Add("flows").Add("108"))
    self.assertEqual(log[0].description, "lorem ipsum")

  def testWriteAuditEventMultipleEvents(self):
    timestamp = rdfvalue.RDFDatetime.Now()

    self.db.WriteAuditEvent(rdf_events.AuditEvent(urn=rdfvalue.RDFURN("foo")))
    self.db.WriteAuditEvent(rdf_events.AuditEvent(urn=rdfvalue.RDFURN("bar")))
    self.db.WriteAuditEvent(rdf_events.AuditEvent(urn=rdfvalue.RDFURN("baz")))

    log = self.db.ReadAllAuditEvents()
    self.assertEqual(len(log), 3)
    self.assertEqual(log[0].urn, rdfvalue.RDFURN("foo"))
    self.assertEqual(log[1].urn, rdfvalue.RDFURN("bar"))
    self.assertEqual(log[2].urn, rdfvalue.RDFURN("baz"))
    self.assertGreater(log[0].timestamp, timestamp)
    self.assertGreater(log[1].timestamp, timestamp)
    self.assertGreater(log[2].timestamp, timestamp)
