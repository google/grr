#!/usr/bin/env python
"""This modules contains tests for clients API handlers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


import ipaddr
import mock

from google.protobuf import timestamp_pb2
from fleetspeak.src.server.proto.fleetspeak_server import admin_pb2
from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import events as rdf_events
from grr_response_core.lib.rdfvalues import test_base as rdf_test_base
from grr_response_server import aff4
from grr_response_server import client_index
from grr_response_server import data_store
from grr_response_server import fleetspeak_connector
from grr_response_server import fleetspeak_utils
from grr_response_server.flows.general import audit
from grr_response_server.gui import api_test_lib
from grr_response_server.gui.api_plugins import client as client_plugin
from grr.test_lib import db_test_lib
from grr.test_lib import test_lib
from grr.test_lib import worker_test_lib


class ApiClientIdTest(rdf_test_base.RDFValueTestMixin, test_lib.GRRBaseTest):
  """Test for ApiClientId."""

  rdfvalue_class = client_plugin.ApiClientId

  def GenerateSample(self, number=0):
    return client_plugin.ApiClientId("C.%016d" % number)

  def testRaisesWhenInitializedFromInvalidValues(self):
    with self.assertRaises(ValueError):
      client_plugin.ApiClientId("blah")

    with self.assertRaises(ValueError):
      client_plugin.ApiClientId("C.0")

    with self.assertRaises(ValueError):
      client_plugin.ApiClientId("C." + "0" * 15)

    with self.assertRaises(ValueError):
      client_plugin.ApiClientId("C." + "1" * 16 + "/foo")

  def testRaisesWhenToClientURNCalledOnUninitializedValue(self):
    client_id = client_plugin.ApiClientId()
    with self.assertRaises(ValueError):
      client_id.ToClientURN()

  def testConvertsToClientURN(self):
    client_id = client_plugin.ApiClientId("C." + "1" * 16)
    client_urn = client_id.ToClientURN()

    self.assertEqual(client_urn.Basename(), client_id)
    self.assertEqual(client_urn, "aff4:/C." + "1" * 16)


class ApiAddClientsLabelsHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Test for ApiAddClientsLabelsHandler."""

  def setUp(self):
    super(ApiAddClientsLabelsHandlerTest, self).setUp()
    self.client_ids = self.SetupClients(3)
    self.handler = client_plugin.ApiAddClientsLabelsHandler()

  def testAddsSingleLabelToSingleClient(self):
    for client_id in self.client_ids:
      self.assertFalse(
          aff4.FACTORY.Open(client_id, token=self.token).GetLabels())
      data_store.REL_DB.WriteClientMetadata(
          client_id.Basename(), fleetspeak_enabled=False)

    self.handler.Handle(
        client_plugin.ApiAddClientsLabelsArgs(
            client_ids=[self.client_ids[0]], labels=[u"foo"]),
        token=self.token)

    # AFF4 labels.
    labels = aff4.FACTORY.Open(self.client_ids[0], token=self.token).GetLabels()
    self.assertLen(labels, 1)
    self.assertEqual(labels[0].name, u"foo")
    self.assertEqual(labels[0].owner, self.token.username)

    for client_id in self.client_ids[1:]:
      self.assertFalse(
          aff4.FACTORY.Open(client_id, token=self.token).GetLabels())

    # Relational DB labels.
    cid = self.client_ids[0].Basename()
    labels = data_store.REL_DB.ReadClientLabels(cid)
    self.assertLen(labels, 1)
    self.assertEqual(labels[0].name, u"foo")
    self.assertEqual(labels[0].owner, self.token.username)

    for client_id in self.client_ids[1:]:
      self.assertFalse(data_store.REL_DB.ReadClientLabels(client_id.Basename()))

  def testAddsTwoLabelsToTwoClients(self):
    for client_id in self.client_ids:
      self.assertFalse(
          aff4.FACTORY.Open(client_id, token=self.token).GetLabels())
      data_store.REL_DB.WriteClientMetadata(
          client_id.Basename(), fleetspeak_enabled=False)

    self.handler.Handle(
        client_plugin.ApiAddClientsLabelsArgs(
            client_ids=[self.client_ids[0], self.client_ids[1]],
            labels=[u"foo", u"bar"]),
        token=self.token)

    # AFF4 labels.
    for client_id in self.client_ids[:2]:
      labels = aff4.FACTORY.Open(client_id, token=self.token).GetLabels()
      self.assertLen(labels, 2)
      self.assertEqual(labels[0].name, u"foo")
      self.assertEqual(labels[0].owner, self.token.username)
      self.assertEqual(labels[1].name, u"bar")
      self.assertEqual(labels[1].owner, self.token.username)

    self.assertFalse(
        aff4.FACTORY.Open(self.client_ids[2], token=self.token).GetLabels())

    # Relational labels.
    for client_id in self.client_ids[:2]:
      labels = data_store.REL_DB.ReadClientLabels(client_id.Basename())
      self.assertLen(labels, 2)
      self.assertEqual(labels[0].owner, self.token.username)
      self.assertEqual(labels[1].owner, self.token.username)
      self.assertCountEqual([labels[0].name, labels[1].name], [u"bar", u"foo"])

    self.assertFalse(
        data_store.REL_DB.ReadClientLabels(self.client_ids[2].Basename()))

  def _FindAuditEvent(self):
    for fd in audit._AllLegacyAuditLogs(token=self.token):
      for event in fd:
        if event.action == rdf_events.AuditEvent.Action.CLIENT_ADD_LABEL:
          for client_id in self.client_ids:
            if event.client == rdf_client.ClientURN(client_id):
              return event

  def testAuditEntryIsCreatedForEveryClient(self):
    self.handler.Handle(
        client_plugin.ApiAddClientsLabelsArgs(
            client_ids=self.client_ids, labels=[u"drei", u"ein", u"zwei"]),
        token=self.token)

    # We need to run .Simulate() so that the appropriate event is fired,
    # collected, and finally written to the logs that we inspect.
    mock_worker = worker_test_lib.MockWorker(token=self.token)
    mock_worker.Simulate()

    event = self._FindAuditEvent()
    self.assertIsNotNone(event)
    self.assertEqual(event.user, self.token.username)
    self.assertEqual(
        event.description, "%s.drei,%s.ein,%s.zwei" %
        (self.token.username, self.token.username, self.token.username))


class ApiRemoveClientsLabelsHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Test for ApiRemoveClientsLabelsHandler."""

  def setUp(self):
    super(ApiRemoveClientsLabelsHandlerTest, self).setUp()
    self.client_ids = self.SetupClients(3)
    self.handler = client_plugin.ApiRemoveClientsLabelsHandler()

  def testRemovesUserLabelFromSingleClient(self):
    with aff4.FACTORY.Open(
        self.client_ids[0], mode="rw", token=self.token) as grr_client:
      grr_client.AddLabels([u"foo", u"bar"])
      data_store.REL_DB.WriteClientMetadata(
          self.client_ids[0].Basename(), fleetspeak_enabled=False)
      data_store.REL_DB.AddClientLabels(self.client_ids[0].Basename(),
                                        self.token.username, [u"foo", u"bar"])

    self.handler.Handle(
        client_plugin.ApiRemoveClientsLabelsArgs(
            client_ids=[self.client_ids[0]], labels=[u"foo"]),
        token=self.token)

    # AFF4 labels.
    labels = aff4.FACTORY.Open(self.client_ids[0], token=self.token).GetLabels()
    self.assertLen(labels, 1)
    self.assertEqual(labels[0].name, u"bar")
    self.assertEqual(labels[0].owner, self.token.username)

    # Relational labels.
    labels = data_store.REL_DB.ReadClientLabels(self.client_ids[0].Basename())
    self.assertLen(labels, 1)
    self.assertEqual(labels[0].name, u"bar")
    self.assertEqual(labels[0].owner, self.token.username)

  def testDoesNotRemoveSystemLabelFromSingleClient(self):
    idx = client_index.ClientIndex()
    with aff4.FACTORY.Open(
        self.client_ids[0], mode="rw", token=self.token) as grr_client:
      grr_client.AddLabel(u"foo", owner=u"GRR")
      data_store.REL_DB.WriteClientMetadata(
          self.client_ids[0].Basename(), fleetspeak_enabled=False)
      data_store.REL_DB.AddClientLabels(self.client_ids[0].Basename(), u"GRR",
                                        [u"foo"])
      idx.AddClientLabels(self.client_ids[0].Basename(), [u"foo"])

    self.handler.Handle(
        client_plugin.ApiRemoveClientsLabelsArgs(
            client_ids=[self.client_ids[0]], labels=[u"foo"]),
        token=self.token)

    # AFF4 labels.
    labels = aff4.FACTORY.Open(self.client_ids[0], token=self.token).GetLabels()
    self.assertLen(labels, 1)

    # Relational labels.
    labels = data_store.REL_DB.ReadClientLabels(self.client_ids[0].Basename())
    self.assertLen(labels, 1)
    # The label is still in the index.
    self.assertEqual(
        idx.LookupClients(["label:foo"]), [self.client_ids[0].Basename()])

  def testRemovesUserLabelWhenSystemLabelWithSimilarNameAlsoExists(self):
    idx = client_index.ClientIndex()
    with aff4.FACTORY.Open(
        self.client_ids[0], mode="rw", token=self.token) as grr_client:
      grr_client.AddLabel(u"foo")
      grr_client.AddLabel(u"foo", owner=u"GRR")
      data_store.REL_DB.WriteClientMetadata(
          self.client_ids[0].Basename(), fleetspeak_enabled=False)
      data_store.REL_DB.AddClientLabels(self.client_ids[0].Basename(),
                                        self.token.username, [u"foo"])
      data_store.REL_DB.AddClientLabels(self.client_ids[0].Basename(), u"GRR",
                                        [u"foo"])
      idx.AddClientLabels(self.client_ids[0].Basename(), [u"foo"])

    self.handler.Handle(
        client_plugin.ApiRemoveClientsLabelsArgs(
            client_ids=[self.client_ids[0]], labels=[u"foo"]),
        token=self.token)

    # AFF4 labels.
    labels = aff4.FACTORY.Open(self.client_ids[0], token=self.token).GetLabels()
    self.assertLen(labels, 1)
    self.assertEqual(labels[0].name, u"foo")
    self.assertEqual(labels[0].owner, u"GRR")

    # Relational labels.
    labels = data_store.REL_DB.ReadClientLabels(self.client_ids[0].Basename())
    self.assertLen(labels, 1)
    self.assertEqual(labels[0].name, u"foo")
    self.assertEqual(labels[0].owner, u"GRR")
    # The label is still in the index.
    self.assertEqual(
        idx.LookupClients(["label:foo"]), [self.client_ids[0].Basename()])


class ApiLabelsRestrictedSearchClientsHandlerTestMixin(object):

  def testSearchWithoutArgsReturnsOnlyClientsWithWhitelistedLabels(self):
    result = self.handler.Handle(
        client_plugin.ApiSearchClientsArgs(), token=self.token)

    self.assertLen(result.items, 2)
    sorted_items = sorted(result.items, key=lambda r: r.client_id)

    self.assertEqual(sorted_items[0].client_id, self.client_ids[0])
    self.assertEqual(sorted_items[1].client_id, self.client_ids[3])

  def testSearchWithNonWhitelistedLabelReturnsNothing(self):
    result = self.handler.Handle(
        client_plugin.ApiSearchClientsArgs(query="label:not-foo"),
        token=self.token)
    self.assertFalse(result.items)

  def testSearchWithWhitelistedLabelReturnsSubSet(self):
    result = self.handler.Handle(
        client_plugin.ApiSearchClientsArgs(query="label:foo"), token=self.token)
    self.assertLen(result.items, 1)
    self.assertEqual(result.items[0].client_id, self.client_ids[0])

    result = self.handler.Handle(
        client_plugin.ApiSearchClientsArgs(query="label:bar"), token=self.token)
    self.assertLen(result.items, 1)
    self.assertEqual(result.items[0].client_id, self.client_ids[3])

  def testSearchWithWhitelistedClientIdsReturnsSubSet(self):
    result = self.handler.Handle(
        client_plugin.ApiSearchClientsArgs(query=self.client_ids[0]),
        token=self.token)
    self.assertLen(result.items, 1)
    self.assertEqual(result.items[0].client_id, self.client_ids[0])

    result = self.handler.Handle(
        client_plugin.ApiSearchClientsArgs(query=self.client_ids[3]),
        token=self.token)
    self.assertLen(result.items, 1)
    self.assertEqual(result.items[0].client_id, self.client_ids[3])

  def testSearchWithBlacklistedClientIdsReturnsNothing(self):
    result = self.handler.Handle(
        client_plugin.ApiSearchClientsArgs(query=self.client_ids[1]),
        token=self.token)
    self.assertFalse(result.items)

    result = self.handler.Handle(
        client_plugin.ApiSearchClientsArgs(query=self.client_ids[2]),
        token=self.token)
    self.assertFalse(result.items)

  def testSearchOrder(self):
    self._Setup100Clients()

    result = self.handler.Handle(
        client_plugin.ApiSearchClientsArgs(
            query="label:foo", offset=0, count=1000),
        token=self.token)
    self.assertEqual([str(res.client_id) for res in result.items],
                     self.client_ids)

    result = []
    for offset, count in [(0, 10), (10, 40), (50, 25), (75, 500)]:
      result.extend(
          self.handler.Handle(
              client_plugin.ApiSearchClientsArgs(
                  query="label:foo", offset=offset, count=count),
              token=self.token).items)
    self.assertEqual([str(res.client_id) for res in result], self.client_ids)


class ApiLabelsRestrictedSearchClientsHandlerTestAFF4(
    ApiLabelsRestrictedSearchClientsHandlerTestMixin,
    api_test_lib.ApiCallHandlerTest):
  """Test for ApiLabelsRestrictedSearchClientsHandler using AFF4."""

  def setUp(self):
    super(ApiLabelsRestrictedSearchClientsHandlerTestAFF4, self).setUp()

    self.client_ids = [u.Basename() for u in self.SetupClients(4)]

    index = client_index.CreateClientIndex(token=self.token)

    def LabelClient(i, label, owner):
      with aff4.FACTORY.Open(
          self.client_ids[i], mode="rw", token=self.token) as grr_client:
        grr_client.AddLabel(label, owner=owner)
        index.AddClient(grr_client)

    LabelClient(0, u"foo", u"david")
    LabelClient(1, u"not-foo", u"david")
    LabelClient(2, u"bar", u"peter_another")
    LabelClient(3, u"bar", u"peter")

    self.handler = client_plugin.ApiLabelsRestrictedSearchClientsHandler(
        labels_whitelist=[u"foo", u"bar"],
        labels_owners_whitelist=[u"david", u"peter"])

  def _Setup100Clients(self):
    self.client_urns = self.SetupClients(100)
    self.client_ids = [u.Basename() for u in self.client_urns]
    index = client_index.CreateClientIndex(token=self.token)
    for client in aff4.FACTORY.MultiOpen(
        self.client_urns, mode="rw", token=self.token):
      with client:
        client.AddLabel(u"foo", owner=u"david")
        index.AddClient(client)


class ApiLabelsRestrictedSearchClientsHandlerTestRelational(
    ApiLabelsRestrictedSearchClientsHandlerTestMixin,
    db_test_lib.RelationalDBEnabledMixin, api_test_lib.ApiCallHandlerTest):
  """Tests ApiLabelsRestrictedSearchClientsHandler using the relational db."""

  def setUp(self):
    super(ApiLabelsRestrictedSearchClientsHandlerTestRelational, self).setUp()

    self.client_ids = sorted(self.SetupTestClientObjects(4))

    data_store.REL_DB.AddClientLabels(self.client_ids[0], u"david", [u"foo"])
    data_store.REL_DB.AddClientLabels(self.client_ids[1], u"david",
                                      [u"not-foo"])
    data_store.REL_DB.AddClientLabels(self.client_ids[2], u"peter_oth",
                                      [u"bar"])
    data_store.REL_DB.AddClientLabels(self.client_ids[3], u"peter", [u"bar"])

    index = client_index.ClientIndex()
    index.AddClientLabels(self.client_ids[0], [u"foo"])
    index.AddClientLabels(self.client_ids[1], [u"not-foo"])
    index.AddClientLabels(self.client_ids[2], [u"bar"])
    index.AddClientLabels(self.client_ids[3], [u"bar"])

    self.handler = client_plugin.ApiLabelsRestrictedSearchClientsHandler(
        labels_whitelist=[u"foo", u"bar"],
        labels_owners_whitelist=[u"david", u"peter"])

  def _Setup100Clients(self):
    self.client_ids = sorted(self.SetupTestClientObjects(100))
    index = client_index.ClientIndex()
    for client_id in self.client_ids:
      data_store.REL_DB.AddClientLabels(client_id, u"david", [u"foo"])
      index.AddClientLabels(client_id, [u"foo"])


class ApiInterrogateClientHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Test for ApiInterrogateClientHandler."""

  def setUp(self):
    super(ApiInterrogateClientHandlerTest, self).setUp()
    self.client_id = self.SetupClient(0)
    self.handler = client_plugin.ApiInterrogateClientHandler()

  def testInterrogateFlowIsStarted(self):
    flows_fd = aff4.FACTORY.Open(self.client_id.Add("flows"), token=self.token)
    flows_urns = list(flows_fd.ListChildren())
    self.assertEmpty(flows_urns)

    args = client_plugin.ApiInterrogateClientArgs(client_id=self.client_id)
    result = self.handler.Handle(args, token=self.token)

    flows_fd = aff4.FACTORY.Open(self.client_id.Add("flows"), token=self.token)
    flows_urns = list(flows_fd.ListChildren())
    self.assertLen(flows_urns, 1)
    self.assertEqual(str(flows_urns[0]), result.operation_id)


