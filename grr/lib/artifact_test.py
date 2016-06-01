#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests for artifacts."""



import gzip
import os
import subprocess
import time

from grr.client import client_utils_linux
from grr.client import client_utils_osx
from grr.client.client_actions import standard
from grr.client.components.rekall_support import rekall_types as rdf_rekall_types
from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import artifact
from grr.lib import artifact_registry
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import parsers
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import collects
# For ArtifactCollectorFlow pylint: disable=unused-import
from grr.lib.flows.general import collectors
# pylint: enable=unused-import
from grr.lib.rdfvalues import anomaly as rdf_anomaly
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import protodict as rdf_protodict

# pylint: mode=test

WMI_SAMPLE = [
    rdf_protodict.Dict({
        u"Version": u"65.61.49216",
        u"InstallDate2": u"",
        u"Name": u"Google Chrome",
        u"Vendor": u"Google, Inc.",
        u"Description": u"Google Chrome",
        u"IdentifyingNumber": u"{35790B21-ACFE-33F5-B320-9DA320D96682}",
        u"InstallDate": u"20130710"
    }), rdf_protodict.Dict({
        u"Version": u"7.0.1",
        u"InstallDate2": u"",
        u"Name": u"Parity Agent",
        u"Vendor": u"Bit9, Inc.",
        u"Description": u"Parity Agent",
        u"IdentifyingNumber": u"{ADC7EB41-4CC2-4FBA-8FBE-9338A9FB7666}",
        u"InstallDate": u"20130710"
    }), rdf_protodict.Dict({
        u"Version": u"8.0.61000",
        u"InstallDate2": u"",
        u"Name": u"Microsoft Visual C++ 2005 Redistributable (x64)",
        u"Vendor": u"Microsoft Corporation",
        u"Description": u"Microsoft Visual C++ 2005 Redistributable (x64)",
        u"IdentifyingNumber": u"{ad8a2fa1-06e7-4b0d-927d-6e54b3d3102}",
        u"InstallDate": u"20130710"
    })
]


class TestCmdProcessor(parsers.CommandParser):

  output_types = ["SoftwarePackage"]
  supported_artifacts = ["TestCmdArtifact"]

  def Parse(self, cmd, args, stdout, stderr, return_val, time_taken,
            knowledge_base):
    _ = cmd, args, stdout, stderr, return_val, time_taken, knowledge_base
    installed = rdf_client.SoftwarePackage.InstallState.INSTALLED
    soft = rdf_client.SoftwarePackage(name="Package1",
                                      description="Desc1",
                                      version="1",
                                      architecture="amd64",
                                      install_state=installed)
    yield soft
    soft = rdf_client.SoftwarePackage(name="Package2",
                                      description="Desc2",
                                      version="1",
                                      architecture="i386",
                                      install_state=installed)
    yield soft

    # Also yield something random so we can test return type filtering.
    yield rdf_client.StatEntry()

    # Also yield an anomaly to test that.
    yield rdf_anomaly.Anomaly(type="PARSER_ANOMALY",
                              symptom="could not parse gremlins.")


class MultiProvideParser(parsers.RegistryValueParser):

  output_types = ["Dict"]
  supported_artifacts = ["DepsProvidesMultiple"]

  def Parse(self, stat, knowledge_base):
    _ = stat, knowledge_base
    test_dict = {"environ_temp": rdfvalue.RDFString("tempvalue"),
                 "environ_path": rdfvalue.RDFString("pathvalue")}
    yield rdf_protodict.Dict(test_dict)


class RekallMock(action_mocks.MemoryClientMock):

  def __init__(self, client_id, result_filename, *args, **kwargs):
    super(RekallMock, self).__init__(*args, **kwargs)

    self.result_filename = result_filename
    self.client_id = client_id

  def RekallAction(self, _):
    # Generate this file with:
    # rekal --output data -f win7_trial_64bit.raw \
    # pslist | gzip - > rekall_pslist_result.dat.gz
    ps_list_file = os.path.join(config_lib.CONFIG["Test.data_dir"],
                                self.result_filename)
    result = rdf_rekall_types.RekallResponse(
        json_messages=gzip.open(ps_list_file).read(10000000),
        plugin="pslist",
        client_urn=self.client_id)

    return [result, rdf_client.Iterator(state="FINISHED")]


