#!/usr/bin/env python
"""Tests for grr.parsers.windows_registry_parser."""


from absl import app

from grr_response_core.lib.parsers import windows_registry_parser
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class WindowsRegistryParserTest(flow_test_lib.FlowTestsBaseclass):

  def _MakeRegStat(self, path, value, registry_type):
    options = rdf_paths.PathSpec.Options.CASE_LITERAL
    pathspec = rdf_paths.PathSpec(
        path=path,
        path_options=options,
        pathtype=rdf_paths.PathSpec.PathType.REGISTRY)

    if registry_type == rdf_client_fs.StatEntry.RegistryType.REG_MULTI_SZ:
      reg_data = rdf_protodict.DataBlob(
          list=rdf_protodict.BlobArray(
              content=[rdf_protodict.DataBlob(string=value)]))
    else:
      reg_data = rdf_protodict.DataBlob().SetValue(value)

    return rdf_client_fs.StatEntry(
        pathspec=pathspec, registry_data=reg_data, registry_type=registry_type)

  def testGetServiceName(self):
    hklm = "HKEY_LOCAL_MACHINE/SYSTEM/CurrentControlSet/services"
    parser = windows_registry_parser.WinServicesParser()
    self.assertEqual(
        parser._GetServiceName("%s/SomeService/Start" % hklm), "SomeService")
    self.assertEqual(
        parser._GetServiceName("%s/SomeService/Parameters/ServiceDLL" % hklm),
        "SomeService")

  def testWinServicesParser(self):
    dword = rdf_client_fs.StatEntry.RegistryType.REG_DWORD_LITTLE_ENDIAN
    reg_str = rdf_client_fs.StatEntry.RegistryType.REG_SZ
    hklm = "HKEY_LOCAL_MACHINE/SYSTEM/CurrentControlSet/Services"
    hklm_set01 = "HKEY_LOCAL_MACHINE/SYSTEM/CurrentControlSet/services"
    service_keys = [
        ("%s/ACPI/Type" % hklm, 1, dword),
        ("%s/ACPI/Start" % hklm, 0, dword),
        # This one is broken, the parser should just ignore it.
        ("%s/notarealservice" % hklm, 3, dword),
        ("%s/ACPI/ErrorControl" % hklm, 3, dword),
        ("%s/ACPI/ImagePath" % hklm, "system32\\drivers\\ACPI.sys", reg_str),
        ("%s/ACPI/DisplayName" % hklm, "Microsoft ACPI Driver", reg_str),
        ("%s/ACPI/Group" % hklm, "Boot Bus Extender", reg_str),
        ("%s/ACPI/DriverPackageId" % hklm,
         "acpi.inf_amd64_neutral_99aaaaabcccccccc", reg_str),
        ("%s/AcpiPmi/Start" % hklm_set01, 3, dword),
        ("%s/AcpiPmi/DisplayName" % hklm_set01, "AcpiPmi",
         rdf_client_fs.StatEntry.RegistryType.REG_MULTI_SZ),
        (u"%s/中国日报/DisplayName" % hklm, u"中国日报", reg_str),
        (u"%s/中国日报/Parameters/ServiceDLL" % hklm, "blah.dll", reg_str)
    ]

    stats = [self._MakeRegStat(*x) for x in service_keys]
    parser = windows_registry_parser.WinServicesParser()
    results = parser.ParseResponses(None, stats)

    names = []
    for result in results:
      if result.display_name == u"中国日报":
        self.assertEqual(result.display_name, u"中国日报")
        self.assertEqual(result.service_dll, "blah.dll")
        names.append(result.display_name)
      elif str(result.registry_key).endswith("AcpiPmi"):
        self.assertEqual(result.name, "AcpiPmi")
        self.assertEqual(result.startup_type, 3)
        self.assertEqual(result.display_name, "['AcpiPmi']")
        self.assertEqual(result.registry_key, "%s/AcpiPmi" % hklm_set01)
        names.append(result.display_name)
      elif str(result.registry_key).endswith("ACPI"):
        self.assertEqual(result.name, "ACPI")
        self.assertEqual(result.service_type, 1)
        self.assertEqual(result.startup_type, 0)
        self.assertEqual(result.error_control, 3)
        self.assertEqual(result.image_path, "system32\\drivers\\ACPI.sys")
        self.assertEqual(result.display_name, "Microsoft ACPI Driver")
        self.assertEqual(result.group_name, "Boot Bus Extender")
        self.assertEqual(result.driver_package_id,
                         "acpi.inf_amd64_neutral_99aaaaabcccccccc")
        names.append(result.display_name)
    self.assertCountEqual(names,
                          [u"中国日报", "['AcpiPmi']", "Microsoft ACPI Driver"])

  def testWinUserSpecialDirs(self):
    reg_str = rdf_client_fs.StatEntry.RegistryType.REG_SZ
    hk_u = "registry/HKEY_USERS/S-1-1-1010-10101-1010"
    service_keys = [("%s/Environment/TEMP" % hk_u, r"temp\path", reg_str),
                    ("%s/Volatile Environment/USERDOMAIN" % hk_u, "GEVULOT",
                     reg_str)]

    stats = [self._MakeRegStat(*x) for x in service_keys]
    parser = windows_registry_parser.WinUserSpecialDirs()
    results = list(parser.ParseMultiple(stats, None))
    self.assertEqual(results[0].temp, r"temp\path")
    self.assertEqual(results[0].userdomain, "GEVULOT")

  def testWinSystemDriveParser(self):
    sysroot = (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT"
               r"\CurrentVersion\SystemRoot")
    stat = self._MakeRegStat(sysroot, r"C:\Windows", None)
    parser = windows_registry_parser.WinSystemDriveParser()
    self.assertEqual(r"C:", next(parser.Parse(stat, None)))

  def testWindowsRegistryInstalledSoftware(self):
    reg_str = rdf_client_fs.StatEntry.RegistryType.REG_SZ
    hklm = "HKEY_LOCAL_MACHINE"
    k = hklm + "/Software/Microsoft/Windows/CurrentVersion/Uninstall"
    service_keys = [
        # Valid.
        (k + "/Google Chrome/DisplayName", "Google Chrome", reg_str),
        (k + "/Google Chrome/DisplayVersion", "89.0.4389.82", reg_str),
        (k + "/Google Chrome/Publisher", "Google LLC", reg_str),
        # Invalid - Contains no data.
        (k + "/AddressBook/Default", "", reg_str),
        # Invalid - Missing DisplayName.
        (k + "/Foo/DisplayVersion", "1.2.3.4", reg_str),
        (k + "/Foo/Publisher", "Bar Inc", reg_str),
        # Valid.
        (k + "/Baz/DisplayName", "Baz", reg_str),
        (k + "/Baz/DisplayVersion", "2.3.4.5", reg_str),
        (k + "/Baz/Publisher", "Baz LLC", reg_str),
    ]

    stats = [self._MakeRegStat(*x) for x in service_keys]
    parser = windows_registry_parser.WindowsRegistryInstalledSoftwareParser()

    got = parser.ParseMultiple(stats, None)  # KnowledgeBase is not used.
    want = [
        rdf_client.SoftwarePackages(packages=[
            rdf_client.SoftwarePackage.Installed(
                name="Google Chrome",
                description="Google LLC",
                version="89.0.4389.82"),
            rdf_client.SoftwarePackage.Installed(
                name="Baz", description="Baz LLC", version="2.3.4.5"),
        ])
    ]

    self.assertEqual(want, got)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
