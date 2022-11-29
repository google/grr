#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from typing import Text
from unittest import mock

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_core.lib.rdfvalues import client_stats as rdf_client_stats
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.util import collection
from grr_response_server import flow
from grr_response_server.databases import db
from grr_response_server.databases import db_test_utils
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import test_lib

CERT = rdf_crypto.RDFX509Cert(b"""-----BEGIN CERTIFICATE-----
MIIF7zCCA9egAwIBAgIBATANBgkqhkiG9w0BAQUFADA+MQswCQYDVQQGEwJVUzEM
MAoGA1UECBMDQ0FMMQswCQYDVQQHEwJTRjEUMBIGA1UEAxMLR1JSIFRlc3QgQ0Ew
HhcNMTEwNTI3MTIxNTExWhcNMTIwNTI2MTIxNTExWjBCMQswCQYDVQQGEwJVUzEM
MAoGA1UECBMDQ0FMMQswCQYDVQQHEwJTRjEYMBYGA1UEAxMPR1JSIFRlc3QgU2Vy
dmVyMIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAwUXBNzWSoEr88dGQ
qZWSwgJ+n/A/QQyNn/ZM57XsqI6IMO6plFmA+DZv2FkTTdniNPmhuL9mjWYA5yg4
KYMbz5igOiBoF9RBeIm2/v2Sg65VFoyCgJNgl3V34mpoDCHBYTi2A/OfoKeSQISb
UfMHsYhPHdGfhjk8dEuMo7MxjrtfAO3Y4QtjTiE07eNdoRQkFtzF0m9oSaytJ95c
BAe1eQ/2zcvxPvnF5yavR4fwKQtk8o1hc21XVG0JvqJ7da79C27cQQP3E/6EYzpN
pkh9n4berPBHV/oxlB2np4zKgXCQ4zDdiw1uEUY9+iFmVEuvzO2e5NJcfnu74sGb
oX+2a2/ph65sMZ2/NF8lRgetvIrtYUl15yypXmH3VobBYvpfGpab1rLt0J1HoVUh
V5Nsrdav0n8EQ+hln/sHz+G5rNe4ZSJbZ8w8b1TOwTENdzOYKAQH/NN9IrsbXNgE
8RHSHfPwibWnhfKS/fy7GO8qah/u2HPQ5S33gao409zbwS6c4sn0nAQhr5H6pHVD
iMLcBPFQ+w6zIk28hOv3GMa5XQtm8ONb/QhOLTbtB+ZCHKCw3bXASVDt7EwvnM/b
cSYS58wKmUQhH3unizXyihLhxC8ck/KMTkGnuGBC0Pz2d6YgcdL4BxAK6udSjSQQ
DB8sWYKJJrmlCnaN2E1eBbPV5PMCAwEAAaOB8zCB8DAJBgNVHRMEAjAAMBEGCWCG
SAGG+EIBAQQEAwIGQDArBglghkgBhvhCAQ0EHhYcVGlueUNBIEdlbmVyYXRlZCBD
ZXJ0aWZpY2F0ZTAdBgNVHQ4EFgQUywgOS64OISRSFNqpMpF83qXKDPIwbgYDVR0j
BGcwZYAUO4+Xefeqvq3W6/eaPxaNv8IHpcuhQqRAMD4xCzAJBgNVBAYTAlVTMQww
CgYDVQQIEwNDQUwxCzAJBgNVBAcTAlNGMRQwEgYDVQQDEwtHUlIgVGVzdCBDQYIJ
AIayxnA7Bp+3MAkGA1UdEgQCMAAwCQYDVR0RBAIwADANBgkqhkiG9w0BAQUFAAOC
AgEAY6z2VZdS83i6N88hVk3Y8qt0xNhP10+tfgsI7auPq2n3PsDNOLPvp2OcUcLI
csMQ/3GTI84uRm0GFnLMAc+A8BQZ14+3kPRju5jWe3KMfP1Ohz5Hm36Uf47tFhgV
VYnyIPwwCE1QPOgbnFt5jR+d3pjhx9TvjfeFKmavxMpxnDD2KWgGZfuE1UqC0DXm
rkimG2Q+dHUFBOMBUKzaklZsr7v4hlc+7XY1n5vRhiuczS9m5mVB05Cg4mrJFcVs
AUsxSuwgMhJqxuNaFw8qMmdkX7ujo5HAtwJqIi91Sdj8xNRqDysd1OagqL3Mx172
wTJu7ZIAURpw52AXxn3PpK5NS3NSvL/PE6SnpHCtfkxaHl/80W2oq7MjSaHbQt2g
8vYuwLEKYVhgEBzEK0p5AqDyabAn49bw9hfT10NElJ/tYEPCKZZwrARBHnpCxLeC
jJVIIMzPOczWnTDw92ls3l6+l075MOzXGo94GNlxt0/HLCQktl9cuF1APmRkiGUe
EaQA1dggxMyZGyZpYmEbrWCiEjKqfIXXnpyw5pxL5Rvoe4kYrQBvbJ1aaWJ87Pcz
gXJvjIkzp4x/MMAgdBOqJm5tJ4nhCHTbXWuIbYymPLn7hqXhyrDZwqnH7kQKPF2/
z5KjO8gWio6YOhsDwrketcBcIANMDYws2+TzrLs9ttuHNS0=
-----END CERTIFICATE-----""")


def _DaysSinceEpoch(days):
  return rdfvalue.RDFDatetime(
      rdfvalue.Duration.From(days, rdfvalue.DAYS).microseconds)


def _FlattenDicts(dicts):
  """Merges an iterable of dicts into one dict."""
  result = {}
  for dict_obj in dicts:
    result.update(dict_obj)
  return result