class ApiGetClientVersionTimesTestMixin(object):
  """Test mixin for ApiGetClientVersionTimes."""

  def setUp(self):
    super(ApiGetClientVersionTimesTestMixin, self).setUp()
    self.handler = client_plugin.ApiGetClientVersionTimesHandler()

  def testHandler(self):
    self._SetUpClient()
    args = client_plugin.ApiGetClientVersionTimesArgs(client_id=self.client_id)
    result = self.handler.Handle(args, token=self.token)

    self.assertLen(result.times, 3)
    self.assertEqual(result.times[0].AsSecondsSinceEpoch(), 100)
    self.assertEqual(result.times[1].AsSecondsSinceEpoch(), 45)
    self.assertEqual(result.times[2].AsSecondsSinceEpoch(), 42)


class ApiGetClientVersionTimesTestRelational(ApiGetClientVersionTimesTestMixin,
                                             api_test_lib.ApiCallHandlerTest):
  """Test for ApiGetClientVersionTimes using the relational db."""

  def setUp(self):
    super(ApiGetClientVersionTimesTestRelational, self).setUp()

    self.enable_relational_db = test_lib.ConfigOverrider(
        {"Database.useForReads": True})
    self.enable_relational_db.Start()

  def tearDown(self):
    super(ApiGetClientVersionTimesTestRelational, self).tearDown()
    self.enable_relational_db.Stop()

  def _SetUpClient(self):
    for time in [42, 45, 100]:
      with test_lib.FakeTime(time):
        client_obj = self.SetupTestClientObject(0)
        self.client_id = client_obj.client_id


