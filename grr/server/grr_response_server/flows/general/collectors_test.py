#!/usr/bin/env python
"""Test the collector flows.

To reduce the size of this module, additional collector flow tests are split out
into collectors_*_test.py files.
"""

import os
import shutil

from absl import app

from grr_response_client import actions
from grr_response_client.client_actions import standard
from grr_response_core import config
from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import mig_artifacts
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util import temp
from grr_response_proto import knowledge_base_pb2
from grr_response_proto import objects_pb2
from grr_response_server import artifact_registry
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server.databases import db
from grr_response_server.databases import db_test_utils
from grr_response_server.flows.general import collectors
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import mig_flow_objects
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import action_mocks
from grr.test_lib import artifact_test_lib
from grr.test_lib import client_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib


def ProcessIter():
  return iter([client_test_lib.MockWindowsProcess()])


class ArtifactCollectorsTestMixin(object):
  """A mixin for artifact collectors tests."""

  def setUp(self):
    """Make sure things are initialized."""
    super().setUp()

    patcher = artifact_test_lib.PatchDefaultArtifactRegistry()
    patcher.start()
    self.addCleanup(patcher.stop)

    artifact_registry.REGISTRY.ClearSources()
    artifact_registry.REGISTRY.ClearRegistry()

    test_artifacts_file = os.path.join(
        config.CONFIG["Test.data_dir"], "artifacts", "test_artifacts.json"
    )
    artifact_registry.REGISTRY.AddFileSource(test_artifacts_file)

    self.fakeartifact = artifact_registry.REGISTRY.GetArtifact("FakeArtifact")
    self.fakeartifact2 = artifact_registry.REGISTRY.GetArtifact("FakeArtifact2")

    self.output_count = 0


