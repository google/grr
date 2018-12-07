#!/usr/bin/env python
"""Tests the client artifactor collection."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import __builtin__
import glob
import io
import os

from builtins import filter  # pylint: disable=redefined-builtin
import mock
import psutil

from grr_response_client.client_actions import artifact_collector
from grr_response_core import config
from grr_response_core.lib import factory
from grr_response_core.lib import flags
from grr_response_core.lib import parser
from grr_response_core.lib import parsers
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr_response_core.lib.rdfvalues import artifacts as rdf_artifact
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr.test_lib import artifact_test_lib
from grr.test_lib import client_test_lib
from grr.test_lib import osx_launchd_testdata
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib


def GetRequest(source, artifact_name, knowledge_base=None):
  expanded_source = rdf_artifact.ExpandedSource(base_source=source)
  expanded_artifact = rdf_artifact.ExpandedArtifact(
      name=artifact_name, sources=[expanded_source])
  return rdf_artifact.ClientArtifactCollectorArgs(
      artifacts=[expanded_artifact],
      apply_parsers=False,
      knowledge_base=knowledge_base)


class ArtifactCollectorTest(client_test_lib.EmptyActionTest):
  """Test the artifact collection on the client."""

  def setUp(self):
    super(ArtifactCollectorTest, self).setUp()
    self.source_type = rdf_artifact.ArtifactSource.SourceType
    self.test_artifacts_file = os.path.join(config.CONFIG["Test.data_dir"],
                                            "artifacts", "test_artifacts.json")

  def RunArtifactCollector(self, request):
    result = self.RunAction(artifact_collector.ArtifactCollector, request)[0]
    collected_artifact = result.collected_artifacts[0]
    return collected_artifact

  @artifact_test_lib.PatchCleanArtifactRegistry
  def testCommandArtifact(self, registry):
    """Test the basic ExecuteCommand action."""

    client_test_lib.Command("/usr/bin/dpkg", args=["--list"], system="Linux")

    registry.AddFileSource(self.test_artifacts_file)
    artifact = registry.GetArtifact("TestCmdArtifact")
    request = GetRequest(artifact.sources[0], artifact.name)
    collected_artifact = self.RunArtifactCollector(request)
    execute_response = collected_artifact.action_results[0].value

    self.assertEqual(collected_artifact.name, "TestCmdArtifact")
    self.assertGreater(execute_response.time_used, 0)

  def testGRRClientActionGetHostname(self):
    """Test the GRR Client Action GetHostname."""

    source = rdf_artifact.ArtifactSource(
        type=self.source_type.GRR_CLIENT_ACTION,
        attributes={"client_action": "GetHostname"})
    request = GetRequest(source, "TestClientActionArtifact")
    collected_artifact = self.RunArtifactCollector(request)
    for action_result in collected_artifact.action_results:
      value = action_result.value
      self.assertTrue(value.string)

  def testGRRClientActionListProcesses(self):
    """Test the GRR Client Action ListProcesses."""

    def ProcessIter():
      return iter([client_test_lib.MockWindowsProcess()])

    source = rdf_artifact.ArtifactSource(
        type=self.source_type.GRR_CLIENT_ACTION,
        attributes={"client_action": "ListProcesses"})
    request = GetRequest(source, "TestClientActionArtifact")

    with utils.Stubber(psutil, "process_iter", ProcessIter):
      collected_artifact = self.RunArtifactCollector(request)
      value = collected_artifact.action_results[0].value
      self.assertIsInstance(value, rdf_client.Process)
      self.assertEqual(value.pid, 10)

  def testGRRClientActionEnumerateInterfaces(self):
    """Test the GRR Client Action EnumerateInterfaces."""

    source = rdf_artifact.ArtifactSource(
        type=self.source_type.GRR_CLIENT_ACTION,
        attributes={"client_action": "EnumerateInterfaces"})
    request = GetRequest(source, "TestClientActionArtifact")

    collected_artifact = self.RunArtifactCollector(request)

    self.assertGreater(len(collected_artifact.action_results), 0)
    for action_result in collected_artifact.action_results:
      value = action_result.value
      self.assertIsInstance(value, rdf_client_network.Interface)

  def testGRRClientActionEnumerateUsers(self):
    """Test the GRR Client Action EnumerateUsers."""

    def MockedOpen(requested_path, mode="rb"):
      try:
        fixture_path = os.path.join(self.base_path, "VFSFixture",
                                    requested_path.lstrip("/"))
        return __builtin__.open.old_target(fixture_path, mode)
      except IOError:
        return __builtin__.open.old_target(requested_path, mode)

    source = rdf_artifact.ArtifactSource(
        type=self.source_type.GRR_CLIENT_ACTION,
        attributes={"client_action": "EnumerateUsers"})
    request = GetRequest(source, "TestClientActionArtifact")

    with utils.MultiStubber((__builtin__, "open", MockedOpen),
                            (glob, "glob", lambda x: ["/var/log/wtmp"])):
      result = self.RunAction(artifact_collector.ArtifactCollector, request)[0]
      collected_artifact = result.collected_artifacts[0]

      self.assertLen(collected_artifact.action_results, 4)
      for action_result in collected_artifact.action_results:
        value = action_result.value
        self.assertIsInstance(value, rdf_client.User)
        if value.username not in ["user1", "user2", "user3", "utuser"]:
          self.fail("Unexpected user found: %s" % value.username)

      # Test that the users were added to the knowledge base
      self.assertLen(result.knowledge_base.users, 4)
      for user in result.knowledge_base.users:
        self.assertIn(user.username, ["user1", "user2", "user3", "utuser"])

  def testGRRClientActionListNetworkConnections(self):
    """Test the GRR Client Action ListNetworkConnections."""

    source = rdf_artifact.ArtifactSource(
        type=self.source_type.GRR_CLIENT_ACTION,
        attributes={"client_action": "ListNetworkConnections"})
    request = GetRequest(source, "TestClientActionArtifact")

    collected_artifact = self.RunArtifactCollector(request)

    for action_result in collected_artifact.action_results:
      value = action_result.value
      self.assertIsInstance(value, rdf_client_network.NetworkConnection)

  def testGRRClientActionStatFS(self):
    """Test the GRR Client Action StatFS."""

    file_path = os.path.join(self.base_path, "numbers.txt")

    source = rdf_artifact.ArtifactSource(
        type=self.source_type.GRR_CLIENT_ACTION,
        attributes={
            "client_action": "StatFS",
            "action_args": {
                "path_list": [file_path]
            }
        })
    request = GetRequest(source, "TestClientActionArtifact")

    collected_artifact = self.RunArtifactCollector(request)

    self.assertLen(collected_artifact.action_results, 1)
    action_result = collected_artifact.action_results[0].value
    self.assertIsInstance(action_result, rdf_client_fs.Volume)

  def testRegistryValueArtifact(self):
    """Test the basic Registry Value collection."""

    source = rdf_artifact.ArtifactSource(
        type=self.source_type.REGISTRY_VALUE,
        attributes={
            "key_value_pairs": [{
                "key": (r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet"
                        r"\Control\Session Manager"),
                "value":
                    "BootExecute"
            }]
        })
    request = GetRequest(source, "FakeRegistryValue")

    with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.REGISTRY,
                                   vfs_test_lib.FakeRegistryVFSHandler):
      with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                     vfs_test_lib.FakeFullVFSHandler):
        collected_artifact = self.RunArtifactCollector(request)
        file_stat = collected_artifact.action_results[0].value
        self.assertIsInstance(file_stat, rdf_client_fs.StatEntry)
        urn = file_stat.pathspec.AFF4Path(self.SetupClient(0))
        self.assertEndsWith(str(urn), "BootExecute")

  def testRegistryKeyArtifact(self):
    """Test the basic Registry Key collection."""

    source = rdf_artifact.ArtifactSource(
        type=self.source_type.REGISTRY_KEY,
        attributes={
            "keys": [
                r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet"
                r"\Control\Session Manager\*"
            ],
        })
    request = GetRequest(source, "TestRegistryKey")

    with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.REGISTRY,
                                   vfs_test_lib.FakeRegistryVFSHandler):
      with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                     vfs_test_lib.FakeFullVFSHandler):
        collected_artifact = self.RunArtifactCollector(request)
        self.assertLen(collected_artifact.action_results, 1)
        file_stat = collected_artifact.action_results[0].value
        self.assertIsInstance(file_stat, rdf_client_fs.StatEntry)

  def testRegistryNoKeysArtifact(self):
    """Test the basic Registry Key collection."""

    source = rdf_artifact.ArtifactSource(
        type=self.source_type.REGISTRY_KEY, attributes={
            "keys": [],
        })
    request = GetRequest(source, "TestRegistryKey")

    with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.REGISTRY,
                                   vfs_test_lib.FakeRegistryVFSHandler):
      with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                     vfs_test_lib.FakeFullVFSHandler):
        collected_artifact = self.RunArtifactCollector(request)
        self.assertEmpty(collected_artifact.action_results)

  def testDirectoryArtifact(self):
    """Test the source type `DIRECTORY`."""

    paths = [
        os.path.join(self.base_path, "%%Users.username%%*"),
        os.path.join(self.base_path, "VFSFixture", "var", "*", "wtmp")
    ]
    expected = [
        os.path.join(self.base_path, "test.plist"),
        os.path.join(self.base_path, "test_img.dd"),
        os.path.join(self.base_path, "tests"),
        os.path.join(self.base_path, "tests_long"),
        os.path.join(self.base_path, "syslog"),
        os.path.join(self.base_path, "syslog_compress.gz"),
        os.path.join(self.base_path, "syslog_false.gz"),
        os.path.join(self.base_path, "VFSFixture", "var", "log", "wtmp"),
    ]
    source = rdf_artifact.ArtifactSource(
        type=self.source_type.DIRECTORY, attributes={"paths": paths})
    knowledge_base = rdf_client.KnowledgeBase(users=[
        rdf_client.User(username="test"),
        rdf_client.User(username="syslog")
    ])
    request = GetRequest(source, "TestDirectory", knowledge_base)

    collected_artifact = self.RunArtifactCollector(request)
    self.assertGreater(len(collected_artifact.action_results), 0)

    for file_stat in collected_artifact.action_results:
      self.assertIsInstance(file_stat.value, rdf_client_fs.StatEntry)
      self.assertIn(file_stat.value.pathspec.path, expected)

  def testGrepArtifact(self):
    """Test the source type `GREP`."""

    paths = [
        os.path.join(self.base_path, "searching", "dpkg.log"),
        os.path.join(self.base_path, "searching", "dpkg_false.log"),
        os.path.join(self.base_path, "searching", "auth.log")
    ]
    content_regex_list = [r"mydo....\.com"]
    source = rdf_artifact.ArtifactSource(
        type=self.source_type.GREP,
        attributes={
            "paths": paths,
            "content_regex_list": content_regex_list
        })
    request = GetRequest(source, "TestGrep")

    collected_artifact = self.RunArtifactCollector(request)
    self.assertLen(collected_artifact.action_results, 1)
    result = collected_artifact.action_results[0].value
    self.assertIsInstance(result, rdf_client_fs.StatEntry)
    self.assertEndsWith(result.pathspec.path, "auth.log")

  @artifact_test_lib.PatchCleanArtifactRegistry
  def testMultipleArtifacts(self, registry):
    """Test collecting multiple artifacts."""

    client_test_lib.Command("/usr/bin/dpkg", args=["--list"], system="Linux")

    registry.AddFileSource(self.test_artifacts_file)
    artifact = registry.GetArtifact("TestCmdArtifact")
    ext_src = rdf_artifact.ExpandedSource(base_source=artifact.sources[0])
    ext_art = rdf_artifact.ExpandedArtifact(
        name=artifact.name, sources=[ext_src])
    request = rdf_artifact.ClientArtifactCollectorArgs(
        artifacts=[ext_art], apply_parsers=False)
    request.artifacts.append(ext_art)
    result = self.RunAction(artifact_collector.ArtifactCollector, request)[0]
    collected_artifacts = list(result.collected_artifacts)
    self.assertLen(collected_artifacts, 2)
    self.assertEqual(collected_artifacts[0].name, "TestCmdArtifact")
    self.assertEqual(collected_artifacts[1].name, "TestCmdArtifact")
    execute_response_1 = collected_artifacts[0].action_results[0].value
    execute_response_2 = collected_artifacts[1].action_results[0].value
    self.assertGreater(execute_response_1.time_used, 0)
    self.assertGreater(execute_response_2.time_used, 0)

  @artifact_test_lib.PatchCleanArtifactRegistry
  def testFilterRequestedArtifactResults(self, registry):
    """Test that only artifacts requested by the user are sent to the server."""

    client_test_lib.Command("/usr/bin/dpkg", args=["--list"], system="Linux")

    registry.AddFileSource(self.test_artifacts_file)
    artifact = registry.GetArtifact("TestCmdArtifact")
    ext_src = rdf_artifact.ExpandedSource(base_source=artifact.sources[0])
    ext_art = rdf_artifact.ExpandedArtifact(
        name=artifact.name, sources=[ext_src])
    request = rdf_artifact.ClientArtifactCollectorArgs(
        artifacts=[ext_art], apply_parsers=False)
    ext_art = rdf_artifact.ExpandedArtifact(
        name=artifact.name, sources=[ext_src], requested_by_user=False)
    request.artifacts.append(ext_art)
    result = self.RunAction(artifact_collector.ArtifactCollector, request)[0]
    collected_artifacts = list(result.collected_artifacts)
    self.assertLen(collected_artifacts, 1)
    self.assertEqual(collected_artifacts[0].name, "TestCmdArtifact")
    execute_response = collected_artifacts[0].action_results[0].value
    self.assertGreater(execute_response.time_used, 0)

  @artifact_test_lib.PatchCleanArtifactRegistry
  def testTSKRaiseValueError(self, registry):
    """Test Raise Error if path type is not OS."""

    registry.AddFileSource(self.test_artifacts_file)

    ext_src = rdf_artifact.ExpandedSource(
        path_type=rdf_paths.PathSpec.PathType.TSK)
    ext_art = rdf_artifact.ExpandedArtifact(
        name="TestArtifact", sources=[ext_src])
    request = rdf_artifact.ClientArtifactCollectorArgs(
        artifacts=[ext_art], apply_parsers=False)

    artifact = registry.GetArtifact("FakeFileArtifact")
    ext_src.base_source = artifact.sources[0]
    with self.assertRaises(ValueError):
      self.RunAction(artifact_collector.ArtifactCollector, request)

    artifact = registry.GetArtifact("BadPathspecArtifact")
    ext_src.base_source = artifact.sources[0]
    with self.assertRaises(ValueError):
      self.RunAction(artifact_collector.ArtifactCollector, request)

  @artifact_test_lib.PatchCleanArtifactRegistry
  def testUnsupportedSourceType(self, registry):
    """Test that an unsupported source type raises an Error."""

    registry.AddFileSource(self.test_artifacts_file)
    artifact = registry.GetArtifact("TestAggregationArtifact")

    ext_src = rdf_artifact.ExpandedSource(base_source=artifact.sources[0])
    ext_art = rdf_artifact.ExpandedArtifact(
        name=artifact.name, sources=[ext_src])
    request = rdf_artifact.ClientArtifactCollectorArgs(
        artifacts=[ext_art],
        knowledge_base=None,
        ignore_interpolation_errors=True,
        apply_parsers=False)

    # The type ARTIFACT_GROUP will raise an error because the group should have
    # been expanded on the server.
    with self.assertRaises(ValueError):
      self.RunAction(artifact_collector.ArtifactCollector, request)


class OSXArtifactCollectorTests(client_test_lib.OSSpecificClientTests):

  def setUp(self):
    super(OSXArtifactCollectorTests, self).setUp()
    # pylint: disable=g-import-not-at-top
    from grr_response_client.client_actions import operating_system
    from grr_response_client.client_actions.osx import osx
    # pylint: enable=g-import-not-at-top
    self.os = operating_system
    self.osx = osx
    self.source_type = rdf_artifact.ArtifactSource.SourceType

  def EnumerateFilesystemsStub(self, args):
    del args  # Unused.
    path = os.path.join(self.base_path, "osx_fsdata")
    with io.open(path, "rb") as f:
      filesystems = self.osx.client_utils_osx.ParseFileSystemsStruct(
          self.osx.client_utils_osx.StatFS64Struct, 7, f.read())
    for fs_struct in filesystems:
      yield rdf_client_fs.Filesystem(
          device=fs_struct.f_mntfromname,
          mount_point=fs_struct.f_mntonname,
          type=fs_struct.f_fstypename)

  def OSXEnumerateRunningServicesStub(self, args):
    del args  # Unused.
    job = osx_launchd_testdata.JOB[0]
    yield rdf_client.OSXServiceInformation(
        label=job.get("Label"),
        program=job.get("Program"),
        sessiontype=job.get("LimitLoadToSessionType"),
        lastexitstatus=int(job["LastExitStatus"]),
        timeout=int(job["TimeOut"]),
        ondemand=bool(job["OnDemand"]))

  def testGRRClientActionEnumerateFilesystems(self):
    """Test the GRR Client Action EnumerateFilesystems."""

    source = rdf_artifact.ArtifactSource(
        type=self.source_type.GRR_CLIENT_ACTION,
        attributes={"client_action": "EnumerateFilesystems"})
    request = GetRequest(source, "TestClientActionArtifact")

    with utils.Stubber(self.os, "EnumerateFilesystemsFromClient",
                       self.EnumerateFilesystemsStub):
      result = self.RunAction(artifact_collector.ArtifactCollector, request)[0]
      collected_artifact = result.collected_artifacts[0]

      self.assertLen(collected_artifact.action_results, 7)

      res = collected_artifact.action_results[0].value
      self.assertIsInstance(res, rdf_client_fs.Filesystem)
      self.assertEqual(res.type, "hfs")

  def testGRRClientActionOSXEnumerateRunningServices(self):
    """Test the GRR Client Action OSXEnumerateRunningServices."""

    source = rdf_artifact.ArtifactSource(
        type=self.source_type.GRR_CLIENT_ACTION,
        attributes={"client_action": "OSXEnumerateRunningServices"})
    request = GetRequest(source, "TestClientActionArtifact")

    with utils.Stubber(self.os, "EnumerateRunningServices",
                       self.OSXEnumerateRunningServicesStub):
      result = self.RunAction(artifact_collector.ArtifactCollector, request)[0]
      collected_artifact = result.collected_artifacts[0]

      self.assertLen(collected_artifact.action_results, 1)

      res = collected_artifact.action_results[0].value
      self.assertIsInstance(res, rdf_client.OSXServiceInformation)
      self.assertEqual(res.label, "com.apple.FileSyncAgent.PHD")


class WindowsArtifactCollectorTests(client_test_lib.OSSpecificClientTests):

  def setUp(self):
    super(WindowsArtifactCollectorTests, self).setUp()
    self.test_artifacts_file = os.path.join(config.CONFIG["Test.data_dir"],
                                            "artifacts", "test_artifacts.json")

    windows_mock = mock.MagicMock()
    modules = {
        ("grr_response_client.client_actions"
         ".windows"):
            windows_mock
    }

    self.module_patcher = mock.patch.dict("sys.modules", modules)
    self.module_patcher.start()

    self.windows = windows_mock.windows

  def tearDown(self):
    super(WindowsArtifactCollectorTests, self).tearDown()
    self.module_patcher.stop()

  @artifact_test_lib.PatchCleanArtifactRegistry
  def testWMIArtifact(self, registry):
    """Test collecting a WMI artifact."""

    registry.AddFileSource(self.test_artifacts_file)
    artifact = registry.GetArtifact("WMIActiveScriptEventConsumer")

    ext_src = rdf_artifact.ExpandedSource(base_source=artifact.sources[0])
    ext_art = rdf_artifact.ExpandedArtifact(
        name=artifact.name, sources=[ext_src])
    request = rdf_artifact.ClientArtifactCollectorArgs(
        artifacts=[ext_art],
        knowledge_base=None,
        ignore_interpolation_errors=True,
        apply_parsers=False)
    result = self.RunAction(artifact_collector.ArtifactCollector, request)[0]
    self.assertIsInstance(result, rdf_artifact.ClientArtifactCollectorResult)

    coll = artifact_collector.ArtifactCollector()
    coll.knowledge_base = None
    coll.ignore_interpolation_errors = True

    expected = rdf_client_action.WMIRequest(
        query="SELECT * FROM ActiveScriptEventConsumer",
        base_object="winmgmts:\\root\\subscription")

    for action, request in coll._ProcessWmiSource(ext_src):
      self.assertEqual(request, expected)
      self.assertEqual(action, self.windows.WmiQueryFromClient)
      self.windows.WmiQueryFromClient.assert_called_with(request)


class TestEchoCmdParser(parser.CommandParser):

  output_types = ["SoftwarePackage"]
  supported_artifacts = ["TestEchoCmdArtifact"]

  def Parse(self, cmd, args, stdout, stderr, return_val, time_taken,
            knowledge_base):
    del cmd, args, stderr, return_val, time_taken, knowledge_base  # Unused
    installed = rdf_client.SoftwarePackage.InstallState.INSTALLED
    soft = rdf_client.SoftwarePackage(
        name="Package",
        description=stdout,
        version="1",
        architecture="amd64",
        install_state=installed)
    yield soft


class FakeFileParser(parser.FileParser):

  output_types = ["AttributedDict"]
  supported_artifacts = ["FakeFileArtifact"]

  def Parse(self, stat, file_obj, knowledge_base):

    del knowledge_base  # Unused.

    lines = set(l.strip() for l in file_obj.read().splitlines())

    users = list(filter(None, lines))

    filename = stat.pathspec.path
    cfg = {"filename": filename, "users": users}

    yield rdf_protodict.AttributedDict(**cfg)


class FakeFileMultiParser(parser.FileMultiParser):

  output_types = ["AttributedDict"]
  supported_artifacts = ["FakeFileArtifact2"]

  def ParseMultiple(self, stats, file_objects, knowledge_base):

    del knowledge_base  # Unused.

    lines = set()
    for file_obj in file_objects:
      lines.update(set(l.strip() for l in file_obj.read().splitlines()))

    users = list(filter(None, lines))

    for stat in stats:
      filename = stat.pathspec.path
      cfg = {"filename": filename, "users": users}

      yield rdf_protodict.AttributedDict(**cfg)


class ParseResponsesTest(client_test_lib.EmptyActionTest):

  @mock.patch.object(parsers, "SINGLE_RESPONSE_PARSER_FACTORY",
                     factory.Factory(parser.SingleResponseParser))
  def testCmdArtifactAction(self):
    """Test the actual client action with parsers."""
    parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register("Cmd", TestEchoCmdParser)

    client_test_lib.Command("/bin/echo", args=["1"])

    source = rdf_artifact.ArtifactSource(
        type=rdf_artifact.ArtifactSource.SourceType.COMMAND,
        attributes={
            "cmd": "/bin/echo",
            "args": ["1"]
        })
    ext_src = rdf_artifact.ExpandedSource(base_source=source)
    ext_art = rdf_artifact.ExpandedArtifact(
        name="TestEchoCmdArtifact", sources=[ext_src])
    request = rdf_artifact.ClientArtifactCollectorArgs(
        artifacts=[ext_art],
        knowledge_base=None,
        ignore_interpolation_errors=True,
        apply_parsers=True)
    result = self.RunAction(artifact_collector.ArtifactCollector, request)[0]
    self.assertIsInstance(result, rdf_artifact.ClientArtifactCollectorResult)
    self.assertLen(result.collected_artifacts, 1)
    res = result.collected_artifacts[0].action_results[0].value
    self.assertIsInstance(res, rdf_client.SoftwarePackage)
    self.assertEqual(res.description, "1\n")

  @mock.patch.object(parsers, "SINGLE_FILE_PARSER_FACTORY",
                     factory.Factory(parser.SingleFileParser))
  def testFakeFileArtifactAction(self):
    """Test collecting a file artifact and parsing the response."""
    parsers.SINGLE_FILE_PARSER_FACTORY.Register("Fake", FakeFileParser)

    file_path = os.path.join(self.base_path, "numbers.txt")
    source = rdf_artifact.ArtifactSource(
        type=rdf_artifact.ArtifactSource.SourceType.FILE,
        attributes={"paths": [file_path]})

    ext_src = rdf_artifact.ExpandedSource(base_source=source)
    ext_art = rdf_artifact.ExpandedArtifact(
        name="FakeFileArtifact", sources=[ext_src])
    request = rdf_artifact.ClientArtifactCollectorArgs(
        artifacts=[ext_art],
        knowledge_base=None,
        ignore_interpolation_errors=True,
        apply_parsers=True)
    result = self.RunAction(artifact_collector.ArtifactCollector, request)[0]
    self.assertLen(result.collected_artifacts[0].action_results, 1)
    res = result.collected_artifacts[0].action_results[0].value
    self.assertIsInstance(res, rdf_protodict.AttributedDict)
    self.assertLen(res.users, 1000)
    self.assertEqual(res.filename, file_path)

  @mock.patch.object(parsers, "MULTI_FILE_PARSER_FACTORY",
                     factory.Factory(parser.MultiFileParser))
  def testFakeFileArtifactActionProcessTogether(self):
    """Test collecting a file artifact and parsing the responses together."""
    parsers.MULTI_FILE_PARSER_FACTORY.Register("Fake", FakeFileMultiParser)

    file_path = os.path.join(self.base_path, "numbers.txt")
    source = rdf_artifact.ArtifactSource(
        type=rdf_artifact.ArtifactSource.SourceType.FILE,
        attributes={"paths": [file_path]})

    ext_src = rdf_artifact.ExpandedSource(base_source=source)
    ext_art = rdf_artifact.ExpandedArtifact(
        name="FakeFileArtifact2", sources=[ext_src])
    request = rdf_artifact.ClientArtifactCollectorArgs(
        artifacts=[ext_art],
        knowledge_base=None,
        ignore_interpolation_errors=True,
        apply_parsers=True)
    result = self.RunAction(artifact_collector.ArtifactCollector, request)[0]
    self.assertLen(result.collected_artifacts[0].action_results, 1)
    res = result.collected_artifacts[0].action_results[0].value
    self.assertIsInstance(res, rdf_protodict.AttributedDict)
    self.assertLen(res.users, 1000)
    self.assertEqual(res.filename, file_path)


class KnowledgeBaseUpdateTest(client_test_lib.EmptyActionTest):

  def InitializeRequest(self, initial_knowledge_base=None, provides=None):
    """Prepare ClientArtifactCollectorArgs."""
    expanded_source = rdf_artifact.ExpandedSource()
    expanded_artifact = rdf_artifact.ExpandedArtifact(
        name="EmptyArtifact", sources=[expanded_source], provides=provides)
    return rdf_artifact.ClientArtifactCollectorArgs(
        artifacts=[expanded_artifact], knowledge_base=initial_knowledge_base)

  def GetUpdatedKnowledgeBase(self):
    """Runs the artifact collector with the specified client action result."""
    with utils.Stubber(artifact_collector.ArtifactCollector, "_ProcessSources",
                       self.GetActionResult):
      result = self.RunAction(artifact_collector.ArtifactCollector,
                              self.request)[0]
    return result.knowledge_base

  def GetActionResult(self, *args):
    del args  # Unused.
    yield [self.response]

  def testAnomaly(self):
    """Test the knowledge base stays uninitialized if an anomaly is returned."""
    self.request = self.InitializeRequest()
    self.response = rdf_anomaly.Anomaly()
    knowledge_base = self.GetUpdatedKnowledgeBase()
    self.assertEqual(knowledge_base, rdf_client.KnowledgeBase())

  def testAddUser(self):
    """Test a user response is added to the knowledge_base."""
    self.request = self.InitializeRequest()
    self.response = rdf_client.User(username="user1", homedir="/home/foo")
    knowledge_base = self.GetUpdatedKnowledgeBase()
    self.assertLen(knowledge_base.users, 1)
    user = knowledge_base.users[0]
    self.assertEqual(user.username, "user1")
    self.assertEqual(user.homedir, "/home/foo")

  def testUpdateUser(self):
    """Test a user response is updated if present in the knowledge base."""
    user = rdf_client.User(username="user1")
    initial_knowledge_base = rdf_client.KnowledgeBase(users=[user])
    self.request = self.InitializeRequest(initial_knowledge_base)
    self.response = rdf_client.User(username="user1", homedir="/home/foo")
    knowledge_base = self.GetUpdatedKnowledgeBase()
    self.assertLen(knowledge_base.users, 1)
    user = knowledge_base.users[0]
    self.assertEqual(user.username, "user1")
    self.assertEqual(user.homedir, "/home/foo")

  def testProvidesMultiple(self):
    """Test provides values are updated from a dictionary."""
    provides = ["domain", "current_control_set"]
    self.request = self.InitializeRequest(provides=provides)
    self.response = rdf_protodict.Dict(
        domain="MICROSOFT",
        current_control_set="HKEY_LOCAL_MACHINE\\SYSTEM\\ControlSet001",
        environ_systemdrive="C:")
    knowledge_base = self.GetUpdatedKnowledgeBase()
    self.assertEqual(knowledge_base.domain, "MICROSOFT")
    self.assertEqual(knowledge_base.current_control_set,
                     "HKEY_LOCAL_MACHINE\\SYSTEM\\ControlSet001")
    self.assertEqual(knowledge_base.environ_systemdrive, "")

  def testProvidesSingleValue(self):
    """Test a single provides value is updated from registry data."""
    provides = ["code_page"]
    self.request = self.InitializeRequest(provides=provides)
    self.response = rdf_client_fs.StatEntry(
        registry_data=rdf_protodict.DataBlob(string="value1"))
    knowledge_base = self.GetUpdatedKnowledgeBase()
    self.assertEqual(knowledge_base.code_page, "value1")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
