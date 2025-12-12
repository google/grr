#!/usr/bin/env python
import io
import ipaddress
import time
from unittest import mock

from absl.testing import absltest
import humanize
from IPython.lib import pretty

import grr_colab
from grr_colab import representer
from grr_response_proto import jobs_pb2
from grr_response_proto import sysinfo_pb2
from grr_response_proto.api import client_pb2


class StatEntryPrettyTest(absltest.TestCase):

  def testFile(self):
    entry = jobs_pb2.StatEntry()
    entry.pathspec.path = '/foo/bar'
    entry.st_size = 42
    entry.st_mode = 33188

    out = io.StringIO()
    pp = pretty.PrettyPrinter(out)
    representer.stat_entry_pretty(entry, pp, cycle=False)

    expected = '📄 bar (-rw-r--r-- /foo/bar, {})'
    expected = expected.format(humanize.naturalsize(42))

    self.assertEqual(out.getvalue(), expected)

  def testDirectory(self):
    entry = jobs_pb2.StatEntry()
    entry.pathspec.path = '/foo/bar'
    entry.st_size = 42
    entry.st_mode = 16877

    out = io.StringIO()
    pp = pretty.PrettyPrinter(out)
    representer.stat_entry_pretty(entry, pp, cycle=False)

    expected = '📂 bar (drwxr-xr-x /foo/bar, {})'
    expected = expected.format(humanize.naturalsize(42))

    self.assertEqual(out.getvalue(), expected)


class BufferReferencePrettyTest(absltest.TestCase):

  def testAsciiData(self):
    ref = jobs_pb2.BufferReference()
    ref.pathspec.path = '/foo/bar'
    ref.offset = 42
    ref.length = 6
    ref.data = b'foobar'

    out = io.StringIO()
    pp = pretty.PrettyPrinter(out)
    representer.buffer_reference_pretty(ref, pp, cycle=False)

    expected = '/foo/bar:42-48: b\'foobar\''
    self.assertEqual(out.getvalue(), expected)

  def testNonAsciiData(self):
    ref = jobs_pb2.BufferReference()
    ref.pathspec.path = '/foo/bar'
    ref.offset = 42
    ref.length = 3
    ref.data = b'\xff\xaa\xff'

    out = io.StringIO()
    pp = pretty.PrettyPrinter(out)
    representer.buffer_reference_pretty(ref, pp, cycle=False)

    expected = '/foo/bar:42-45: b\'\\xff\\xaa\\xff\''
    self.assertEqual(out.getvalue(), expected)


class NetworkAddressPrettyTest(absltest.TestCase):

  def testIPv4(self):
    ipv4 = ipaddress.IPv4Address('42.0.255.32')
    address = jobs_pb2.NetworkAddress()
    address.address_type = jobs_pb2.NetworkAddress.INET
    address.packed_bytes = ipv4.packed

    out = io.StringIO()
    pp = pretty.PrettyPrinter(out)
    representer.network_address_pretty(address, pp, cycle=False)

    expected = 'inet 42.0.255.32'
    self.assertEqual(out.getvalue(), expected)

  def testIPv6(self):
    ipv6 = ipaddress.IPv6Address('2001:db8::1000')
    address = jobs_pb2.NetworkAddress()
    address.address_type = jobs_pb2.NetworkAddress.INET6
    address.packed_bytes = ipv6.packed

    out = io.StringIO()
    pp = pretty.PrettyPrinter(out)
    representer.network_address_pretty(address, pp, cycle=False)

    expected = 'inet6 2001:db8::1000'
    self.assertEqual(out.getvalue(), expected)