class ArtifactTest(test_lib.FlowTestsBaseclass):
  """Helper class for tests using artifacts."""

  def setUp(self):
    """Make sure things are initialized."""
    super(ArtifactTest, self).setUp()
    # Common group of mocks used by lots of tests.
    self.client_mock = action_mocks.ActionMock("TransferBuffer", "StatFile",
                                               "Find", "HashBuffer", "HashFile",
                                               "ListDirectory",
                                               "FingerprintFile", "Grep",
                                               "WmiQuery")

  def LoadTestArtifacts(self):
    """Add the test artifacts in on top of whatever is in the registry."""
    artifact_registry.REGISTRY.AddFileSource(os.path.join(config_lib.CONFIG[
        "Test.data_dir"], "artifacts", "test_artifacts.json"))

  class MockClient(action_mocks.MemoryClientMock):

    def WmiQuery(self, _):
      return WMI_SAMPLE

  def MockClientMountPointsWithImage(self, image_path, fs_type="ext2"):
    """Mock the client to run off a test image.

    Args:
       image_path: The path to the image file.
       fs_type: The filesystem in the image.

    Returns:
        A context manager which ensures that client actions are served off the
        test image.
    """

    def MockGetMountpoints():
      return {"/": (image_path, fs_type)}

    return utils.MultiStubber(
        (client_utils_linux, "GetMountpoints", MockGetMountpoints),
        (client_utils_osx, "GetMountpoints", MockGetMountpoints),
        (standard, "HASH_CACHE", utils.FastStore(100)))

  def RunCollectorAndGetCollection(self, artifact_list, client_mock=None, **kw):
    """Helper to handle running the collector flow."""
    if client_mock is None:
      client_mock = self.MockClient(client_id=self.client_id)

    output_name = "/analysis/output/%s" % int(time.time())

    for _ in test_lib.TestFlowHelper("ArtifactCollectorFlow",
                                     client_mock=client_mock,
                                     output=output_name,
                                     client_id=self.client_id,
                                     artifact_list=artifact_list,
                                     token=self.token,
                                     **kw):
      pass

    output_urn = self.client_id.Add(output_name)
    return aff4.FACTORY.Open(output_urn,
                             aff4_type=collects.RDFValueCollection,
                             token=self.token)


