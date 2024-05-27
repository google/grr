#!/usr/bin/env python
"""This modules contains tests for clients API handlers."""

import ipaddress
from unittest import mock

from absl import app
from absl.testing import absltest

from google.protobuf import timestamp_pb2
from google.protobuf import text_format
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_core.lib.rdfvalues import cloud as rdf_cloud
from grr_response_core.lib.rdfvalues import test_base as rdf_test_base
from grr_response_proto import objects_pb2
from grr_response_proto.api import client_pb2
from grr_response_server import client_index
from grr_response_server import data_store
from grr_response_server import fleetspeak_connector
from grr_response_server import fleetspeak_utils
from grr_response_server.gui import api_test_lib
from grr_response_server.gui.api_plugins import client as client_plugin
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import db_test_lib
from grr.test_lib import test_lib
from fleetspeak.src.server.proto.fleetspeak_server import admin_pb2


class ApiClientTest(absltest.TestCase):

  def _CreateFilledOutClientSnapshot(self):
    snapshot = rdf_objects.ClientSnapshot(client_id="C.0000000000000000")
    snapshot.metadata.source_flow_id = "ABCDEF"
    client_information = rdf_client.ClientInformation(
        client_name="GRR Monitor",
        client_version="1234",
        client_description="some client description",
        build_time="1980-01-01T12:00:00.000000+00:00",
        labels=["label1", "label2"],
    )
    snapshot.startup_info.client_info = client_information
    snapshot.startup_info.boot_time = rdfvalue.RDFDatetime.FromHumanReadable(
        "2024-01-01"
    )
    hardware_info = rdf_client.HardwareInfo(
        system_manufacturer="System-Manufacturer-123",
        bios_version="Bios-Version-123",
        serial_number="123abc",
        system_uuid="a-b-c-1-2-3",
    )
    snapshot.hardware_info = hardware_info
    snapshot.os_release = "Windows"
    snapshot.os_version = "14.4"
    snapshot.kernel = "4.0.0"
    snapshot.arch = "x86_64"
    users = [
        rdf_client.User(username="fred", full_name="Ok Guy Fred"),
        rdf_client.User(username="joe", full_name="Good Guy Joe"),
    ]
    knowledge_base = rdf_client.KnowledgeBase(
        os="Linux",
        os_release="RedHat Linux",
        os_major_version=4,
        os_minor_version=2,
        fqdn="test123.examples.com",
        users=users,
    )
    snapshot.knowledge_base = knowledge_base
    interfaces = [
        rdf_client_network.Interface(
            ifname="if0",
            addresses=[
                rdf_client_network.NetworkAddress(
                    human_readable_address="192.168.0.123"
                ),
                rdf_client_network.NetworkAddress(
                    human_readable_address="2001:abcd::123"
                ),
            ],
        ),
        rdf_client_network.Interface(
            ifname="if1",
            mac_address=rdf_client_network.MacAddress.FromHumanReadableAddress(
                "aabbccddee%02x" % 123
            ),
        ),
        rdf_client_network.Interface(
            ifname="if2",
            mac_address=rdf_client_network.MacAddress.FromHumanReadableAddress(
                "bbccddeeff%02x" % 123
            ),
        ),
    ]
    snapshot.interfaces = interfaces
    volumes = [
        rdf_client_fs.Volume(
            windowsvolume=rdf_client_fs.WindowsVolume(drive_letter="C:"),
            bytes_per_sector=4096,
            sectors_per_allocation_unit=1,
            actual_available_allocation_units=50,
            total_allocation_units=100,
        ),
        rdf_client_fs.Volume(
            unixvolume=rdf_client_fs.UnixVolume(mount_point="/"),
            bytes_per_sector=4096,
            sectors_per_allocation_unit=1,
            actual_available_allocation_units=10,
            total_allocation_units=100,
        ),
    ]
    snapshot.volumes = volumes
    cloud_instance = rdf_cloud.CloudInstance(
        cloud_type=rdf_cloud.CloudInstance.InstanceType.GOOGLE,
        google=rdf_cloud.GoogleCloudInstance(
            unique_id="us-central1-a/myproject/1771384456894610289"
        ),
    )
    snapshot.cloud_instance = cloud_instance
    timestamp = rdfvalue.RDFDatetime.FromHumanReadable("2024-01-01")
    snapshot.timestamp = timestamp
    snapshot.edr_agents.append(rdf_client.EdrAgent(name="foo", agent_id="1337"))
    snapshot.edr_agents.append(rdf_client.EdrAgent(name="bar", agent_id="108"))
    snapshot.memory_size = 123456

    return snapshot

  def testInitFromClientObject(self):
    snapshot = self._CreateFilledOutClientSnapshot()

    want_client = client_plugin.ApiClient(
        client_id="C.0000000000000000",
        urn="aff4:/C.0000000000000000",
        source_flow_id="ABCDEF",
        agent_info=snapshot.startup_info.client_info,
        hardware_info=snapshot.hardware_info,
        os_info=rdf_client.Uname(
            fqdn="test123.examples.com",
            kernel="4.0.0",
            machine="x86_64",
            release="Windows",
            system="Linux",
            version="14.4",
        ),
        knowledge_base=snapshot.knowledge_base,
        cloud_instance=snapshot.cloud_instance,
        volumes=snapshot.volumes,
        age=snapshot.timestamp,
        interfaces=snapshot.interfaces,
        last_booted_at=snapshot.startup_info.boot_time,
        memory_size=snapshot.memory_size,
        users=snapshot.knowledge_base.users,
    )

    result = client_plugin.ApiClient().InitFromClientObject(snapshot)

    self.assertEqual(result, want_client)

  def testInitFromClientInfo_WithSnapshot(self):
    snapshot = self._CreateFilledOutClientSnapshot()
    client_info = rdf_objects.ClientFullInfo(last_snapshot=snapshot)

    want_client = client_plugin.ApiClient(
        client_id="C.0000000000000000",
        urn="aff4:/C.0000000000000000",
        source_flow_id="ABCDEF",
        agent_info=snapshot.startup_info.client_info,
        hardware_info=snapshot.hardware_info,
        os_info=rdf_client.Uname(
            fqdn="test123.examples.com",
            kernel="4.0.0",
            machine="x86_64",
            release="Windows",
            system="Linux",
            version="14.4",
        ),
        knowledge_base=snapshot.knowledge_base,
        cloud_instance=snapshot.cloud_instance,
        volumes=snapshot.volumes,
        age=snapshot.timestamp,
        interfaces=snapshot.interfaces,
        last_booted_at=snapshot.startup_info.boot_time,
        memory_size=snapshot.memory_size,
        users=snapshot.knowledge_base.users,
    )

    result = client_plugin.ApiClient().InitFromClientInfo(
        "C.0000000000000000", client_info
    )

    self.assertEqual(result, want_client)

  def testInitFromClientInfo_WithSnapshot_BadId(self):
    snapshot = self._CreateFilledOutClientSnapshot()
    client_info = rdf_objects.ClientFullInfo(last_snapshot=snapshot)

    with self.assertRaises(ValueError):
      client_plugin.ApiClient().InitFromClientInfo(
          "C.1111111111111111", client_info
      )

  def testInitFromClientInfo_WithoutSnapshot(self):
    first_seen_time = rdfvalue.RDFDatetime.FromHumanReadable("2022-01-01")
    boot_time = rdfvalue.RDFDatetime.FromHumanReadable("2022-02-02")
    ping_time = rdfvalue.RDFDatetime.FromHumanReadable("2022-03-03")
    crash_time = rdfvalue.RDFDatetime.FromHumanReadable("2022-04-04")
    metadata = rdf_objects.ClientMetadata(
        first_seen=first_seen_time,
        ping=ping_time,
        last_crash_timestamp=crash_time,
    )
    labels = [
        rdf_objects.ClientLabel(name="label3"),
        rdf_objects.ClientLabel(name="label4"),
    ]
    client_info = rdf_objects.ClientFullInfo(metadata=metadata, labels=labels)
    client_info.last_startup_info.boot_time = boot_time
    client_information = rdf_client.ClientInformation(
        client_name="GRR Monitor",
        client_version="1234",
        client_description="some client description",
        build_time="1980-01-01T12:00:00.000000+00:00",
        labels=["label1", "label2"],
    )
    client_info.last_startup_info.client_info = client_information
    client_info.last_rrg_startup.metadata.version.major = 1
    client_info.last_rrg_startup.metadata.version.minor = 2
    client_info.last_rrg_startup.metadata.version.patch = 3
    rrg_args = "some args --were passed"
    client_info.last_rrg_startup.args = rrg_args

    want_client = client_plugin.ApiClient(
        client_id="C.0000000000000000",
        agent_info=client_information,
        age=first_seen_time,
        first_seen_at=first_seen_time,
        last_booted_at=boot_time,
        last_seen_at=ping_time,
        last_crash_at=crash_time,
        labels=labels,
        rrg_args=rrg_args,
        rrg_version="1.2.3",
    )

    result = client_plugin.ApiClient().InitFromClientInfo(
        "C.0000000000000000", client_info
    )

    self.assertEqual(result, want_client)

  def testInitFromClientInfoAgeWithSnapshot(self):
    first_seen_time = rdfvalue.RDFDatetime.FromHumanReadable("2022-01-01")
    last_snapshot_time = rdfvalue.RDFDatetime.FromHumanReadable("2022-02-02")

    info = rdf_objects.ClientFullInfo()
    info.metadata.first_seen = first_seen_time
    info.last_snapshot.client_id = "C.1122334455667788"
    info.last_snapshot.timestamp = last_snapshot_time

    client = client_plugin.ApiClient()
    client.InitFromClientInfo("C.1122334455667788", info)

    self.assertEqual(client.age, last_snapshot_time)

  def testInitFromClientInfoWithoutSnapshot(self):
    first_seen_time = rdfvalue.RDFDatetime.FromHumanReadable("2022-01-01")

    info = rdf_objects.ClientFullInfo()
    info.metadata.first_seen = first_seen_time

    client = client_plugin.ApiClient()
    client.InitFromClientInfo("C.1122334455667788", info)

    self.assertEqual(client.age, first_seen_time)

  def testInitFromClientInfoRRG(self):
    info = rdf_objects.ClientFullInfo()
    info.last_rrg_startup.args = ["--foo", "--bar", "--baz"]
    info.last_rrg_startup.metadata.version.major = 1
    info.last_rrg_startup.metadata.version.minor = 2
    info.last_rrg_startup.metadata.version.patch = 3

    api_client = client_plugin.ApiClient()
    api_client.InitFromClientInfo("C.0123456789ABCDEF", info)

    self.assertEqual(api_client.rrg_version, "1.2.3")
    self.assertEqual(api_client.rrg_args, ["--foo", "--bar", "--baz"])


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
    super().setUp()
    self.client_ids = self.SetupClients(3)
    self.handler = client_plugin.ApiAddClientsLabelsHandler()

  def testAddsSingleLabelToSingleClient(self):
    self.handler.Handle(
        client_pb2.ApiAddClientsLabelsArgs(
            client_ids=[self.client_ids[0]], labels=["foo"]
        ),
        context=self.context,
    )

    cid = self.client_ids[0]
    labels = data_store.REL_DB.ReadClientLabels(cid)
    self.assertLen(labels, 1)
    self.assertEqual(labels[0].name, "foo")
    self.assertEqual(labels[0].owner, self.context.username)

    for client_id in self.client_ids[1:]:
      self.assertFalse(data_store.REL_DB.ReadClientLabels(client_id))

  def testAddsTwoLabelsToTwoClients(self):
    self.handler.Handle(
        client_pb2.ApiAddClientsLabelsArgs(
            client_ids=[self.client_ids[0], self.client_ids[1]],
            labels=["foo", "bar"],
        ),
        context=self.context,
    )

    for client_id in self.client_ids[:2]:
      labels = data_store.REL_DB.ReadClientLabels(client_id)
      self.assertLen(labels, 2)
      self.assertEqual(labels[0].owner, self.context.username)
      self.assertEqual(labels[1].owner, self.context.username)
      self.assertCountEqual([labels[0].name, labels[1].name], ["bar", "foo"])

    self.assertFalse(data_store.REL_DB.ReadClientLabels(self.client_ids[2]))

  def testForemanTimeIsResetOnLabelAdd(self):
    cid = self.client_ids[0]

    data_store.REL_DB.WriteClientMetadata(
        cid,
        last_foreman=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3600),
    )

    self.handler.Handle(
        client_pb2.ApiAddClientsLabelsArgs(client_ids=[cid], labels=["foo"]),
        context=self.context,
    )

    md = data_store.REL_DB.ReadClientMetadata(cid)
    self.assertTrue(md.HasField("last_foreman_time"))
    self.assertEqual(
        md.last_foreman_time,
        int(data_store.REL_DB.MinTimestamp()),
    )


class ApiRemoveClientsLabelsHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Test for ApiRemoveClientsLabelsHandler."""

  def setUp(self):
    super().setUp()
    self.client_ids = self.SetupClients(3)
    self.handler = client_plugin.ApiRemoveClientsLabelsHandler()

  def testRemovesUserLabelFromSingleClient(self):
    data_store.REL_DB.WriteClientMetadata(self.client_ids[0])
    data_store.REL_DB.AddClientLabels(
        self.client_ids[0], self.context.username, ["foo", "bar"]
    )

    self.handler.Handle(
        client_pb2.ApiRemoveClientsLabelsArgs(
            client_ids=[self.client_ids[0]], labels=["foo"]
        ),
        context=self.context,
    )

    labels = data_store.REL_DB.ReadClientLabels(self.client_ids[0])
    self.assertLen(labels, 1)
    self.assertEqual(labels[0].name, "bar")
    self.assertEqual(labels[0].owner, self.context.username)

  def testDoesNotRemoveSystemLabelFromSingleClient(self):
    data_store.REL_DB.WriteClientMetadata(self.client_ids[0])
    data_store.REL_DB.WriteGRRUser("GRR")
    data_store.REL_DB.AddClientLabels(self.client_ids[0], "GRR", ["foo"])
    idx = client_index.ClientIndex()
    idx.AddClientLabels(self.client_ids[0], ["foo"])

    self.handler.Handle(
        client_pb2.ApiRemoveClientsLabelsArgs(
            client_ids=[self.client_ids[0]], labels=["foo"]
        ),
        context=self.context,
    )

    labels = data_store.REL_DB.ReadClientLabels(self.client_ids[0])
    self.assertLen(labels, 1)
    # The label is still in the index.
    self.assertEqual(idx.LookupClients(["label:foo"]), [self.client_ids[0]])

  def testRemovesUserLabelWhenSystemLabelWithSimilarNameAlsoExists(self):
    data_store.REL_DB.WriteGRRUser(self.context.username)
    data_store.REL_DB.WriteGRRUser("GRR")

    data_store.REL_DB.WriteClientMetadata(self.client_ids[0])
    data_store.REL_DB.AddClientLabels(
        self.client_ids[0], self.context.username, ["foo"]
    )
    data_store.REL_DB.AddClientLabels(self.client_ids[0], "GRR", ["foo"])
    idx = client_index.ClientIndex()
    idx.AddClientLabels(self.client_ids[0], ["foo"])

    self.handler.Handle(
        client_pb2.ApiRemoveClientsLabelsArgs(
            client_ids=[self.client_ids[0]], labels=["foo"]
        ),
        context=self.context,
    )

    labels = data_store.REL_DB.ReadClientLabels(self.client_ids[0])
    self.assertLen(labels, 1)
    self.assertEqual(labels[0].name, "foo")
    self.assertEqual(labels[0].owner, "GRR")
    # The label is still in the index.
    self.assertEqual(idx.LookupClients(["label:foo"]), [self.client_ids[0]])


class ApiLabelsRestrictedSearchClientsHandlerTestRelational(
    api_test_lib.ApiCallHandlerTest
):
  """Tests ApiLabelsRestrictedSearchClientsHandler."""

  def setUp(self):
    super().setUp()

    self.client_ids = self.SetupClients(4)

    data_store.REL_DB.WriteGRRUser("david")
    data_store.REL_DB.WriteGRRUser("peter")
    data_store.REL_DB.WriteGRRUser("peter_oth")

    data_store.REL_DB.AddClientLabels(self.client_ids[0], "david", ["foo"])
    data_store.REL_DB.AddClientLabels(self.client_ids[1], "david", ["not-foo"])
    data_store.REL_DB.AddClientLabels(self.client_ids[2], "peter_oth", ["bar"])
    data_store.REL_DB.AddClientLabels(self.client_ids[3], "peter", ["bar"])

    index = client_index.ClientIndex()
    index.AddClientLabels(self.client_ids[0], ["foo"])
    index.AddClientLabels(self.client_ids[1], ["not-foo"])
    index.AddClientLabels(self.client_ids[2], ["bar"])
    index.AddClientLabels(self.client_ids[3], ["bar"])

    self.handler = client_plugin.ApiLabelsRestrictedSearchClientsHandler(
        allow_labels=["foo", "bar"], allow_labels_owners=["david", "peter"]
    )

  def _Setup100Clients(self):
    self.client_ids = self.SetupClients(100)
    index = client_index.ClientIndex()
    for client_id in self.client_ids:
      data_store.REL_DB.AddClientLabels(client_id, "david", ["foo"])
      index.AddClientLabels(client_id, ["foo"])

  def testSearchWithoutArgsReturnsOnlyClientsWithAllowedLabels(self):
    result = self.handler.Handle(
        client_pb2.ApiSearchClientsArgs(), context=self.context
    )

    self.assertLen(result.items, 2)
    sorted_items = sorted(result.items, key=lambda r: r.client_id)

    self.assertEqual(sorted_items[0].client_id, self.client_ids[0])
    self.assertEqual(sorted_items[1].client_id, self.client_ids[3])

  def testSearchWithNonAllowedLabelReturnsNothing(self):
    result = self.handler.Handle(
        client_pb2.ApiSearchClientsArgs(query="label:not-foo"),
        context=self.context,
    )
    self.assertFalse(result.items)

  def testSearchWithAllowedLabelReturnsSubSet(self):
    result = self.handler.Handle(
        client_pb2.ApiSearchClientsArgs(query="label:foo"),
        context=self.context,
    )
    self.assertLen(result.items, 1)
    self.assertEqual(result.items[0].client_id, self.client_ids[0])

    result = self.handler.Handle(
        client_pb2.ApiSearchClientsArgs(query="label:bar"),
        context=self.context,
    )
    self.assertLen(result.items, 1)
    self.assertEqual(result.items[0].client_id, self.client_ids[3])

  def testSearchWithAllowedClientIdsReturnsSubSet(self):
    result = self.handler.Handle(
        client_pb2.ApiSearchClientsArgs(query=self.client_ids[0]),
        context=self.context,
    )
    self.assertLen(result.items, 1)
    self.assertEqual(result.items[0].client_id, self.client_ids[0])

    result = self.handler.Handle(
        client_pb2.ApiSearchClientsArgs(query=self.client_ids[3]),
        context=self.context,
    )
    self.assertLen(result.items, 1)
    self.assertEqual(result.items[0].client_id, self.client_ids[3])

  def testSearchWithDisallowedClientIdsReturnsNothing(self):
    result = self.handler.Handle(
        client_pb2.ApiSearchClientsArgs(query=self.client_ids[1]),
        context=self.context,
    )
    self.assertFalse(result.items)

    result = self.handler.Handle(
        client_pb2.ApiSearchClientsArgs(query=self.client_ids[2]),
        context=self.context,
    )
    self.assertFalse(result.items)

  def testSearchOrder(self):
    self._Setup100Clients()

    result = self.handler.Handle(
        client_pb2.ApiSearchClientsArgs(
            query="label:foo", offset=0, count=1000
        ),
        context=self.context,
    )
    self.assertEqual(
        [str(res.client_id) for res in result.items], self.client_ids
    )

    result = []
    for offset, count in [(0, 10), (10, 40), (50, 25), (75, 500)]:
      result.extend(
          self.handler.Handle(
              client_pb2.ApiSearchClientsArgs(
                  query="label:foo", offset=offset, count=count
              ),
              context=self.context,
          ).items
      )
    self.assertEqual([str(res.client_id) for res in result], self.client_ids)


class ApiInterrogateClientHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Test for ApiInterrogateClientHandler."""

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)
    self.handler = client_plugin.ApiInterrogateClientHandler()

  def testInterrogateFlowIsStarted(self):
    self.assertEmpty(data_store.REL_DB.ReadAllFlowObjects(self.client_id))

    args = client_pb2.ApiInterrogateClientArgs(client_id=self.client_id)
    result = self.handler.Handle(args, context=self.context)

    results = data_store.REL_DB.ReadAllFlowObjects(self.client_id)
    self.assertLen(results, 1)
    self.assertEqual(result.operation_id, results[0].flow_id)
    self.assertEqual(results[0].creator, "api_test_user")


