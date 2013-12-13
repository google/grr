#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""Tests for artifacts."""



import os
import subprocess

# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.client import vfs
from grr.lib import aff4
from grr.lib import artifact
from grr.lib import artifact_lib
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import parsers
from grr.lib import rdfvalue
from grr.lib import test_lib


# Shorcut to make things cleaner.
Artifact = artifact_lib.GenericArtifact   # pylint: disable=g-bad-name
Collector = artifact_lib.Collector        # pylint: disable=g-bad-name


class GRRArtifactTest(test_lib.GRRBaseTest):

  def testRDFMaps(self):
    """Validate the RDFMaps."""
    for rdf_name, dat in artifact.GRRArtifactMappings.rdf_map.items():
      # "info/software", "InstalledSoftwarePackages", "INSTALLED_PACKAGES",
      # "Append"
      _, aff4_type, aff4_attribute, operator = dat

      if operator not in ["Set", "Append"]:
        raise artifact_lib.ArtifactDefinitionError(
            "Bad RDFMapping, unknown operator %s in %s" %
            (operator, rdf_name))

      if aff4_type not in aff4.AFF4Object.classes:
        raise artifact_lib.ArtifactDefinitionError(
            "Bad RDFMapping, invalid AFF4 Object %s in %s" %
            (aff4_type, rdf_name))

      attr = getattr(aff4.AFF4Object.classes[aff4_type].SchemaCls,
                     aff4_attribute)()
      if not isinstance(attr, rdfvalue.RDFValue):
        raise artifact_lib.ArtifactDefinitionError(
            "Bad RDFMapping, bad attribute %s for %s" %
            (aff4_attribute, rdf_name))


WMI_SAMPLE = [
    rdfvalue.Dict({u"Version": u"65.61.49216", u"InstallDate2": u"",
                   u"Name": u"Google Chrome", u"Vendor": u"Google, Inc.",
                   u"Description": u"Google Chrome", u"IdentifyingNumber":
                   u"{35790B21-ACFE-33F5-B320-9DA320D96682}",
                   u"InstallDate": u"20130710"}),
    rdfvalue.Dict({u"Version": u"7.0.1", u"InstallDate2": u"",
                   u"Name": u"Parity Agent", u"Vendor": u"Bit9, Inc.",
                   u"Description": u"Parity Agent", u"IdentifyingNumber":
                   u"{ADC7EB41-4CC2-4FBA-8FBE-9338A9FB7666}",
                   u"InstallDate": u"20130710"}),
    rdfvalue.Dict({u"Version": u"8.0.61000", u"InstallDate2": u"",
                   u"Name": u"Microsoft Visual C++ 2005 Redistributable (x64)",
                   u"Vendor": u"Microsoft Corporation", u"Description":
                   u"Microsoft Visual C++ 2005 Redistributable (x64)",
                   u"IdentifyingNumber":
                   u"{ad8a2fa1-06e7-4b0d-927d-6e54b3d3102}",
                   u"InstallDate": u"20130710"})]


class TestCmdProcessor(parsers.CommandParser):

  output_types = ["SoftwarePackage"]
  supported_artifacts = ["TestCmdArtifact"]

  def Parse(self, cmd, args, stdout, stderr, return_val, time_taken,
            knowledge_base):
    _ = cmd, args, stdout, stderr, return_val, time_taken, knowledge_base
    installed = rdfvalue.SoftwarePackage.InstallState.INSTALLED
    soft = rdfvalue.SoftwarePackage(name="Package1", description="Desc1",
                                    version="1", architecture="amd64",
                                    install_state=installed)
    yield soft
    soft = rdfvalue.SoftwarePackage(name="Package2", description="Desc2",
                                    version="1", architecture="i386",
                                    install_state=installed)
    yield soft

    # Also yield something random so we can test return type filtering.
    yield rdfvalue.StatEntry()


class TestCmdArtifact(Artifact):
  """Test command artifact for dpkg."""
  SUPPORTED_OS = ["Linux"]
  LABELS = ["Software"]

  COLLECTORS = [
      Collector(action="RunCommand",
                args={"cmd": "/usr/bin/dpkg", "args": ["--list"]},
                returned_types=["SoftwarePackage"]
               )
  ]


class TestFileArtifact(Artifact):
  """Linux auth log file."""
  SUPPORTED_OS = ["Linux"]
  LABELS = ["Logs", "Authentication"]
  COLLECTORS = [
      Collector(action="GetFile",
                args={"path": "/var/log/auth.log"})
  ]


class TestFilesArtifact(Artifact):
  """Linux auth log file."""
  SUPPORTED_OS = ["Linux"]
  LABELS = ["Logs", "Authentication"]
  COLLECTORS = [
      Collector(action="GetFiles",
                args={"path_list": ["/var/log/auth.log"]})
  ]


