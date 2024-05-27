#!/usr/bin/env python
import ipaddress

from absl.testing import absltest

from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_proto import jobs_pb2
from grr_response_proto import knowledge_base_pb2
from grr_response_proto import objects_pb2
from grr_response_proto import sysinfo_pb2
from grr_response_proto.api import client_pb2
from grr_response_server.gui.api_plugins import client
from grr_response_server.gui.api_plugins import mig_client
from grr_response_server.models import clients
from grr_response_server.rdfvalues import mig_objects


class FleetspeakValidationInfoFromDictTest(absltest.TestCase):

  def testEmpty(self):
    result = clients.FleetspeakValidationInfoFromDict({})

    self.assertEmpty(result.tags)

  def testSingle(self):
    result = clients.FleetspeakValidationInfoFromDict({"foo": "bar"})

    self.assertLen(result.tags, 1)
    self.assertEqual(result.tags[0].key, "foo")
    self.assertEqual(result.tags[0].value, "bar")

  def testMultiple(self):
    result = clients.FleetspeakValidationInfoFromDict({
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

    result = clients.FleetspeakValidationInfoToDict(info)
    self.assertEmpty(result)

  def testSingle(self):
    info = jobs_pb2.FleetspeakValidationInfo()
    info.tags.add(key="foo", value="bar")

    result = clients.FleetspeakValidationInfoToDict(info)
    self.assertDictEqual(result, {"foo": "bar"})

  def testMultiple(self):
    info = jobs_pb2.FleetspeakValidationInfo()
    info.tags.add(key="1", value="foo")
    info.tags.add(key="2", value="bar")
    info.tags.add(key="3", value="quux")

    result = clients.FleetspeakValidationInfoToDict(info)
    self.assertDictEqual(result, {"1": "foo", "2": "bar", "3": "quux"})

  def testEmptyKey(self):
    info = jobs_pb2.FleetspeakValidationInfo()
    info.tags.add(key="", value="foo")

    with self.assertRaises(ValueError) as context:
      clients.FleetspeakValidationInfoToDict(info)

    self.assertEqual(str(context.exception), "Empty tag key")

  def testEmptyValue(self):
    info = jobs_pb2.FleetspeakValidationInfo()
    info.tags.add(key="foo", value="")

    with self.assertRaises(ValueError) as context:
      clients.FleetspeakValidationInfoToDict(info)

    self.assertEqual(str(context.exception), "Empty tag value for key 'foo'")

  def testDuplicateKey(self):
    info = jobs_pb2.FleetspeakValidationInfo()
    info.tags.add(key="foo", value="bar")
    info.tags.add(key="foo", value="baz")

    with self.assertRaises(ValueError) as context:
      clients.FleetspeakValidationInfoToDict(info)

    self.assertEqual(str(context.exception), "Duplicate tag key 'foo'")


class NetworkAddressFromPackedBytes(absltest.TestCase):

  def testInvalidLength(self):
    with self.assertRaises(ValueError):
      clients.NetworkAddressFromPackedBytes(b"0.1.2.3")

  def testIPv4(self):
    packed_bytes = ipaddress.IPv4Address("196.128.0.1").packed

    result = clients.NetworkAddressFromPackedBytes(packed_bytes)
    self.assertEqual(result.packed_bytes, packed_bytes)
    self.assertEqual(result.address_type, jobs_pb2.NetworkAddress.INET)

  def testIPv6(self):
    packed_bytes = ipaddress.IPv6Address("::1").packed

    result = clients.NetworkAddressFromPackedBytes(packed_bytes)
    self.assertEqual(result.packed_bytes, packed_bytes)
    self.assertEqual(result.address_type, jobs_pb2.NetworkAddress.INET6)


class NetworkAddressFromIPAddress(absltest.TestCase):

  def testIPv4(self):
    ip_address = ipaddress.IPv4Address("196.128.0.1")

    result = clients.NetworkAddressFromIPAddress(ip_address)
    self.assertEqual(result.packed_bytes, ip_address.packed)
    self.assertEqual(result.address_type, jobs_pb2.NetworkAddress.INET)

  def testIPv6(self):
    ip_address = ipaddress.IPv6Address("::1")

    result = clients.NetworkAddressFromIPAddress(ip_address)
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
        users=snapshot.knowledge_base.users,
    )
    got_api_client = clients.ApiClientFromClientSnapshot(snapshot)
    self.assertEqual(want_client, got_api_client)

  # TODO: Remove compatibility test once migration is complete
  # and we remove the RDFValue.
  def testEquivalentToRDFConstructor(self):
    in_proto = _GenerateClientSnapshot()
    got_proto = clients.ApiClientFromClientSnapshot(in_proto)

    in_rdf = mig_objects.ToRDFClientSnapshot(in_proto)

    # Make sure it builds an equivalent RDFValue to the following:
    want_rdf = client.ApiClient().InitFromClientObject(in_rdf)
    want_proto = mig_client.ToProtoApiClient(want_rdf)
    self.assertEqual(want_proto, got_proto)


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
        users=snapshot.knowledge_base.users,
    )

    got_api_client = clients.ApiClientFromClientFullInfo(
        "C.0000000000000000", client_info
    )

    self.assertEqual(got_api_client, want_client)

  # TODO: Remove compatibility test once migration is complete
  # and we remove the RDFValue.
  def testEquivalentToRDFConstructor_WithSnapshot(self):
    snapshot = _GenerateClientSnapshot()
    proto_input = objects_pb2.ClientFullInfo(last_snapshot=snapshot)

    got_proto = clients.ApiClientFromClientFullInfo(
        "C.0000000000000000", proto_input
    )

    rdf_input = mig_objects.ToRDFClientFullInfo(proto_input)

    # Make sure it builds an equivalent RDFValue to the following:
    want_rdf = client.ApiClient().InitFromClientInfo(
        "C.0000000000000000", rdf_input
    )
    want_proto = mig_client.ToProtoApiClient(want_rdf)
    self.assertEqual(want_proto, got_proto)

  def testWithSnapshot_BadId(self):
    snapshot = _GenerateClientSnapshot()
    client_info = objects_pb2.ClientFullInfo(last_snapshot=snapshot)

    with self.assertRaises(ValueError):
      clients.ApiClientFromClientFullInfo("C.1111111111111111", client_info)

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

    got_api_client = clients.ApiClientFromClientFullInfo(
        "C.0000000000000000", client_info
    )

    self.assertEqual(got_api_client, want_client)

  # TODO: Remove compatibility test once migration is complete
  # and we remove the RDFValue.
  def testEquivalentToRDFConstructor_WithoutSnapshot(self):
    proto_input = self._GenerateClientFullInfo(1, 2, 3)
    got_proto = clients.ApiClientFromClientFullInfo(
        "C.0000000000000000", proto_input
    )

    rdf_input = mig_objects.ToRDFClientFullInfo(proto_input)

    # Make sure it builds an equivalent RDFValue to the following:
    want_rdf = client.ApiClient().InitFromClientInfo(
        "C.0000000000000000", rdf_input
    )
    want_proto = mig_client.ToProtoApiClient(want_rdf)
    self.assertEqual(want_proto, got_proto)


if __name__ == "__main__":
  absltest.main()