class TestArtifactCollectors(
    ArtifactCollectorsTestMixin, flow_test_lib.FlowTestsBaseclass
):
  """Test the artifact collection mechanism with fake artifacts."""

  def testInterpolateArgs(self):
    client_id = db_test_utils.InitializeClient(data_store.REL_DB)
    flow_id = db_test_utils.InitializeFlow(data_store.REL_DB, client_id)

    args = rdf_artifacts.ArtifactCollectorFlowArgs()
    collect_flow = collectors.ArtifactCollectorFlow(
        rdf_flow_objects.Flow(client_id=client_id, flow_id=flow_id, args=args)
    )

    kb = knowledge_base_pb2.KnowledgeBase()
    kb.users.append(knowledge_base_pb2.User(username="test1"))
    kb.users.append(knowledge_base_pb2.User(username="test2"))
    collect_flow.store.knowledge_base.CopyFrom(kb)

    collect_flow.current_artifact_name = "blah"

    list_args = collect_flow._InterpolateList(
        ["%%users.username%%", r"%%users.username%%\aa"]
    )
    self.assertCountEqual(
        list_args, ["test1", "test2", r"test1\aa", r"test2\aa"]
    )

    list_args = collect_flow._InterpolateList(["one"])
    self.assertEqual(list_args, ["one"])

    # Ignore the failure in users.desktop, report the others.
    collect_flow.args.ignore_interpolation_errors = True
    list_args = collect_flow._InterpolateList(
        ["%%users.uid%%", r"%%users.username%%\aa"]
    )
    self.assertCountEqual(list_args, [r"test1\aa", r"test2\aa"])

    # Both fail.
    list_args = collect_flow._InterpolateList(
        [r"%%users.uid%%\aa", r"%%users.sid%%\aa"]
    )
    self.assertCountEqual(list_args, [])

  def testGetArtifact(self):
    """Test we can get a basic artifact."""
    # Dynamically add an ArtifactSource specifying the base path.
    file_path = os.path.join(self.base_path, "win_hello.exe")
    coll1 = rdf_artifacts.ArtifactSource(
        type=rdf_artifacts.ArtifactSource.SourceType.FILE,
        attributes={"paths": [file_path]},
    )
    self.fakeartifact.sources.append(coll1)

    self._GetArtifact("FakeArtifact")

  def testArtifactUpload(self):
    file_path = os.path.join(self.base_path, "win_hello.exe")

    artifact_source = """
  name: ArtifactFromSource
  doc: My first artifact.
  labels:
    - Logs
    - Authentication
  supported_os:
    - Linux
  sources:
    - type: FILE
      attributes:
        paths:
          - %s
""" % file_path

    artifact_obj = artifact_registry.REGISTRY.ArtifactsFromYaml(
        artifact_source
    )[0]
    artifact_registry.REGISTRY._CheckDirty()

    data_store.REL_DB.WriteArtifact(mig_artifacts.ToProtoArtifact(artifact_obj))

    # Make sure that the artifact is not yet registered and the flow will have
    # to read it from the data store.
    with self.assertRaises(rdf_artifacts.ArtifactNotRegisteredError):
      artifact_registry.REGISTRY.GetArtifact("ArtifactFromSource")

    self._GetArtifact("ArtifactFromSource")

  def _GetArtifact(self, artifact_name):
    client_mock = action_mocks.FileFinderClientMock()
    client_id = self.SetupClient(0, system="Linux")
    file_path = os.path.join(self.base_path, "win_hello.exe")

    artifact_list = [artifact_name]
    flow_test_lib.StartAndRunFlow(
        collectors.ArtifactCollectorFlow,
        client_mock,
        creator=self.test_username,
        client_id=client_id,
        flow_args=rdf_artifacts.ArtifactCollectorFlowArgs(
            artifact_list=artifact_list,
            use_raw_filesystem_access=False,
        ),
    )

    fd2 = open(file_path, "rb")
    fd2.seek(0, 2)
    expected_size = fd2.tell()

    components = file_path.strip("/").split("/")
    fd = file_store.OpenFile(
        db.ClientPath(
            client_id,
            rdf_objects.PathInfo.PathType.OS,
            components=tuple(components),
        )
    )
    fd.Seek(0, 2)
    size = fd.Tell()
    self.assertEqual(size, expected_size)

  def testRegistryValueArtifact(self):
    client_id = self.SetupClient(0, system="Linux")

    with vfs_test_lib.VFSOverrider(
        rdf_paths.PathSpec.PathType.REGISTRY,
        vfs_test_lib.FakeRegistryVFSHandler,
    ):
      with vfs_test_lib.VFSOverrider(
          rdf_paths.PathSpec.PathType.OS, vfs_test_lib.FakeFullVFSHandler
      ):
        client_mock = action_mocks.ActionMock(standard.GetFileStat)
        coll1 = rdf_artifacts.ArtifactSource(
            type=rdf_artifacts.ArtifactSource.SourceType.REGISTRY_VALUE,
            attributes={
                "key_value_pairs": [{
                    "key": (
                        r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet"
                        r"\Control\Session Manager"
                    ),
                    "value": "BootExecute",
                }]
            },
        )
        self.fakeartifact.sources.append(coll1)
        artifact_list = ["FakeArtifact"]
        flow_id = flow_test_lib.StartAndRunFlow(
            collectors.ArtifactCollectorFlow,
            client_mock,
            flow_args=rdf_artifacts.ArtifactCollectorFlowArgs(
                artifact_list=artifact_list,
            ),
            creator=self.test_username,
            client_id=client_id,
        )

    # Test the statentry got stored.
    results = flow_test_lib.GetFlowResults(client_id, flow_id)
    self.assertIsInstance(results[0], rdf_client_fs.StatEntry)
    self.assertEndsWith(results[0].pathspec.CollapsePath(), "BootExecute")

  def testRegistryDefaultValueArtifact(self):
    client_id = self.SetupClient(0, system="Linux")
    with vfs_test_lib.VFSOverrider(
        rdf_paths.PathSpec.PathType.REGISTRY,
        vfs_test_lib.FakeRegistryVFSHandler,
    ):
      with vfs_test_lib.VFSOverrider(
          rdf_paths.PathSpec.PathType.OS, vfs_test_lib.FakeFullVFSHandler
      ):
        client_mock = action_mocks.ActionMock(standard.GetFileStat)
        coll1 = rdf_artifacts.ArtifactSource(
            type=rdf_artifacts.ArtifactSource.SourceType.REGISTRY_VALUE,
            attributes={
                "key_value_pairs": [{
                    "key": r"HKEY_LOCAL_MACHINE/SOFTWARE/ListingTest",
                    "value": "",
                }]
            },
        )
        self.fakeartifact.sources.append(coll1)
        artifact_list = ["FakeArtifact"]
        flow_id = flow_test_lib.StartAndRunFlow(
            collectors.ArtifactCollectorFlow,
            client_mock,
            flow_args=rdf_artifacts.ArtifactCollectorFlowArgs(
                artifact_list=artifact_list,
            ),
            creator=self.test_username,
            client_id=client_id,
        )

    results = flow_test_lib.GetFlowResults(client_id, flow_id)
    self.assertIsInstance(results[0], rdf_client_fs.StatEntry)
    self.assertEqual(results[0].registry_data.GetValue(), "DefaultValue")

  def testRegistryKeyArtifact_WithGlob(self):
    client_id = self.SetupClient(0, system="Windows")

    # We need to write some dummy snapshot to ensure the knowledgebase is there.
    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Windows"
    snapshot.knowledge_base.users.append(
        knowledge_base_pb2.User(username="user1", sid="S-1111")
    )
    snapshot.knowledge_base.users.append(
        knowledge_base_pb2.User(username="user2", sid="S-2222")
    )
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    # When the client is called, we expect the glob to have been expanded.
    class FakeSomeKey(actions.ActionPlugin):
      in_rdfvalue = rdf_file_finder.FileFinderArgs
      out_rdfvalues = [rdf_file_finder.FileFinderResult]

      def Run(self, args: rdf_file_finder.FileFinderArgs) -> None:
        assert r"HKEY_USERS/S-1111/SomeKey" in args.paths
        assert r"HKEY_USERS/S-2222/SomeKey" in args.paths
        self.SendReply(
            rdf_file_finder.FileFinderResult(
                stat_entry=rdf_client_fs.StatEntry(
                    pathspec=rdf_paths.PathSpec(
                        path=r"some_result",
                        pathtype=rdf_paths.PathSpec.PathType.REGISTRY,
                    ),
                )
            )
        )

    registry_key_artifact_source = rdf_artifacts.ArtifactSource(
        type=rdf_artifacts.ArtifactSource.SourceType.REGISTRY_KEY,
        attributes={"keys": [r"HKEY_USERS/%%users.sid%%/SomeKey"]},
    )
    self.fakeartifact.sources.append(registry_key_artifact_source)
    # This is needed to ensure the artifact is not skipped.
    self.fakeartifact.supported_os = ["Windows"]
    artifact_list = ["FakeArtifact"]
    flow_id = flow_test_lib.StartAndRunFlow(
        collectors.ArtifactCollectorFlow,
        action_mocks.ActionMock.With({
            "VfsFileFinder": FakeSomeKey,
        }),
        flow_args=rdf_artifacts.ArtifactCollectorFlowArgs(
            artifact_list=artifact_list,
        ),
        creator=self.test_username,
        client_id=client_id,
    )
    results = flow_test_lib.GetFlowResults(client_id, flow_id)
    self.assertIsInstance(results[0], rdf_client_fs.StatEntry)
    self.assertEqual(results[0].pathspec.path, "some_result")

  def testRegistryValueArtifact_WithGlob(self):
    client_id = self.SetupClient(0, system="Windows")

    # When the client is called, we expect the glob to have been expanded.
    class FakeSomeValue(actions.ActionPlugin):
      in_rdfvalue = rdf_file_finder.FileFinderArgs
      out_rdfvalues = [rdf_file_finder.FileFinderResult]

      def Run(self, args: rdf_file_finder.FileFinderArgs) -> None:
        assert r"HKEY_USERS\*\SomeKey\SomeValue" in args.paths
        self.SendReply(
            rdf_file_finder.FileFinderResult(
                stat_entry=rdf_client_fs.StatEntry(
                    pathspec=rdf_paths.PathSpec(
                        path=r"some_result",
                        pathtype=rdf_paths.PathSpec.PathType.REGISTRY,
                    ),
                )
            )
        )

    # Unlike for `REGISTRY_KEY`, `REGISTRY_VALUE` only goes to ClientFileFinder
    # if the glob contains `*`, otherwise `%%` kb interpolations are done
    # directly by `ArtifactCollectorFlow` (not sent to `ClientFileFinder`).
    # This is why we don't need to write a dummy snapshot in this test case.
    registry_key_artifact_source = rdf_artifacts.ArtifactSource(
        type=rdf_artifacts.ArtifactSource.SourceType.REGISTRY_VALUE,
        attributes={
            "key_value_pairs": [{
                "key": r"HKEY_USERS\*\SomeKey",
                "value": "SomeValue",
            }]
        },
    )
    self.fakeartifact.sources.append(registry_key_artifact_source)
    # This is needed to ensure the artifact is not skipped.
    self.fakeartifact.supported_os = ["Windows"]
    artifact_list = ["FakeArtifact"]
    flow_id = flow_test_lib.StartAndRunFlow(
        collectors.ArtifactCollectorFlow,
        action_mocks.ActionMock.With({
            "VfsFileFinder": FakeSomeValue,
        }),
        flow_args=rdf_artifacts.ArtifactCollectorFlowArgs(
            artifact_list=artifact_list,
        ),
        creator=self.test_username,
        client_id=client_id,
    )
    results = flow_test_lib.GetFlowResults(client_id, flow_id)
    self.assertIsInstance(results[0], rdf_client_fs.StatEntry)
    self.assertEqual(results[0].pathspec.path, "some_result")

  def testSupportedOS(self):
    """Test supported_os inside the collector object."""
    client_id = self.SetupClient(0, system="Linux")

    class FileFinderReturnsFoo(actions.ActionPlugin):
      in_rdfvalue = rdf_file_finder.FileFinderArgs
      out_rdfvalues = [rdf_file_finder.FileFinderResult]

      def Run(self, args: rdf_file_finder.FileFinderArgs) -> None:
        self.SendReply(
            rdf_file_finder.FileFinderResult(
                stat_entry=rdf_client_fs.StatEntry(
                    pathspec=rdf_paths.PathSpec(
                        path="/foo",
                        pathtype=rdf_paths.PathSpec.PathType.OS,
                    )
                )
            )
        )

    client_mock = action_mocks.ActionMock.With({
        "FileFinderOS": FileFinderReturnsFoo,
    })

    coll1 = rdf_artifacts.ArtifactSource(
        type=rdf_artifacts.ArtifactSource.SourceType.PATH,
        attributes={"paths": ["/foo"]},
        supported_os=["Windows"],
    )
    self.fakeartifact.sources.append(coll1)

    results = self._RunPathArtifact(client_id, client_mock, ["FakeArtifact"])
    self.assertEmpty(results)

    coll1.supported_os = ["Linux", "Windows"]
    self.fakeartifact.sources = []
    self.fakeartifact.sources.append(coll1)
    results = self._RunPathArtifact(client_id, client_mock, ["FakeArtifact"])
    self.assertTrue(results)

    coll1.supported_os = ["NotTrue"]
    self.fakeartifact.sources = []
    self.fakeartifact.sources.append(coll1)
    results = self._RunPathArtifact(client_id, client_mock, ["FakeArtifact"])
    self.assertEmpty(results)

    coll1.supported_os = ["Linux", "Windows"]
    self.fakeartifact.supported_os = ["Linux"]
    results = self._RunPathArtifact(client_id, client_mock, ["FakeArtifact"])
    self.assertTrue(results)

    self.fakeartifact.supported_os = ["Windows"]
    results = self._RunPathArtifact(client_id, client_mock, ["FakeArtifact"])
    self.assertEmpty(results)

  def _RunPathArtifact(
      self, client_id, client_mock, artifact_list, implementation_type=None
  ):
    self.output_count += 1
    flow_id = flow_test_lib.StartAndRunFlow(
        collectors.ArtifactCollectorFlow,
        client_mock,
        creator=self.test_username,
        client_id=client_id,
        flow_args=rdf_artifacts.ArtifactCollectorFlowArgs(
            artifact_list=artifact_list,
            implementation_type=implementation_type,
            use_raw_filesystem_access=(implementation_type is not None),
        ),
    )

    return flow_test_lib.GetFlowResults(client_id, flow_id)

  def testFlowProgressHasEntryForArtifactWithoutResults(self):
    client_id = self.SetupClient(0, system="Linux")

    class FakeFileFinderOS(actions.ActionPlugin):
      in_rdfvalue = rdf_file_finder.FileFinderArgs
      out_rdfvalues = [rdf_file_finder.FileFinderResult]

      def Run(self, args: rdf_file_finder.FileFinderArgs) -> None:
        pass  # No results.

    self.fakeartifact.sources.append(
        rdf_artifacts.ArtifactSource(
            type=rdf_artifacts.ArtifactSource.SourceType.PATH,
            attributes={"paths": ["/test/foo"]},
        )
    )

    flow_id = flow_test_lib.StartAndRunFlow(
        collectors.ArtifactCollectorFlow,
        action_mocks.ActionMock.With({
            "FileFinderOS": FakeFileFinderOS,
        }),
        client_id=client_id,
        flow_args=rdf_artifacts.ArtifactCollectorFlowArgs(
            artifact_list=["FakeArtifact"],
        ),
    )

    progress = flow_test_lib.GetFlowProgress(client_id, flow_id)
    self.assertLen(progress.artifacts, 1)
    self.assertEqual(progress.artifacts[0].name, "FakeArtifact")
    self.assertEqual(progress.artifacts[0].num_results, 0)

  def testFlowProgressIsCountingResults(self):
    client_id = self.SetupClient(0, system="Linux")

    class FakeFileFinderOS(actions.ActionPlugin):
      in_rdfvalue = rdf_file_finder.FileFinderArgs
      out_rdfvalues = [rdf_file_finder.FileFinderResult]

      def Run(self, args: rdf_file_finder.FileFinderArgs) -> None:
        self.SendReply(
            rdf_file_finder.FileFinderResult(
                stat_entry=rdf_client_fs.StatEntry(
                    pathspec=rdf_paths.PathSpec(
                        path="/test/foo1",
                        pathtype=rdf_paths.PathSpec.PathType.OS,
                    )
                )
            )
        )
        self.SendReply(
            rdf_file_finder.FileFinderResult(
                stat_entry=rdf_client_fs.StatEntry(
                    pathspec=rdf_paths.PathSpec(
                        path="/test/foo2",
                        pathtype=rdf_paths.PathSpec.PathType.OS,
                    )
                )
            )
        )

    self.fakeartifact.sources.append(
        rdf_artifacts.ArtifactSource(
            type=rdf_artifacts.ArtifactSource.SourceType.PATH,
            attributes={"paths": ["/test/foo*"]},
        )
    )

    flow_id = flow_test_lib.StartAndRunFlow(
        collectors.ArtifactCollectorFlow,
        action_mocks.ActionMock.With({
            "FileFinderOS": FakeFileFinderOS,
        }),
        client_id=client_id,
        flow_args=rdf_artifacts.ArtifactCollectorFlowArgs(
            artifact_list=["FakeArtifact"],
        ),
    )

    progress = flow_test_lib.GetFlowProgress(client_id, flow_id)
    self.assertLen(progress.artifacts, 1)
    self.assertEqual(progress.artifacts[0].name, "FakeArtifact")
    self.assertEqual(progress.artifacts[0].num_results, 2)

  def testProcessesResultsOfFailedChildArtifactCollector(self):
    client_id = self.SetupClient(0, system="Linux")

    class FakeExecuteAction(actions.ActionPlugin):
      in_rdfvalue = rdf_client_action.ExecuteRequest
      out_rdfvalues = [rdf_client_action.ExecuteResponse]

      def Run(self, args: rdf_client_action.ExecuteRequest) -> None:
        self.SendReply(
            rdf_client_action.ExecuteResponse(
                exit_status=0,
                stdout=b"finished",
            )
        )
        raise ValueError()

    self.fakeartifact.sources.append(
        rdf_artifacts.ArtifactSource(
            type=rdf_artifacts.ArtifactSource.SourceType.ARTIFACT_GROUP,
            attributes={"names": ["FakeArtifact2"]},
        )
    )

    self.fakeartifact2.sources.append(
        rdf_artifacts.ArtifactSource(
            type=rdf_artifacts.ArtifactSource.SourceType.COMMAND,
            attributes={"cmd": "foo", "args": ["bar"]},
        )
    )

    flow_id = flow_test_lib.StartAndRunFlow(
        collectors.ArtifactCollectorFlow,
        action_mocks.ActionMock.With({
            "ExecuteCommand": FakeExecuteAction,
        }),
        client_id=client_id,
        check_flow_errors=False,
        flow_args=rdf_artifacts.ArtifactCollectorFlowArgs(
            artifact_list=["FakeArtifact"],
        ),
    )

    results = flow_test_lib.GetFlowResults(client_id, flow_id)
    self.assertLen(results, 1)
    self.assertEqual(results[0].stdout, b"finished")

  def testArtifactGroupGetsParentArgs(self):
    client_id = db_test_utils.InitializeClient(data_store.REL_DB)
    # Client metadata is not enough, we need some KB data to be present.
    client = objects_pb2.ClientSnapshot(client_id=client_id)
    client.knowledge_base.fqdn = "hidrogenesse.example.com"
    client.knowledge_base.os = "linux"
    data_store.REL_DB.WriteClientSnapshot(client)

    artifact_registry.REGISTRY.RegisterArtifact(
        rdf_artifacts.Artifact(
            name="Planta",
            doc="Animalito",
            sources=[
                rdf_artifacts.ArtifactSource(
                    type=rdf_artifacts.ArtifactSource.SourceType.ARTIFACT_GROUP,
                    attributes={"names": ["Máquina"]},
                )
            ],
        )
    )
    artifact_registry.REGISTRY.RegisterArtifact(
        rdf_artifacts.Artifact(
            name="Máquina",
            doc="Piedra",
            sources=[
                rdf_artifacts.ArtifactSource(
                    type=rdf_artifacts.ArtifactSource.SourceType.PATH,
                    attributes={"paths": ["planta"]},
                )
            ],
        )
    )

    class DoesNothingFileFinderOS(actions.ActionPlugin):
      in_rdfvalue = rdf_file_finder.FileFinderArgs
      out_rdfvalues = [rdf_file_finder.FileFinderResult]

      def Run(self, args: rdf_file_finder.FileFinderArgs) -> None:
        pass  # No results.

    flow_id = flow_test_lib.StartAndRunFlow(
        collectors.ArtifactCollectorFlow,
        action_mocks.ActionMock.With({
            "FileFinderOS": DoesNothingFileFinderOS,
        }),
        client_id=client_id,
        flow_args=rdf_artifacts.ArtifactCollectorFlowArgs(
            artifact_list=["Planta"],
            use_raw_filesystem_access=True,
            implementation_type=rdf_paths.PathSpec.ImplementationType.DIRECT,
            max_file_size=1,
            ignore_interpolation_errors=True,
        ),
        check_flow_errors=False,  # We expect the child flow to fail.
    )

    child_flows = data_store.REL_DB.ReadChildFlowObjects(client_id, flow_id)
    self.assertLen(child_flows, 1)
    args = mig_flow_objects.ToRDFFlow(child_flows[0]).args
    self.assertEqual(args.use_raw_filesystem_access, True)
    self.assertEqual(
        args.implementation_type,
        rdf_paths.PathSpec.ImplementationType.DIRECT,
    )
    self.assertEqual(args.max_file_size, 1)
    self.assertEqual(args.ignore_interpolation_errors, True)

  def testDirectory(self):
    client_id = self.SetupClient(0, system="Linux")
    client_mock = action_mocks.FileFinderClientMock()
    with temp.AutoTempDirPath() as temp_dir_path:
      coll1 = rdf_artifacts.ArtifactSource(
          type=rdf_artifacts.ArtifactSource.SourceType.PATH,
          attributes={"paths": [temp_dir_path]},
      )
      self.fakeartifact.sources.append(coll1)
      results = self._RunPathArtifact(client_id, client_mock, ["FakeArtifact"])
      self.assertLen(results, 1)
      self.assertEqual(results[0].pathspec.path, temp_dir_path)

  def testFile(self):
    client_id = self.SetupClient(0, system="Linux")
    client_mock = action_mocks.FileFinderClientMock()
    with temp.AutoTempFilePath() as temp_file_path:
      coll1 = rdf_artifacts.ArtifactSource(
          type=rdf_artifacts.ArtifactSource.SourceType.FILE,
          attributes={"paths": [temp_file_path]},
      )
      self.fakeartifact.sources.append(coll1)
      results = self._RunPathArtifact(client_id, client_mock, ["FakeArtifact"])
      self.assertLen(results, 1)
      self.assertEqual(results[0].pathspec.path, temp_file_path)

  def testArtifactFilesDownloaderFlow(self):
    client_id = self.SetupClient(0, system="Linux")
    client_mock = action_mocks.FileFinderClientMock()
    with temp.AutoTempFilePath() as temp_file_path:
      coll1 = rdf_artifacts.ArtifactSource(
          type=rdf_artifacts.ArtifactSource.SourceType.FILE,
          attributes={"paths": [temp_file_path]},
      )
      self.fakeartifact.sources.append(coll1)

      flow_id = flow_test_lib.StartAndRunFlow(
          collectors.ArtifactFilesDownloaderFlow,
          client_mock,
          creator=self.test_username,
          client_id=client_id,
          flow_args=collectors.ArtifactFilesDownloaderFlowArgs(
              artifact_list=["FakeArtifact"],
          ),
      )
      results = flow_test_lib.GetFlowResults(client_id, flow_id)
      self.assertLen(results, 1)
      self.assertEqual(results[0].downloaded_file.pathspec.path, temp_file_path)