class InterfacePrettyTest(absltest.TestCase):

  def testNoAddresses(self):
    iface = jobs_pb2.Interface()
    iface.mac_address = b'\xaa\x12\x42\xff\xa5\xd0'
    iface.ifname = 'foo'

    out = io.StringIO()
    pp = pretty.PrettyPrinter(out)
    representer.interface_pretty(iface, pp, cycle=False)

    expected = """\
foo (MAC: aa:12:42:ff:a5:d0):
"""
    self.assertEqual(out.getvalue(), expected)

  def testSingleAddress(self):
    ipv4 = ipaddress.IPv4Address('42.0.255.32')
    address = jobs_pb2.NetworkAddress()
    address.address_type = jobs_pb2.NetworkAddress.INET
    address.packed_bytes = ipv4.packed

    iface = jobs_pb2.Interface()
    iface.mac_address = b'\xaa\x12\x42\xff\xa5\xd0'
    iface.ifname = 'foo'
    iface.addresses.extend([address])

    out = io.StringIO()
    pp = pretty.PrettyPrinter(out)
    representer.interface_pretty(iface, pp, cycle=False)

    expected = """\
foo (MAC: aa:12:42:ff:a5:d0):
    inet 42.0.255.32
"""
    self.assertEqual(out.getvalue(), expected)

  def testMultipleAddresses(self):
    ipv4 = ipaddress.IPv4Address('42.0.255.32')
    address1 = jobs_pb2.NetworkAddress()
    address1.address_type = jobs_pb2.NetworkAddress.INET
    address1.packed_bytes = ipv4.packed

    ipv6 = ipaddress.IPv6Address('2001:db8::1000')
    address2 = jobs_pb2.NetworkAddress()
    address2.address_type = jobs_pb2.NetworkAddress.INET6
    address2.packed_bytes = ipv6.packed

    iface = jobs_pb2.Interface()
    iface.mac_address = b'\xaa\x12\x42\xff\xa5\xd0'
    iface.ifname = 'foo'
    iface.addresses.extend([address1, address2])

    out = io.StringIO()
    pp = pretty.PrettyPrinter(out)
    representer.interface_pretty(iface, pp, cycle=False)

    expected = """\
foo (MAC: aa:12:42:ff:a5:d0):
    inet 42.0.255.32
    inet6 2001:db8::1000
"""
    self.assertEqual(out.getvalue(), expected)


class ProcessPrettyTest(absltest.TestCase):

  def testFitWidth(self):
    process = sysinfo_pb2.Process()
    process.pid = 1
    process.username = 'admin'
    process.nice = 10
    process.VMS_size = 42
    process.RSS_size = 43
    process.status = 'sleeping'
    process.memory_percent = 2.5
    process.exe = '/foo/bar'

    out = io.StringIO()
    pp = pretty.PrettyPrinter(out, max_width=55)
    representer.process_pretty(process, pp, cycle=False)

    expected = '     1 admin      10   42B   43B S  2.5 /foo/bar'

    self.assertEqual(out.getvalue(), expected)

  def testExceedMaxWidth(self):
    process = sysinfo_pb2.Process()
    process.pid = 1
    process.username = 'longusername'
    process.nice = 10
    process.VMS_size = 42
    process.RSS_size = 43
    process.status = 'sleeping'
    process.memory_percent = 2.5
    process.exe = '/foo/bar/baz'

    out = io.StringIO()
    pp = pretty.PrettyPrinter(out, max_width=55)
    representer.process_pretty(process, pp, cycle=False)

    expected = '     1 longusern  10   42B   43B S  2.5 /foo/bar/baz'

    self.assertEqual(out.getvalue(), expected)


