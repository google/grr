#!/usr/bin/env python
from unittest import mock

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.util import collection
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import knowledge_base_pb2
from grr_response_proto import objects_pb2
from grr_response_server import flow
from grr_response_server.databases import db
from grr_response_server.databases import db_test_utils
from grr_response_server.models import clients as models_clients
from grr_response_proto.rrg import startup_pb2 as rrg_startup_pb2


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
      d.WriteClientSnapshot(objects_pb2.ClientSnapshot(client_id=client_id))
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
    d.WriteClientMetadata(client_id_1)

    client_id_2 = "C.00413187fefa1dcf"
    # Typical initial non-FS write
    d.WriteClientMetadata(
        client_id_2,
        first_seen=rdfvalue.RDFDatetime(100000000),
    )

    res = d.MultiReadClientMetadata([client_id_1, client_id_2])
    self.assertLen(res, 2)

    m1 = res[client_id_1]
    self.assertIsInstance(m1, objects_pb2.ClientMetadata)

    m2 = res[client_id_2]
    self.assertIsInstance(m2, objects_pb2.ClientMetadata)
    self.assertEqual(m2.first_seen, int(rdfvalue.RDFDatetime(100000000)))

  def testClientMetadataDefaultValues(self):
    d = self.db

    client_id = "C.ab413187fefa1dcf"
    # Empty initialization
    d.WriteClientMetadata(client_id)

    # Check NULL/empty default values
    md = d.ReadClientMetadata(client_id)
    self.assertEmpty(md.certificate)
    self.assertFalse(md.first_seen)
    self.assertFalse(md.ping)
    self.assertFalse(md.last_foreman_time)
    self.assertFalse(md.last_crash_timestamp)
    self.assertFalse(md.startup_info_timestamp)
    self.assertFalse(md.HasField("last_fleetspeak_validation_info"))

  def testClientMetadataSkipFields(self):
    client_id = "C.fc413187fefa1dcf"
    self.db.WriteClientMetadata(
        client_id,
        first_seen=rdfvalue.RDFDatetime(100000000),
        last_foreman=rdfvalue.RDFDatetime(100000002),
        last_ping=rdfvalue.RDFDatetime(100000003),
        fleetspeak_validation_info={"foo": "bar"},
    )
    # Skip fields
    self.db.WriteClientMetadata(
        client_id,
        first_seen=None,
        last_foreman=None,
        last_ping=None,
        fleetspeak_validation_info=None,
    )

    md = self.db.ReadClientMetadata(client_id)
    self.assertEqual(md.first_seen, int(rdfvalue.RDFDatetime(100000000)))
    self.assertEqual(md.last_foreman_time, int(rdfvalue.RDFDatetime(100000002)))
    self.assertEqual(md.ping, int(rdfvalue.RDFDatetime(100000003)))
    self.assertEqual(
        models_clients.FleetspeakValidationInfoToDict(
            md.last_fleetspeak_validation_info
        ),
        {"foo": "bar"},
    )

  def testClientMetadataSubsecond(self):
    client_id = "C.fc413187fefa1dcf"
    self.db.WriteClientMetadata(
        client_id,
        first_seen=rdfvalue.RDFDatetime(100000001),
        last_foreman=rdfvalue.RDFDatetime(100000021),
        last_ping=rdfvalue.RDFDatetime(100000031),
    )
    res = self.db.MultiReadClientMetadata([client_id])
    self.assertLen(res, 1)
    m1 = res[client_id]
    self.assertEqual(m1.first_seen, rdfvalue.RDFDatetime(100000001))
    self.assertEqual(m1.last_foreman_time, rdfvalue.RDFDatetime(100000021))
    self.assertEqual(m1.ping, rdfvalue.RDFDatetime(100000031))

  def testClientMetadataPing(self):
    d = self.db

    client_id = db_test_utils.InitializeClient(self.db)

    # Typical update on client ping.
    d.WriteClientMetadata(
        client_id,
        last_ping=rdfvalue.RDFDatetime(200000000000),
        last_foreman=rdfvalue.RDFDatetime(220000000000),
    )

    res = d.MultiReadClientMetadata([client_id])
    self.assertLen(res, 1)
    m1 = res[client_id]
    self.assertIsInstance(m1, objects_pb2.ClientMetadata)
    self.assertEqual(m1.ping, int(rdfvalue.RDFDatetime(200000000000)))
    self.assertEqual(
        m1.last_foreman_time,
        int(rdfvalue.RDFDatetime(220000000000)),
    )

  def testMultiWriteClientMetadata(self):
    d = self.db

    client_id_1 = db_test_utils.InitializeClient(self.db)
    client_id_2 = db_test_utils.InitializeClient(self.db)

    d.MultiWriteClientMetadata(
        [client_id_1, client_id_2], last_foreman=rdfvalue.RDFDatetime(100000034)
    )

    res = d.MultiReadClientMetadata([client_id_1, client_id_2])
    self.assertLen(res, 2)

    m1 = res[client_id_1]
    self.assertEqual(m1.last_foreman_time, int(rdfvalue.RDFDatetime(100000034)))

    m2 = res[client_id_2]
    self.assertEqual(m2.last_foreman_time, int(rdfvalue.RDFDatetime(100000034)))

  def testMultiWriteClientMetadataNoValues(self):
    client_id_1 = db_test_utils.InitializeClient(self.db)
    client_id_2 = db_test_utils.InitializeClient(self.db)

    self.db.MultiWriteClientMetadata(
        [client_id_1, client_id_2]
    )  # Should not fail.

  def testMultiWriteClientMetadataNoClients(self):
    self.db.MultiWriteClientMetadata(
        [], last_foreman=rdfvalue.RDFDatetime(100000035)
    )  # Should not fail.

  def testReadAllClientIDsEmpty(self):
    result = list(self.db.ReadAllClientIDs())
    self.assertEmpty(result)

  def testReadAllClientIDsSome(self):
    client_a_id = db_test_utils.InitializeClient(self.db)
    client_b_id = db_test_utils.InitializeClient(self.db)
    client_c_id = db_test_utils.InitializeClient(self.db)

    client_ids = list(self.db.ReadAllClientIDs())
    self.assertLen(client_ids, 1)
    self.assertCountEqual(
        client_ids[0], [client_a_id, client_b_id, client_c_id]
    )

  def testReadAllClientIDsNotEvenlyDivisibleByBatchSize(self):
    client_a_id = db_test_utils.InitializeClient(self.db)
    client_b_id = db_test_utils.InitializeClient(self.db)
    client_c_id = db_test_utils.InitializeClient(self.db)

    client_ids = list(self.db.ReadAllClientIDs(batch_size=2))
    self.assertEqual([len(batch) for batch in client_ids], [2, 1])
    self.assertCountEqual(
        collection.Flatten(client_ids), [client_a_id, client_b_id, client_c_id]
    )

  def testReadAllClientIDsEvenlyDivisibleByBatchSize(self):
    client_a_id = db_test_utils.InitializeClient(self.db)
    client_b_id = db_test_utils.InitializeClient(self.db)
    client_c_id = db_test_utils.InitializeClient(self.db)
    client_d_id = db_test_utils.InitializeClient(self.db)

    client_ids = list(self.db.ReadAllClientIDs(batch_size=2))
    self.assertEqual([len(batch) for batch in client_ids], [2, 2])
    self.assertCountEqual(
        collection.Flatten(client_ids),
        [client_a_id, client_b_id, client_c_id, client_d_id],
    )

  def testReadAllClientIDsFilterLastPing(self):
    self.db.WriteClientMetadata("C.0000000000000001")
    self.db.WriteClientMetadata(
        "C.0000000000000002",
        last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(2),
    )
    self.db.WriteClientMetadata(
        "C.0000000000000003",
        last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3),
    )
    self.db.WriteClientMetadata(
        "C.0000000000000004",
        last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(4),
    )
    client_ids = self.db.ReadAllClientIDs(
        min_last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3)
    )
    self.assertCountEqual(
        collection.Flatten(client_ids),
        ["C.0000000000000003", "C.0000000000000004"],
    )

  def testReadClientLastPings_ResultsDivisibleByBatchSize(self):
    client_ids = self._WriteClientLastPingData()
    (
        client_id5,
        client_id6,
        client_id7,
        client_id8,
        client_id9,
        client_id10,
    ) = client_ids[4:]

    results = list(
        self.db.ReadClientLastPings(
            min_last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3),
            batch_size=3,
        )
    )

    self.assertEqual([len(batch) for batch in results], [3, 3])

    self.assertEqual(
        _FlattenDicts(results),
        {
            client_id5: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3),
            client_id6: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3),
            client_id7: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(4),
            client_id8: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(4),
            client_id9: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(5),
            client_id10: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(5),
        },
    )

  def testReadClientLastPings_ResultsNotDivisibleByBatchSize(self):
    client_ids = self._WriteClientLastPingData()
    (
        client_id5,
        client_id6,
        client_id7,
        client_id8,
        client_id9,
        client_id10,
    ) = client_ids[4:]

    results = list(
        self.db.ReadClientLastPings(
            min_last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3),
            batch_size=4,
        )
    )

    self.assertEqual([len(batch) for batch in results], [4, 2])

    self.assertEqual(
        _FlattenDicts(results),
        {
            client_id5: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3),
            client_id6: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3),
            client_id7: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(4),
            client_id8: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(4),
            client_id9: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(5),
            client_id10: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(5),
        },
    )

  def testReadClientLastPings_NoFilter(self):
    client_ids = self._WriteClientLastPingData()
    (
        client_id1,
        client_id2,
        client_id3,
        client_id4,
        client_id5,
        client_id6,
        client_id7,
        client_id8,
        client_id9,
        client_id10,
    ) = client_ids

    self.assertEqual(
        list(self.db.ReadClientLastPings()),
        [{
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
        }],
    )

  def testReadClientLastPings_AllFilters(self):
    client_ids = self._WriteClientLastPingData()
    client_id5 = client_ids[4]
    client_id6 = client_ids[5]
    client_id7 = client_ids[6]
    client_id8 = client_ids[7]

    actual_data = self.db.ReadClientLastPings(
        min_last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3),
        max_last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(4),
    )
    expected_data = [{
        client_id5: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3),
        client_id6: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3),
        client_id7: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(4),
        client_id8: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(4),
    }]
    self.assertEqual(list(actual_data), expected_data)

  def testReadClientLastPings_MinPingFilter(self):
    client_ids = self._WriteClientLastPingData()
    client_id5 = client_ids[4]
    client_id6 = client_ids[5]
    client_id7 = client_ids[6]
    client_id8 = client_ids[7]
    client_id9 = client_ids[8]
    client_id10 = client_ids[9]

    actual_data = self.db.ReadClientLastPings(
        min_last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3)
    )
    expected_data = [{
        client_id5: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3),
        client_id6: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3),
        client_id7: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(4),
        client_id8: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(4),
        client_id9: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(5),
        client_id10: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(5),
    }]
    self.assertEqual(list(actual_data), expected_data)

  def testReadClientLastPings_MaxPingFilter(self):
    client_ids = self._WriteClientLastPingData()
    client_id1 = client_ids[0]
    client_id2 = client_ids[1]
    client_id3 = client_ids[2]
    client_id4 = client_ids[3]
    client_id5 = client_ids[4]
    client_id6 = client_ids[5]

    actual_data = self.db.ReadClientLastPings(
        max_last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3)
    )
    expected_data = [{
        client_id1: None,
        client_id2: None,
        client_id3: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(2),
        client_id4: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(2),
        client_id5: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3),
        client_id6: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3),
    }]
    self.assertEqual(list(actual_data), expected_data)

  def _WriteClientLastPingData(self):
    """Writes test data for ReadClientLastPings() tests."""
    client_ids = tuple("C.00000000000000%02d" % i for i in range(1, 11))
    (
        client_id1,
        client_id2,
        client_id3,
        client_id4,
        client_id5,
        client_id6,
        client_id7,
        client_id8,
        client_id9,
        client_id10,
    ) = client_ids

    self.db.WriteClientMetadata(client_id1)
    self.db.WriteClientMetadata(client_id2)
    self.db.WriteClientMetadata(
        client_id3, last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(2)
    )
    self.db.WriteClientMetadata(
        client_id4, last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(2)
    )
    self.db.WriteClientMetadata(
        client_id5, last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3)
    )
    self.db.WriteClientMetadata(
        client_id6, last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3)
    )
    self.db.WriteClientMetadata(
        client_id7, last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(4)
    )
    self.db.WriteClientMetadata(
        client_id8, last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(4)
    )
    self.db.WriteClientMetadata(
        client_id9, last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(5)
    )
    self.db.WriteClientMetadata(
        client_id10, last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(5)
    )

    return client_ids

  def _SetUpReadClientSnapshotHistoryTest(self):
    d = self.db

    self.client_id = db_test_utils.InitializeClient(self.db)

    timestamps = [d.Now()]

    client = objects_pb2.ClientSnapshot(client_id=self.client_id, kernel="12.3")
    client.knowledge_base.fqdn = "test1234.examples.com"
    d.WriteClientSnapshot(client)
    timestamps.append(
        rdfvalue.RDFDatetime(d.ReadClientSnapshot(self.client_id).timestamp)
    )

    timestamps.append(d.Now())

    client.kernel = "12.4"
    d.WriteClientSnapshot(client)
    timestamps.append(
        rdfvalue.RDFDatetime(d.ReadClientSnapshot(self.client_id).timestamp)
    )

    timestamps.append(d.Now())

    return timestamps

  def testReadClientSnapshotHistory(self):
    d = self.db

    self._SetUpReadClientSnapshotHistoryTest()

    hist = d.ReadClientSnapshotHistory(self.client_id)
    self.assertLen(hist, 2)
    self.assertIsInstance(hist[0], objects_pb2.ClientSnapshot)
    self.assertIsInstance(hist[1], objects_pb2.ClientSnapshot)
    self.assertGreater(hist[0].timestamp, hist[1].timestamp)
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

  def testClientStartupInfo(self):
    """StartupInfo is written to a separate table, make sure the merge works."""
    client_id = db_test_utils.InitializeClient(self.db)

    client = objects_pb2.ClientSnapshot(client_id=client_id, kernel="12.3")
    client.startup_info.boot_time = 123
    client.knowledge_base.fqdn = "test1234.examples.com"
    self.db.WriteClientSnapshot(client)

    client = self.db.ReadClientSnapshot(client_id)
    self.assertEqual(client.startup_info.boot_time, 123)

    client = objects_pb2.ClientSnapshot(client_id=client_id)
    client.kernel = "12.4"
    client.startup_info.boot_time = 124
    self.db.WriteClientSnapshot(client)

    client = objects_pb2.ClientSnapshot(client_id=client_id)
    client.kernel = "12.5"
    client.startup_info.boot_time = 125
    self.db.WriteClientSnapshot(client)

    hist = self.db.ReadClientSnapshotHistory(client_id)
    self.assertLen(hist, 3)
    startup_infos = [cl.startup_info for cl in hist]
    self.assertEqual([si.boot_time for si in startup_infos], [125, 124, 123])

  def testReadClientStartupInfoHistory(self):
    self.client_id = db_test_utils.InitializeClient(self.db)

    startup_1 = jobs_pb2.StartupInfo()
    startup_1.boot_time = 123
    startup_1.client_info.client_version = 1
    self.db.WriteClientStartupInfo(self.client_id, startup_1)

    startup_2 = jobs_pb2.StartupInfo()
    startup_2.boot_time = 124
    startup_2.client_info.client_version = 2
    self.db.WriteClientStartupInfo(self.client_id, startup_2)

    hist = self.db.ReadClientStartupInfoHistory(self.client_id)
    self.assertLen(hist, 2)
    self.assertIsInstance(hist[0], jobs_pb2.StartupInfo)
    self.assertIsInstance(hist[1], jobs_pb2.StartupInfo)
    self.assertGreater(hist[0].timestamp, hist[1].timestamp)
    self.assertEqual(hist[0].boot_time, 124)
    self.assertEqual(hist[1].boot_time, 123)

  def testReadClientStartupInfoHistoryWithEmptyTimerange(self):
    self.client_id = db_test_utils.InitializeClient(self.db)

    startup_1 = jobs_pb2.StartupInfo()
    startup_1.boot_time = 123
    startup_1.client_info.client_version = 1
    self.db.WriteClientStartupInfo(self.client_id, startup_1)

    startup_2 = jobs_pb2.StartupInfo()
    startup_2.boot_time = 124
    startup_2.client_info.client_version = 2
    self.db.WriteClientStartupInfo(self.client_id, startup_2)

    hist = self.db.ReadClientStartupInfoHistory(
        self.client_id, timerange=(None, None)
    )
    self.assertLen(hist, 2)
    self.assertEqual(hist[0].boot_time, 124)
    self.assertEqual(hist[1].boot_time, 123)

  def testReadClientStartupInfoHistoryWithTimerangeWithBothFromTo(self):
    self.client_id = db_test_utils.InitializeClient(self.db)

    timestamp_before = self.db.Now()

    startup_1 = jobs_pb2.StartupInfo()
    startup_1.boot_time = 1
    self.db.WriteClientStartupInfo(self.client_id, startup_1)

    timestamp_between = self.db.Now()

    startup_2 = jobs_pb2.StartupInfo()
    startup_2.boot_time = 2
    startup_2.client_info.client_version = 2
    self.db.WriteClientStartupInfo(self.client_id, startup_2)
    timestamp_after = self.db.Now()

    hist = self.db.ReadClientStartupInfoHistory(
        self.client_id, timerange=(timestamp_before, timestamp_between)
    )
    self.assertLen(hist, 1)
    self.assertEqual(hist[0].boot_time, 1)

    hist = self.db.ReadClientStartupInfoHistory(
        self.client_id, timerange=(timestamp_between, timestamp_after)
    )
    self.assertLen(hist, 1)
    self.assertEqual(hist[0].boot_time, 2)

    hist = self.db.ReadClientStartupInfoHistory(
        self.client_id, timerange=(timestamp_before, timestamp_after)
    )
    self.assertLen(hist, 2)
    self.assertEqual(hist[0].boot_time, 2)
    self.assertEqual(hist[1].boot_time, 1)

  def testReadClientStartupInfoHistoryWithTimerangeWithFromOnly(self):
    self.client_id = db_test_utils.InitializeClient(self.db)

    startup_1 = jobs_pb2.StartupInfo()
    startup_1.boot_time = 1
    self.db.WriteClientStartupInfo(self.client_id, startup_1)

    timestamp_between = self.db.Now()

    startup_2 = jobs_pb2.StartupInfo()
    startup_2.boot_time = 2
    self.db.WriteClientStartupInfo(self.client_id, startup_2)

    hist = self.db.ReadClientStartupInfoHistory(
        self.client_id, timerange=(timestamp_between, None)
    )
    self.assertLen(hist, 1)
    self.assertEqual(hist[0].boot_time, 2)

  def testReadClientStartupInfoHistoryWithTimerangeWithToOnly(self):
    self.client_id = db_test_utils.InitializeClient(self.db)

    startup_1 = jobs_pb2.StartupInfo()
    startup_1.boot_time = 1
    self.db.WriteClientStartupInfo(self.client_id, startup_1)

    timestamp_between = rdfvalue.RDFDatetime(
        self.db.ReadClientStartupInfo(self.client_id).timestamp
    )

    startup_2 = jobs_pb2.StartupInfo()
    startup_2.boot_time = 2
    startup_2.client_info.client_version = 2
    self.db.WriteClientStartupInfo(self.client_id, startup_2)

    hist = self.db.ReadClientStartupInfoHistory(
        self.client_id, timerange=(None, timestamp_between)
    )
    self.assertLen(hist, 1)
    self.assertEqual(hist[0].boot_time, 1)

  def testReadClientStartupInfoHistoryWithEmptyHistory(self):
    self.client_id = db_test_utils.InitializeClient(self.db)

    timestamp_1 = self.db.Now()
    # No startup info written.
    timestamp_2 = self.db.Now()

    hist = self.db.ReadClientStartupInfoHistory(
        self.client_id, timerange=(timestamp_1, timestamp_2)
    )
    self.assertEmpty(hist)

  def testReadClientStartupInfoHistoryIncludesSnapshotCollectionsByDefault(
      self,
  ):
    self.client_id = db_test_utils.InitializeClient(self.db)

    snapshot = objects_pb2.ClientSnapshot(client_id=self.client_id)
    snapshot.startup_info.boot_time = 123
    self.db.WriteClientSnapshot(snapshot)

    hist = self.db.ReadClientStartupInfoHistory(self.client_id)
    self.assertLen(hist, 1)
    self.assertEqual(hist[0].boot_time, 123)

  def testReadClientStartupInfoHistoryWithExcludeSnapshotCollections(self):
    self.client_id = db_test_utils.InitializeClient(self.db)

    startup = jobs_pb2.StartupInfo()
    startup.boot_time = 123
    startup.client_info.client_version = 1
    self.db.WriteClientStartupInfo(self.client_id, startup)

    snapshot = objects_pb2.ClientSnapshot(client_id=self.client_id)
    snapshot.startup_info.boot_time = 124
    self.db.WriteClientSnapshot(snapshot)

    hist = self.db.ReadClientStartupInfoHistory(
        self.client_id, exclude_snapshot_collections=True
    )
    self.assertLen(hist, 1)
    self.assertIsInstance(hist[0], jobs_pb2.StartupInfo)
    self.assertEqual(hist[0].boot_time, 123)

  def testClientSummary(self):
    d = self.db

    client_id_1 = db_test_utils.InitializeClient(self.db)
    client_id_2 = db_test_utils.InitializeClient(self.db)
    client_id_3 = db_test_utils.InitializeClient(self.db)

    d.WriteClientSnapshot(
        objects_pb2.ClientSnapshot(
            client_id=client_id_1,
            knowledge_base=knowledge_base_pb2.KnowledgeBase(
                fqdn="test1234.examples.com"
            ),
            kernel="12.3",
        )
    )
    d.WriteClientSnapshot(
        objects_pb2.ClientSnapshot(
            client_id=client_id_1,
            knowledge_base=knowledge_base_pb2.KnowledgeBase(
                fqdn="test1234.examples.com"
            ),
            kernel="12.4",
        )
    )

    d.WriteClientSnapshot(
        objects_pb2.ClientSnapshot(
            client_id=client_id_2,
            knowledge_base=knowledge_base_pb2.KnowledgeBase(
                fqdn="test1235.examples.com"
            ),
            kernel="12.4",
        )
    )

    hist = d.ReadClientSnapshotHistory(client_id_1)
    self.assertLen(hist, 2)

    # client_3 should be excluded - no snapshot yet
    res = d.MultiReadClientSnapshot([client_id_1, client_id_2, client_id_3])
    self.assertLen(res, 3)
    self.assertIsInstance(res[client_id_1], objects_pb2.ClientSnapshot)
    self.assertIsInstance(res[client_id_2], objects_pb2.ClientSnapshot)
    self.assertIsNotNone(res[client_id_1].timestamp)
    self.assertIsNotNone(res[client_id_2].timestamp)
    self.assertEqual(
        res[client_id_1].knowledge_base.fqdn, "test1234.examples.com"
    )
    self.assertEqual(res[client_id_1].kernel, "12.4")
    self.assertEqual(
        res[client_id_2].knowledge_base.fqdn, "test1235.examples.com"
    )
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
    d.AddClientKeywords(
        client_id_1,
        [
            "joe",
            "machine.test.example1.com",
            "machine.test.example1",
            "machine.test",
            "machine",
            "🚀",
        ],
    )
    d.AddClientKeywords(
        client_id_2,
        [
            "fred",
            "machine.test.example2.com",
            "machine.test.example2",
            "machine.test",
            "machine",
            "🚀🚀",
        ],
    )
    d.AddClientKeywords(client_id_3, ["foo", "bar", "baz"])

    res = d.ListClientsForKeywords(["fred", "machine", "missing"])
    self.assertEqual(res["fred"], [client_id_2])
    self.assertCountEqual(res["machine"], [client_id_1, client_id_2])
    self.assertEqual(res["missing"], [])

    for kw, client_id in [("🚀", client_id_1), ("🚀🚀", client_id_2)]:
      res = d.ListClientsForKeywords([kw])
      self.assertEqual(
          res[kw],
          [client_id],
          "Expected [%s] when reading keyword %s, got %s"
          % (client_id, kw, res[kw]),
      )

  def testClientKeywordsTimeRanges(self):
    d = self.db
    client_id = db_test_utils.InitializeClient(self.db)

    d.AddClientKeywords(client_id, ["hostname1"])
    change_time = rdfvalue.RDFDatetime.Now()
    d.AddClientKeywords(client_id, ["hostname2"])

    res = d.ListClientsForKeywords(
        ["hostname1", "hostname2"], start_time=change_time
    )
    self.assertEqual(res["hostname1"], [])
    self.assertEqual(res["hostname2"], [client_id])

  def testRemoveClientKeyword(self):
    d = self.db
    client_id = db_test_utils.InitializeClient(self.db)
    temporary_kw = "investigation42"
    d.AddClientKeywords(
        client_id,
        [
            "joe",
            "machine.test.example.com",
            "machine.test.example",
            "machine.test",
            temporary_kw,
        ],
    )
    self.assertEqual(
        d.ListClientsForKeywords([temporary_kw])[temporary_kw], [client_id]
    )
    d.RemoveClientKeyword(client_id, temporary_kw)
    self.assertEqual(d.ListClientsForKeywords([temporary_kw])[temporary_kw], [])
    self.assertEqual(d.ListClientsForKeywords(["joe"])["joe"], [client_id])

  def testMultiAddClientKeywordsSingleClientSingleKeyword(self):
    client_id = db_test_utils.InitializeClient(self.db)

    self.db.MultiAddClientKeywords([client_id], ["foo"])

    foo_clients = self.db.ListClientsForKeywords(["foo"])["foo"]
    self.assertEqual(foo_clients, [client_id])

  def testMultiAddClientKeywordsSingleClientMultipleKeywords(self):
    client_id = db_test_utils.InitializeClient(self.db)

    self.db.MultiAddClientKeywords([client_id], ["foo", "bar"])

    foo_clients = self.db.ListClientsForKeywords(["foo"])["foo"]
    self.assertEqual(foo_clients, [client_id])

    bar_clients = self.db.ListClientsForKeywords(["bar"])["bar"]
    self.assertEqual(bar_clients, [client_id])

  def testMultiAddClientKeywordsMultipleClientsSingleKeyword(self):
    client_id_1 = db_test_utils.InitializeClient(self.db)
    client_id_2 = db_test_utils.InitializeClient(self.db)

    self.db.MultiAddClientKeywords([client_id_1, client_id_2], ["foo"])

    foo_clients = self.db.ListClientsForKeywords(["foo"])["foo"]
    self.assertCountEqual(foo_clients, [client_id_1, client_id_2])

  def testMultiAddClientKeywordsMultipleClientsMultipleKeywords(self):
    client_id_1 = db_test_utils.InitializeClient(self.db)
    client_id_2 = db_test_utils.InitializeClient(self.db)

    self.db.MultiAddClientKeywords([client_id_1, client_id_2], ["foo", "bar"])

    foo_clients = self.db.ListClientsForKeywords(["foo"])["foo"]
    self.assertCountEqual(foo_clients, [client_id_1, client_id_2])

    bar_clients = self.db.ListClientsForKeywords(["bar"])["bar"]
    self.assertCountEqual(bar_clients, [client_id_1, client_id_2])

  def testMultiAddClientKeywordsMultipleClientsNoKeywords(self):
    client_id_1 = db_test_utils.InitializeClient(self.db)
    client_id_2 = db_test_utils.InitializeClient(self.db)

    # Should not fail.
    self.db.MultiAddClientKeywords([client_id_1, client_id_2], [])

  def testMultiAddClientKeywordsNoClientsMultipleKeywords(self):
    self.db.MultiAddClientKeywords([], ["foo", "bar"])

    foo_clients = self.db.ListClientsForKeywords(["foo"])["foo"]
    self.assertEmpty(foo_clients)

    bar_clients = self.db.ListClientsForKeywords(["bar"])["bar"]
    self.assertEmpty(bar_clients)

  def testMultiAddClientKeywordsUnknownClient(self):
    with self.assertRaises(db.AtLeastOneUnknownClientError) as context:
      self.db.MultiAddClientKeywords(["C.4815162342"], ["foo", "bar"])

    self.assertEqual(context.exception.client_ids, ["C.4815162342"])

  def testClientLabels(self):
    d = self.db

    self.db.WriteGRRUser("owner1")
    self.db.WriteGRRUser("owner2")
    client_id = db_test_utils.InitializeClient(self.db)

    self.assertEqual(d.ReadClientLabels(client_id), [])

    d.AddClientLabels(client_id, "owner1", ["label1🚀"])
    d.AddClientLabels(client_id, "owner2", ["label2", "label🚀3"])

    all_labels = [
        objects_pb2.ClientLabel(name="label1🚀", owner="owner1"),
        objects_pb2.ClientLabel(name="label2", owner="owner2"),
        objects_pb2.ClientLabel(name="label🚀3", owner="owner2"),
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
        d.ReadClientLabels(client_id),
        [
            objects_pb2.ClientLabel(name="label1🚀", owner="owner1"),
            objects_pb2.ClientLabel(name="label2", owner="owner2"),
        ],
    )

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
        objects_pb2.ClientLabel(name="🚀🍰1", owner="owner1"),
        objects_pb2.ClientLabel(name="🚀🍰2", owner="owner2"),
        objects_pb2.ClientLabel(name="🚀🍰3", owner="owner2"),
    ]

    self.assertEqual(d.ReadClientLabels(client_id), all_labels)

    d.RemoveClientLabels(client_id, "owner1", ["does not exist"])
    self.assertEqual(d.ReadClientLabels(client_id), all_labels)

    # This label is actually owned by owner2.
    d.RemoveClientLabels(client_id, "owner1", ["🚀🍰3"])
    self.assertEqual(d.ReadClientLabels(client_id), all_labels)

    d.RemoveClientLabels(client_id, "owner2", ["🚀🍰3"])
    self.assertEqual(
        d.ReadClientLabels(client_id),
        [
            objects_pb2.ClientLabel(name="🚀🍰1", owner="owner1"),
            objects_pb2.ClientLabel(name="🚀🍰2", owner="owner2"),
        ],
    )

  def testLongClientLabelCanBeSaved(self):
    label = "x" + "🚀" * (db.MAX_LABEL_LENGTH - 2) + "x"
    d = self.db
    self.db.WriteGRRUser("owner1")
    client_id = db_test_utils.InitializeClient(self.db)
    d.AddClientLabels(client_id, "owner1", [label])
    self.assertEqual(
        d.ReadClientLabels(client_id),
        [
            objects_pb2.ClientLabel(name=label, owner="owner1"),
        ],
    )

  def testTooLongClientLabelRaises(self):
    label = "a" * (db.MAX_LABEL_LENGTH + 1)
    d = self.db
    self.db.WriteGRRUser("owner1")
    client_id = db_test_utils.InitializeClient(self.db)
    with self.assertRaises(ValueError):
      d.AddClientLabels(client_id, "owner1", [label])

  def testMultiAddClientLabelsSingleClientMultipleLabels(self):
    owner = db_test_utils.InitializeUser(self.db)
    client_id = db_test_utils.InitializeClient(self.db)

    self.db.MultiAddClientLabels([client_id], owner, ["abc", "def"])

    labels = self.db.MultiReadClientLabels([client_id])[client_id]
    labels.sort(key=lambda label: label.name)

    self.assertEqual(labels[0].owner, owner)
    self.assertEqual(labels[0].name, "abc")
    self.assertEqual(labels[1].owner, owner)
    self.assertEqual(labels[1].name, "def")

  def testMultiAddClientLabelsMultipleClientsSingleLabel(self):
    owner = db_test_utils.InitializeUser(self.db)
    client_id_1 = db_test_utils.InitializeClient(self.db)
    client_id_2 = db_test_utils.InitializeClient(self.db)

    self.db.MultiAddClientLabels([client_id_1, client_id_2], owner, ["abc"])

    labels = self.db.MultiReadClientLabels([client_id_1, client_id_2])

    self.assertEqual(labels[client_id_1][0].owner, owner)
    self.assertEqual(labels[client_id_1][0].name, "abc")

    self.assertEqual(labels[client_id_2][0].owner, owner)
    self.assertEqual(labels[client_id_2][0].name, "abc")

  def testMultiAddClientLabelsMultipleClientsMultipleLabels(self):
    owner = db_test_utils.InitializeUser(self.db)
    client_id_1 = db_test_utils.InitializeClient(self.db)
    client_id_2 = db_test_utils.InitializeClient(self.db)

    self.db.MultiAddClientLabels(
        [client_id_1, client_id_2], owner, ["abc", "def"]
    )

    labels = self.db.MultiReadClientLabels([client_id_1, client_id_2])

    client_1_labels = labels[client_id_1]
    client_1_labels.sort(key=lambda label: label.name)
    self.assertEqual(client_1_labels[0].owner, owner)
    self.assertEqual(client_1_labels[0].name, "abc")
    self.assertEqual(client_1_labels[1].owner, owner)
    self.assertEqual(client_1_labels[1].name, "def")

    client_2_labels = labels[client_id_2]
    client_1_labels.sort(key=lambda label: label.name)
    self.assertEqual(client_2_labels[0].owner, owner)
    self.assertEqual(client_2_labels[0].name, "abc")
    self.assertEqual(client_2_labels[1].owner, owner)
    self.assertEqual(client_2_labels[1].name, "def")

  def testMultiAddClientLabelsNoClientsMultipleLabels(self):
    owner = db_test_utils.InitializeUser(self.db)

    self.db.MultiAddClientLabels([], owner, ["abc", "def"])  # Should not fail.

  def testMultiAddClientLabelsMultipleClientsNoLabels(self):
    owner = db_test_utils.InitializeUser(self.db)
    client_id_1 = db_test_utils.InitializeClient(self.db)
    client_id_2 = db_test_utils.InitializeClient(self.db)

    self.db.MultiAddClientLabels([client_id_1, client_id_2], owner, [])

    labels = self.db.MultiReadClientLabels([client_id_1, client_id_2])
    self.assertEqual(labels[client_id_1], [])
    self.assertEqual(labels[client_id_2], [])

  def testMultiAddClientLabelsUnknownClient(self):
    owner = db_test_utils.InitializeUser(self.db)

    with self.assertRaises(db.AtLeastOneUnknownClientError) as context:
      self.db.MultiAddClientLabels(["C.4815162342"], owner, ["foo"])

    self.assertEqual(context.exception.client_ids, ["C.4815162342"])

  def testMultiAddClientLabelsUnknownUser(self):
    client_id = db_test_utils.InitializeClient(self.db)

    with self.assertRaises(db.UnknownGRRUserError) as context:
      self.db.MultiAddClientLabels([client_id], "owner", ["foo"])

    self.assertEqual(context.exception.username, "owner")

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

    d.WriteClientStartupInfo(client_id, jobs_pb2.StartupInfo(boot_time=1337))
    d.WriteClientStartupInfo(client_id, jobs_pb2.StartupInfo(boot_time=2000))

    last_is = d.ReadClientStartupInfo(client_id)
    self.assertIsInstance(last_is, jobs_pb2.StartupInfo)
    self.assertEqual(last_is.boot_time, 2000)

    md = self.db.ReadClientMetadata(client_id)
    self.assertEqual(md.startup_info_timestamp, last_is.timestamp)

  def testReadClientStartupInfoNone(self):
    client_id = db_test_utils.InitializeClient(self.db)
    self.assertIsNone(self.db.ReadClientStartupInfo(client_id))

  def testWriteClientRRGStartupUnknownClient(self):
    client_id = "C.1234567890ABCDEF"

    startup = rrg_startup_pb2.Startup()

    with self.assertRaises(db.UnknownClientError) as context:
      self.db.WriteClientRRGStartup(client_id, startup)

    self.assertEqual(context.exception.client_id, client_id)

  def testWriteClientRRGStartupNone(self):
    client_id = db_test_utils.InitializeClient(self.db)

    info = self.db.ReadClientFullInfo(client_id)
    self.assertFalse(info.HasField("last_rrg_startup"))

  def testWriteClientRRGStartupSingle(self):
    client_id = db_test_utils.InitializeClient(self.db)

    startup = rrg_startup_pb2.Startup()
    startup.metadata.version.major = 1
    startup.metadata.version.minor = 2
    startup.metadata.version.patch = 3
    self.db.WriteClientRRGStartup(client_id, startup)

    info = self.db.ReadClientFullInfo(client_id)
    self.assertEqual(info.last_rrg_startup, startup)

  def testWriteClientRRGStartupMultipleStartups(self):
    client_id = db_test_utils.InitializeClient(self.db)

    startup_1 = rrg_startup_pb2.Startup()
    startup_1.metadata.version.major = 1
    startup_1.metadata.version.minor = 2
    startup_1.metadata.version.patch = 3
    self.db.WriteClientRRGStartup(client_id, startup_1)

    startup_2 = rrg_startup_pb2.Startup()
    startup_2.metadata.version.major = 4
    startup_2.metadata.version.minor = 5
    startup_2.metadata.version.patch = 6
    self.db.WriteClientRRGStartup(client_id, startup_2)

    info = self.db.ReadClientFullInfo(client_id)
    self.assertEqual(info.last_rrg_startup, startup_2)

  def testWriteClientRRGStartupMultipleClients(self):
    client_id_1 = db_test_utils.InitializeClient(self.db)
    client_id_2 = db_test_utils.InitializeClient(self.db)

    startup_1 = rrg_startup_pb2.Startup()
    startup_1.metadata.version.major = 1
    startup_1.metadata.version.minor = 2
    startup_1.metadata.version.patch = 3
    self.db.WriteClientRRGStartup(client_id_1, startup_1)

    startup_2 = rrg_startup_pb2.Startup()
    startup_2.metadata.version.major = 4
    startup_2.metadata.version.minor = 5
    startup_2.metadata.version.patch = 6
    self.db.WriteClientRRGStartup(client_id_2, startup_2)

    info_1 = self.db.ReadClientFullInfo(client_id_1)
    self.assertEqual(info_1.last_rrg_startup, startup_1)

    info_2 = self.db.ReadClientFullInfo(client_id_2)
    self.assertEqual(info_2.last_rrg_startup, startup_2)

  def testReadClientRRGStartupUnknownClient(self):
    with self.assertRaises(db.UnknownClientError):
      self.db.ReadClientRRGStartup("C.0123456789ABCDEF")

  def testReadClientRRGStartupNone(self):
    client_id = db_test_utils.InitializeClient(self.db)

    self.assertIsNone(self.db.ReadClientRRGStartup(client_id))

  def testReadClientRRGStartupSingle(self):
    client_id = db_test_utils.InitializeClient(self.db)

    startup = rrg_startup_pb2.Startup()
    startup.metadata.version.major = 1
    startup.metadata.version.minor = 2
    startup.metadata.version.patch = 3
    self.db.WriteClientRRGStartup(client_id, startup)

    self.assertEqual(self.db.ReadClientRRGStartup(client_id), startup)

  def testReadClientRRGStartupMultipleStartups(self):
    client_id = db_test_utils.InitializeClient(self.db)

    startup_1 = rrg_startup_pb2.Startup()
    startup_1.metadata.version.major = 1
    startup_1.metadata.version.minor = 2
    startup_1.metadata.version.patch = 3
    self.db.WriteClientRRGStartup(client_id, startup_1)

    startup_2 = rrg_startup_pb2.Startup()
    startup_2.metadata.version.major = 4
    startup_2.metadata.version.minor = 5
    startup_2.metadata.version.patch = 6
    self.db.WriteClientRRGStartup(client_id, startup_2)

    self.assertEqual(self.db.ReadClientRRGStartup(client_id), startup_2)

  def testReadClientRRGStartupMultipleClients(self):
    client_id_1 = db_test_utils.InitializeClient(self.db)
    client_id_2 = db_test_utils.InitializeClient(self.db)

    startup_1 = rrg_startup_pb2.Startup()
    startup_1.metadata.version.major = 1
    startup_1.metadata.version.minor = 2
    startup_1.metadata.version.patch = 3
    self.db.WriteClientRRGStartup(client_id_1, startup_1)

    startup_2 = rrg_startup_pb2.Startup()
    startup_2.metadata.version.major = 4
    startup_2.metadata.version.minor = 5
    startup_2.metadata.version.patch = 6
    self.db.WriteClientRRGStartup(client_id_2, startup_2)

    self.assertEqual(self.db.ReadClientRRGStartup(client_id_1), startup_1)
    self.assertEqual(self.db.ReadClientRRGStartup(client_id_2), startup_2)

  def testCrashHistory(self):
    d = self.db

    client_id = db_test_utils.InitializeClient(self.db)

    ci = jobs_pb2.ClientCrash(timestamp=12345, crash_message="Crash #1")
    d.WriteClientCrashInfo(client_id, ci)
    ci.crash_message = "Crash #2"
    d.WriteClientCrashInfo(client_id, ci)
    ci.crash_message = "Crash #3"
    d.WriteClientCrashInfo(client_id, ci)

    last_is = d.ReadClientCrashInfo(client_id)
    self.assertIsInstance(last_is, jobs_pb2.ClientCrash)
    self.assertEqual(last_is.crash_message, "Crash #3")
    self.assertTrue(last_is.HasField("timestamp"))

    hist = d.ReadClientCrashInfoHistory(client_id)
    self.assertLen(hist, 3)
    self.assertEqual(
        [ci.crash_message for ci in hist], ["Crash #3", "Crash #2", "Crash #1"]
    )
    self.assertGreater(hist[0].timestamp, hist[1].timestamp)
    self.assertGreater(hist[1].timestamp, hist[2].timestamp)

    md = self.db.ReadClientMetadata(client_id)
    self.assertEqual(md.last_crash_timestamp, int(hist[0].timestamp))

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

    cl = objects_pb2.ClientSnapshot(
        client_id=client_id,
        knowledge_base=knowledge_base_pb2.KnowledgeBase(
            fqdn="test1234.examples.com"
        ),
        kernel="12.3",
    )
    d.WriteClientSnapshot(cl)
    si = jobs_pb2.StartupInfo(boot_time=1)
    d.WriteClientStartupInfo(client_id, si)
    d.AddClientLabels(client_id, "test_owner", ["test_label1", "test_label2"])

    full_info = d.ReadClientFullInfo(client_id)

    # No timestamp on the expected values, so we clear them.
    full_info.last_snapshot.ClearField("timestamp")
    full_info.last_snapshot.startup_info.ClearField("timestamp")
    full_info.last_startup_info.ClearField("timestamp")

    self.assertEqual(full_info.last_snapshot.client_id, client_id)
    self.assertEqual(full_info.last_snapshot.kernel, "12.3")
    self.assertEqual(
        full_info.last_snapshot.knowledge_base.fqdn, "test1234.examples.com"
    )

    self.assertEqual(full_info.last_startup_info.boot_time, 1)

    self.assertLen(full_info.labels, 2)
    self.assertEqual(full_info.labels[0].owner, "test_owner")
    self.assertEqual(full_info.labels[0].name, "test_label1")

    self.assertEqual(full_info.labels[1].owner, "test_owner")
    self.assertEqual(full_info.labels[1].name, "test_label2")

  def testReadClientFullInfoTimestamps(self):
    client_id = db_test_utils.InitializeClient(self.db)

    first_seen_time = rdfvalue.RDFDatetime.Now()
    last_ping_time = rdfvalue.RDFDatetime.Now()
    last_foreman_time = rdfvalue.RDFDatetime.Now()

    self.db.WriteClientMetadata(
        client_id=client_id,
        first_seen=first_seen_time,
        last_ping=last_ping_time,
        last_foreman=last_foreman_time,
    )

    pre_time = self.db.Now()

    startup_info = jobs_pb2.StartupInfo()
    startup_info.client_info.client_name = "rrg"
    self.db.WriteClientStartupInfo(client_id, startup_info)

    crash_info = jobs_pb2.ClientCrash()
    crash_info.client_info.client_name = "grr"
    self.db.WriteClientCrashInfo(client_id, crash_info)

    post_time = self.db.Now()

    full_info = self.db.ReadClientFullInfo(client_id)
    self.assertEqual(full_info.metadata.first_seen, int(first_seen_time))
    self.assertEqual(full_info.metadata.ping, int(last_ping_time))
    self.assertEqual(
        full_info.metadata.last_foreman_time, int(last_foreman_time)
    )

    self.assertBetween(
        full_info.metadata.startup_info_timestamp, int(pre_time), int(post_time)
    )
    self.assertBetween(
        full_info.metadata.last_crash_timestamp, int(pre_time), int(post_time)
    )

  def _SetupFullInfoClients(self):
    self.db.WriteGRRUser("test_owner")

    for i in range(10):
      client_id = db_test_utils.InitializeClient(
          self.db, "C.000000005000000%d" % i
      )

      cl = objects_pb2.ClientSnapshot(
          client_id=client_id,
          knowledge_base=knowledge_base_pb2.KnowledgeBase(
              fqdn="test%d.examples.com" % i
          ),
          kernel="12.3.%d" % i,
      )
      self.db.WriteClientSnapshot(cl)
      si = jobs_pb2.StartupInfo(boot_time=i)
      self.db.WriteClientStartupInfo(client_id, si)
      self.db.AddClientLabels(
          client_id,
          "test_owner",
          ["test_label-a-%d" % i, "test_label-b-%d" % i],
      )

  def _VerifySnapshots(self, snapshots):
    snapshots = sorted(snapshots, key=lambda s: s.client_id)
    self.assertLen(snapshots, 10)
    for i, s in enumerate(snapshots):
      self.assertEqual(s.client_id, "C.000000005000000%d" % i)
      self.assertEqual(s.knowledge_base.fqdn, "test%d.examples.com" % i)

  def _SetupLastPingClients(self, now):
    time_past = now - rdfvalue.Duration.From(1, rdfvalue.DAYS)

    client_ids_to_ping = {}
    for i in range(10):
      client_id = db_test_utils.InitializeClient(self.db)

      self.db.WriteClientSnapshot(
          objects_pb2.ClientSnapshot(client_id=client_id)
      )
      ping = time_past if i % 2 == 0 else now
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
        list(client_ids_to_ping.keys()), min_last_ping=cutoff_time
    )
    self.assertCountEqual(expected_client_ids, full_infos)

  def testMultiReadClientsFullInfoWithEmptyList(self):
    d = self.db

    self.assertEqual(d.MultiReadClientFullInfo([]), {})

  def testMultiReadClientsFullInfoSkipsMissingClients(self):
    d = self.db

    present_client_id = "C.fc413187fefa1dcf"
    # Typical initial FS enabled write
    d.WriteClientMetadata(present_client_id)

    missing_client_id = "C.00413187fefa1dcf"

    full_infos = d.MultiReadClientFullInfo(
        [present_client_id, missing_client_id]
    )
    self.assertEqual(list(full_infos.keys()), [present_client_id])

  def testMultiReadClientsFullInfoNoSnapshot(self):
    d = self.db

    client_id = "C.fc413187fefa1dcf"
    d.WriteClientMetadata(client_id)
    full_info = d.MultiReadClientFullInfo([client_id])[client_id]
    self.assertEqual(full_info.last_snapshot.client_id, client_id)

  def testReadClientMetadataRaisesWhenClientIsMissing(self):
    with self.assertRaises(db.UnknownClientError):
      self.db.ReadClientMetadata("C.00413187fefa1dcf")

  def testReadClientFullInfoRaisesWhenClientIsMissing(self):
    with self.assertRaises(db.UnknownClientError):
      self.db.ReadClientFullInfo("C.00413187fefa1dcf")

  @mock.patch.object(db, "_MAX_CLIENT_PLATFORM_LENGTH", 10)
  def testWriteClientSnapshotLongPlatform(self):
    snapshot = objects_pb2.ClientSnapshot(client_id="C.0000000000000001")
    snapshot.knowledge_base.os = "🚀" * 12
    with self.assertRaises(db.StringTooLongError):
      self.db.WriteClientSnapshot(snapshot)

  def testWriteClientSnapshotSequence(self):
    count = 64

    client_id = db_test_utils.InitializeClient(self.db)
    snapshot = objects_pb2.ClientSnapshot(client_id=client_id)

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

    written_snapshot = objects_pb2.ClientSnapshot()
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
    snapshot = objects_pb2.ClientSnapshot(client_id=client_id)
    snapshot.startup_info.client_info.client_version = 42
    self.db.WriteClientSnapshot(snapshot)

    # Crash information
    self.db.WriteClientCrashInfo(
        client_id,
        jobs_pb2.ClientCrash(timestamp=12345, crash_message="Crash #1"),
    )

    # Index keywords.
    self.db.AddClientKeywords(client_id, ["machine.test.example1.com"])

    # A flow.
    flow_id = flow.RandomFlowId()
    self.db.WriteFlowObject(
        flows_pb2.Flow(client_id=client_id, flow_id=flow_id)
    )
    # A flow request.
    self.db.WriteFlowRequests([
        flows_pb2.FlowRequest(
            client_id=client_id, flow_id=flow_id, request_id=1
        )
    ])

    # A flow response.
    self.db.WriteFlowResponses([
        flows_pb2.FlowResponse(
            client_id=client_id, flow_id=flow_id, request_id=1, response_id=1
        )
    ])

    # A flow processing request.
    self.db.WriteFlowProcessingRequests(
        [flows_pb2.FlowProcessingRequest(client_id=client_id, flow_id=flow_id)]
    )

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

    # A flow.
    with self.assertRaises(db.UnknownFlowError):
      self.db.ReadFlowObject(client_id, flow_id)

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

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.os_version = "3.14"
    snapshot.arch = "i686"
    snapshot.knowledge_base.os = "redox"
    snapshot.knowledge_base.os_major_version = 3
    snapshot.knowledge_base.os_minor_version = 14
    self.db.WriteClientSnapshot(snapshot)

    startup = jobs_pb2.StartupInfo()
    startup.boot_time = int(rdfvalue.RDFDatetime.Now())
    startup.client_info.client_version = 1337
    self.db.WriteClientStartupInfo(client_id, startup)

    crash = jobs_pb2.ClientCrash()
    crash.client_id = client_id
    crash.client_info.client_version = 1337
    crash.timestamp = int(rdfvalue.RDFDatetime.Now())
    self.db.WriteClientCrashInfo(client_id, crash)

    self.db.DeleteClient(client_id)

    with self.assertRaises(db.UnknownClientError):
      self.db.ReadClientFullInfo(client_id)

  def testDeleteClientWithPaths(self):
    client_id = db_test_utils.InitializeClient(self.db)

    path_info_0 = objects_pb2.PathInfo(
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("foo", "bar", "baz"),
    )
    path_info_0.stat_entry.st_size = 42

    path_info_1 = objects_pb2.PathInfo(
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("foo", "bar", "quux"),
    )
    path_info_1.hash_entry.sha256 = b"quux"

    path_info_2 = objects_pb2.PathInfo(
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("foo", "norf", "thud"),
    )
    path_info_2.stat_entry.st_size = 1337
    path_info_2.hash_entry.sha256 = b"norf"

    self.db.WritePathInfos(client_id, [path_info_0, path_info_1, path_info_2])

    self.db.DeleteClient(client_id)

    with self.assertRaises(db.UnknownClientError):
      self.db.ReadClientFullInfo(client_id)

  def testFleetspeakValidationInfoIsInitiallyUnset(self):
    client_id = "C.fc413187fefa1dcf"
    self.db.WriteClientMetadata(
        client_id, first_seen=rdfvalue.RDFDatetime(100000000)
    )

    res = self.db.MultiReadClientMetadata([client_id])
    self.assertLen(res, 1)
    metadata = res[client_id]
    self.assertFalse(metadata.HasField("last_fleetspeak_validation_info"))

  def testWritesFleetspeakValidationInfo(self):
    client_id = "C.fc413187fefa1dcf"

    self.db.WriteClientMetadata(
        client_id, fleetspeak_validation_info={"foo": "bar", "12": "34"}
    )

    res = self.db.MultiReadClientMetadata([client_id])
    self.assertLen(res, 1)
    metadata = res[client_id]
    info = models_clients.FleetspeakValidationInfoToDict(
        metadata.last_fleetspeak_validation_info
    )
    self.assertEqual(info, {"foo": "bar", "12": "34"})

  def testOverwritesFleetspeakValidationInfo(self):
    client_id = "C.fc413187fefa1dcf"

    self.db.WriteClientMetadata(
        client_id, fleetspeak_validation_info={"foo": "bar", "12": "34"}
    )
    self.db.WriteClientMetadata(
        client_id, fleetspeak_validation_info={"foo": "bar", "new": "1234"}
    )

    res = self.db.MultiReadClientMetadata([client_id])
    self.assertLen(res, 1)
    metadata = res[client_id]
    info = models_clients.FleetspeakValidationInfoToDict(
        metadata.last_fleetspeak_validation_info
    )
    self.assertEqual(info, {"foo": "bar", "new": "1234"})

  def testRemovesFleetspeakValidationInfoWhenValidationInfoIsEmpty(self):
    client_id = "C.fc413187fefa1dcf"

    self.db.WriteClientMetadata(
        client_id, fleetspeak_validation_info={"foo": "bar"}
    )
    self.db.WriteClientMetadata(client_id, fleetspeak_validation_info={})

    res = self.db.MultiReadClientMetadata([client_id])
    self.assertLen(res, 1)
    metadata = res[client_id]
    self.assertFalse(metadata.HasField("last_fleetspeak_validation_info"))

  def testKeepsFleetspeakValidationInfoWhenValidationInfoIsNotPresent(self):
    client_id = "C.fc413187fefa1dcf"

    self.db.WriteClientMetadata(
        client_id, fleetspeak_validation_info={"foo": "bar"}
    )
    self.db.WriteClientMetadata(client_id)

    res = self.db.MultiReadClientMetadata([client_id])
    self.assertLen(res, 1)
    metadata = res[client_id]
    info = models_clients.FleetspeakValidationInfoToDict(
        metadata.last_fleetspeak_validation_info
    )
    self.assertEqual(info, {"foo": "bar"})


# This file is a test library and thus does not require a __main__ block.
