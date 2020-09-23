#!/usr/bin/env python
# Lint as: python3
# -*- encoding: utf-8 -*-
"""This modules contains tests for clients API handlers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import ipaddress

from absl import app
import mock

from google.protobuf import timestamp_pb2
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import test_base as rdf_test_base
from grr_response_server import client_index
from grr_response_server import data_store
from grr_response_server import fleetspeak_connector
from grr_response_server import fleetspeak_utils
from grr_response_server.gui import api_test_lib
from grr_response_server.gui.api_plugins import client as client_plugin
from grr.test_lib import db_test_lib
from grr.test_lib import test_lib
from fleetspeak.src.server.proto.fleetspeak_server import admin_pb2


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

  def testRaisesWhenToStringCalledOnUninitializedValue(self):
    client_id = client_plugin.ApiClientId()
    with self.assertRaises(ValueError):
      client_id.ToString()

  def testConvertsToString(self):
    client_id = client_plugin.ApiClientId("C." + "1" * 16)
    client_id_str = client_id.ToString()

    self.assertEqual(client_id_str, "C." + "1" * 16)


class ApiAddClientsLabelsHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Test for ApiAddClientsLabelsHandler."""

  def setUp(self):
    super(ApiAddClientsLabelsHandlerTest, self).setUp()
    self.client_ids = self.SetupClients(3)
    self.handler = client_plugin.ApiAddClientsLabelsHandler()

  def testAddsSingleLabelToSingleClient(self):
    self.handler.Handle(
        client_plugin.ApiAddClientsLabelsArgs(
            client_ids=[self.client_ids[0]], labels=[u"foo"]),
        context=self.context)

    cid = self.client_ids[0]
    labels = data_store.REL_DB.ReadClientLabels(cid)
    self.assertLen(labels, 1)
    self.assertEqual(labels[0].name, u"foo")
    self.assertEqual(labels[0].owner, self.context.username)

    for client_id in self.client_ids[1:]:
      self.assertFalse(data_store.REL_DB.ReadClientLabels(client_id))

  def testAddsTwoLabelsToTwoClients(self):
    self.handler.Handle(
        client_plugin.ApiAddClientsLabelsArgs(
            client_ids=[self.client_ids[0], self.client_ids[1]],
            labels=[u"foo", u"bar"]),
        context=self.context)

    for client_id in self.client_ids[:2]:
      labels = data_store.REL_DB.ReadClientLabels(client_id)
      self.assertLen(labels, 2)
      self.assertEqual(labels[0].owner, self.context.username)
      self.assertEqual(labels[1].owner, self.context.username)
      self.assertCountEqual([labels[0].name, labels[1].name], [u"bar", u"foo"])

    self.assertFalse(data_store.REL_DB.ReadClientLabels(self.client_ids[2]))


class ApiRemoveClientsLabelsHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Test for ApiRemoveClientsLabelsHandler."""

  def setUp(self):
    super(ApiRemoveClientsLabelsHandlerTest, self).setUp()
    self.client_ids = self.SetupClients(3)
    self.handler = client_plugin.ApiRemoveClientsLabelsHandler()

  def testRemovesUserLabelFromSingleClient(self):
    data_store.REL_DB.WriteClientMetadata(
        self.client_ids[0], fleetspeak_enabled=False)
    data_store.REL_DB.AddClientLabels(self.client_ids[0], self.context.username,
                                      [u"foo", u"bar"])

    self.handler.Handle(
        client_plugin.ApiRemoveClientsLabelsArgs(
            client_ids=[self.client_ids[0]], labels=[u"foo"]),
        context=self.context)

    labels = data_store.REL_DB.ReadClientLabels(self.client_ids[0])
    self.assertLen(labels, 1)
    self.assertEqual(labels[0].name, u"bar")
    self.assertEqual(labels[0].owner, self.context.username)

  def testDoesNotRemoveSystemLabelFromSingleClient(self):
    data_store.REL_DB.WriteClientMetadata(
        self.client_ids[0], fleetspeak_enabled=False)
    data_store.REL_DB.AddClientLabels(self.client_ids[0], u"GRR", [u"foo"])
    idx = client_index.ClientIndex()
    idx.AddClientLabels(self.client_ids[0], [u"foo"])

    self.handler.Handle(
        client_plugin.ApiRemoveClientsLabelsArgs(
            client_ids=[self.client_ids[0]], labels=[u"foo"]),
        context=self.context)

    labels = data_store.REL_DB.ReadClientLabels(self.client_ids[0])
    self.assertLen(labels, 1)
    # The label is still in the index.
    self.assertEqual(idx.LookupClients(["label:foo"]), [self.client_ids[0]])

  def testRemovesUserLabelWhenSystemLabelWithSimilarNameAlsoExists(self):
    data_store.REL_DB.WriteClientMetadata(
        self.client_ids[0], fleetspeak_enabled=False)
    data_store.REL_DB.AddClientLabels(self.client_ids[0], self.context.username,
                                      [u"foo"])
    data_store.REL_DB.AddClientLabels(self.client_ids[0], u"GRR", [u"foo"])
    idx = client_index.ClientIndex()
    idx.AddClientLabels(self.client_ids[0], [u"foo"])

    self.handler.Handle(
        client_plugin.ApiRemoveClientsLabelsArgs(
            client_ids=[self.client_ids[0]], labels=[u"foo"]),
        context=self.context)

    labels = data_store.REL_DB.ReadClientLabels(self.client_ids[0])
    self.assertLen(labels, 1)
    self.assertEqual(labels[0].name, u"foo")
    self.assertEqual(labels[0].owner, u"GRR")
    # The label is still in the index.
    self.assertEqual(idx.LookupClients(["label:foo"]), [self.client_ids[0]])


class ApiLabelsRestrictedSearchClientsHandlerTestRelational(
    api_test_lib.ApiCallHandlerTest):
  """Tests ApiLabelsRestrictedSearchClientsHandler."""

  def setUp(self):
    super(ApiLabelsRestrictedSearchClientsHandlerTestRelational, self).setUp()

    self.client_ids = self.SetupClients(4)

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
        allow_labels=[u"foo", u"bar"], allow_labels_owners=[u"david", u"peter"])

  def _Setup100Clients(self):
    self.client_ids = self.SetupClients(100)
    index = client_index.ClientIndex()
    for client_id in self.client_ids:
      data_store.REL_DB.AddClientLabels(client_id, u"david", [u"foo"])
      index.AddClientLabels(client_id, [u"foo"])

  def testSearchWithoutArgsReturnsOnlyClientsWithAllowedLabels(self):
    result = self.handler.Handle(
        client_plugin.ApiSearchClientsArgs(), context=self.context)

    self.assertLen(result.items, 2)
    sorted_items = sorted(result.items, key=lambda r: r.client_id)

    self.assertEqual(sorted_items[0].client_id, self.client_ids[0])
    self.assertEqual(sorted_items[1].client_id, self.client_ids[3])

  def testSearchWithNonAllowedLabelReturnsNothing(self):
    result = self.handler.Handle(
        client_plugin.ApiSearchClientsArgs(query="label:not-foo"),
        context=self.context)
    self.assertFalse(result.items)

  def testSearchWithAllowedLabelReturnsSubSet(self):
    result = self.handler.Handle(
        client_plugin.ApiSearchClientsArgs(query="label:foo"),
        context=self.context)
    self.assertLen(result.items, 1)
    self.assertEqual(result.items[0].client_id, self.client_ids[0])

    result = self.handler.Handle(
        client_plugin.ApiSearchClientsArgs(query="label:bar"),
        context=self.context)
    self.assertLen(result.items, 1)
    self.assertEqual(result.items[0].client_id, self.client_ids[3])

  def testSearchWithAllowedClientIdsReturnsSubSet(self):
    result = self.handler.Handle(
        client_plugin.ApiSearchClientsArgs(query=self.client_ids[0]),
        context=self.context)
    self.assertLen(result.items, 1)
    self.assertEqual(result.items[0].client_id, self.client_ids[0])

    result = self.handler.Handle(
        client_plugin.ApiSearchClientsArgs(query=self.client_ids[3]),
        context=self.context)
    self.assertLen(result.items, 1)
    self.assertEqual(result.items[0].client_id, self.client_ids[3])

  def testSearchWithDisallowedClientIdsReturnsNothing(self):
    result = self.handler.Handle(
        client_plugin.ApiSearchClientsArgs(query=self.client_ids[1]),
        context=self.context)
    self.assertFalse(result.items)

    result = self.handler.Handle(
        client_plugin.ApiSearchClientsArgs(query=self.client_ids[2]),
        context=self.context)
    self.assertFalse(result.items)

  def testSearchOrder(self):
    self._Setup100Clients()

    result = self.handler.Handle(
        client_plugin.ApiSearchClientsArgs(
            query="label:foo", offset=0, count=1000),
        context=self.context)
    self.assertEqual([str(res.client_id) for res in result.items],
                     self.client_ids)

    result = []
    for offset, count in [(0, 10), (10, 40), (50, 25), (75, 500)]:
      result.extend(
          self.handler.Handle(
              client_plugin.ApiSearchClientsArgs(
                  query="label:foo", offset=offset, count=count),
              context=self.context).items)
    self.assertEqual([str(res.client_id) for res in result], self.client_ids)


class ApiInterrogateClientHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Test for ApiInterrogateClientHandler."""

  def setUp(self):
    super(ApiInterrogateClientHandlerTest, self).setUp()
    self.client_id = self.SetupClient(0)
    self.handler = client_plugin.ApiInterrogateClientHandler()

  def testInterrogateFlowIsStarted(self):
    self.assertEmpty(data_store.REL_DB.ReadAllFlowObjects(self.client_id))

    args = client_plugin.ApiInterrogateClientArgs(client_id=self.client_id)
    result = self.handler.Handle(args, context=self.context)

    results = data_store.REL_DB.ReadAllFlowObjects(self.client_id)
    self.assertLen(results, 1)
    self.assertEqual(result.operation_id, results[0].flow_id)
    self.assertEqual(results[0].creator, "api_test_user")