class ApiGetClientVersionTimesTest(api_test_lib.ApiCallHandlerTest):
  """Test for ApiGetClientVersionTimes using the relational db."""

  def setUp(self):
    super().setUp()
    self.handler = client_plugin.ApiGetClientVersionTimesHandler()

  def testHandler(self):
    self._SetUpClient()
    args = client_pb2.ApiGetClientVersionTimesArgs(client_id=self.client_id)
    result = self.handler.Handle(args, context=self.context)

    self.assertLen(result.times, 3)
    self.assertEqual(result.times[0], 100_000_000)
    self.assertEqual(result.times[1], 45_000_000)
    self.assertEqual(result.times[2], 42_000_000)

  def _SetUpClient(self):
    for time in [42, 45, 100]:
      with test_lib.FakeTime(time):
        self.client_id = self.SetupClient(0)


class ApiGetClientVersionsTest(api_test_lib.ApiCallHandlerTest):
  """Test for ApiGetClientVersions using the relational db."""

  def setUp(self):
    super().setUp()
    self.handler = client_plugin.ApiGetClientVersionsHandler()

  def testReturnsAll(self):
    self.client_id = self.SetupClient(0)
    self.fqdn = "test1234.examples.com"
    kernels = [42, 45, 100]

    for time in kernels:
      with test_lib.FakeTime(time):
        client = objects_pb2.ClientSnapshot(
            client_id=self.client_id, kernel=f"{time}"
        )
        client.knowledge_base.fqdn = self.fqdn
        data_store.REL_DB.WriteClientSnapshot(client)

    args = client_pb2.ApiGetClientVersionsArgs(client_id=self.client_id)
    with test_lib.FakeTime(101):
      result = self.handler.Handle(args, context=self.context)

    self.assertLen(result.items, 3)
    self.assertEqual(result.items[0].client_id, self.client_id)
    self.assertEqual(result.items[0].knowledge_base.fqdn, self.fqdn)
    self.assertEqual(result.items[0].os_info.kernel, f"{kernels[0]}")
    self.assertEqual(result.items[1].client_id, self.client_id)
    self.assertEqual(result.items[1].knowledge_base.fqdn, self.fqdn)
    self.assertEqual(result.items[1].os_info.kernel, f"{kernels[1]}")
    self.assertEqual(result.items[2].client_id, self.client_id)
    self.assertEqual(result.items[2].knowledge_base.fqdn, self.fqdn)
    self.assertEqual(result.items[2].os_info.kernel, f"{kernels[2]}")

  def testFiltersStartAndEnd(self):
    self.client_id = self.SetupClient(0)
    self.fqdn = "test1234.examples.com"
    kernels = [42, 45, 100]

    for time in kernels:
      with test_lib.FakeTime(time):
        client = objects_pb2.ClientSnapshot(
            client_id=self.client_id, kernel=f"{time}"
        )
        client.knowledge_base.fqdn = self.fqdn
        data_store.REL_DB.WriteClientSnapshot(client)

    args = client_pb2.ApiGetClientVersionsArgs(
        client_id=self.client_id,
        start=43000000,
        end=53000000,
    )
    with test_lib.FakeTime(101):
      result = self.handler.Handle(args, context=self.context)

    self.assertLen(result.items, 1)
    self.assertEqual(result.items[0].client_id, self.client_id)
    self.assertEqual(result.items[0].knowledge_base.fqdn, self.fqdn)
    self.assertEqual(result.items[0].os_info.kernel, f"{kernels[1]}")