class GRRArtifactTest(ArtifactTest):

  def testRDFMaps(self):
    """Validate the RDFMaps."""
    for rdf_name, dat in artifact.GRRArtifactMappings.rdf_map.items():
      # "info/software", "InstalledSoftwarePackages", "INSTALLED_PACKAGES",
      # "Append"
      _, aff4_type, aff4_attribute, operator = dat

      if operator not in ["Append", "Overwrite"]:
        raise artifact_registry.ArtifactDefinitionError(
            "Bad RDFMapping, unknown operator %s in %s" % (operator, rdf_name))

      if aff4_type not in aff4.AFF4Object.classes:
        raise artifact_registry.ArtifactDefinitionError(
            "Bad RDFMapping, invalid AFF4 Object %s in %s" %
            (aff4_type, rdf_name))

      attr = getattr(aff4.AFF4Object.classes[aff4_type].SchemaCls,
                     aff4_attribute)()
      if not isinstance(attr, rdfvalue.RDFValue):
        raise artifact_registry.ArtifactDefinitionError(
            "Bad RDFMapping, bad attribute %s for %s" %
            (aff4_attribute, rdf_name))

  def testUploadArtifactYamlFileAndDumpToYaml(self):
    artifact_registry.REGISTRY.ClearRegistry()
    artifact_registry.REGISTRY.ClearSources()
    artifact_registry.REGISTRY._CheckDirty()

    try:

      test_artifacts_file = os.path.join(config_lib.CONFIG["Test.data_dir"],
                                         "artifacts", "test_artifacts.json")
      filecontent = open(test_artifacts_file).read()
      artifact.UploadArtifactYamlFile(filecontent, token=self.token)
      loaded_artifacts = artifact_registry.REGISTRY.GetArtifacts()
      self.assertEqual(len(loaded_artifacts), 18)
      self.assertIn("DepsWindirRegex", [a.name for a in loaded_artifacts])

      # Now dump back to YAML.
      yaml_data = artifact_registry.REGISTRY.DumpArtifactsToYaml()
      for snippet in [
          "name: TestFilesArtifact",
          "urls: ['https://msdn.microsoft.com/en-us/library/aa384749%28v=vs.85",
          "returned_types: [SoftwarePackage]",
          "args: [--list]",
          "cmd: /usr/bin/dpkg",
      ]:
        self.assertIn(snippet, yaml_data)
    finally:
      artifact.ArtifactLoader().RunOnce()

  def testUploadArtifactYamlFileMissingDoc(self):
    content = """name: Nodoc
sources:
- type: GREP
  attributes:
    paths: [/etc/blah]
    content_regex_list: ["stuff"]
supported_os: [Linux]
"""
    with self.assertRaises(artifact_registry.ArtifactDefinitionError):
      artifact.UploadArtifactYamlFile(content, token=self.token)

  def testUploadArtifactYamlFileBadList(self):
    content = """name: BadList
doc: here's the doc
sources:
- type: GREP
  attributes:
    paths: /etc/blah
    content_regex_list: ["stuff"]
supported_os: [Linux]
"""
    with self.assertRaises(artifact_registry.ArtifactDefinitionError):
      artifact.UploadArtifactYamlFile(content, token=self.token)

  def testUploadArtifactYamlFileMissingNamesAttribute(self):
    content = """name: BadGroupMissingNames
doc: broken
sources:
- type: ARTIFACT_GROUP
  attributes:
    - 'One'
    - 'Two'
supported_os: [Linux]
"""

    with self.assertRaises(artifact_registry.ArtifactDefinitionError):
      artifact.UploadArtifactYamlFile(content, token=self.token)

  def testCommandArgumentOrderIsPreserved(self):
    content = """name: CommandOrder
doc: here's the doc
sources:
- type: COMMAND
  attributes:
    args: ["-L", "-v", "-n"]
    cmd: /sbin/iptables
supported_os: [Linux]
"""
    artifact.UploadArtifactYamlFile(content, token=self.token)
    artifact_obj = artifact_registry.REGISTRY.GetArtifacts(
        name_list=["CommandOrder"]).pop()
    arglist = artifact_obj.sources[0].attributes.get("args")
    self.assertEqual(arglist, ["-L", "-v", "-n"])

    # Check serialize/deserialize doesn't change order.
    serialized = artifact_obj.SerializeToString()
    artifact_obj = artifact_registry.Artifact(serialized)
    arglist = artifact_obj.sources[0].attributes.get("args")
    self.assertEqual(arglist, ["-L", "-v", "-n"])


