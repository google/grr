#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests for artifacts."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import gzip
import logging
import os
import subprocess

from grr_response_client.client_actions import searching
from grr_response_client.client_actions import standard
from grr_response_core import config
from grr_response_core.lib import flags
from grr_response_core.lib import parser
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.parsers import linux_file_parser
from grr_response_core.lib.parsers import rekall_artifact_parser
from grr_response_core.lib.parsers import wmi_parser
from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import rekall_types as rdf_rekall_types
from grr_response_server import aff4
from grr_response_server import aff4_flows
from grr_response_server import artifact
from grr_response_server import artifact_registry
from grr_response_server import data_store
from grr_response_server.aff4_objects import aff4_grr
from grr_response_server.flows.general import collectors
from grr_response_server.flows.general import filesystem
from grr.test_lib import action_mocks
from grr.test_lib import artifact_test_lib
from grr.test_lib import client_test_lib
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import parser_test_lib
from grr.test_lib import rekall_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib

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
    }),
    rdf_protodict.Dict({
        u"Version": u"7.0.1",
        u"InstallDate2": u"",
        u"Name": u"Parity Agent",
        u"Vendor": u"Bit9, Inc.",
        u"Description": u"Parity Agent",
        u"IdentifyingNumber": u"{ADC7EB41-4CC2-4FBA-8FBE-9338A9FB7666}",
        u"InstallDate": u"20130710"
    }),
    rdf_protodict.Dict({
        u"Version": u"8.0.61000",
        u"InstallDate2": u"",
        u"Name": u"Microsoft Visual C++ 2005 Redistributable (x64)",
        u"Vendor": u"Microsoft Corporation",
        u"Description": u"Microsoft Visual C++ 2005 Redistributable (x64)",
        u"IdentifyingNumber": u"{ad8a2fa1-06e7-4b0d-927d-6e54b3d3102}",
        u"InstallDate": u"20130710"
    })
]


# TODO(hanuszczak): Rename it back to `TestCmdProcessor` once new testing
# framework is properly set up.
#
# Class of this name is clashing with other `TestCmdProcessor` (declared in
# `//grr/server/grr_response_server/gui/selenium_tests/
# artifact_view_test.py`) and breaks the test class register. This should be
# fixed when the test class register is gone and new test discovery (`pytest`)
# is deployed.
class CmdProcessor(parser.CommandParser):

  output_types = ["SoftwarePackage"]
  supported_artifacts = ["TestCmdArtifact"]

  def Parse(self, cmd, args, stdout, stderr, return_val, time_taken,
            knowledge_base):
    _ = cmd, args, stdout, stderr, return_val, time_taken, knowledge_base
    installed = rdf_client.SoftwarePackage.InstallState.INSTALLED
    soft = rdf_client.SoftwarePackage(
        name="Package1",
        description="Desc1",
        version="1",
        architecture="amd64",
        install_state=installed)
    yield soft
    soft = rdf_client.SoftwarePackage(
        name="Package2",
        description="Desc2",
        version="1",
        architecture="i386",
        install_state=installed)
    yield soft

    # Also yield something random so we can test return type filtering.
    yield rdf_client_fs.StatEntry()

    # Also yield an anomaly to test that.
    yield rdf_anomaly.Anomaly(
        type="PARSER_ANOMALY", symptom="could not parse gremlins.")


class MultiProvideParser(parser.RegistryValueParser):

  output_types = ["Dict"]
  supported_artifacts = ["DepsProvidesMultiple"]

  def Parse(self, stat, knowledge_base):
    _ = stat, knowledge_base
    test_dict = {
        "environ_temp": rdfvalue.RDFString("tempvalue"),
        "environ_path": rdfvalue.RDFString("pathvalue")
    }
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
    ps_list_file = os.path.join(config.CONFIG["Test.data_dir"],
                                self.result_filename)
    result = rdf_rekall_types.RekallResponse(
        json_messages=gzip.open(ps_list_file).read(),
        plugin="pslist",
        client_urn=self.client_id)

    return [result]


