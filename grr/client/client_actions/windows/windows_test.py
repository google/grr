#!/usr/bin/env python
import os
import stat
import time

import mock

from grr.client import vfs
from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import client_fixture
from grr.lib import flags
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.aff4_objects import collects
# For RegistryFinder pylint: disable=unused-import
from grr.lib.flows.general import registry as _
# pylint: enable=unused-import
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import protodict as rdf_protodict


class WindowsActionTests(test_lib.OSSpecificClientTests):

  def setUp(self):
    super(WindowsActionTests, self).setUp()
    self.win32com = mock.MagicMock()
    self.win32com.client = mock.MagicMock()
    modules = {
        "_winreg": mock.MagicMock(),
        # Requires mocking because exceptions.WindowsError does not exist
        "exceptions": mock.MagicMock(),
        "pythoncom": mock.MagicMock(),
        "pywintypes": mock.MagicMock(),
        "win32api": mock.MagicMock(),
        # Necessary to stop the import of client_actions.standard re-populating
        # actions.ActionPlugin.classes
        ("grr.client.client_actions"
         ".standard"): mock.MagicMock(),
        "win32com": self.win32com,
        "win32com.client": self.win32com.client,
        "win32file": mock.MagicMock(),
        "win32service": mock.MagicMock(),
        "win32serviceutil": mock.MagicMock(),
        "winerror": mock.MagicMock(),
        "wmi": mock.MagicMock()
    }

    self.module_patcher = mock.patch.dict("sys.modules", modules)
    self.module_patcher.start()

    # pylint: disable= g-import-not-at-top
    from grr.client.client_actions.windows import windows
    # pylint: enable=g-import-not-at-top
    self.windows = windows

  def tearDown(self):
    super(WindowsActionTests, self).tearDown()
    self.module_patcher.stop()

  def testEnumerateInterfaces(self):
    # Stub out wmi.WMI().Win32_NetworkAdapterConfiguration(IPEnabled=1)
    wmi_object = self.windows.wmi.WMI.return_value
    wmi_object.Win32_NetworkAdapterConfiguration.return_value = [
        client_fixture.WMIWin32NetworkAdapterConfigurationMock()
    ]

    enumif = self.windows.EnumerateInterfaces()
    interface_dict_list = list(enumif.RunNetAdapterWMIQuery())

    self.assertEqual(len(interface_dict_list), 1)
    interface = interface_dict_list[0]
    self.assertEqual(len(interface["addresses"]), 4)
    addresses = [x.human_readable_address for x in interface["addresses"]]
    self.assertItemsEqual(addresses, ["192.168.1.20",
                                      "ffff::ffff:aaaa:1111:aaaa",
                                      "dddd:0:8888:6666:bbbb:aaaa:eeee:bbbb",
                                      "dddd:0:8888:6666:bbbb:aaaa:ffff:bbbb"])

  def testRunWMI(self):
    wmi_obj = self.windows.win32com.client.GetObject.return_value
    mock_query_result = mock.MagicMock()
    mock_query_result.Properties_ = []
    mock_config = client_fixture.WMIWin32NetworkAdapterConfigurationMock
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


class FakeKeyHandle(object):

  def __init__(self, value):
    self.value = value.replace("\\", "/")

  def __enter__(self):
    return self

  def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
    return False