class ArtifactFlowLinuxTest(ArtifactTest):

  def setUp(self):
    """Make sure things are initialized."""
    super(ArtifactFlowLinuxTest, self).setUp()
    with aff4.FACTORY.Open(
        self.SetupClients(1, system="Linux",
                          os_version="12.04")[0], mode="rw",
        token=self.token) as fd:

      # Add some users
      kb = fd.Get(fd.Schema.KNOWLEDGE_BASE)
      kb.MergeOrAddUser(rdf_client.User(username="gogol"))
      kb.MergeOrAddUser(rdf_client.User(username="gevulot"))
      kb.MergeOrAddUser(rdf_client.User(username="exomemory"))
      fd.Set(kb)

    self.LoadTestArtifacts()

  def testCmdArtifact(self):
    """Check we can run command based artifacts and get anomalies."""
    client_mock = self.MockClient("ExecuteCommand", client_id=self.client_id)
    with utils.Stubber(subprocess, "Popen", test_lib.Popen):
      for _ in test_lib.TestFlowHelper("ArtifactCollectorFlow",
                                       client_mock,
                                       client_id=self.client_id,
                                       store_results_in_aff4=True,
                                       use_tsk=False,
                                       artifact_list=["TestCmdArtifact"],
                                       token=self.token):
        pass
    urn = self.client_id.Add("info/software")
    fd = aff4.FACTORY.Open(urn, token=self.token)
    packages = fd.Get(fd.Schema.INSTALLED_PACKAGES)
    self.assertEqual(len(packages), 2)
    self.assertEqual(packages[0].__class__.__name__, "SoftwarePackage")

    with aff4.FACTORY.Open(
        self.client_id.Add("anomalies"),
        token=self.token) as anomaly_coll:
      self.assertEqual(len(anomaly_coll), 1)
      self.assertTrue("gremlin" in anomaly_coll[0].symptom)

  def testFilesArtifact(self):
    """Check GetFiles artifacts."""
    with test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                               test_lib.FakeTestDataVFSHandler):
      self.RunCollectorAndGetCollection(["TestFilesArtifact"],
                                        client_mock=self.client_mock)
      urn = self.client_id.Add("fs/os/").Add("var/log/auth.log")
      aff4.FACTORY.Open(urn, aff4_type=aff4_grr.VFSBlobImage, token=self.token)

  def testLinuxPasswdHomedirsArtifact(self):
    """Check LinuxPasswdHomedirs artifacts."""
    with test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                               test_lib.FakeTestDataVFSHandler):
      fd = self.RunCollectorAndGetCollection(["LinuxPasswdHomedirs"],
                                             client_mock=self.client_mock)

      self.assertEqual(len(fd), 3)
      self.assertItemsEqual([x.username for x in fd], [u"exomemory", u"gevulot",
                                                       u"gogol"])
      for user in fd:
        if user.username == u"exomemory":
          self.assertEqual(user.full_name, u"Never Forget (admin)")
          self.assertEqual(user.gid, 47)
          self.assertEqual(user.homedir, u"/var/lib/exomemory")
          self.assertEqual(user.shell, u"/bin/sh")
          self.assertEqual(user.uid, 46)

  def testArtifactOutput(self):
    """Check we can run command based artifacts."""
    with test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                               test_lib.FakeTestDataVFSHandler):
      # Will raise if something goes wrong.
      self.RunCollectorAndGetCollection(["TestFilesArtifact"],
                                        client_mock=self.client_mock)

      # Will raise if something goes wrong.
      self.RunCollectorAndGetCollection(["TestFilesArtifact"],
                                        client_mock=self.client_mock,
                                        split_output_by_artifact=True)

      # Test the on_no_results_error option.
      with self.assertRaises(RuntimeError) as context:
        self.RunCollectorAndGetCollection(["NullArtifact"],
                                          client_mock=self.client_mock,
                                          split_output_by_artifact=True,
                                          on_no_results_error=True)
      if "collector returned 0 responses" not in str(context.exception):
        raise RuntimeError("0 responses should have been returned")


class ArtifactFlowWindowsTest(ArtifactTest):

  def setUp(self):
    """Make sure things are initialized."""
    super(ArtifactFlowWindowsTest, self).setUp()
    self.SetupClients(1, system="Windows", os_version="6.2", arch="AMD64")
    self.LoadTestArtifacts()

  def testWMIQueryArtifact(self):
    """Check we can run WMI based artifacts."""
    self.RunCollectorAndGetCollection(["WMIInstalledSoftware"],
                                      store_results_in_aff4=True)
    urn = self.client_id.Add("info/software")
    fd = aff4.FACTORY.Open(urn, token=self.token)
    packages = fd.Get(fd.Schema.INSTALLED_PACKAGES)
    self.assertEqual(len(packages), 3)
    self.assertEqual(packages[0].description, "Google Chrome")

  def testRekallPsListArtifact(self):
    """Check we can run Rekall based artifacts."""
    test_lib.WriteComponent(token=self.token)

    fd = self.RunCollectorAndGetCollection(["RekallPsList"], RekallMock(
        self.client_id, "rekall_pslist_result.dat.gz"))

    self.assertEqual(len(fd), 35)
    self.assertEqual(fd[0].exe, "System")
    self.assertEqual(fd[0].pid, 4)
    self.assertIn("DumpIt.exe", [x.exe for x in fd])

  def testRekallVadArtifact(self):
    """Check we can run Rekall based artifacts."""
    test_lib.WriteComponent(token=self.token)

    # The client should now be populated with the data we care about.
    with aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token) as fd:
      fd.Set(fd.Schema.KNOWLEDGE_BASE(os="Windows", environ_systemdrive=r"c:"))

    fd = self.RunCollectorAndGetCollection(["FullVADBinaryList"], RekallMock(
        self.client_id, "rekall_vad_result.dat.gz"))

    self.assertEqual(len(fd), 1705)
    self.assertEqual(fd[0].path, u"c:\\Windows\\System32\\ntdll.dll")
    for x in fd:
      self.assertEqual(x.pathtype, "OS")
      extension = x.path.lower().split(".")[-1]
      self.assertIn(extension, ["exe", "dll", "pyd", "drv", "mui", "cpl"])