@db_test_lib.DualDBTest
class ArtifactTest(flow_test_lib.FlowTestsBaseclass):
  """Helper class for tests using artifacts."""

  def setUp(self):
    """Make sure things are initialized."""
    super(ArtifactTest, self).setUp()
    # Common group of mocks used by lots of tests.
    self.client_mock = action_mocks.ActionMock(
        searching.Find,
        searching.Grep,
        standard.HashBuffer,
        standard.HashFile,
        standard.ListDirectory,
        standard.GetFileStat,
        standard.TransferBuffer,
    )

    self._artifact_patcher = artifact_test_lib.PatchDefaultArtifactRegistry()
    self._artifact_patcher.start()

  def tearDown(self):
    self._artifact_patcher.stop()
    super(ArtifactTest, self).tearDown()

  def LoadTestArtifacts(self):
    """Add the test artifacts in on top of whatever is in the registry."""
    artifact_registry.REGISTRY.AddFileSource(
        os.path.join(config.CONFIG["Test.data_dir"], "artifacts",
                     "test_artifacts.json"))

  class MockClient(action_mocks.MemoryClientMock):

    def WmiQuery(self, _):
      return WMI_SAMPLE

  def RunCollectorAndGetCollection(self,
                                   artifact_list,
                                   client_mock=None,
                                   client_id=None,
                                   **kw):
    """Helper to handle running the collector flow."""
    if client_mock is None:
      client_mock = self.MockClient(client_id=client_id)

    session_id = flow_test_lib.TestFlowHelper(
        collectors.ArtifactCollectorFlow.__name__,
        client_mock=client_mock,
        client_id=client_id,
        artifact_list=artifact_list,
        token=self.token,
        **kw)

    return flow_test_lib.GetFlowResults(client_id, session_id)


@db_test_lib.DualDBTest
class GRRArtifactTest(ArtifactTest):

  def testUploadArtifactYamlFileAndDumpToYaml(self):
    artifact_registry.REGISTRY.ClearRegistry()
    artifact_registry.REGISTRY.ClearSources()
    artifact_registry.REGISTRY._CheckDirty()

    try:

      test_artifacts_file = os.path.join(config.CONFIG["Test.data_dir"],
                                         "artifacts", "test_artifacts.json")
      filecontent = open(test_artifacts_file, "rb").read()
      artifact.UploadArtifactYamlFile(filecontent)
      loaded_artifacts = artifact_registry.REGISTRY.GetArtifacts()
      self.assertGreaterEqual(len(loaded_artifacts), 20)
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
    with self.assertRaises(rdf_artifacts.ArtifactDefinitionError):
      artifact.UploadArtifactYamlFile(content)

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
    with self.assertRaises(rdf_artifacts.ArtifactDefinitionError):
      artifact.UploadArtifactYamlFile(content)

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

    with self.assertRaises(rdf_artifacts.ArtifactDefinitionError):
      artifact.UploadArtifactYamlFile(content)

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
    artifact.UploadArtifactYamlFile(content)
    artifact_obj = artifact_registry.REGISTRY.GetArtifacts(
        name_list=["CommandOrder"]).pop()
    arglist = artifact_obj.sources[0].attributes.get("args")
    self.assertEqual(arglist, ["-L", "-v", "-n"])

    # Check serialize/deserialize doesn't change order.
    serialized = artifact_obj.SerializeToString()
    artifact_obj = rdf_artifacts.Artifact.FromSerializedString(serialized)
    arglist = artifact_obj.sources[0].attributes.get("args")
    self.assertEqual(arglist, ["-L", "-v", "-n"])

  def testSystemArtifactOverwrite(self):
    content = """
name: WMIActiveScriptEventConsumer
doc: here's the doc
sources:
- type: COMMAND
  attributes:
    args: ["-L", "-v", "-n"]
    cmd: /sbin/iptables
supported_os: [Linux]
"""
    artifact_registry.REGISTRY.ClearRegistry()
    artifact_registry.REGISTRY.ClearSources()
    artifact_registry.REGISTRY._CheckDirty()

    # System artifacts come from the test file.
    self.LoadTestArtifacts()

    # Uploaded files go to this collection.
    artifact_store_urn = aff4.ROOT_URN.Add("artifact_store")
    artifact_registry.REGISTRY.AddDatastoreSources([artifact_store_urn])

    # WMIActiveScriptEventConsumer is a system artifact, we can't overwrite it.
    with self.assertRaises(rdf_artifacts.ArtifactDefinitionError):
      artifact.UploadArtifactYamlFile(content)

    # Override the check and upload anyways. This simulates the case
    # where an artifact ends up shadowing a system artifact somehow -
    # for example when the system artifact was created after the
    # artifact was uploaded to the data store for testing.
    artifact.UploadArtifactYamlFile(content, overwrite_system_artifacts=True)

    # The shadowing artifact is at this point stored in the
    # collection. On the next full reload of the registry, there will
    # be an error that we can't overwrite the system artifact. The
    # artifact should automatically get deleted from the collection to
    # mitigate the problem.
    with self.assertRaises(rdf_artifacts.ArtifactDefinitionError):
      artifact_registry.REGISTRY._ReloadArtifacts()

    # As stated above, now this should work.
    artifact_registry.REGISTRY._ReloadArtifacts()

    # Make sure the artifact is now loaded and it's the version from the file.
    self.assertIn("WMIActiveScriptEventConsumer",
                  artifact_registry.REGISTRY._artifacts)
    artifact_obj = artifact_registry.REGISTRY.GetArtifact(
        "WMIActiveScriptEventConsumer")
    self.assertStartsWith(artifact_obj.loaded_from, "file:")

    # The artifact is gone from the collection.
    coll = artifact_registry.ArtifactCollection(artifact_store_urn)
    self.assertNotIn("WMIActiveScriptEventConsumer", coll)

  def testUploadArtifactBadDependencies(self):
    yaml_artifact = """
name: InvalidArtifact
doc: An artifact group with invalid dependencies.
sources:
- type: ARTIFACT_GROUP
  attributes:
    names:
      - NonExistingArtifact
"""
    with self.assertRaises(rdf_artifacts.ArtifactDependencyError):
      artifact.UploadArtifactYamlFile(yaml_artifact)