class RegistryFake(test_lib.FakeRegistryVFSHandler):

  def __init__(self, **kwargs):
    self.PopulateCache()
    super(RegistryFake, self).__init__(**kwargs)

  def OpenKey(self, key, sub_key):
    res = "%s/%s" % (key.value, sub_key.replace("\\", "/"))
    res = res.lower().rstrip("/")
    if not res.startswith("/"):
      res = "/" + res
    if res in self.cache[self.prefix]:
      return FakeKeyHandle(res)
    raise IOError()

  def QueryValueEx(self, key, value_name):
    full_key = os.path.join(key.value, value_name).rstrip("/")
    try:
      stat_entry = self.cache[self.prefix][full_key][1]
      data = stat_entry.registry_data.GetValue()
      if data:
        return data, str
    except KeyError:
      pass

    raise IOError()

  def QueryInfoKey(self, key):
    modification_time = 10000000 * (11644473600 + time.time())
    return len(self._GetKeys(key)), len(self._GetValues(key)), modification_time

  def EnumKey(self, key, index):
    try:
      return self._GetKeys(key)[index]
    except IndexError:
      raise IOError()

  def _GetKeys(self, key):
    res = []
    for path in self.cache[self.prefix]:
      if os.path.dirname(path) == key.value:
        sub_type, stat_entry = self.cache[self.prefix][path]
        if sub_type.__name__ == "VFSDirectory":
          res.append(os.path.basename(stat_entry.pathspec.path))
    return sorted(res)

  def EnumValue(self, key, index):
    try:
      subkey = self._GetValues(key)[index]
      value, value_type = self.QueryValueEx(key, subkey)
      return subkey, value, value_type
    except IndexError:
      raise IOError()

  def _GetValues(self, key):
    res = []
    for path in self.cache[self.prefix]:
      if os.path.dirname(path) == key.value:
        sub_type, stat_entry = self.cache[self.prefix][path]
        if sub_type.__name__ == "VFSFile":
          res.append(os.path.basename(stat_entry.pathspec.path))
    return sorted(res)