class TestAggregationArtifact(Artifact):
  """Test artifact aggregation."""
  SUPPORTED_OS = ["Windows"]
  LABELS = ["Software"]

  COLLECTORS = [
      Collector(action="CollectArtifacts",
                args={"artifact_list": ["VolatilityPsList"]},
                returned_types=["Process"]),

      Collector(action="CollectArtifacts",
                args={"artifact_list": ["WindowsWMIInstalledSoftware"]},
                returned_types=["SoftwarePackage"])
  ]


class NullArtifact(Artifact):
  """Null."""


class TestAggregationArtifactDeps(TestAggregationArtifact):
  """Test artifact aggregation dependencies."""
  COLLECTORS = [
      Collector(action="CollectArtifacts",
                args={"artifact_list": ["TestAggregationArtifact"]},
                returned_types=["Process"])
  ]


class ArtifactFlowTest(test_lib.FlowTestsBaseclass):

  class MockClient(test_lib.MemoryClientMock):

    def WmiQuery(self, _):
      return WMI_SAMPLE

    def VolatilityAction(self, _):
      ps_list_file = os.path.join(config_lib.CONFIG["Test.data_dir"],
                                  "vol_pslist_result.dat")
      serialized_result = open(ps_list_file).read(100000)
      return [rdfvalue.VolatilityResult(serialized_result)]

  def setUp(self):
    """Make sure things are initialized."""
    super(ArtifactFlowTest, self).setUp()
    fd = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    fd.Set(fd.Schema.SYSTEM("Linux"))
    kb = fd.Schema.KNOWLEDGE_BASE()
    artifact.SetCoreGRRKnowledgeBaseValues(kb, fd)
    fd.Set(kb)
    fd.Flush()

  def testCmdArtifact(self):
    """Check we can run command based artifacts."""

    class Popen(object):
      """A mock object for subprocess.Popen."""

      def __init__(self, run, stdout, stderr, stdin):
        Popen.running_args = run
        Popen.stdout = stdout
        Popen.stderr = stderr
        Popen.stdin = stdin
        Popen.returncode = 0

      def communicate(self):  # pylint: disable=g-bad-name
        return "stdout here", "stderr here"

    client_mock = self.MockClient("ExecuteCommand")
    with test_lib.Stubber(subprocess, "Popen", Popen):
      for _ in test_lib.TestFlowHelper(
          "ArtifactCollectorFlow", client_mock, client_id=self.client_id,
          store_results_in_aff4=True, use_tsk=False,
          artifact_list=["TestCmdArtifact"], token=self.token):
        pass
    urn = self.client_id.Add("info/software")
    fd = aff4.FACTORY.Open(urn, token=self.token)
    packages = fd.Get(fd.Schema.INSTALLED_PACKAGES)
    self.assertEquals(len(packages), 2)
    self.assertEquals(packages[0].__class__.__name__, "SoftwarePackage")

  def testWMIQueryArtifact(self):
    """Check we can run WMI based artifacts."""

    fd = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    fd.Set(fd.Schema.SYSTEM("Windows"))
    fd.Set(fd.Schema.OS_VERSION("6.2"))
    fd.Flush()

    for _ in test_lib.TestFlowHelper(
        "ArtifactCollectorFlow", self.MockClient(),
        client_id=self.client_id, store_results_in_aff4=True,
        artifact_list=["WindowsWMIInstalledSoftware"], token=self.token):
      pass

    urn = self.client_id.Add("info/software")
    fd = aff4.FACTORY.Open(urn, token=self.token)
    packages = fd.Get(fd.Schema.INSTALLED_PACKAGES)
    self.assertEquals(len(packages), 3)
    self.assertEquals(packages[0].description, "Google Chrome")

  def testVolatilityArtifact(self):
    """Check we can run volatility based artifacts."""
    self.CreateSignedDriver()
    fd = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    fd.Set(fd.Schema.SYSTEM("Windows"))
    fd.Set(fd.Schema.ARCH("AMD64"))
    fd.Set(fd.Schema.OS_VERSION("6.2"))
    fd.Flush()
    for _ in test_lib.TestFlowHelper(
        "ArtifactCollectorFlow", self.MockClient(),
        client_id=self.client_id,
        artifact_list=["VolatilityPsList"], output="/analysis/foo",
        token=self.token, store_results_in_aff4=False):
      pass

    urn = self.client_id.Add("/analysis/foo")
    fd = aff4.FACTORY.Open(urn, aff4_type="RDFValueCollection",
                           token=self.token)
    self.assertEquals(len(fd), 50)
    self.assertEquals(fd[0].exe, "System")
    self.assertEquals(fd[0].pid, 4)

  def testFileArtifact(self):
    """Check we can run command based artifacts."""
    # Update the artifact path to point to the test directory.
    TestFileArtifact.COLLECTORS[0].args["path"] = (
        os.path.join(self.base_path, "auth.log"))

    client_mock = test_lib.ActionMock("TransferBuffer", "StatFile", "Find",
                                      "HashBuffer", "ListDirectory",
                                      "HashFile")
    for _ in test_lib.TestFlowHelper(
        "ArtifactCollectorFlow", client_mock, client_id=self.client_id,
        artifact_list=["TestFileArtifact"], use_tsk=False, token=self.token):
      pass
    urn = self.client_id.Add("fs/os/").Add(self.base_path).Add("auth.log")
    aff4.FACTORY.Open(urn, aff4_type="VFSBlobImage", token=self.token)

  def testFilesArtifact(self):
    """Check we can run command based artifacts."""
    # Update the artifact path to point to the test directory.
    TestFilesArtifact.COLLECTORS[0].args["path_list"] = (
        [os.path.join(self.base_path, "auth.log")])
    client_mock = test_lib.ActionMock("TransferBuffer", "StatFile", "Find",
                                      "HashBuffer", "ListDirectory",
                                      "HashFile")
    for _ in test_lib.TestFlowHelper(
        "ArtifactCollectorFlow", client_mock, client_id=self.client_id,
        artifact_list=["TestFilesArtifact"], use_tsk=False, token=self.token):
      pass
    urn = self.client_id.Add("fs/os/").Add(self.base_path).Add("auth.log")
    aff4.FACTORY.Open(urn, aff4_type="VFSBlobImage", token=self.token)

  def testAggregationArtifact(self):
    """Check we can dependency artifacts."""
    fd = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    fd.Set(fd.Schema.SYSTEM("Windows"))
    fd.Set(fd.Schema.ARCH("AMD64"))
    fd.Set(fd.Schema.OS_VERSION("6.2"))
    self.CreateSignedDriver()
    fd.Flush()
    for _ in test_lib.TestFlowHelper(
        "ArtifactCollectorFlow", self.MockClient(),
        client_id=self.client_id,
        artifact_list=["TestAggregationArtifact"], output="/analysis/foo",
        token=self.token):
      pass
    urn = self.client_id.Add("analysis/foo")
    fd = aff4.FACTORY.Open(urn, aff4_type="RDFValueCollection",
                           token=self.token)
    self.assertEquals(len(fd), 53)

  def testArtifactOutput(self):
    """Check we can run command based artifacts."""
    fd = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    fd.Set(fd.Schema.SYSTEM("Linux"))
    fd.Flush()
    output_path = "analysis/MyDownloadedFiles"

    # Update the artifact path to point to the test directory.
    TestFileArtifact.COLLECTORS[0].args["path"] = (
        os.path.join(self.base_path, "auth.log"))

    client_mock = test_lib.ActionMock("TransferBuffer", "StatFile", "HashFile",
                                      "HashBuffer", "ListDirectory", "Find")
    for _ in test_lib.TestFlowHelper(
        "ArtifactCollectorFlow", client_mock, client_id=self.client_id,
        artifact_list=["TestFileArtifact"], use_tsk=False, token=self.token,
        output=output_path):
      pass

    urn = self.client_id.Add(output_path)
    # will raise if it doesn't exist
    fd = aff4.FACTORY.Open(urn, aff4_type="RDFValueCollection",
                           token=self.token)

    # Test the writing to the subdir per artifact.
    for _ in test_lib.TestFlowHelper(
        "ArtifactCollectorFlow", client_mock, client_id=self.client_id,
        artifact_list=["TestFileArtifact"], use_tsk=False, token=self.token,
        output=output_path, split_output_by_artifact=True):
      pass

    urn = self.client_id.Add(output_path).Add("TestFileArtifact")
    # will raise if it doesn't exist
    fd = aff4.FACTORY.Open(urn, aff4_type="RDFValueCollection",
                           token=self.token)

    # Test the no_results_errors option.
    with self.assertRaises(RuntimeError) as context:
      for _ in test_lib.TestFlowHelper(
          "ArtifactCollectorFlow", client_mock, client_id=self.client_id,
          artifact_list=["NullArtifact"], use_tsk=False, token=self.token,
          output=output_path, split_output_by_artifact=True,
          no_results_errors=True):
        pass
    if "collector returned 0 responses" not in context.exception.message:
      raise RuntimeError("0 responses should have been returned")

  def testArtifactsDependencies(self):
    """Check artifact dependencies work."""
    deps = TestAggregationArtifactDeps.GetArtifactDependencies()
    self.assertListEqual(list(deps), ["TestAggregationArtifact"])
    deps = TestAggregationArtifactDeps.GetArtifactDependencies(recursive=True)
    self.assertListEqual(list(deps), ["TestAggregationArtifact"])

    # Test recursive loop.
    coll = TestAggregationArtifactDeps.COLLECTORS[0]
    backup = coll.args["artifact_list"]
    coll.args["artifact_list"] = ["TestAggregationArtifactDeps"]
    with self.assertRaises(RuntimeError) as e:
      deps = TestAggregationArtifactDeps.GetArtifactDependencies(recursive=True)
    self.assertTrue("artifact recursion depth" in e.exception.message)
    coll.args["artifact_list"] = backup   # Restore old collector.


