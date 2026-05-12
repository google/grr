#!/usr/bin/env python
import ipaddress

from absl.testing import absltest

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_proto import jobs_pb2
from grr_response_proto import knowledge_base_pb2
from grr_response_proto import objects_pb2
from grr_response_proto import sysinfo_pb2
from grr_response_proto.api import client_pb2
from grr_response_server.models import clients as models_clients


class FleetspeakValidationInfoFromDictTest(absltest.TestCase):

  def testEmpty(self):
    result = models_clients.FleetspeakValidationInfoFromDict({})

    self.assertEmpty(result.tags)

  def testSingle(self):
    result = models_clients.FleetspeakValidationInfoFromDict({"foo": "bar"})

    self.assertLen(result.tags, 1)
    self.assertEqual(result.tags[0].key, "foo")
    self.assertEqual(result.tags[0].value, "bar")

  def testMultiple(self):
    result = models_clients.FleetspeakValidationInfoFromDict({
        "1": "foo",
        "2": "bar",
        "3": "quux",
    })

    self.assertLen(result.tags, 3)

    tags = sorted(result.tags, key=lambda _: _.key)

    self.assertEqual(tags[0].key, "1")
    self.assertEqual(tags[1].key, "2")
    self.assertEqual(tags[2].key, "3")

    self.assertEqual(tags[0].value, "foo")
    self.assertEqual(tags[1].value, "bar")
    self.assertEqual(tags[2].value, "quux")


class FleetspeakValidationInfoToDictTest(absltest.TestCase):

  def testEmpty(self):
    info = jobs_pb2.FleetspeakValidationInfo()

    result = models_clients.FleetspeakValidationInfoToDict(info)
    self.assertEmpty(result)

  def testSingle(self):
    info = jobs_pb2.FleetspeakValidationInfo()
    info.tags.add(key="foo", value="bar")

    result = models_clients.FleetspeakValidationInfoToDict(info)
    self.assertDictEqual(result, {"foo": "bar"})

  def testMultiple(self):
    info = jobs_pb2.FleetspeakValidationInfo()
    info.tags.add(key="1", value="foo")
    info.tags.add(key="2", value="bar")
    info.tags.add(key="3", value="quux")

    result = models_clients.FleetspeakValidationInfoToDict(info)
    self.assertDictEqual(result, {"1": "foo", "2": "bar", "3": "quux"})

  def testEmptyKey(self):
    info = jobs_pb2.FleetspeakValidationInfo()
    info.tags.add(key="", value="foo")

    with self.assertRaises(ValueError) as context:
      models_clients.FleetspeakValidationInfoToDict(info)

    self.assertEqual(str(context.exception), "Empty tag key")

  def testEmptyValue(self):
    info = jobs_pb2.FleetspeakValidationInfo()
    info.tags.add(key="foo", value="")

    with self.assertRaises(ValueError) as context:
      models_clients.FleetspeakValidationInfoToDict(info)

    self.assertEqual(str(context.exception), "Empty tag value for key 'foo'")

  def testDuplicateKey(self):
    info = jobs_pb2.FleetspeakValidationInfo()
    info.tags.add(key="foo", value="bar")
    info.tags.add(key="foo", value="baz")

    with self.assertRaises(ValueError) as context:
      models_clients.FleetspeakValidationInfoToDict(info)

    self.assertEqual(str(context.exception), "Duplicate tag key 'foo'")


class NetworkAddressFromPackedBytes(absltest.TestCase):

  def testInvalidLength(self):
    with self.assertRaises(ValueError):
      models_clients.NetworkAddressFromPackedBytes(b"0.1.2.3")

  def testIPv4(self):
    packed_bytes = ipaddress.IPv4Address("196.128.0.1").packed

    result = models_clients.NetworkAddressFromPackedBytes(packed_bytes)
    self.assertEqual(result.packed_bytes, packed_bytes)
    self.assertEqual(result.address_type, jobs_pb2.NetworkAddress.INET)

  def testIPv6(self):
    packed_bytes = ipaddress.IPv6Address("::1").packed

    result = models_clients.NetworkAddressFromPackedBytes(packed_bytes)
    self.assertEqual(result.packed_bytes, packed_bytes)
    self.assertEqual(result.address_type, jobs_pb2.NetworkAddress.INET6)