class RegistryVFSTests(test_lib.EmptyActionTest):

  def setUp(self):
    super(RegistryVFSTests, self).setUp()
    modules = {
        "_winreg": mock.MagicMock(),
        "ctypes": mock.MagicMock(),
        "ctypes.wintypes": mock.MagicMock(),
        # Requires mocking because exceptions.WindowsError does not exist
        "exceptions": mock.MagicMock(),
    }

    self.module_patcher = mock.patch.dict("sys.modules", modules)
    self.module_patcher.start()

    # pylint: disable= g-import-not-at-top
    from grr.client.vfs_handlers import registry
    import exceptions
    import _winreg
    # pylint: enable=g-import-not-at-top

    fixture = RegistryFake()

    self.stubber = utils.MultiStubber(
        (registry, "KeyHandle", FakeKeyHandle),
        (registry, "OpenKey", fixture.OpenKey),
        (registry, "QueryValueEx", fixture.QueryValueEx),
        (registry, "QueryInfoKey", fixture.QueryInfoKey),
        (registry, "EnumValue", fixture.EnumValue),
        (registry, "EnumKey", fixture.EnumKey))
    self.stubber.Start()

    # Add the Registry handler to the vfs.
    vfs.VFSInit().Run()
    _winreg.HKEY_USERS = "HKEY_USERS"
    _winreg.HKEY_LOCAL_MACHINE = "HKEY_LOCAL_MACHINE"
    exceptions.WindowsError = IOError

  def tearDown(self):
    super(RegistryVFSTests, self).tearDown()
    self.module_patcher.stop()
    self.stubber.Stop()

  def testRegistryListing(self):

    pathspec = rdf_paths.PathSpec(pathtype=rdf_paths.PathSpec.PathType.REGISTRY,
                                  path=(
                                      "/HKEY_USERS/S-1-5-20/Software/Microsoft"
                                      "/Windows/CurrentVersion/Run"))

    expected_names = {"MctAdmin": stat.S_IFDIR, "Sidebar": stat.S_IFDIR}
    expected_data = [u"%ProgramFiles%\\Windows Sidebar\\Sidebar.exe /autoRun",
                     u"%TEMP%\\Sidebar.exe"]

    for f in vfs.VFSOpen(pathspec).ListFiles():
      base, name = os.path.split(f.pathspec.CollapsePath())
      self.assertEqual(base, pathspec.CollapsePath())
      self.assertIn(name, expected_names)
      self.assertIn(f.registry_data.GetValue(), expected_data)

  def _RunRegistryFinder(self, paths=None):
    client_mock = action_mocks.ActionMock("Find", "TransferBuffer",
                                          "HashBuffer", "FingerprintFile",
                                          "FingerprintFile", "Grep", "StatFile")

    output_path = "analysis/file_finder"
    client_id = self.SetupClients(1)[0]

    aff4.FACTORY.Delete(client_id.Add(output_path), token=self.token)

    for _ in test_lib.TestFlowHelper("RegistryFinder",
                                     client_mock,
                                     client_id=client_id,
                                     keys_paths=paths,
                                     conditions=[],
                                     token=self.token,
                                     output=output_path):
      pass

    try:
      return list(aff4.FACTORY.Open(
          client_id.Add(output_path),
          aff4_type=collects.RDFValueCollection,
          token=self.token))
    except aff4.InstantiationError:
      return []

  def testRegistryFinder(self):
    # Listing inside a key gives the values.
    results = self._RunRegistryFinder(
        ["HKEY_LOCAL_MACHINE/SOFTWARE/ListingTest/*"])
    self.assertEqual(len(results), 2)
    self.assertEqual(
        sorted([x.stat_entry.registry_data.GetValue() for x in results]),
        ["Value1", "Value2"])

    # This is a key so we should get back the default value.
    results = self._RunRegistryFinder(
        ["HKEY_LOCAL_MACHINE/SOFTWARE/ListingTest"])

    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].stat_entry.registry_data.GetValue(),
                     "DefaultValue")

    # The same should work using a wildcard.
    results = self._RunRegistryFinder(["HKEY_LOCAL_MACHINE/SOFTWARE/*"])

    self.assertTrue(results)
    paths = [x.stat_entry.pathspec.path for x in results]
    expected_path = u"/HKEY_LOCAL_MACHINE/SOFTWARE/ListingTest"
    self.assertIn(expected_path, paths)
    idx = paths.index(expected_path)
    self.assertEqual(results[idx].stat_entry.registry_data.GetValue(),
                     "DefaultValue")

  def testRecursiveRegistryListing(self):
    """Test our ability to walk over a registry tree."""

    pathspec = rdf_paths.PathSpec(pathtype=rdf_paths.PathSpec.PathType.REGISTRY)

    walk_tups_0 = list(vfs.VFSOpen(pathspec).RecursiveListNames())
    self.assertEqual(walk_tups_0,
                     [(r"", [r"HKEY_LOCAL_MACHINE", r"HKEY_USERS"], [])])

    walk_tups_1 = list(vfs.VFSOpen(pathspec).RecursiveListNames(depth=1))
    self.assertEqual(walk_tups_1,
                     [(r"", [r"HKEY_LOCAL_MACHINE", r"HKEY_USERS"], []),
                      (r"HKEY_LOCAL_MACHINE", [r"SOFTWARE", r"SYSTEM"], []),
                      (r"HKEY_USERS",
                       [r"S-1-5-20",
                        r"S-1-5-21-2911950750-476812067-1487428992-1001",
                        r"S-1-5-21-702227000-2140022111-3110739999-1990"], [])])

    walk_tups_inf = list(vfs.VFSOpen(pathspec).RecursiveListNames(depth=float(
        "inf")))
    self.assertEqual(
        walk_tups_inf,
        [(r"", [r"HKEY_LOCAL_MACHINE", r"HKEY_USERS"], []),
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
          r"\ProfileList", [r"S-1-5-21-702227000-2140022111-3110739999-1990",
                            r"S-1-5-21-702227068-2140022151-3110739409-1000"],
          [r"ProfilesDirectory", r"ProgramData"]),
         (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion"
          r"\ProfileList\S-1-5-21-702227000-2140022111-3110739999-1990", [],
          [r"ProfileImagePath"]),
         (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion"
          r"\ProfileList\S-1-5-21-702227068-2140022151-3110739409-1000", [],
          [r"ProfileImagePath"]), (r"HKEY_LOCAL_MACHINE\SYSTEM",
                                   [r"ControlSet001", r"Select"], []),
         (r"HKEY_LOCAL_MACHINE\SYSTEM\ControlSet001", [r"Control"], []),
         (r"HKEY_LOCAL_MACHINE\SYSTEM\ControlSet001\Control",
          [r"Nls", r"Session Manager", r"TimeZoneInformation"], []),
         (r"HKEY_LOCAL_MACHINE\SYSTEM\ControlSet001\Control\Nls", [r"CodePage"],
          []), (r"HKEY_LOCAL_MACHINE\SYSTEM\ControlSet001\Control\Nls\CodePage",
                [], [r"ACP"]),
         (r"HKEY_LOCAL_MACHINE\SYSTEM\ControlSet001\Control\Session Manager",
          [r"Environment"], []),
         (r"HKEY_LOCAL_MACHINE\SYSTEM\ControlSet001\Control\Session Manager"
          r"\Environment", [], [r"Path", r"TEMP", r"windir"]),
         (r"HKEY_LOCAL_MACHINE\SYSTEM\ControlSet001\Control"
          r"\TimeZoneInformation", [], [r"StandardName"]),
         (r"HKEY_LOCAL_MACHINE\SYSTEM\Select", [], [r"Current"]),
         (r"HKEY_USERS",
          [r"S-1-5-20", r"S-1-5-21-2911950750-476812067-1487428992-1001",
           r"S-1-5-21-702227000-2140022111-3110739999-1990"], []),
         (r"HKEY_USERS\S-1-5-20", [r"Software"], []),
         (r"HKEY_USERS\S-1-5-20\Software", [r"Microsoft"], []),
         (r"HKEY_USERS\S-1-5-20\Software\Microsoft", [r"Windows"], []),
         (r"HKEY_USERS\S-1-5-20\Software\Microsoft\Windows",
          [r"CurrentVersion"], []),
         (r"HKEY_USERS\S-1-5-20\Software\Microsoft\Windows\CurrentVersion",
          [r"Run"], []),
         (r"HKEY_USERS\S-1-5-20\Software\Microsoft\Windows\CurrentVersion\Run",
          [], [r"MctAdmin", r"Sidebar"]),
         (r"HKEY_USERS\S-1-5-21-2911950750-476812067-1487428992-1001",
          [r"Software"], []),
         (r"HKEY_USERS\S-1-5-21-2911950750-476812067-1487428992-1001\Software",
          [r"Microsoft"], []),
         (r"HKEY_USERS\S-1-5-21-2911950750-476812067-1487428992-1001\Software"
          r"\Microsoft", [r"Windows"], []),
         (r"HKEY_USERS\S-1-5-21-2911950750-476812067-1487428992-1001\Software"
          r"\Microsoft\Windows", [r"CurrentVersion"], []),
         (r"HKEY_USERS\S-1-5-21-2911950750-476812067-1487428992-1001\Software"
          r"\Microsoft\Windows\CurrentVersion", [r"Explorer"], []),
         (r"HKEY_USERS\S-1-5-21-2911950750-476812067-1487428992-1001\Software"
          r"\Microsoft\Windows\CurrentVersion\Explorer", [r"ComDlg32"], []),
         (r"HKEY_USERS\S-1-5-21-2911950750-476812067-1487428992-1001\Software"
          r"\Microsoft\Windows\CurrentVersion\Explorer\ComDlg32",
          [r"OpenSavePidlMRU"], []),
         (r"HKEY_USERS\S-1-5-21-2911950750-476812067-1487428992-1001\Software"
          r"\Microsoft\Windows\CurrentVersion\Explorer\ComDlg32"
          r"\OpenSavePidlMRU", [r"dd"], []),
         (r"HKEY_USERS\S-1-5-21-2911950750-476812067-1487428992-1001\Software"
          r"\Microsoft\Windows\CurrentVersion\Explorer\ComDlg32\OpenSavePidlMRU"
          r"\dd", [], [r"0"]),
         (r"HKEY_USERS\S-1-5-21-702227000-2140022111-3110739999-1990",
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
          r"\Microsoft\Windows\CurrentVersion\Run", [], [r"NothingToSeeHere"])])


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