@db_test_lib.DualDBTest
class ArtifactFlowLinuxTest(ArtifactTest):

  def setUp(self):
    """Make sure things are initialized."""
    super(ArtifactFlowLinuxTest, self).setUp()
    users = [
        rdf_client.User(username="gogol"),
        rdf_client.User(username="gevulot"),
        rdf_client.User(username="exomemory"),
        rdf_client.User(username="user1"),
        rdf_client.User(username="user2"),
    ]
    self.SetupClient(0, system="Linux", os_version="12.04", users=users)

    self.LoadTestArtifacts()

  @parser_test_lib.WithParser("Cmd", CmdProcessor)
  def testCmdArtifact(self):
    """Check we can run command based artifacts and get anomalies."""
    client_id = test_lib.TEST_CLIENT_ID
    client_mock = self.MockClient(standard.ExecuteCommand, client_id=client_id)
    with utils.Stubber(subprocess, "Popen", client_test_lib.Popen):
      session_id = flow_test_lib.TestFlowHelper(
          collectors.ArtifactCollectorFlow.__name__,
          client_mock,
          client_id=client_id,
          use_tsk=False,
          artifact_list=["TestCmdArtifact"],
          token=self.token)

    results = flow_test_lib.GetFlowResults(client_id, session_id)
    self.assertLen(results, 3)
    packages = [p for p in results if isinstance(p, rdf_client.SoftwarePackage)]
    self.assertLen(packages, 2)

    anomalies = [a for a in results if isinstance(a, rdf_anomaly.Anomaly)]
    self.assertLen(anomalies, 1)
    self.assertIn("gremlin", anomalies[0].symptom)

  def testFilesArtifact(self):
    """Check GetFiles artifacts."""
    client_id = test_lib.TEST_CLIENT_ID
    with vfs_test_lib.FakeTestDataVFSOverrider():
      self.RunCollectorAndGetCollection(["TestFilesArtifact"],
                                        client_mock=self.client_mock,
                                        client_id=client_id)
      urn = client_id.Add("fs/os/").Add("var/log/auth.log")
      aff4.FACTORY.Open(urn, aff4_type=aff4_grr.VFSBlobImage, token=self.token)

  @parser_test_lib.WithParser("Passwd", linux_file_parser.PasswdBufferParser)
  def testLinuxPasswdHomedirsArtifact(self):
    """Check LinuxPasswdHomedirs artifacts."""
    with vfs_test_lib.FakeTestDataVFSOverrider():
      fd = self.RunCollectorAndGetCollection(["LinuxPasswdHomedirs"],
                                             client_mock=self.client_mock,
                                             client_id=test_lib.TEST_CLIENT_ID)

      self.assertLen(fd, 5)
      self.assertCountEqual(
          [x.username for x in fd],
          [u"exomemory", u"gevulot", u"gogol", u"user1", u"user2"])
      for user in fd:
        if user.username == u"exomemory":
          self.assertEqual(user.full_name, u"Never Forget (admin)")
          self.assertEqual(user.gid, 47)
          self.assertEqual(user.homedir, u"/var/lib/exomemory")
          self.assertEqual(user.shell, u"/bin/sh")
          self.assertEqual(user.uid, 46)

  def testArtifactOutput(self):
    """Check we can run command based artifacts."""
    client_id = test_lib.TEST_CLIENT_ID
    with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                   vfs_test_lib.FakeTestDataVFSHandler):
      # Will raise if something goes wrong.
      self.RunCollectorAndGetCollection(["TestFilesArtifact"],
                                        client_mock=self.client_mock,
                                        client_id=client_id)

      # Will raise if something goes wrong.
      self.RunCollectorAndGetCollection(["TestFilesArtifact"],
                                        client_mock=self.client_mock,
                                        client_id=client_id,
                                        split_output_by_artifact=True)

      # Test the error_on_no_results option.
      with self.assertRaises(RuntimeError) as context:
        with test_lib.SuppressLogs():
          self.RunCollectorAndGetCollection(["NullArtifact"],
                                            client_mock=self.client_mock,
                                            client_id=client_id,
                                            split_output_by_artifact=True,
                                            error_on_no_results=True)
      if "collector returned 0 responses" not in context.exception.message:
        raise RuntimeError("0 responses should have been returned")


