#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
import abc

from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import crypto
from grr.lib.rdfvalues import objects
from grr.server import db

CERT = crypto.RDFX509Cert("""-----BEGIN CERTIFICATE-----
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
-----END CERTIFICATE-----""")


class DatabaseTestMixin(object):
  """An abstract class for testing db.Database implementations.

  Implementations should override CreateDatabase in order to produce
  a test suite for a particular implementation of db.Database.

  This class does not inherit from `TestCase` to prevent the test runner from
  executing its method. Instead it should be mixed into the actual test classes.
  """
  __metaclass__ = abc.ABCMeta

  @abc.abstractmethod
  def CreateDatabase(self):
    """Create a test database.

    Returns:
      A pair (db, cleanup), where db is an instance of db.Database to be tested
      and cleanup is a function which destroys db, releasing any resources held
      by it.
    """

  def setUp(self):
    self.db, self.cleanup = self.CreateDatabase()

  def tearDown(self):
    if self.cleanup:
      self.cleanup()

  def _InitializeClient(self, client_id):
    self.db.WriteClientMetadata(client_id, fleetspeak_enabled=True)

  def testDatabaseType(self):
    d = self.db
    self.assertIsInstance(d, db.Database)

  def testClientWriteToUnknownClient(self):
    d = self.db
    client_id = "C.fc413187fefa1dcf"

    with self.assertRaises(db.UnknownClientError):
      d.WriteClientSnapshot(objects.ClientSnapshot(client_id=client_id))

    # fleetspeak_enabled not set means update.
    with self.assertRaises(db.UnknownClientError):
      d.WriteClientMetadata(client_id, first_seen=rdfvalue.RDFDatetime.Now())

  def testKeywordWriteToUnknownClient(self):
    d = self.db
    client_id = "C.fc413187fefa1dcf"

    with self.assertRaises(db.UnknownClientError):
      d.AddClientKeywords(client_id, ["keyword"])

    d.RemoveClientKeyword(client_id, "test")

  def testLabelWriteToUnknownClient(self):
    d = self.db
    client_id = "C.fc413187fefa1dcf"

    with self.assertRaises(db.UnknownClientError):
      d.AddClientLabels(client_id, "testowner", ["label"])

    d.RemoveClientLabels(client_id, "testowner", ["label"])

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

    res = d.ReadClientsMetadata([client_id_1, client_id_2])
    self.assertEqual(len(res), 2)

    m1 = res[client_id_1]
    self.assertIsInstance(m1, objects.ClientMetadata)
    self.assertTrue(m1.fleetspeak_enabled)

    m2 = res[client_id_2]
    self.assertIsInstance(m2, objects.ClientMetadata)
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
    res = self.db.ReadClientsMetadata([client_id])
    self.assertEqual(len(res), 1)
    m1 = res[client_id]
    self.assertEqual(m1.first_seen, rdfvalue.RDFDatetime(100000001))
    self.assertEqual(m1.clock, rdfvalue.RDFDatetime(100000011))
    self.assertEqual(m1.last_foreman_time, rdfvalue.RDFDatetime(100000021))
    self.assertEqual(m1.ping, rdfvalue.RDFDatetime(100000031))

  def testClientMetadataPing(self):
    d = self.db

    client_id_1 = "C.fc413187fefa1dcf"
    self._InitializeClient(client_id_1)

    # Typical update on client ping.
    d.WriteClientMetadata(
        client_id_1,
        last_ping=rdfvalue.RDFDatetime(200000000000),
        last_clock=rdfvalue.RDFDatetime(210000000000),
        last_ip=rdf_client.NetworkAddress(human_readable_address="8.8.8.8"),
        last_foreman=rdfvalue.RDFDatetime(220000000000))

    res = d.ReadClientsMetadata([client_id_1])
    self.assertEqual(len(res), 1)
    m1 = res[client_id_1]
    self.assertIsInstance(m1, objects.ClientMetadata)
    self.assertTrue(m1.fleetspeak_enabled)
    self.assertEqual(m1.ping, rdfvalue.RDFDatetime(200000000000))
    self.assertEqual(m1.clock, rdfvalue.RDFDatetime(210000000000))
    self.assertEqual(
        m1.ip, rdf_client.NetworkAddress(human_readable_address="8.8.8.8"))
    self.assertEqual(m1.last_foreman_time, rdfvalue.RDFDatetime(220000000000))

  def testClientMetadataValidatesIP(self):
    d = self.db
    client_id = "C.fc413187fefa1dcf"
    with self.assertRaises(ValueError):
      d.WriteClientMetadata(
          client_id, fleetspeak_enabled=True, last_ip="127.0.0.1")

  def testClientSnapshotHistory(self):
    d = self.db

    client_id = "C.fc413187fefa1dcf"
    self._InitializeClient(client_id)

    client = objects.ClientSnapshot(client_id=client_id, kernel="12.3")
    client.knowledge_base.fqdn = "test1234.examples.com"
    d.WriteClientSnapshot(client)
    client.kernel = "12.4"
    d.WriteClientSnapshot(client)

    hist = d.ReadClientSnapshotHistory(client_id)
    self.assertEqual(len(hist), 2)
    self.assertIsInstance(hist[0], objects.ClientSnapshot)
    self.assertIsInstance(hist[1], objects.ClientSnapshot)
    self.assertGreater(hist[0].timestamp, hist[1].timestamp)
    self.assertIsInstance(hist[0].timestamp, rdfvalue.RDFDatetime)
    self.assertEqual(hist[0].kernel, "12.4")
    self.assertEqual(hist[1].kernel, "12.3")

  def testWriteClientSnapshotHistory(self):
    client_id = "C.0000000000000000"
    self._InitializeClient(client_id)

    client_a = objects.ClientSnapshot(client_id=client_id)
    client_a.kernel = "1.2.3"
    client_a.startup_info.client_info.client_version = 42
    client_a.timestamp = rdfvalue.RDFDatetime.FromHumanReadable("2010-01-01")

    client_b = objects.ClientSnapshot(client_id=client_id)
    client_b.kernel = "4.5.6"
    client_b.startup_info.client_info.client_version = 108
    client_b.timestamp = rdfvalue.RDFDatetime.FromHumanReadable("2010-02-01")

    client_c = objects.ClientSnapshot(client_id=client_id)
    client_c.kernel = "7.8.9"
    client_c.startup_info.client_info.client_version = 707
    client_c.timestamp = rdfvalue.RDFDatetime.FromHumanReadable("2010-03-01")

    self.db.WriteClientSnapshotHistory([client_a, client_b, client_c])

    # Check whether the client history has been recorded correctly.
    history = self.db.ReadClientSnapshotHistory(client_id)
    self.assertEqual(len(history), 3)

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
    self.assertEqual(len(history), 3)

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
    client_id = "C.0000000000000000"
    self._InitializeClient(client_id)

    client_new = objects.ClientSnapshot(client_id=client_id)
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
    client_id = "C.0000000000000000"
    self._InitializeClient(client_id)

    client_old = objects.ClientSnapshot(client_id=client_id)
    client_old.kernel = "1.0.0"
    self.db.WriteClientSnapshot(client_old)

    old_timestamp = self.db.ReadClientSnapshot(client_id).timestamp

    client_new = objects.ClientSnapshot(client_id=client_id)
    client_new.kernel = "2.0.0"
    client_new.timestamp = rdfvalue.RDFDatetime.Now()
    self.db.WriteClientSnapshotHistory([client_new])

    info = self.db.ReadClientFullInfo(client_id)
    self.assertEqual(info.last_snapshot.kernel, "2.0.0")
    self.assertGreater(info.last_snapshot.timestamp, old_timestamp)
    self.assertGreater(info.last_startup_info.timestamp, old_timestamp)

  def testWriteClientSnapshotHistoryDoesNotUpdateLastTimestampIfOlder(self):
    client_id = "C.0000000000000000"
    self._InitializeClient(client_id)

    client_new = objects.ClientSnapshot(client_id=client_id)
    client_new.kernel = "2.0.0"
    self.db.WriteClientSnapshot(client_new)

    new_timestamp = self.db.ReadClientSnapshot(client_id).timestamp

    client_old = objects.ClientSnapshot(client_id=client_id)
    client_old.kernel = "1.0.0"
    client_old.timestamp = new_timestamp - rdfvalue.Duration("1d")
    self.db.WriteClientSnapshotHistory([client_old])

    info = self.db.ReadClientFullInfo(client_id)
    self.assertEqual(info.last_snapshot.kernel, "2.0.0")
    self.assertEqual(info.last_snapshot.timestamp, new_timestamp)
    self.assertEqual(info.last_startup_info.timestamp, new_timestamp)

  def testWriteClientSnapshotHistoryUpdatesOnlyLastClientTimestamp(self):
    client_id = "C.0000000000000000"
    self._InitializeClient(client_id)

    client_old = objects.ClientSnapshot(client_id=client_id)
    client_old.kernel = "1.0.0"
    client_old.startup_info.client_info.client_name = "foo"
    self.db.WriteClientSnapshot(client_old)

    old_timestamp = self.db.ReadClientSnapshot(client_id).timestamp

    startup_info = rdf_client.StartupInfo()
    startup_info.client_info.client_name = "bar"
    self.db.WriteClientStartupInfo(client_id, startup_info)

    startup_timestamp = self.db.ReadClientStartupInfo(client_id).timestamp

    client_new = objects.ClientSnapshot(client_id=client_id)
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
    client_id = "C.0000000000000000"
    self._InitializeClient(client_id)

    client = objects.ClientMetadata()
    client.os_version = "16.04"
    client.timestamp = rdfvalue.RDFDatetime.FromHumanReadable("2010-04-10")

    with self.assertRaisesRegexp(TypeError, "client instance"):
      self.db.WriteClientSnapshotHistory([client])

  def testWriteClientSnapshotHistoryRaiseValueErrorOnEmpty(self):
    with self.assertRaisesRegexp(ValueError, "empty"):
      self.db.WriteClientSnapshotHistory([])

  def testWriteClientSnapshotHistoryRaiseValueErrorOnNonUniformIds(self):
    client_id_a = "C.000000000000000a"
    client_id_b = "C.000000000000000b"
    self._InitializeClient(client_id_a)
    self._InitializeClient(client_id_b)

    client_a = objects.ClientSnapshot(client_id=client_id_a)
    client_a.timestamp = rdfvalue.RDFDatetime.FromHumanReadable("2010-05-12")

    client_b = objects.ClientSnapshot(client_id=client_id_b)
    client_b.timestamp = rdfvalue.RDFDatetime.FromHumanReadable("2010-06-12")

    with self.assertRaisesRegexp(ValueError, "client id"):
      self.db.WriteClientSnapshotHistory([client_a, client_b])

  def testWriteClientSnapshotHistoryRaiseAttributeError(self):
    client_id = "C.0000000000000000"
    self._InitializeClient(client_id)

    client = objects.ClientSnapshot(client_id=client_id)
    client.kernel = "1.2.3"
    client.startup_info.client_info.client_version = 42

    with self.assertRaisesRegexp(AttributeError, "timestamp"):
      self.db.WriteClientSnapshotHistory([client])

  def testWriteClientSnapshotHistoryRaiseOnNonExistingClient(self):
    client_id = "C.0000000000000000"

    client = objects.ClientSnapshot(client_id=client_id)
    client.kernel = "1.2.3"
    client.timestamp = rdfvalue.RDFDatetime.FromHumanReadable("2001-01-01")

    with self.assertRaises(db.UnknownClientError):
      self.db.WriteClientSnapshotHistory([client])

  def testClientStartupInfo(self):
    """StartupInfo is written to a separate table, make sure the merge works."""
    d = self.db

    client_id = "C.fc413187fefa1dcf"
    self._InitializeClient(client_id)

    client = objects.ClientSnapshot(client_id=client_id, kernel="12.3")
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
    self.assertEqual(len(hist), 3)
    startup_infos = [cl.startup_info for cl in hist]
    self.assertEqual([si.boot_time for si in startup_infos], [125, 124, 123])

    # StartupInfos written using WriteClient show up in the StartupInfoHistory.
    history = d.ReadClientStartupInfoHistory(client_id)
    self.assertEqual(len(history), 3)
    self.assertEqual(startup_infos, history)

  def testClientSummary(self):
    d = self.db

    client_id_1 = "C.0000000000000001"
    client_id_2 = "C.0000000000000002"
    client_id_3 = "C.0000000000000003"
    self._InitializeClient(client_id_1)
    self._InitializeClient(client_id_2)
    self._InitializeClient(client_id_3)

    d.WriteClientSnapshot(
        objects.ClientSnapshot(
            client_id=client_id_1,
            knowledge_base=rdf_client.KnowledgeBase(
                fqdn="test1234.examples.com"),
            kernel="12.3"))
    d.WriteClientSnapshot(
        objects.ClientSnapshot(
            client_id=client_id_1,
            knowledge_base=rdf_client.KnowledgeBase(
                fqdn="test1234.examples.com"),
            kernel="12.4"))

    d.WriteClientSnapshot(
        objects.ClientSnapshot(
            client_id=client_id_2,
            knowledge_base=rdf_client.KnowledgeBase(
                fqdn="test1235.examples.com"),
            kernel="12.4"))

    hist = d.ReadClientSnapshotHistory(client_id_1)
    self.assertEqual(len(hist), 2)

    # client_3 should be excluded - no snapshot yet
    res = d.ReadClientsSnapshot([client_id_1, client_id_2, client_id_3])
    self.assertEqual(len(res), 3)
    self.assertIsInstance(res[client_id_1], objects.ClientSnapshot)
    self.assertIsInstance(res[client_id_2], objects.ClientSnapshot)
    self.assertIsInstance(res[client_id_1].timestamp, rdfvalue.RDFDatetime)
    self.assertIsNotNone(res[client_id_2].timestamp)
    self.assertEqual(res[client_id_1].knowledge_base.fqdn,
                     "test1234.examples.com")
    self.assertEqual(res[client_id_1].kernel, "12.4")
    self.assertEqual(res[client_id_2].knowledge_base.fqdn,
                     "test1235.examples.com")
    self.assertFalse(res[client_id_3])

  def testClientValidates(self):
    d = self.db

    # Write some metadata so the client write would otherwise succeed.
    client_id = "C.fc413187fefa1dcf"
    d.WriteClientMetadata(client_id, fleetspeak_enabled=True)
    with self.assertRaises(ValueError):
      d.WriteClientSnapshot("test1235.examples.com")

  def testClientKeywords(self):
    d = self.db
    client_id_1 = "C.0000000000000001"
    client_id_2 = "C.0000000000000002"
    client_id_3 = "C.0000000000000003"
    for cid in [client_id_1, client_id_2, client_id_3]:
      d.WriteClientMetadata(cid, fleetspeak_enabled=True)

    # Typical keywords are usernames and prefixes of hostnames.
    d.AddClientKeywords(client_id_1, [
        "joe", "machine.test.example1.com", "machine.test.example1",
        "machine.test", "machine", u"⊙_ʘ"
    ])
    d.AddClientKeywords(client_id_2, [
        "fred", "machine.test.example2.com", "machine.test.example2",
        "machine.test", "machine", u"ಠ_ಠ"
    ])
    res = d.ListClientsForKeywords(["fred", "machine", "missing"])
    self.assertEqual(res["fred"], [client_id_2])
    self.assertEqual(sorted(res["machine"]), [client_id_1, client_id_2])
    self.assertEqual(res["missing"], [])

    for kw, client_id in [(u"⊙_ʘ", client_id_1), (u"ಠ_ಠ", client_id_2),
                          (utils.SmartStr(u"⊙_ʘ"), client_id_1)]:
      res = d.ListClientsForKeywords([kw])
      self.assertEqual(res[kw], [client_id],
                       "Expected [%s] when reading keyword %s, got %s" %
                       (client_id, kw, res[kw]))

  def testClientKeywordsTimeRanges(self):
    d = self.db
    client_id = "C.0000000000000001"
    self._InitializeClient(client_id)

    d.AddClientKeywords(client_id, ["hostname1"])
    change_time = rdfvalue.RDFDatetime.Now()
    d.AddClientKeywords(client_id, ["hostname2"])

    res = d.ListClientsForKeywords(
        ["hostname1", "hostname2"], start_time=change_time)
    self.assertEqual(res["hostname1"], [])
    self.assertEqual(res["hostname2"], [client_id])

  def testRemoveClientKeyword(self):
    d = self.db
    client_id = "C.0000000000000001"
    temporary_kw = "investigation42"
    self._InitializeClient(client_id)
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
    client_id = "C.0000000000000001"
    self._InitializeClient(client_id)

    self.assertEqual(d.ReadClientLabels(client_id), [])

    d.AddClientLabels(client_id, "owner1", ["label1"])
    d.AddClientLabels(client_id, "owner2", ["label2", "label3"])

    all_labels = [
        objects.ClientLabel(name="label1", owner="owner1"),
        objects.ClientLabel(name="label2", owner="owner2"),
        objects.ClientLabel(name="label3", owner="owner2")
    ]

    self.assertEqual(d.ReadClientLabels(client_id), all_labels)
    self.assertEqual(d.ReadClientLabels("C.0000000000000002"), [])

    # Can't hurt to insert this one again.
    d.AddClientLabels(client_id, "owner1", ["label1"])
    self.assertEqual(d.ReadClientLabels(client_id), all_labels)

    d.RemoveClientLabels(client_id, "owner1", ["does not exist"])
    self.assertEqual(d.ReadClientLabels(client_id), all_labels)

    # Label3 is actually owned by owner2.
    d.RemoveClientLabels(client_id, "owner1", ["label3"])
    self.assertEqual(d.ReadClientLabels(client_id), all_labels)

    d.RemoveClientLabels(client_id, "owner2", ["label3"])
    self.assertEqual(
        d.ReadClientLabels(client_id), [
            objects.ClientLabel(name="label1", owner="owner1"),
            objects.ClientLabel(name="label2", owner="owner2"),
        ])

  def testClientLabelsUnicode(self):
    d = self.db
    client_id = "C.0000000000000001"
    self._InitializeClient(client_id)

    self.assertEqual(d.ReadClientLabels(client_id), [])

    d.AddClientLabels(client_id, "owner1", [u"⛄࿄1"])
    d.AddClientLabels(client_id, "owner2", [u"⛄࿄2"])
    d.AddClientLabels(client_id, "owner2", [utils.SmartStr(u"⛄࿄3")])

    all_labels = [
        objects.ClientLabel(name=u"⛄࿄1", owner="owner1"),
        objects.ClientLabel(name=u"⛄࿄2", owner="owner2"),
        objects.ClientLabel(name=u"⛄࿄3", owner="owner2")
    ]

    self.assertEqual(d.ReadClientLabels(client_id), all_labels)

    d.RemoveClientLabels(client_id, "owner1", ["does not exist"])
    self.assertEqual(d.ReadClientLabels(client_id), all_labels)

    # This label is actually owned by owner2.
    d.RemoveClientLabels(client_id, "owner1", [u"⛄࿄3"])
    self.assertEqual(d.ReadClientLabels(client_id), all_labels)

    d.RemoveClientLabels(client_id, "owner2", [u"⛄࿄3"])
    self.assertEqual(
        d.ReadClientLabels(client_id), [
            objects.ClientLabel(name=u"⛄࿄1", owner="owner1"),
            objects.ClientLabel(name=u"⛄࿄2", owner="owner2")
        ])

  def testFilledGRRUserReadWrite(self):
    d = self.db

    u_expected = objects.GRRUser(
        username="foo",
        ui_mode="ADVANCED",
        canary_mode=True,
        user_type=objects.GRRUser.UserType.USER_TYPE_ADMIN)
    u_expected.password.SetPassword("blah")
    d.WriteGRRUser(
        "foo",
        password=u_expected.password,
        ui_mode=u_expected.ui_mode,
        canary_mode=u_expected.canary_mode,
        user_type=u_expected.user_type)

    u = d.ReadGRRUser("foo")
    self.assertEqual(u_expected, u)

  def testEmptyGRRUserReadWrite(self):
    d = self.db

    d.WriteGRRUser("foo")
    u = d.ReadGRRUser("foo")
    u_expected = objects.GRRUser(username="foo")

    self.assertEqual(u_expected, u)

  def testReadingUnknownGRRUserFails(self):
    d = self.db

    with self.assertRaises(db.UnknownGRRUserError):
      d.ReadGRRUser("foo")

  def testReadingMultipleGRRUsersEntriesWorks(self):
    d = self.db

    u_foo = objects.GRRUser(
        username="foo",
        ui_mode="ADVANCED",
        canary_mode=True,
        user_type=objects.GRRUser.UserType.USER_TYPE_ADMIN)
    d.WriteGRRUser(
        u_foo.username,
        ui_mode=u_foo.ui_mode,
        canary_mode=u_foo.canary_mode,
        user_type=u_foo.user_type)
    u_bar = objects.GRRUser(username="bar")
    d.WriteGRRUser(u_bar.username)

    users = sorted(d.ReadAllGRRUsers(), key=lambda x: x.username)
    self.assertEqual(users[0], u_bar)
    self.assertEqual(users[1], u_foo)

  def testStartupHistory(self):
    d = self.db

    client_id = "C.0000000050000001"
    si = rdf_client.StartupInfo(boot_time=1)

    with self.assertRaises(db.UnknownClientError):
      d.WriteClientStartupInfo(client_id, si)

    self._InitializeClient(client_id)

    d.WriteClientStartupInfo(client_id, si)
    si.boot_time = 2
    d.WriteClientStartupInfo(client_id, si)
    si.boot_time = 3
    d.WriteClientStartupInfo(client_id, si)

    last_is = d.ReadClientStartupInfo(client_id)
    self.assertIsInstance(last_is, rdf_client.StartupInfo)
    self.assertEqual(last_is.boot_time, 3)
    self.assertIsInstance(last_is.timestamp, rdfvalue.RDFDatetime)

    hist = d.ReadClientStartupInfoHistory(client_id)
    self.assertEqual(len(hist), 3)
    self.assertEqual([si.boot_time for si in hist], [3, 2, 1])
    self.assertIsInstance(hist[0].timestamp, rdfvalue.RDFDatetime)
    self.assertGreater(hist[0].timestamp, hist[1].timestamp)
    self.assertGreater(hist[1].timestamp, hist[2].timestamp)

    md = self.db.ReadClientMetadata(client_id)
    self.assertEqual(md.startup_info_timestamp, hist[0].timestamp)

    self.assertIsNone(d.ReadClientStartupInfo("C.0000000000000000"))
    self.assertEqual(d.ReadClientStartupInfoHistory("C.0000000000000000"), [])

  def testCrashHistory(self):
    d = self.db

    client_id = "C.0000000050000001"
    ci = rdf_client.ClientCrash(timestamp=12345, crash_message="Crash #1")

    with self.assertRaises(db.UnknownClientError):
      d.WriteClientCrashInfo(client_id, ci)

    self._InitializeClient(client_id)

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
    self.assertEqual(len(hist), 3)
    self.assertEqual([ci.crash_message for ci in hist],
                     ["Crash #3", "Crash #2", "Crash #1"])
    self.assertIsInstance(hist[0].timestamp, rdfvalue.RDFDatetime)
    self.assertGreater(hist[0].timestamp, hist[1].timestamp)
    self.assertGreater(hist[1].timestamp, hist[2].timestamp)

    md = self.db.ReadClientMetadata(client_id)
    self.assertEqual(md.last_crash_timestamp, hist[0].timestamp)

    self.assertIsNone(d.ReadClientCrashInfo("C.0000000000000000"))
    self.assertEqual(d.ReadClientCrashInfoHistory("C.0000000000000000"), [])

  def testReadClientFullFullInfoReturnsCorrectResult(self):
    d = self.db

    client_id = "C.0000000050000001"
    self._InitializeClient(client_id)

    cl = objects.ClientSnapshot(
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
        [objects.ClientLabel(owner="test_owner", name="test_label")])

  def testReadAllClientsFullInfoReadsMultipleClientsWithMultipleLabels(self):
    d = self.db

    for i in range(10):
      client_id = "C.000000005000000%d" % i
      self._InitializeClient(client_id)

      cl = objects.ClientSnapshot(
          client_id=client_id,
          knowledge_base=rdf_client.KnowledgeBase(
              fqdn="test%d.examples.com" % i),
          kernel="12.3.%d" % i)
      d.WriteClientSnapshot(cl)
      d.WriteClientMetadata(client_id, certificate=CERT)
      si = rdf_client.StartupInfo(boot_time=i)
      d.WriteClientStartupInfo(client_id, si)
      d.AddClientLabels(
          client_id, "test_owner",
          ["test_label-a-%d" % i, "test_label-b-%d" % i])

    c_infos = sorted(
        d.ReadAllClientsFullInfo(), key=lambda c: c.last_snapshot.client_id)
    for i, full_info in enumerate(c_infos):
      self.assertEqual(full_info.last_snapshot.client_id,
                       "C.000000005000000%d" % i)
      self.assertEqual(full_info.metadata.certificate, CERT)
      self.assertEqual(full_info.last_startup_info.boot_time, i)
      self.assertEqual(
          sorted(full_info.labels, key=lambda l: l.name), [
              objects.ClientLabel(
                  owner="test_owner", name="test_label-a-%d" % i),
              objects.ClientLabel(
                  owner="test_owner", name="test_label-b-%d" % i)
          ])

  def testReadAllClientsFullInfoFiltersClientsByLastPingTime(self):
    d = self.db

    now = rdfvalue.RDFDatetime.Now()
    time_past = now - rdfvalue.Duration("1d")

    expected_client_ids = set()
    for i in range(10):
      client_id = "C.000000005000000%d" % i
      self._InitializeClient(client_id)

      d.WriteClientSnapshot(objects.ClientSnapshot(client_id=client_id))
      d.WriteClientMetadata(
          client_id, last_ping=(time_past if i % 2 == 0 else now))

      if i % 2 != 0:
        expected_client_ids.add(client_id)

    c_ids = set(
        c.last_snapshot.client_id for c in d.ReadAllClientsFullInfo(
            min_last_ping=now - rdfvalue.Duration("1s")))
    self.assertEqual(expected_client_ids, c_ids)

  def testReadWriteApprovalRequestWithEmptyNotifiedUsersEmailsAndGrants(self):
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    client_id = "C.0000000050000001"
    approval_request = objects.ApprovalRequest(
        approval_type=objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
        subject_id=client_id,
        requestor_username="requestor",
        reason="some test reason",
        expiration_time=rdfvalue.RDFDatetime(42))

    approval_id = d.WriteApprovalRequest(approval_request)
    self.assertTrue(approval_id)

    read_request = d.ReadApprovalRequest("requestor", approval_id)

    # Approval id and timestamp are generated in WriteApprovalRequest so we're
    # filling them into our model object ot make sure that equality check works.
    approval_request.approval_id = read_request.approval_id
    approval_request.timestamp = read_request.timestamp
    self.assertEqual(approval_request, read_request)

  def testReadWriteApprovalRequestsWithFilledInUsersEmailsAndGrants(self):
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    client_id = "C.0000000050000001"
    approval_request = objects.ApprovalRequest(
        approval_type=objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
        subject_id=client_id,
        requestor_username="requestor",
        reason="some test reason",
        expiration_time=rdfvalue.RDFDatetime(42),
        notified_users=["user1", "user2", "user3"],
        email_cc_addresses=["a@b.com", "c@d.com"],
        grants=[
            objects.ApprovalGrant(grantor_username="user_foo"),
            objects.ApprovalGrant(grantor_username="user_bar")
        ])

    approval_id = d.WriteApprovalRequest(approval_request)

    read_request = d.ReadApprovalRequest("requestor", approval_id)

    self.assertEqual(
        sorted(approval_request.notified_users),
        sorted(read_request.notified_users))
    self.assertEqual(
        sorted(approval_request.email_cc_addresses),
        sorted(read_request.email_cc_addresses))
    self.assertEqual(
        sorted(g.grantor_username for g in approval_request.grants),
        sorted(g.grantor_username for g in read_request.grants))

  def testGrantApprovalAddsNewGrantor(self):
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    client_id = "C.0000000050000001"
    approval_request = objects.ApprovalRequest(
        approval_type=objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
        subject_id=client_id,
        requestor_username="requestor",
        reason="some test reason",
        expiration_time=rdfvalue.RDFDatetime(42))
    approval_id = d.WriteApprovalRequest(approval_request)

    read_request = d.ReadApprovalRequest("requestor", approval_id)
    self.assertFalse(read_request.grants)

    d.GrantApproval("requestor", approval_id, "grantor")
    read_request = d.ReadApprovalRequest("requestor", approval_id)
    self.assertEqual(len(read_request.grants), 1)
    self.assertEqual(read_request.grants[0].grantor_username, "grantor")

  def testGrantApprovalAddsMultipleGrantorsWithSameName(self):
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    client_id = "C.0000000050000001"
    approval_request = objects.ApprovalRequest(
        approval_type=objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
        subject_id=client_id,
        requestor_username="requestor",
        reason="some test reason",
        expiration_time=rdfvalue.RDFDatetime(42))
    approval_id = d.WriteApprovalRequest(approval_request)

    for _ in range(3):
      d.GrantApproval("requestor", approval_id, "grantor")

    read_request = d.ReadApprovalRequest("requestor", approval_id)
    self.assertEqual(len(read_request.grants), 3)
    self.assertEqual([g.grantor_username for g in read_request.grants],
                     ["grantor"] * 3)

  def testReadApprovalRequeststReturnsNothingWhenNoApprovals(self):
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    approvals = list(
        d.ReadApprovalRequests(
            "requestor",
            objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT))
    self.assertFalse(approvals)

  def testReadApprovalRequestsReturnsSingleApproval(self):
    client_id = "C.0000000050000001"
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    approval_request = objects.ApprovalRequest(
        approval_type=objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
        subject_id=client_id,
        requestor_username="requestor",
        reason="some test reason",
        expiration_time=rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d"))
    approval_id = d.WriteApprovalRequest(approval_request)

    approvals = list(
        d.ReadApprovalRequests(
            "requestor",
            objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT))

    self.assertEqual(len(approvals), 1)
    self.assertEqual(approvals[0].approval_id, approval_id)

    # Approval id and timestamp are generated in WriteApprovalRequest so we're
    # filling them into our model object ot make sure that equality check works.
    approval_request.approval_id = approvals[0].approval_id
    approval_request.timestamp = approvals[0].timestamp
    self.assertEqual(approval_request, approvals[0])

  def testReadApprovalRequestsReturnsMultipleApprovals(self):
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    expiration_time = rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d")

    approval_ids = set()
    for i in range(10):
      approval_request = objects.ApprovalRequest(
          approval_type=objects.ApprovalRequest.ApprovalType.
          APPROVAL_TYPE_CLIENT,
          subject_id="C.000000005000000%d" % i,
          requestor_username="requestor",
          reason="some test reason",
          expiration_time=expiration_time)
      approval_ids.add(d.WriteApprovalRequest(approval_request))

    approvals = list(
        d.ReadApprovalRequests(
            "requestor",
            objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT))

    self.assertEqual(len(approvals), 10)
    self.assertEqual(set(a.approval_id for a in approvals), approval_ids)

  def testReadApprovalRequestsIncludesGrantsIntoSingleApproval(self):
    client_id = "C.0000000050000001"
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    approval_request = objects.ApprovalRequest(
        approval_type=objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
        subject_id=client_id,
        requestor_username="requestor",
        reason="some test reason",
        grants=[
            objects.ApprovalGrant(grantor_username="grantor1"),
            objects.ApprovalGrant(grantor_username="grantor2")
        ],
        expiration_time=rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d"))
    approval_id = d.WriteApprovalRequest(approval_request)

    approvals = list(
        d.ReadApprovalRequests(
            "requestor",
            objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT))

    self.assertEqual(len(approvals), 1)
    self.assertEqual(approvals[0].approval_id, approval_id)

    self.assertEqual(
        sorted(g.grantor_username for g in approvals[0].grants),
        ["grantor1", "grantor2"])

  def testReadApprovalRequestsIncludesGrantsIntoMultipleResults(self):
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    for i in range(10):
      approval_request = objects.ApprovalRequest(
          approval_type=objects.ApprovalRequest.ApprovalType.
          APPROVAL_TYPE_CLIENT,
          subject_id="C.00000000000000%d" % i,
          requestor_username="requestor",
          reason="some test reason %d" % i,
          grants=[
              objects.ApprovalGrant(grantor_username="grantor_%d_1" % i),
              objects.ApprovalGrant(grantor_username="grantor_%d_2" % i)
          ],
          expiration_time=rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d"))
      d.WriteApprovalRequest(approval_request)

    approvals = sorted(
        d.ReadApprovalRequests(
            "requestor",
            objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT),
        key=lambda a: a.reason)

    self.assertEqual(len(approvals), 10)

    for i, approval in enumerate(approvals):
      self.assertEqual(
          sorted(g.grantor_username for g in approval.grants),
          ["grantor_%d_1" % i, "grantor_%d_2" % i])

  def testReadApprovalRequestsFiltersOutExpiredApprovals(self):
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    time_future = rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d")
    time_past = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("1d")

    non_expired_approval_ids = set()
    for i in range(10):
      approval_request = objects.ApprovalRequest(
          approval_type=objects.ApprovalRequest.ApprovalType.
          APPROVAL_TYPE_CLIENT,
          subject_id="C.000000005000000%d" % i,
          requestor_username="requestor",
          reason="some test reason",
          expiration_time=(time_future if i % 2 == 0 else time_past))

      approval_id = d.WriteApprovalRequest(approval_request)
      if i % 2 == 0:
        non_expired_approval_ids.add(approval_id)

    approvals = list(
        d.ReadApprovalRequests(
            "requestor",
            objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT))

    self.assertEqual(len(approvals), 5)
    self.assertEqual(
        set(a.approval_id for a in approvals), non_expired_approval_ids)

  def testReadApprovalRequestsKeepsExpiredApprovalsWhenAsked(self):
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    time_future = rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d")
    time_past = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("1d")

    approval_ids = set()
    for i in range(10):
      approval_request = objects.ApprovalRequest(
          approval_type=objects.ApprovalRequest.ApprovalType.
          APPROVAL_TYPE_CLIENT,
          subject_id="C.000000005000000%d" % i,
          requestor_username="requestor",
          reason="some test reason",
          expiration_time=(time_future if i % 2 == 0 else time_past))

      approval_ids.add(d.WriteApprovalRequest(approval_request))

    approvals = list(
        d.ReadApprovalRequests(
            "requestor",
            objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
            include_expired=True))

    self.assertEqual(len(approvals), 10)
    self.assertEqual(set(a.approval_id for a in approvals), approval_ids)

  def testReadApprovalRequestsForSubjectReturnsNothingWhenNoApprovals(self):
    client_id = "C.0000000050000001"
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    approvals = list(
        d.ReadApprovalRequests(
            "requestor",
            objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
            subject_id=client_id))
    self.assertFalse(approvals)

  def testReadApprovalRequestsForSubjectReturnsSingleNonExpiredApproval(self):
    client_id = "C.0000000050000001"
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    approval_request = objects.ApprovalRequest(
        approval_type=objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
        subject_id=client_id,
        requestor_username="requestor",
        reason="some test reason",
        expiration_time=rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d"))
    approval_id = d.WriteApprovalRequest(approval_request)

    approvals = list(
        d.ReadApprovalRequests(
            "requestor",
            objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
            subject_id=client_id))

    self.assertEqual(len(approvals), 1)
    self.assertEqual(approvals[0].approval_id, approval_id)

    # Approval id and timestamp are generated in WriteApprovalRequest so we're
    # filling them into our model object ot make sure that equality check works.
    approval_request.approval_id = approvals[0].approval_id
    approval_request.timestamp = approvals[0].timestamp
    self.assertEqual(approval_request, approvals[0])

  def testReadApprovalRequestsForSubjectReturnsManyNonExpiredApproval(self):
    client_id = "C.0000000050000001"
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    expiration_time = rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d")

    approval_ids = set()
    for _ in range(10):
      approval_request = objects.ApprovalRequest(
          approval_type=objects.ApprovalRequest.ApprovalType.
          APPROVAL_TYPE_CLIENT,
          subject_id=client_id,
          requestor_username="requestor",
          reason="some test reason",
          expiration_time=expiration_time)
      approval_ids.add(d.WriteApprovalRequest(approval_request))

    approvals = list(
        d.ReadApprovalRequests(
            "requestor",
            objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
            subject_id=client_id))

    self.assertEqual(len(approvals), 10)
    self.assertEqual(set(a.approval_id for a in approvals), approval_ids)

  def testReadApprovalRequestsForSubjectIncludesGrantsIntoSingleResult(self):
    client_id = "C.0000000050000001"
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    approval_request = objects.ApprovalRequest(
        approval_type=objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
        subject_id=client_id,
        requestor_username="requestor",
        reason="some test reason",
        grants=[
            objects.ApprovalGrant(grantor_username="grantor1"),
            objects.ApprovalGrant(grantor_username="grantor2")
        ],
        expiration_time=rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d"))
    approval_id = d.WriteApprovalRequest(approval_request)

    approvals = list(
        d.ReadApprovalRequests(
            "requestor",
            objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
            subject_id=client_id))

    self.assertEqual(len(approvals), 1)
    self.assertEqual(approvals[0].approval_id, approval_id)

    self.assertEqual(
        sorted(g.grantor_username for g in approvals[0].grants),
        ["grantor1", "grantor2"])

  def testReadApprovalRequestsForSubjectIncludesGrantsIntoMultipleResults(self):
    client_id = "C.000000000000001"
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    for i in range(10):
      approval_request = objects.ApprovalRequest(
          approval_type=objects.ApprovalRequest.ApprovalType.
          APPROVAL_TYPE_CLIENT,
          subject_id=client_id,
          requestor_username="requestor",
          reason="some test reason %d" % i,
          grants=[
              objects.ApprovalGrant(grantor_username="grantor_%d_1" % i),
              objects.ApprovalGrant(grantor_username="grantor_%d_2" % i)
          ],
          expiration_time=rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d"))
      d.WriteApprovalRequest(approval_request)

    approvals = sorted(
        d.ReadApprovalRequests(
            "requestor",
            objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
            subject_id=client_id),
        key=lambda a: a.reason)

    self.assertEqual(len(approvals), 10)

    for i, approval in enumerate(approvals):
      self.assertEqual(
          sorted(g.grantor_username for g in approval.grants),
          ["grantor_%d_1" % i, "grantor_%d_2" % i])

  def testReadApprovalRequestsForSubjectFiltersOutExpiredApprovals(self):
    client_id = "C.0000000050000001"
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    time_future = rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d")
    time_past = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("1d")

    non_expired_approval_ids = set()
    for i in range(10):
      approval_request = objects.ApprovalRequest(
          approval_type=objects.ApprovalRequest.ApprovalType.
          APPROVAL_TYPE_CLIENT,
          subject_id=client_id,
          requestor_username="requestor",
          reason="some test reason",
          expiration_time=(time_future if i % 2 == 0 else time_past))

      approval_id = d.WriteApprovalRequest(approval_request)
      if i % 2 == 0:
        non_expired_approval_ids.add(approval_id)

    approvals = list(
        d.ReadApprovalRequests(
            "requestor",
            objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
            subject_id=client_id))

    self.assertEqual(len(approvals), 5)
    self.assertEqual(
        set(a.approval_id for a in approvals), non_expired_approval_ids)

  def testReadApprovalRequestsForSubjectKeepsExpiredApprovalsWhenAsked(self):
    client_id = "C.0000000050000001"
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    time_future = rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d")
    time_past = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("1d")

    approval_ids = set()
    for i in range(10):
      approval_request = objects.ApprovalRequest(
          approval_type=objects.ApprovalRequest.ApprovalType.
          APPROVAL_TYPE_CLIENT,
          subject_id=client_id,
          requestor_username="requestor",
          reason="some test reason",
          expiration_time=(time_future if i % 2 == 0 else time_past))

      approval_ids.add(d.WriteApprovalRequest(approval_request))

    approvals = list(
        d.ReadApprovalRequests(
            "requestor",
            objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
            subject_id=client_id,
            include_expired=True))

    self.assertEqual(len(approvals), 10)
    self.assertEqual(set(a.approval_id for a in approvals), approval_ids)