class StatEntryListTest(absltest.TestCase):

  def testEmptyResults(self):
    sts = representer.StatEntryList([])

    out = io.StringIO()
    sts._repr_pretty_(pretty.PrettyPrinter(out), cycle=False)
    self.assertEqual(out.getvalue(), 'No results.')

  def testCycle(self):
    sts = representer.StatEntryList([])

    out = io.StringIO()
    with self.assertRaises(AssertionError):
      sts._repr_pretty_(pretty.PrettyPrinter(out), cycle=True)

  def testSingleDirectory(self):
    entry = jobs_pb2.StatEntry()
    entry.pathspec.path = '/foo/bar'
    entry.st_size = 42
    entry.st_mode = 16877

    sts = representer.StatEntryList([entry])

    out = io.StringIO()
    sts._repr_pretty_(pretty.PrettyPrinter(out), cycle=False)

    expected = """
/foo
    📂 bar (drwxr-xr-x /foo/bar, {})
"""
    expected = expected.format(humanize.naturalsize(42))

    self.assertEqual(out.getvalue(), expected)

  def testSingleFile(self):
    entry = jobs_pb2.StatEntry()
    entry.pathspec.path = '/foo/bar'
    entry.st_size = 42
    entry.st_mode = 33188

    sts = representer.StatEntryList([entry])

    out = io.StringIO()
    sts._repr_pretty_(pretty.PrettyPrinter(out), cycle=False)

    expected = """
/foo
    📄 bar (-rw-r--r-- /foo/bar, {})
"""
    expected = expected.format(humanize.naturalsize(42))

    self.assertEqual(out.getvalue(), expected)

  def testCommonImplicitRoot(self):
    entry1 = jobs_pb2.StatEntry()
    entry1.pathspec.path = '/foo/bar'
    entry1.st_size = 42
    entry1.st_mode = 33188

    entry2 = jobs_pb2.StatEntry()
    entry2.pathspec.path = '/foo/baz'
    entry2.st_size = 43
    entry2.st_mode = 16877

    sts = representer.StatEntryList([entry1, entry2])

    out = io.StringIO()
    sts._repr_pretty_(pretty.PrettyPrinter(out), cycle=False)

    expected = """
/foo
    📄 bar (-rw-r--r-- /foo/bar, {})
    📂 baz (drwxr-xr-x /foo/baz, {})
"""
    expected = expected.format(
        humanize.naturalsize(42), humanize.naturalsize(43))

    self.assertEqual(out.getvalue(), expected)

  def testDifferentRoots(self):
    entry1 = jobs_pb2.StatEntry()
    entry1.pathspec.path = '/foo1/bar'
    entry1.st_size = 42
    entry1.st_mode = 33188

    entry2 = jobs_pb2.StatEntry()
    entry2.pathspec.path = '/foo2/baz'
    entry2.st_size = 43
    entry2.st_mode = 16877

    sts = representer.StatEntryList([entry1, entry2])

    out = io.StringIO()
    sts._repr_pretty_(pretty.PrettyPrinter(out), cycle=False)

    expected = """
/foo1
    📄 bar (-rw-r--r-- /foo1/bar, {})
/foo2
    📂 baz (drwxr-xr-x /foo2/baz, {})
"""
    expected = expected.format(
        humanize.naturalsize(42), humanize.naturalsize(43))

    self.assertEqual(out.getvalue(), expected)

  def testNestedDirectories(self):
    entry1 = jobs_pb2.StatEntry()
    entry1.pathspec.path = '/foo/bar'
    entry1.st_size = 42
    entry1.st_mode = 16877

    entry2 = jobs_pb2.StatEntry()
    entry2.pathspec.path = '/foo/bar/baz'
    entry2.st_size = 42
    entry2.st_mode = 16877

    entry3 = jobs_pb2.StatEntry()
    entry3.pathspec.path = '/foo/bar/baz/quux'
    entry3.st_size = 42
    entry3.st_mode = 16877

    sts = representer.StatEntryList([entry1, entry2, entry3])

    out = io.StringIO()
    sts._repr_pretty_(pretty.PrettyPrinter(out), cycle=False)

    expected = """
/foo
    📂 bar (drwxr-xr-x /foo/bar, {size})
        📂 baz (drwxr-xr-x /foo/bar/baz, {size})
            📂 quux (drwxr-xr-x /foo/bar/baz/quux, {size})
"""
    expected = expected.format(size=humanize.naturalsize(42))

    self.assertEqual(out.getvalue(), expected)

  def testCommonExplicitRoot(self):
    entry1 = jobs_pb2.StatEntry()
    entry1.pathspec.path = '/foo/bar'
    entry1.st_size = 42
    entry1.st_mode = 16877

    entry2 = jobs_pb2.StatEntry()
    entry2.pathspec.path = '/foo/bar/baz'
    entry2.st_size = 42
    entry2.st_mode = 33188

    entry3 = jobs_pb2.StatEntry()
    entry3.pathspec.path = '/foo/bar/quux'
    entry3.st_size = 42
    entry3.st_mode = 33188

    sts = representer.StatEntryList([entry1, entry2, entry3])

    out = io.StringIO()
    sts._repr_pretty_(pretty.PrettyPrinter(out), cycle=False)

    expected = """
/foo
    📂 bar (drwxr-xr-x /foo/bar, {size})
        📄 baz (-rw-r--r-- /foo/bar/baz, {size})
        📄 quux (-rw-r--r-- /foo/bar/quux, {size})
"""
    expected = expected.format(size=humanize.naturalsize(42))

    self.assertEqual(out.getvalue(), expected)

  def testSlice(self):
    entry1 = jobs_pb2.StatEntry()
    entry2 = jobs_pb2.StatEntry()

    sts = representer.StatEntryList([entry1, entry2])
    sts = sts[:1]

    self.assertLen(sts, 1)
    self.assertIsInstance(sts, representer.StatEntryList)