class GrrKbTest(ArtifactTest):

  def setUp(self):
    super(GrrKbTest, self).setUp()
    test_lib.ClientFixture(self.client_id, token=self.token)

  def ClearKB(self):
    client = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    client.Set(client.Schema.KNOWLEDGE_BASE, rdf_client.KnowledgeBase())
    client.Flush()


class GrrKbWindowsTest(GrrKbTest):

  def setUp(self):
    super(GrrKbWindowsTest, self).setUp()
    self.SetupClients(1, system="Windows", os_version="6.2", arch="AMD64")

    self.os_overrider = test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                              test_lib.FakeFullVFSHandler)
    self.reg_overrider = test_lib.VFSOverrider(
        rdf_paths.PathSpec.PathType.REGISTRY, test_lib.FakeRegistryVFSHandler)
    self.os_overrider.Start()
    self.reg_overrider.Start()

  def tearDown(self):
    super(GrrKbWindowsTest, self).tearDown()
    try:
      self.os_overrider.Stop()
      self.reg_overrider.Stop()
    except AttributeError:
      pass

  def testKnowledgeBaseRetrievalWindows(self):
    """Check we can retrieve a knowledge base from a client."""
    self.ClearKB()
    for _ in test_lib.TestFlowHelper("KnowledgeBaseInitializationFlow",
                                     self.client_mock,
                                     client_id=self.client_id,
                                     token=self.token):
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

    self.assertItemsEqual([x.username for x in kb.users], ["jim", "kovacs"])
    user = kb.GetUser(username="jim")
    self.assertEqual(user.username, "jim")
    self.assertEqual(user.sid, "S-1-5-21-702227068-2140022151-3110739409-1000")

  def testKnowledgeBaseMultiProvides(self):
    """Check we can handle multi-provides."""
    self.ClearKB()
    # Replace some artifacts with test one that will run the MultiProvideParser.
    self.LoadTestArtifacts()
    with test_lib.ConfigOverrider(
        {"Artifacts.knowledge_base": ["DepsProvidesMultiple"]}):
      for _ in test_lib.TestFlowHelper("KnowledgeBaseInitializationFlow",
                                       self.client_mock,
                                       client_id=self.client_id,
                                       token=self.token):
        pass

      # The client should now be populated with the data we care about.
      client = aff4.FACTORY.Open(self.client_id, token=self.token)
      kb = artifact.GetArtifactKnowledgeBase(client)
      self.assertEqual(kb.environ_temp, "tempvalue")
      self.assertEqual(kb.environ_path, "pathvalue")

  def testGlobRegistry(self):
    """Test that glob works on registry."""
    paths = ["HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows NT"
             "\\CurrentVersion\\ProfileList\\ProfilesDirectory",
             "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows NT"
             "\\CurrentVersion\\ProfileList\\AllUsersProfile"]

    for _ in test_lib.TestFlowHelper(
        "Glob",
        self.client_mock,
        paths=paths,
        pathtype=rdf_paths.PathSpec.PathType.REGISTRY,
        client_id=self.client_id,
        token=self.token):
      pass

    path = paths[0].replace("\\", "/")

    fd = aff4.FACTORY.Open(
        self.client_id.Add("registry").Add(path),
        token=self.token)
    self.assertEqual(fd.__class__.__name__, "VFSFile")
    self.assertEqual(
        fd.Get(fd.Schema.STAT).registry_data.GetValue(), "%SystemDrive%\\Users")

  def testGetDependencies(self):
    """Test that dependencies are calculated correctly."""
    artifact_registry.REGISTRY.ClearSources()
    try:
      test_artifacts_file = os.path.join(config_lib.CONFIG["Test.data_dir"],
                                         "artifacts", "test_artifacts.json")
      artifact_registry.REGISTRY.AddFileSource(test_artifacts_file)

      # No dependencies
      args = artifact.CollectArtifactDependenciesArgs(
          artifact_list=["DepsHomedir2"])
      collect_obj = artifact.CollectArtifactDependencies(None, token=self.token)
      collect_obj.args = args
      collect_obj.knowledge_base = None
      collect_obj.state.Register("all_deps", set())
      collect_obj.state.Register("awaiting_deps_artifacts", [])
      collect_obj.state.Register("knowledge_base",
                                 rdf_client.KnowledgeBase(os="Windows"))
      no_deps = collect_obj.GetFirstFlowsForCollection()

      self.assertItemsEqual(no_deps, [])
      self.assertItemsEqual(collect_obj.state.all_deps, [])
      self.assertItemsEqual(collect_obj.state.awaiting_deps_artifacts, [])

      # Dependency tree with a single starting point
      args = artifact.CollectArtifactDependenciesArgs(
          artifact_list=["DepsHomedir"])
      collect_obj.args = args
      no_deps = collect_obj.GetFirstFlowsForCollection()

      self.assertItemsEqual(no_deps, ["DepsControlSet"])
      self.assertItemsEqual(collect_obj.state.all_deps, ["environ_windir",
                                                         "users.username",
                                                         "current_control_set"])
      self.assertItemsEqual(collect_obj.state.awaiting_deps_artifacts,
                            ["DepsWindir", "DepsWindirRegex"])
    finally:
      artifact.ArtifactLoader().RunOnce()

  def testGetKBDependencies(self):
    """Test that KB dependencies are calculated correctly."""
    artifact_registry.REGISTRY.ClearSources()
    try:
      test_artifacts_file = os.path.join(config_lib.CONFIG["Test.data_dir"],
                                         "artifacts", "test_artifacts.json")
      artifact_registry.REGISTRY.AddFileSource(test_artifacts_file)

      with test_lib.ConfigOverrider({
          "Artifacts.knowledge_base": ["DepsParent", "DepsDesktop",
                                       "DepsHomedir", "DepsWindir",
                                       "DepsWindirRegex", "DepsControlSet",
                                       "FakeArtifact"],
          "Artifacts.knowledge_base_additions": ["DepsHomedir2"],
          "Artifacts.knowledge_base_skip": ["DepsWindir"],
          "Artifacts.knowledge_base_heavyweight": ["FakeArtifact"]
      }):
        args = artifact.KnowledgeBaseInitializationArgs(lightweight=True)
        kb_init = artifact.KnowledgeBaseInitializationFlow(None,
                                                           token=self.token)
        kb_init.args = args
        kb_init.state.Register("all_deps", set())
        kb_init.state.Register("awaiting_deps_artifacts", [])
        kb_init.state.Register("knowledge_base",
                               rdf_client.KnowledgeBase(os="Windows"))
        no_deps = kb_init.GetFirstFlowsForCollection()

        self.assertItemsEqual(no_deps, ["DepsControlSet", "DepsHomedir2"])
        self.assertItemsEqual(kb_init.state.all_deps,
                              ["users.homedir", "users.desktop",
                               "users.username", "environ_windir",
                               "current_control_set"])
        self.assertItemsEqual(kb_init.state.awaiting_deps_artifacts,
                              ["DepsParent", "DepsDesktop", "DepsHomedir",
                               "DepsWindirRegex"])
    finally:
      artifact.ArtifactLoader().RunOnce()