class ApiGetClientVersionTimesTestAFF4(ApiGetClientVersionTimesTestMixin,
                                       api_test_lib.ApiCallHandlerTest):
  """Test for ApiGetClientVersionTimes using AFF4."""

  def _SetUpClient(self):
    for time in [42, 45, 100]:
      with test_lib.FakeTime(time):
        client_urn = self.SetupClient(0)
        self.client_id = client_urn.Basename()


def TSProtoFromString(string):
  ts = timestamp_pb2.Timestamp()
  ts.FromJsonString(string)
  return ts


class ApiFleetspeakIntegrationTest(api_test_lib.ApiCallHandlerTest):

  def testUpdateClientsFromFleetspeak(self):
    client_id_1 = client_plugin.ApiClientId("C." + "1" * 16)
    client_id_2 = client_plugin.ApiClientId("C." + "2" * 16)
    client_id_3 = client_plugin.ApiClientId("C." + "3" * 16)
    clients = [
        client_plugin.ApiClient(client_id=client_id_1, fleetspeak_enabled=True),
        client_plugin.ApiClient(client_id=client_id_2, fleetspeak_enabled=True),
        client_plugin.ApiClient(
            client_id=client_id_3, fleetspeak_enabled=False),
    ]
    conn = mock.MagicMock()
    conn.outgoing.ListClients.return_value = admin_pb2.ListClientsResponse(
        clients=[
            admin_pb2.Client(
                client_id=fleetspeak_utils.GRRIDToFleetspeakID(client_id_1),
                last_contact_time=TSProtoFromString("2018-01-01T00:00:01Z"),
                last_clock=TSProtoFromString("2018-01-01T00:00:02Z")),
            admin_pb2.Client(
                client_id=fleetspeak_utils.GRRIDToFleetspeakID(client_id_2),
                last_contact_time=TSProtoFromString("2018-01-02T00:00:01Z"),
                last_clock=TSProtoFromString("2018-01-02T00:00:02Z"))
        ])
    with mock.patch.object(fleetspeak_connector, "CONN", conn):
      client_plugin.UpdateClientsFromFleetspeak(clients)
    self.assertEqual(clients, [
        client_plugin.ApiClient(
            client_id=client_id_1,
            fleetspeak_enabled=True,
            last_seen_at=rdfvalue.RDFDatetime.FromHumanReadable(
                "2018-01-01T00:00:01Z"),
            last_clock=rdfvalue.RDFDatetime.FromHumanReadable(
                "2018-01-01T00:00:02Z")),
        client_plugin.ApiClient(
            client_id=client_id_2,
            fleetspeak_enabled=True,
            last_seen_at=rdfvalue.RDFDatetime.FromHumanReadable(
                "2018-01-02T00:00:01Z"),
            last_clock=rdfvalue.RDFDatetime.FromHumanReadable(
                "2018-01-02T00:00:02Z")),
        client_plugin.ApiClient(
            client_id=client_id_3, fleetspeak_enabled=False),
    ])

  def testGetAddrFromFleetspeakIpV4(self):
    client_id = client_plugin.ApiClientId("C." + "1" * 16)
    conn = mock.MagicMock()
    conn.outgoing.ListClients.return_value = admin_pb2.ListClientsResponse(
        clients=[
            admin_pb2.Client(
                client_id=fleetspeak_utils.GRRIDToFleetspeakID(client_id),
                last_contact_address="100.1.1.100:50000",
                last_contact_time=TSProtoFromString("2018-01-01T00:00:01Z"),
                last_clock=TSProtoFromString("2018-01-01T00:00:02Z"))
        ])
    with mock.patch.object(fleetspeak_connector, "CONN", conn):
      ip_str, ipaddr_obj = client_plugin._GetAddrFromFleetspeak(client_id)
      self.assertEqual(ip_str, "100.1.1.100")
      self.assertEqual(ipaddr_obj, ipaddr.IPAddress("100.1.1.100"))

  def testGetAddrFromFleetspeakIpV6(self):
    client_id = client_plugin.ApiClientId("C." + "1" * 16)
    conn = mock.MagicMock()
    conn.outgoing.ListClients.return_value = admin_pb2.ListClientsResponse(
        clients=[
            admin_pb2.Client(
                client_id=fleetspeak_utils.GRRIDToFleetspeakID(client_id),
                last_contact_address="[2001:0db8:85a3::8a2e:0370:7334]:50000",
                last_contact_time=TSProtoFromString("2018-01-01T00:00:01Z"),
                last_clock=TSProtoFromString("2018-01-01T00:00:02Z"))
        ])
    with mock.patch.object(fleetspeak_connector, "CONN", conn):
      ip_str, ipaddr_obj = client_plugin._GetAddrFromFleetspeak(client_id)
      self.assertEqual(ip_str, "2001:0db8:85a3::8a2e:0370:7334")
      self.assertEqual(
          ipaddr_obj,
          ipaddr.IPAddress("2001:0db8:85a3:0000:0000:8a2e:0370:7334"))

  def testGetAddrFromFleetspeakMissing(self):
    client_id = client_plugin.ApiClientId("C." + "1" * 16)
    conn = mock.MagicMock()
    conn.outgoing.ListClients.return_value = admin_pb2.ListClientsResponse(
        clients=[
            admin_pb2.Client(
                client_id=fleetspeak_utils.GRRIDToFleetspeakID(client_id),
                last_contact_time=TSProtoFromString("2018-01-01T00:00:01Z"),
                last_clock=TSProtoFromString("2018-01-01T00:00:02Z"))
        ])
    with mock.patch.object(fleetspeak_connector, "CONN", conn):
      ip_str, ipaddr_obj = client_plugin._GetAddrFromFleetspeak(client_id)
      self.assertEqual(ip_str, "")
      self.assertIsNone(ipaddr_obj)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