class NetworkAddressFromIPAddress(absltest.TestCase):

  def testIPv4(self):
    ip_address = ipaddress.IPv4Address("196.128.0.1")

    result = models_clients.NetworkAddressFromIPAddress(ip_address)
    self.assertEqual(result.packed_bytes, ip_address.packed)
    self.assertEqual(result.address_type, jobs_pb2.NetworkAddress.INET)

  def testIPv6(self):
    ip_address = ipaddress.IPv6Address("::1")

    result = models_clients.NetworkAddressFromIPAddress(ip_address)
    self.assertEqual(result.packed_bytes, ip_address.packed)
    self.assertEqual(result.address_type, jobs_pb2.NetworkAddress.INET6)


def _GenerateClientSnapshot() -> objects_pb2.ClientSnapshot:
  snapshot = objects_pb2.ClientSnapshot(client_id="C.0000000000000000")
  snapshot.metadata.source_flow_id = "ABCDEF"
  client_information = jobs_pb2.ClientInformation(
      client_name="GRR Monitor",
      client_version=1234,
      client_description="some client description",
      build_time="1980-01-01T12:00:00.000000+00:00",
      labels=["label1", "label2"],
  )
  snapshot.startup_info.client_info.CopyFrom(client_information)
  snapshot.startup_info.boot_time = 20240101
  hardware_info = sysinfo_pb2.HardwareInfo(
      system_manufacturer="System-Manufacturer-123",
      bios_version="Bios-Version-123",
      serial_number="123abc",
      system_uuid="a-b-c-1-2-3",
  )
  snapshot.hardware_info.CopyFrom(hardware_info)
  snapshot.os_release = "Windows"
  snapshot.os_version = "14.4"
  snapshot.kernel = "4.0.0"
  snapshot.arch = "x86_64"
  users = [
      knowledge_base_pb2.User(username="fred", full_name="Ok Guy Fred"),
      knowledge_base_pb2.User(username="joe", full_name="Good Guy Joe"),
  ]
  knowledge_base = knowledge_base_pb2.KnowledgeBase(
      os="Linux",
      os_release="RedHat Linux",
      os_major_version=4,
      os_minor_version=2,
      fqdn="test123.examples.com",
      users=users,
  )
  snapshot.knowledge_base.CopyFrom(knowledge_base)
  interfaces = [
      jobs_pb2.Interface(
          ifname="if0",
          addresses=[
              jobs_pb2.NetworkAddress(
                  packed_bytes=ipaddress.IPv4Address("192.168.0.123").packed,
                  address_type=jobs_pb2.NetworkAddress.INET,
              ),
              jobs_pb2.NetworkAddress(
                  packed_bytes=ipaddress.IPv6Address("2001:abcd::123").packed,
                  address_type=jobs_pb2.NetworkAddress.INET6,
              ),
          ],
      ),
      jobs_pb2.Interface(
          ifname="if1",
          mac_address=rdf_client_network.MacAddress.FromHumanReadableAddress(
              "aabbccddee%02x" % 123
          ).SerializeToBytes(),
      ),
      jobs_pb2.Interface(
          ifname="if2",
          mac_address=rdf_client_network.MacAddress.FromHumanReadableAddress(
              "bbccddeeff%02x" % 123
          ).SerializeToBytes(),
      ),
  ]
  snapshot.interfaces.extend(interfaces)
  volumes = [
      sysinfo_pb2.Volume(
          windowsvolume=sysinfo_pb2.WindowsVolume(drive_letter="C:"),
          bytes_per_sector=4096,
          sectors_per_allocation_unit=1,
          actual_available_allocation_units=50,
          total_allocation_units=100,
      ),
      sysinfo_pb2.Volume(
          unixvolume=sysinfo_pb2.UnixVolume(mount_point="/"),
          bytes_per_sector=4096,
          sectors_per_allocation_unit=1,
          actual_available_allocation_units=10,
          total_allocation_units=100,
      ),
  ]
  snapshot.volumes.extend(volumes)
  cloud_instance = jobs_pb2.CloudInstance(
      cloud_type=jobs_pb2.CloudInstance.InstanceType.GOOGLE,
      google=jobs_pb2.GoogleCloudInstance(
          unique_id="us-central1-a/myproject/1771384456894610289"
      ),
  )
  snapshot.cloud_instance.CopyFrom(cloud_instance)
  timestamp = 20240404
  snapshot.timestamp = timestamp
  snapshot.edr_agents.append(jobs_pb2.EdrAgent(name="foo", agent_id="1337"))
  snapshot.edr_agents.append(jobs_pb2.EdrAgent(name="bar", agent_id="108"))
  snapshot.memory_size = 123456

  return snapshot


