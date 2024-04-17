#!/usr/bin/env python
"""Unit test for the linux cmd parser."""

import os

from absl import app

from grr_response_core.lib.parsers import linux_cmd_parser
from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr.test_lib import test_lib


class LinuxCmdParserTest(test_lib.GRRBaseTest):
  """Test parsing of linux command output."""

  def testRpmCmdParser(self):
    """Ensure we can extract packages from rpm output."""
    parser = linux_cmd_parser.RpmCmdParser()
    content = b"""
      glib2-2.12.3-4.el5_3.1
      elfutils-libelf-0.137-3.el5
      libgpg-error-1.4-2
      keyutils-libs-1.2-1.el5
      less-436-9.el5
      libstdc++-devel-4.1.2-55.el5
      gcc-c++-4.1.2-55.el5
      -not-valid.123.el5
    """
    stderr = b"error: rpmdbNextIterator: skipping h#"
    out = list(parser.Parse("/bin/rpm", ["-qa"], content, stderr, 0, None))
    # A package list and an Anomaly.
    self.assertLen(out, 2)
    anomaly = [o for o in out if isinstance(o, rdf_anomaly.Anomaly)]
    self.assertLen(anomaly, 1)

    package_lists = [
        o for o in out if isinstance(o, rdf_client.SoftwarePackages)
    ]
    self.assertLen(package_lists, 1)

    package_list = package_lists[0]

    self.assertLen(package_list.packages, 7)

    software = {o.name: o.version for o in package_list.packages}
    expected = {
        "glib2": "2.12.3-4.el5_3.1",
        "elfutils-libelf": "0.137-3.el5",
        "libgpg-error": "1.4-2",
        "keyutils-libs": "1.2-1.el5",
        "less": "436-9.el5",
        "libstdc++-devel": "4.1.2-55.el5",
        "gcc-c++": "4.1.2-55.el5",
    }
    self.assertCountEqual(expected, software)
    self.assertEqual("Broken rpm database.", anomaly[0].symptom)

  def testDpkgCmdParser(self):
    """Ensure we can extract packages from dpkg output."""
    parser = linux_cmd_parser.DpkgCmdParser()
    content = open(os.path.join(self.base_path, "dpkg.out"), "rb").read()
    out = list(parser.Parse("/usr/bin/dpkg", ["--list"], content, b"", 0, None))
    self.assertLen(out, 1)
    package_list = out[0]
    self.assertLen(package_list.packages, 181)
    self.assertEqual(
        package_list.packages[0],
        rdf_client.SoftwarePackage(
            name="acpi-support-base",
            description=(
                "scripts for handling base ACPI events such as the power button"
            ),
            version="0.140-5",
            architecture="all",
            install_state=rdf_client.SoftwarePackage.InstallState.INSTALLED,
        ),
    )
    self.assertEqual(
        package_list.packages[22],
        rdf_client.SoftwarePackage(
            name="diffutils",
            description=None,  # Test package with empty description.
            version="1:3.2-6",
            architecture="amd64",
            install_state=rdf_client.SoftwarePackage.InstallState.INSTALLED,
        ),
    )

  def testDpkgCmdParserPrecise(self):
    """Ensure we can extract packages from dpkg output on ubuntu precise."""
    parser = linux_cmd_parser.DpkgCmdParser()
    content = open(
        os.path.join(self.base_path, "dpkg.precise.out"), "rb"
    ).read()
    out = list(parser.Parse("/usr/bin/dpkg", ["--list"], content, b"", 0, None))
    self.assertLen(out, 1)
    package_list = out[0]
    self.assertLen(package_list.packages, 30)
    self.assertEqual(
        package_list.packages[0],
        rdf_client.SoftwarePackage(
            name="adduser",
            description="add and remove users and groups",
            version="3.113ubuntu2",
            architecture=None,
            install_state=rdf_client.SoftwarePackage.InstallState.INSTALLED,
        ),
    )
    self.assertEqual(
        package_list.packages[12],
        rdf_client.SoftwarePackage(
            name="diffutils",
            description=None,  # Test package with empty description.
            version="1:3.2-1ubuntu1",
            architecture=None,
            install_state=rdf_client.SoftwarePackage.InstallState.INSTALLED,
        ),
    )

  def testDmidecodeParser(self):
    """Test to see if we can get data from dmidecode output."""
    parser = linux_cmd_parser.DmidecodeCmdParser()
    content = open(os.path.join(self.base_path, "dmidecode.out"), "rb").read()
    parse_result = list(
        parser.Parse("/usr/sbin/dmidecode", ["-q"], content, b"", 0, None)
    )
    self.assertLen(parse_result, 1)
    hardware = parse_result[0]

    self.assertIsInstance(hardware, rdf_client.HardwareInfo)

    self.assertEqual(hardware.serial_number, "2UA25107BB")
    self.assertEqual(hardware.system_manufacturer, "Hewlett-Packard")
    self.assertEqual(hardware.system_product_name, "HP Z420 Workstation")
    self.assertEqual(
        hardware.system_uuid, "4596BF80-41F0-11E2-A3B4-10604B5C7F38"
    )
    self.assertEqual(hardware.system_sku_number, "C2R51UC#ABA")
    self.assertEqual(hardware.system_family, "103C_53335X G=D")

    self.assertEqual(hardware.bios_vendor, "Hewlett-Packard")
    self.assertEqual(hardware.bios_version, "J61 v02.08")
    self.assertEqual(hardware.bios_release_date, "10/17/2012")
    self.assertEqual(hardware.bios_rom_size, "16384 kB")
    self.assertEqual(hardware.bios_revision, "2.8")


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  app.run(main)
