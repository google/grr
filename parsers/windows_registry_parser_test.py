#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests for grr.parsers.windows_registry_parser."""

from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.parsers import windows_registry_parser


class WindowsRegistryParserTest(test_lib.FlowTestsBaseclass):

  def _MakeRegStat(self, path, value, registry_type):
    options = rdfvalue.PathSpec.Options.CASE_LITERAL
    pathspec = rdfvalue.PathSpec(path=path,
                                 path_options=options,
                                 pathtype=rdfvalue.PathSpec.PathType.REGISTRY)

    if registry_type == rdfvalue.StatEntry.RegistryType.REG_MULTI_SZ:
      reg_data = rdfvalue.DataBlob(list=rdfvalue.BlobArray(
          content=rdfvalue.DataBlob(string=value)))
    else:
      reg_data = rdfvalue.DataBlob().SetValue(value)

    return rdfvalue.StatEntry(aff4path=self.client_id.Add("registry").Add(path),
                              pathspec=pathspec,
                              registry_data=reg_data,
                              registry_type=registry_type)

  def testGetServiceName(self):
    hklm = "HKEY_LOCAL_MACHINE/SYSTEM/CurrentControlSet/services"
    parser = windows_registry_parser.WinServicesParser()
    self.assertEqual(parser._GetServiceName(
        "%s/SomeService/Start" % hklm), "SomeService")
    self.assertEqual(parser._GetServiceName(
        "%s/SomeService/Parameters/ServiceDLL" % hklm), "SomeService")

  def testWinServicesParser(self):
    dword = rdfvalue.StatEntry.RegistryType.REG_DWORD_LITTLE_ENDIAN
    reg_str = rdfvalue.StatEntry.RegistryType.REG_SZ
    hklm = "HKEY_LOCAL_MACHINE/SYSTEM/CurrentControlSet/Services"
    hklm_set01 = "HKEY_LOCAL_MACHINE/SYSTEM/ControlSet001/services"
    service_keys = [
        ("%s/ACPI/Type" % hklm, 1, dword),
        ("%s/ACPI/Start" % hklm, 0, dword),
        ("%s/ACPI/ErrorControl" % hklm, 3, dword),
        ("%s/ACPI/ImagePath" % hklm, "system32\\drivers\\ACPI.sys", reg_str),
        ("%s/ACPI/DisplayName" % hklm, "Microsoft ACPI Driver", reg_str),
        ("%s/ACPI/Group" % hklm, "Boot Bus Extender", reg_str),
        ("%s/ACPI/DriverPackageId" % hklm,
         "acpi.inf_amd64_neutral_99aaaaabcccccccc", reg_str),
        ("%s/AcpiPmi/Start" % hklm_set01, 3, dword),
        ("%s/AcpiPmi/DisplayName" % hklm_set01, "AcpiPmi",
         rdfvalue.StatEntry.RegistryType.REG_MULTI_SZ),
        (u"%s/中国日报/DisplayName" % hklm, u"中国日报", reg_str),
        (u"%s/中国日报/Parameters/ServiceDLL" % hklm, "blah.dll", reg_str)
        ]

    stats = [self._MakeRegStat(*x) for x in service_keys]
    parser = windows_registry_parser.WinServicesParser()
    results = parser.ParseMultiple(stats, None)

    non_ascii = results.next()
    self.assertEqual(non_ascii.display_name, u"中国日报")
    self.assertEqual(non_ascii.service_dll, "blah.dll")

    acpipmi = results.next()
    self.assertEqual(acpipmi.name, "AcpiPmi")
    self.assertEqual(acpipmi.startup_type, 3)
    self.assertEqual(acpipmi.display_name, "[u'AcpiPmi']")
    self.assertEqual(acpipmi.registry_key.Path(),
                     "/C.1000000000000000/registry/%s/AcpiPmi" % hklm_set01)

    acpi = results.next()
    self.assertEqual(acpi.name, "ACPI")
    self.assertEqual(acpi.service_type, 1)
    self.assertEqual(acpi.startup_type, 0)
    self.assertEqual(acpi.error_control, 3)
    self.assertEqual(acpi.image_path, "system32\\drivers\\ACPI.sys")
    self.assertEqual(acpi.display_name, "Microsoft ACPI Driver")
    self.assertEqual(acpi.group_name, "Boot Bus Extender")
    self.assertEqual(acpi.driver_package_id,
                     "acpi.inf_amd64_neutral_99aaaaabcccccccc")
    self.assertRaises(StopIteration, results.next)

  def testWinUserSpecialDirs(self):
    reg_str = rdfvalue.StatEntry.RegistryType.REG_SZ
    hk_u = "registry/HKEY_USERS/S-1-1-1010-10101-1010"
    service_keys = [
        ("%s/Environment/TEMP" % hk_u, r"temp\path", reg_str),
        ("%s/Volatile Environment/USERDOMAIN" % hk_u, "GEVULOT", reg_str)
        ]

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
    self.assertEqual(r"C:", parser.Parse(stat, None).next())


