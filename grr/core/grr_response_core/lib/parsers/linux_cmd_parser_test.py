#!/usr/bin/env python
"""Unit test for the linux cmd parser."""

import os
from typing import Sequence
from typing import Text

from absl import app
from absl.testing import absltest

from grr_response_core.lib.parsers import linux_cmd_parser
from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr.test_lib import test_lib


class YumListCmdParserTest(absltest.TestCase):

  def testSimpleOutput(self):
    output = """\
Installed Packages
foo.i386         3.14 @foo
bar.z80          2.71 @bar
java-1.8.0.armv8 1.41 @baz
    """

    packages = self._Parse(output)
    self.assertSequenceEqual(packages, [
        rdf_client.SoftwarePackage.Installed(
            name="foo", architecture="i386", publisher="@foo", version="3.14"),
        rdf_client.SoftwarePackage.Installed(
            name="bar", architecture="z80", publisher="@bar", version="2.71"),
        rdf_client.SoftwarePackage.Installed(
            name="java-1.8.0",
            architecture="armv8",
            publisher="@baz",
            version="1.41"),
    ])

  def testWrappedOutput(self):
    output = """\
Installed Packages
foo.i386  3.14
               @foo
bar.z80   2.71 @bar
baz.armv8
          1.41 @baz
    """

    packages = self._Parse(output)
    self.assertSequenceEqual(packages, [
        rdf_client.SoftwarePackage.Installed(
            name="foo", architecture="i386", publisher="@foo", version="3.14"),
        rdf_client.SoftwarePackage.Installed(
            name="bar", architecture="z80", publisher="@bar", version="2.71"),
        rdf_client.SoftwarePackage.Installed(
            name="baz", architecture="armv8", publisher="@baz", version="1.41"),
    ])

  def testRealOutput(self):
    output = """\
Installed Packages
NetworkManager.x86_64      1:1.8.0-12.el7_4    @rhui-rhel-7-server-e4s-rhui-rpms
NetworkManager-config-server.noarch
                           1:1.8.0-12.el7_4    @rhui-rhel-7-server-e4s-rhui-rpms
NetworkManager-libnm.x86_64
                           1:1.8.0-12.el7_4    @rhui-rhel-7-server-e4s-rhui-rpms
NetworkManager-team.x86_64 1:1.8.0-12.el7_4    @rhui-rhel-7-server-e4s-rhui-rpms
NetworkManager-tui.x86_64  1:1.8.0-12.el7_4    @rhui-rhel-7-server-e4s-rhui-rpms
Red_Hat_Enterprise_Linux-Release_Notes-7-en-US.noarch
                           7-2.el7             @anaconda
cronie-anacron.x86_64      1.4.11-17.el7       @anaconda
crontabs.noarch            1.11-6.20121102git.el7
                                               @anaconda
device-mapper.x86_64       7:1.02.140-8.el7    @anaconda
device-mapper-event.x86_64 7:1.02.140-8.el7    @rhui-rhel-7-server-e4s-rhui-rpms
device-mapper-event-libs.x86_64
                           7:1.02.140-8.el7    @rhui-rhel-7-server-e4s-rhui-rpms
device-mapper-libs.x86_64  7:1.02.140-8.el7    @anaconda
device-mapper-persistent-data.x86_64
                           0.7.0-0.1.rc6.el7_4.1
                                               @rhui-rhel-7-server-e4s-rhui-rpms
dhclient.x86_64            12:4.2.5-58.el7_4.4 @rhui-rhel-7-server-e4s-rhui-rpms
dhcp-common.x86_64         12:4.2.5-58.el7_4.4 @rhui-rhel-7-server-e4s-rhui-rpms
    """

    packages = self._Parse(output)
    self.assertSequenceEqual(packages, [
        rdf_client.SoftwarePackage.Installed(
            name="NetworkManager",
            architecture="x86_64",
            version="1:1.8.0-12.el7_4",
            publisher="@rhui-rhel-7-server-e4s-rhui-rpms"),
        rdf_client.SoftwarePackage.Installed(
            name="NetworkManager-config-server",
            architecture="noarch",
            version="1:1.8.0-12.el7_4",
            publisher="@rhui-rhel-7-server-e4s-rhui-rpms"),
        rdf_client.SoftwarePackage.Installed(
            name="NetworkManager-libnm",
            architecture="x86_64",
            version="1:1.8.0-12.el7_4",
            publisher="@rhui-rhel-7-server-e4s-rhui-rpms"),
        rdf_client.SoftwarePackage.Installed(
            name="NetworkManager-team",
            architecture="x86_64",
            version="1:1.8.0-12.el7_4",
            publisher="@rhui-rhel-7-server-e4s-rhui-rpms"),
        rdf_client.SoftwarePackage.Installed(
            name="NetworkManager-tui",
            architecture="x86_64",
            version="1:1.8.0-12.el7_4",
            publisher="@rhui-rhel-7-server-e4s-rhui-rpms"),
        rdf_client.SoftwarePackage.Installed(
            name="Red_Hat_Enterprise_Linux-Release_Notes-7-en-US",
            architecture="noarch",
            version="7-2.el7",
            publisher="@anaconda"),
        rdf_client.SoftwarePackage.Installed(
            name="cronie-anacron",
            architecture="x86_64",
            version="1.4.11-17.el7",
            publisher="@anaconda"),
        rdf_client.SoftwarePackage.Installed(
            name="crontabs",
            architecture="noarch",
            version="1.11-6.20121102git.el7",
            publisher="@anaconda"),
        rdf_client.SoftwarePackage.Installed(
            name="device-mapper",
            architecture="x86_64",
            version="7:1.02.140-8.el7",
            publisher="@anaconda"),
        rdf_client.SoftwarePackage.Installed(
            name="device-mapper-event",
            architecture="x86_64",
            version="7:1.02.140-8.el7",
            publisher="@rhui-rhel-7-server-e4s-rhui-rpms"),
        rdf_client.SoftwarePackage.Installed(
            name="device-mapper-event-libs",
            architecture="x86_64",
            version="7:1.02.140-8.el7",
            publisher="@rhui-rhel-7-server-e4s-rhui-rpms"),
        rdf_client.SoftwarePackage.Installed(
            name="device-mapper-libs",
            architecture="x86_64",
            version="7:1.02.140-8.el7",
            publisher="@anaconda"),
        rdf_client.SoftwarePackage.Installed(
            name="device-mapper-persistent-data",
            architecture="x86_64",
            version="0.7.0-0.1.rc6.el7_4.1",
            publisher="@rhui-rhel-7-server-e4s-rhui-rpms"),
        rdf_client.SoftwarePackage.Installed(
            name="dhclient",
            architecture="x86_64",
            version="12:4.2.5-58.el7_4.4",
            publisher="@rhui-rhel-7-server-e4s-rhui-rpms"),
        rdf_client.SoftwarePackage.Installed(
            name="dhcp-common",
            architecture="x86_64",
            version="12:4.2.5-58.el7_4.4",
            publisher="@rhui-rhel-7-server-e4s-rhui-rpms"),
    ])

  @staticmethod
  def _Parse(output: Text) -> Sequence[rdf_client.SoftwarePackage]:
    parser = linux_cmd_parser.YumListCmdParser()
    parsed = list(
        parser.Parse(
            cmd="yum",
            args=["list installed"],
            stdout=output.encode("utf-8"),
            stderr=b"",
            return_val=0,
            knowledge_base=None))

    return parsed[0].packages