class ApiClientFromClientSnapshot(absltest.TestCase):

  def testFullClientSnapshot(self):
    snapshot = _GenerateClientSnapshot()
    want_client = client_pb2.ApiClient(
        client_id="C.0000000000000000",
        urn="aff4:/C.0000000000000000",
        source_flow_id="ABCDEF",
        agent_info=snapshot.startup_info.client_info,
        hardware_info=snapshot.hardware_info,
        os_info=jobs_pb2.Uname(
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
    )
    got_api_client = models_clients.ApiClientFromClientSnapshot(snapshot)
    self.assertEqual(want_client, got_api_client)


class ApiClientFromClientFullInfo(absltest.TestCase):

  def testWithSnapshot(self):
    snapshot = _GenerateClientSnapshot()
    client_info = objects_pb2.ClientFullInfo(last_snapshot=snapshot)

    want_client = client_pb2.ApiClient(
        client_id="C.0000000000000000",
        urn="aff4:/C.0000000000000000",
        source_flow_id="ABCDEF",
        agent_info=snapshot.startup_info.client_info,
        hardware_info=snapshot.hardware_info,
        os_info=jobs_pb2.Uname(
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
    )

    got_api_client = models_clients.ApiClientFromClientFullInfo(
        "C.0000000000000000", client_info
    )

    self.assertEqual(got_api_client, want_client)

  def testWithSnapshot_BadId(self):
    snapshot = _GenerateClientSnapshot()
    client_info = objects_pb2.ClientFullInfo(last_snapshot=snapshot)

    with self.assertRaises(ValueError):
      models_clients.ApiClientFromClientFullInfo(
          "C.1111111111111111", client_info
      )

  def _GenerateClientFullInfo(
      self, major=1, minor=2, patch=3, rrg_args_str="some args --were passed"
  ) -> objects_pb2.ClientFullInfo:
    first_seen_time = 20220101
    boot_time = 20220202
    ping_time = 20220303
    crash_time = 20220404
    metadata = objects_pb2.ClientMetadata(
        first_seen=first_seen_time,
        ping=ping_time,
        last_crash_timestamp=crash_time,
    )
    labels = [
        objects_pb2.ClientLabel(name="label3"),
        objects_pb2.ClientLabel(name="label4"),
    ]
    client_info = objects_pb2.ClientFullInfo(metadata=metadata, labels=labels)
    client_info.last_startup_info.boot_time = boot_time
    client_information = jobs_pb2.ClientInformation(
        client_name="GRR Monitor",
        client_version=1234,
        client_description="some client description",
        build_time="1980-01-01T12:00:00.000000+00:00",
        labels=["label1", "label2"],
    )
    client_info.last_startup_info.client_info.CopyFrom(client_information)
    client_info.last_rrg_startup.metadata.version.major = major
    client_info.last_rrg_startup.metadata.version.minor = minor
    client_info.last_rrg_startup.metadata.version.patch = patch
    client_info.last_rrg_startup.args.extend([rrg_args_str])

    return client_info

  def testWithoutSnapshot(self):
    rrg_args_str = "some args --were passed"
    client_info = self._GenerateClientFullInfo(1, 2, 3, rrg_args_str)
    want_client = client_pb2.ApiClient(
        client_id="C.0000000000000000",
        agent_info=client_info.last_startup_info.client_info,
        age=client_info.metadata.first_seen,
        first_seen_at=client_info.metadata.first_seen,
        last_booted_at=client_info.last_startup_info.boot_time,
        last_seen_at=client_info.metadata.ping,
        last_crash_at=client_info.metadata.last_crash_timestamp,
        rrg_args=[rrg_args_str],
        rrg_version="1.2.3",
    )
    for label in client_info.labels:
      want_client.labels.append(label)

    got_api_client = models_clients.ApiClientFromClientFullInfo(
        "C.0000000000000000", client_info
    )

    self.assertEqual(got_api_client, want_client)

  def testInitFromClientInfoAgeWithSnapshot(self):
    first_seen_time = rdfvalue.RDFDatetime.FromHumanReadable("2022-01-01")
    last_snapshot_time = rdfvalue.RDFDatetime.FromHumanReadable("2022-02-02")

    info = objects_pb2.ClientFullInfo()
    info.metadata.first_seen = int(first_seen_time)
    info.last_snapshot.client_id = "C.1122334455667788"
    info.last_snapshot.timestamp = int(last_snapshot_time)

    api_client = models_clients.ApiClientFromClientFullInfo(
        "C.1122334455667788", info
    )

    self.assertEqual(api_client.age, int(last_snapshot_time))

  def testInitFromClientInfoWithoutSnapshot(self):
    first_seen_time = rdfvalue.RDFDatetime.FromHumanReadable("2022-01-01")

    info = objects_pb2.ClientFullInfo()
    info.metadata.first_seen = int(first_seen_time)

    api_client = models_clients.ApiClientFromClientFullInfo(
        "C.1122334455667788", info
    )

    self.assertEqual(api_client.age, first_seen_time)

  def testInitFromClientInfoRRG(self):
    info = objects_pb2.ClientFullInfo()
    info.last_rrg_startup.args.extend(["--foo", "--bar", "--baz"])
    info.last_rrg_startup.metadata.version.major = 1
    info.last_rrg_startup.metadata.version.minor = 2
    info.last_rrg_startup.metadata.version.patch = 3
    info.last_rrg_startup.metadata.version.pre = "quux"

    api_client = models_clients.ApiClientFromClientFullInfo(
        "C.0123456789ABCDEF", info
    )

    self.assertEqual(api_client.rrg_version, "1.2.3-quux")
    self.assertEqual(api_client.rrg_args, ["--foo", "--bar", "--baz"])


class GetIpAddressesFromClientSnapshotTest(absltest.TestCase):

  def testEmpty(self):
    snapshot = objects_pb2.ClientSnapshot()
    self.assertEmpty(models_clients.GetIpAddressesFromClientSnapshot(snapshot))

  def testFiltering(self):
    snapshot = objects_pb2.ClientSnapshot()
    interface = snapshot.interfaces.add()

    addr = interface.addresses.add()
    addr.packed_bytes = ipaddress.IPv4Address("127.0.0.1").packed
    addr.address_type = jobs_pb2.NetworkAddress.INET

    addr = interface.addresses.add()
    addr.packed_bytes = ipaddress.IPv6Address("::1").packed
    addr.address_type = jobs_pb2.NetworkAddress.INET6

    addr = interface.addresses.add()
    addr.packed_bytes = ipaddress.IPv6Address("fe80::1").packed
    addr.address_type = jobs_pb2.NetworkAddress.INET6

    addr = interface.addresses.add()
    addr.packed_bytes = ipaddress.IPv4Address("1.2.3.4").packed
    addr.address_type = jobs_pb2.NetworkAddress.INET

    self.assertEqual(
        models_clients.GetIpAddressesFromClientSnapshot(snapshot), ["1.2.3.4"]
    )

  def testIpv4AndIpv6(self):
    snapshot = objects_pb2.ClientSnapshot()
    interface = snapshot.interfaces.add()

    addr4 = interface.addresses.add()
    addr4.packed_bytes = ipaddress.IPv4Address("1.1.1.1").packed
    addr4.address_type = jobs_pb2.NetworkAddress.INET

    addr6 = interface.addresses.add()
    addr6.packed_bytes = ipaddress.IPv6Address("2001:db8::1").packed
    addr6.address_type = jobs_pb2.NetworkAddress.INET6

    self.assertEqual(
        models_clients.GetIpAddressesFromClientSnapshot(snapshot),
        ["1.1.1.1", "2001:db8::1"],
    )

  def testSorting(self):
    snapshot = objects_pb2.ClientSnapshot()
    interface = snapshot.interfaces.add()

    addr = interface.addresses.add()
    addr.packed_bytes = ipaddress.IPv4Address("1.2.3.5").packed
    addr.address_type = jobs_pb2.NetworkAddress.INET

    addr = interface.addresses.add()
    addr.packed_bytes = ipaddress.IPv4Address("1.2.3.4").packed
    addr.address_type = jobs_pb2.NetworkAddress.INET

    self.assertEqual(
        models_clients.GetIpAddressesFromClientSnapshot(snapshot),
        ["1.2.3.4", "1.2.3.5"],
    )


class HumanReadableMacAddressTest(absltest.TestCase):

  def testHexify(self):
    self.assertEqual(
        models_clients.HumanReadableMacAddress(b"\x01\x02\x03\x04\x05\x06"),
        "010203040506",
    )


class GetMacAddressesFromClientSnapshotTest(absltest.TestCase):

  def testEmpty(self):
    snapshot = objects_pb2.ClientSnapshot()
    self.assertEmpty(models_clients.GetMacAddressesFromClientSnapshot(snapshot))

  def testNullAddressFiltered(self):
    snapshot = objects_pb2.ClientSnapshot()
    interface = snapshot.interfaces.add()
    interface.mac_address = b"\x00" * 6
    self.assertEmpty(models_clients.GetMacAddressesFromClientSnapshot(snapshot))

  def testValidAddresses(self):
    snapshot = objects_pb2.ClientSnapshot()
    snapshot.interfaces.add(mac_address=b"\x01\x02\x03\x04\x05\x06")
    snapshot.interfaces.add(mac_address=b"\xaa\xbb\xcc\xdd\xee\xff")
    # Duplicate
    snapshot.interfaces.add(mac_address=b"\x01\x02\x03\x04\x05\x06")

    self.assertEqual(
        models_clients.GetMacAddressesFromClientSnapshot(snapshot),
        ["010203040506", "aabbccddeeff"],
    )


class GetSummaryFromClientSnapshotTest(absltest.TestCase):

  def testClientSummary(self):
    snapshot = _GenerateClientSnapshot()
    summary = models_clients.GetSummaryFromClientSnapshot(snapshot)

    self.assertEqual(summary.client_id, "C.0000000000000000")
    self.assertEqual(summary.timestamp, 20240404)

    self.assertEqual(summary.system_info.release, "Windows")
    self.assertEqual(summary.system_info.version, "14.4")
    self.assertEqual(summary.system_info.kernel, "4.0.0")
    self.assertEqual(summary.system_info.machine, "x86_64")
    self.assertEqual(summary.system_info.fqdn, "test123.examples.com")
    self.assertEqual(summary.system_info.system, "Linux")

    self.assertEqual(summary.serial_number, "123abc")
    self.assertEqual(summary.system_manufacturer, "System-Manufacturer-123")
    self.assertEqual(summary.system_uuid, "a-b-c-1-2-3")

    self.assertEqual(
        summary.cloud_instance_id, "us-central1-a/myproject/1771384456894610289"
    )
    self.assertEqual(summary.cloud_type, jobs_pb2.CloudInstance.GOOGLE)

    self.assertCountEqual([u.username for u in summary.users], ["fred", "joe"])
    self.assertLen(summary.interfaces, 3)
    self.assertEqual(summary.interfaces[0].ifname, "if0")

    self.assertEqual(summary.client_info.client_name, "GRR Monitor")
    self.assertLen(summary.edr_agents, 2)
    self.assertEqual(summary.edr_agents[0].name, "foo")

  def testClientSummaryTimestamp(self):
    snapshot = objects_pb2.ClientSnapshot()
    snapshot.timestamp = 1337
    summary = models_clients.GetSummaryFromClientSnapshot(snapshot)
    self.assertEqual(summary.timestamp, 1337)

  def testGetSummaryEdrAgents(self):
    snapshot = objects_pb2.ClientSnapshot(client_id="C.0123456789012345")
    snapshot.edr_agents.add(name="foo", agent_id="1337")
    snapshot.edr_agents.add(name="bar", agent_id="108")

    summary = models_clients.GetSummaryFromClientSnapshot(snapshot)
    self.assertLen(summary.edr_agents, 2)
    self.assertEqual(summary.edr_agents[0].name, "foo")
    self.assertEqual(summary.edr_agents[1].name, "bar")
    self.assertEqual(summary.edr_agents[0].agent_id, "1337")
    self.assertEqual(summary.edr_agents[1].agent_id, "108")

  def testGetSummaryOsReleaseSnapshot(self):
    snapshot = objects_pb2.ClientSnapshot(
        client_id="C.0123456789012345",
        os_release="Rocky Linux",
    )
    snapshot.knowledge_base.os_release = "RedHat Linux"

    summary = models_clients.GetSummaryFromClientSnapshot(snapshot)
    self.assertEqual(summary.system_info.release, "Rocky Linux")

  def testGetSummaryOsReleaseKnowledgeBase(self):
    snapshot = objects_pb2.ClientSnapshot(client_id="C.0123456789012345")
    snapshot.knowledge_base.os_release = "RedHat Linux"

    summary = models_clients.GetSummaryFromClientSnapshot(snapshot)
    self.assertEqual(summary.system_info.release, "RedHat Linux")

  def testGetSummaryOsVersionSnapshot(self):
    snapshot = objects_pb2.ClientSnapshot(
        client_id="C.0123456789012345",
        os_version="13.37",
    )
    snapshot.knowledge_base.os_release = "RedHat Linux"
    snapshot.knowledge_base.os_major_version = 4
    snapshot.knowledge_base.os_minor_version = 2

    summary = models_clients.GetSummaryFromClientSnapshot(snapshot)
    self.assertEqual(summary.system_info.version, "13.37")

  def testGetSummaryOsVersionKnowledgeBase(self):
    snapshot = objects_pb2.ClientSnapshot(client_id="C.0123456789012345")
    snapshot.knowledge_base.os_release = "RedHat Linux"
    snapshot.knowledge_base.os_major_version = 4
    snapshot.knowledge_base.os_minor_version = 2

    summary = models_clients.GetSummaryFromClientSnapshot(snapshot)
    self.assertEqual(summary.system_info.version, "4.2")


if __name__ == "__main__":
  absltest.main()