class GrrKbTest(test_lib.FlowTestsBaseclass):
  def SetupMocks(self):
    test_lib.ClientFixture(self.client_id, token=self.token)

    client = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    client.Set(client.Schema.SYSTEM("Windows"))
    client.Set(client.Schema.OS_VERSION("6.2"))
    client.Flush()

    vfs.VFS_HANDLERS[
        rdfvalue.PathSpec.PathType.REGISTRY] = test_lib.ClientRegistryVFSFixture
    vfs.VFS_HANDLERS[
        rdfvalue.PathSpec.PathType.OS] = test_lib.ClientFullVFSFixture

  def testKnowledgeBaseRetrieval(self):
    """Check we can retrieve a knowledge base from a client."""
    self.SetupMocks()

    client_mock = test_lib.ActionMock("TransferBuffer", "StatFile", "Find",
                                      "HashBuffer", "ListDirectory", "HashFile")

    for _ in test_lib.TestFlowHelper(
        "KnowledgeBaseInitializationFlow", client_mock,
        client_id=self.client_id, token=self.token):
      pass

    # The client should now be populated with the data we care about.
    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    kb = artifact.GetArtifactKnowledgeBase(client)
    self.assertEqual(kb.environ_systemroot, "C:\\Windows")
    self.assertEqual(kb.time_zone, "US/Alaska")
    self.assertEqual(kb.code_page, "cp_1252")

    self.assertEqual(kb.environ_windir, "C:\\Windows")
    self.assertEqual(kb.environ_allusersprofile, "C:\\Users\\All Users")
    self.assertEqual(kb.environ_allusersappdata, "C:\\ProgramData")
    self.assertEqual(kb.environ_temp, "C:\\Windows\\TEMP")
    self.assertEqual(kb.environ_systemdrive, "C:")

    user = kb.GetUser(username="jim")
    self.assertEqual(user.username, "jim")
    self.assertEqual(user.sid, "S-1-5-21-702227068-2140022151-3110739409-1000")

  def testKnowledgeBaseRetrievalDarwin(self):
    """Check we can retrieve a kb from a non-windows client."""
    test_lib.ClientFixture(self.client_id, token=self.token)
    client = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    client.Set(client.Schema.SYSTEM("Darwin"))
    client.Set(client.Schema.OS_VERSION("10.9"))
    client.Close()

    client_mock = test_lib.ActionMock("TransferBuffer", "StatFile", "Find",
                                      "HashBuffer", "ListDirectory", "HashFile")

    for _ in test_lib.TestFlowHelper(
        "KnowledgeBaseInitializationFlow", client_mock,
        client_id=self.client_id, token=self.token):
      pass
    client = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    kb = artifact.GetArtifactKnowledgeBase(client)
    self.assertEqual(kb.os_major_version, 10)
    self.assertEqual(kb.os_minor_version, 9)
    user = kb.GetUser(username="Ernie")
    self.assertEqual(user.username, "Ernie")

  def testGlobRegistry(self):
    """Test that glob works on registry."""
    self.SetupMocks()

    client_mock = test_lib.ActionMock("TransferBuffer", "StatFile", "Find",
                                      "HashBuffer", "ListDirectory")

    paths = ["HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows NT"
             "\\CurrentVersion\\ProfileList\\ProfilesDirectory",
             "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows NT"
             "\\CurrentVersion\\ProfileList\\AllUsersProfile"]

    for _ in test_lib.TestFlowHelper(
        "Glob", client_mock, paths=paths,
        pathtype=rdfvalue.PathSpec.PathType.REGISTRY,
        client_id=self.client_id, token=self.token):
      pass

    path = paths[0].replace("\\", "/")

    fd = aff4.FACTORY.Open(self.client_id.Add("registry").Add(path),
                           token=self.token)
    self.assertEqual(fd.__class__.__name__, "VFSFile")
    self.assertEqual(fd.Get(fd.Schema.STAT).registry_data.GetValue(),
                     "%SystemDrive%\\Users")


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
