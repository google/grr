#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
import abc

from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import crypto
from grr.lib.rdfvalues import objects
from grr.server import db


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
      d.WriteClient(objects.Client(client_id=client_id))

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

  def testClientHistory(self):
    d = self.db

    client_id = "C.fc413187fefa1dcf"
    self._InitializeClient(client_id)

    client = objects.Client(client_id=client_id, kernel="12.3")
    client.knowledge_base.fqdn = "test1234.examples.com"
    d.WriteClient(client)
    client.kernel = "12.4"
    d.WriteClient(client)

    hist = d.ReadClientHistory(client_id)
    self.assertEqual(len(hist), 2)
    self.assertIsInstance(hist[0], objects.Client)
    self.assertIsInstance(hist[1], objects.Client)
    self.assertGreater(hist[0].timestamp, hist[1].timestamp)
    self.assertIsInstance(hist[0].timestamp, rdfvalue.RDFDatetime)
    self.assertEqual(hist[0].kernel, "12.4")
    self.assertEqual(hist[1].kernel, "12.3")

  def testWriteClientHistory(self):
    client_id = "C.0000000000000000"
    self._InitializeClient(client_id)

    client_a = objects.Client(client_id=client_id)
    client_a.kernel = "1.2.3"
    client_a.startup_info.client_info.client_version = 42
    client_a.timestamp = rdfvalue.RDFDatetime.FromHumanReadable("2010-01-01")

    client_b = objects.Client(client_id=client_id)
    client_b.kernel = "4.5.6"
    client_b.startup_info.client_info.client_version = 108
    client_b.timestamp = rdfvalue.RDFDatetime.FromHumanReadable("2010-02-01")

    client_c = objects.Client(client_id=client_id)
    client_c.kernel = "7.8.9"
    client_c.startup_info.client_info.client_version = 707
    client_c.timestamp = rdfvalue.RDFDatetime.FromHumanReadable("2010-03-01")

    self.db.WriteClientHistory([client_a, client_b, client_c])

    # Check whether the client history has been recorded correctly.
    history = self.db.ReadClientHistory(client_id)
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

  def testWriteClientHistoryUpdatesLastTimestampIfNotSet(self):
    client_id = "C.0000000000000000"
    self._InitializeClient(client_id)

    client_new = objects.Client(client_id=client_id)
    client_new.kernel = "1.0.0"
    client_new.timestamp = rdfvalue.RDFDatetime.FromHumanReadable("2010-01-01")
    self.db.WriteClientHistory([client_new])

    info = self.db.ReadClientFullInfo(client_id)
    self.assertEqual(info["client"].kernel, "1.0.0")
    self.assertEqual(info["client"].timestamp,
                     rdfvalue.RDFDatetime.FromHumanReadable("2010-01-01"))
    self.assertEqual(info["last_startup_info"].timestamp,
                     rdfvalue.RDFDatetime.FromHumanReadable("2010-01-01"))

  def testWriteClientHistoryUpdatesLastTimestampIfNewer(self):
    client_id = "C.0000000000000000"
    self._InitializeClient(client_id)

    client_old = objects.Client(client_id=client_id)
    client_old.kernel = "1.0.0"
    self.db.WriteClient(client_old)

    old_timestamp = self.db.ReadClient(client_id).timestamp

    client_new = objects.Client(client_id=client_id)
    client_new.kernel = "2.0.0"
    client_new.timestamp = rdfvalue.RDFDatetime.Now()
    self.db.WriteClientHistory([client_new])

    info = self.db.ReadClientFullInfo(client_id)
    self.assertEqual(info["client"].kernel, "2.0.0")
    self.assertGreater(info["client"].timestamp, old_timestamp)
    self.assertGreater(info["last_startup_info"].timestamp, old_timestamp)

  def testWriteClientHistoryDoesNotUpdateLastTimestampIfOlder(self):
    client_id = "C.0000000000000000"
    self._InitializeClient(client_id)

    client_new = objects.Client(client_id=client_id)
    client_new.kernel = "2.0.0"
    self.db.WriteClient(client_new)

    new_timestamp = self.db.ReadClient(client_id).timestamp

    client_old = objects.Client(client_id=client_id)
    client_old.kernel = "1.0.0"
    client_old.timestamp = new_timestamp - rdfvalue.Duration("1d")
    self.db.WriteClientHistory([client_old])

    info = self.db.ReadClientFullInfo(client_id)
    self.assertEqual(info["client"].kernel, "2.0.0")
    self.assertEqual(info["client"].timestamp, new_timestamp)
    self.assertEqual(info["last_startup_info"].timestamp, new_timestamp)

  def testWriteClientHistoryUpdatesOnlyLastClientTimestamp(self):
    client_id = "C.0000000000000000"
    self._InitializeClient(client_id)

    client_old = objects.Client(client_id=client_id)
    client_old.kernel = "1.0.0"
    client_old.startup_info.client_info.client_name = "foo"
    self.db.WriteClient(client_old)

    old_timestamp = self.db.ReadClient(client_id).timestamp

    startup_info = rdf_client.StartupInfo()
    startup_info.client_info.client_name = "bar"
    self.db.WriteClientStartupInfo(client_id, startup_info)

    startup_timestamp = self.db.ReadClientStartupInfo(client_id).timestamp

    client_new = objects.Client(client_id=client_id)
    client_new.kernel = "2.0.0"
    client_new.startup_info.client_info.client_name = "baz"
    client_new.timestamp = rdfvalue.RDFDatetime.Lerp(
        0.5, start_time=old_timestamp, end_time=startup_timestamp)
    self.db.WriteClientHistory([client_new])

    info = self.db.ReadClientFullInfo(client_id)
    self.assertEqual(info["client"].kernel, "2.0.0")
    self.assertEqual(info["client"].startup_info.client_info.client_name, "baz")
    self.assertEqual(info["client"].timestamp, client_new.timestamp)
    self.assertEqual(info["last_startup_info"].client_info.client_name, "bar")
    self.assertEqual(info["last_startup_info"].timestamp, startup_timestamp)

  def testWriteClientHistoryRaiseTypeError(self):
    client_id = "C.0000000000000000"
    self._InitializeClient(client_id)

    client = objects.ClientMetadata()
    client.os_version = "16.04"
    client.timestamp = rdfvalue.RDFDatetime.FromHumanReadable("2010-04-10")

    with self.assertRaisesRegexp(TypeError, "client instance"):
      self.db.WriteClientHistory([client])

  def testWriteClientHistoryRaiseValueErrorOnEmpty(self):
    with self.assertRaisesRegexp(ValueError, "empty"):
      self.db.WriteClientHistory([])

  def testWriteClientHistoryRaiseValueErrorOnNonUniformIds(self):
    client_id_a = "C.000000000000000a"
    client_id_b = "C.000000000000000b"
    self._InitializeClient(client_id_a)
    self._InitializeClient(client_id_b)

    client_a = objects.Client(client_id=client_id_a)
    client_a.timestamp = rdfvalue.RDFDatetime.FromHumanReadable("2010-05-12")

    client_b = objects.Client(client_id=client_id_b)
    client_b.timestamp = rdfvalue.RDFDatetime.FromHumanReadable("2010-06-12")

    with self.assertRaisesRegexp(ValueError, "client id"):
      self.db.WriteClientHistory([client_a, client_b])

  def testWriteClientHistoryRaiseAttributeError(self):
    client_id = "C.0000000000000000"
    self._InitializeClient(client_id)

    client = objects.Client(client_id=client_id)
    client.kernel = "1.2.3"
    client.startup_info.client_info.client_version = 42

    with self.assertRaisesRegexp(AttributeError, "timestamp"):
      self.db.WriteClientHistory([client])

  def testWriteClientHistoryRaiseOnNonExistingClient(self):
    client_id = "C.0000000000000000"

    client = objects.Client(client_id=client_id)
    client.kernel = "1.2.3"
    client.timestamp = rdfvalue.RDFDatetime.FromHumanReadable("2001-01-01")

    with self.assertRaises(db.UnknownClientError):
      self.db.WriteClientHistory([client])

  def testClientStartupInfo(self):
    """StartupInfo is written to a separate table, make sure the merge works."""
    d = self.db

    client_id = "C.fc413187fefa1dcf"
    self._InitializeClient(client_id)

    client = objects.Client(client_id=client_id, kernel="12.3")
    client.startup_info = rdf_client.StartupInfo(boot_time=123)
    client.knowledge_base.fqdn = "test1234.examples.com"
    d.WriteClient(client)

    client = d.ReadClient(client_id)
    self.assertEqual(client.startup_info.boot_time, 123)

    client.kernel = "12.4"
    client.startup_info = rdf_client.StartupInfo(boot_time=124)
    d.WriteClient(client)

    client.kernel = "12.5"
    client.startup_info = rdf_client.StartupInfo(boot_time=125)
    d.WriteClient(client)

    hist = d.ReadClientHistory(client_id)
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

    d.WriteClient(
        objects.Client(
            client_id=client_id_1,
            knowledge_base=rdf_client.KnowledgeBase(
                fqdn="test1234.examples.com"),
            kernel="12.3"))
    d.WriteClient(
        objects.Client(
            client_id=client_id_1,
            knowledge_base=rdf_client.KnowledgeBase(
                fqdn="test1234.examples.com"),
            kernel="12.4"))

    d.WriteClient(
        objects.Client(
            client_id=client_id_2,
            knowledge_base=rdf_client.KnowledgeBase(
                fqdn="test1235.examples.com"),
            kernel="12.4"))

    hist = d.ReadClientHistory(client_id_1)
    self.assertEqual(len(hist), 2)

    # client_3 should be excluded - no snapshot yet
    res = d.ReadClients([client_id_1, client_id_2, client_id_3])
    self.assertEqual(len(res), 3)
    self.assertIsInstance(res[client_id_1], objects.Client)
    self.assertIsInstance(res[client_id_2], objects.Client)
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
      d.WriteClient("test1235.examples.com")

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

  def testFullInfo(self):
    d = self.db

    client_id = "C.0000000050000001"
    self._InitializeClient(client_id)

    cl = objects.Client(
        client_id=client_id,
        knowledge_base=rdf_client.KnowledgeBase(fqdn="test1234.examples.com"),
        kernel="12.3")
    d.WriteClient(cl)
    d.WriteClientMetadata(client_id, certificate=CERT)
    si = rdf_client.StartupInfo(boot_time=1)
    d.WriteClientStartupInfo(client_id, si)
    d.AddClientLabels(client_id, "test_owner", ["test_label"])

    full_info = d.ReadClientFullInfo(client_id)
    self.assertEqual(full_info["client"], cl)
    self.assertEqual(full_info["metadata"].certificate, CERT)
    self.assertEqual(full_info["last_startup_info"], si)
    self.assertEqual(
        full_info["labels"],
        [objects.ClientLabel(owner="test_owner", name="test_label")])


CERT = crypto.RDFX509Cert("""-----BEGIN CERTIFICATE-----
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
-----END CERTIFICATE-----""")
