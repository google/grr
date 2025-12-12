#!/usr/bin/env python
import io
import os
import re
from typing import Iterable, Iterator, Optional

from absl import app

from grr_response_client import actions
from grr_response_client.client_actions import file_fingerprint
from grr_response_client.client_actions import searching
from grr_response_client.client_actions import standard
from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import mig_client_action
from grr_response_core.lib.rdfvalues import mig_client_fs
from grr_response_core.lib.rdfvalues import mig_file_finder
from grr_response_core.lib.rdfvalues import mig_protodict
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import knowledge_base_pb2
from grr_response_proto import objects_pb2
from grr_response_server import action_registry
from grr_response_server import artifact
from grr_response_server import artifact_registry
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server import server_stubs
from grr_response_server.databases import db
from grr_response_server.databases import db_test_utils
from grr_response_server.flows.general import collectors
from grr.test_lib import action_mocks
from grr.test_lib import artifact_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import rrg_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib
from grr_response_proto import rrg_pb2
from grr_response_proto.rrg import winreg_pb2 as rrg_winreg_pb2
from grr_response_proto.rrg.action import get_winreg_value_pb2 as rrg_get_winreg_value_pb2
from grr_response_proto.rrg.action import grep_file_contents_pb2 as rrg_grep_file_contents_pb2
from grr_response_proto.rrg.action import list_utmp_users_pb2 as rrg_list_utmp_users_pb2
from grr_response_proto.rrg.action import list_winreg_keys_pb2 as rrg_list_winreg_keys_pb2
from grr_response_proto.rrg.action import query_wmi_pb2 as rrg_query_wmi_pb2

# pylint: mode=test

WMI_SAMPLE = [
    rdf_protodict.Dict({
        "Version": "65.61.49216",
        "InstallDate2": "",
        "Name": "Google Chrome",
        "Vendor": "Google, Inc.",
        "Description": "Google Chrome",
        "IdentifyingNumber": "{35790B21-ACFE-33F5-B320-9DA320D96682}",
        "InstallDate": "20130710",
    }),
    rdf_protodict.Dict({
        "Version": "7.0.1",
        "InstallDate2": "",
        "Name": "Parity Agent",
        "Vendor": "Bit9, Inc.",
        "Description": "Parity Agent",
        "IdentifyingNumber": "{ADC7EB41-4CC2-4FBA-8FBE-9338A9FB7666}",
        "InstallDate": "20130710",
    }),
    rdf_protodict.Dict({
        "Version": "8.0.61000",
        "InstallDate2": "",
        "Name": "Microsoft Visual C++ 2005 Redistributable (x64)",
        "Vendor": "Microsoft Corporation",
        "Description": "Microsoft Visual C++ 2005 Redistributable (x64)",
        "IdentifyingNumber": "{ad8a2fa1-06e7-4b0d-927d-6e54b3d3102}",
        "InstallDate": "20130710",
    }),
]


# TODO: These should be defined next to the test they are used in
# once the metaclass registry madness is resolved.

# pylint: disable=function-redefined


class FooAction(server_stubs.ClientActionStub):

  in_rdfvalue = None
  out_rdfvalues = [rdfvalue.RDFString]


action_registry.RegisterAdditionalTestClientAction(FooAction)


class FooAction(actions.ActionPlugin):

  in_rdfvalue = None
  out_rdfvalues = [rdfvalue.RDFString]

  def Run(self, args):
    del args  # Unused.
    self.SendReply(rdfvalue.RDFString("zażółć gęślą jaźń 🎮"))


# pylint: enable=function-redefined


class ArtifactTest(flow_test_lib.FlowTestsBaseclass):
  """Helper class for tests using artifacts."""

  def setUp(self):
    """Make sure things are initialized."""
    super().setUp()
    self.client_mock = action_mocks.ClientFileFinderWithVFS()

    patcher = artifact_test_lib.PatchDefaultArtifactRegistry()
    patcher.start()
    self.addCleanup(patcher.stop)

  def LoadTestArtifacts(self):
    """Add the test artifacts in on top of whatever is in the registry."""
    artifact_registry.REGISTRY.AddFileSource(
        os.path.join(
            config.CONFIG["Test.data_dir"], "artifacts", "test_artifacts.json"
        )
    )

  class MockClient(action_mocks.MemoryClientMock):

    def WmiQuery(self, _):
      return WMI_SAMPLE

  def RunCollectorAndGetResults(
      self,
      artifact_list: Iterable[str],
      client_mock: Optional[action_mocks.ActionMock] = None,
      client_id: Optional[str] = None,
      error_on_no_results: bool = False,
      split_output_by_artifact: bool = False,
  ):
    """Helper to handle running the collector flow."""
    if client_mock is None:
      client_mock = self.MockClient(client_id=client_id)

    session_id = flow_test_lib.StartAndRunFlow(
        collectors.ArtifactCollectorFlow,
        client_mock=client_mock,
        client_id=client_id,
        flow_args=rdf_artifacts.ArtifactCollectorFlowArgs(
            artifact_list=artifact_list,
            error_on_no_results=error_on_no_results,
            split_output_by_artifact=split_output_by_artifact,
        ),
        creator=self.test_username,
    )

    return flow_test_lib.GetFlowResults(client_id, session_id)