class RelationalTestArtifactCollectors(
    ArtifactCollectorsTestMixin, test_lib.GRRBaseTest
):

  def testSplitsResultsByArtifact(self):
    """Test that artifacts get split into separate collections."""
    client_id = self.SetupClient(0, system="Linux")

    class FileFinderReturnsFooBar(actions.ActionPlugin):
      in_rdfvalue = rdf_file_finder.FileFinderArgs
      out_rdfvalues = [rdf_file_finder.FileFinderResult]

      def Run(self, args: rdf_file_finder.FileFinderArgs) -> None:
        self.SendReply(
            rdf_file_finder.FileFinderResult(
                stat_entry=rdf_client_fs.StatEntry(
                    pathspec=rdf_paths.PathSpec(
                        path="/test/bar",
                        pathtype=rdf_paths.PathSpec.PathType.OS,
                    )
                )
            )
        )

    coll1 = rdf_artifacts.ArtifactSource(
        type=rdf_artifacts.ArtifactSource.SourceType.PATH,
        attributes={"paths": ["/foo/bar"]},
    )
    self.fakeartifact.sources.append(coll1)
    self.fakeartifact2.sources.append(coll1)
    artifact_list = ["FakeArtifact", "FakeArtifact2"]
    flow_id = flow_test_lib.StartAndRunFlow(
        collectors.ArtifactCollectorFlow,
        action_mocks.ActionMock.With({
            "FileFinderOS": FileFinderReturnsFooBar,
        }),
        creator=self.test_username,
        client_id=client_id,
        flow_args=rdf_artifacts.ArtifactCollectorFlowArgs(
            artifact_list=artifact_list,
            split_output_by_artifact=True,
        ),
    )
    results_by_tag = flow_test_lib.GetFlowResultsByTag(client_id, flow_id)
    self.assertCountEqual(
        results_by_tag.keys(),
        ["artifact:FakeArtifact", "artifact:FakeArtifact2"],
    )


