#!/usr/bin/env python
import os
import stat
import time

import mock

from grr.client import vfs
from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
from grr.test_data import client_fixture


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
        client_fixture.WMIWin32NetworkAdapterConfigurationMock()]

    enumif = self.windows.EnumerateInterfaces()
    interface_dict_list = list(enumif.RunNetAdapterWMIQuery())

    self.assertEqual(len(interface_dict_list), 1)
    interface = interface_dict_list[0]
    self.assertEqual(len(interface["addresses"]), 4)
    addresses = [x.human_readable_address for x in interface["addresses"]]
    self.assertItemsEqual(addresses,
                          ["192.168.1.20", "ffff::ffff:aaaa:1111:aaaa",
                           "dddd:0:8888:6666:bbbb:aaaa:eeee:bbbb",
                           "dddd:0:8888:6666:bbbb:aaaa:ffff:bbbb"])

  def testGetWMIAccount(self):
    enum_users = self.windows.EnumerateUsers()
    enum_users.special_folders = []
    result = enum_users.GetWMIAccount(
        client_fixture.USR_ACCOUNT_WMI,
        "S-1-5-21-3067777777-777777777-7777777774-500", "Users/Auser",
        client_fixture.USR_ACCOUNT_WMI_SIDS)

    self.assertEqual(result["username"], "Auser")
    self.assertEqual(result["domain"], "MYHOST-WIN")
    self.assertEqual(result["sid"],
                     "S-1-5-21-3067777777-777777777-7777777774-500")

    # SID not in known SIDs
    result = enum_users.GetWMIAccount(
        client_fixture.USR_ACCOUNT_WMI,
        "S-1-5-21-3067777777-777777777-7777777774-500", "Users/Auser",
        ["S-1-5-21"])
    self.assertEqual(result, None)

  def testRunWMI(self):
    wmi_obj = self.windows.win32com.client.GetObject.return_value
    mock_query_result = mock.MagicMock()
    mock_query_result.Properties_ = []
    wmi_properties = (client_fixture.WMIWin32NetworkAdapterConfigurationMock.
                      __dict__.iteritems())
    for key, value in wmi_properties:
      keyval = mock.MagicMock()
      keyval.Name, keyval.Value = key, value
      mock_query_result.Properties_.append(keyval)

    wmi_obj.ExecQuery.return_value = [mock_query_result]

    result_list = list(self.windows.RunWMIQuery("select blah"))
    self.assertEqual(len(result_list), 1)

    result = result_list.pop()
    self.assertTrue(isinstance(result, rdfvalue.Dict))
    nest = result["NestingTest"]

    self.assertEqual(nest["one"]["two"], [3, 4])
    self.assertTrue("Unsupported type" in nest["one"]["broken"])
    self.assertTrue(isinstance(nest["one"]["three"], rdfvalue.Dict))

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

  def __init__(self):
    self.PopulateCache()

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
        if  sub_type == "VFSDirectory":
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
        if  sub_type == "VFSFile":
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

    pathspec = rdfvalue.PathSpec(
        pathtype=rdfvalue.PathSpec.PathType.REGISTRY,
        path=("/HKEY_USERS/S-1-5-20/Software/Microsoft"
              "/Windows/CurrentVersion/Run"))

    expected_names = {"MctAdmin": stat.S_IFDIR,
                      "Sidebar": stat.S_IFDIR}
    expected_data = [u"%ProgramFiles%\\Windows Sidebar\\Sidebar.exe /autoRun",
                     u"%TEMP%\\Sidebar.exe"]

    for f in vfs.VFSOpen(pathspec).ListFiles():
      base, name = os.path.split(f.pathspec.CollapsePath())
      self.assertEqual(base, pathspec.CollapsePath())
      self.assertIn(name, expected_names)
      self.assertIn(f.registry_data.GetValue(), expected_data)

  def _RunRegistryFinder(self, paths=None):
    client_mock = action_mocks.ActionMock(
        "Find", "TransferBuffer", "HashBuffer", "FingerprintFile",
        "FingerprintFile", "Grep", "StatFile")

    output_path = "analysis/file_finder"

    client_id = rdfvalue.ClientURN("C.0000000000000001")

    aff4.FACTORY.Delete(client_id.Add(output_path),
                        token=self.token)

    for _ in test_lib.TestFlowHelper(
        "RegistryFinder", client_mock, client_id=client_id,
        keys_paths=paths,
        conditions=[], token=self.token, output=output_path):
      pass

    try:
      return list(aff4.FACTORY.Open(client_id.Add(output_path),
                                    aff4_type="RDFValueCollection",
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
    results = self._RunRegistryFinder(
        ["HKEY_LOCAL_MACHINE/SOFTWARE/*"])

    self.assertTrue(results)
    paths = [x.stat_entry.pathspec.path for x in results]
    expected_path = u"/HKEY_LOCAL_MACHINE/SOFTWARE/ListingTest"
    self.assertIn(expected_path, paths)
    idx = paths.index(expected_path)
    self.assertEqual(results[idx].stat_entry.registry_data.GetValue(),
                     "DefaultValue")


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