class LinuxCmdParserTest(test_lib.GRRBaseTest):
  """Test parsing of linux command output."""

  def testYumListCmdParser(self):
    """Ensure we can extract packages from yum output."""
    parser = linux_cmd_parser.YumListCmdParser()
    content = open(os.path.join(self.base_path, "yum.out"), "rb").read()
    out = list(
        parser.Parse("/usr/bin/yum", ["list installed -q"], content, b"", 0,
                     None))
    self.assertLen(out, 1)
    self.assertLen(out[0].packages, 2)
    package = out[0].packages[0]
    self.assertIsInstance(package, rdf_client.SoftwarePackage)
    self.assertEqual(package.name, "ConsoleKit")
    self.assertEqual(package.architecture, "x86_64")
    self.assertEqual(package.publisher, "@base")

  def testYumRepolistCmdParser(self):
    """Test to see if we can get data from yum repolist output."""
    parser = linux_cmd_parser.YumRepolistCmdParser()
    content = open(os.path.join(self.base_path, "repolist.out"), "rb").read()
    repolist = list(
        parser.Parse("/usr/bin/yum", ["repolist", "-v", "-q"], content, b"", 0,
                     None))
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
        "gcc-c++": "4.1.2-55.el5"
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
            description="scripts for handling base ACPI events such as the power button",
            version="0.140-5",
            architecture="all",
            install_state=rdf_client.SoftwarePackage.InstallState.INSTALLED))
    self.assertEqual(
        package_list.packages[22],
        rdf_client.SoftwarePackage(
            name="diffutils",
            description=None,  # Test package with empty description.
            version="1:3.2-6",
            architecture="amd64",
            install_state=rdf_client.SoftwarePackage.InstallState.INSTALLED))

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
            install_state=rdf_client.SoftwarePackage.InstallState.INSTALLED))
    self.assertEqual(
        package_list.packages[12],
        rdf_client.SoftwarePackage(
            name="diffutils",
            description=None,  # Test package with empty description.
            version="1:3.2-1ubuntu1",
            architecture=None,
            install_state=rdf_client.SoftwarePackage.InstallState.INSTALLED))

  def testDmidecodeParser(self):
    """Test to see if we can get data from dmidecode output."""
    parser = linux_cmd_parser.DmidecodeCmdParser()
    content = open(os.path.join(self.base_path, "dmidecode.out"), "rb").read()
    parse_result = list(
        parser.Parse("/usr/sbin/dmidecode", ["-q"], content, b"", 0, None))
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
    stdout = b"""\
UID         PID   PPID  C STIME TTY          TIME CMD
root          1      0  0 Oct02 ?        00:01:35 /sbin/init splash
root          2      0  0 Oct02 ?        00:00:00 [kthreadd]
root          5      2  0 Oct02 ?        00:00:00 [kworker/0:0H]
colord    68931      1  0 Oct02 ?        00:00:00 /usr/lib/colord/colord
foobar    69081  69080  1 Oct02 ?        02:08:49 cinnamon --replace
"""

    parser = linux_cmd_parser.PsCmdParser()
    processes = list(parser.Parse("/bin/ps", "-ef", stdout, b"", 0, None))

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
    stdout = b"""\
UID     PID   PPID  C STIME TTY          TIME CMD
foo       1      0  0 Sep01 ?        00:01:23 /baz/norf
bar       2      1  0 Sep02 ?        00:00:00 /baz/norf --thud --quux
THIS IS AN INVALID LINE
quux      5      2  0 Sep03 ?        00:00:00 /blargh/norf
quux    ???    ???  0 Sep04 ?        00:00:00 ???
foo       4      2  0 Sep05 ?        00:00:00 /foo/bar/baz --quux=1337
"""

    parser = linux_cmd_parser.PsCmdParser()
    processes = list(parser.Parse("/bin/ps", "-ef", stdout, b"", 0, None))

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
  app.run(main)
