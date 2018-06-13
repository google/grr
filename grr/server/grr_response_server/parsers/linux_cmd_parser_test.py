#!/usr/bin/env python
"""Unit test for the linux cmd parser."""

import os


from grr import config
from grr.lib import flags
from grr.lib import parser as lib_parser
from grr.lib.rdfvalues import anomaly as rdf_anomaly
from grr.lib.rdfvalues import client as rdf_client
from grr.server.grr_response_server import artifact
from grr.server.grr_response_server.parsers import linux_cmd_parser
from grr.test_lib import artifact_test_lib
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
    self.assertEqual(len(out), 2)
    self.assertTrue(isinstance(out[0], rdf_client.SoftwarePackage))
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
    self.assertTrue(isinstance(repolist[0], rdf_client.PackageRepository))

    self.assertEqual(repolist[0].id, "rhel")
    self.assertEqual(repolist[0].name, "rhel repo")
    self.assertEqual(repolist[0].revision, "1")
    self.assertEqual(repolist[0].last_update, "Sun Mar 15 08:51:32")
    self.assertEqual(repolist[0].num_packages, "12")
    self.assertEqual(repolist[0].size, "8 GB")
    self.assertEqual(repolist[0].baseurl, "http://rhel/repo")
    self.assertEqual(repolist[0].timeout,
                     "1200 second(s) (last: Mon Apr  1 20:30:02 2016)")
    self.assertEqual(len(repolist), 2)

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
    self.assertEqual(7, len(software))
    self.assertEqual(1, len(anomaly))
    expected = {
        "glib2": "2.12.3-4.el5_3.1",
        "elfutils-libelf": "0.137-3.el5",
        "libgpg-error": "1.4-2",
        "keyutils-libs": "1.2-1.el5",
        "less": "436-9.el5",
        "libstdc++-devel": "4.1.2-55.el5",
        "gcc-c++": "4.1.2-55.el5"
    }
    self.assertItemsEqual(expected, software)
    self.assertEqual("Broken rpm database.", anomaly[0].symptom)

  def testDpkgCmdParser(self):
    """Ensure we can extract packages from dpkg output."""
    parser = linux_cmd_parser.DpkgCmdParser()
    content = open(os.path.join(self.base_path, "checks/data/dpkg.out"),
                   "rb").read()
    out = list(
        parser.Parse("/usr/bin/dpkg", ["--list"], content, "", 0, 5, None))
    self.assertEqual(len(out), 181)
    self.assertTrue(isinstance(out[1], rdf_client.SoftwarePackage))
    self.assertTrue(out[0].name, "acpi-support-base")

  def testDpkgCmdParserPrecise(self):
    """Ensure we can extract packages from dpkg output on ubuntu precise."""
    parser = linux_cmd_parser.DpkgCmdParser()
    content = open(
        os.path.join(self.base_path, "checks/data/dpkg.precise.out"),
        "rb").read()
    out = list(
        parser.Parse("/usr/bin/dpkg", ["--list"], content, "", 0, 5, None))
    self.assertEqual(len(out), 30)
    self.assertTrue(isinstance(out[1], rdf_client.SoftwarePackage))
    self.assertTrue(out[0].name, "adduser")

  def testDmidecodeParser(self):
    """Test to see if we can get data from dmidecode output."""
    parser = linux_cmd_parser.DmidecodeCmdParser()
    content = open(os.path.join(self.base_path, "dmidecode.out"), "rb").read()
    hardware = parser.Parse("/usr/sbin/dmidecode", ["-q"], content, "", 0, 5,
                            None)
    self.assertTrue(isinstance(hardware, rdf_client.HardwareInfo))

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

  def testPsCmdParser(self):
    """Tests for the PsCmdParser class."""
    parser = linux_cmd_parser.PsCmdParser()
    # Check the detailed 'ps' output. i.e. lots of args.
    content = open(os.path.join(self.base_path, "pscmd.out"), "rb").read()
    args = [
        "h", "-ewwo",
        "pid,ppid,comm,ruid,uid,suid,rgid,gid,sgid,user,tty,stat,nice,"
        "thcount,pcpu,rss,vsz,pmem,cmd"
    ]
    processes = list(parser.Parse("/bin/ps", args, content, "", 0, 5, None))
    # Confirm we parsed all the appropriate lines.
    self.assertEqual(5, len(processes))
    # Check we got a list of valid processes.
    process = None
    for process in processes:
      self.assertTrue(isinstance(process, rdf_client.Process))

    # Now lets tear apart the last one.
    self.assertEquals(136095, process.pid)
    self.assertEquals("ps", process.name)
    self.assertEquals(27262, process.effective_uid)
    self.assertEquals("usernam", process.username)
    self.assertEquals("pts/0", process.terminal)
    self.assertEquals(0.0, process.user_cpu_time)
    self.assertEquals(920, process.RSS_size)
    args.insert(0, "ps")
    self.assertEquals(args, process.cmdline)

    # Check the simple 'ps -ef' output.
    content = open(os.path.join(self.base_path, "psefcmd.out"), "rb").read()
    args = ["-ef"]
    processes = list(parser.Parse("/bin/ps", args, content, "", 0, 5, None))
    # Confirm we parsed all the appropriate lines.
    self.assertEqual(6, len(processes))
    # Check we got a list of valid processes.
    process = None
    for process in processes:
      self.assertTrue(isinstance(process, rdf_client.Process))

    # Now lets tear apart the last one.
    self.assertEquals(337492, process.pid)
    self.assertEquals(592357, process.ppid)
    self.assertEquals("ps", process.name)
    self.assertEquals("usernam", process.username)
    self.assertEquals("pts/0", process.terminal)
    self.assertEquals(0.0, process.cpu_percent)
    args.insert(0, "ps")
    self.assertEquals(args, process.cmdline)

  @artifact_test_lib.PatchDefaultArtifactRegistry
  def testPsCmdParserValidation(self, registry):
    """Test the PsCmdParser pass Validation() method."""
    test_artifacts_file = os.path.join(config.CONFIG["Test.data_dir"],
                                       "artifacts", "test_artifacts.json")
    registry.AddFileSource(test_artifacts_file)

    parser = linux_cmd_parser.PsCmdParser

    # Test with no ps cmd artifact.
    parser.Validate()

    # Test with good ps artifacts.
    content_good1 = """name: GoodPsArgs1
doc: "ps with the default/typical non-specified format."
sources:
- type: COMMAND
  attributes:
    cmd: "/bin/ps"
    args: ["-ef"]
supported_os: [Linux]
"""
    content_good2 = """name: GoodPsArgs2
doc: "ps where we specify the format."
sources:
- type: COMMAND
  attributes:
    cmd: "/bin/ps"
    args: ["h", "-ewwo", "pid,ppid,uid,comm,cmd"]
supported_os: [Linux]
"""
    artifact.UploadArtifactYamlFile(content_good1)
    artifact.UploadArtifactYamlFile(content_good2)
    # Add these new artifacts to the supported ones for the parser.
    parser.supported_artifacts.extend(["GoodPsArgs1", "GoodPsArgs2"])
    parser.Validate()

    # Now add a bad ones. This should cause the validator to raise an error.
    content_bad1 = """name: BadPsArgsDuplicateCmd
doc: "ps command with 'cmd' specified more than once."
sources:
- type: COMMAND
  attributes:
    cmd: "/bin/ps"
    args: ["h", "-ewwo", "pid,ppid,uid,cmd,comm,cmd"]
supported_os: [Linux]
"""
    content_bad2 = """name: BadPsArgsCmdNotAtEnd
doc: "ps command with 'cmd' specified, but not at the end."
sources:
- type: COMMAND
  attributes:
    cmd: "/bin/ps"
    args: ["-ewwo", "pid,ppid,uid,cmd,comm"]
supported_os: [Linux]
"""
    artifact.UploadArtifactYamlFile(content_bad1)
    artifact.UploadArtifactYamlFile(content_bad2)
    orig = parser.supported_artifacts
    for bad_artifact in ["BadPsArgsDuplicateCmd", "BadPsArgsCmdNotAtEnd"]:
      with self.assertRaises(lib_parser.ParserDefinitionError):
        # Reset and add the new artifacts to the supported ones for the parser.
        parser.supported_artifacts = list(orig)
        parser.supported_artifacts.append(bad_artifact)
        parser.Validate()


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  flags.StartMain(main)
