#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl.testing import absltest
from future.utils import iteritems
from future.utils import iterkeys
from future.utils import string_types
import mock

from grr_response_client.client_actions.windows import windows
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr.test_lib import client_test_lib


class WindowsActionTests(absltest.TestCase):

  def testEnumerateInterfaces(self):
    replies = []
    enumif = windows.EnumerateInterfaces()
    enumif.SendReply = replies.append
    enumif.Run(None)

    self.assertNotEmpty(replies)
    found_address = False
    for interface in replies:
      for address in interface.addresses:
        self.assertNotEmpty(address.human_readable_address)
        found_address = True
    if not found_address:
      self.fail("Not a single address found in EnumerateInterfaces {}".format(
          replies))

  def testEnumerateInterfacesMock(self):
    # Stub out wmi.WMI().Win32_NetworkAdapterConfiguration()
    wmi = mock.MagicMock()
    wmi.Win32_NetworkAdapterConfiguration.return_value = [
        client_test_lib.WMIWin32NetworkAdapterConfigurationMock()
    ]

    replies = []
    with mock.patch.object(windows.wmi, "WMI", return_value=wmi):
      enumif = windows.EnumerateInterfaces()
      enumif.SendReply = replies.append
      enumif.Run(None)

    self.assertLen(replies, 1)
    interface = replies[0]
    self.assertLen(interface.addresses, 4)
    addresses = [x.human_readable_address for x in interface.addresses]
    self.assertCountEqual(addresses, [
        "192.168.1.20", "ffff::ffff:aaaa:1111:aaaa",
        "dddd:0:8888:6666:bbbb:aaaa:eeee:bbbb",
        "dddd:0:8888:6666:bbbb:aaaa:ffff:bbbb"
    ])

  def testRunWMI(self):
    result_list = list(windows.RunWMIQuery("SELECT * FROM Win32_logicalDisk"))
    self.assertNotEmpty(result_list)

    drive = result_list[0]
    self.assertIsInstance(drive, rdf_protodict.Dict)
    self.assertNotEmpty(drive["DeviceID"])
    self.assertGreater(int(drive["Size"]), 0)

  def testRunWMIMocked(self):
    with mock.patch.object(windows, "win32com") as win32com:
      wmi_obj = win32com.client.GetObject.return_value
      mock_query_result = mock.MagicMock()
      mock_query_result.Properties_ = []
      mock_config = client_test_lib.WMIWin32NetworkAdapterConfigurationMock
      wmi_properties = iteritems(mock_config.__dict__)
      for key, value in wmi_properties:
        keyval = mock.MagicMock()
        keyval.Name, keyval.Value = key, value
        mock_query_result.Properties_.append(keyval)

      wmi_obj.ExecQuery.return_value = [mock_query_result]

      result_list = list(windows.RunWMIQuery("select blah"))
    self.assertLen(result_list, 1)

    result = result_list.pop()
    self.assertIsInstance(result, rdf_protodict.Dict)
    nest = result["NestingTest"]

    self.assertEqual(nest["one"]["two"], [3, 4])
    self.assertIn("Unsupported type", nest["one"]["broken"])
    self.assertIsInstance(nest["one"]["three"], rdf_protodict.Dict)

    self.assertEqual(nest["four"], [])
    self.assertEqual(nest["five"], "astring")
    self.assertEqual(nest["six"], [None, None, ""])
    self.assertEqual(nest["seven"], None)
    self.assertCountEqual(iterkeys(nest["rdfvalue"]), ["a"])

    self.assertEqual(result["GatewayCostMetric"], [0, 256])
    self.assertIsInstance(result["OpaqueObject"], string_types)
    self.assertIn("Unsupported type", result["OpaqueObject"])


if __name__ == "__main__":
  absltest.main()