class GrrKbLinuxTest(GrrKbTest):

  def setUp(self):
    super(GrrKbLinuxTest, self).setUp()
    self.SetupClients(1, system="Linux", os_version="12.04")

  def testKnowledgeBaseRetrievalLinux(self):
    """Check we can retrieve a Linux kb."""
    self.ClearKB()
    with test_lib.ConfigOverrider({
        "Artifacts.knowledge_base": ["LinuxWtmp", "NetgroupConfiguration",
                                     "LinuxPasswdHomedirs", "LinuxRelease"],
        "Artifacts.netgroup_filter_regexes": ["^login$"],
        "Artifacts.netgroup_user_blacklist": ["isaac"]
    }):
      with test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                 test_lib.FakeTestDataVFSHandler):

        for _ in test_lib.TestFlowHelper("KnowledgeBaseInitializationFlow",
                                         self.client_mock,
                                         client_id=self.client_id,
                                         token=self.token):
          pass
        client = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
        kb = artifact.GetArtifactKnowledgeBase(client)
        self.assertEqual(kb.os_major_version, 14)
        self.assertEqual(kb.os_minor_version, 4)
        # user 1,2,3 from wtmp. yagharek from netgroup.
        self.assertItemsEqual([x.username for x in kb.users],
                              ["user1", "user2", "user3", "yagharek"])
        user = kb.GetUser(username="user1")
        self.assertEqual(user.last_logon.AsSecondsFromEpoch(), 1296552099)
        self.assertEqual(user.homedir, "/home/user1")

  def testKnowledgeBaseRetrievalLinuxPasswd(self):
    """Check we can retrieve a Linux kb."""
    self.ClearKB()
    with test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                               test_lib.FakeTestDataVFSHandler):
      with test_lib.ConfigOverrider({
          "Artifacts.knowledge_base": ["LinuxWtmp", "LinuxPasswdHomedirs",
                                       "LinuxRelease"],
          "Artifacts.knowledge_base_additions": [],
          "Artifacts.knowledge_base_skip": []
      }):

        for _ in test_lib.TestFlowHelper("KnowledgeBaseInitializationFlow",
                                         self.client_mock,
                                         client_id=self.client_id,
                                         token=self.token):
          pass

        client = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
        kb = artifact.GetArtifactKnowledgeBase(client)
        self.assertEqual(kb.os_major_version, 14)
        self.assertEqual(kb.os_minor_version, 4)
        # user 1,2,3 from wtmp.
        self.assertItemsEqual([x.username for x in kb.users],
                              ["user1", "user2", "user3"])
        user = kb.GetUser(username="user1")
        self.assertEqual(user.last_logon.AsSecondsFromEpoch(), 1296552099)
        self.assertEqual(user.homedir, "/home/user1")

        user = kb.GetUser(username="user2")
        self.assertEqual(user.last_logon.AsSecondsFromEpoch(), 1296552102)
        self.assertEqual(user.homedir, "/home/user2")

        self.assertFalse(kb.GetUser(username="buguser3"))

  def testKnowledgeBaseRetrievalLinuxNoUsers(self):
    """Cause a users.username dependency failure."""
    self.ClearKB()
    with test_lib.ConfigOverrider({
        "Artifacts.knowledge_base": ["NetgroupConfiguration",
                                     "NssCacheLinuxPasswdHomedirs",
                                     "LinuxRelease"],
        "Artifacts.netgroup_filter_regexes": ["^doesntexist$"]
    }):

      with test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                 test_lib.FakeTestDataVFSHandler):

        for _ in test_lib.TestFlowHelper("KnowledgeBaseInitializationFlow",
                                         self.client_mock,
                                         require_complete=False,
                                         client_id=self.client_id,
                                         token=self.token):
          pass
        client = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
        kb = artifact.GetArtifactKnowledgeBase(client)
        self.assertEqual(kb.os_major_version, 14)
        self.assertEqual(kb.os_minor_version, 4)
        self.assertItemsEqual([x.username for x in kb.users], [])


class GrrKbDarwinTest(GrrKbTest):

  def setUp(self):
    super(GrrKbDarwinTest, self).setUp()
    self.SetupClients(1, system="Darwin", os_version="10.9")

  def testKnowledgeBaseRetrievalDarwin(self):
    """Check we can retrieve a Darwin kb."""
    self.ClearKB()
    with test_lib.ConfigOverrider({"Artifacts.knowledge_base": ["OSXUsers"]}):
      with test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                 test_lib.ClientVFSHandlerFixture):

        for _ in test_lib.TestFlowHelper("KnowledgeBaseInitializationFlow",
                                         self.client_mock,
                                         client_id=self.client_id,
                                         token=self.token):
          pass
        client = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")

        kb = artifact.GetArtifactKnowledgeBase(client)
        self.assertEqual(kb.os_major_version, 10)
        self.assertEqual(kb.os_minor_version, 9)
        # scalzi from /Users dir listing.
        self.assertItemsEqual([x.username for x in kb.users], ["scalzi"])
        user = kb.GetUser(username="scalzi")
        self.assertEqual(user.homedir, "/Users/scalzi")


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