class BufferReferenceListTest(absltest.TestCase):

  def testEmptyResults(self):
    brs = representer.BufferReferenceList([])

    out = io.StringIO()
    brs._repr_pretty_(pretty.PrettyPrinter(out), cycle=False)
    self.assertEqual(out.getvalue(), 'No results.')

  def testCycle(self):
    brs = representer.BufferReferenceList([])

    out = io.StringIO()
    with self.assertRaises(AssertionError):
      brs._repr_pretty_(pretty.PrettyPrinter(out), cycle=True)

  def testMultipleItems(self):
    ref1 = jobs_pb2.BufferReference()
    ref1.pathspec.path = '/foo/bar'
    ref1.offset = 42
    ref1.length = 6
    ref1.data = b'foobar'

    ref2 = jobs_pb2.BufferReference()
    ref2.pathspec.path = '/quux'
    ref2.offset = 42
    ref2.length = 4
    ref2.data = b'quux'

    brs = representer.BufferReferenceList([ref1, ref2])

    out = io.StringIO()
    brs._repr_pretty_(pretty.PrettyPrinter(out), cycle=False)

    expected = """
/foo/bar:42-48: b\'foobar\'
/quux:42-46: b\'quux\'
"""
    self.assertEqual(out.getvalue(), expected)

  def testSlice(self):
    ref1 = jobs_pb2.BufferReference()
    ref2 = jobs_pb2.BufferReference()

    brs = representer.BufferReferenceList([ref1, ref2])
    self.assertIsInstance(brs[:1], representer.BufferReferenceList)


class InterfaceListTest(absltest.TestCase):

  def testEmptyResults(self):
    ifaces = representer.InterfaceList([])

    out = io.StringIO()
    ifaces._repr_pretty_(pretty.PrettyPrinter(out), cycle=False)
    self.assertEqual(out.getvalue(), 'No results.')

  def testCycle(self):
    ifaces = representer.InterfaceList([])

    out = io.StringIO()
    with self.assertRaises(AssertionError):
      ifaces._repr_pretty_(pretty.PrettyPrinter(out), cycle=True)

  def testMultipleItems(self):
    ipv4 = ipaddress.IPv4Address('42.0.255.32')
    address1 = jobs_pb2.NetworkAddress()
    address1.address_type = jobs_pb2.NetworkAddress.INET
    address1.packed_bytes = ipv4.packed

    ipv6 = ipaddress.IPv6Address('2001:db8::1000')
    address2 = jobs_pb2.NetworkAddress()
    address2.address_type = jobs_pb2.NetworkAddress.INET6
    address2.packed_bytes = ipv6.packed

    iface1 = jobs_pb2.Interface()
    iface1.mac_address = b'\xaa\x12\x42\xff\xa5\xd0'
    iface1.ifname = 'foo'
    iface1.addresses.extend([address1])

    iface2 = jobs_pb2.Interface()
    iface2.mac_address = b'\xaa\x12\x42\xff\xa5\xd1'
    iface2.ifname = 'bar'
    iface2.addresses.extend([address2])

    ifaces = representer.InterfaceList([iface1, iface2])

    out = io.StringIO()
    ifaces._repr_pretty_(pretty.PrettyPrinter(out), cycle=False)

    expected = """
foo (MAC: aa:12:42:ff:a5:d0):
    inet 42.0.255.32

bar (MAC: aa:12:42:ff:a5:d1):
    inet6 2001:db8::1000
"""
    self.assertEqual(out.getvalue(), expected)

  def testSlice(self):
    iface1 = jobs_pb2.Interface()
    iface2 = jobs_pb2.Interface()

    ifaces = representer.InterfaceList([iface1, iface2])
    self.assertIsInstance(ifaces[:1], representer.InterfaceList)


