#!/usr/bin/env python
import ipaddress

from absl.testing import absltest

from grr_response_proto import jobs_pb2
from grr_response_server.models import clients


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


if __name__ == "__main__":
  absltest.main()
