#!/usr/bin/env python
"""Unit test for the linux cmd parser."""

import os


from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.parsers import linux_cmd_parser


class LinuxCmdParserTest(test_lib.GRRBaseTest):
  """Test parsing of linux command output."""

  def testDpkgCmdParser(self):
    """Ensure we can extract packages from dpkg output."""
    parser = linux_cmd_parser.DpkgCmdParser()
    content = open(os.path.join(self.base_path, "dpkg.out")).read()
    out = list(parser.Parse("/usr/bin/dpkg", ["--list"], content, "", 0, 5,
                            None))
    self.assertEqual(len(out), 181)
    self.assertTrue(isinstance(out[1], rdfvalue.SoftwarePackage))
    self.assertTrue(out[0].name, "acpi-support-base")

  def testDmidecodeParser(self):
    """Test to see if we can get data from dmidecode output."""
    parser = linux_cmd_parser.DmidecodeCmdParser()
    content = open(os.path.join(self.base_path, "dmidecode.out")).read()
    hardware = parser.Parse(
        "/usr/sbin/dmidecode", ["-q"], content, "", 0, 5, None)
    self.assertTrue(isinstance(hardware, rdfvalue.HardwareInfo))
    self.assertEqual(hardware.serial_number, "2UA25107BB")
    self.assertEqual(hardware.system_manufacturer, "Hewlett-Packard")


def main(args):
  test_lib.main(args)

if __name__ == "__main__":
  flags.StartMain(main)