def TSProtoFromString(string):
  ts = timestamp_pb2.Timestamp()
  ts.FromJsonString(string)
  return ts


class ApiFleetspeakIntegrationTest(api_test_lib.ApiCallHandlerTest):

  def testUpdateClientsFromFleetspeak(self):
    client_id_1 = "C." + "1" * 16
    client_id_2 = "C." + "2" * 16
    client_id_3 = "C." + "3" * 16
    clients = [
        client_pb2.ApiClient(client_id=client_id_1),
        client_pb2.ApiClient(client_id=client_id_2),
        client_pb2.ApiClient(client_id=client_id_3),
    ]
    conn = mock.MagicMock()
    conn.outgoing.ListClients.return_value = admin_pb2.ListClientsResponse(
        clients=[
            admin_pb2.Client(
                client_id=fleetspeak_utils.GRRIDToFleetspeakID(client_id_1),
                last_contact_time=TSProtoFromString("2018-01-01T00:00:01Z"),
                last_clock=TSProtoFromString("2018-01-01T00:00:02Z"),
            ),
            admin_pb2.Client(
                client_id=fleetspeak_utils.GRRIDToFleetspeakID(client_id_2),
                last_contact_time=TSProtoFromString("2018-01-02T00:00:01Z"),
                last_clock=TSProtoFromString("2018-01-02T00:00:02Z"),
            ),
        ]
    )
    with mock.patch.object(fleetspeak_connector, "CONN", conn):
      client_plugin.UpdateClientsFromFleetspeak(clients)
    self.assertEqual(
        clients,
        [
            client_pb2.ApiClient(
                client_id=client_id_1,
                last_seen_at=rdfvalue.RDFDatetime.FromHumanReadable(
                    "2018-01-01T00:00:01Z"
                ).AsMicrosecondsSinceEpoch(),
                last_clock=rdfvalue.RDFDatetime.FromHumanReadable(
                    "2018-01-01T00:00:02Z"
                ).AsMicrosecondsSinceEpoch(),
            ),
            client_pb2.ApiClient(
                client_id=client_id_2,
                last_seen_at=rdfvalue.RDFDatetime.FromHumanReadable(
                    "2018-01-02T00:00:01Z"
                ).AsMicrosecondsSinceEpoch(),
                last_clock=rdfvalue.RDFDatetime.FromHumanReadable(
                    "2018-01-02T00:00:02Z"
                ).AsMicrosecondsSinceEpoch(),
            ),
            client_pb2.ApiClient(client_id=client_id_3),
        ],
    )

  def testGetAddrFromFleetspeakIpV4(self):
    client_id = client_plugin.ApiClientId("C." + "1" * 16)
    conn = mock.MagicMock()
    conn.outgoing.ListClients.return_value = admin_pb2.ListClientsResponse(
        clients=[
            admin_pb2.Client(
                client_id=fleetspeak_utils.GRRIDToFleetspeakID(client_id),
                last_contact_address="100.1.1.100:50000",
                last_contact_time=TSProtoFromString("2018-01-01T00:00:01Z"),
                last_clock=TSProtoFromString("2018-01-01T00:00:02Z"),
            )
        ]
    )
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
                last_clock=TSProtoFromString("2018-01-01T00:00:02Z"),
            )
        ]
    )
    with mock.patch.object(fleetspeak_connector, "CONN", conn):
      ip_str, ipaddr_obj = client_plugin._GetAddrFromFleetspeak(client_id)
      self.assertEqual(ip_str, "2001:0db8:85a3::8a2e:0370:7334")
      self.assertEqual(
          ipaddr_obj,
          ipaddress.ip_address("2001:0db8:85a3:0000:0000:8a2e:0370:7334"),
      )

  def testGetAddrFromFleetspeakMissing(self):
    client_id = client_plugin.ApiClientId("C." + "1" * 16)
    conn = mock.MagicMock()
    conn.outgoing.ListClients.return_value = admin_pb2.ListClientsResponse(
        clients=[
            admin_pb2.Client(
                client_id=fleetspeak_utils.GRRIDToFleetspeakID(client_id),
                last_contact_time=TSProtoFromString("2018-01-01T00:00:01Z"),
                last_clock=TSProtoFromString("2018-01-01T00:00:02Z"),
            )
        ]
    )
    with mock.patch.object(fleetspeak_connector, "CONN", conn):
      ip_str, ipaddr_obj = client_plugin._GetAddrFromFleetspeak(client_id)
      self.assertEqual(ip_str, "")
      self.assertIsNone(ipaddr_obj)