class ApiGetClientVersionTimesTestMixin(object):
  """Test mixin for ApiGetClientVersionTimes."""

  def setUp(self):
    super(ApiGetClientVersionTimesTestMixin, self).setUp()
    self.handler = client_plugin.ApiGetClientVersionTimesHandler()

  def testHandler(self):
    self._SetUpClient()
    args = client_plugin.ApiGetClientVersionTimesArgs(client_id=self.client_id)
    result = self.handler.Handle(args, context=self.context)

    self.assertLen(result.times, 3)
    self.assertEqual(result.times[0].AsSecondsSinceEpoch(), 100)
    self.assertEqual(result.times[1].AsSecondsSinceEpoch(), 45)
    self.assertEqual(result.times[2].AsSecondsSinceEpoch(), 42)


class ApiGetClientVersionTimesTest(ApiGetClientVersionTimesTestMixin,
                                   api_test_lib.ApiCallHandlerTest):
  """Test for ApiGetClientVersionTimes using the relational db."""

  def _SetUpClient(self):
    for time in [42, 45, 100]:
      with test_lib.FakeTime(time):
        self.client_id = self.SetupClient(0)


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
      self.assertEqual(ipaddr_obj, ipaddress.ip_address("100.1.1.100"))

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
          ipaddress.ip_address("2001:0db8:85a3:0000:0000:8a2e:0370:7334"))

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


