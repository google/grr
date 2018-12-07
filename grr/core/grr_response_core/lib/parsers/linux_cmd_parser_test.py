#!/usr/bin/env python
"""Unit test for the linux cmd parser."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os


from absl.testing import absltest
from grr_response_core.lib import flags
from grr_response_core.lib.parsers import linux_cmd_parser
from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr.test_lib import test_lib


class LinuxCmdParserTest(test_lib.GRRBaseTest):
  """Test parsing of linux command output."""

  def testYumListCmdParser(self):
    """Ensure we can extract packages from yum output."""
    parser = linux_cmd_parser.YumListCmdParser()
    content = open(os.path.join(self.base_path, "yum.out"), "rb").read()
    out = list(
        parser.Parse("/usr/bin/yum", ["list installed -q"], content, "", 0, 5,
                     None))
    self.assertLen(out, 2)
    self.assertIsInstance(out[0], rdf_client.SoftwarePackage)
    self.assertEqual(out[0].name, "ConsoleKit")
    self.assertEqual(out[0].architecture, "x86_64")
    self.assertEqual(out[0].publisher, "@base")

  def testYumRepolistCmdParser(self):
    """Test to see if we can get data from yum repolist output."""
    parser = linux_cmd_parser.YumRepolistCmdParser()
    content = open(os.path.join(self.base_path, "repolist.out"), "rb").read()
    repolist = list(
        parser.Parse("/usr/bin/yum", ["repolist", "-v", "-q"], content, "", 0,
                     5, None))
    self.assertIsInstance(repolist[0], rdf_client.PackageRepository)

    self.assertEqual(repolist[0].id, "rhel")
    self.assertEqual(repolist[0].name, "rhel repo")
    self.assertEqual(repolist[0].revision, "1")
    self.assertEqual(repolist[0].last_update, "Sun Mar 15 08:51:32")
    self.assertEqual(repolist[0].num_packages, "12")
    self.assertEqual(repolist[0].size, "8 GB")
    self.assertEqual(repolist[0].baseurl, "http://rhel/repo")
    self.assertEqual(repolist[0].timeout,
                     "1200 second(s) (last: Mon Apr  1 20:30:02 2016)")
    self.assertLen(repolist, 2)

  def testRpmCmdParser(self):
    """Ensure we can extract packages from rpm output."""
    parser = linux_cmd_parser.RpmCmdParser()
    content = """
      glib2-2.12.3-4.el5_3.1
      elfutils-libelf-0.137-3.el5
      libgpg-error-1.4-2
      keyutils-libs-1.2-1.el5
      less-436-9.el5
      libstdc++-devel-4.1.2-55.el5
      gcc-c++-4.1.2-55.el5
      -not-valid.123.el5
    """
    stderr = "error: rpmdbNextIterator: skipping h#"
    out = list(parser.Parse("/bin/rpm", ["-qa"], content, stderr, 0, 5, None))
    software = {
        o.name: o.version
        for o in out
        if isinstance(o, rdf_client.SoftwarePackage)
    }
    anomaly = [o for o in out if isinstance(o, rdf_anomaly.Anomaly)]
    self.assertLen(software, 7)
    self.assertLen(anomaly, 1)
    expected = {
        "glib2": "2.12.3-4.el5_3.1",
        "elfutils-libelf": "0.137-3.el5",
        "libgpg-error": "1.4-2",
        "keyutils-libs": "1.2-1.el5",
        "less": "436-9.el5",
        "libstdc++-devel": "4.1.2-55.el5",
        "gcc-c++": "4.1.2-55.el5"
    }
    self.assertCountEqual(expected, software)
    self.assertEqual("Broken rpm database.", anomaly[0].symptom)

  def testDpkgCmdParser(self):
    """Ensure we can extract packages from dpkg output."""
    parser = linux_cmd_parser.DpkgCmdParser()
    content = open(os.path.join(self.base_path, "checks/data/dpkg.out"),
                   "rb").read()
    out = list(
        parser.Parse("/usr/bin/dpkg", ["--list"], content, "", 0, 5, None))
    self.assertLen(out, 181)
    self.assertIsInstance(out[1], rdf_client.SoftwarePackage)
    self.assertTrue(out[0].name, "acpi-support-base")

  def testDpkgCmdParserPrecise(self):
    """Ensure we can extract packages from dpkg output on ubuntu precise."""
    parser = linux_cmd_parser.DpkgCmdParser()
    content = open(
        os.path.join(self.base_path, "checks/data/dpkg.precise.out"),
        "rb").read()
    out = list(
        parser.Parse("/usr/bin/dpkg", ["--list"], content, "", 0, 5, None))
    self.assertLen(out, 30)
    self.assertIsInstance(out[1], rdf_client.SoftwarePackage)
    self.assertTrue(out[0].name, "adduser")

  def testDmidecodeParser(self):
    """Test to see if we can get data from dmidecode output."""
    parser = linux_cmd_parser.DmidecodeCmdParser()
    content = open(os.path.join(self.base_path, "dmidecode.out"), "rb").read()
    parse_result = list(
        parser.Parse("/usr/sbin/dmidecode", ["-q"], content, "", 0, 5, None))
    self.assertLen(parse_result, 1)
    hardware = parse_result[0]

    self.assertIsInstance(hardware, rdf_client.HardwareInfo)

    self.assertEqual(hardware.serial_number, "2UA25107BB")
    self.assertEqual(hardware.system_manufacturer, "Hewlett-Packard")
    self.assertEqual(hardware.system_product_name, "HP Z420 Workstation")
    self.assertEqual(hardware.system_uuid,
                     "4596BF80-41F0-11E2-A3B4-10604B5C7F38")
    self.assertEqual(hardware.system_sku_number, "C2R51UC#ABA")
    self.assertEqual(hardware.system_family, "103C_53335X G=D")

    self.assertEqual(hardware.bios_vendor, "Hewlett-Packard")
    self.assertEqual(hardware.bios_version, "J61 v02.08")
    self.assertEqual(hardware.bios_release_date, "10/17/2012")
    self.assertEqual(hardware.bios_rom_size, "16384 kB")
    self.assertEqual(hardware.bios_revision, "2.8")


class PsCmdParserTest(absltest.TestCase):

  def testRealOutput(self):
    stdout = """\