@db_test_lib.TestDatabases()
class ApiSearchClientsHandlerTest(api_test_lib.ApiCallHandlerTest):

  def setUp(self):
    super().setUp()
    self.search_handler = client_plugin.ApiSearchClientsHandler()
    self.add_labels_handler = client_plugin.ApiAddClientsLabelsHandler()

  def _AddLabels(self, client_id, labels):
    args = client_pb2.ApiAddClientsLabelsArgs(
        client_ids=[client_id],
        labels=labels,
    )
    self.add_labels_handler.Handle(args=args, context=self.context)

  def testSearchByLabel(self):
    client_id = self.SetupClient(
        0, ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(13)
    )
    self._AddLabels(client_id, labels=["foo"])
    api_result = self.search_handler.Handle(
        client_pb2.ApiSearchClientsArgs(query="label:foo")
    )
    self.assertLen(api_result.items, 1)
    self.assertEqual(api_result.items[0].client_id, client_id)
    self.assertEqual(
        api_result.items[0].last_seen_at,
        int(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(13)),
    )

  def testUnicode(self):
    client_a_id = self.SetupClient(0)
    self._AddLabels(client_a_id, labels=["gżegżółka"])

    client_b_id = self.SetupClient(1)
    self._AddLabels(client_b_id, labels=["orłosęp"])

    args_a = client_pb2.ApiSearchClientsArgs(
        query="label:gżegżółka", offset=0, count=128
    )

    result_a = self.search_handler.Handle(args_a, context=self.context)
    self.assertLen(result_a.items, 1)
    self.assertEqual(result_a.items[0].client_id, client_a_id)

    args_b = client_pb2.ApiSearchClientsArgs(
        query="label:orłosęp", offset=0, count=128
    )

    result_b = self.search_handler.Handle(args_b, context=self.context)
    self.assertLen(result_b.items, 1)
    self.assertEqual(result_b.items[0].client_id, client_b_id)

  def testUnicodeMultipleClients(self):
    client_a_id = self.SetupClient(0)
    self._AddLabels(client_a_id, labels=["ścierwnik", "krzyżówka"])

    client_b_id = self.SetupClient(1)
    self._AddLabels(client_b_id, labels=["nurogęś", "ścierwnik"])

    args = client_pb2.ApiSearchClientsArgs(
        query="label:ścierwnik", offset=0, count=1000
    )

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

    args = client_pb2.ApiSearchClientsArgs(
        query="label:raróg label:sokół", offset=0, count=1000
    )

    result = self.search_handler.Handle(args, context=self.context)
    result_client_ids = [item.client_id for item in result.items]
    self.assertCountEqual(result_client_ids, [client_a_id, client_c_id])

  def testUnicodeQuoted(self):
    client_id = self.SetupClient(0)
    self._AddLabels(
        client_id, labels=["dzięcioł białoszyi", "świergotek łąkowy"]
    )

    args = client_pb2.ApiSearchClientsArgs(
        query="label:'dzięcioł białoszyi' label:'świergotek łąkowy'"
    )

    result = self.search_handler.Handle(args, context=self.context)
    self.assertLen(result.items, 1)
    self.assertEqual(result.items[0].client_id, client_id)