@db_test_lib.DualDBTest
class ArtifactFlowWindowsTest(ArtifactTest):

  def setUp(self):
    """Make sure things are initialized."""
    super(ArtifactFlowWindowsTest, self).setUp()
    self.SetupClient(0, system="Windows", os_version="6.2", arch="AMD64")
    self.LoadTestArtifacts()

  @parser_test_lib.WithParser("WmiInstalledSoftware",
                              wmi_parser.WMIInstalledSoftwareParser)
  def testWMIQueryArtifact(self):
    """Check we can run WMI based artifacts."""
    client_id = self.SetupClient(
        0, system="Windows", os_version="6.2", arch="AMD64")
    col = self.RunCollectorAndGetCollection(["WMIInstalledSoftware"],
                                            client_id=client_id)

    self.assertLen(col, 3)
    descriptions = [package.description for package in col]
    self.assertIn("Google Chrome", descriptions)

  @parser_test_lib.WithParser("RekallPsList",
                              rekall_artifact_parser.RekallPsListParser)
  def testRekallPsListArtifact(self):
    """Check we can run Rekall based artifacts."""
    client_id = test_lib.TEST_CLIENT_ID
    with test_lib.ConfigOverrider({
        "Rekall.enabled":
            True,
        "Rekall.profile_server":
            rekall_test_lib.TestRekallRepositoryProfileServer.__name__
    }):
      fd = self.RunCollectorAndGetCollection(["RekallPsList"],
                                             RekallMock(
                                                 client_id,
                                                 "rekall_pslist_result.dat.gz"),
                                             client_id=client_id)

    self.assertLen(fd, 35)
    self.assertEqual(fd[0].exe, "System")
    self.assertEqual(fd[0].pid, 4)
    self.assertIn("DumpIt.exe", [x.exe for x in fd])

  @parser_test_lib.WithParser("RekallVad",
                              rekall_artifact_parser.RekallVADParser)
  def testRekallVadArtifact(self):
    """Check we can run Rekall based artifacts."""
    client_id = self.SetupClient(0, system="Windows")
    # The client should now be populated with the data we care about.
    kb = rdf_client.KnowledgeBase(os="Windows", environ_systemdrive=r"c:")
    if data_store.RelationalDBReadEnabled():
      client = data_store.REL_DB.ReadClientSnapshot(client_id.Basename())
      client.knowledge_base = kb
      data_store.REL_DB.WriteClientSnapshot(client)
    else:
      with aff4.FACTORY.Open(client_id, mode="rw", token=self.token) as fd:
        fd.Set(fd.Schema.KNOWLEDGE_BASE, kb)

    with test_lib.ConfigOverrider({
        "Rekall.enabled":
            True,
        "Rekall.profile_server":
            rekall_test_lib.TestRekallRepositoryProfileServer.__name__
    }):
      fd = self.RunCollectorAndGetCollection(["FullVADBinaryList"],
                                             RekallMock(
                                                 client_id,
                                                 "rekall_vad_result.dat.gz"),
                                             client_id=client_id)

    self.assertLen(fd, 1705)
    self.assertEqual(fd[0].path, u"c:\\Windows\\System32\\ntdll.dll")
    for x in fd:
      self.assertEqual(x.pathtype, "OS")
      extension = x.path.lower().split(".")[-1]
      self.assertIn(extension, ["exe", "dll", "pyd", "drv", "mui", "cpl"])