class MeetsConditionsTest(test_lib.GRRBaseTest):
  """Test the module-level method `MeetsConditions`."""

  def testSourceMeetsOSConditions(self):
    """Test we can get a GRR client artifact with conditions."""

    knowledge_base = rdf_client.KnowledgeBase()
    knowledge_base.os = "Windows"

    # Run with unsupported OS.
    source = rdf_artifacts.ArtifactSource(
        type=rdf_artifacts.ArtifactSource.SourceType.PATH,
        attributes={"paths": ["/test/foo"]},
        supported_os=["Linux"],
    )
    self.assertFalse(collectors.MeetsOSConditions(knowledge_base, source))

    # Run with supported OS.
    source = rdf_artifacts.ArtifactSource(
        type=rdf_artifacts.ArtifactSource.SourceType.PATH,
        attributes={"paths": ["/test/foo"]},
        supported_os=["Linux", "Windows"],
    )
    self.assertTrue(collectors.MeetsOSConditions(knowledge_base, source))


def InitGRRWithTestArtifacts(self):
  artifact_registry.REGISTRY.ClearSources()
  artifact_registry.REGISTRY.ClearRegistry()

  test_artifacts_file = os.path.join(
      config.CONFIG["Test.data_dir"], "artifacts", "test_artifacts.json"
  )
  artifact_registry.REGISTRY.AddFileSource(test_artifacts_file)

  self.addCleanup(artifact_registry.REGISTRY.AddDefaultSources)
  self.addCleanup(artifact_registry.REGISTRY.ClearRegistry)
  self.addCleanup(artifact_registry.REGISTRY.ClearSources)


def InitGRRWithTestSources(self, artifacts_data):
  artifact_registry.REGISTRY.ClearSources()
  artifact_registry.REGISTRY.ClearRegistry()

  artifacts_temp_dir = temp.TempDirPath()
  with open(os.path.join(artifacts_temp_dir, "test_artifacts.yaml"), "w") as fd:
    fd.write(artifacts_data)

  artifact_registry.REGISTRY.AddDirSources([artifacts_temp_dir])
  self.addCleanup(lambda: shutil.rmtree(artifacts_temp_dir))
  self.addCleanup(artifact_registry.REGISTRY.AddDefaultSources)
  self.addCleanup(artifact_registry.REGISTRY.ClearRegistry)
  self.addCleanup(artifact_registry.REGISTRY.ClearSources)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