class DatabaseTestClientsMixin(object):
  """An abstract class for testing db.Database implementations.

  This mixin adds methods to test the handling of client data.
  """

  def testClientWriteToUnknownClient(self):
    d = self.db
    client_id = "C.fc413187fefa1dcf"

    with self.assertRaises(db.UnknownClientError) as context:
      d.WriteClientSnapshot(rdf_objects.ClientSnapshot(client_id=client_id))
    self.assertEqual(context.exception.client_id, client_id)

  def testKeywordWriteToUnknownClient(self):
    d = self.db
    client_id = "C.fc413187fefa1dcf"

    with self.assertRaises(db.UnknownClientError) as context:
      d.AddClientKeywords(client_id, ["keyword"])
    self.assertEqual(context.exception.client_id, client_id)

    d.RemoveClientKeyword(client_id, "test")

  # TODO(hanuszczak): Write tests that check whether labels respect foreign key
  # constraints on the `Users` table.

  def testLabelWriteToUnknownClient(self):
    d = self.db
    client_id = "C.fc413187fefa1dcf"

    self.db.WriteGRRUser("testowner")

    with self.assertRaises(db.UnknownClientError) as context:
      d.AddClientLabels(client_id, "testowner", ["label"])
    self.assertEqual(context.exception.client_id, client_id)

    d.RemoveClientLabels(client_id, "testowner", ["label"])

  def testAddRemoveClientLabelsWorkWithTuplesAsArgument(self):
    # See https://github.com/google/grr/issues/716 for an additional context.
    # AddClientlabels/ReadClientLabels require "labels" argument to be
    # iterable. DB implementation has to respect this assumption.
    d = self.db
    client_id = "C.fc413187fefa1dcf"

    self.db.WriteGRRUser("testowner")

    with self.assertRaises(db.UnknownClientError) as context:
      d.AddClientLabels(client_id, "testowner", ("label",))
    self.assertEqual(context.exception.client_id, client_id)

    d.RemoveClientLabels(client_id, "testowner", ("label",))

  def testClientMetadataInitialWrite(self):
    d = self.db

    client_id_1 = "C.fc413187fefa1dcf"
    # Typical initial FS enabled write
    d.WriteClientMetadata(client_id_1, fleetspeak_enabled=True)

    client_id_2 = "C.00413187fefa1dcf"
    # Typical initial non-FS write
    d.WriteClientMetadata(
        client_id_2,
        certificate=CERT,
        first_seen=rdfvalue.RDFDatetime(100000000),
        fleetspeak_enabled=False)

    res = d.MultiReadClientMetadata([client_id_1, client_id_2])
    self.assertLen(res, 2)

    m1 = res[client_id_1]
    self.assertIsInstance(m1, rdf_objects.ClientMetadata)
    self.assertTrue(m1.fleetspeak_enabled)

    m2 = res[client_id_2]
    self.assertIsInstance(m2, rdf_objects.ClientMetadata)
    self.assertFalse(m2.fleetspeak_enabled)
    self.assertEqual(m2.certificate, CERT)
    self.assertEqual(m2.first_seen, rdfvalue.RDFDatetime(100000000))

  def testClientMetadataSubsecond(self):
    client_id = "C.fc413187fefa1dcf"
    self.db.WriteClientMetadata(
        client_id,
        certificate=CERT,
        first_seen=rdfvalue.RDFDatetime(100000001),
        last_clock=rdfvalue.RDFDatetime(100000011),
        last_foreman=rdfvalue.RDFDatetime(100000021),
        last_ping=rdfvalue.RDFDatetime(100000031),
        fleetspeak_enabled=False)
    res = self.db.MultiReadClientMetadata([client_id])
    self.assertLen(res, 1)
    m1 = res[client_id]
    self.assertEqual(m1.first_seen, rdfvalue.RDFDatetime(100000001))
    self.assertEqual(m1.clock, rdfvalue.RDFDatetime(100000011))
    self.assertEqual(m1.last_foreman_time, rdfvalue.RDFDatetime(100000021))
    self.assertEqual(m1.ping, rdfvalue.RDFDatetime(100000031))

  def testClientMetadataPing(self):
    d = self.db

    client_id = db_test_utils.InitializeClient(self.db)

    # Typical update on client ping.
    d.WriteClientMetadata(
        client_id,
        fleetspeak_enabled=True,
        last_ping=rdfvalue.RDFDatetime(200000000000),
        last_clock=rdfvalue.RDFDatetime(210000000000),
        last_ip=rdf_client_network.NetworkAddress(
            human_readable_address="8.8.8.8"),
        last_foreman=rdfvalue.RDFDatetime(220000000000))

    res = d.MultiReadClientMetadata([client_id])
    self.assertLen(res, 1)
    m1 = res[client_id]
    self.assertIsInstance(m1, rdf_objects.ClientMetadata)
    self.assertTrue(m1.fleetspeak_enabled)
    self.assertEqual(m1.ping, rdfvalue.RDFDatetime(200000000000))
    self.assertEqual(m1.clock, rdfvalue.RDFDatetime(210000000000))
    self.assertEqual(
        m1.ip,
        rdf_client_network.NetworkAddress(human_readable_address="8.8.8.8"))
    self.assertEqual(m1.last_foreman_time, rdfvalue.RDFDatetime(220000000000))

  def testClientMetadataValidatesIP(self):
    d = self.db
    client_id = "C.fc413187fefa1dcf"
    with self.assertRaises(TypeError):
      d.WriteClientMetadata(
          client_id, fleetspeak_enabled=True, last_ip="127.0.0.1")

  def testReadAllClientIDsEmpty(self):
    result = list(self.db.ReadAllClientIDs())
    self.assertEmpty(result)

  def testReadAllClientIDsSome(self):
    client_a_id = db_test_utils.InitializeClient(self.db)
    client_b_id = db_test_utils.InitializeClient(self.db)
    client_c_id = db_test_utils.InitializeClient(self.db)

    client_ids = list(self.db.ReadAllClientIDs())
    self.assertLen(client_ids, 1)
    self.assertCountEqual(client_ids[0],
                          [client_a_id, client_b_id, client_c_id])

  def testReadAllClientIDsNotEvenlyDivisibleByBatchSize(self):
    client_a_id = db_test_utils.InitializeClient(self.db)
    client_b_id = db_test_utils.InitializeClient(self.db)
    client_c_id = db_test_utils.InitializeClient(self.db)

    client_ids = list(self.db.ReadAllClientIDs(batch_size=2))
    self.assertEqual([len(batch) for batch in client_ids], [2, 1])
    self.assertCountEqual(
        collection.Flatten(client_ids), [client_a_id, client_b_id, client_c_id])

  def testReadAllClientIDsEvenlyDivisibleByBatchSize(self):
    client_a_id = db_test_utils.InitializeClient(self.db)
    client_b_id = db_test_utils.InitializeClient(self.db)
    client_c_id = db_test_utils.InitializeClient(self.db)
    client_d_id = db_test_utils.InitializeClient(self.db)

    client_ids = list(self.db.ReadAllClientIDs(batch_size=2))
    self.assertEqual([len(batch) for batch in client_ids], [2, 2])
    self.assertCountEqual(
        collection.Flatten(client_ids),
        [client_a_id, client_b_id, client_c_id, client_d_id])

  def testReadAllClientIDsFilterLastPing(self):
    self.db.WriteClientMetadata("C.0000000000000001", fleetspeak_enabled=True)
    self.db.WriteClientMetadata(
        "C.0000000000000002",
        last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(2))
    self.db.WriteClientMetadata(
        "C.0000000000000003",
        last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3))
    self.db.WriteClientMetadata(
        "C.0000000000000004",
        last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(4))
    client_ids = self.db.ReadAllClientIDs(
        min_last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3))
    self.assertCountEqual(
        collection.Flatten(client_ids),
        ["C.0000000000000003", "C.0000000000000004"])

  def testReadClientLastPings_ResultsDivisibleByBatchSize(self):
    client_ids = self._WriteClientLastPingData()
    (client_id5, client_id6, client_id7, client_id8, client_id9,
     client_id10) = client_ids[4:]

    results = list(
        self.db.ReadClientLastPings(
            min_last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3),
            batch_size=3))

    self.assertEqual([len(batch) for batch in results], [3, 3])

    self.assertEqual(
        _FlattenDicts(results), {
            client_id5: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3),
            client_id6: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3),
            client_id7: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(4),
            client_id8: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(4),
            client_id9: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(5),
            client_id10: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(5),
        })

  def testReadClientLastPings_ResultsNotDivisibleByBatchSize(self):
    client_ids = self._WriteClientLastPingData()
    (client_id5, client_id6, client_id7, client_id8, client_id9,
     client_id10) = client_ids[4:]

    results = list(
        self.db.ReadClientLastPings(
            min_last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3),
            batch_size=4))

    self.assertEqual([len(batch) for batch in results], [4, 2])

    self.assertEqual(
        _FlattenDicts(results), {
            client_id5: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3),
            client_id6: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3),
            client_id7: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(4),
            client_id8: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(4),
            client_id9: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(5),
            client_id10: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(5),
        })

  def testReadClientLastPings_NoFilter(self):
    client_ids = self._WriteClientLastPingData()
    (client_id1, client_id2, client_id3, client_id4, client_id5, client_id6,
     client_id7, client_id8, client_id9, client_id10) = client_ids

    self.assertEqual(
        list(self.db.ReadClientLastPings()), [{
            client_id1: None,
            client_id2: None,
            client_id3: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(2),
            client_id4: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(2),
            client_id5: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3),
            client_id6: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3),
            client_id7: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(4),
            client_id8: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(4),
            client_id9: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(5),
            client_id10: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(5),
        }])

  def testReadClientLastPings_AllFiltersFleetspeak(self):
    client_ids = self._WriteClientLastPingData()
    client_id6 = client_ids[5]
    client_id8 = client_ids[7]

    actual_data = self.db.ReadClientLastPings(
        min_last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3),
        max_last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(4),
        fleetspeak_enabled=True)
    expected_data = [{
        client_id6: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3),
        client_id8: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(4),
    }]
    self.assertEqual(list(actual_data), expected_data)

  def testReadClientLastPings_AllFiltersNoFleetspeak(self):
    client_ids = self._WriteClientLastPingData()
    client_id5 = client_ids[4]
    client_id7 = client_ids[6]

    actual_data = self.db.ReadClientLastPings(
        min_last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3),
        max_last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(4),
        fleetspeak_enabled=False)
    expected_data = [{
        client_id5: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3),
        client_id7: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(4),
    }]
    self.assertEqual(list(actual_data), expected_data)

  def testReadClientLastPings_MinPingFleetspeakFilters(self):
    client_ids = self._WriteClientLastPingData()
    client_id5 = client_ids[4]
    client_id7 = client_ids[6]
    client_id9 = client_ids[8]

    actual_data = self.db.ReadClientLastPings(
        min_last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3),
        fleetspeak_enabled=False)
    expected_data = [{
        client_id5: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3),
        client_id7: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(4),
        client_id9: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(5),
    }]
    self.assertEqual(list(actual_data), expected_data)

  def testReadClientLastPings_MaxPingFleetspeakFilters(self):
    client_ids = self._WriteClientLastPingData()
    client_id2 = client_ids[1]
    client_id4 = client_ids[3]
    client_id6 = client_ids[5]

    actual_data = self.db.ReadClientLastPings(
        max_last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3),
        fleetspeak_enabled=True)
    expected_data = [{
        client_id2: None,
        client_id4: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(2),
        client_id6: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3),
    }]
    self.assertEqual(list(actual_data), expected_data)

  def _WriteClientLastPingData(self):
    """Writes test data for ReadClientLastPings() tests."""
    client_ids = tuple("C.00000000000000%02d" % i for i in range(1, 11))
    (client_id1, client_id2, client_id3, client_id4, client_id5, client_id6,
     client_id7, client_id8, client_id9, client_id10) = client_ids

    self.db.WriteClientMetadata(client_id1, fleetspeak_enabled=False)
    self.db.WriteClientMetadata(client_id2, fleetspeak_enabled=True)
    self.db.WriteClientMetadata(
        client_id3, last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(2))
    self.db.WriteClientMetadata(
        client_id4,
        last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(2),
        fleetspeak_enabled=True)
    self.db.WriteClientMetadata(
        client_id5, last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3))
    self.db.WriteClientMetadata(
        client_id6,
        last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3),
        fleetspeak_enabled=True)
    self.db.WriteClientMetadata(
        client_id7, last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(4))
    self.db.WriteClientMetadata(
        client_id8,
        last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(4),
        fleetspeak_enabled=True)
    self.db.WriteClientMetadata(
        client_id9, last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(5))
    self.db.WriteClientMetadata(
        client_id10,
        last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(5),
        fleetspeak_enabled=True)

    return client_ids

  def _SetUpReadClientSnapshotHistoryTest(self):
    d = self.db

    self.client_id = db_test_utils.InitializeClient(self.db)

    timestamps = [rdfvalue.RDFDatetime.Now()]

    client = rdf_objects.ClientSnapshot(client_id=self.client_id, kernel="12.3")
    client.knowledge_base.fqdn = "test1234.examples.com"
    d.WriteClientSnapshot(client)
    timestamps.append(d.ReadClientSnapshot(self.client_id).timestamp)

    timestamps.append(rdfvalue.RDFDatetime.Now())

    client.kernel = "12.4"
    d.WriteClientSnapshot(client)
    timestamps.append(d.ReadClientSnapshot(self.client_id).timestamp)

    timestamps.append(rdfvalue.RDFDatetime.Now())

    return timestamps

  def testReadClientSnapshotHistory(self):
    d = self.db

    self._SetUpReadClientSnapshotHistoryTest()

    hist = d.ReadClientSnapshotHistory(self.client_id)
    self.assertLen(hist, 2)
    self.assertIsInstance(hist[0], rdf_objects.ClientSnapshot)
    self.assertIsInstance(hist[1], rdf_objects.ClientSnapshot)
    self.assertGreater(hist[0].timestamp, hist[1].timestamp)
    self.assertIsInstance(hist[0].timestamp, rdfvalue.RDFDatetime)
    self.assertEqual(hist[0].kernel, "12.4")
    self.assertEqual(hist[1].kernel, "12.3")

  def testReadClientSnapshotHistoryWithEmptyTimerange(self):
    d = self.db

    self._SetUpReadClientSnapshotHistoryTest()

    hist = d.ReadClientSnapshotHistory(self.client_id, timerange=(None, None))
    self.assertLen(hist, 2)
    self.assertEqual(hist[0].kernel, "12.4")
    self.assertEqual(hist[1].kernel, "12.3")

  def testReadClientSnapshotHistoryWithTimerangeWithBothFromTo(self):
    d = self.db

    ts = self._SetUpReadClientSnapshotHistoryTest()

    hist = d.ReadClientSnapshotHistory(self.client_id, timerange=(ts[0], ts[2]))
    self.assertLen(hist, 1)
    self.assertEqual(hist[0].kernel, "12.3")

    hist = d.ReadClientSnapshotHistory(self.client_id, timerange=(ts[2], ts[4]))
    self.assertLen(hist, 1)
    self.assertEqual(hist[0].kernel, "12.4")

    hist = d.ReadClientSnapshotHistory(self.client_id, timerange=(ts[0], ts[4]))
    self.assertLen(hist, 2)
    self.assertEqual(hist[0].kernel, "12.4")
    self.assertEqual(hist[1].kernel, "12.3")

  def testReadClientSnapshotHistoryWithTimerangeWithFromOnly(self):
    d = self.db

    ts = self._SetUpReadClientSnapshotHistoryTest()

    hist = d.ReadClientSnapshotHistory(self.client_id, timerange=(ts[0], None))
    self.assertLen(hist, 2)
    self.assertEqual(hist[0].kernel, "12.4")
    self.assertEqual(hist[1].kernel, "12.3")

    hist = d.ReadClientSnapshotHistory(self.client_id, timerange=(ts[2], None))
    self.assertLen(hist, 1)
    self.assertEqual(hist[0].kernel, "12.4")

    hist = d.ReadClientSnapshotHistory(self.client_id, timerange=(ts[4], None))
    self.assertEmpty(hist)

  def testReadClientSnapshotHistoryWithTimerangeWithToOnly(self):
    d = self.db

    ts = self._SetUpReadClientSnapshotHistoryTest()

    hist = d.ReadClientSnapshotHistory(self.client_id, timerange=(None, ts[0]))
    self.assertEmpty(hist)

    hist = d.ReadClientSnapshotHistory(self.client_id, timerange=(None, ts[2]))
    self.assertLen(hist, 1)
    self.assertEqual(hist[0].kernel, "12.3")

    hist = d.ReadClientSnapshotHistory(self.client_id, timerange=(None, ts[4]))
    self.assertLen(hist, 2)
    self.assertEqual(hist[0].kernel, "12.4")
    self.assertEqual(hist[1].kernel, "12.3")

  def testReadClientSnapshotHistoryWithTimerangeEdgeCases(self):
    # Timerange should work as [from, to]. I.e. "from" is inclusive and "to"
    # is inclusive.

    d = self.db

    ts = self._SetUpReadClientSnapshotHistoryTest()

    hist = d.ReadClientSnapshotHistory(self.client_id, timerange=(ts[1], ts[1]))
    self.assertLen(hist, 1)
    self.assertEqual(hist[0].kernel, "12.3")

    hist = d.ReadClientSnapshotHistory(self.client_id, timerange=(ts[1], ts[2]))
    self.assertLen(hist, 1)
    self.assertEqual(hist[0].kernel, "12.3")

    hist = d.ReadClientSnapshotHistory(self.client_id, timerange=(ts[1], ts[3]))
    self.assertLen(hist, 2)
    self.assertEqual(hist[0].kernel, "12.4")
    self.assertEqual(hist[1].kernel, "12.3")

  def testWriteClientSnapshotHistory(self):
    client_id = db_test_utils.InitializeClient(self.db)

    client_a = rdf_objects.ClientSnapshot(client_id=client_id)
    client_a.kernel = "1.2.3"
    client_a.startup_info.client_info.client_version = 42
    client_a.timestamp = rdfvalue.RDFDatetime.FromHumanReadable("2010-01-01")

    client_b = rdf_objects.ClientSnapshot(client_id=client_id)
    client_b.kernel = "4.5.6"
    client_b.startup_info.client_info.client_version = 108
    client_b.timestamp = rdfvalue.RDFDatetime.FromHumanReadable("2010-02-01")

    client_c = rdf_objects.ClientSnapshot(client_id=client_id)
    client_c.kernel = "7.8.9"
    client_c.startup_info.client_info.client_version = 707
    client_c.timestamp = rdfvalue.RDFDatetime.FromHumanReadable("2010-03-01")

    self.db.WriteClientSnapshotHistory([client_a, client_b, client_c])

    # Check whether the client history has been recorded correctly.
    history = self.db.ReadClientSnapshotHistory(client_id)
    self.assertLen(history, 3)

    self.assertEqual(history[0].kernel, "7.8.9")
    self.assertEqual(history[0].startup_info.client_info.client_version, 707)
    self.assertEqual(history[0].timestamp,
                     rdfvalue.RDFDatetime.FromHumanReadable("2010-03-01"))

    self.assertEqual(history[1].kernel, "4.5.6")
    self.assertEqual(history[1].startup_info.client_info.client_version, 108)
    self.assertEqual(history[1].timestamp,
                     rdfvalue.RDFDatetime.FromHumanReadable("2010-02-01"))

    self.assertEqual(history[2].kernel, "1.2.3")
    self.assertEqual(history[2].startup_info.client_info.client_version, 42)
    self.assertEqual(history[2].timestamp,
                     rdfvalue.RDFDatetime.FromHumanReadable("2010-01-01"))

    # Check whether the snapshot history has been recorded correctly.
    history = self.db.ReadClientStartupInfoHistory(client_id)
    self.assertLen(history, 3)

    self.assertEqual(history[0].client_info.client_version, 707)
    self.assertEqual(history[0].timestamp,
                     rdfvalue.RDFDatetime.FromHumanReadable("2010-03-01"))

    self.assertEqual(history[1].client_info.client_version, 108)
    self.assertEqual(history[1].timestamp,
                     rdfvalue.RDFDatetime.FromHumanReadable("2010-02-01"))

    self.assertEqual(history[2].client_info.client_version, 42)
    self.assertEqual(history[2].timestamp,
                     rdfvalue.RDFDatetime.FromHumanReadable("2010-01-01"))

  def testWriteClientSnapshotHistoryUpdatesLastTimestampIfNotSet(self):
    client_id = db_test_utils.InitializeClient(self.db)

    client_new = rdf_objects.ClientSnapshot(client_id=client_id)
    client_new.kernel = "1.0.0"
    client_new.timestamp = rdfvalue.RDFDatetime.FromHumanReadable("2010-01-01")
    self.db.WriteClientSnapshotHistory([client_new])

    info = self.db.ReadClientFullInfo(client_id)
    self.assertEqual(info.last_snapshot.kernel, "1.0.0")
    self.assertEqual(info.last_snapshot.timestamp,
                     rdfvalue.RDFDatetime.FromHumanReadable("2010-01-01"))
    self.assertEqual(info.last_startup_info.timestamp,
                     rdfvalue.RDFDatetime.FromHumanReadable("2010-01-01"))

  def testWriteClientSnapshotHistoryUpdatesLastTimestampIfNewer(self):
    client_id = db_test_utils.InitializeClient(self.db)

    client_old = rdf_objects.ClientSnapshot(client_id=client_id)
    client_old.kernel = "1.0.0"
    self.db.WriteClientSnapshot(client_old)

    old_timestamp = self.db.ReadClientSnapshot(client_id).timestamp

    client_new = rdf_objects.ClientSnapshot(client_id=client_id)
    client_new.kernel = "2.0.0"
    client_new.timestamp = rdfvalue.RDFDatetime.Now()
    self.db.WriteClientSnapshotHistory([client_new])

    info = self.db.ReadClientFullInfo(client_id)
    self.assertEqual(info.last_snapshot.kernel, "2.0.0")
    self.assertGreater(info.last_snapshot.timestamp, old_timestamp)
    self.assertGreater(info.last_startup_info.timestamp, old_timestamp)

  def testWriteClientSnapshotHistoryDoesNotUpdateLastTimestampIfOlder(self):
    client_id = db_test_utils.InitializeClient(self.db)

    client_new = rdf_objects.ClientSnapshot(client_id=client_id)
    client_new.kernel = "2.0.0"
    self.db.WriteClientSnapshot(client_new)

    new_timestamp = self.db.ReadClientSnapshot(client_id).timestamp

    client_old = rdf_objects.ClientSnapshot(client_id=client_id)
    client_old.kernel = "1.0.0"
    client_old.timestamp = new_timestamp - rdfvalue.Duration.From(
        1, rdfvalue.DAYS)
    self.db.WriteClientSnapshotHistory([client_old])

    info = self.db.ReadClientFullInfo(client_id)
    self.assertEqual(info.last_snapshot.kernel, "2.0.0")
    self.assertEqual(info.last_snapshot.timestamp, new_timestamp)
    self.assertEqual(info.last_startup_info.timestamp, new_timestamp)

  def testWriteClientSnapshotHistoryUpdatesOnlyLastClientTimestamp(self):
    client_id = db_test_utils.InitializeClient(self.db)

    client_old = rdf_objects.ClientSnapshot(client_id=client_id)
    client_old.kernel = "1.0.0"
    client_old.startup_info.client_info.client_name = "foo"
    self.db.WriteClientSnapshot(client_old)

    old_timestamp = self.db.ReadClientSnapshot(client_id).timestamp

    startup_info = rdf_client.StartupInfo()
    startup_info.client_info.client_name = "bar"
    self.db.WriteClientStartupInfo(client_id, startup_info)

    startup_timestamp = self.db.ReadClientStartupInfo(client_id).timestamp

    client_new = rdf_objects.ClientSnapshot(client_id=client_id)
    client_new.kernel = "2.0.0"
    client_new.startup_info.client_info.client_name = "baz"
    client_new.timestamp = rdfvalue.RDFDatetime.Lerp(
        0.5, start_time=old_timestamp, end_time=startup_timestamp)
    self.db.WriteClientSnapshotHistory([client_new])

    info = self.db.ReadClientFullInfo(client_id)
    last_snapshot = info.last_snapshot
    last_startup_info = info.last_startup_info
    self.assertEqual(last_snapshot.kernel, "2.0.0")
    self.assertEqual(last_snapshot.startup_info.client_info.client_name, "baz")
    self.assertEqual(last_snapshot.timestamp, client_new.timestamp)
    self.assertEqual(last_startup_info.client_info.client_name, "bar")
    self.assertEqual(last_startup_info.timestamp, startup_timestamp)

  def testWriteClientSnapshotHistoryRaiseTypeError(self):
    client = rdf_objects.ClientMetadata()
    client.os_version = "16.04"
    client.timestamp = rdfvalue.RDFDatetime.FromHumanReadable("2010-04-10")

    with self.assertRaisesRegex(TypeError, "Expected"):
      self.db.WriteClientSnapshotHistory([client])

  def testWriteClientSnapshotHistoryRaiseValueErrorOnEmpty(self):
    with self.assertRaisesRegex(ValueError, "empty"):
      self.db.WriteClientSnapshotHistory([])

  def testWriteClientSnapshotHistoryRaiseValueErrorOnNonUniformIds(self):
    client_id_a = db_test_utils.InitializeClient(self.db)
    client_id_b = db_test_utils.InitializeClient(self.db)

    client_a = rdf_objects.ClientSnapshot(client_id=client_id_a)
    client_a.timestamp = rdfvalue.RDFDatetime.FromHumanReadable("2010-05-12")

    client_b = rdf_objects.ClientSnapshot(client_id=client_id_b)
    client_b.timestamp = rdfvalue.RDFDatetime.FromHumanReadable("2010-06-12")

    with self.assertRaisesRegex(ValueError, "client id"):
      self.db.WriteClientSnapshotHistory([client_a, client_b])

  def testWriteClientSnapshotHistoryRaiseAttributeError(self):
    client_id = db_test_utils.InitializeClient(self.db)

    client = rdf_objects.ClientSnapshot(client_id=client_id)
    client.kernel = "1.2.3"
    client.startup_info.client_info.client_version = 42

    with self.assertRaisesRegex(AttributeError, "timestamp"):
      self.db.WriteClientSnapshotHistory([client])

  def testWriteClientSnapshotHistoryRaiseOnNonExistingClient(self):
    client_id = "C.0000000000000000"

    client = rdf_objects.ClientSnapshot(client_id=client_id)
    client.kernel = "1.2.3"
    client.timestamp = rdfvalue.RDFDatetime.FromHumanReadable("2001-01-01")

    with self.assertRaises(db.UnknownClientError) as context:
      self.db.WriteClientSnapshotHistory([client])
    self.assertEqual(context.exception.client_id, client_id)

  def testClientStartupInfo(self):
    """StartupInfo is written to a separate table, make sure the merge works."""
    d = self.db

    client_id = db_test_utils.InitializeClient(self.db)

    client = rdf_objects.ClientSnapshot(client_id=client_id, kernel="12.3")
    client.startup_info = rdf_client.StartupInfo(boot_time=123)
    client.knowledge_base.fqdn = "test1234.examples.com"
    d.WriteClientSnapshot(client)

    client = d.ReadClientSnapshot(client_id)
    self.assertEqual(client.startup_info.boot_time, 123)

    client.kernel = "12.4"
    client.startup_info = rdf_client.StartupInfo(boot_time=124)
    d.WriteClientSnapshot(client)

    client.kernel = "12.5"
    client.startup_info = rdf_client.StartupInfo(boot_time=125)
    d.WriteClientSnapshot(client)

    hist = d.ReadClientSnapshotHistory(client_id)
    self.assertLen(hist, 3)
    startup_infos = [cl.startup_info for cl in hist]
    self.assertEqual([si.boot_time for si in startup_infos], [125, 124, 123])

    # StartupInfos written using WriteClient show up in the StartupInfoHistory.
    history = d.ReadClientStartupInfoHistory(client_id)
    self.assertLen(history, 3)
    self.assertEqual(startup_infos, history)

  def testClientSummary(self):
    d = self.db

    client_id_1 = db_test_utils.InitializeClient(self.db)
    client_id_2 = db_test_utils.InitializeClient(self.db)
    client_id_3 = db_test_utils.InitializeClient(self.db)

    d.WriteClientSnapshot(
        rdf_objects.ClientSnapshot(
            client_id=client_id_1,
            knowledge_base=rdf_client.KnowledgeBase(
                fqdn="test1234.examples.com"),
            kernel="12.3"))
    d.WriteClientSnapshot(
        rdf_objects.ClientSnapshot(
            client_id=client_id_1,
            knowledge_base=rdf_client.KnowledgeBase(
                fqdn="test1234.examples.com"),
            kernel="12.4"))

    d.WriteClientSnapshot(
        rdf_objects.ClientSnapshot(
            client_id=client_id_2,
            knowledge_base=rdf_client.KnowledgeBase(
                fqdn="test1235.examples.com"),
            kernel="12.4"))

    hist = d.ReadClientSnapshotHistory(client_id_1)
    self.assertLen(hist, 2)

    # client_3 should be excluded - no snapshot yet
    res = d.MultiReadClientSnapshot([client_id_1, client_id_2, client_id_3])
    self.assertLen(res, 3)
    self.assertIsInstance(res[client_id_1], rdf_objects.ClientSnapshot)
    self.assertIsInstance(res[client_id_2], rdf_objects.ClientSnapshot)
    self.assertIsInstance(res[client_id_1].timestamp, rdfvalue.RDFDatetime)
    self.assertIsNotNone(res[client_id_2].timestamp)
    self.assertEqual(res[client_id_1].knowledge_base.fqdn,
                     "test1234.examples.com")
    self.assertEqual(res[client_id_1].kernel, "12.4")
    self.assertEqual(res[client_id_2].knowledge_base.fqdn,
                     "test1235.examples.com")
    self.assertFalse(res[client_id_3])

  def testMultiReadClientSnapshotInfoWithEmptyList(self):
    d = self.db

    self.assertEqual(d.MultiReadClientSnapshot([]), {})

  def testClientValidates(self):
    d = self.db

    client_id = db_test_utils.InitializeClient(self.db)
    with self.assertRaises(TypeError):
      d.WriteClientSnapshot(client_id)

  def testClientKeywords(self):
    d = self.db
    client_id_1 = db_test_utils.InitializeClient(self.db)
    client_id_2 = db_test_utils.InitializeClient(self.db)
    client_id_3 = db_test_utils.InitializeClient(self.db)

    # Typical keywords are usernames and prefixes of hostnames.
    d.AddClientKeywords(client_id_1, [
        "joe", "machine.test.example1.com", "machine.test.example1",
        "machine.test", "machine", "🚀"
    ])
    d.AddClientKeywords(client_id_2, [
        "fred", "machine.test.example2.com", "machine.test.example2",
        "machine.test", "machine", "🚀🚀"
    ])
    d.AddClientKeywords(client_id_3, ["foo", "bar", "baz"])

    res = d.ListClientsForKeywords(["fred", "machine", "missing"])
    self.assertEqual(res["fred"], [client_id_2])
    self.assertCountEqual(res["machine"], [client_id_1, client_id_2])
    self.assertEqual(res["missing"], [])

    for kw, client_id in [("🚀", client_id_1), ("🚀🚀", client_id_2)]:
      res = d.ListClientsForKeywords([kw])
      self.assertEqual(
          res[kw], [client_id],
          "Expected [%s] when reading keyword %s, got %s" %
          (client_id, kw, res[kw]))

  def testClientKeywordsTimeRanges(self):
    d = self.db
    client_id = db_test_utils.InitializeClient(self.db)

    d.AddClientKeywords(client_id, ["hostname1"])
    change_time = rdfvalue.RDFDatetime.Now()
    d.AddClientKeywords(client_id, ["hostname2"])

    res = d.ListClientsForKeywords(["hostname1", "hostname2"],
                                   start_time=change_time)
    self.assertEqual(res["hostname1"], [])
    self.assertEqual(res["hostname2"], [client_id])

  def testRemoveClientKeyword(self):
    d = self.db
    client_id = db_test_utils.InitializeClient(self.db)
    temporary_kw = "investigation42"
    d.AddClientKeywords(client_id, [
        "joe", "machine.test.example.com", "machine.test.example",
        "machine.test", temporary_kw
    ])
    self.assertEqual(
        d.ListClientsForKeywords([temporary_kw])[temporary_kw], [client_id])
    d.RemoveClientKeyword(client_id, temporary_kw)
    self.assertEqual(d.ListClientsForKeywords([temporary_kw])[temporary_kw], [])
    self.assertEqual(d.ListClientsForKeywords(["joe"])["joe"], [client_id])

  def testClientLabels(self):
    d = self.db

    self.db.WriteGRRUser("owner1")
    self.db.WriteGRRUser("owner2")
    client_id = db_test_utils.InitializeClient(self.db)

    self.assertEqual(d.ReadClientLabels(client_id), [])

    d.AddClientLabels(client_id, "owner1", ["label1🚀"])
    d.AddClientLabels(client_id, "owner2", ["label2", "label🚀3"])

    all_labels = [
        rdf_objects.ClientLabel(name="label1🚀", owner="owner1"),
        rdf_objects.ClientLabel(name="label2", owner="owner2"),
        rdf_objects.ClientLabel(name="label🚀3", owner="owner2")
    ]

    self.assertEqual(d.ReadClientLabels(client_id), all_labels)
    self.assertEqual(d.ReadClientLabels("C.0000000000000002"), [])

    # Can't hurt to insert this one again.
    d.AddClientLabels(client_id, "owner1", ["label1🚀"])
    self.assertEqual(d.ReadClientLabels(client_id), all_labels)

    d.RemoveClientLabels(client_id, "owner1", ["does not exist"])
    self.assertEqual(d.ReadClientLabels(client_id), all_labels)

    # Label3 is actually owned by owner2.
    d.RemoveClientLabels(client_id, "owner1", ["label🚀3"])
    self.assertEqual(d.ReadClientLabels(client_id), all_labels)

    d.RemoveClientLabels(client_id, "owner2", ["label🚀3"])
    self.assertEqual(
        d.ReadClientLabels(client_id), [
            rdf_objects.ClientLabel(name="label1🚀", owner="owner1"),
            rdf_objects.ClientLabel(name="label2", owner="owner2"),
        ])

  def testClientLabelsUnicode(self):
    d = self.db

    self.db.WriteGRRUser("owner1")
    self.db.WriteGRRUser("owner2")
    client_id = db_test_utils.InitializeClient(self.db)

    self.assertEqual(d.ReadClientLabels(client_id), [])

    d.AddClientLabels(client_id, "owner1", ["🚀🍰1"])
    d.AddClientLabels(client_id, "owner2", ["🚀🍰2"])
    d.AddClientLabels(client_id, "owner2", ["🚀🍰3"])

    all_labels = [
        rdf_objects.ClientLabel(name="🚀🍰1", owner="owner1"),
        rdf_objects.ClientLabel(name="🚀🍰2", owner="owner2"),
        rdf_objects.ClientLabel(name="🚀🍰3", owner="owner2")
    ]

    self.assertEqual(d.ReadClientLabels(client_id), all_labels)

    d.RemoveClientLabels(client_id, "owner1", ["does not exist"])
    self.assertEqual(d.ReadClientLabels(client_id), all_labels)

    # This label is actually owned by owner2.
    d.RemoveClientLabels(client_id, "owner1", ["🚀🍰3"])
    self.assertEqual(d.ReadClientLabels(client_id), all_labels)

    d.RemoveClientLabels(client_id, "owner2", ["🚀🍰3"])
    self.assertEqual(
        d.ReadClientLabels(client_id), [
            rdf_objects.ClientLabel(name="🚀🍰1", owner="owner1"),
            rdf_objects.ClientLabel(name="🚀🍰2", owner="owner2")
        ])

  def testLongClientLabelCanBeSaved(self):
    label = "x" + "🚀" * (db.MAX_LABEL_LENGTH - 2) + "x"
    d = self.db
    self.db.WriteGRRUser("owner1")
    client_id = db_test_utils.InitializeClient(self.db)
    d.AddClientLabels(client_id, "owner1", [label])
    self.assertEqual(
        d.ReadClientLabels(client_id), [
            rdf_objects.ClientLabel(name=label, owner="owner1"),
        ])

  def testTooLongClientLabelRaises(self):
    label = "a" * (db.MAX_LABEL_LENGTH + 1)
    d = self.db
    self.db.WriteGRRUser("owner1")
    client_id = db_test_utils.InitializeClient(self.db)
    with self.assertRaises(ValueError):
      d.AddClientLabels(client_id, "owner1", [label])

  def testReadAllLabelsReturnsLabelsFromSingleClient(self):
    d = self.db

    self.db.WriteGRRUser("owner1🚀")
    client_id = db_test_utils.InitializeClient(self.db)

    d.AddClientLabels(client_id, "owner1🚀", ["foo🚀"])

    all_labels = d.ReadAllClientLabels()
    self.assertCountEqual(all_labels, ["foo🚀"])

  def testReadAllLabelsReturnsLabelsFromMultipleClients(self):
    d = self.db

    self.db.WriteGRRUser("owner1")
    self.db.WriteGRRUser("owner2")
    client_id_1 = db_test_utils.InitializeClient(self.db)
    client_id_2 = db_test_utils.InitializeClient(self.db)

    d.AddClientLabels(client_id_1, "owner1", ["foo"])
    d.AddClientLabels(client_id_2, "owner1", ["foo"])
    d.AddClientLabels(client_id_1, "owner2", ["bar"])
    d.AddClientLabels(client_id_2, "owner2", ["bar"])

    self.assertCountEqual(d.ReadAllClientLabels(), ["foo", "bar"])

  def testReadClientStartupInfo(self):
    d = self.db

    client_id = db_test_utils.InitializeClient(self.db)

    d.WriteClientStartupInfo(client_id, rdf_client.StartupInfo(boot_time=1337))
    d.WriteClientStartupInfo(client_id, rdf_client.StartupInfo(boot_time=2000))

    last_is = d.ReadClientStartupInfo(client_id)
    self.assertIsInstance(last_is, rdf_client.StartupInfo)
    self.assertEqual(last_is.boot_time, 2000)
    self.assertIsInstance(last_is.timestamp, rdfvalue.RDFDatetime)

    md = self.db.ReadClientMetadata(client_id)
    self.assertEqual(md.startup_info_timestamp, last_is.timestamp)

  def testReadClientStartupInfoNone(self):
    client_id = db_test_utils.InitializeClient(self.db)
    self.assertIsNone(self.db.ReadClientStartupInfo(client_id))

  def testReadClientStartupInfoHistory(self):
    d = self.db

    client_id = db_test_utils.InitializeClient(self.db)
    d.WriteClientStartupInfo(client_id, rdf_client.StartupInfo(boot_time=1))
    d.WriteClientStartupInfo(client_id, rdf_client.StartupInfo(boot_time=2))
    d.WriteClientStartupInfo(client_id, rdf_client.StartupInfo(boot_time=3))

    hist = d.ReadClientStartupInfoHistory(client_id)
    self.assertLen(hist, 3)
    self.assertEqual([si.boot_time for si in hist], [3, 2, 1])
    self.assertIsInstance(hist[0].timestamp, rdfvalue.RDFDatetime)
    self.assertGreater(hist[0].timestamp, hist[1].timestamp)
    self.assertGreater(hist[1].timestamp, hist[2].timestamp)

    md = self.db.ReadClientMetadata(client_id)
    self.assertEqual(md.startup_info_timestamp, hist[0].timestamp)

  def testReadClientStartupInfoHistoryEmpty(self):
    client_id = db_test_utils.InitializeClient(self.db)
    self.assertEqual(self.db.ReadClientStartupInfoHistory(client_id), [])

  def _SetUpReadClientStartupInfoHistoryTest(self):
    d = self.db

    self.client_id = db_test_utils.InitializeClient(self.db)

    timestamps = [self.db.Now()]

    si = rdf_client.StartupInfo(boot_time=1)
    d.WriteClientStartupInfo(self.client_id, si)
    timestamps.append(d.ReadClientStartupInfo(self.client_id).timestamp)

    timestamps.append(self.db.Now())

    si = rdf_client.StartupInfo(boot_time=2)
    d.WriteClientStartupInfo(self.client_id, si)
    timestamps.append(d.ReadClientStartupInfo(self.client_id).timestamp)

    timestamps.append(self.db.Now())

    return timestamps

  def testReadClientStartupInfoHistoryWithEmptyTimerange(self):
    d = self.db

    self._SetUpReadClientStartupInfoHistoryTest()

    hist = d.ReadClientStartupInfoHistory(
        self.client_id, timerange=(None, None))
    self.assertLen(hist, 2)
    self.assertEqual(hist[0].boot_time, 2)
    self.assertEqual(hist[1].boot_time, 1)

  def testReadClientStartupInfoHistoryWithTimerangeWithBothFromTo(self):
    d = self.db

    ts = self._SetUpReadClientStartupInfoHistoryTest()

    hist = d.ReadClientStartupInfoHistory(
        self.client_id, timerange=(ts[0], ts[2]))
    self.assertLen(hist, 1)
    self.assertEqual(hist[0].boot_time, 1)

    hist = d.ReadClientStartupInfoHistory(
        self.client_id, timerange=(ts[2], ts[4]))
    self.assertLen(hist, 1)
    self.assertEqual(hist[0].boot_time, 2)

    hist = d.ReadClientStartupInfoHistory(
        self.client_id, timerange=(ts[0], ts[4]))
    self.assertLen(hist, 2)
    self.assertEqual(hist[0].boot_time, 2)
    self.assertEqual(hist[1].boot_time, 1)

  def testReadClientStartupInfoHistoryWithTimerangeWithFromOnly(self):
    d = self.db

    ts = self._SetUpReadClientStartupInfoHistoryTest()

    hist = d.ReadClientStartupInfoHistory(
        self.client_id, timerange=(ts[0], None))
    self.assertLen(hist, 2)
    self.assertEqual(hist[0].boot_time, 2)
    self.assertEqual(hist[1].boot_time, 1)

    hist = d.ReadClientStartupInfoHistory(
        self.client_id, timerange=(ts[2], None))
    self.assertLen(hist, 1)
    self.assertEqual(hist[0].boot_time, 2)

    hist = d.ReadClientStartupInfoHistory(
        self.client_id, timerange=(ts[4], None))
    self.assertEmpty(hist)

  def testReadClientStartupInfoHistoryWithTimerangeWithToOnly(self):
    d = self.db

    ts = self._SetUpReadClientStartupInfoHistoryTest()

    hist = d.ReadClientStartupInfoHistory(
        self.client_id, timerange=(None, ts[0]))
    self.assertEmpty(hist)

    hist = d.ReadClientStartupInfoHistory(
        self.client_id, timerange=(None, ts[2]))
    self.assertLen(hist, 1)
    self.assertEqual(hist[0].boot_time, 1)

    hist = d.ReadClientStartupInfoHistory(
        self.client_id, timerange=(None, ts[4]))
    self.assertLen(hist, 2)
    self.assertEqual(hist[0].boot_time, 2)
    self.assertEqual(hist[1].boot_time, 1)

  def testReadClientStartupInfoHistoryWithTimerangeEdgeCases(self):
    # Timerange should work as [from, to]. I.e. "from" is inclusive and "to"
    # is inclusive.

    d = self.db

    ts = self._SetUpReadClientStartupInfoHistoryTest()

    hist = d.ReadClientStartupInfoHistory(
        self.client_id, timerange=(ts[1], ts[1]))
    self.assertLen(hist, 1)
    self.assertEqual(hist[0].boot_time, 1)

    hist = d.ReadClientStartupInfoHistory(
        self.client_id, timerange=(ts[1], ts[2]))
    self.assertLen(hist, 1)
    self.assertEqual(hist[0].boot_time, 1)

    hist = d.ReadClientStartupInfoHistory(
        self.client_id, timerange=(ts[1], ts[3]))
    self.assertLen(hist, 2)
    self.assertEqual(hist[0].boot_time, 2)
    self.assertEqual(hist[1].boot_time, 1)

  def testCrashHistory(self):
    d = self.db

    client_id = db_test_utils.InitializeClient(self.db)

    ci = rdf_client.ClientCrash(timestamp=12345, crash_message="Crash #1")
    d.WriteClientCrashInfo(client_id, ci)
    ci.crash_message = "Crash #2"
    d.WriteClientCrashInfo(client_id, ci)
    ci.crash_message = "Crash #3"
    d.WriteClientCrashInfo(client_id, ci)

    last_is = d.ReadClientCrashInfo(client_id)
    self.assertIsInstance(last_is, rdf_client.ClientCrash)
    self.assertEqual(last_is.crash_message, "Crash #3")
    self.assertIsInstance(last_is.timestamp, rdfvalue.RDFDatetime)

    hist = d.ReadClientCrashInfoHistory(client_id)
    self.assertLen(hist, 3)
    self.assertEqual([ci.crash_message for ci in hist],
                     ["Crash #3", "Crash #2", "Crash #1"])
    self.assertIsInstance(hist[0].timestamp, rdfvalue.RDFDatetime)
    self.assertGreater(hist[0].timestamp, hist[1].timestamp)
    self.assertGreater(hist[1].timestamp, hist[2].timestamp)

    md = self.db.ReadClientMetadata(client_id)
    self.assertEqual(md.last_crash_timestamp, hist[0].timestamp)

    self.assertIsNone(d.ReadClientCrashInfo("C.0000000000000000"))
    self.assertEqual(d.ReadClientCrashInfoHistory("C.0000000000000000"), [])

  def testEmptyCrashHistory(self):
    client_id = "C.0000000050000001"
    self.assertIsNone(self.db.ReadClientCrashInfo(client_id))
    self.assertEqual(self.db.ReadClientCrashInfoHistory(client_id), [])

  def testReadClientFullInfoPartialReads(self):
    client_id = db_test_utils.InitializeClient(self.db)
    self.assertIsNotNone(self.db.ReadClientFullInfo(client_id))

  def testReadClientFullInfoReturnsCorrectResult(self):
    d = self.db

    self.db.WriteGRRUser("test_owner")
    client_id = db_test_utils.InitializeClient(self.db)

    cl = rdf_objects.ClientSnapshot(
        client_id=client_id,
        knowledge_base=rdf_client.KnowledgeBase(fqdn="test1234.examples.com"),
        kernel="12.3")
    d.WriteClientSnapshot(cl)
    d.WriteClientMetadata(client_id, certificate=CERT)
    si = rdf_client.StartupInfo(boot_time=1)
    d.WriteClientStartupInfo(client_id, si)
    d.AddClientLabels(client_id, "test_owner", ["test_label"])

    full_info = d.ReadClientFullInfo(client_id)
    self.assertEqual(full_info.last_snapshot, cl)
    self.assertEqual(full_info.metadata.certificate, CERT)
    self.assertEqual(full_info.last_startup_info, si)
    self.assertEqual(
        full_info.labels,
        [rdf_objects.ClientLabel(owner="test_owner", name="test_label")])

  def testReadClientFullInfoTimestamps(self):
    client_id = db_test_utils.InitializeClient(self.db)

    first_seen_time = rdfvalue.RDFDatetime.Now()
    last_clock_time = rdfvalue.RDFDatetime.Now()
    last_ping_time = rdfvalue.RDFDatetime.Now()
    last_foreman_time = rdfvalue.RDFDatetime.Now()

    self.db.WriteClientMetadata(
        client_id=client_id,
        first_seen=first_seen_time,
        last_clock=last_clock_time,
        last_ping=last_ping_time,
        last_foreman=last_foreman_time)

    pre_time = self.db.Now()

    startup_info = rdf_client.StartupInfo()
    startup_info.client_info.client_name = "rrg"
    self.db.WriteClientStartupInfo(client_id, startup_info)

    crash_info = rdf_client.ClientCrash()
    crash_info.client_info.client_name = "grr"
    self.db.WriteClientCrashInfo(client_id, crash_info)

    post_time = self.db.Now()

    full_info = self.db.ReadClientFullInfo(client_id)
    self.assertEqual(full_info.metadata.first_seen, first_seen_time)
    self.assertEqual(full_info.metadata.clock, last_clock_time)
    self.assertEqual(full_info.metadata.ping, last_ping_time)
    self.assertEqual(full_info.metadata.last_foreman_time, last_foreman_time)

    self.assertBetween(full_info.metadata.startup_info_timestamp, pre_time,
                       post_time)
    self.assertBetween(full_info.metadata.last_crash_timestamp, pre_time,
                       post_time)

  def _SetupFullInfoClients(self):
    self.db.WriteGRRUser("test_owner")

    for i in range(10):
      client_id = db_test_utils.InitializeClient(self.db,
                                                 "C.000000005000000%d" % i)

      cl = rdf_objects.ClientSnapshot(
          client_id=client_id,
          knowledge_base=rdf_client.KnowledgeBase(fqdn="test%d.examples.com" %
                                                  i),
          kernel="12.3.%d" % i)
      self.db.WriteClientSnapshot(cl)
      self.db.WriteClientMetadata(client_id, certificate=CERT)
      si = rdf_client.StartupInfo(boot_time=i)
      self.db.WriteClientStartupInfo(client_id, si)
      self.db.AddClientLabels(
          client_id, "test_owner",
          ["test_label-a-%d" % i, "test_label-b-%d" % i])

  def _VerifySnapshots(self, snapshots):
    snapshots = sorted(snapshots, key=lambda s: s.client_id)
    self.assertLen(snapshots, 10)
    for i, s in enumerate(snapshots):
      self.assertEqual(s.client_id, "C.000000005000000%d" % i)
      self.assertEqual(s.knowledge_base.fqdn, "test%d.examples.com" % i)

  def _VerifyFullInfos(self, c_infos):
    c_infos = sorted(c_infos, key=lambda c: c.last_snapshot.client_id)
    for i, full_info in enumerate(c_infos):
      self.assertEqual(full_info.last_snapshot.client_id,
                       "C.000000005000000%d" % i)
      self.assertEqual(full_info.metadata.certificate, CERT)
      self.assertEqual(full_info.last_startup_info.boot_time, i)
      self.assertCountEqual(full_info.labels, [
          rdf_objects.ClientLabel(
              owner="test_owner", name="test_label-a-%d" % i),
          rdf_objects.ClientLabel(
              owner="test_owner", name="test_label-b-%d" % i)
      ])

  def testIterateAllClientsFullInfo(self):
    self._SetupFullInfoClients()
    self._VerifyFullInfos(self.db.IterateAllClientsFullInfo())

  def testIterateAllClientsFullInfoSmallBatches(self):
    self._SetupFullInfoClients()
    self._VerifyFullInfos(self.db.IterateAllClientsFullInfo(batch_size=2))

  def testIterateAllClientSnapshots(self):
    self._SetupFullInfoClients()
    snapshots = self.db.IterateAllClientSnapshots()
    self._VerifySnapshots(snapshots)

  def testIterateAllClientSnapshotsSmallBatches(self):
    self._SetupFullInfoClients()
    snapshots = self.db.IterateAllClientSnapshots(batch_size=2)
    self._VerifySnapshots(snapshots)

  def _SetupLastPingClients(self, now):
    time_past = now - rdfvalue.Duration.From(1, rdfvalue.DAYS)

    client_ids_to_ping = {}
    for i in range(10):
      client_id = db_test_utils.InitializeClient(self.db)

      self.db.WriteClientSnapshot(
          rdf_objects.ClientSnapshot(client_id=client_id))
      ping = (time_past if i % 2 == 0 else now)
      self.db.WriteClientMetadata(client_id, last_ping=ping)

      client_ids_to_ping[client_id] = ping

    return client_ids_to_ping

  def testMultiReadClientsFullInfoFiltersClientsByLastPingTime(self):
    d = self.db

    base_time = self.db.Now()
    cutoff_time = base_time - rdfvalue.Duration.From(1, rdfvalue.SECONDS)
    client_ids_to_ping = self._SetupLastPingClients(base_time)

    expected_client_ids = [
        cid for cid, ping in client_ids_to_ping.items() if ping == base_time
    ]
    full_infos = d.MultiReadClientFullInfo(
        list(client_ids_to_ping.keys()), min_last_ping=cutoff_time)
    self.assertCountEqual(expected_client_ids, full_infos)

  def testMultiReadClientsFullInfoWithEmptyList(self):
    d = self.db

    self.assertEqual(d.MultiReadClientFullInfo([]), {})

  def testMultiReadClientsFullInfoSkipsMissingClients(self):
    d = self.db

    present_client_id = "C.fc413187fefa1dcf"
    # Typical initial FS enabled write
    d.WriteClientMetadata(present_client_id, fleetspeak_enabled=True)

    missing_client_id = "C.00413187fefa1dcf"

    full_infos = d.MultiReadClientFullInfo(
        [present_client_id, missing_client_id])
    self.assertEqual(list(full_infos.keys()), [present_client_id])

  def testMultiReadClientsFullInfoNoSnapshot(self):
    d = self.db

    client_id = "C.fc413187fefa1dcf"
    d.WriteClientMetadata(client_id, fleetspeak_enabled=True)
    full_info = d.MultiReadClientFullInfo([client_id])[client_id]
    expected_snapshot = rdf_objects.ClientSnapshot(client_id=client_id)
    self.assertEqual(full_info.last_snapshot, expected_snapshot)

  def testReadClientMetadataRaisesWhenClientIsMissing(self):
    with self.assertRaises(db.UnknownClientError):
      self.db.ReadClientMetadata("C.00413187fefa1dcf")

  def testReadClientFullInfoRaisesWhenClientIsMissing(self):
    with self.assertRaises(db.UnknownClientError):
      self.db.ReadClientFullInfo("C.00413187fefa1dcf")

  def _SetupClientStats(self):
    db_test_utils.InitializeClient(self.db, "C.0000000000000001")
    db_test_utils.InitializeClient(self.db, "C.0000000000000002")

    offsets = [
        rdfvalue.Duration.From(0, rdfvalue.SECONDS),
        rdfvalue.Duration.From(1, rdfvalue.SECONDS),
        db.CLIENT_STATS_RETENTION,
        db.CLIENT_STATS_RETENTION + rdfvalue.Duration.From(1, rdfvalue.SECONDS),
    ]
    now = rdfvalue.RDFDatetime.Now()

    for offset_i, offset in enumerate(offsets):
      with test_lib.FakeTime(now - offset):
        for client_id in [1, 2]:
          stats = rdf_client_stats.ClientStats(
              RSS_size=offset_i,
              VMS_size=client_id,
              timestamp=rdfvalue.RDFDatetime.Now())
          self.db.WriteClientStats("C.%016x" % client_id, stats)

    return now

  def testReadClientStats_Empty(self):
    client_id = db_test_utils.InitializeClient(self.db)

    self.assertEmpty(self.db.ReadClientStats(client_id))

  def testReadClientStats_NotEmpty(self):
    client_id = db_test_utils.InitializeClient(self.db)

    self.db.WriteClientStats(
        client_id, rdf_client_stats.ClientStats(RSS_size=0xF00, VMS_size=0xB42))

    stats = self.db.ReadClientStats(client_id)
    self.assertLen(stats, 1)
    self.assertEqual(stats[0].RSS_size, 0xF00)
    self.assertEqual(stats[0].VMS_size, 0xB42)

  def testReadClientStats_ManyClients(self):
    client_id_1 = db_test_utils.InitializeClient(self.db)
    client_id_2 = db_test_utils.InitializeClient(self.db)

    self.db.WriteClientStats(client_id_1, rdf_client_stats.ClientStats())
    self.db.WriteClientStats(client_id_2, rdf_client_stats.ClientStats())
    self.db.WriteClientStats(client_id_2, rdf_client_stats.ClientStats())

    self.assertLen(self.db.ReadClientStats(client_id_1), 1)
    self.assertLen(self.db.ReadClientStats(client_id_2), 2)

  def testReadClientStats_Ordered(self):
    client_id = db_test_utils.InitializeClient(self.db)

    for idx in range(10):
      stats = rdf_client_stats.ClientStats(RSS_size=idx)
      self.db.WriteClientStats(client_id, stats)

    for idx, stats in enumerate(self.db.ReadClientStats(client_id)):
      self.assertEqual(stats.RSS_size, idx)

  def testReadClientStats_MinTime(self):
    client_id = db_test_utils.InitializeClient(self.db)

    self.db.WriteClientStats(client_id,
                             rdf_client_stats.ClientStats(RSS_size=0xF00))
    timestamp = self.db.Now()
    self.db.WriteClientStats(client_id,
                             rdf_client_stats.ClientStats(RSS_size=0xB42))

    stats = self.db.ReadClientStats(client_id, min_timestamp=timestamp)
    self.assertLen(stats, 1)
    self.assertEqual(stats[0].RSS_size, 0xB42)

  def testReadClientStats_MaxTime(self):
    client_id = db_test_utils.InitializeClient(self.db)

    self.db.WriteClientStats(client_id,
                             rdf_client_stats.ClientStats(RSS_size=0xF00))
    timestamp = self.db.Now()
    self.db.WriteClientStats(client_id,
                             rdf_client_stats.ClientStats(RSS_size=0xB42))

    stats = self.db.ReadClientStats(client_id, max_timestamp=timestamp)
    self.assertLen(stats, 1)
    self.assertEqual(stats[0].RSS_size, 0xF00)

  def testReadClientStats_MinMaxTime(self):
    client_id = db_test_utils.InitializeClient(self.db)

    self.db.WriteClientStats(client_id,
                             rdf_client_stats.ClientStats(RSS_size=0xF00))
    min_timestamp = self.db.Now()
    self.db.WriteClientStats(client_id,
                             rdf_client_stats.ClientStats(RSS_size=0xB42))
    max_timestamp = self.db.Now()
    self.db.WriteClientStats(client_id,
                             rdf_client_stats.ClientStats(RSS_size=0x00F))

    stats = self.db.ReadClientStats(
        client_id, min_timestamp=min_timestamp, max_timestamp=max_timestamp)
    self.assertLen(stats, 1)
    self.assertEqual(stats[0].RSS_size, 0xB42)

  def testDeleteOldClientStats_Empty(self):
    cutoff_time = self.db.Now()

    self.assertEmpty(list(self.db.DeleteOldClientStats(cutoff_time)))

  def testDeleteOldClientStats_NotEmpty(self):
    client_id = db_test_utils.InitializeClient(self.db)

    self.db.WriteClientStats(client_id, rdf_client_stats.ClientStats())
    self.db.WriteClientStats(client_id, rdf_client_stats.ClientStats())
    self.db.WriteClientStats(client_id, rdf_client_stats.ClientStats())
    cutoff_time = self.db.Now()

    self.assertEqual(sum(self.db.DeleteOldClientStats(cutoff_time)), 3)

    self.assertEmpty(list(self.db.ReadClientStats(client_id)))

  def testDeleteOldClientStats_CutoffTime(self):
    client_id = db_test_utils.InitializeClient(self.db)

    self.db.WriteClientStats(client_id,
                             rdf_client_stats.ClientStats(RSS_size=0xF00))
    self.db.WriteClientStats(client_id,
                             rdf_client_stats.ClientStats(RSS_size=0xB42))
    cutoff_time = self.db.Now()
    self.db.WriteClientStats(client_id,
                             rdf_client_stats.ClientStats(RSS_size=0x00F))

    self.assertEqual(sum(self.db.DeleteOldClientStats(cutoff_time)), 2)

    stats = self.db.ReadClientStats(client_id)
    self.assertLen(stats, 1)
    self.assertEqual(stats[0].RSS_size, 0x00F)

  def testDeleteOldClientStats_BatchSize(self):
    client_id = db_test_utils.InitializeClient(self.db)

    self.db.WriteClientStats(client_id,
                             rdf_client_stats.ClientStats(RSS_size=0xF00))
    self.db.WriteClientStats(client_id,
                             rdf_client_stats.ClientStats(RSS_size=0xB42))
    self.db.WriteClientStats(client_id,
                             rdf_client_stats.ClientStats(RSS_size=0x00F))
    cutoff_time = self.db.Now()

    results = list(self.db.DeleteOldClientStats(cutoff_time, batch_size=1))
    self.assertEqual(results, [1, 1, 1])

  def testDeleteOldClientStats_BatchSizeNegative(self):
    with self.assertRaises(ValueError):
      self.db.DeleteOldClientStats(cutoff_time=self.db.Now(), batch_size=-42)

  def testWriteClientStatsForNonExistingClient(self):
    with self.assertRaises(db.UnknownClientError) as context:
      self.db.WriteClientStats("C.0000000000000005",
                               rdf_client_stats.ClientStats())
    self.assertEqual(context.exception.client_id, "C.0000000000000005")

  def _WriteTestClientsWithData(self,
                                client_indices,
                                last_ping=None,
                                client_name=None,
                                client_version=None,
                                os=None,
                                os_release=None,
                                os_version=None,
                                labels_dict=None):
    for index in client_indices:
      client_id = "C.1%015x" % index
      self.db.WriteClientMetadata(
          client_id, last_ping=last_ping, fleetspeak_enabled=False)
      self.db.WriteClientSnapshot(
          rdf_objects.ClientSnapshot(
              client_id=client_id,
              startup_info=rdf_client.StartupInfo(
                  client_info=rdf_client.ClientInformation(
                      client_name=client_name, client_version=client_version)),
              knowledge_base=rdf_client.KnowledgeBase(os=os),
              os_release=os_release,
              os_version=os_version))
      for owner, labels in labels_dict.items():
        self.db.WriteGRRUser(owner)
        self.db.AddClientLabels(client_id, owner=owner, labels=labels)

  def _WriteTestDataForFleetStatsTesting(self):
    self._WriteTestClientsWithData(
        range(0, 5),
        last_ping=_DaysSinceEpoch(32),
        client_name="GRR",
        client_version=1111,
        os="Linux",
        os_release="Ubuntu",
        os_version="16.04",
        labels_dict={
            "GRR": ["grr-foo", "grr-bar"],
            "tester": ["tester-foo", "tester-bar"]
        })
    self._WriteTestClientsWithData(
        range(5, 7),
        last_ping=None,
        client_name="GRR",
        client_version=1111,
        os="Linux",
        os_release="Ubuntu",
        os_version="16.04",
        labels_dict={"GRR": ["grr-foo", "grr-bar"]})
    self._WriteTestClientsWithData(
        range(7, 10),
        last_ping=_DaysSinceEpoch(38),
        client_name="GRR",
        client_version=2222,
        os="Linux",
        os_release="Ubuntu",
        os_version="18.04",
        labels_dict={"GRR": ["grr-foo", "grr-bar"]})
    self._WriteTestClientsWithData(
        range(10, 13),
        last_ping=_DaysSinceEpoch(43),
        client_name="GRR",
        client_version=1111,
        os="Darwin",
        os_release="OSX",
        os_version="10.12.2",
        labels_dict={"GRR": ["grr-foo", "grr-bar", "grr-baz"]})
    self._WriteTestClientsWithData(
        range(13, 14),
        last_ping=_DaysSinceEpoch(15),
        client_name="GRR",
        client_version=1111,
        os="Darwin",
        os_release="OSX",
        os_version="10.12.2",
        labels_dict={})  # Client has no labels.
    self._WriteTestClientsWithData(
        range(14, 15),
        last_ping=_DaysSinceEpoch(15),
        client_name="GRR",
        client_version=1111,
        os="Darwin",
        os_release="OSX",
        os_version="10.12.2",
        labels_dict={"tester": ["tester-foo"]})  # Client has no GRR labels.
    # Client with missing data.
    self._WriteTestClientsWithData(
        range(15, 16),
        last_ping=_DaysSinceEpoch(15),
        labels_dict={"GRR": ["grr-foo"]})
    self._WriteTestClientsWithData(
        range(16, 17),
        last_ping=_DaysSinceEpoch(1),  # Ancient ping timestamp.
        client_name="GRR",
        client_version=1111,
        os="Linux",
        os_release="Ubuntu",
        os_version="16.04",
        labels_dict={"GRR": ["grr-foo", "grr-bar"]})

  def testCountClientVersionStringsByLabel(self):
    self._WriteTestDataForFleetStatsTesting()
    with test_lib.FakeTime(_DaysSinceEpoch(44)):
      fleet_stats = self.db.CountClientVersionStringsByLabel({1, 2, 8, 30})
      for client_label in fleet_stats.GetAllLabels():
        self.assertIsInstance(client_label, Text)
      expected_label_counts = {
          (2, "grr-foo", "GRR 1111"): 3,
          (2, "grr-bar", "GRR 1111"): 3,
          (2, "grr-baz", "GRR 1111"): 3,
          (8, "grr-foo", "GRR 1111"): 3,
          (8, "grr-bar", "GRR 1111"): 3,
          (8, "grr-baz", "GRR 1111"): 3,
          (8, "grr-foo", "GRR 2222"): 3,
          (8, "grr-bar", "GRR 2222"): 3,
          (30, "grr-foo", "GRR 1111"): 8,
          (30, "grr-bar", "GRR 1111"): 8,
          (30, "grr-baz", "GRR 1111"): 3,
          (30, "grr-foo", "GRR 2222"): 3,
          (30, "grr-bar", "GRR 2222"): 3,
          (30, "grr-foo", " Unknown-GRR-version"): 1,
      }
      expected_total_counts = {
          (2, "GRR 1111"): 3,
          (8, "GRR 1111"): 3,
          (8, "GRR 2222"): 3,
          (30, "GRR 1111"): 10,
          (30, "GRR 2222"): 3,
          (30, " Unknown-GRR-version"): 1,
      }
      self.assertDictEqual(fleet_stats.GetFlattenedLabelCounts(),
                           expected_label_counts)
      self.assertDictEqual(fleet_stats.GetFlattenedTotalCounts(),
                           expected_total_counts)

  def testCountClientPlatformsByLabel(self):
    self._WriteTestDataForFleetStatsTesting()
    with test_lib.FakeTime(_DaysSinceEpoch(44)):
      fleet_stats = self.db.CountClientPlatformsByLabel({1, 2, 8, 30})
      for client_label in fleet_stats.GetAllLabels():
        self.assertIsInstance(client_label, Text)
      expected_label_counts = {
          (2, "grr-foo", "Darwin"): 3,
          (2, "grr-bar", "Darwin"): 3,
          (2, "grr-baz", "Darwin"): 3,
          (8, "grr-foo", "Darwin"): 3,
          (8, "grr-bar", "Darwin"): 3,
          (8, "grr-baz", "Darwin"): 3,
          (8, "grr-foo", "Linux"): 3,
          (8, "grr-bar", "Linux"): 3,
          (30, "grr-foo", "Darwin"): 3,
          (30, "grr-bar", "Darwin"): 3,
          (30, "grr-baz", "Darwin"): 3,
          (30, "grr-foo", "Linux"): 8,
          (30, "grr-bar", "Linux"): 8,
          (30, "grr-foo", ""): 1,
      }
      expected_total_counts = {
          (2, "Darwin"): 3,
          (8, "Darwin"): 3,
          (8, "Linux"): 3,
          (30, "Darwin"): 5,
          (30, "Linux"): 8,
          (30, ""): 1,
      }
      self.assertDictEqual(fleet_stats.GetFlattenedLabelCounts(),
                           expected_label_counts)
      self.assertDictEqual(fleet_stats.GetFlattenedTotalCounts(),
                           expected_total_counts)

  def testCountClientPlatformReleasesByLabel(self):
    self._WriteTestDataForFleetStatsTesting()
    with test_lib.FakeTime(_DaysSinceEpoch(44)):
      fleet_stats = self.db.CountClientPlatformReleasesByLabel({1, 2, 8, 30})
      for client_label in fleet_stats.GetAllLabels():
        self.assertIsInstance(client_label, Text)
      expected_label_counts = {
          (2, "grr-foo", "Darwin-OSX-10.12.2"): 3,
          (2, "grr-bar", "Darwin-OSX-10.12.2"): 3,
          (2, "grr-baz", "Darwin-OSX-10.12.2"): 3,
          (8, "grr-foo", "Darwin-OSX-10.12.2"): 3,
          (8, "grr-bar", "Darwin-OSX-10.12.2"): 3,
          (8, "grr-baz", "Darwin-OSX-10.12.2"): 3,
          (8, "grr-foo", "Linux-Ubuntu-18.04"): 3,
          (8, "grr-bar", "Linux-Ubuntu-18.04"): 3,
          (30, "grr-foo", "Darwin-OSX-10.12.2"): 3,
          (30, "grr-bar", "Darwin-OSX-10.12.2"): 3,
          (30, "grr-baz", "Darwin-OSX-10.12.2"): 3,
          (30, "grr-foo", "Linux-Ubuntu-18.04"): 3,
          (30, "grr-bar", "Linux-Ubuntu-18.04"): 3,
          (30, "grr-foo", "Linux-Ubuntu-16.04"): 5,
          (30, "grr-bar", "Linux-Ubuntu-16.04"): 5,
          (30, "grr-foo", "--"): 1,
      }
      expected_total_counts = {
          (2, "Darwin-OSX-10.12.2"): 3,
          (8, "Darwin-OSX-10.12.2"): 3,
          (8, "Linux-Ubuntu-18.04"): 3,
          (30, "Darwin-OSX-10.12.2"): 5,
          (30, "Linux-Ubuntu-16.04"): 5,
          (30, "Linux-Ubuntu-18.04"): 3,
          (30, "--"): 1,
      }
      self.assertDictEqual(fleet_stats.GetFlattenedLabelCounts(),
                           expected_label_counts)
      self.assertDictEqual(fleet_stats.GetFlattenedTotalCounts(),
                           expected_total_counts)

  @mock.patch.object(db, "_MAX_GRR_VERSION_LENGTH", 10)
  def testWriteClientSnapshotLongGRRVersion(self):
    snapshot = rdf_objects.ClientSnapshot(client_id="C.0000000000000001")
    snapshot.startup_info.client_info.client_description = "🚀" * 12
    snapshot.startup_info.client_info.client_version = 1234
    with self.assertRaises(db.StringTooLongError):
      self.db.WriteClientSnapshot(snapshot)

  @mock.patch.object(db, "_MAX_CLIENT_PLATFORM_LENGTH", 10)
  def testWriteClientSnapshotLongPlatform(self):
    snapshot = rdf_objects.ClientSnapshot(client_id="C.0000000000000001")
    snapshot.knowledge_base.os = "🚀" * 12
    with self.assertRaises(db.StringTooLongError):
      self.db.WriteClientSnapshot(snapshot)

  @mock.patch.object(db, "_MAX_CLIENT_PLATFORM_RELEASE_LENGTH", 10)
  def testWriteClientSnapshotLongPlatformRelease(self):
    snapshot = rdf_objects.ClientSnapshot(client_id="C.0000000000000001")
    snapshot.knowledge_base.os = "🚀" * 12
    with self.assertRaises(db.StringTooLongError):
      self.db.WriteClientSnapshot(snapshot)

  def testWriteClientSnapshotSequence(self):
    count = 64

    client_id = db_test_utils.InitializeClient(self.db)
    snapshot = rdf_objects.ClientSnapshot(client_id=client_id)

    # Updates of the client snapshots next to each other should not fail
    # and each of them should have distinct timestamp.
    for idx in range(count):
      snapshot.startup_info.client_info.revision = idx
      snapshot.kernel = f"3.14.{idx}"
      self.db.WriteClientSnapshot(snapshot)

    snapshots = self.db.ReadClientSnapshotHistory(client_id)
    self.assertLen(snapshots, count)

    # Returned snapshots will be ordered from the newest to oldest, so we invert
    # the order for cleaner assertions.
    for idx, snapshot in enumerate(reversed(snapshots)):
      self.assertEqual(snapshot.startup_info.client_info.revision, idx)
      self.assertEqual(snapshot.kernel, f"3.14.{idx}")

  def testWriteClientSnapshotNonDestructiveArgs(self):
    client_id = db_test_utils.InitializeClient(self.db)

    written_snapshot = rdf_objects.ClientSnapshot()
    written_snapshot.client_id = client_id
    written_snapshot.startup_info.client_info.labels.append("foo")

    self.db.WriteClientSnapshot(written_snapshot)
    read_snapshot = self.db.ReadClientSnapshot(client_id)

    self.assertEqual(written_snapshot.startup_info.client_info.labels, ["foo"])
    self.assertEqual(read_snapshot.startup_info.client_info.labels, ["foo"])

  def _AddClientKeyedData(self, client_id):
    # Client labels.
    self.db.WriteGRRUser("testowner")
    self.db.AddClientLabels(client_id, "testowner", ["label"])

    # Client snapshot including client startup info.
    snapshot = rdf_objects.ClientSnapshot(client_id=client_id)
    snapshot.startup_info.client_info.client_version = 42
    self.db.WriteClientSnapshot(snapshot)

    # Crash information
    self.db.WriteClientCrashInfo(
        client_id,
        rdf_client.ClientCrash(timestamp=12345, crash_message="Crash #1"))

    # Index keywords.
    self.db.AddClientKeywords(client_id, ["machine.test.example1.com"])

    # Client stats.
    self.db.WriteClientStats(
        client_id, rdf_client_stats.ClientStats(RSS_size=10, VMS_size=123))

    # A flow.
    flow_id = flow.RandomFlowId()
    self.db.WriteFlowObject(
        rdf_flow_objects.Flow(client_id=client_id, flow_id=flow_id))
    # A flow request.
    self.db.WriteFlowRequests([
        rdf_flow_objects.FlowRequest(
            client_id=client_id, flow_id=flow_id, request_id=1)
    ])

    # A flow response.
    self.db.WriteFlowResponses([
        rdf_flow_objects.FlowResponse(
            client_id=client_id, flow_id=flow_id, request_id=1, response_id=1)
    ])

    # A flow processing request.
    self.db.WriteFlowProcessingRequests(
        [rdf_flows.FlowProcessingRequest(client_id=client_id, flow_id=flow_id)])

    # A client action request.
    self.db.WriteClientActionRequests([
        rdf_flows.ClientActionRequest(
            client_id=client_id, flow_id=flow_id, request_id=1)
    ])

    return flow_id

  def _CheckClientKeyedDataWasDeleted(self, client_id, flow_id):

    # Client labels.
    self.assertEmpty(self.db.ReadClientLabels(client_id))

    # Client snapshot including client startup info.
    self.assertIsNone(self.db.ReadClientSnapshot(client_id))
    self.assertIsNone(self.db.ReadClientStartupInfo(client_id))

    # Crash information
    self.assertIsNone(self.db.ReadClientCrashInfo(client_id))

    # Index keywords.
    res = self.db.ListClientsForKeywords(["machine.test.example1.com"])
    self.assertEqual(res, {"machine.test.example1.com": []})

    # Client stats.
    self.assertEmpty(self.db.ReadClientStats(client_id))

    # A flow.
    with self.assertRaises(db.UnknownFlowError):
      self.db.ReadFlowObject(client_id, flow_id)

    # A client action request.
    self.assertEmpty(self.db.ReadAllClientActionRequests(client_id))

  def testDeleteClient(self):
    client_id = db_test_utils.InitializeClient(self.db)

    # Add some data that will be stored with the client id as foreign key. None
    # of this additional data should stop the client from being deleted.

    flow_id = self._AddClientKeyedData(client_id)

    self.db.DeleteClient(client_id=client_id)

    with self.assertRaises(db.UnknownClientError):
      self.db.ReadClientMetadata(client_id)

    self._CheckClientKeyedDataWasDeleted(client_id, flow_id)

  def testDeleteNonExistingClient(self):
    client_id = "C.0000000000000000"
    with self.assertRaises(db.UnknownClientError):
      self.db.DeleteClient(client_id=client_id)

  def testDeleteClientNoAdditionalData(self):
    client_id = db_test_utils.InitializeClient(self.db)
    self.db.DeleteClient(client_id=client_id)
    with self.assertRaises(db.UnknownClientError):
      self.db.ReadClientMetadata(client_id)

  def testDeleteClientWithAssociatedMetadata(self):
    client_id = db_test_utils.InitializeClient(self.db)

    snapshot = rdf_objects.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.os_version = "3.14"
    snapshot.arch = "i686"
    snapshot.knowledge_base.os = "redox"
    snapshot.knowledge_base.os_major_version = 3
    snapshot.knowledge_base.os_minor_version = 14
    self.db.WriteClientSnapshot(snapshot)

    startup = rdf_client.StartupInfo()
    startup.boot_time = rdfvalue.RDFDatetime.Now()
    startup.client_info.client_version = 1337
    self.db.WriteClientStartupInfo(client_id, startup)

    crash = rdf_client.ClientCrash()
    crash.client_id = client_id
    crash.client_info.client_version = 1337
    crash.timestamp = rdfvalue.RDFDatetime.Now()
    self.db.WriteClientCrashInfo(client_id, crash)

    self.db.DeleteClient(client_id)

    with self.assertRaises(db.UnknownClientError):
      self.db.ReadClientFullInfo(client_id)

  def testDeleteClientWithPaths(self):
    client_id = db_test_utils.InitializeClient(self.db)

    path_info_0 = rdf_objects.PathInfo.OS(components=("foo", "bar", "baz"))
    path_info_0.stat_entry.st_size = 42

    path_info_1 = rdf_objects.PathInfo.OS(components=("foo", "bar", "quux"))
    path_info_1.hash_entry.sha256 = b"quux"

    path_info_2 = rdf_objects.PathInfo.OS(components=("foo", "norf", "thud"))
    path_info_2.stat_entry.st_size = 1337
    path_info_2.hash_entry.sha256 = b"norf"

    self.db.WritePathInfos(client_id, [path_info_0, path_info_1, path_info_2])

    self.db.DeleteClient(client_id)

    with self.assertRaises(db.UnknownClientError):
      self.db.ReadClientFullInfo(client_id)

  def testFleetspeakValidationInfoIsInitiallyUnset(self):
    client_id = "C.fc413187fefa1dcf"
    self.db.WriteClientMetadata(
        client_id, first_seen=rdfvalue.RDFDatetime(100000000))

    res = self.db.MultiReadClientMetadata([client_id])
    self.assertLen(res, 1)
    metadata = res[client_id]
    self.assertFalse(metadata.last_fleetspeak_validation_info)

  def testWritesFleetspeakValidationInfo(self):
    client_id = "C.fc413187fefa1dcf"

    self.db.WriteClientMetadata(
        client_id, fleetspeak_validation_info={
            "foo": "bar",
            "12": "34"
        })

    res = self.db.MultiReadClientMetadata([client_id])
    self.assertLen(res, 1)
    metadata = res[client_id]
    self.assertEqual(metadata.last_fleetspeak_validation_info.ToStringDict(), {
        "foo": "bar",
        "12": "34"
    })

  def testOverwritesFleetspeakValidationInfo(self):
    client_id = "C.fc413187fefa1dcf"

    self.db.WriteClientMetadata(
        client_id, fleetspeak_validation_info={
            "foo": "bar",
            "12": "34"
        })
    self.db.WriteClientMetadata(
        client_id, fleetspeak_validation_info={
            "foo": "bar",
            "new": "1234"
        })

    res = self.db.MultiReadClientMetadata([client_id])
    self.assertLen(res, 1)
    metadata = res[client_id]
    self.assertEqual(metadata.last_fleetspeak_validation_info.ToStringDict(), {
        "foo": "bar",
        "new": "1234"
    })

  def testRemovesFleetspeakValidationInfoWhenValidationInfoIsEmpty(self):
    client_id = "C.fc413187fefa1dcf"

    self.db.WriteClientMetadata(
        client_id, fleetspeak_validation_info={"foo": "bar"})
    self.db.WriteClientMetadata(client_id, fleetspeak_validation_info={})

    res = self.db.MultiReadClientMetadata([client_id])
    self.assertLen(res, 1)
    metadata = res[client_id]
    self.assertFalse(metadata.last_fleetspeak_validation_info)

  def testRemovesFleetspeakValidationInfoWhenValidationInfoIsNotPresent(self):
    client_id = "C.fc413187fefa1dcf"

    self.db.WriteClientMetadata(
        client_id, fleetspeak_validation_info={"foo": "bar"})
    self.db.WriteClientMetadata(client_id)

    res = self.db.MultiReadClientMetadata([client_id])
    self.assertLen(res, 1)
    metadata = res[client_id]
    self.assertFalse(metadata.last_fleetspeak_validation_info)


# This file is a test library and thus does not require a __main__ block.
