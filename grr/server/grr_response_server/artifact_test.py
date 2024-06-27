#!/usr/bin/env python
"""Tests for artifacts."""

import io
import os
from typing import Iterator

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
from grr_response_core.lib.rdfvalues import mig_client_action
from grr_response_core.lib.rdfvalues import mig_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
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
        os.path.join(config.CONFIG["Test.data_dir"], "artifacts",
                     "test_artifacts.json"))

  class MockClient(action_mocks.MemoryClientMock):

    def WmiQuery(self, _):
      return WMI_SAMPLE

  def RunCollectorAndGetResults(self,
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
        creator=self.test_username,
        **kw)

    return flow_test_lib.GetFlowResults(client_id, session_id)


class GRRArtifactTest(ArtifactTest):

  def testUploadArtifactYamlFileAndDumpToYaml(self):
    artifact_registry.REGISTRY.ClearRegistry()
    artifact_registry.REGISTRY.ClearSources()
    artifact_registry.REGISTRY._CheckDirty()

    try:

      test_artifacts_file = os.path.join(config.CONFIG["Test.data_dir"],
                                         "artifacts", "test_artifacts.json")

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
          artifacts_by_name["TestEchoArtifact"].sources[0].returned_types,
          ["SoftwarePackages"],
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
        name_list=["CommandOrder"]).pop()
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
    self.assertIn("WMIActiveScriptEventConsumer",
                  artifact_registry.REGISTRY._artifacts)
    artifact_obj = artifact_registry.REGISTRY.GetArtifact(
        "WMIActiveScriptEventConsumer")
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
      self.RunCollectorAndGetResults(["TestFilesArtifact"],
                                     client_mock=self.client_mock,
                                     client_id=client_id)

      # Will raise if something goes wrong.
      self.RunCollectorAndGetResults(["TestFilesArtifact"],
                                     client_mock=self.client_mock,
                                     client_id=client_id,
                                     split_output_by_artifact=True)

      # Test the error_on_no_results option.
      with self.assertRaises(RuntimeError) as context:
        with test_lib.SuppressLogs():
          self.RunCollectorAndGetResults(["NullArtifact"],
                                         client_mock=self.client_mock,
                                         client_id=client_id,
                                         split_output_by_artifact=True,
                                         error_on_no_results=True)
      if "collector returned 0 responses" not in str(context.exception):
        raise RuntimeError("0 responses should have been returned")


class GrrKbTest(ArtifactTest):

  def _RunKBI(self, **kw):
    session_id = flow_test_lib.TestFlowHelper(
        artifact.KnowledgeBaseInitializationFlow.__name__,
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
        **kw,
    )

    results = flow_test_lib.GetFlowResults(test_lib.TEST_CLIENT_ID, session_id)
    self.assertLen(results, 1)
    return results[0]


class GrrKbWindowsTest(GrrKbTest):

  def setUp(self):
    super().setUp()
    self.SetupClient(0, system="Windows", os_version="6.2", arch="AMD64")

    os_overrider = vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                             vfs_test_lib.FakeFullVFSHandler)
    os_overrider.Start()
    self.addCleanup(os_overrider.Stop)

    reg_overrider = vfs_test_lib.VFSOverrider(
        rdf_paths.PathSpec.PathType.REGISTRY,
        vfs_test_lib.FakeRegistryVFSHandler)
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

    session_id = flow_test_lib.TestFlowHelper(
        artifact.KnowledgeBaseInitializationFlow.__name__,
        client_id=test_lib.TEST_CLIENT_ID,
        client_mock=KnowledgebaseInitMock(),
    )

    results = flow_test_lib.GetFlowResults(test_lib.TEST_CLIENT_ID, session_id)

    self.assertLen(results, 1)
    self.assertIsInstance(results[0], rdf_client.KnowledgeBase)

    kb = results[0]

    self.assertCountEqual([x.username for x in kb.users],
                          ["user1", "user2", "user3", "yagharek"])
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
        # pyformat: disable
        if (args.pathspec.pathtype != jobs_pb2.PathSpec.PathType.REGISTRY or
            args.pathspec.path != r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\SystemRoot"):
        # pylint: enable=line-too-long
        # pyformat: enable
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

        # pyformat: disable
        if (args.pathspec.pathtype != jobs_pb2.PathSpec.PathType.OS or
            args.pathspec.path != "X:\\Users"):
        # pyformat: enable
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
        # pyformat: disable
        if (args.pathspec.pathtype != jobs_pb2.PathSpec.PathType.REGISTRY or
            args.pathspec.path != r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\SystemRoot"):
          # pylint: enable=line-too-long
          # pyformat: enable
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

        # pyformat: disable
        if (args.pathspec.pathtype != jobs_pb2.PathSpec.PathType.OS or
            args.pathspec.path != "X:\\Users"):
          # pyformat: enable
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


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