UID         PID   PPID  C STIME TTY          TIME CMD
root          1      0  0 Oct02 ?        00:01:35 /sbin/init splash
root          2      0  0 Oct02 ?        00:00:00 [kthreadd]
root          5      2  0 Oct02 ?        00:00:00 [kworker/0:0H]
colord    68931      1  0 Oct02 ?        00:00:00 /usr/lib/colord/colord
foobar    69081  69080  1 Oct02 ?        02:08:49 cinnamon --replace
"""

    parser = linux_cmd_parser.PsCmdParser()
    processes = list(parser.Parse("/bin/ps", "-ef", stdout, "", 0, 0, None))

    self.assertLen(processes, 5)

    self.assertEqual(processes[0].username, "root")
    self.assertEqual(processes[0].pid, 1)
    self.assertEqual(processes[0].ppid, 0)
    self.assertEqual(processes[0].cpu_percent, 0.0)
    self.assertEqual(processes[0].terminal, "?")
    self.assertEqual(processes[0].cmdline, ["/sbin/init", "splash"])

    self.assertEqual(processes[1].username, "root")
    self.assertEqual(processes[1].pid, 2)
    self.assertEqual(processes[1].ppid, 0)
    self.assertEqual(processes[1].cpu_percent, 0.0)
    self.assertEqual(processes[1].terminal, "?")
    self.assertEqual(processes[1].cmdline, ["[kthreadd]"])

    self.assertEqual(processes[2].username, "root")
    self.assertEqual(processes[2].pid, 5)
    self.assertEqual(processes[2].ppid, 2)
    self.assertEqual(processes[2].cpu_percent, 0.0)
    self.assertEqual(processes[2].terminal, "?")
    self.assertEqual(processes[2].cmdline, ["[kworker/0:0H]"])

    self.assertEqual(processes[3].username, "colord")
    self.assertEqual(processes[3].pid, 68931)
    self.assertEqual(processes[3].ppid, 1)
    self.assertEqual(processes[3].cpu_percent, 0.0)
    self.assertEqual(processes[3].terminal, "?")
    self.assertEqual(processes[3].cmdline, ["/usr/lib/colord/colord"])

    self.assertEqual(processes[4].username, "foobar")
    self.assertEqual(processes[4].pid, 69081)
    self.assertEqual(processes[4].ppid, 69080)
    self.assertEqual(processes[4].cpu_percent, 1.0)
    self.assertEqual(processes[4].terminal, "?")
    self.assertEqual(processes[4].cmdline, ["cinnamon", "--replace"])

  def testDoesNotFailOnIncorrectInput(self):
    stdout = """\
UID     PID   PPID  C STIME TTY          TIME CMD
foo       1      0  0 Sep01 ?        00:01:23 /baz/norf
bar       2      1  0 Sep02 ?        00:00:00 /baz/norf --thud --quux
THIS IS AN INVALID LINE
quux      5      2  0 Sep03 ?        00:00:00 /blargh/norf
quux    ???    ???  0 Sep04 ?        00:00:00 ???
foo       4      2  0 Sep05 ?        00:00:00 /foo/bar/baz --quux=1337
"""

    parser = linux_cmd_parser.PsCmdParser()
    processes = list(parser.Parse("/bin/ps", "-ef", stdout, "", 0, 0, None))

    self.assertLen(processes, 4)

    self.assertEqual(processes[0].username, "foo")
    self.assertEqual(processes[0].pid, 1)
    self.assertEqual(processes[0].ppid, 0)
    self.assertEqual(processes[0].cpu_percent, 0)
    self.assertEqual(processes[0].terminal, "?")
    self.assertEqual(processes[0].cmdline, ["/baz/norf"])

    self.assertEqual(processes[1].username, "bar")
    self.assertEqual(processes[1].pid, 2)
    self.assertEqual(processes[1].ppid, 1)
    self.assertEqual(processes[1].cpu_percent, 0)
    self.assertEqual(processes[1].terminal, "?")
    self.assertEqual(processes[1].cmdline, ["/baz/norf", "--thud", "--quux"])

    self.assertEqual(processes[2].username, "quux")
    self.assertEqual(processes[2].pid, 5)
    self.assertEqual(processes[2].ppid, 2)
    self.assertEqual(processes[2].cpu_percent, 0)
    self.assertEqual(processes[2].terminal, "?")
    self.assertEqual(processes[2].cmdline, ["/blargh/norf"])

    self.assertEqual(processes[3].username, "foo")
    self.assertEqual(processes[3].pid, 4)
    self.assertEqual(processes[3].ppid, 2)
    self.assertEqual(processes[3].cpu_percent, 0)
    self.assertEqual(processes[3].terminal, "?")
    self.assertEqual(processes[3].cmdline, ["/foo/bar/baz", "--quux=1337"])


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  flags.StartMain(main)