class GRRArtifactTest(ArtifactTest):

  def testUploadArtifactYamlFileAndDumpToYaml(self):
    artifact_registry.REGISTRY.ClearRegistry()
    artifact_registry.REGISTRY.ClearSources()
    artifact_registry.REGISTRY._CheckDirty()

    try:

      test_artifacts_file = os.path.join(
          config.CONFIG["Test.data_dir"], "artifacts", "test_artifacts.json"
      )

      with io.open(test_artifacts_file, mode="r", encoding="utf-8") as filedesc:
        artifact.UploadArtifactYamlFile(filedesc.read())
      loaded_artifacts = artifact_registry.REGISTRY.GetArtifacts()
      self.assertGreaterEqual(len(loaded_artifacts), 20)

      artifacts_by_name = {
          artifact.name: artifact for artifact in loaded_artifacts
      }
      self.assertIn("DepsWindir", artifacts_by_name)
      self.assertIn("TestFilesArtifact", artifacts_by_name)
      self.assertStartsWith(
          artifacts_by_name["WMIActiveScriptEventConsumer"].urls[0],
          "https://msdn.microsoft.com/en-us/library/",
      )
      self.assertEqual(
          artifacts_by_name["TestCmdArtifact"].sources[0].attributes["cmd"],
          "/usr/bin/dpkg",
      )
      self.assertEqual(
          artifacts_by_name["TestCmdArtifact"].sources[0].attributes["args"],
          ["--list"],
      )
    finally:
      artifact.LoadArtifactsOnce()

  def testUploadArtifactYamlFileMissingDoc(self):
    content = """name: Nodoc
sources:
- type: PATH
  attributes:
    paths: [/etc/blah]
supported_os: [Linux]
"""
    with self.assertRaises(rdf_artifacts.ArtifactDefinitionError):
      artifact.UploadArtifactYamlFile(content)

  def testUploadArtifactYamlFileBadList(self):
    content = """name: BadList
doc: here's the doc
sources:
- type: PATH
  attributes:
    paths: /etc/blah
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
        name_list=["CommandOrder"]
    ).pop()
    arglist = artifact_obj.sources[0].attributes.get("args")
    self.assertEqual(arglist, ["-L", "-v", "-n"])

    # Check serialize/deserialize doesn't change order.
    serialized = artifact_obj.SerializeToBytes()
    artifact_obj = rdf_artifacts.Artifact.FromSerializedBytes(serialized)
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

    # WMIActiveScriptEventConsumer is a system artifact, we can't overwrite it.
    with self.assertRaises(rdf_artifacts.ArtifactDefinitionError):
      artifact.UploadArtifactYamlFile(content)

    # Override the check and upload anyways. This simulates the case
    # where an artifact ends up shadowing a system artifact somehow -
    # for example when the system artifact was created after the
    # artifact was uploaded to the data store for testing.
    artifact.UploadArtifactYamlFile(content, overwrite_system_artifacts=True)

    # The shadowing artifact is at this point stored in the data store. On the
    # next full reload of the registry, there will be an error that we can't
    # overwrite the system artifact. The artifact should automatically get
    # deleted from the data store to mitigate the problem.
    with self.assertRaises(rdf_artifacts.ArtifactDefinitionError):
      artifact_registry.REGISTRY._ReloadArtifacts()

    # As stated above, now this should work.
    artifact_registry.REGISTRY._ReloadArtifacts()

    # Make sure the artifact is now loaded and it's the version from the file.
    self.assertIn(
        "WMIActiveScriptEventConsumer", artifact_registry.REGISTRY._artifacts
    )
    artifact_obj = artifact_registry.REGISTRY.GetArtifact(
        "WMIActiveScriptEventConsumer"
    )
    self.assertTrue(
        artifact_registry.REGISTRY.IsLoadedFrom(artifact_obj.name, "file:")
    )

    # The artifact is gone from the data store.
    with self.assertRaises(db.UnknownArtifactError):
      data_store.REL_DB.ReadArtifact("WMIActiveScriptEventConsumer")

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


class ArtifactFlowLinuxTest(ArtifactTest):

  def setUp(self):
    """Make sure things are initialized."""
    super().setUp()
    users = [
        knowledge_base_pb2.User(username="gogol"),
        knowledge_base_pb2.User(username="gevulot"),
        knowledge_base_pb2.User(username="exomemory"),
        knowledge_base_pb2.User(username="user1"),
        knowledge_base_pb2.User(username="user2"),
    ]
    self.SetupClient(0, system="Linux", os_version="12.04", users=users)

    self.LoadTestArtifacts()

  def testFilesArtifact(self):
    """Check GetFiles artifacts."""
    client_id = test_lib.TEST_CLIENT_ID
    with vfs_test_lib.FakeTestDataVFSOverrider():
      self.RunCollectorAndGetResults(
          ["TestFilesArtifact"],
          client_mock=action_mocks.ClientFileFinderWithVFS(),
          client_id=client_id,
      )
      cp = db.ClientPath.OS(client_id, ("var", "log", "auth.log"))
      fd = file_store.OpenFile(cp)
      self.assertNotEmpty(fd.read())

  def testArtifactOutput(self):
    """Check we can run command based artifacts."""
    client_id = test_lib.TEST_CLIENT_ID
    with vfs_test_lib.FakeTestDataVFSOverrider():
      # Will raise if something goes wrong.
      self.RunCollectorAndGetResults(
          ["TestFilesArtifact"],
          client_mock=self.client_mock,
          client_id=client_id,
      )

      # Will raise if something goes wrong.
      self.RunCollectorAndGetResults(
          ["TestFilesArtifact"],
          client_mock=self.client_mock,
          client_id=client_id,
          split_output_by_artifact=True,
      )

      # Test the error_on_no_results option.
      with self.assertRaises(RuntimeError) as context:
        with test_lib.SuppressLogs():
          self.RunCollectorAndGetResults(
              ["NullArtifact"],
              client_mock=self.client_mock,
              client_id=client_id,
              split_output_by_artifact=True,
              error_on_no_results=True,
          )
      if "collector returned 0 responses" not in str(context.exception):
        raise RuntimeError("0 responses should have been returned")


class GrrKbTest(ArtifactTest):

  def _RunKBI(self, require_complete: bool = True):
    session_id = flow_test_lib.StartAndRunFlow(
        artifact.KnowledgeBaseInitializationFlow,
        # TODO: remove additional client actions when Glob flow
        # ArtifactCollectorFlow dependency is removed.
        action_mocks.ClientFileFinderWithVFS(
            file_fingerprint.FingerprintFile,
            searching.Find,
            searching.Grep,
            standard.HashBuffer,
            standard.HashFile,
            standard.GetFileStat,
            standard.ListDirectory,
            standard.TransferBuffer,
        ),
        client_id=test_lib.TEST_CLIENT_ID,
        creator=self.test_username,
        flow_args=artifact.KnowledgeBaseInitializationArgs(
            require_complete=require_complete,
        ),
    )

    results = flow_test_lib.GetFlowResults(test_lib.TEST_CLIENT_ID, session_id)
    self.assertLen(results, 1)
    return results[0]


class GrrKbWindowsTest(GrrKbTest):

  def setUp(self):
    super().setUp()
    self.SetupClient(0, system="Windows", os_version="6.2", arch="AMD64")

    os_overrider = vfs_test_lib.VFSOverrider(
        rdf_paths.PathSpec.PathType.OS, vfs_test_lib.FakeFullVFSHandler
    )
    os_overrider.Start()
    self.addCleanup(os_overrider.Stop)

    reg_overrider = vfs_test_lib.VFSOverrider(
        rdf_paths.PathSpec.PathType.REGISTRY,
        vfs_test_lib.FakeRegistryVFSHandler,
    )
    reg_overrider.Start()
    self.addCleanup(reg_overrider.Stop)

  def testKnowledgeBaseRetrievalWindows(self):
    """Check we can retrieve a knowledge base from a client."""
    kb = self._RunKBI()

    self.assertEqual(kb.environ_systemroot, "C:\\Windows")
    self.assertEqual(kb.time_zone, "US/Alaska")
    self.assertEqual(kb.code_page, "cp_1252")

    self.assertEqual(kb.environ_windir, "C:\\Windows")
    self.assertEqual(kb.environ_profilesdirectory, "C:\\Users")
    self.assertEqual(kb.environ_allusersprofile, "C:\\ProgramData")
    self.assertEqual(kb.environ_allusersappdata, "C:\\ProgramData")
    self.assertEqual(kb.environ_temp, "C:\\Windows\\TEMP")
    self.assertEqual(kb.environ_systemdrive, "C:")

    self.assertCountEqual([x.username for x in kb.users], ["jim", "kovacs"])
    user = kb.GetUser(username="jim")
    self.assertEqual(user.username, "jim")
    self.assertEqual(user.sid, "S-1-5-21-702227068-2140022151-3110739409-1000")


class GrrKbLinuxTest(GrrKbTest):

  def setUp(self):
    super().setUp()
    self.SetupClient(0, system="Linux", os_version="12.04")

  def testKnowledgeBaseRetrievalLinux(self):
    """Check we can retrieve a Linux kb."""

    class KnowledgebaseInitMock(action_mocks.FileFinderClientMock):

      def EnumerateUsers(
          self,
          args: None,
      ) -> Iterator[rdf_client.User]:
        del args  # Unused.

        yield rdf_client.User(
            username="user1",
            homedir="/home/user1",
            last_logon=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1296552099),
        )
        yield rdf_client.User(
            username="user2",
            homedir="/home/user2",
            last_logon=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1234567890),
        )
        yield rdf_client.User(
            username="user3",
            homedir="/home/user3",
            last_logon=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3456789012),
        )
        yield rdf_client.User(
            username="yagharek",
            homedir="/home/yagharek",
            last_logon=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(7890123456),
        )

    session_id = flow_test_lib.StartAndRunFlow(
        artifact.KnowledgeBaseInitializationFlow,
        client_id=test_lib.TEST_CLIENT_ID,
        client_mock=KnowledgebaseInitMock(),
    )

    results = flow_test_lib.GetFlowResults(test_lib.TEST_CLIENT_ID, session_id)

    self.assertLen(results, 1)
    self.assertIsInstance(results[0], rdf_client.KnowledgeBase)

    kb = results[0]

    self.assertCountEqual(
        [x.username for x in kb.users], ["user1", "user2", "user3", "yagharek"]
    )
    user = kb.GetUser(username="user1")
    self.assertEqual(user.last_logon.AsSecondsSinceEpoch(), 1296552099)
    self.assertEqual(user.homedir, "/home/user1")

  def testKnowledgeBaseRetrievalLinuxNoUsers(self):
    """Cause a users.username dependency failure."""
    with vfs_test_lib.FakeTestDataVFSOverrider():
      kb = self._RunKBI(require_complete=False)

    self.assertEqual(kb.os_major_version, 14)
    self.assertEqual(kb.os_minor_version, 4)
    self.assertCountEqual([x.username for x in kb.users], [])


class GrrKbDarwinTest(GrrKbTest):

  def setUp(self):
    super().setUp()
    self.SetupClient(0, system="Darwin", os_version="10.9")

  def testKnowledgeBaseRetrievalDarwin(self):
    """Check we can retrieve a Darwin kb."""
    with vfs_test_lib.VFSOverrider(
        rdf_paths.PathSpec.PathType.OS,
        vfs_test_lib.ClientVFSHandlerFixture,
    ):
      kb = self._RunKBI()

    self.assertEqual(kb.os_major_version, 10)
    self.assertEqual(kb.os_minor_version, 9)
    # scalzi from /Users dir listing.
    self.assertCountEqual([x.username for x in kb.users], ["scalzi"])
    user = kb.GetUser(username="scalzi")
    self.assertEqual(user.homedir, "/Users/scalzi")


class KnowledgeBaseInitializationFlowTest(flow_test_lib.FlowTestsBaseclass):

  def testWindowsListUsersDir(self):
    assert data_store.REL_DB is not None
    rel_db: db.Database = data_store.REL_DB

    creator = db_test_utils.InitializeUser(rel_db)
    client_id = db_test_utils.InitializeClient(rel_db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Windows"
    rel_db.WriteClientSnapshot(snapshot)

    class ActionMock(action_mocks.ActionMock):

      def GetFileStat(
          self,
          args: rdf_client_action.GetFileStatRequest,
      ) -> Iterator[rdf_client_fs.StatEntry]:
        args = mig_client_action.ToProtoGetFileStatRequest(args)

        # pylint: disable=line-too-long
        # fmt: off
        if (args.pathspec.pathtype != jobs_pb2.PathSpec.PathType.REGISTRY or
            args.pathspec.path != r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\SystemRoot"):
        # pylint: enable=line-too-long
        # fmt: on
          raise OSError(f"Unsupported path: {args.pathspec}")

        result = jobs_pb2.StatEntry()
        result.registry_type = jobs_pb2.StatEntry.RegistryType.REG_SZ
        result.registry_data.string = "X:\\"
        yield mig_client_fs.ToRDFStatEntry(result)

      def ListDirectory(
          self,
          args: rdf_client_action.ListDirRequest,
      ) -> Iterator[rdf_client_fs.StatEntry]:
        args = mig_client_action.ToProtoListDirRequest(args)

        # fmt: off
        if (args.pathspec.pathtype != jobs_pb2.PathSpec.PathType.OS or
            args.pathspec.path != "X:\\Users"):
        # fmt: on
          raise OSError(f"Unsupported path: {args.pathspec}")

        result = jobs_pb2.StatEntry()
        result.pathspec.pathtype = jobs_pb2.PathSpec.PathType.OS

        result.pathspec.path = "X:\\Users\\Administrator"
        result.st_mode = 0o40777
        yield mig_client_fs.ToRDFStatEntry(result)

        result.pathspec.path = "X:\\Users\\All Users"
        result.st_mode = 0o40777
        yield mig_client_fs.ToRDFStatEntry(result)

        result.pathspec.path = "X:\\Users\\bar"
        result.st_mode = 0o40777
        yield mig_client_fs.ToRDFStatEntry(result)

        result.pathspec.path = "X:\\Users\\baz"
        result.st_mode = 0o40777
        yield mig_client_fs.ToRDFStatEntry(result)

        result.pathspec.path = "X:\\Users\\Default"
        result.st_mode = 0o40555
        yield mig_client_fs.ToRDFStatEntry(result)

        result.pathspec.path = "X:\\Users\\Default User"
        result.st_mode = 0o40555
        yield mig_client_fs.ToRDFStatEntry(result)

        result.pathspec.path = "X:\\Users\\defaultuser0"
        result.st_mode = 0o40777
        yield mig_client_fs.ToRDFStatEntry(result)

        result.pathspec.path = "X:\\Users\\desktop.ini"
        result.st_mode = 0o100666
        yield mig_client_fs.ToRDFStatEntry(result)

        result.pathspec.path = "X:\\Users\\foo"
        result.st_mode = 0o40777
        yield mig_client_fs.ToRDFStatEntry(result)

        result.pathspec.path = "X:\\Users\\Public"
        result.st_mode = 0o40555
        yield mig_client_fs.ToRDFStatEntry(result)

    flow_id = flow_test_lib.StartAndRunFlow(
        artifact.KnowledgeBaseInitializationFlow,
        ActionMock(),
        client_id=client_id,
        creator=creator,
    )

    results = flow_test_lib.GetFlowResults(client_id, flow_id)

    self.assertLen(results, 1)
    self.assertLen(results[0].users, 3)

    users_by_username = {user.username: user for user in results[0].users}

    self.assertIn("foo", users_by_username)
    self.assertEqual(users_by_username["foo"].homedir, "X:\\Users\\foo")

    self.assertIn("bar", users_by_username)
    self.assertEqual(users_by_username["bar"].homedir, "X:\\Users\\bar")

    self.assertIn("baz", users_by_username)
    self.assertEqual(users_by_username["baz"].homedir, "X:\\Users\\baz")

  # TODO: Remove once the `ListDirectory` action is fixed not
  # to yield results with leading slashes on Windows.
  def testWindowsListUsersDirWithForwardAndLeadingSlashes(self):
    assert data_store.REL_DB is not None
    rel_db: db.Database = data_store.REL_DB

    creator = db_test_utils.InitializeUser(rel_db)
    client_id = db_test_utils.InitializeClient(rel_db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Windows"
    rel_db.WriteClientSnapshot(snapshot)

    class ActionMock(action_mocks.ActionMock):

      def GetFileStat(
          self,
          args: rdf_client_action.GetFileStatRequest,
      ) -> Iterator[rdf_client_fs.StatEntry]:
        args = mig_client_action.ToProtoGetFileStatRequest(args)

        # pylint: disable=line-too-long
        # fmt: off
        if (args.pathspec.pathtype != jobs_pb2.PathSpec.PathType.REGISTRY or
            args.pathspec.path != r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\SystemRoot"):
          # pylint: enable=line-too-long
          # fmt: on
          raise OSError(f"Unsupported path: {args.pathspec}")

        result = jobs_pb2.StatEntry()
        result.registry_type = jobs_pb2.StatEntry.RegistryType.REG_SZ
        result.registry_data.string = "X:\\"
        yield mig_client_fs.ToRDFStatEntry(result)

      def ListDirectory(
          self,
          args: rdf_client_action.ListDirRequest,
      ) -> Iterator[rdf_client_fs.StatEntry]:
        args = mig_client_action.ToProtoListDirRequest(args)

        if (
            args.pathspec.pathtype != jobs_pb2.PathSpec.PathType.OS
            or args.pathspec.path != "X:\\Users"
        ):
          raise OSError(f"Unsupported path: {args.pathspec}")

        result = jobs_pb2.StatEntry()
        result.pathspec.pathtype = jobs_pb2.PathSpec.PathType.OS

        result.pathspec.path = "/X:/Users/foobar"
        result.st_mode = 0o40777
        yield mig_client_fs.ToRDFStatEntry(result)

    flow_id = flow_test_lib.StartAndRunFlow(
        artifact.KnowledgeBaseInitializationFlow,
        ActionMock(),
        client_id=client_id,
        creator=creator,
    )

    results = flow_test_lib.GetFlowResults(client_id, flow_id)

    self.assertLen(results, 1)
    self.assertLen(results[0].users, 1)
    self.assertEqual(results[0].users[0].username, "foobar")
    self.assertEqual(results[0].users[0].homedir, "X:\\Users\\foobar")

  def testWindowsWmiUsersQuery(self):
    assert data_store.REL_DB is not None
    rel_db: db.Database = data_store.REL_DB

    creator = db_test_utils.InitializeUser(rel_db)
    client_id = db_test_utils.InitializeClient(rel_db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Windows"
    rel_db.WriteClientSnapshot(snapshot)

    class ActionMock(action_mocks.ActionMock):

      def VfsFileFinder(
          self, args: rdf_file_finder.FileFinderArgs
      ) -> Iterator[rdf_file_finder.FileFinderResult]:
        args = mig_file_finder.ToProtoFileFinderArgs(args)

        if (
            args.action.action_type
            != rdf_file_finder.FileFinderAction.Action.STAT
            or args.pathtype != rdf_paths.PathSpec.PathType.REGISTRY
        ):
          raise OSError("Unsupported arguments")

        if args.paths[0].startswith("HKEY_USERS"):
          # Skip _ProcessWindowsProfileExtras
          return

        result = flows_pb2.FileFinderResult()
        result.stat_entry.registry_type = jobs_pb2.StatEntry.RegistryType.REG_SZ
        result.stat_entry.registry_data.string = "X:\\Users\\foobar"
        result.stat_entry.pathspec.pathtype = (
            jobs_pb2.PathSpec.PathType.REGISTRY
        )
        result.stat_entry.pathspec.path = (
            r"HKEY_LOCAL_MACHINE\Software\Microsoft\Windows"
            r" NT\CurrentVersion\ProfileList\S-1-5-21-702227000-2140022111-3110739999-1990\ProfileImagePath"
        )
        yield mig_file_finder.ToRDFFileFinderResult(result)

      def WmiQuery(
          self, args: rdf_client_action.WMIRequest
      ) -> Iterator[rdf_protodict.Dict]:
        args = mig_client_action.ToProtoWMIRequest(args)

        if not args.query.upper().startswith("SELECT "):
          raise RuntimeError("Non-`SELECT` WMI query")

        result = jobs_pb2.Dict()

        sid_entry = result.dat.add()
        sid_entry.k.string = "SID"
        sid_entry.v.string = "S-1-5-21-702227000-2140022111-3110739999-1990"

        domain_entry = result.dat.add()
        domain_entry.k.string = "Domain"
        domain_entry.v.string = "TestDomain"

        yield mig_protodict.ToRDFDict(result)

    flow_id = flow_test_lib.StartAndRunFlow(
        artifact.KnowledgeBaseInitializationFlow,
        ActionMock(),
        client_id=client_id,
        creator=creator,
        flow_args=artifact.KnowledgeBaseInitializationArgs(
            lightweight=False,
        ),
    )

    results = flow_test_lib.GetFlowResults(client_id, flow_id)

    self.assertLen(results, 1)
    self.assertLen(results[0].users, 1)
    self.assertEqual(results[0].users[0].username, "foobar")
    self.assertEqual(results[0].users[0].homedir, "X:\\Users\\foobar")
    self.assertEqual(
        results[0].users[0].sid, "S-1-5-21-702227000-2140022111-3110739999-1990"
    )
    self.assertEqual(results[0].users[0].userdomain, "TestDomain")

  def testRRGLinux(self):
    assert data_store.REL_DB is not None
    rel_db: db.Database = data_store.REL_DB

    client_id = db_test_utils.InitializeRRGClient(rel_db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    rel_db.WriteClientSnapshot(snapshot)

    def GetFileContentsHandler(session: rrg_test_lib.Session) -> None:
      del session  # Unused.

      # This action is needed by hardware information subflow, we do not care
      # about that data here.
      raise NotImplementedError()

    def ListUtmpUsersHandler(session: rrg_test_lib.Session) -> None:
      args = rrg_list_utmp_users_pb2.Args()
      assert session.args.Unpack(args)

      if args.path.raw_bytes.decode("utf-8") != "/var/log/wtmp":
        raise RuntimeError(f"Unknown path: {args.path!r}")

      result_foo = rrg_list_utmp_users_pb2.Result()
      result_foo.username = "foo".encode("utf-8")
      session.Reply(result_foo)

      result_quux = rrg_list_utmp_users_pb2.Result()
      result_quux.username = "quux".encode("utf-8")
      session.Reply(result_quux)

    def GrepFileContentHandler(session: rrg_test_lib.Session) -> None:
      args = rrg_grep_file_contents_pb2.Args()
      assert session.args.Unpack(args)

      if args.path.raw_bytes.decode("utf-8") == "/etc/passwd":
        content = """\