@db_test_lib.TestDatabases()
class ApiSearchClientsHandlerTest(api_test_lib.ApiCallHandlerTest):

  def setUp(self):
    super(ApiSearchClientsHandlerTest, self).setUp()
    self.search_handler = client_plugin.ApiSearchClientsHandler()
    self.add_labels_handler = client_plugin.ApiAddClientsLabelsHandler()

  def _AddLabels(self, client_id, labels):
    args = client_plugin.ApiAddClientsLabelsArgs()
    args.client_ids = [client_id]
    args.labels = labels
    self.add_labels_handler.Handle(args=args, context=self.context)

  def testSearchByLabel(self):
    client_id = self.SetupClient(
        0, ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(13))
    self._AddLabels(client_id, labels=["foo"])
    api_result = self.search_handler.Handle(
        client_plugin.ApiSearchClientsArgs(query="label:foo"))
    self.assertLen(api_result.items, 1)
    self.assertEqual(api_result.items[0].client_id, client_id)
    self.assertEqual(api_result.items[0].last_seen_at,
                     rdfvalue.RDFDatetime.FromSecondsSinceEpoch(13))

  def testUnicode(self):
    client_a_id = self.SetupClient(0)
    self._AddLabels(client_a_id, labels=["gżegżółka"])

    client_b_id = self.SetupClient(1)
    self._AddLabels(client_b_id, labels=["orłosęp"])

    args_a = client_plugin.ApiSearchClientsArgs(
        query="label:gżegżółka", offset=0, count=128)

    result_a = self.search_handler.Handle(args_a, context=self.context)
    self.assertLen(result_a.items, 1)
    self.assertEqual(result_a.items[0].client_id, client_a_id)

    args_b = client_plugin.ApiSearchClientsArgs(
        query="label:orłosęp", offset=0, count=128)

    result_b = self.search_handler.Handle(args_b, context=self.context)
    self.assertLen(result_b.items, 1)
    self.assertEqual(result_b.items[0].client_id, client_b_id)

  def testUnicodeMultipleClients(self):
    client_a_id = self.SetupClient(0)
    self._AddLabels(client_a_id, labels=["ścierwnik", "krzyżówka"])

    client_b_id = self.SetupClient(1)
    self._AddLabels(client_b_id, labels=["nurogęś", "ścierwnik"])

    args = client_plugin.ApiSearchClientsArgs(
        query="label:ścierwnik", offset=0, count=1000)

    result = self.search_handler.Handle(args, context=self.context)
    result_client_ids = [item.client_id for item in result.items]
    self.assertCountEqual(result_client_ids, [client_a_id, client_b_id])

  def testUnicodeMultipleLabels(self):
    client_a_id = self.SetupClient(0)
    self._AddLabels(client_a_id, labels=["pustułka", "sokół", "raróg"])

    client_b_id = self.SetupClient(1)
    self._AddLabels(client_b_id, labels=["raróg", "żuraw", "białozór"])

    client_c_id = self.SetupClient(2)
    self._AddLabels(client_c_id, labels=["raróg", "sokół", "gołąb"])

    args = client_plugin.ApiSearchClientsArgs(
        query="label:raróg label:sokół", offset=0, count=1000)

    result = self.search_handler.Handle(args, context=self.context)
    result_client_ids = [item.client_id for item in result.items]
    self.assertCountEqual(result_client_ids, [client_a_id, client_c_id])

  def testUnicodeQuoted(self):
    client_id = self.SetupClient(0)
    self._AddLabels(
        client_id, labels=["dzięcioł białoszyi", "świergotek łąkowy"])

    args = client_plugin.ApiSearchClientsArgs(
        query="label:'dzięcioł białoszyi' label:'świergotek łąkowy'")

    result = self.search_handler.Handle(args, context=self.context)
    self.assertLen(result.items, 1)
    self.assertEqual(result.items[0].client_id, client_id)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