class ClientListTest(absltest.TestCase):

  class _MockClient(grr_colab.Client):

    class MockInnerClient(object):

      def __init__(self):
        self.data = client_pb2.ApiClient()

    def __init__(self, client_id='', hostname='', last_seen_at=0):
      self._snapshot = None
      self._client = ClientListTest._MockClient.MockInnerClient()
      self._client.data.client_id = client_id
      self._client.client_id = client_id
      self._client.data.knowledge_base.fqdn = hostname
      self._client.data.last_seen_at = last_seen_at

  def testEmptyResults(self):
    cs = representer.ClientList([])

    out = io.StringIO()
    cs._repr_pretty_(pretty.PrettyPrinter(out), cycle=False)
    self.assertEqual(out.getvalue(), 'No results.')

  def testCycle(self):
    cs = representer.ClientList([])

    out = io.StringIO()
    with self.assertRaises(AssertionError):
      cs._repr_pretty_(pretty.PrettyPrinter(out), cycle=True)

  def testMultipleItems(self):
    current_time_secs = 1560000000
    last_seen1 = (current_time_secs - 1) * (10**6)
    last_seen2 = (current_time_secs - 4 * 60 * 60 * 24) * (10**6)

    client1 = ClientListTest._MockClient('foo', 'host1', last_seen1)
    client2 = ClientListTest._MockClient('bar', 'host2', last_seen2)

    clients = representer.ClientList([client1, client2])
    out = io.StringIO()

    with mock.patch.object(time, 'time', return_value=current_time_secs):
      clients._repr_pretty_(pretty.PrettyPrinter(out), cycle=False)

    expected = """
🌕 foo @ host1 (1 seconds ago)
🌑 bar @ host2 (4 days ago)
"""
    self.assertEqual(out.getvalue(), expected)

  def testSlice(self):
    client1 = ClientListTest._MockClient()
    client2 = ClientListTest._MockClient()

    clients = representer.ClientList([client1, client2])
    self.assertIsInstance(clients[:1], representer.ClientList)


class ProcessListTest(absltest.TestCase):

  def testEmptyResults(self):
    ps = representer.ProcessList([])

    out = io.StringIO()
    ps._repr_pretty_(pretty.PrettyPrinter(out), cycle=False)
    self.assertEqual(out.getvalue(), 'No results.')

  def testCycle(self):
    ps = representer.ProcessList([])

    out = io.StringIO()
    with self.assertRaises(AssertionError):
      ps._repr_pretty_(pretty.PrettyPrinter(out), cycle=True)

  def testMultipleItems(self):
    process1 = sysinfo_pb2.Process()
    process1.pid = 1
    process1.username = 'admin'
    process1.nice = 10
    process1.VMS_size = 42
    process1.RSS_size = 43
    process1.status = 'sleeping'
    process1.memory_percent = 2.5
    process1.exe = '/foo/bar'

    process2 = sysinfo_pb2.Process()
    process2.pid = 2
    process2.username = 'admin'
    process2.VMS_size = 40
    process2.RSS_size = 41
    process2.status = 'zombie'
    process2.exe = '/foo/baz/quux'

    ps = representer.ProcessList([process1, process2])

    out = io.StringIO()
    ps._repr_pretty_(pretty.PrettyPrinter(out, max_width=55), cycle=False)

    expected = """
   PID USER       NI  VIRT   RES S MEM% Command
     1 admin      10   42B   43B S  2.5 /foo/bar
     2 admin       0   40B   41B Z  0.0 /foo/baz/quux
"""
    self.assertEqual(out.getvalue(), expected)

  def testSlice(self):
    process1 = sysinfo_pb2.Process()
    process2 = sysinfo_pb2.Process()

    ps = representer.ProcessList([process1, process2])
    self.assertIsInstance(ps[:1], representer.ProcessList)


if __name__ == '__main__':
  absltest.main()
