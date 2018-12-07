#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import platform
import stat
import unittest


from future.utils import iteritems
from future.utils import iterkeys
from future.utils import string_types
import mock

from grr_response_client import vfs
from grr_response_core.lib import flags
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr.test_lib import client_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib


class WindowsActionTests(client_test_lib.OSSpecificClientTests):

  def setUp(self):
    super(WindowsActionTests, self).setUp()
    self.win32com = mock.MagicMock()
    self.win32com.client = mock.MagicMock()
    modules = {
        "_winreg":
            mock.MagicMock(),
        "pythoncom":
            mock.MagicMock(),
        "pywintypes":
            mock.MagicMock(),
        "win32api":
            mock.MagicMock(),
        # Necessary to stop the import of client_actions.standard re-populating
        # actions.ActionPlugin.classes
        ("grr_response_client.client_actions"
         ".standard"):
            mock.MagicMock(),
        "win32com":
            self.win32com,
        "win32com.client":
            self.win32com.client,
        "win32file":
            mock.MagicMock(),
        "win32service":
            mock.MagicMock(),
        "win32serviceutil":
            mock.MagicMock(),
        "winerror":
            mock.MagicMock(),
        "wmi":
            mock.MagicMock()
    }

    self.module_patcher = mock.patch.dict("sys.modules", modules)
    self.module_patcher.start()

    # pylint: disable= g-import-not-at-top
    from grr_response_client.client_actions.windows import windows
    # pylint: enable=g-import-not-at-top
    self.windows = windows

  def tearDown(self):
    super(WindowsActionTests, self).tearDown()
    self.module_patcher.stop()

  @unittest.skipIf(
      platform.system() == "Darwin",
      ("IPv6 address strings are cosmetically slightly different on OS X, "
       "and we only expect this parsing code to run on Linux or maybe Windows"))
  def testEnumerateInterfaces(self):
    # Stub out wmi.WMI().Win32_NetworkAdapterConfiguration()
    wmi_object = self.windows.wmi.WMI.return_value
    wmi_object.Win32_NetworkAdapterConfiguration.return_value = [
        client_test_lib.WMIWin32NetworkAdapterConfigurationMock()
    ]

    enumif = self.windows.EnumerateInterfaces()

    replies = []

    def Collect(reply):
      replies.append(reply)

    enumif.SendReply = Collect
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
    wmi_obj = self.windows.win32com.client.GetObject.return_value
    mock_query_result = mock.MagicMock()
    mock_query_result.Properties_ = []
    mock_config = client_test_lib.WMIWin32NetworkAdapterConfigurationMock
    wmi_properties = iteritems(mock_config.__dict__)
    for key, value in wmi_properties:
      keyval = mock.MagicMock()
      keyval.Name, keyval.Value = key, value
      mock_query_result.Properties_.append(keyval)

    wmi_obj.ExecQuery.return_value = [mock_query_result]

    result_list = list(self.windows.RunWMIQuery("select blah"))
    self.assertLen(result_list, 1)

    result = result_list.pop()
    self.assertIsInstance(result, rdf_protodict.Dict)
    nest = result["NestingTest"]

    self.assertEqual(nest["one"]["two"], [3, 4])
    self.assertTrue("Unsupported type" in nest["one"]["broken"])
    self.assertIsInstance(nest["one"]["three"], rdf_protodict.Dict)

    self.assertEqual(nest["four"], [])
    self.assertEqual(nest["five"], "astring")
    self.assertEqual(nest["six"], [None, None, ""])
    self.assertEqual(nest["seven"], None)
    self.assertCountEqual(iterkeys(nest["rdfvalue"]), ["a"])

    self.assertEqual(result["GatewayCostMetric"], [0, 256])
    self.assertIsInstance(result["OpaqueObject"], string_types)
    self.assertIn("Unsupported type", result["OpaqueObject"])


class RegistryVFSTests(client_test_lib.EmptyActionTest):

  def setUp(self):
    super(RegistryVFSTests, self).setUp()
    self.registry_stubber = vfs_test_lib.RegistryVFSStubber()
    self.registry_stubber.Start()

  def tearDown(self):
    super(RegistryVFSTests, self).tearDown()
    self.registry_stubber.Stop()

  def testRegistryListing(self):

    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.REGISTRY,
        path=("/HKEY_USERS/S-1-5-20/Software/Microsoft"
              "/Windows/CurrentVersion/Run"))

    expected_names = {"MctAdmin": stat.S_IFDIR, "Sidebar": stat.S_IFDIR}
    expected_data = [
        u"%ProgramFiles%\\Windows Sidebar\\Sidebar.exe /autoRun",
        u"%TEMP%\\Sidebar.exe"
    ]

    for f in vfs.VFSOpen(pathspec).ListFiles():
      base, name = os.path.split(f.pathspec.CollapsePath())
      self.assertEqual(base, pathspec.CollapsePath())
      self.assertIn(name, expected_names)
      self.assertIn(f.registry_data.GetValue(), expected_data)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
