#!/usr/bin/env python
import os
import platform
import stat
import unittest

import mock

from grr_response_client import vfs
from grr.lib import flags
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import protodict as rdf_protodict
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
        # Requires mocking because exceptions.WindowsError does not exist
        "exceptions":
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

    self.assertEqual(len(replies), 1)
    interface = replies[0]
    self.assertEqual(len(interface.addresses), 4)
    addresses = [x.human_readable_address for x in interface.addresses]
    self.assertItemsEqual(addresses, [
        "192.168.1.20", "ffff::ffff:aaaa:1111:aaaa",
        "dddd:0:8888:6666:bbbb:aaaa:eeee:bbbb",
        "dddd:0:8888:6666:bbbb:aaaa:ffff:bbbb"
    ])

  def testRunWMI(self):
    wmi_obj = self.windows.win32com.client.GetObject.return_value
    mock_query_result = mock.MagicMock()
    mock_query_result.Properties_ = []
    mock_config = client_test_lib.WMIWin32NetworkAdapterConfigurationMock
    wmi_properties = mock_config.__dict__.iteritems()
    for key, value in wmi_properties:
      keyval = mock.MagicMock()
      keyval.Name, keyval.Value = key, value
      mock_query_result.Properties_.append(keyval)

    wmi_obj.ExecQuery.return_value = [mock_query_result]

    result_list = list(self.windows.RunWMIQuery("select blah"))
    self.assertEqual(len(result_list), 1)

    result = result_list.pop()
    self.assertTrue(isinstance(result, rdf_protodict.Dict))
    nest = result["NestingTest"]

    self.assertEqual(nest["one"]["two"], [3, 4])
    self.assertTrue("Unsupported type" in nest["one"]["broken"])
    self.assertTrue(isinstance(nest["one"]["three"], rdf_protodict.Dict))

    self.assertEqual(nest["four"], [])
    self.assertEqual(nest["five"], "astring")
    self.assertEqual(nest["six"], [None, None, ""])
    self.assertEqual(nest["seven"], None)
    self.assertItemsEqual(nest["rdfvalue"].keys(), ["a"])

    self.assertEqual(result["GatewayCostMetric"], [0, 256])
    self.assertTrue(isinstance(result["OpaqueObject"], basestring))
    self.assertTrue("Unsupported type" in result["OpaqueObject"])


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

  def testRecursiveRegistryListing(self):
    """Test our ability to walk over a registry tree."""

    pathspec = rdf_paths.PathSpec(pathtype=rdf_paths.PathSpec.PathType.REGISTRY)

    walk_tups_0 = list(vfs.VFSOpen(pathspec).RecursiveListNames())
    walk_tups_1 = list(vfs.VFSOpen(pathspec).RecursiveListNames(depth=1))
    walk_tups_2 = list(vfs.VFSOpen(pathspec).RecursiveListNames(depth=2))
    walk_tups_inf = list(
        vfs.VFSOpen(pathspec).RecursiveListNames(depth=float("inf")))

    self.assertEqual(walk_tups_0,
                     [(r"", [r"HKEY_LOCAL_MACHINE", r"HKEY_USERS"], [])])

    self.assertEqual(
        walk_tups_1,
        [(r"", [r"HKEY_LOCAL_MACHINE", r"HKEY_USERS"], []),
         (r"HKEY_LOCAL_MACHINE", [r"SOFTWARE", r"SYSTEM"], []),
         (r"HKEY_USERS",
          [r"S-1-5-20", r"S-1-5-21-702227000-2140022111-3110739999-1990"], [])])

    self.assertEqual(walk_tups_2, [
        (r"", [r"HKEY_LOCAL_MACHINE", r"HKEY_USERS"], []),
        (r"HKEY_LOCAL_MACHINE", [r"SOFTWARE", r"SYSTEM"], []),
        (r"HKEY_LOCAL_MACHINE\SOFTWARE", [r"ListingTest", r"Microsoft"], []),
        (r"HKEY_LOCAL_MACHINE\SYSTEM", [r"CurrentControlSet", r"Select"], []),
        (r"HKEY_USERS",
         [r"S-1-5-20", r"S-1-5-21-702227000-2140022111-3110739999-1990"], []),
        (r"HKEY_USERS\S-1-5-20", [r"Software"], []),
        (r"HKEY_USERS\S-1-5-21-702227000-2140022111-3110739999-1990",
         [r"Software"], []),
    ])

    self.assertEqual(walk_tups_inf, [
        (r"", [r"HKEY_LOCAL_MACHINE", r"HKEY_USERS"], []),
        (r"HKEY_LOCAL_MACHINE", [r"SOFTWARE", r"SYSTEM"], []),
        (r"HKEY_LOCAL_MACHINE\SOFTWARE", [r"ListingTest", r"Microsoft"], []),
        (r"HKEY_LOCAL_MACHINE\SOFTWARE\ListingTest", [],
         [r"Value1", r"Value2"]), (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft",
                                   [r"Windows", r"Windows NT"], []),
        (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows", [r"CurrentVersion"],
         []), (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion",
               [], [r"ProgramFilesDir", r"ProgramFilesDir (x86)"]),
        (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT",
         [r"CurrentVersion"], []),
        (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion",
         [r"ProfileList"], [r"SystemRoot"]),
        (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion"
         r"\ProfileList", [
             r"S-1-5-21-702227000-2140022111-3110739999-1990",
             r"S-1-5-21-702227068-2140022151-3110739409-1000"
         ], [r"ProfilesDirectory", r"ProgramData"]),
        (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion"
         r"\ProfileList\S-1-5-21-702227000-2140022111-3110739999-1990", [],
         [r"ProfileImagePath"]),
        (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion"
         r"\ProfileList\S-1-5-21-702227068-2140022151-3110739409-1000", [],
         [r"ProfileImagePath"]),
        (r"HKEY_LOCAL_MACHINE\SYSTEM", [r"CurrentControlSet", r"Select"], []),
        (r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet", [r"Control"], []),
        (r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control",
         [r"Nls", r"Session Manager", r"TimeZoneInformation"], []),
        (r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Nls",
         [r"CodePage"], []),
        (r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Nls\CodePage",
         [], [r"ACP"]),
        (r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager",
         [r"Environment"], []),
        (r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager"
         r"\Environment", [], [r"Path", r"TEMP", r"windir"]),
        (r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control"
         r"\TimeZoneInformation", [], [r"StandardName"]),
        (r"HKEY_LOCAL_MACHINE\SYSTEM\Select", [],
         [r"Current"]), (r"HKEY_USERS", [
             r"S-1-5-20", r"S-1-5-21-702227000-2140022111-3110739999-1990"
         ], []), (r"HKEY_USERS\S-1-5-20", [r"Software"],
                  []), (r"HKEY_USERS\S-1-5-20\Software", [r"Microsoft"], []),
        (r"HKEY_USERS\S-1-5-20\Software\Microsoft", [r"Windows"], []),
        (r"HKEY_USERS\S-1-5-20\Software\Microsoft\Windows", [r"CurrentVersion"],
         []), (r"HKEY_USERS\S-1-5-20\Software\Microsoft\Windows\CurrentVersion",
               [r"Run"], []),
        (r"HKEY_USERS\S-1-5-20\Software\Microsoft\Windows\CurrentVersion\Run",
         [], [r"MctAdmin", r"Sidebar"
             ]), (r"HKEY_USERS\S-1-5-21-702227000-2140022111-3110739999-1990",
                  [r"Software"], []),
        (r"HKEY_USERS\S-1-5-21-702227000-2140022111-3110739999-1990\Software",
         [r"Microsoft"], []),
        (r"HKEY_USERS\S-1-5-21-702227000-2140022111-3110739999-1990\Software"
         r"\Microsoft", [r"Windows"], []),
        (r"HKEY_USERS\S-1-5-21-702227000-2140022111-3110739999-1990\Software"
         r"\Microsoft\Windows", [r"CurrentVersion"], []),
        (r"HKEY_USERS\S-1-5-21-702227000-2140022111-3110739999-1990\Software"
         r"\Microsoft\Windows\CurrentVersion", [r"Run"], []),
        (r"HKEY_USERS\S-1-5-21-702227000-2140022111-3110739999-1990\Software"
         r"\Microsoft\Windows\CurrentVersion\Run", [], [r"NothingToSeeHere"])
    ])


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