class GrrKbTest(ArtifactTest):

  def _RunKBI(self, **kw):
    session_id = flow_test_lib.TestFlowHelper(
        artifact.KnowledgeBaseInitializationFlow.__name__,
        self.client_mock,
        client_id=test_lib.TEST_CLIENT_ID,
        token=self.token,
        **kw)

    results = flow_test_lib.GetFlowResults(test_lib.TEST_CLIENT_ID, session_id)
    self.assertLen(results, 1)
    return results[0]


@db_test_lib.DualDBTest
class GrrKbWindowsTest(GrrKbTest):

  def setUp(self):
    super(GrrKbWindowsTest, self).setUp()
    self.SetupClient(0, system="Windows", os_version="6.2", arch="AMD64")

    self.os_overrider = vfs_test_lib.VFSOverrider(
        rdf_paths.PathSpec.PathType.OS, vfs_test_lib.FakeFullVFSHandler)
    self.reg_overrider = vfs_test_lib.VFSOverrider(
        rdf_paths.PathSpec.PathType.REGISTRY,
        vfs_test_lib.FakeRegistryVFSHandler)
    self.os_overrider.Start()
    self.reg_overrider.Start()

  def tearDown(self):
    super(GrrKbWindowsTest, self).tearDown()
    try:
      self.os_overrider.Stop()
      self.reg_overrider.Stop()
    except AttributeError:
      pass

  @parser_test_lib.WithAllParsers
  def testKnowledgeBaseRetrievalWindows(self):
    """Check we can retrieve a knowledge base from a client."""
    kb = self._RunKBI()

    self.assertEqual(kb.environ_systemroot, "C:\\Windows")
    self.assertEqual(kb.time_zone, "US/Alaska")
    self.assertEqual(kb.code_page, "cp_1252")

    self.assertEqual(kb.environ_windir, "C:\\Windows")
    self.assertEqual(kb.environ_profilesdirectory, "C:\\Users")
    self.assertEqual(kb.environ_allusersprofile, "C:\\Users\\All Users")
    self.assertEqual(kb.environ_allusersappdata, "C:\\ProgramData")
    self.assertEqual(kb.environ_temp, "C:\\Windows\\TEMP")
    self.assertEqual(kb.environ_systemdrive, "C:")

    self.assertCountEqual([x.username for x in kb.users], ["jim", "kovacs"])
    user = kb.GetUser(username="jim")
    self.assertEqual(user.username, "jim")
    self.assertEqual(user.sid, "S-1-5-21-702227068-2140022151-3110739409-1000")

  @parser_test_lib.WithParser("MultiProvide", MultiProvideParser)
  def testKnowledgeBaseMultiProvides(self):
    """Check we can handle multi-provides."""
    # Replace some artifacts with test one that will run the MultiProvideParser.
    self.LoadTestArtifacts()
    with test_lib.ConfigOverrider(
        {"Artifacts.knowledge_base": ["DepsProvidesMultiple"]}):
      kb = self._RunKBI()

      self.assertEqual(kb.environ_temp, "tempvalue")
      self.assertEqual(kb.environ_path, "pathvalue")

  def testGlobRegistry(self):
    """Test that glob works on registry."""
    client_id = test_lib.TEST_CLIENT_ID
    paths = [
        "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows NT"
        "\\CurrentVersion\\ProfileList\\ProfilesDirectory",
        "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows NT"
        "\\CurrentVersion\\ProfileList\\AllUsersProfile"
    ]

    flow_test_lib.TestFlowHelper(
        filesystem.Glob.__name__,
        self.client_mock,
        paths=paths,
        pathtype=rdf_paths.PathSpec.PathType.REGISTRY,
        client_id=client_id,
        token=self.token)
    path = paths[0].replace("\\", "/")

    fd = aff4.FACTORY.Open(
        client_id.Add("registry").Add(path), token=self.token)
    self.assertEqual(fd.__class__.__name__, "VFSFile")
    self.assertEqual(
        fd.Get(fd.Schema.STAT).registry_data.GetValue(), "%SystemDrive%\\Users")

  @parser_test_lib.WithAllParsers
  def testGetKBDependencies(self):
    """Test that KB dependencies are calculated correctly."""
    artifact_registry.REGISTRY.ClearSources()
    try:
      test_artifacts_file = os.path.join(config.CONFIG["Test.data_dir"],
                                         "artifacts", "test_artifacts.json")
      artifact_registry.REGISTRY.AddFileSource(test_artifacts_file)

      with test_lib.ConfigOverrider({
          "Artifacts.knowledge_base": [
              "DepsParent", "DepsDesktop", "DepsHomedir", "DepsWindir",
              "DepsWindirRegex", "DepsControlSet", "FakeArtifact"
          ],
          "Artifacts.knowledge_base_additions": ["DepsHomedir2"],
          "Artifacts.knowledge_base_skip": ["DepsWindir"],
          "Artifacts.knowledge_base_heavyweight": ["FakeArtifact"]
      }):
        args = artifact.KnowledgeBaseInitializationArgs(lightweight=True)
        kb_init = aff4_flows.KnowledgeBaseInitializationFlow(
            None, token=self.token)
        kb_init.args = args
        kb_init.state["all_deps"] = set()
        kb_init.state["awaiting_deps_artifacts"] = []
        kb_init.state["knowledge_base"] = rdf_client.KnowledgeBase(os="Windows")
        no_deps = kb_init.GetFirstFlowsForCollection()

        self.assertCountEqual(no_deps, ["DepsControlSet", "DepsHomedir2"])
        self.assertCountEqual(kb_init.state.all_deps, [
            "users.homedir", "users.desktop", "users.username",
            "environ_windir", "current_control_set"
        ])
        self.assertCountEqual(
            kb_init.state.awaiting_deps_artifacts,
            ["DepsParent", "DepsDesktop", "DepsHomedir", "DepsWindirRegex"])
    finally:
      artifact.ArtifactLoader().RunOnce()

  def _RunKBIFlow(self, artifact_list):
    self.LoadTestArtifacts()
    with test_lib.ConfigOverrider({"Artifacts.knowledge_base": artifact_list}):
      logging.disable(logging.CRITICAL)
      try:
        session_id = flow_test_lib.TestFlowHelper(
            artifact.KnowledgeBaseInitializationFlow.__name__,
            self.client_mock,
            client_id=test_lib.TEST_CLIENT_ID,
            token=self.token)
      finally:
        logging.disable(logging.NOTSET)
    return session_id

  @parser_test_lib.WithAllParsers
  def testKnowledgeBaseNoProvides(self):
    with self.assertRaises(RuntimeError) as context:
      self._RunKBIFlow(["NoProvides"])

    self.assertIn("does not have a provide", context.exception.message)

  def testKnowledgeBaseMultipleProvidesNoDict(self):
    with self.assertRaises(RuntimeError) as context:
      self._RunKBIFlow(["TooManyProvides"])

    self.assertIn("multiple provides clauses", context.exception.message)