class ApiGetFleetspeakPendingMessageCountHandlerTest(
    api_test_lib.ApiCallHandlerTest
):

  @mock.patch.object(fleetspeak_connector, "CONN")
  def testHandle(self, _):
    handler = client_plugin.ApiGetFleetspeakPendingMessageCountHandler()
    args = client_pb2.ApiGetFleetspeakPendingMessageCountArgs(
        client_id="C.1111111111111111"
    )
    with mock.patch.object(
        fleetspeak_utils, "GetFleetspeakPendingMessageCount", return_value=42
    ) as mock_get:
      result = handler.Handle(args)
      self.assertEqual(mock_get.call_args[0][0], "C.1111111111111111")
      self.assertEqual(result.count, 42)


class ApiGetFleetspeakPendingMessagesHandlerTest(
    api_test_lib.ApiCallHandlerTest
):

  @mock.patch.object(fleetspeak_connector, "CONN")
  def testHandle(self, _):
    handler = client_plugin.ApiGetFleetspeakPendingMessagesHandler()
    args = client_pb2.ApiGetFleetspeakPendingMessagesArgs(
        client_id="C.1111111111111111", offset=1, limit=2, want_data=True
    )
    fleetspeak_proto = admin_pb2.GetPendingMessagesResponse()
    text_format.Parse(
        """
        messages: {
          message_id: "m1"
          source: {
            client_id: "\x00\x00\x00\x00\x00\x00\x00\x01"
            service_name: "s1"
          }
          source_message_id: "m2"
          destination : {
            client_id: "\x00\x00\x00\x00\x00\x00\x00\x02"
            service_name: "s2"
          }
          message_type: "mt"
          creation_time: {
            seconds: 1617187637
            nanos: 101000
          }
          data: {
            [type.googleapis.com/google.protobuf.Timestamp] {
              seconds: 1234
            }
          }
          validation_info: {
            tags: {
              key: "k1"
              value: "v1"
            }
          }
          result: {
            processed_time: {
              seconds: 1617187637
              nanos: 101000
            }
            failed: True
            failed_reason: "fr"
          }
          priority: LOW
          background: true
          annotations: {
            entries: {
              key: "ak1"
              value: "av1"
            }
          }
        }
        """,
        fleetspeak_proto,
    )
    expected_result = client_pb2.ApiGetFleetspeakPendingMessagesResult()
    text_format.Parse(
        """
        messages: {
          message_id: "m1"
          source: {
            client_id: "C.0000000000000001"
            service_name: "s1"
          }
          source_message_id: "m2"
          destination : {
            client_id: "C.0000000000000002"
            service_name: "s2"
          }
          message_type: "mt"
          creation_time: 1617187637000101
          data: {
            [type.googleapis.com/google.protobuf.Timestamp] {
              seconds: 1234
            }
          }
          validation_info: {
            tags: {
              key: "k1"
              value: "v1"
            }
          }
          result: {
            processed_time: 1617187637000101
            failed: True
            failed_reason: "fr"
          }
          priority: LOW
          background: true
          annotations: {
            entries: {
              key: "ak1"
              value: "av1"
            }
          }
        }
        """,
        expected_result,
    )
    with mock.patch.object(
        fleetspeak_utils,
        "GetFleetspeakPendingMessages",
        return_value=fleetspeak_proto,
    ) as mock_get:
      result = handler.Handle(args)
      self.assertEqual(mock_get.call_args[0][0], "C.1111111111111111")
      self.assertEqual(mock_get.call_args[1]["offset"], 1)
      self.assertEqual(mock_get.call_args[1]["limit"], 2)
      self.assertEqual(mock_get.call_args[1]["want_data"], True)
      self.assertEqual(result, expected_result)

  @mock.patch.object(fleetspeak_connector, "CONN")
  def testHandle_EmptySourceClientId(self, _):
    handler = client_plugin.ApiGetFleetspeakPendingMessagesHandler()
    args = client_pb2.ApiGetFleetspeakPendingMessagesArgs(
        client_id="C.1111111111111111"
    )
    fleetspeak_proto = admin_pb2.GetPendingMessagesResponse()
    text_format.Parse(
        """
        messages: {
          source: {
            service_name: "s1"
            client_id: ""
          }
        }
        """,
        fleetspeak_proto,
    )
    expected_result = client_pb2.ApiGetFleetspeakPendingMessagesResult()
    text_format.Parse(
        """
        messages: {
          source: {
            service_name: "s1"
          }
        }
        """,
        expected_result,
    )
    with mock.patch.object(
        fleetspeak_utils,
        "GetFleetspeakPendingMessages",
        return_value=fleetspeak_proto,
    ):
      result = handler.Handle(args)
      print(result)
      print("---------")
      print(expected_result)
      self.assertEqual(result, expected_result)

  @mock.patch.object(fleetspeak_connector, "CONN")
  def testHandle_MissingSourceClientId(self, _):
    handler = client_plugin.ApiGetFleetspeakPendingMessagesHandler()
    args = client_pb2.ApiGetFleetspeakPendingMessagesArgs(
        client_id="C.1111111111111111"
    )
    fleetspeak_proto = admin_pb2.GetPendingMessagesResponse()
    text_format.Parse(
        """
        messages: {
          source: {
            service_name: "s1"
          }
        }
        """,
        fleetspeak_proto,
    )
    expected_result = client_pb2.ApiGetFleetspeakPendingMessagesResult()
    text_format.Parse(
        """
        messages: {
          source: {
            service_name: "s1"
          }
        }
        """,
        expected_result,
    )
    with mock.patch.object(
        fleetspeak_utils,
        "GetFleetspeakPendingMessages",
        return_value=fleetspeak_proto,
    ):
      result = handler.Handle(args)
      self.assertEqual(result, expected_result)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