root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
bin:x:2:2:bin:/bin:/usr/sbin/nologin
sys:x:3:3:sys:/dev:/usr/sbin/nologin
man:x:6:12:man:/var/cache/man:/usr/sbin/nologin
sshd:x:114:65534::/var/run/sshd:/usr/sbin/nologin
"""
      elif args.path.raw_bytes.decode("utf-8") == "/etc/passwd.cache":
        content = """\
foo:x:1337:42:Jan Fóbarski:/home/foo:/bin/bash
bar:x:1338:42:Basia Barbarska:/home/bar:/bin/bash
quux:x:1339:41:Mirosław Kwudzyniak:/home/quux:/bin/bash
"""
      else:
        raise RuntimeError(f"Unknown path: {args.path!r}")

      for line in content.splitlines():
        for match in re.finditer(args.regex, line):
          result = rrg_grep_file_contents_pb2.Result()
          result.offset = match.start()
          result.content = match[0]
          session.Reply(result)

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=artifact.KnowledgeBaseInitializationFlow,
        flow_args=artifact.KnowledgeBaseInitializationArgs(),
        handlers={
            rrg_pb2.Action.GET_FILE_CONTENTS: GetFileContentsHandler,
            rrg_pb2.Action.GREP_FILE_CONTENTS: GrepFileContentHandler,
            rrg_pb2.Action.LIST_UTMP_USERS: ListUtmpUsersHandler,
        },
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=1024)
    self.assertLen(results, 1)

    kb = knowledge_base_pb2.KnowledgeBase()
    self.assertTrue(results[0].payload.Unpack(kb))

    users_by_username = {user.username: user for user in kb.users}
    self.assertLen(users_by_username, 2)

    user_foo = users_by_username["foo"]
    self.assertEqual(user_foo.uid, 1337)
    self.assertEqual(user_foo.gid, 42)
    self.assertEqual(user_foo.full_name, "Jan Fóbarski")
    self.assertEqual(user_foo.homedir, "/home/foo")
    self.assertEqual(user_foo.shell, "/bin/bash")

    user_quux = users_by_username["quux"]
    self.assertEqual(user_quux.uid, 1339)
    self.assertEqual(user_quux.gid, 41)
    self.assertEqual(user_quux.full_name, "Mirosław Kwudzyniak")
    self.assertEqual(user_quux.homedir, "/home/quux")
    self.assertEqual(user_quux.shell, "/bin/bash")

  def testRRGMacos(self):
    assert data_store.REL_DB is not None
    rel_db: db.Database = data_store.REL_DB

    client_id = db_test_utils.InitializeRRGClient(rel_db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Darwin"
    rel_db.WriteClientSnapshot(snapshot)

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=artifact.KnowledgeBaseInitializationFlow,
        flow_args=artifact.KnowledgeBaseInitializationArgs(),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/Users/foo": {},
            "/Users/bar": {},
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=1024)
    self.assertLen(results, 1)

    kb = knowledge_base_pb2.KnowledgeBase()
    self.assertTrue(results[0].payload.Unpack(kb))

    users_by_username = {user.username: user for user in kb.users}
    self.assertLen(users_by_username, 2)

    user_foo = users_by_username["foo"]
    self.assertEqual(user_foo.homedir, "/Users/foo")

    user_bar = users_by_username["bar"]
    self.assertEqual(user_bar.homedir, "/Users/bar")

  def testRRGWindows(self):
    assert data_store.REL_DB is not None
    rel_db: db.Database = data_store.REL_DB

    client_id = db_test_utils.InitializeRRGClient(rel_db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Windows"
    rel_db.WriteClientSnapshot(snapshot)

    def GetWinregValueHandler(session: rrg_test_lib.Session) -> None:
      args = rrg_get_winreg_value_pb2.Args()
      assert session.args.Unpack(args)

      # pylint: disable=line-too-long
      # fmt: off
      value = {
          rrg_winreg_pb2.LOCAL_MACHINE: {
              r"SOFTWARE\Microsoft\Windows\CurrentVersion": {
                  "CommonFilesDir": rrg_winreg_pb2.Value(
                      string=r"C:\Program Files\Common Files",
                  ),
                  "CommonFilesDir (x86)": rrg_winreg_pb2.Value(
                      string=r"C:\Program Files (x86)\Common Files",
                  ),
                  "ProgramFilesDir": rrg_winreg_pb2.Value(
                      string=r"C:\Program Files",
                  ),
                  "ProgramFilesDir (x86)": rrg_winreg_pb2.Value(
                      string=r"C:\Program Files (x86)",
                  ),
              },
              r"SOFTWARE\Microsoft\Windows NT\CurrentVersion": {
                  "SystemRoot": rrg_winreg_pb2.Value(
                      string=r"C:\Windows",
                  ),
              },
              r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList": {
                  # `AllUsersProfile` is not supported since Windows Vista but
                  # we provide it here to have good code coverage.
                  "AllUsersProfile": rrg_winreg_pb2.Value(
                      string=r"C:\ProgramData",
                  ),
                  "ProfilesDirectory": rrg_winreg_pb2.Value(
                      expand_string=r"%SystemDrive%\Users",
                  ),
                  "ProgramData": rrg_winreg_pb2.Value(
                      expand_string=r"%SystemDrive%\ProgramData",
                  ),
              },
              r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\S-1-5-21-11112222-3333344444-555556666-777888": {
                  "ProfileImagePath": rrg_winreg_pb2.Value(
                      expand_string=r"C:\Users\foobar",
                  ),
              },
              r"SYSTEM\CurrentControlSet\Control\Nls\CodePage": {
                  "ACP": rrg_winreg_pb2.Value(
                      string="1252",
                  ),
              },
              r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment": {
                  "ComSpec": rrg_winreg_pb2.Value(
                      expand_string=r"%SystemRoot%\system32\cmd.exe",
                  ),
                  "DriverData": rrg_winreg_pb2.Value(
                      string=r"C:\Windows\System32\Drivers\DriverData",
                  ),
                  "Path": rrg_winreg_pb2.Value(
                      string=r"C:\Windows\system32;C:\Windows",
                  ),
                  "TEMP": rrg_winreg_pb2.Value(
                      expand_string=r"%SystemRoot%\TEMP",
                  ),
                  "windir": rrg_winreg_pb2.Value(
                      expand_string=r"%SystemRoot%",
                  ),
              },
              r"SYSTEM\CurrentControlSet\Control\TimeZoneInformation": {
                  "TimeZoneKeyName": rrg_winreg_pb2.Value(
                      string=r"Pacific Standard Time",
                  ),
              },
              r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters": {
                  "Domain": rrg_winreg_pb2.Value(
                      string="ad.example.com",
                  ),
              },
              r"SYSTEM\Select": {
                  "Current": rrg_winreg_pb2.Value(
                      uint32=0x00000001,
                  ),
              },
          },
          rrg_winreg_pb2.USERS: {
              r"S-1-5-21-11112222-3333344444-555556666-777888\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders": {
                  "{A520A1A4-1780-4FF6-BD18-167343C5AF16}": rrg_winreg_pb2.Value(
                      string=r"C:\Users\foobar\AppData\LocalLow",
                  ),
                  "Desktop": rrg_winreg_pb2.Value(
                      string=r"C:\Users\foobar\Desktop",
                  ),
                  "AppData": rrg_winreg_pb2.Value(
                      string=r"C:\Users\foobar\AppData\Roaming",
                  ),
                  "Local AppData": rrg_winreg_pb2.Value(
                      string=r"C:\Users\foobar\AppData\Local",
                  ),
                  "Cookies": rrg_winreg_pb2.Value(
                      string=r"C:\Users\foobar\AppData\Local\Microsoft\Windows\INetCookies",
                  ),
                  "Cache": rrg_winreg_pb2.Value(
                      string=r"C:\Users\foobar\AppData\Local\Microsoft\Windows\INetCache",
                  ),
                  "Recent": rrg_winreg_pb2.Value(
                      string=r"C:\Users\foobar\AppData\Roaming\Microsoft\Windows\Recent",
                  ),
                  "Startup": rrg_winreg_pb2.Value(
                      string=r"C:\Users\foobar\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup",
                  ),
                  "Personal": rrg_winreg_pb2.Value(
                      string=r"C:\Users\foobar\Documents",
                  ),
              },
              r"S-1-5-21-11112222-3333344444-555556666-777888\Environment": {
                  "TEMP": rrg_winreg_pb2.Value(
                      expand_string=r"%USERPROFILE%\AppData\Local\Temp",
                  ),
              },
              r"S-1-5-21-11112222-3333344444-555556666-777888\Volatile Environment": {
                  "USERDOMAIN": rrg_winreg_pb2.Value(
                      string=r"GOOGLE",
                  ),
              },
          },
      }[args.root][args.key][args.name]
      # pylint: enable=line-too-long
      # fmt: on

      result = rrg_get_winreg_value_pb2.Result()
      result.root = args.root
      result.key = args.key
      result.value.name = args.name
      result.value.MergeFrom(value)
      session.Reply(result)

    def ListWinregKeysHandler(session: rrg_test_lib.Session) -> None:
      args = rrg_list_winreg_keys_pb2.Args()
      assert session.args.Unpack(args)

      subkeys = {
          rrg_winreg_pb2.LOCAL_MACHINE: {
              r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList": [
                  "S-1-5-18",
                  "S-1-5-19",
                  "S-1-5-20",
                  "S-1-5-21-11112222-3333344444-555556666-777888",
              ],
          },
      }[args.root][args.key]

      for subkey in subkeys:
        result = rrg_list_winreg_keys_pb2.Result()
        result.root = args.root
        result.key = args.key
        result.subkey = subkey
        session.Reply(result)

    def QueryWmiHandler(session: rrg_test_lib.Session) -> None:
      del session  # Unused.

      raise NotImplementedError()

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=artifact.KnowledgeBaseInitializationFlow,
        flow_args=artifact.KnowledgeBaseInitializationArgs(),
        handlers={
            rrg_pb2.Action.GET_WINREG_VALUE: GetWinregValueHandler,
            rrg_pb2.Action.LIST_WINREG_KEYS: ListWinregKeysHandler,
            rrg_pb2.Action.QUERY_WMI: QueryWmiHandler,
        }
        | rrg_test_lib.FakeWindowsFileHandlers({
            "C:\\Users\\All Users": "C:\\ProgramData",
            "C:\\Users\\Default": {},
            "C:\\Users\\Default User": "C:\\Users\\quux",
            "C:\\Users\\desktop.ini": b"",
            "C:\\Users\\quux": {},
            "C:\\Users\\Public": {},
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=1024)
    self.assertLen(results, 1)

    kb = knowledge_base_pb2.KnowledgeBase()
    self.assertTrue(results[0].payload.Unpack(kb))

    self.assertEqual(
        kb.environ_path,
        r"C:\Windows\system32;C:\Windows",
    )
    self.assertEqual(
        kb.environ_temp,
        r"C:\Windows\TEMP",
    )
    self.assertEqual(
        kb.environ_allusersprofile,
        r"C:\ProgramData",
    )
    self.assertEqual(
        kb.environ_commonprogramfiles,
        r"C:\Program Files\Common Files",
    )
    self.assertEqual(
        kb.environ_commonprogramfilesx86,
        r"C:\Program Files (x86)\Common Files",
    )
    self.assertEqual(
        kb.environ_comspec,
        r"C:\Windows\system32\cmd.exe",
    )
    self.assertEqual(
        kb.environ_driverdata,
        r"C:\Windows\System32\Drivers\DriverData",
    )
    self.assertEqual(
        kb.environ_profilesdirectory,
        r"C:\Users",
    )
    self.assertEqual(
        kb.environ_programfiles,
        r"C:\Program Files",
    )
    self.assertEqual(
        kb.environ_programfilesx86,
        r"C:\Program Files (x86)",
    )
    self.assertEqual(
        kb.environ_programdata,
        r"C:\ProgramData",
    )
    self.assertEqual(
        kb.environ_systemdrive,
        r"C:",
    )
    self.assertEqual(
        kb.environ_systemroot,
        r"C:\Windows",
    )
    self.assertEqual(
        kb.environ_windir,
        r"C:\Windows",
    )
    self.assertEqual(
        kb.current_control_set,
        r"HKEY_LOCAL_MACHINE\SYSTEM\ControlSet001",
    )
    self.assertEqual(
        kb.code_page,
        r"cp_1252",
    )
    self.assertEqual(
        kb.domain,
        r"ad.example.com",
    )
    self.assertEqual(
        kb.time_zone,
        r"PST8PDT",
    )

    users_by_username = {user.username: user for user in kb.users}
    self.assertIn("foobar", users_by_username)  # From registry.
    self.assertIn("quux", users_by_username)  # From `Users` folder.

    self.assertEqual(
        users_by_username["foobar"].temp,
        # TODO: Currently we do not support per-user environment
        # variable expansion. We should revisit this assertion once we do.
        r"%USERPROFILE%\AppData\Local\Temp",
    )
    self.assertEqual(
        users_by_username["foobar"].desktop,
        r"C:\Users\foobar\Desktop",
    )
    self.assertEqual(
        users_by_username["foobar"].userdomain,
        r"GOOGLE",
    )
    self.assertEqual(
        users_by_username["foobar"].sid,
        r"S-1-5-21-11112222-3333344444-555556666-777888",
    )
    self.assertEqual(
        users_by_username["foobar"].userprofile,
        r"C:\Users\foobar",
    )
    self.assertEqual(
        users_by_username["foobar"].appdata,
        r"C:\Users\foobar\AppData\Roaming",
    )
    self.assertEqual(
        users_by_username["foobar"].localappdata,
        r"C:\Users\foobar\AppData\Local",
    )
    self.assertEqual(
        users_by_username["foobar"].internet_cache,
        r"C:\Users\foobar\AppData\Local\Microsoft\Windows\INetCache",
    )
    self.assertEqual(
        users_by_username["foobar"].cookies,
        r"C:\Users\foobar\AppData\Local\Microsoft\Windows\INetCookies",
    )
    self.assertEqual(
        users_by_username["foobar"].recent,
        r"C:\Users\foobar\AppData\Roaming\Microsoft\Windows\Recent",
    )
    self.assertEqual(
        users_by_username["foobar"].personal,
        r"C:\Users\foobar\Documents",
    )
    self.assertEqual(
        users_by_username["foobar"].startup,
        # pylint: disable=line-too-long
        # pyformat: disable
        r"C:\Users\foobar\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup",
        # pyformat: enable
        # pylint: enable=line-too-long
    )
    self.assertEqual(
        users_by_username["foobar"].localappdata_low,
        r"C:\Users\foobar\AppData\LocalLow",
    )
    self.assertEqual(
        users_by_username["foobar"].homedir,
        r"C:\Users\foobar",
    )

    self.assertEqual(
        users_by_username["quux"].homedir,
        "C:\\Users\\quux",
    )

  def testRRGWindowsUserFallbackDedup(self):
    assert data_store.REL_DB is not None
    rel_db: db.Database = data_store.REL_DB

    client_id = db_test_utils.InitializeRRGClient(rel_db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Windows"
    rel_db.WriteClientSnapshot(snapshot)

    def GetWinregValueHandler(session: rrg_test_lib.Session) -> None:
      args = rrg_get_winreg_value_pb2.Args()
      assert session.args.Unpack(args)

      # pylint: disable=line-too-long
      # fmt: off
      value = {
          rrg_winreg_pb2.LOCAL_MACHINE: {
              r"SOFTWARE\Microsoft\Windows NT\CurrentVersion": {
                  "SystemRoot": rrg_winreg_pb2.Value(
                      string=r"C:\Windows",
                  ),
              },
              r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\S-1-5-21-11112222-3333344444-555556666-777888": {
                  "ProfileImagePath": rrg_winreg_pb2.Value(
                      expand_string=r"C:\Users\foobar",
                  ),
              },
          },
          rrg_winreg_pb2.USERS: {
              r"S-1-5-21-11112222-3333344444-555556666-777888\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders": {
                  "Desktop": rrg_winreg_pb2.Value(
                      string=r"C:\Users\foobar\Desktop",
                  ),
              },
              r"S-1-5-21-11112222-3333344444-555556666-777888\Environment": {
                  "TEMP": rrg_winreg_pb2.Value(
                      expand_string=r"%USERPROFILE%\AppData\Local\Temp",
                  ),
              },
              r"S-1-5-21-11112222-3333344444-555556666-777888\Volatile Environment": {
                  "USERDOMAIN": rrg_winreg_pb2.Value(
                      string=r"GOOGLE",
                  ),
              },
          },
      }[args.root][args.key][args.name]
      # pylint: enable=line-too-long
      # fmt: on

      result = rrg_get_winreg_value_pb2.Result()
      result.root = args.root
      result.key = args.key
      result.value.name = args.name
      result.value.MergeFrom(value)
      session.Reply(result)

    def ListWinregKeysHandler(session: rrg_test_lib.Session) -> None:
      args = rrg_list_winreg_keys_pb2.Args()
      assert session.args.Unpack(args)

      subkeys = {
          rrg_winreg_pb2.LOCAL_MACHINE: {
              r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList": [
                  "S-1-5-21-11112222-3333344444-555556666-777888",
              ],
          },
      }[args.root][args.key]

      for subkey in subkeys:
        result = rrg_list_winreg_keys_pb2.Result()
        result.root = args.root
        result.key = args.key
        result.subkey = subkey
        session.Reply(result)

    def QueryWmiHandler(session: rrg_test_lib.Session) -> None:
      del session  # Unused.

      raise NotImplementedError()

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=artifact.KnowledgeBaseInitializationFlow,
        flow_args=artifact.KnowledgeBaseInitializationArgs(),
        handlers={
            rrg_pb2.Action.GET_WINREG_VALUE: GetWinregValueHandler,
            rrg_pb2.Action.LIST_WINREG_KEYS: ListWinregKeysHandler,
            rrg_pb2.Action.QUERY_WMI: QueryWmiHandler,
        }
        | rrg_test_lib.FakeWindowsFileHandlers({
            "C:\\Users\\foobar": {},
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=1024)
    self.assertLen(results, 1)

    kb = knowledge_base_pb2.KnowledgeBase()
    self.assertTrue(results[0].payload.Unpack(kb))

    self.assertLen(kb.users, 1)

    user = kb.users[0]
    self.assertEqual(user.username, "foobar")
    self.assertEqual(user.sid, "S-1-5-21-11112222-3333344444-555556666-777888")
    self.assertEqual(user.userdomain, "GOOGLE")
    self.assertEqual(user.userprofile, r"C:\Users\foobar")
    self.assertEqual(user.homedir, r"C:\Users\foobar")
    self.assertEqual(user.desktop, r"C:\Users\foobar\Desktop")

  def testRRGWindowsTimeZoneStandardNameFallback(self):
    assert data_store.REL_DB is not None
    rel_db: db.Database = data_store.REL_DB

    client_id = db_test_utils.InitializeRRGClient(rel_db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Windows"
    rel_db.WriteClientSnapshot(snapshot)

    def GetWinregValueHandler(session: rrg_test_lib.Session) -> None:
      args = rrg_get_winreg_value_pb2.Args()
      assert session.args.Unpack(args)

      value = {
          rrg_winreg_pb2.LOCAL_MACHINE: {
              r"SYSTEM\CurrentControlSet\Control\TimeZoneInformation": {
                  "StandardName": rrg_winreg_pb2.Value(
                      string=r"Pacific Standard Time",
                  ),
              },
          },
      }[args.root][args.key][args.name]

      result = rrg_get_winreg_value_pb2.Result()
      result.root = args.root
      result.key = args.key
      result.value.name = args.name
      result.value.MergeFrom(value)
      session.Reply(result)

    def ListWinregKeysHandler(session: rrg_test_lib.Session) -> None:
      del session  # Unused.

      raise NotImplementedError()

    def QueryWmiHandler(session: rrg_test_lib.Session) -> None:
      del session  # Unused.

      raise NotImplementedError()

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=artifact.KnowledgeBaseInitializationFlow,
        flow_args=artifact.KnowledgeBaseInitializationArgs(),
        handlers={
            rrg_pb2.Action.GET_WINREG_VALUE: GetWinregValueHandler,
            rrg_pb2.Action.LIST_WINREG_KEYS: ListWinregKeysHandler,
            rrg_pb2.Action.QUERY_WMI: QueryWmiHandler,
        },
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=1024)
    self.assertLen(results, 1)

    kb = knowledge_base_pb2.KnowledgeBase()
    self.assertTrue(results[0].payload.Unpack(kb))

    self.assertEqual(kb.time_zone, "PST8PDT")

  def testRRGWindowsWMIUserAccount(self):
    assert data_store.REL_DB is not None
    rel_db: db.Database = data_store.REL_DB

    client_id = db_test_utils.InitializeRRGClient(rel_db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Windows"
    rel_db.WriteClientSnapshot(snapshot)

    def GetWinregValueHandler(session: rrg_test_lib.Session) -> None:
      del session  # Unused.

      raise NotImplementedError()

    def ListWinregKeysHandler(session: rrg_test_lib.Session) -> None:
      del session  # Unused.

      raise NotImplementedError()

    def QueryWmiHandler(session: rrg_test_lib.Session) -> None:
      result = rrg_query_wmi_pb2.Result()
      result.row["SID"].string = "S-1-5-21-11112222-3333344444-555556666-777888"
      result.row["Name"].string = "foo"
      result.row["FullName"].string = "Foo Thudycz"
      result.row["Domain"].string = "EXAMPLE"
      session.Reply(result)

      result = rrg_query_wmi_pb2.Result()
      result.row["SID"].string = "S-1-5-21-99998888-7777766666-555554444-333222"
      result.row["Name"].string = "bar"
      result.row["FullName"].string = "Bar Quuxerski"
      result.row["Domain"].string = "EXAMPLE"
      session.Reply(result)

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=artifact.KnowledgeBaseInitializationFlow,
        flow_args=artifact.KnowledgeBaseInitializationArgs(
            lightweight=False,
        ),
        handlers={
            rrg_pb2.Action.GET_WINREG_VALUE: GetWinregValueHandler,
            rrg_pb2.Action.LIST_WINREG_KEYS: ListWinregKeysHandler,
            rrg_pb2.Action.QUERY_WMI: QueryWmiHandler,
        },
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=1024)
    self.assertLen(results, 1)

    kb = knowledge_base_pb2.KnowledgeBase()
    self.assertTrue(results[0].payload.Unpack(kb))

    self.assertLen(kb.users, 2)

    users_by_username = {user.username: user for user in kb.users}

    foo = users_by_username["foo"]
    self.assertEqual(foo.sid, "S-1-5-21-11112222-3333344444-555556666-777888")
    self.assertEqual(foo.full_name, "Foo Thudycz")
    self.assertEqual(foo.userdomain, "EXAMPLE")

    bar = users_by_username["bar"]
    self.assertEqual(bar.sid, "S-1-5-21-99998888-7777766666-555554444-333222")
    self.assertEqual(bar.full_name, "Bar Quuxerski")
    self.assertEqual(bar.userdomain, "EXAMPLE")


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