@db_test_lib.DualDBTest
class GrrKbLinuxTest(GrrKbTest):

  def setUp(self):
    super(GrrKbLinuxTest, self).setUp()
    self.SetupClient(0, system="Linux", os_version="12.04")

  @parser_test_lib.WithAllParsers
  def testKnowledgeBaseRetrievalLinux(self):
    """Check we can retrieve a Linux kb."""
    with test_lib.ConfigOverrider({
        "Artifacts.knowledge_base": [
            "LinuxWtmp", "NetgroupConfiguration", "LinuxPasswdHomedirs",
            "LinuxRelease"
        ],
        "Artifacts.netgroup_filter_regexes": ["^login$"],
        "Artifacts.netgroup_user_blacklist": ["isaac"]
    }):
      with vfs_test_lib.FakeTestDataVFSOverrider():
        with test_lib.SuppressLogs():
          kb = self._RunKBI()

    self.assertEqual(kb.os_major_version, 14)
    self.assertEqual(kb.os_minor_version, 4)
    # user 1,2,3 from wtmp. yagharek from netgroup.
    self.assertCountEqual([x.username for x in kb.users],
                          ["user1", "user2", "user3", "yagharek"])
    user = kb.GetUser(username="user1")
    self.assertEqual(user.last_logon.AsSecondsSinceEpoch(), 1296552099)
    self.assertEqual(user.homedir, "/home/user1")

  @parser_test_lib.WithAllParsers
  def testKnowledgeBaseRetrievalLinuxPasswd(self):
    """Check we can retrieve a Linux kb."""
    with vfs_test_lib.FakeTestDataVFSOverrider():
      with test_lib.ConfigOverrider({
          "Artifacts.knowledge_base": [
              "LinuxWtmp", "LinuxPasswdHomedirs", "LinuxRelease"
          ],
          "Artifacts.knowledge_base_additions": [],
          "Artifacts.knowledge_base_skip": []
      }):
        with test_lib.SuppressLogs():
          kb = self._RunKBI()

    self.assertEqual(kb.os_major_version, 14)
    self.assertEqual(kb.os_minor_version, 4)
    # user 1,2,3 from wtmp.
    self.assertCountEqual([x.username for x in kb.users],
                          ["user1", "user2", "user3"])
    user = kb.GetUser(username="user1")
    self.assertEqual(user.last_logon.AsSecondsSinceEpoch(), 1296552099)
    self.assertEqual(user.homedir, "/home/user1")

    user = kb.GetUser(username="user2")
    self.assertEqual(user.last_logon.AsSecondsSinceEpoch(), 1296552102)
    self.assertEqual(user.homedir, "/home/user2")

    self.assertFalse(kb.GetUser(username="buguser3"))

  @parser_test_lib.WithAllParsers
  def testKnowledgeBaseRetrievalLinuxNoUsers(self):
    """Cause a users.username dependency failure."""
    with test_lib.ConfigOverrider({
        "Artifacts.knowledge_base": [
            "NetgroupConfiguration", "NssCacheLinuxPasswdHomedirs",
            "LinuxRelease"
        ],
        "Artifacts.netgroup_filter_regexes": ["^doesntexist$"]
    }):
      with vfs_test_lib.FakeTestDataVFSOverrider():
        with test_lib.SuppressLogs():
          kb = self._RunKBI(require_complete=False)

    self.assertEqual(kb.os_major_version, 14)
    self.assertEqual(kb.os_minor_version, 4)
    self.assertCountEqual([x.username for x in kb.users], [])


@db_test_lib.DualDBTest
class GrrKbDarwinTest(GrrKbTest):

  def setUp(self):
    super(GrrKbDarwinTest, self).setUp()
    self.SetupClient(0, system="Darwin", os_version="10.9")

  @parser_test_lib.WithAllParsers
  def testKnowledgeBaseRetrievalDarwin(self):
    """Check we can retrieve a Darwin kb."""
    with test_lib.ConfigOverrider({"Artifacts.knowledge_base": ["MacOSUsers"]}):
      with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                     vfs_test_lib.ClientVFSHandlerFixture):
        kb = self._RunKBI()

    self.assertEqual(kb.os_major_version, 10)
    self.assertEqual(kb.os_minor_version, 9)
    # scalzi from /Users dir listing.
    self.assertCountEqual([x.username for x in kb.users], ["scalzi"])
    user = kb.GetUser(username="scalzi")
    self.assertEqual(user.homedir, "/Users/scalzi")


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
