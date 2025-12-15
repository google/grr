#!/usr/bin/env python
"""Test the collector flows.

To reduce the size of this module, additional collector flow tests are split out
into collectors_*_test.py files.
"""

import hashlib
import os
import shutil
import stat
from typing import Iterable, Optional
from unittest import mock

from absl import app

from grr_response_client import actions
from grr_response_client.client_actions import standard
from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import mig_artifacts
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util import temp
from grr_response_proto import artifact_pb2
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import knowledge_base_pb2
from grr_response_proto import objects_pb2
from grr_response_proto import signed_commands_pb2
from grr_response_server import artifact_registry
from grr_response_server import blob_store
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server.databases import db
from grr_response_server.databases import db_test_utils
from grr_response_server.flows.general import collectors
from grr_response_server.models import blobs as models_blobs
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import mig_flow_objects
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import action_mocks
from grr.test_lib import artifact_test_lib
from grr.test_lib import client_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import rrg_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib
from grr_response_proto import rrg_pb2
from grr_response_proto.rrg import fs_pb2 as rrg_fs_pb2
from grr_response_proto.rrg import os_pb2 as rrg_os_pb2
from grr_response_proto.rrg import winreg_pb2 as rrg_winreg_pb2
from grr_response_proto.rrg.action import execute_signed_command_pb2 as rrg_execute_signed_command_pb2
from grr_response_proto.rrg.action import get_file_metadata_pb2 as rrg_get_file_metadata_pb2
from grr_response_proto.rrg.action import list_winreg_keys_pb2 as rrg_list_winreg_keys_pb2
from grr_response_proto.rrg.action import list_winreg_values_pb2 as rrg_list_winreg_values_pb2
from grr_response_proto.rrg.action import query_wmi_pb2 as rrg_query_wmi_pb2


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

  def testRRGPath_Simple(self):
    client_id = db_test_utils.InitializeRRGClient(
        data_store.REL_DB,
        os_type=rrg_os_pb2.LINUX,
    )

    # We write a dummy snapshot as otherwise the artifact collector will launch
    # an extra interrogation flow at first.
    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    artifact = artifact_pb2.Artifact()
    artifact.name = "PathExample"
    artifact.doc = "An example artifact with a path to collect"

    artifact_source = artifact.sources.add()
    artifact_source.type = artifact_pb2.ArtifactSource.PATH

    attr_paths = artifact_source.attributes.dat.add()
    attr_paths.k.string = "paths"
    attr_paths.v.list.content.add().string = "/foo/bar"

    artifact_registry.REGISTRY.RegisterArtifact(
        mig_artifacts.ToRDFArtifact(artifact)
    )

    args = flows_pb2.ArtifactCollectorFlowArgs()
    args.artifact_list.append("PathExample")

    def GetFileMetadataHandler(session: rrg_test_lib.Session) -> None:
      args = rrg_get_file_metadata_pb2.Args()
      assert session.args.Unpack(args)

      if len(args.paths) != 1:
        raise RuntimeError(f"Unexpected number of paths: {args.paths}")
      if args.paths[0].raw_bytes.decode("utf-8") != "/foo/bar":
        raise RuntimeError(f"Unexpected path: {args.paths[0]}")

      result = rrg_get_file_metadata_pb2.Result()
      result.path.raw_bytes = "/foo/bar".encode("utf-8")
      result.metadata.type = rrg_fs_pb2.FileMetadata.Type.FILE
      result.metadata.size = 42
      result.metadata.access_time.GetCurrentTime()
      result.metadata.modification_time.GetCurrentTime()
      result.metadata.creation_time.GetCurrentTime()

      result.metadata.unix_dev = 251
      result.metadata.unix_ino = 2
      result.metadata.unix_nlink = 21
      result.metadata.unix_uid = 44123
      result.metadata.unix_gid = 85123
      result.metadata.unix_rdev = 1
      result.metadata.unix_blksize = 4096
      result.metadata.unix_blocks = 8

      session.Reply(result)

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=collectors.ArtifactCollectorFlow,
        flow_args=mig_artifacts.ToRDFArtifactCollectorFlowArgs(args),
        handlers={
            rrg_pb2.Action.GET_FILE_METADATA: GetFileMetadataHandler,
        },
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_results = data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0, 128)
    self.assertLen(flow_results, 1)

    result = jobs_pb2.StatEntry()
    self.assertTrue(flow_results[0].payload.Unpack(result))
    self.assertEqual(flow_results[0].tag, "artifact:PathExample")

    self.assertEqual(result.pathspec.pathtype, jobs_pb2.PathSpec.PathType.OS)
    self.assertEqual(result.pathspec.path, "/foo/bar")
    self.assertTrue(stat.S_ISREG(result.st_mode))
    self.assertEqual(result.st_size, 42)
    self.assertGreater(result.st_atime, 0)
    self.assertGreater(result.st_mtime, 0)
    self.assertGreater(result.st_btime, 0)

    self.assertEqual(result.st_dev, 251)
    self.assertEqual(result.st_ino, 2)
    self.assertEqual(result.st_nlink, 21)
    self.assertEqual(result.st_uid, 44123)
    self.assertEqual(result.st_gid, 85123)
    self.assertEqual(result.st_rdev, 1)
    self.assertEqual(result.st_blksize, 4096)
    self.assertEqual(result.st_blocks, 8)

    path_info = data_store.REL_DB.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("foo", "bar"),
    )
    self.assertEqual(path_info.stat_entry.pathspec.path, "/foo/bar")
    self.assertEqual(path_info.stat_entry.st_size, 42)

  def testRRGPath_Multiple(self):
    client_id = db_test_utils.InitializeRRGClient(
        data_store.REL_DB,
        os_type=rrg_os_pb2.LINUX,
    )

    # We write a dummy snapshot as otherwise the artifact collector will launch
    # an extra interrogation flow at first.
    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    artifact = artifact_pb2.Artifact()
    artifact.name = "MultiplePathsExample"
    artifact.doc = "An example artifact with multiple paths to collect"

    artifact_source = artifact.sources.add()
    artifact_source.type = artifact_pb2.ArtifactSource.PATH

    attr_paths = artifact_source.attributes.dat.add()
    attr_paths.k.string = "paths"
    attr_paths.v.list.content.add().string = "/foo/bar"
    attr_paths.v.list.content.add().string = "/foo/baz"

    artifact_registry.REGISTRY.RegisterArtifact(
        mig_artifacts.ToRDFArtifact(artifact)
    )

    args = flows_pb2.ArtifactCollectorFlowArgs()
    args.artifact_list.append("MultiplePathsExample")

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=collectors.ArtifactCollectorFlow,
        flow_args=mig_artifacts.ToRDFArtifactCollectorFlowArgs(args),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/bar": os.urandom(42),
            "/foo/baz": "/quux/norf",
        }),
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_results = data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0, 128)
    self.assertLen(flow_results, 2)

    results_by_path = {}
    for flow_result in flow_results:
      result = jobs_pb2.StatEntry()
      self.assertTrue(flow_result.payload.Unpack(result))
      self.assertEqual(flow_result.tag, "artifact:MultiplePathsExample")

      results_by_path[result.pathspec.path] = result

    self.assertTrue(stat.S_ISREG(results_by_path["/foo/bar"].st_mode))
    self.assertEqual(results_by_path["/foo/bar"].st_size, 42)
    self.assertGreater(results_by_path["/foo/bar"].st_atime, 0)
    self.assertGreater(results_by_path["/foo/bar"].st_mtime, 0)
    self.assertGreater(results_by_path["/foo/bar"].st_btime, 0)

    self.assertTrue(stat.S_ISLNK(results_by_path["/foo/baz"].st_mode))
    self.assertEqual(results_by_path["/foo/baz"].symlink, "/quux/norf")
    self.assertGreater(results_by_path["/foo/baz"].st_atime, 0)
    self.assertGreater(results_by_path["/foo/baz"].st_mtime, 0)

    path_info_bar = data_store.REL_DB.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("foo", "bar"),
    )
    self.assertEqual(path_info_bar.stat_entry.pathspec.path, "/foo/bar")
    self.assertEqual(path_info_bar.stat_entry.st_size, 42)

    path_info_baz = data_store.REL_DB.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("foo", "baz"),
    )
    self.assertEqual(path_info_baz.stat_entry.pathspec.path, "/foo/baz")
    self.assertEqual(path_info_baz.stat_entry.symlink, "/quux/norf")

  def testRRGPath_Glob(self):
    client_id = db_test_utils.InitializeRRGClient(
        data_store.REL_DB,
        os_type=rrg_os_pb2.LINUX,
    )

    # We write a dummy snapshot as otherwise the artifact collector will launch
    # an extra interrogation flow at first.
    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    artifact = artifact_pb2.Artifact()
    artifact.name = "PathWithGlobExample"
    artifact.doc = "An example artifact with globbed path to collect"

    artifact_source = artifact.sources.add()
    artifact_source.type = artifact_pb2.ArtifactSource.PATH

    attr_paths = artifact_source.attributes.dat.add()
    attr_paths.k.string = "paths"
    attr_paths.v.list.content.add().string = "/foo/ba*"

    artifact_registry.REGISTRY.RegisterArtifact(
        mig_artifacts.ToRDFArtifact(artifact)
    )

    args = flows_pb2.ArtifactCollectorFlowArgs()
    args.artifact_list.append("PathWithGlobExample")

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=collectors.ArtifactCollectorFlow,
        flow_args=mig_artifacts.ToRDFArtifactCollectorFlowArgs(args),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/bar": os.urandom(42),
            "/foo/baz/thud": b"",
            "/foo/quux": b"",
        }),
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_results = data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0, 128)
    self.assertLen(flow_results, 2)

    results_by_path = {}
    for flow_result in flow_results:
      result = jobs_pb2.StatEntry()
      self.assertTrue(flow_result.payload.Unpack(result))
      self.assertEqual(flow_result.tag, "artifact:PathWithGlobExample")

      results_by_path[result.pathspec.path] = result

    self.assertTrue(stat.S_ISREG(results_by_path["/foo/bar"].st_mode))
    self.assertEqual(results_by_path["/foo/bar"].st_size, 42)

    self.assertTrue(stat.S_ISDIR(results_by_path["/foo/baz"].st_mode))

    path_info_bar = data_store.REL_DB.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("foo", "bar"),
    )
    self.assertEqual(path_info_bar.stat_entry.pathspec.path, "/foo/bar")
    self.assertEqual(path_info_bar.stat_entry.st_size, 42)

    path_info_baz = data_store.REL_DB.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("foo", "baz"),
    )
    self.assertEqual(path_info_baz.stat_entry.pathspec.path, "/foo/baz")
    self.assertTrue(path_info_baz.directory)

    self.assertNotIn("/foo/baz/thud", results_by_path)
    self.assertNotIn("/foo/quux", results_by_path)

  def testRRGPath_Interpolation(self):
    client_id = db_test_utils.InitializeRRGClient(
        data_store.REL_DB,
        os_type=rrg_os_pb2.LINUX,
    )

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"

    user_foo = snapshot.knowledge_base.users.add()
    user_foo.username = "foo"
    user_foo.homedir = "/home/foo"

    user_bar = snapshot.knowledge_base.users.add()
    user_bar.username = "bar"
    user_bar.homedir = "/home/bar"

    data_store.REL_DB.WriteClientSnapshot(snapshot)

    artifact = artifact_pb2.Artifact()
    artifact.name = "InterpolatedPathExample"
    artifact.doc = "An example artifact with an interpolated path to collect"

    artifact_source = artifact.sources.add()
    artifact_source.type = artifact_pb2.ArtifactSource.PATH

    attr_paths = artifact_source.attributes.dat.add()
    attr_paths.k.string = "paths"
    attr_paths.v.list.content.add().string = "%%users.homedir%%/quux"

    artifact_registry.REGISTRY.RegisterArtifact(
        mig_artifacts.ToRDFArtifact(artifact)
    )

    args = flows_pb2.ArtifactCollectorFlowArgs()
    args.artifact_list.append("InterpolatedPathExample")

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=collectors.ArtifactCollectorFlow,
        flow_args=mig_artifacts.ToRDFArtifactCollectorFlowArgs(args),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/home/foo/quux": os.urandom(42),
            "/home/bar/quux": os.urandom(1337),
        }),
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_results = data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0, 128)
    self.assertLen(flow_results, 2)

    results_by_path = {}
    for flow_result in flow_results:
      result = jobs_pb2.StatEntry()
      self.assertTrue(flow_result.payload.Unpack(result))
      self.assertEqual(flow_result.tag, "artifact:InterpolatedPathExample")

      results_by_path[result.pathspec.path] = result

    self.assertTrue(stat.S_ISREG(results_by_path["/home/foo/quux"].st_mode))
    self.assertEqual(results_by_path["/home/foo/quux"].st_size, 42)
    self.assertGreater(results_by_path["/home/foo/quux"].st_atime, 0)
    self.assertGreater(results_by_path["/home/foo/quux"].st_mtime, 0)
    self.assertGreater(results_by_path["/home/foo/quux"].st_btime, 0)

    self.assertTrue(stat.S_ISREG(results_by_path["/home/bar/quux"].st_mode))
    self.assertEqual(results_by_path["/home/bar/quux"].st_size, 1337)
    self.assertGreater(results_by_path["/home/bar/quux"].st_atime, 0)
    self.assertGreater(results_by_path["/home/bar/quux"].st_mtime, 0)
    self.assertGreater(results_by_path["/home/bar/quux"].st_btime, 0)

    path_info_foo = data_store.REL_DB.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("home", "foo", "quux"),
    )
    self.assertEqual(path_info_foo.stat_entry.pathspec.path, "/home/foo/quux")
    self.assertEqual(path_info_foo.stat_entry.st_size, 42)

    path_info_bar = data_store.REL_DB.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("home", "bar", "quux"),
    )
    self.assertEqual(path_info_bar.stat_entry.pathspec.path, "/home/bar/quux")
    self.assertEqual(path_info_bar.stat_entry.st_size, 1337)

  def testRRGPath_Windows(self):
    client_id = db_test_utils.InitializeRRGClient(
        data_store.REL_DB,
        os_type=rrg_os_pb2.WINDOWS,
    )

    # We write a dummy snapshot as otherwise the artifact collector will launch
    # an extra interrogation flow at first.
    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Windows"
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    artifact = artifact_pb2.Artifact()
    artifact.name = "WindowsPathExample"
    artifact.doc = "An example artifact with a Windows path to collect"

    artifact_source = artifact.sources.add()
    artifact_source.type = artifact_pb2.ArtifactSource.PATH

    attr_paths = artifact_source.attributes.dat.add()
    attr_paths.k.string = "paths"
    attr_paths.v.list.content.add().string = "X:\\Foo Bar\\baz.exe"

    artifact_registry.REGISTRY.RegisterArtifact(
        mig_artifacts.ToRDFArtifact(artifact)
    )

    args = flows_pb2.ArtifactCollectorFlowArgs()
    args.artifact_list.append("WindowsPathExample")

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=collectors.ArtifactCollectorFlow,
        flow_args=mig_artifacts.ToRDFArtifactCollectorFlowArgs(args),
        handlers=rrg_test_lib.FakeWindowsFileHandlers({
            "X:\\Foo Bar\\baz.exe": os.urandom(303),
        }),
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_results = data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0, 128)
    self.assertLen(flow_results, 1)

    result = jobs_pb2.StatEntry()
    self.assertTrue(flow_results[0].payload.Unpack(result))
    self.assertEqual(flow_results[0].tag, "artifact:WindowsPathExample")

    self.assertEqual(result.pathspec.pathtype, jobs_pb2.PathSpec.PathType.OS)
    self.assertEqual(result.pathspec.path, "X:/Foo Bar/baz.exe")
    self.assertTrue(stat.S_ISREG(result.st_mode))
    self.assertEqual(result.st_size, 303)
    self.assertGreater(result.st_atime, 0)
    self.assertGreater(result.st_mtime, 0)
    self.assertGreater(result.st_btime, 0)

    path_info = data_store.REL_DB.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("X:", "Foo Bar", "baz.exe"),
    )
    self.assertEqual(path_info.stat_entry.pathspec.path, "X:/Foo Bar/baz.exe")
    self.assertEqual(path_info.stat_entry.st_size, 303)

  def testRRGPath_Overlap(self):
    client_id = db_test_utils.InitializeRRGClient(
        data_store.REL_DB,
        os_type=rrg_os_pb2.LINUX,
    )

    # We write a dummy snapshot as otherwise the artifact collector will launch
    # an extra interrogation flow at first.
    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    artifact = artifact_pb2.Artifact()
    artifact.name = "PathWithOverlapsExample"
    artifact.doc = "An example artifact with overlapping paths to collect"

    artifact_source = artifact.sources.add()
    artifact_source.type = artifact_pb2.ArtifactSource.PATH

    attr_paths = artifact_source.attributes.dat.add()
    attr_paths.k.string = "paths"
    attr_paths.v.list.content.add().string = "/foo/*.bin"
    attr_paths.v.list.content.add().string = "/*/thud.bin"

    artifact_registry.REGISTRY.RegisterArtifact(
        mig_artifacts.ToRDFArtifact(artifact)
    )

    args = flows_pb2.ArtifactCollectorFlowArgs()
    args.artifact_list.append("PathWithOverlapsExample")

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=collectors.ArtifactCollectorFlow,
        flow_args=mig_artifacts.ToRDFArtifactCollectorFlowArgs(args),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/thud.bin": b"",
            "/foo/thud.txt": b"",
            "/foo/quux.bin": b"",
            "/bar/thud.bin": b"",
            "/bar/quux.bin": b"",
        }),
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_results = data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0, 128)
    self.assertLen(flow_results, 3)

    results_by_path = {}
    for flow_result in flow_results:
      result = jobs_pb2.StatEntry()
      self.assertTrue(flow_result.payload.Unpack(result))
      self.assertEqual(flow_result.tag, "artifact:PathWithOverlapsExample")

      results_by_path[result.pathspec.path] = result

    self.assertIn("/foo/thud.bin", results_by_path)
    self.assertIn("/foo/quux.bin", results_by_path)
    self.assertIn("/bar/thud.bin", results_by_path)
    self.assertNotIn("/foo/thud.txt", results_by_path)
    self.assertNotIn("/bar/quux.bin", results_by_path)

  def testRRGPath_Mixed(self):
    client_id = db_test_utils.InitializeRRGClient(
        data_store.REL_DB,
        os_type=rrg_os_pb2.LINUX,
    )

    # We write a dummy snapshot as otherwise the artifact collector will launch
    # an extra interrogation flow at first.
    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    artifact = artifact_pb2.Artifact()
    artifact.name = "PathWithMixedGlobsExample"
    artifact.doc = "An example artifact with globbed and not paths to collect"

    artifact_source = artifact.sources.add()
    artifact_source.type = artifact_pb2.ArtifactSource.PATH

    attr_paths = artifact_source.attributes.dat.add()
    attr_paths.k.string = "paths"
    attr_paths.v.list.content.add().string = "/foo/thud.bin"
    attr_paths.v.list.content.add().string = "/ba?/*.txt"

    artifact_registry.REGISTRY.RegisterArtifact(
        mig_artifacts.ToRDFArtifact(artifact)
    )

    args = flows_pb2.ArtifactCollectorFlowArgs()
    args.artifact_list.append("PathWithMixedGlobsExample")

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=collectors.ArtifactCollectorFlow,
        flow_args=mig_artifacts.ToRDFArtifactCollectorFlowArgs(args),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/thud.bin": b"",
            "/bar/quux.txt": b"",
            "/bar/quux.bin": b"",
            "/baz/quux.txt": b"",
            "/baz/quux.bin": b"",
            "/norf/quux.txt": b"",
            "/norf/quux.bin": b"",
        }),
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_results = data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0, 128)
    self.assertLen(flow_results, 3)

    results_by_path = {}
    for flow_result in flow_results:
      result = jobs_pb2.StatEntry()
      self.assertTrue(flow_result.payload.Unpack(result))
      self.assertEqual(flow_result.tag, "artifact:PathWithMixedGlobsExample")

      results_by_path[result.pathspec.path] = result

    self.assertIn("/foo/thud.bin", results_by_path)
    self.assertIn("/bar/quux.txt", results_by_path)
    self.assertIn("/baz/quux.txt", results_by_path)

    self.assertNotIn("/norf/quux.txt", results_by_path)
    self.assertNotIn("/norf/quux.bin", results_by_path)

  def testRRGFile_Simple(self):
    client_id = db_test_utils.InitializeRRGClient(
        data_store.REL_DB,
        os_type=rrg_os_pb2.LINUX,
    )

    # We write a dummy snapshot as otherwise the artifact collector will launch
    # an extra interrogation flow at first.
    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    artifact = artifact_pb2.Artifact()
    artifact.name = "FileExample"
    artifact.doc = "An example artifact with a file to collect"

    artifact_source = artifact.sources.add()
    artifact_source.type = artifact_pb2.ArtifactSource.FILE

    attr_paths = artifact_source.attributes.dat.add()
    attr_paths.k.string = "paths"
    attr_paths.v.list.content.add().string = "/foo/bar"

    artifact_registry.REGISTRY.RegisterArtifact(
        mig_artifacts.ToRDFArtifact(artifact)
    )

    args = flows_pb2.ArtifactCollectorFlowArgs()
    args.artifact_list.append("FileExample")

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=collectors.ArtifactCollectorFlow,
        flow_args=mig_artifacts.ToRDFArtifactCollectorFlowArgs(args),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/bar": b"\xff" * 42,
        }),
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_progress = flows_pb2.ArtifactCollectorFlowProgress()
    self.assertTrue(flow_obj.progress.Unpack(flow_progress))
    self.assertLen(flow_progress.artifacts, 1)
    self.assertEqual(flow_progress.artifacts[0].name, "FileExample")
    self.assertEqual(flow_progress.artifacts[0].num_results, 1)
    self.assertEqual(
        flow_progress.artifacts[0].status,
        flows_pb2.ArtifactProgress.SUCCESS,
    )

    flow_results = data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0, 128)
    self.assertLen(flow_results, 1)

    result = jobs_pb2.StatEntry()
    self.assertTrue(flow_results[0].payload.Unpack(result))
    self.assertEqual(flow_results[0].tag, "artifact:FileExample")

    self.assertEqual(result.pathspec.pathtype, jobs_pb2.PathSpec.PathType.OS)
    self.assertEqual(result.pathspec.path, "/foo/bar")
    self.assertTrue(stat.S_ISREG(result.st_mode))
    self.assertEqual(result.st_size, 42)
    self.assertGreater(result.st_atime, 0)
    self.assertGreater(result.st_mtime, 0)
    self.assertGreater(result.st_btime, 0)

    path_info = data_store.REL_DB.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("foo", "bar"),
    )
    self.assertEqual(path_info.stat_entry.pathspec.path, "/foo/bar")
    self.assertEqual(path_info.stat_entry.st_size, 42)
    self.assertEqual(
        path_info.hash_entry.sha256,
        hashlib.sha256(b"\xff" * 42).digest(),
    )

    file = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("foo", "bar"),
        )
    )
    self.assertEqual(file.read(), b"\xff" * 42)

  def testRRGFile_Empty(self):
    client_id = db_test_utils.InitializeRRGClient(
        data_store.REL_DB,
        os_type=rrg_os_pb2.LINUX,
    )

    # We write a dummy snapshot as otherwise the artifact collector will launch
    # an extra interrogation flow at first.
    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    artifact = artifact_pb2.Artifact()
    artifact.name = "EmptyFileExample"
    artifact.doc = "An example artifact with an empty file to collect"

    artifact_source = artifact.sources.add()
    artifact_source.type = artifact_pb2.ArtifactSource.FILE

    attr_paths = artifact_source.attributes.dat.add()
    attr_paths.k.string = "paths"
    attr_paths.v.list.content.add().string = "/foo/bar"

    artifact_registry.REGISTRY.RegisterArtifact(
        mig_artifacts.ToRDFArtifact(artifact)
    )

    args = flows_pb2.ArtifactCollectorFlowArgs()
    args.artifact_list.append("EmptyFileExample")

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=collectors.ArtifactCollectorFlow,
        flow_args=mig_artifacts.ToRDFArtifactCollectorFlowArgs(args),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/bar": b"",
        }),
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_progress = flows_pb2.ArtifactCollectorFlowProgress()
    self.assertTrue(flow_obj.progress.Unpack(flow_progress))
    self.assertLen(flow_progress.artifacts, 1)
    self.assertEqual(flow_progress.artifacts[0].name, "EmptyFileExample")
    self.assertEqual(flow_progress.artifacts[0].num_results, 1)
    self.assertEqual(
        flow_progress.artifacts[0].status,
        flows_pb2.ArtifactProgress.SUCCESS,
    )

    flow_results = data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0, 128)
    self.assertLen(flow_results, 1)

    result = jobs_pb2.StatEntry()
    self.assertTrue(flow_results[0].payload.Unpack(result))
    self.assertEqual(flow_results[0].tag, "artifact:EmptyFileExample")

    self.assertEqual(result.pathspec.pathtype, jobs_pb2.PathSpec.PathType.OS)
    self.assertEqual(result.pathspec.path, "/foo/bar")
    self.assertTrue(stat.S_ISREG(result.st_mode))
    self.assertEqual(result.st_size, 0)
    self.assertGreater(result.st_atime, 0)
    self.assertGreater(result.st_mtime, 0)
    self.assertGreater(result.st_btime, 0)

    path_info = data_store.REL_DB.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("foo", "bar"),
    )
    self.assertEqual(path_info.stat_entry.pathspec.path, "/foo/bar")
    self.assertEqual(path_info.stat_entry.st_size, 0)
    self.assertEqual(
        path_info.hash_entry.sha256,
        hashlib.sha256(b"").digest(),
    )

    file = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("foo", "bar"),
        )
    )
    self.assertEqual(file.read(), b"")

  def testRRGFile_EmptyAndNotEmpty(self):
    client_id = db_test_utils.InitializeRRGClient(
        data_store.REL_DB,
        os_type=rrg_os_pb2.LINUX,
    )

    # We write a dummy snapshot as otherwise the artifact collector will launch
    # an extra interrogation flow at first.
    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    artifact = artifact_pb2.Artifact()
    artifact.name = "EmptyAndNotEmptyFileExample"
    artifact.doc = "An example artifact with an empty and not files to collect"

    artifact_source = artifact.sources.add()
    artifact_source.type = artifact_pb2.ArtifactSource.FILE

    attr_paths = artifact_source.attributes.dat.add()
    attr_paths.k.string = "paths"
    attr_paths.v.list.content.add().string = "/empty"
    attr_paths.v.list.content.add().string = "/not-empty"

    artifact_registry.REGISTRY.RegisterArtifact(
        mig_artifacts.ToRDFArtifact(artifact)
    )

    args = flows_pb2.ArtifactCollectorFlowArgs()
    args.artifact_list.append("EmptyAndNotEmptyFileExample")

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=collectors.ArtifactCollectorFlow,
        flow_args=mig_artifacts.ToRDFArtifactCollectorFlowArgs(args),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/empty": b"",
            "/not-empty": b"Lorem ipsum.",
        }),
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_progress = flows_pb2.ArtifactCollectorFlowProgress()
    self.assertTrue(flow_obj.progress.Unpack(flow_progress))
    self.assertLen(flow_progress.artifacts, 1)
    self.assertEqual(flow_progress.artifacts[0].num_results, 2)
    self.assertEqual(
        flow_progress.artifacts[0].status,
        flows_pb2.ArtifactProgress.SUCCESS,
    )

    flow_results = data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0, 128)
    self.assertLen(flow_results, 2)

    results_by_path = {}
    for flow_result in flow_results:
      result = jobs_pb2.StatEntry()
      self.assertTrue(flow_result.payload.Unpack(result))

      results_by_path[result.pathspec.path] = result

    result_empty = results_by_path["/empty"]
    self.assertTrue(stat.S_ISREG(result_empty.st_mode))
    self.assertEqual(result_empty.st_size, 0)
    self.assertGreater(result_empty.st_atime, 0)
    self.assertGreater(result_empty.st_mtime, 0)
    self.assertGreater(result_empty.st_btime, 0)

    result_not_empty = results_by_path["/not-empty"]
    self.assertTrue(stat.S_ISREG(result_not_empty.st_mode))
    self.assertEqual(result_not_empty.st_size, len(b"Lorem ipsum."))  # pylint: disable=g-generic-assert
    self.assertGreater(result_not_empty.st_atime, 0)
    self.assertGreater(result_not_empty.st_mtime, 0)
    self.assertGreater(result_not_empty.st_btime, 0)

    path_info_empty = data_store.REL_DB.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("empty",),
    )
    self.assertEqual(
        path_info_empty.stat_entry.pathspec.path,
        "/empty",
    )
    self.assertEqual(
        path_info_empty.stat_entry.st_size,
        0,
    )
    self.assertEqual(
        path_info_empty.hash_entry.sha256,
        hashlib.sha256(b"").digest(),
    )

    path_info_not_empty = data_store.REL_DB.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("not-empty",),
    )
    self.assertEqual(
        path_info_not_empty.stat_entry.pathspec.path,
        "/not-empty",
    )
    self.assertEqual(  # pylint: disable=g-generic-assert
        path_info_not_empty.stat_entry.st_size,
        len("Lorem ipsum."),
    )
    self.assertEqual(
        path_info_not_empty.hash_entry.sha256,
        hashlib.sha256(b"Lorem ipsum.").digest(),
    )

    file_empty = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("empty",),
        )
    )
    self.assertEqual(file_empty.read(), b"")

    file_not_empty = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("not-empty",),
        )
    )
    self.assertEqual(file_not_empty.read(), b"Lorem ipsum.")

  def testRRGFile_NonExisting(self):
    client_id = db_test_utils.InitializeRRGClient(
        data_store.REL_DB,
        os_type=rrg_os_pb2.LINUX,
    )

    # We write a dummy snapshot as otherwise the artifact collector will launch
    # an extra interrogation flow at first.
    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    artifact = artifact_pb2.Artifact()
    artifact.name = "NonExistingFileExample"
    artifact.doc = "An example artifact with an non-existing file to collect"

    artifact_source = artifact.sources.add()
    artifact_source.type = artifact_pb2.ArtifactSource.FILE

    attr_paths = artifact_source.attributes.dat.add()
    attr_paths.k.string = "paths"
    attr_paths.v.list.content.add().string = "/foo/bar"

    artifact_registry.REGISTRY.RegisterArtifact(
        mig_artifacts.ToRDFArtifact(artifact)
    )

    args = flows_pb2.ArtifactCollectorFlowArgs()
    args.artifact_list.append("NonExistingFileExample")

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=collectors.ArtifactCollectorFlow,
        flow_args=mig_artifacts.ToRDFArtifactCollectorFlowArgs(args),
        handlers=rrg_test_lib.FakePosixFileHandlers({}),
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_progress = flows_pb2.ArtifactCollectorFlowProgress()
    self.assertTrue(flow_obj.progress.Unpack(flow_progress))
    self.assertLen(flow_progress.artifacts, 1)
    self.assertEqual(flow_progress.artifacts[0].name, "NonExistingFileExample")
    self.assertEqual(flow_progress.artifacts[0].num_results, 0)
    self.assertEqual(
        flow_progress.artifacts[0].status,
        flows_pb2.ArtifactProgress.SUCCESS,
    )

    flow_results = data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0, 128)
    self.assertEmpty(flow_results)

  def testRRGFile_Large(self):
    client_id = db_test_utils.InitializeRRGClient(
        data_store.REL_DB,
        os_type=rrg_os_pb2.LINUX,
    )
    content = os.urandom(7 * 1024 * 1024 + 1337)  # ~7 MiB.

    # We write a dummy snapshot as otherwise the artifact collector will launch
    # an extra interrogation flow at first.
    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    artifact = artifact_pb2.Artifact()
    artifact.name = "LargeFileExample"
    artifact.doc = "An example artifact with a file to collect"

    artifact_source = artifact.sources.add()
    artifact_source.type = artifact_pb2.ArtifactSource.FILE

    attr_paths = artifact_source.attributes.dat.add()
    attr_paths.k.string = "paths"
    attr_paths.v.list.content.add().string = "/foo/bar"

    artifact_registry.REGISTRY.RegisterArtifact(
        mig_artifacts.ToRDFArtifact(artifact)
    )

    args = flows_pb2.ArtifactCollectorFlowArgs()
    args.artifact_list.append("LargeFileExample")

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=collectors.ArtifactCollectorFlow,
        flow_args=mig_artifacts.ToRDFArtifactCollectorFlowArgs(args),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/bar": content,
        }),
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_progress = flows_pb2.ArtifactCollectorFlowProgress()
    self.assertTrue(flow_obj.progress.Unpack(flow_progress))
    self.assertLen(flow_progress.artifacts, 1)
    self.assertEqual(flow_progress.artifacts[0].name, "LargeFileExample")
    self.assertEqual(flow_progress.artifacts[0].num_results, 1)
    self.assertEqual(
        flow_progress.artifacts[0].status,
        flows_pb2.ArtifactProgress.SUCCESS,
    )

    flow_results = data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0, 128)
    self.assertLen(flow_results, 1)

    result = jobs_pb2.StatEntry()
    self.assertTrue(flow_results[0].payload.Unpack(result))
    self.assertEqual(flow_results[0].tag, "artifact:LargeFileExample")

    self.assertEqual(result.pathspec.pathtype, jobs_pb2.PathSpec.PathType.OS)
    self.assertEqual(result.pathspec.path, "/foo/bar")
    self.assertTrue(stat.S_ISREG(result.st_mode))
    self.assertEqual(result.st_size, len(content))
    self.assertGreater(result.st_atime, 0)
    self.assertGreater(result.st_mtime, 0)
    self.assertGreater(result.st_btime, 0)

    path_info = data_store.REL_DB.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("foo", "bar"),
    )
    self.assertEqual(path_info.stat_entry.pathspec.path, "/foo/bar")
    self.assertEqual(path_info.stat_entry.st_size, len(content))
    self.assertEqual(
        path_info.hash_entry.sha256,
        hashlib.sha256(content).digest(),
    )

    file = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("foo", "bar"),
        )
    )
    self.assertEqual(file.read(), content)

  def testRRGFile_Duplicate(self):
    client_id = db_test_utils.InitializeRRGClient(
        data_store.REL_DB,
        os_type=rrg_os_pb2.LINUX,
    )

    # We write a dummy snapshot as otherwise the artifact collector will launch
    # an extra interrogation flow at first.
    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    artifact = artifact_pb2.Artifact()
    artifact.name = "FileDuplicateExample"
    artifact.doc = "An example artifact with a duplicated files to collect"

    artifact_source = artifact.sources.add()
    artifact_source.type = artifact_pb2.ArtifactSource.FILE

    attr_paths = artifact_source.attributes.dat.add()
    attr_paths.k.string = "paths"
    attr_paths.v.list.content.add().string = "/foo/bar"
    attr_paths.v.list.content.add().string = "/foo/bar"

    artifact_registry.REGISTRY.RegisterArtifact(
        mig_artifacts.ToRDFArtifact(artifact)
    )

    args = flows_pb2.ArtifactCollectorFlowArgs()
    args.artifact_list.append("FileDuplicateExample")

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=collectors.ArtifactCollectorFlow,
        flow_args=mig_artifacts.ToRDFArtifactCollectorFlowArgs(args),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/bar": b"\xff" * 42,
        }),
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_progress = flows_pb2.ArtifactCollectorFlowProgress()
    self.assertTrue(flow_obj.progress.Unpack(flow_progress))
    self.assertLen(flow_progress.artifacts, 1)
    self.assertEqual(flow_progress.artifacts[0].name, "FileDuplicateExample")
    # TODO: Add assertion on number of results. For the time being
    # we report the incorrect number of results here because of duplicates.
    self.assertEqual(
        flow_progress.artifacts[0].status,
        flows_pb2.ArtifactProgress.SUCCESS,
    )

    flow_results = data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0, 128)
    self.assertLen(flow_results, 1)

    result = jobs_pb2.StatEntry()
    self.assertTrue(flow_results[0].payload.Unpack(result))
    self.assertEqual(flow_results[0].tag, "artifact:FileDuplicateExample")

    self.assertEqual(result.pathspec.pathtype, jobs_pb2.PathSpec.PathType.OS)
    self.assertEqual(result.pathspec.path, "/foo/bar")
    self.assertTrue(stat.S_ISREG(result.st_mode))
    self.assertEqual(result.st_size, 42)
    self.assertGreater(result.st_atime, 0)
    self.assertGreater(result.st_mtime, 0)
    self.assertGreater(result.st_btime, 0)

    path_info = data_store.REL_DB.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("foo", "bar"),
    )
    self.assertEqual(path_info.stat_entry.pathspec.path, "/foo/bar")
    self.assertEqual(path_info.stat_entry.st_size, 42)
    self.assertEqual(
        path_info.hash_entry.sha256,
        hashlib.sha256(b"\xff" * 42).digest(),
    )

    file = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("foo", "bar"),
        )
    )
    self.assertEqual(file.read(), b"\xff" * 42)

  def testRRGFile_Glob(self):
    client_id = db_test_utils.InitializeRRGClient(
        data_store.REL_DB,
        os_type=rrg_os_pb2.LINUX,
    )

    # We write a dummy snapshot as otherwise the artifact collector will launch
    # an extra interrogation flow at first.
    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    artifact = artifact_pb2.Artifact()
    artifact.name = "FileWithGlobExample"
    artifact.doc = "An example artifact with globbed file to collect"

    artifact_source = artifact.sources.add()
    artifact_source.type = artifact_pb2.ArtifactSource.FILE

    attr_paths = artifact_source.attributes.dat.add()
    attr_paths.k.string = "paths"
    attr_paths.v.list.content.add().string = "/foo/ba*"

    artifact_registry.REGISTRY.RegisterArtifact(
        mig_artifacts.ToRDFArtifact(artifact)
    )

    args = flows_pb2.ArtifactCollectorFlowArgs()
    args.artifact_list.append("FileWithGlobExample")

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=collectors.ArtifactCollectorFlow,
        flow_args=mig_artifacts.ToRDFArtifactCollectorFlowArgs(args),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/bar": b"BAR",
            "/foo/baz": b"BAZ",
        }),
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_progress = flows_pb2.ArtifactCollectorFlowProgress()
    self.assertTrue(flow_obj.progress.Unpack(flow_progress))
    self.assertLen(flow_progress.artifacts, 1)
    self.assertEqual(flow_progress.artifacts[0].name, "FileWithGlobExample")
    self.assertEqual(flow_progress.artifacts[0].num_results, 2)
    self.assertEqual(
        flow_progress.artifacts[0].status,
        flows_pb2.ArtifactProgress.SUCCESS,
    )

    flow_results = data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0, 128)
    self.assertLen(flow_results, 2)

    results_by_path = {}
    for flow_result in flow_results:
      result = jobs_pb2.StatEntry()
      self.assertTrue(flow_result.payload.Unpack(result))
      self.assertEqual(flow_result.tag, "artifact:FileWithGlobExample")

      results_by_path[result.pathspec.path] = result

    self.assertTrue(stat.S_ISREG(results_by_path["/foo/bar"].st_mode))
    self.assertEqual(results_by_path["/foo/bar"].st_size, 3)

    self.assertTrue(stat.S_ISREG(results_by_path["/foo/baz"].st_mode))
    self.assertEqual(results_by_path["/foo/baz"].st_size, 3)

    path_info_bar = data_store.REL_DB.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("foo", "bar"),
    )
    self.assertEqual(path_info_bar.stat_entry.pathspec.path, "/foo/bar")
    self.assertEqual(path_info_bar.stat_entry.st_size, 3)
    self.assertEqual(
        path_info_bar.hash_entry.sha256,
        hashlib.sha256(b"BAR").digest(),
    )

    path_info_baz = data_store.REL_DB.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("foo", "baz"),
    )
    self.assertEqual(path_info_baz.stat_entry.pathspec.path, "/foo/baz")
    self.assertEqual(path_info_baz.stat_entry.st_size, 3)
    self.assertEqual(
        path_info_baz.hash_entry.sha256,
        hashlib.sha256(b"BAZ").digest(),
    )

    file_bar = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("foo", "bar"),
        )
    )
    self.assertEqual(file_bar.read(), b"BAR")

    file_baz = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("foo", "baz"),
        )
    )
    self.assertEqual(file_baz.read(), b"BAZ")

  def testRRGFile_Glob_Overlap(self):
    client_id = db_test_utils.InitializeRRGClient(
        data_store.REL_DB,
        os_type=rrg_os_pb2.LINUX,
    )

    # We write a dummy snapshot as otherwise the artifact collector will launch
    # an extra interrogation flow at first.
    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    artifact = artifact_pb2.Artifact()
    artifact.name = "FileWithGlobOverlapExample"
    artifact.doc = "An example artifact with overlapping globs to collect"

    artifact_source = artifact.sources.add()
    artifact_source.type = artifact_pb2.ArtifactSource.FILE

    attr_paths = artifact_source.attributes.dat.add()
    attr_paths.k.string = "paths"
    attr_paths.v.list.content.add().string = "/*/bar"
    attr_paths.v.list.content.add().string = "/*/bar-baz"

    artifact_registry.REGISTRY.RegisterArtifact(
        mig_artifacts.ToRDFArtifact(artifact)
    )

    args = flows_pb2.ArtifactCollectorFlowArgs()
    args.artifact_list.append("FileWithGlobOverlapExample")

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=collectors.ArtifactCollectorFlow,
        flow_args=mig_artifacts.ToRDFArtifactCollectorFlowArgs(args),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/bar": b"BAR",
            "/foo/bar-baz": b"BAZ",
        }),
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_progress = flows_pb2.ArtifactCollectorFlowProgress()
    self.assertTrue(flow_obj.progress.Unpack(flow_progress))
    self.assertLen(flow_progress.artifacts, 1)
    # TODO: Add assertion on number of results. For the time being
    # we report the incorrect number of results here because of duplicates.
    self.assertEqual(
        flow_progress.artifacts[0].status,
        flows_pb2.ArtifactProgress.SUCCESS,
    )

    flow_results = data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0, 128)
    self.assertLen(flow_results, 2)

    results_by_path = {}
    for flow_result in flow_results:
      result = jobs_pb2.StatEntry()
      self.assertTrue(flow_result.payload.Unpack(result))
      self.assertEqual(flow_result.tag, "artifact:FileWithGlobOverlapExample")

      results_by_path[result.pathspec.path] = result

    self.assertTrue(stat.S_ISREG(results_by_path["/foo/bar"].st_mode))
    self.assertEqual(results_by_path["/foo/bar"].st_size, 3)

    self.assertTrue(stat.S_ISREG(results_by_path["/foo/bar-baz"].st_mode))
    self.assertEqual(results_by_path["/foo/bar-baz"].st_size, 3)

    path_info_bar = data_store.REL_DB.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("foo", "bar"),
    )
    self.assertEqual(path_info_bar.stat_entry.pathspec.path, "/foo/bar")
    self.assertEqual(path_info_bar.stat_entry.st_size, 3)
    self.assertEqual(
        path_info_bar.hash_entry.sha256,
        hashlib.sha256(b"BAR").digest(),
    )

    path_info_baz = data_store.REL_DB.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("foo", "bar-baz"),
    )
    self.assertEqual(path_info_baz.stat_entry.pathspec.path, "/foo/bar-baz")
    self.assertEqual(path_info_baz.stat_entry.st_size, 3)
    self.assertEqual(
        path_info_baz.hash_entry.sha256,
        hashlib.sha256(b"BAZ").digest(),
    )

    file_bar = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("foo", "bar"),
        )
    )
    self.assertEqual(file_bar.read(), b"BAR")

    file_baz = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("foo", "bar-baz"),
        )
    )
    self.assertEqual(file_baz.read(), b"BAZ")

  def testRRGFile_BlobstoreDelay(self):
    client_id = db_test_utils.InitializeRRGClient(
        data_store.REL_DB,
        os_type=rrg_os_pb2.LINUX,
    )

    # We write a dummy snapshot as otherwise the artifact collector will launch
    # an extra interrogation flow at first.
    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    artifact = artifact_pb2.Artifact()
    artifact.name = "FileWithDelayExample"
    artifact.doc = "An example artifact with a file and delayed blobstore"

    artifact_source = artifact.sources.add()
    artifact_source.type = artifact_pb2.ArtifactSource.FILE

    attr_paths = artifact_source.attributes.dat.add()
    attr_paths.k.string = "paths"
    attr_paths.v.list.content.add().string = "/foo/bar"

    artifact_registry.REGISTRY.RegisterArtifact(
        mig_artifacts.ToRDFArtifact(artifact)
    )

    args = flows_pb2.ArtifactCollectorFlowArgs()
    args.artifact_list.append("FileWithDelayExample")

    class DelayedBlobstore(blob_store.BlobStore):

      def __init__(self, delegate: blob_store.BlobStore):
        self._delegate = delegate
        self._attempts = 0

      def WriteBlobs(
          self,
          blobs: dict[models_blobs.BlobID, bytes],
      ) -> None:
        return self._delegate.WriteBlobs(blobs)

      def ReadBlobs(
          self,
          blob_ids: Iterable[models_blobs.BlobID],
      ) -> dict[models_blobs.BlobID, Optional[bytes]]:
        self._attempts += 1
        if self._attempts <= 3:
          return {blob_id: None for blob_id in blob_ids}
        else:
          return self._delegate.ReadBlobs(blob_ids)

      def CheckBlobsExist(
          self,
          blob_ids: Iterable[models_blobs.BlobID],
      ) -> dict[models_blobs.BlobID, bool]:
        self._attempts += 1
        if self._attempts <= 3:
          return {blob_id: None for blob_id in blob_ids}
        else:
          return self._delegate.CheckBlobsExist(blob_ids)

    self.enter_context(
        mock.patch.object(
            data_store,
            "BLOBS",
            DelayedBlobstore(data_store.BLOBS),
        )
    )
    self.enter_context(
        mock.patch.object(
            collectors.ArtifactCollectorFlow,
            "_BLOB_WAIT_DELAY",
            rdfvalue.Duration(0),
        )
    )

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=collectors.ArtifactCollectorFlow,
        flow_args=mig_artifacts.ToRDFArtifactCollectorFlowArgs(args),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/bar": b"\xff" * 42,
        }),
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_progress = flows_pb2.ArtifactCollectorFlowProgress()
    self.assertTrue(flow_obj.progress.Unpack(flow_progress))
    self.assertLen(flow_progress.artifacts, 1)
    self.assertEqual(flow_progress.artifacts[0].name, "FileWithDelayExample")
    self.assertEqual(flow_progress.artifacts[0].num_results, 1)
    self.assertEqual(
        flow_progress.artifacts[0].status,
        flows_pb2.ArtifactProgress.SUCCESS,
    )

    flow_results = data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0, 128)
    self.assertLen(flow_results, 1)

    result = jobs_pb2.StatEntry()
    self.assertTrue(flow_results[0].payload.Unpack(result))
    self.assertEqual(flow_results[0].tag, "artifact:FileWithDelayExample")

    self.assertEqual(result.pathspec.pathtype, jobs_pb2.PathSpec.PathType.OS)
    self.assertEqual(result.pathspec.path, "/foo/bar")
    self.assertTrue(stat.S_ISREG(result.st_mode))
    self.assertEqual(result.st_size, 42)
    self.assertGreater(result.st_atime, 0)
    self.assertGreater(result.st_mtime, 0)
    self.assertGreater(result.st_btime, 0)

    path_info = data_store.REL_DB.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("foo", "bar"),
    )
    self.assertEqual(path_info.stat_entry.pathspec.path, "/foo/bar")
    self.assertEqual(path_info.stat_entry.st_size, 42)
    self.assertEqual(
        path_info.hash_entry.sha256,
        hashlib.sha256(b"\xff" * 42).digest(),
    )

    file = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("foo", "bar"),
        )
    )
    self.assertEqual(file.read(), b"\xff" * 42)

  def testRRGFile_MultipleArtifacts(self):
    client_id = db_test_utils.InitializeRRGClient(
        data_store.REL_DB,
        os_type=rrg_os_pb2.LINUX,
    )

    # We write a dummy snapshot as otherwise the artifact collector will launch
    # an extra interrogation flow at first.
    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    artifact1 = artifact_pb2.Artifact()
    artifact1.name = "FileExample1"
    artifact1.doc = "An example artifact with a file to collect"

    artifact1_source = artifact1.sources.add()
    artifact1_source.type = artifact_pb2.ArtifactSource.FILE

    attr_paths = artifact1_source.attributes.dat.add()
    attr_paths.k.string = "paths"
    attr_paths.v.list.content.add().string = "/foo/bar"

    artifact2 = artifact_pb2.Artifact()
    artifact2.name = "FileExample2"
    artifact2.doc = "An example artifact with a file to collect"

    artifact2_source = artifact2.sources.add()
    artifact2_source.type = artifact_pb2.ArtifactSource.FILE

    attr_paths = artifact2_source.attributes.dat.add()
    attr_paths.k.string = "paths"
    attr_paths.v.list.content.add().string = "/foo/baz"

    artifact_registry.REGISTRY.RegisterArtifact(
        mig_artifacts.ToRDFArtifact(artifact1)
    )
    artifact_registry.REGISTRY.RegisterArtifact(
        mig_artifacts.ToRDFArtifact(artifact2)
    )

    args = flows_pb2.ArtifactCollectorFlowArgs()
    args.artifact_list.append("FileExample1")
    args.artifact_list.append("FileExample2")

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=collectors.ArtifactCollectorFlow,
        flow_args=mig_artifacts.ToRDFArtifactCollectorFlowArgs(args),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/bar": b"\xff" * 42,
            "/foo/baz": b"\x00" * 1337,
        }),
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_progress = flows_pb2.ArtifactCollectorFlowProgress()
    self.assertTrue(flow_obj.progress.Unpack(flow_progress))
    self.assertLen(flow_progress.artifacts, 2)

    artifact_progress_by_name = {
        artifact_progress.name: artifact_progress
        for artifact_progress in flow_progress.artifacts
    }

    self.assertIn("FileExample1", artifact_progress_by_name)
    self.assertIn("FileExample2", artifact_progress_by_name)

    self.assertEqual(artifact_progress_by_name["FileExample1"].num_results, 1)
    self.assertEqual(artifact_progress_by_name["FileExample2"].num_results, 1)

    self.assertEqual(
        artifact_progress_by_name["FileExample1"].status,
        flows_pb2.ArtifactProgress.SUCCESS,
    )
    self.assertEqual(
        artifact_progress_by_name["FileExample2"].status,
        flows_pb2.ArtifactProgress.SUCCESS,
    )

    flow_results = data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0, 128)
    self.assertLen(flow_results, 2)

    flow_result_tags = [flow_result.tag for flow_result in flow_results]
    self.assertIn("artifact:FileExample1", flow_result_tags)
    self.assertIn("artifact:FileExample2", flow_result_tags)

    results_by_path = {}
    for flow_result in flow_results:
      result = jobs_pb2.StatEntry()
      self.assertTrue(flow_result.payload.Unpack(result))

      results_by_path[result.pathspec.path] = result

    result_bar = results_by_path["/foo/bar"]
    self.assertTrue(stat.S_ISREG(result_bar.st_mode))
    self.assertEqual(result_bar.st_size, 42)
    self.assertGreater(result_bar.st_atime, 0)
    self.assertGreater(result_bar.st_mtime, 0)
    self.assertGreater(result_bar.st_btime, 0)

    result_baz = results_by_path["/foo/baz"]
    self.assertTrue(stat.S_ISREG(result_baz.st_mode))
    self.assertEqual(result_baz.st_size, 1337)
    self.assertGreater(result_baz.st_atime, 0)
    self.assertGreater(result_baz.st_mtime, 0)
    self.assertGreater(result_baz.st_btime, 0)

    path_info_bar = data_store.REL_DB.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("foo", "bar"),
    )
    self.assertEqual(path_info_bar.stat_entry.pathspec.path, "/foo/bar")
    self.assertEqual(path_info_bar.stat_entry.st_size, 42)
    self.assertEqual(
        path_info_bar.hash_entry.sha256,
        hashlib.sha256(b"\xff" * 42).digest(),
    )

    path_info_baz = data_store.REL_DB.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("foo", "baz"),
    )
    self.assertEqual(path_info_baz.stat_entry.pathspec.path, "/foo/baz")
    self.assertEqual(path_info_baz.stat_entry.st_size, 1337)
    self.assertEqual(
        path_info_baz.hash_entry.sha256,
        hashlib.sha256(b"\x00" * 1337).digest(),
    )

    file_bar = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("foo", "bar"),
        )
    )
    self.assertEqual(file_bar.read(), b"\xff" * 42)

    file_baz = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("foo", "baz"),
        )
    )
    self.assertEqual(file_baz.read(), b"\x00" * 1337)

  def testRRGFile_MultipleArtifacts_SameFile(self):
    client_id = db_test_utils.InitializeRRGClient(
        data_store.REL_DB,
        os_type=rrg_os_pb2.LINUX,
    )

    # We write a dummy snapshot as otherwise the artifact collector will launch
    # an extra interrogation flow at first.
    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    artifact1 = artifact_pb2.Artifact()
    artifact1.name = "FileExample1"
    artifact1.doc = "An example artifact with a file to collect"

    artifact1_source = artifact1.sources.add()
    artifact1_source.type = artifact_pb2.ArtifactSource.FILE

    attr_paths = artifact1_source.attributes.dat.add()
    attr_paths.k.string = "paths"
    attr_paths.v.list.content.add().string = "/foo/bar"

    artifact2 = artifact_pb2.Artifact()
    artifact2.name = "FileExample2"
    artifact2.doc = "An example artifact with a file to collect"

    artifact2_source = artifact2.sources.add()
    artifact2_source.type = artifact_pb2.ArtifactSource.FILE

    attr_paths = artifact2_source.attributes.dat.add()
    attr_paths.k.string = "paths"
    attr_paths.v.list.content.add().string = "/foo/bar"

    artifact_registry.REGISTRY.RegisterArtifact(
        mig_artifacts.ToRDFArtifact(artifact1)
    )
    artifact_registry.REGISTRY.RegisterArtifact(
        mig_artifacts.ToRDFArtifact(artifact2)
    )

    args = flows_pb2.ArtifactCollectorFlowArgs()
    args.artifact_list.append("FileExample1")
    args.artifact_list.append("FileExample2")

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=collectors.ArtifactCollectorFlow,
        flow_args=mig_artifacts.ToRDFArtifactCollectorFlowArgs(args),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/bar": b"\xff" * 42,
        }),
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_progress = flows_pb2.ArtifactCollectorFlowProgress()
    self.assertTrue(flow_obj.progress.Unpack(flow_progress))
    self.assertLen(flow_progress.artifacts, 2)

    artifact_progress_by_name = {
        artifact_progress.name: artifact_progress
        for artifact_progress in flow_progress.artifacts
    }

    self.assertIn("FileExample1", artifact_progress_by_name)
    self.assertIn("FileExample2", artifact_progress_by_name)

    self.assertEqual(artifact_progress_by_name["FileExample1"].num_results, 1)
    self.assertEqual(artifact_progress_by_name["FileExample2"].num_results, 1)

    self.assertEqual(
        artifact_progress_by_name["FileExample1"].status,
        flows_pb2.ArtifactProgress.SUCCESS,
    )
    self.assertEqual(
        artifact_progress_by_name["FileExample2"].status,
        flows_pb2.ArtifactProgress.SUCCESS,
    )

    flow_results = data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0, 128)
    self.assertLen(flow_results, 2)

    flow_result_tags = [flow_result.tag for flow_result in flow_results]
    self.assertIn("artifact:FileExample1", flow_result_tags)
    self.assertIn("artifact:FileExample2", flow_result_tags)

    result_1 = jobs_pb2.StatEntry()
    self.assertTrue(flow_results[0].payload.Unpack(result_1))
    self.assertTrue(stat.S_ISREG(result_1.st_mode))
    self.assertEqual(result_1.st_size, 42)
    self.assertGreater(result_1.st_atime, 0)
    self.assertGreater(result_1.st_mtime, 0)
    self.assertGreater(result_1.st_btime, 0)

    result_2 = jobs_pb2.StatEntry()
    self.assertTrue(flow_results[1].payload.Unpack(result_2))
    self.assertTrue(stat.S_ISREG(result_2.st_mode))
    self.assertEqual(result_2.st_size, 42)
    self.assertGreater(result_2.st_atime, 0)
    self.assertGreater(result_2.st_mtime, 0)
    self.assertGreater(result_2.st_btime, 0)

    path_info = data_store.REL_DB.ReadPathInfo(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("foo", "bar"),
    )
    self.assertEqual(path_info.stat_entry.pathspec.path, "/foo/bar")
    self.assertEqual(path_info.stat_entry.st_size, 42)
    self.assertEqual(
        path_info.hash_entry.sha256,
        hashlib.sha256(b"\xff" * 42).digest(),
    )

    file = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("foo", "bar"),
        )
    )
    self.assertEqual(file.read(), b"\xff" * 42)

  def testRRGRegistryKey_Simple(self):
    client_id = db_test_utils.InitializeRRGClient(
        data_store.REL_DB,
        os_type=rrg_os_pb2.WINDOWS,
    )

    # We write a dummy snapshot as otherwise the artifact collector will launch
    # an extra interrogation flow at first.
    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Windows"
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    artifact = artifact_pb2.Artifact()
    artifact.name = "RegistryKeyExample"
    artifact.doc = "An example artifact with a registry key to collect"

    artifact_source = artifact.sources.add()
    artifact_source.type = artifact_pb2.ArtifactSource.REGISTRY_KEY

    attr_keys = artifact_source.attributes.dat.add()
    attr_keys.k.string = "keys"
    attr_keys.v.list.content.add().string = r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager\SubSystems"  # pylint: disable=line-too-long

    artifact_registry.REGISTRY.RegisterArtifact(
        mig_artifacts.ToRDFArtifact(artifact)
    )

    args = flows_pb2.ArtifactCollectorFlowArgs()
    args.artifact_list.append("RegistryKeyExample")

    def ListWinregValuesHandler(session: rrg_test_lib.Session) -> None:
      # pylint: disable=line-too-long
      # pyformat: disable
      args = rrg_list_winreg_values_pb2.Args()
      assert session.args.Unpack(args)

      assert args.root == rrg_winreg_pb2.LOCAL_MACHINE
      assert args.key == r"SYSTEM\CurrentControlSet\Control\Session Manager\SubSystems"
      assert args.max_depth == 0

      result = rrg_list_winreg_values_pb2.Result()
      result.root = rrg_winreg_pb2.LOCAL_MACHINE
      result.key = r"SYSTEM\CurrentControlSet\Control\Session Manager\SubSystems"
      result.value.string = "mnmsrvc"
      session.Reply(result)

      result = rrg_list_winreg_values_pb2.Result()
      result.root = rrg_winreg_pb2.LOCAL_MACHINE
      result.key = r"SYSTEM\CurrentControlSet\Control\Session Manager\SubSystems"
      result.value.name = "Debug"
      result.value.expand_string = ""
      session.Reply(result)

      result = rrg_list_winreg_values_pb2.Result()
      result.root = rrg_winreg_pb2.LOCAL_MACHINE
      result.key = r"SYSTEM\CurrentControlSet\Control\Session Manager\SubSystems"
      result.value.name = "Kmode"
      result.value.expand_string = r"\SystemRoot\System32\win32k.sys"
      session.Reply(result)
      # pylint: enable=line-too-long
      # pyformat: enable

    def ListWinregKeysHandler(session: rrg_test_lib.Session) -> None:
      # pylint: disable=line-too-long
      # pyformat: disable
      args = rrg_list_winreg_keys_pb2.Args()
      assert session.args.Unpack(args)

      assert args.root == rrg_winreg_pb2.LOCAL_MACHINE
      assert args.key == r"SYSTEM\CurrentControlSet\Control\Session Manager\SubSystems"
      assert args.max_depth == 0
      # pylint: enable=line-too-long
      # pyformat: enable

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=collectors.ArtifactCollectorFlow,
        flow_args=mig_artifacts.ToRDFArtifactCollectorFlowArgs(args),
        handlers={
            rrg_pb2.Action.LIST_WINREG_VALUES: ListWinregValuesHandler,
            rrg_pb2.Action.LIST_WINREG_KEYS: ListWinregKeysHandler,
        },
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_results = data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0, 128)
    self.assertLen(flow_results, 3)

    results_by_path = {}
    for flow_result in flow_results:
      self.assertEqual(flow_result.tag, "artifact:RegistryKeyExample")

      result = jobs_pb2.StatEntry()
      self.assertTrue(flow_result.payload.Unpack(result))

      results_by_path[result.pathspec.path] = result

    result_default = results_by_path[
        r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager\SubSystems"  # pylint:disable=line-too-long
    ]
    self.assertEqual(
        result_default.registry_type,
        jobs_pb2.StatEntry.REG_SZ,
    )
    self.assertEqual(
        result_default.registry_data.string,
        "mnmsrvc",
    )

    result_debug = results_by_path[
        r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager\SubSystems\Debug"  # pylint:disable=line-too-long
    ]
    self.assertEqual(
        result_debug.registry_type,
        jobs_pb2.StatEntry.REG_EXPAND_SZ,
    )
    self.assertEqual(
        result_debug.registry_data.string,
        "",
    )

    result_kmode = results_by_path[
        r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager\SubSystems\Kmode"  # pylint:disable=line-too-long
    ]
    self.assertEqual(
        result_kmode.registry_type,
        jobs_pb2.StatEntry.REG_EXPAND_SZ,
    )
    self.assertEqual(
        result_kmode.registry_data.string,
        r"\SystemRoot\System32\win32k.sys",
    )

  def testRRGRegistryKey_Glob(self):
    client_id = db_test_utils.InitializeRRGClient(
        data_store.REL_DB,
        os_type=rrg_os_pb2.WINDOWS,
    )

    # We write a dummy snapshot as otherwise the artifact collector will launch
    # an extra interrogation flow at first.
    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Windows"
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    artifact = artifact_pb2.Artifact()
    artifact.name = "RegistryKeyWithGlobExample"
    artifact.doc = "An example artifact with a registry key to collect"

    artifact_source = artifact.sources.add()
    artifact_source.type = artifact_pb2.ArtifactSource.REGISTRY_KEY

    attr_keys = artifact_source.attributes.dat.add()
    attr_keys.k.string = "keys"
    attr_keys.v.list.content.add().string = r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\*"  # pylint: disable=line-too-long

    artifact_registry.REGISTRY.RegisterArtifact(
        mig_artifacts.ToRDFArtifact(artifact)
    )

    args = flows_pb2.ArtifactCollectorFlowArgs()
    args.artifact_list.append("RegistryKeyWithGlobExample")

    def ListWinregValuesHandler(session: rrg_test_lib.Session) -> None:
      # pylint: disable=line-too-long
      # pyformat: disable
      args = rrg_list_winreg_values_pb2.Args()
      assert session.args.Unpack(args)

      assert args.root == rrg_winreg_pb2.LOCAL_MACHINE
      assert args.key == r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"
      assert args.max_depth == 1

      result = rrg_list_winreg_values_pb2.Result()
      result.root = rrg_winreg_pb2.LOCAL_MACHINE
      result.key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"
      result.value.string = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
      session.Reply(result)

      result = rrg_list_winreg_values_pb2.Result()
      result.root = rrg_winreg_pb2.LOCAL_MACHINE
      result.key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"
      result.value.name = "Path"
      result.value.string = r"C:\Program Files\Google\Chrome\Application"
      session.Reply(result)

      result = rrg_list_winreg_values_pb2.Result()
      result.root = rrg_winreg_pb2.LOCAL_MACHINE
      result.key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\pwsh.exe"
      result.value.string = r"C:\Program Files\PowerShell\7\pwsh.exe"
      session.Reply(result)

      result = rrg_list_winreg_values_pb2.Result()
      result.root = rrg_winreg_pb2.LOCAL_MACHINE
      result.key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\setup.exe"
      result.value.string = ""
      session.Reply(result)

      result = rrg_list_winreg_values_pb2.Result()
      result.root = rrg_winreg_pb2.LOCAL_MACHINE
      result.key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\setup.exe"
      result.value.name = "BlockOnTSNonInstallMode"
      result.value.uint32 = 1
      session.Reply(result)

      result = rrg_list_winreg_values_pb2.Result()
      result.root = rrg_winreg_pb2.LOCAL_MACHINE
      result.key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe"
      result.value.string = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
      session.Reply(result)

      result = rrg_list_winreg_values_pb2.Result()
      result.root = rrg_winreg_pb2.LOCAL_MACHINE
      result.key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe"
      result.value.name = "Path"
      result.value.string = r"C:\Program Files (x86)\Microsoft\Edge\Application"
      session.Reply(result)
      # pylint: enable=line-too-long
      # pyformat: enable

    def ListWinregKeysHandler(session: rrg_test_lib.Session) -> None:
      # pylint: disable=line-too-long
      # pyformat: disable
      args = rrg_list_winreg_keys_pb2.Args()
      assert session.args.Unpack(args)

      assert args.root == rrg_winreg_pb2.LOCAL_MACHINE
      assert args.key == r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"
      assert args.max_depth == 2

      result = rrg_list_winreg_keys_pb2.Result()
      result.root = rrg_winreg_pb2.LOCAL_MACHINE
      result.key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"

      result.subkey = r"chrome.exe"
      session.Reply(result)

      result.subkey = r"pwsh.exe"
      session.Reply(result)

      result.subkey = r"setup.exe"
      session.Reply(result)

      result.subkey = r"msedge.exe"
      session.Reply(result)

      result.subkey = r"msedge.exe\SupportedProtocols"
      session.Reply(result)
      # pylint: enable=line-too-long
      # pyformat: enable

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=collectors.ArtifactCollectorFlow,
        flow_args=mig_artifacts.ToRDFArtifactCollectorFlowArgs(args),
        handlers={
            rrg_pb2.Action.LIST_WINREG_VALUES: ListWinregValuesHandler,
            rrg_pb2.Action.LIST_WINREG_KEYS: ListWinregKeysHandler,
        },
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_results = data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0, 128)
    self.assertLen(flow_results, 7 + 1)

    result_keys_by_path = {}
    result_values_by_path = {}
    for flow_result in flow_results:
      result = jobs_pb2.StatEntry()
      self.assertTrue(flow_result.payload.Unpack(result))

      if stat.S_ISDIR(result.st_mode):
        result_keys_by_path[result.pathspec.path] = result
      else:
        result_values_by_path[result.pathspec.path] = result

    self.assertLen(result_keys_by_path, 1)
    self.assertIn(
        r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe\SupportedProtocols",  # pylint:disable=line-too-long
        result_keys_by_path,
    )

    result_chrome = result_values_by_path[
        r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"  # pylint:disable=line-too-long
    ]
    self.assertEqual(
        result_chrome.registry_type,
        jobs_pb2.StatEntry.REG_SZ,
    )
    self.assertEqual(
        result_chrome.registry_data.string,
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    )

    result_chrome_path = result_values_by_path[
        r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe\Path"  # pylint:disable=line-too-long
    ]
    self.assertEqual(
        result_chrome_path.registry_type,
        jobs_pb2.StatEntry.REG_SZ,
    )
    self.assertEqual(
        result_chrome_path.registry_data.string,
        r"C:\Program Files\Google\Chrome\Application",
    )

    result_pwsh = result_values_by_path[
        r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\pwsh.exe"  # pylint: disable=line-too-long
    ]
    self.assertEqual(
        result_pwsh.registry_type,
        jobs_pb2.StatEntry.REG_SZ,
    )
    self.assertEqual(
        result_pwsh.registry_data.string,
        r"C:\Program Files\PowerShell\7\pwsh.exe",
    )

    result_setup = result_values_by_path[
        r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\setup.exe"  # pylint: disable=line-too-long
    ]
    self.assertEqual(
        result_setup.registry_type,
        jobs_pb2.StatEntry.REG_SZ,
    )
    self.assertEqual(
        result_setup.registry_data.string,
        "",
    )
    result_setup_imode = result_values_by_path[
        r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\setup.exe\BlockOnTSNonInstallMode"  # pylint: disable=line-too-long
    ]
    self.assertEqual(
        result_setup_imode.registry_type,
        jobs_pb2.StatEntry.REG_DWORD,
    )
    self.assertEqual(
        result_setup_imode.registry_data.integer,
        1,
    )

    result_msedge = result_values_by_path[
        r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe"  # pylint: disable=line-too-long
    ]
    self.assertEqual(
        result_msedge.registry_type,
        jobs_pb2.StatEntry.REG_SZ,
    )
    self.assertEqual(
        result_msedge.registry_data.string,
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    )

    result_msedge_path = result_values_by_path[
        r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe\Path"  # pylint: disable=line-too-long
    ]
    self.assertEqual(
        result_msedge_path.registry_type,
        jobs_pb2.StatEntry.REG_SZ,
    )
    self.assertEqual(
        result_msedge_path.registry_data.string,
        r"C:\Program Files (x86)\Microsoft\Edge\Application",
    )

  def testRRGRegistryKey_RecursiveGlob(self):
    client_id = db_test_utils.InitializeRRGClient(
        data_store.REL_DB,
        os_type=rrg_os_pb2.WINDOWS,
    )

    # We write a dummy snapshot as otherwise the artifact collector will launch
    # an extra interrogation flow at first.
    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Windows"
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    artifact = artifact_pb2.Artifact()
    artifact.name = "RegistryKeyWithRecursiveGlobExample"
    artifact.doc = "An example artifact with a registry key to collect"

    artifact_source = artifact.sources.add()
    artifact_source.type = artifact_pb2.ArtifactSource.REGISTRY_KEY

    attr_keys = artifact_source.attributes.dat.add()
    attr_keys.k.string = "keys"
    attr_keys.v.list.content.add().string = r"HKEY_LOCAL_MACHINE\SOFTWARE\**2\App Paths\*"  # pylint: disable=line-too-long

    artifact_registry.REGISTRY.RegisterArtifact(
        mig_artifacts.ToRDFArtifact(artifact)
    )

    args = flows_pb2.ArtifactCollectorFlowArgs()
    args.artifact_list.append("RegistryKeyWithRecursiveGlobExample")

    def ListWinregValuesHandler(session: rrg_test_lib.Session) -> None:
      args = rrg_list_winreg_values_pb2.Args()
      assert session.args.Unpack(args)

      assert args.root == rrg_winreg_pb2.LOCAL_MACHINE
      assert args.key == r"SOFTWARE"
      assert args.max_depth == 4

      result = rrg_list_winreg_values_pb2.Result()
      result.root = rrg_winreg_pb2.LOCAL_MACHINE
      result.key = r"SOFTWARE\Microsoft\App Paths\foo.exe"
      result.value.string = r"C:\Program Files\Microsoft\Foo\foo.exe"
      session.Reply(result)

      result = rrg_list_winreg_values_pb2.Result()
      result.root = rrg_winreg_pb2.LOCAL_MACHINE
      result.key = r"SOFTWARE\Microsoft\App Paths\bar.exe"
      result.value.string = r"C:\Program Files\Microsoft\Bar\bar.exe"
      session.Reply(result)

      result = rrg_list_winreg_values_pb2.Result()
      result.root = rrg_winreg_pb2.LOCAL_MACHINE
      result.key = r"SOFTWARE\Microsoft\Irrelevant Paths\norf.exe"
      result.value.string = r"C:\Program Files\Microsoft\Norf\norf.exe"
      session.Reply(result)

      result = rrg_list_winreg_values_pb2.Result()
      result.root = rrg_winreg_pb2.LOCAL_MACHINE
      result.key = r"SOFTWARE\Google\App Paths\quux.exe"
      result.value.string = r"C:\Program Files\Google\Quux\quux.exe"
      session.Reply(result)

      result = rrg_list_winreg_values_pb2.Result()
      result.root = rrg_winreg_pb2.LOCAL_MACHINE
      result.key = r"SOFTWARE\Google\Chrome\App Paths\chrome.exe"
      result.value.string = r"C:\Program Files\Google\Chrome\chrome.exe"
      session.Reply(result)

      result = rrg_list_winreg_values_pb2.Result()
      result.root = rrg_winreg_pb2.LOCAL_MACHINE
      result.key = r"SOFTWARE\Google\Too\Deep\App Paths\blargh.exe"
      result.value.string = r"C:\Program Files\Google\Blargh\blargh.exe"
      session.Reply(result)

    def ListWinregKeysHandler(session: rrg_test_lib.Session) -> None:
      args = rrg_list_winreg_keys_pb2.Args()
      assert session.args.Unpack(args)

      assert args.root == rrg_winreg_pb2.LOCAL_MACHINE
      assert args.key == r"SOFTWARE"
      assert args.max_depth == 5

      result = rrg_list_winreg_keys_pb2.Result()
      result.root = rrg_winreg_pb2.LOCAL_MACHINE
      result.key = r"SOFTWARE"

      result.subkey = r"Microsoft"
      session.Reply(result)

      result.subkey = r"Microsoft\App Paths"
      session.Reply(result)

      result.subkey = r"Microsoft\App Paths\foo.exe"
      session.Reply(result)

      result.subkey = r"Microsoft\App Paths\bar.exe"
      session.Reply(result)

      result.subkey = r"Microsoft\Irrelevant Paths\norf.exe"
      session.Reply(result)

      result.subkey = r"Google"
      session.Reply(result)

      result.subkey = r"Google\App Paths"
      session.Reply(result)

      result.subkey = r"Google\App Paths\quux.exe"
      session.Reply(result)

      result.subkey = r"Google\Chrome"
      session.Reply(result)

      result.subkey = r"Google\Chrome\App Paths"
      session.Reply(result)

      result.subkey = r"Google\Chrome\App Paths\chrome.exe"
      session.Reply(result)

      result.subkey = r"Google\Too"
      session.Reply(result)

      result.subkey = r"Google\Too\Deep"
      session.Reply(result)

      result.subkey = r"Google\Too\Deep\App Paths"
      session.Reply(result)

      result.subkey = r"Google\Too\Deep\App Paths\blargh.exe"
      session.Reply(result)

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=collectors.ArtifactCollectorFlow,
        flow_args=mig_artifacts.ToRDFArtifactCollectorFlowArgs(args),
        handlers={
            rrg_pb2.Action.LIST_WINREG_VALUES: ListWinregValuesHandler,
            rrg_pb2.Action.LIST_WINREG_KEYS: ListWinregKeysHandler,
        },
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_results = data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0, 128)
    self.assertLen(flow_results, 4)

    result_keys_by_path = {}
    result_values_by_path = {}
    for flow_result in flow_results:
      result = jobs_pb2.StatEntry()
      self.assertTrue(flow_result.payload.Unpack(result))

      if stat.S_ISDIR(result.st_mode):
        result_keys_by_path[result.pathspec.path] = result
      else:
        result_values_by_path[result.pathspec.path] = result

    # No keys that we glob for have any subkeys, so there should be no keys
    # reported.
    self.assertEmpty(result_keys_by_path)

    result_foo = result_values_by_path[
        r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\App Paths\foo.exe"
    ]
    self.assertEqual(result_foo.registry_type, jobs_pb2.StatEntry.REG_SZ)
    self.assertEqual(
        result_foo.registry_data.string,
        r"C:\Program Files\Microsoft\Foo\foo.exe",
    )

    result_bar = result_values_by_path[
        r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\App Paths\bar.exe"
    ]
    self.assertEqual(result_bar.registry_type, jobs_pb2.StatEntry.REG_SZ)
    self.assertEqual(
        result_bar.registry_data.string,
        r"C:\Program Files\Microsoft\Bar\bar.exe",
    )

    result_quux = result_values_by_path[
        r"HKEY_LOCAL_MACHINE\SOFTWARE\Google\App Paths\quux.exe"
    ]
    self.assertEqual(result_quux.registry_type, jobs_pb2.StatEntry.REG_SZ)
    self.assertEqual(
        result_quux.registry_data.string,
        r"C:\Program Files\Google\Quux\quux.exe",
    )

    result_chrome = result_values_by_path[
        r"HKEY_LOCAL_MACHINE\SOFTWARE\Google\Chrome\App Paths\chrome.exe"
    ]
    self.assertEqual(result_chrome.registry_type, jobs_pb2.StatEntry.REG_SZ)
    self.assertEqual(
        result_chrome.registry_data.string,
        r"C:\Program Files\Google\Chrome\chrome.exe",
    )

    self.assertNotIn(
        r"SOFTWARE\Microsoft\Irrelevant Paths\norf.exe",
        result_values_by_path,
    )
    self.assertNotIn(
        r"SOFTWARE\Google\Too\Deep\App Paths\blargh.exe",
        result_values_by_path,
    )

  def testRRGRegistryKey_Interpolation(self):
    client_id = db_test_utils.InitializeRRGClient(
        data_store.REL_DB,
        os_type=rrg_os_pb2.WINDOWS,
    )

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Windows"

    user_1 = snapshot.knowledge_base.users.add()
    user_1.username = "user1"
    user_1.sid = "S-1-5-80-111-111-111"

    user_2 = snapshot.knowledge_base.users.add()
    user_2.username = "user2"
    user_2.sid = "S-1-5-80-222-222-222"

    data_store.REL_DB.WriteClientSnapshot(snapshot)

    artifact = artifact_pb2.Artifact()
    artifact.name = "InterpolatedRegistryKeyExample"
    artifact.doc = "An example artifact with a registry key to collect"

    artifact_source = artifact.sources.add()
    artifact_source.type = artifact_pb2.ArtifactSource.REGISTRY_KEY

    attr_keys = artifact_source.attributes.dat.add()
    attr_keys.k.string = "keys"
    attr_keys.v.list.content.add().string = r"HKEY_USERS\%%users.sid%%\Software\Quux"  # pylint: disable=line-too-long

    artifact_registry.REGISTRY.RegisterArtifact(
        mig_artifacts.ToRDFArtifact(artifact)
    )

    args = flows_pb2.ArtifactCollectorFlowArgs()
    args.artifact_list.append("InterpolatedRegistryKeyExample")

    def ListWinregValuesHandler(session: rrg_test_lib.Session) -> None:
      args = rrg_list_winreg_values_pb2.Args()
      assert session.args.Unpack(args)

      assert args.root == rrg_winreg_pb2.USERS

      result = rrg_list_winreg_values_pb2.Result()
      result.root = rrg_winreg_pb2.USERS

      if args.key.startswith("S-1-5-80-111-111-111\\"):
        assert args.key == r"S-1-5-80-111-111-111\Software\Quux"
        result.key = r"S-1-5-80-111-111-111\Software\Quux"
        result.value.string = "foo"
      elif args.key.startswith("S-1-5-80-222-222-222"):
        assert args.key == r"S-1-5-80-222-222-222\Software\Quux"
        result.key = r"S-1-5-80-222-222-222\Software\Quux"
        result.value.string = "bar"
      else:
        raise RuntimeError(f"Unexpected key: {args.key}")

      session.Reply(result)

    def ListWinregKeysHandler(session: rrg_test_lib.Session) -> None:
      args = rrg_list_winreg_keys_pb2.Args()
      assert session.args.Unpack(args)

      assert args.root == rrg_winreg_pb2.LOCAL_MACHINE
      assert args.max_depth == 1

      if args.key.startswith("S-1-5-80-111-111-111\\"):
        assert args.key == r"S-1-5-80-111-111-111\Software\Quux"
      elif args.key.startswith("S-1-5-80-222-222-222"):
        assert args.key == r"S-1-5-80-222-222-222\Software\Quux"
      else:
        raise RuntimeError(f"Unexpected key: {args.key}")

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=collectors.ArtifactCollectorFlow,
        flow_args=mig_artifacts.ToRDFArtifactCollectorFlowArgs(args),
        handlers={
            rrg_pb2.Action.LIST_WINREG_VALUES: ListWinregValuesHandler,
            rrg_pb2.Action.LIST_WINREG_KEYS: ListWinregKeysHandler,
        },
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_results = data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0, 128)
    self.assertLen(flow_results, 2)

    results_by_path = {}
    for flow_result in flow_results:
      result = jobs_pb2.StatEntry()
      self.assertTrue(flow_result.payload.Unpack(result))

      results_by_path[result.pathspec.path] = result

    result_1 = results_by_path[r"HKEY_USERS\S-1-5-80-111-111-111\Software\Quux"]
    self.assertEqual(result_1.registry_type, jobs_pb2.StatEntry.REG_SZ)
    self.assertEqual(result_1.registry_data.string, "foo")

    result_2 = results_by_path[r"HKEY_USERS\S-1-5-80-222-222-222\Software\Quux"]
    self.assertEqual(result_2.registry_type, jobs_pb2.StatEntry.REG_SZ)
    self.assertEqual(result_2.registry_data.string, "bar")

  def testRRGRegistryValue_Simple(self):
    client_id = db_test_utils.InitializeRRGClient(
        data_store.REL_DB,
        os_type=rrg_os_pb2.WINDOWS,
    )

    # We write a dummy snapshot as otherwise the artifact collector will launch
    # an extra interrogation flow at first.
    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Windows"
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    artifact = artifact_pb2.Artifact()
    artifact.name = "RegistryValueExample"
    artifact.doc = "An example artifact with a registry value to collect"

    artifact_source = artifact.sources.add()
    artifact_source.type = artifact_pb2.ArtifactSource.REGISTRY_VALUE

    attr_kv_pairs = artifact_source.attributes.dat.add()
    attr_kv_pairs.k.string = "key_value_pairs"

    attr_kv_pair = attr_kv_pairs.v.list.content.add()

    attr_key = attr_kv_pair.dict.dat.add()
    attr_key.k.string = "key"
    attr_key.v.string = r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager\AppCompatCache"  # pylint: disable=line-too-long

    attr_value = attr_kv_pair.dict.dat.add()
    attr_value.k.string = "value"
    attr_value.v.string = "AppCompatCache"

    artifact_registry.REGISTRY.RegisterArtifact(
        mig_artifacts.ToRDFArtifact(artifact)
    )

    args = flows_pb2.ArtifactCollectorFlowArgs()
    args.artifact_list.append("RegistryValueExample")

    def ListWinregValuesHandler(session: rrg_test_lib.Session) -> None:
      # pylint: disable=line-too-long
      # pyformat: disable
      args = rrg_list_winreg_values_pb2.Args()
      assert session.args.Unpack(args)

      assert args.root == rrg_winreg_pb2.LOCAL_MACHINE
      assert args.key == r"SYSTEM\CurrentControlSet\Control\Session Manager\AppCompatCache"
      assert args.max_depth == 0

      result = rrg_list_winreg_values_pb2.Result()
      result.root = rrg_winreg_pb2.LOCAL_MACHINE
      result.key = r"SYSTEM\CurrentControlSet\Control\Session Manager\AppCompatCache"
      result.value.string = ""
      session.Reply(result)

      result = rrg_list_winreg_values_pb2.Result()
      result.root = rrg_winreg_pb2.LOCAL_MACHINE
      result.key = r"SYSTEM\CurrentControlSet\Control\Session Manager\AppCompatCache"
      result.value.name = "AppCompatCache"
      result.value.bytes = b"\x11\x33\x77"
      session.Reply(result)

      result = rrg_list_winreg_values_pb2.Result()
      result.root = rrg_winreg_pb2.LOCAL_MACHINE
      result.key = r"SYSTEM\CurrentControlSet\Control\Session Manager\AppCompatCache"
      result.value.name = "CacheMainSdb"
      result.value.bytes = b"\xff\xff\xff"
      session.Reply(result)

      result = rrg_list_winreg_values_pb2.Result()
      result.root = rrg_winreg_pb2.LOCAL_MACHINE
      result.key = r"SYSTEM\CurrentControlSet\Control\Session Manager\AppCompatCache"
      result.value.name = "SdbTime"
      result.value.bytes = b"\x11\x22\x33"
      session.Reply(result)
      # pylint: enable=line-too-long
      # pyformat: enable

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=collectors.ArtifactCollectorFlow,
        flow_args=mig_artifacts.ToRDFArtifactCollectorFlowArgs(args),
        handlers={
            rrg_pb2.Action.LIST_WINREG_VALUES: ListWinregValuesHandler,
        },
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_results = data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0, 128)
    self.assertLen(flow_results, 1)
    self.assertEqual(flow_results[0].tag, "artifact:RegistryValueExample")

    result = jobs_pb2.StatEntry()
    self.assertTrue(flow_results[0].payload.Unpack(result))

    self.assertEqual(result.pathspec.path, r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager\AppCompatCache\AppCompatCache")  # pylint: disable=line-too-long
    self.assertEqual(result.registry_type, jobs_pb2.StatEntry.REG_BINARY)
    self.assertEqual(result.registry_data.data, b"\x11\x33\x77")

  def testRRGRegistryValue_Glob(self):
    client_id = db_test_utils.InitializeRRGClient(
        data_store.REL_DB,
        os_type=rrg_os_pb2.WINDOWS,
    )

    # We write a dummy snapshot as otherwise the artifact collector will launch
    # an extra interrogation flow at first.
    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Windows"
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    artifact = artifact_pb2.Artifact()
    artifact.name = "RegistryValueWithGlobExample"
    artifact.doc = "An example artifact with a registry value to collect"

    artifact_source = artifact.sources.add()
    artifact_source.type = artifact_pb2.ArtifactSource.REGISTRY_VALUE

    attr_kv_pairs = artifact_source.attributes.dat.add()
    attr_kv_pairs.k.string = "key_value_pairs"

    attr_kv_pair = attr_kv_pairs.v.list.content.add()

    attr_key = attr_kv_pair.dict.dat.add()
    attr_key.k.string = "key"
    attr_key.v.string = r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Active Setup\Installed Components\*"  # pylint: disable=line-too-long

    attr_value = attr_kv_pair.dict.dat.add()
    attr_value.k.string = "value"
    attr_value.v.string = "Version"

    artifact_registry.REGISTRY.RegisterArtifact(
        mig_artifacts.ToRDFArtifact(artifact)
    )

    args = flows_pb2.ArtifactCollectorFlowArgs()
    args.artifact_list.append("RegistryValueWithGlobExample")

    def ListWinregValuesHandler(session: rrg_test_lib.Session) -> None:
      # pylint: disable=line-too-long
      # pyformat: disable
      args = rrg_list_winreg_values_pb2.Args()
      assert session.args.Unpack(args)

      assert args.root == rrg_winreg_pb2.LOCAL_MACHINE
      assert args.key == r"SOFTWARE\Microsoft\Active Setup\Installed Components"
      assert args.max_depth == 1

      result = rrg_list_winreg_values_pb2.Result()
      result.root = rrg_winreg_pb2.LOCAL_MACHINE
      result.key = r"SOFTWARE\Microsoft\Active Setup\Installed Components\{11d63315-c3d1-22d4-94ab-2292a64c7e81}"
      result.value.string = "Microsoft Windows Media Player 12.0"
      session.Reply(result)

      result = rrg_list_winreg_values_pb2.Result()
      result.root = rrg_winreg_pb2.LOCAL_MACHINE
      result.key = r"SOFTWARE\Microsoft\Active Setup\Installed Components\{11d63315-c3d1-22d4-94ab-2292a64c7e81}"
      result.value.name = "Locale"
      result.value.string = "EN"
      session.Reply(result)

      result = rrg_list_winreg_values_pb2.Result()
      result.root = rrg_winreg_pb2.LOCAL_MACHINE
      result.key = r"SOFTWARE\Microsoft\Active Setup\Installed Components\{11d63315-c3d1-22d4-94ab-2292a64c7e81}"
      result.value.name = "Version"
      result.value.string = "12,0,10011,16384"
      session.Reply(result)

      result = rrg_list_winreg_values_pb2.Result()
      result.root = rrg_winreg_pb2.LOCAL_MACHINE
      result.key = r"SOFTWARE\Microsoft\Active Setup\Installed Components\{1ef288a1-b63b-25f2-8721-22e45b98eed3}"
      result.value.string = "Internet Explorer Setup Tools"
      session.Reply(result)

      result = rrg_list_winreg_values_pb2.Result()
      result.root = rrg_winreg_pb2.LOCAL_MACHINE
      result.key = r"SOFTWARE\Microsoft\Active Setup\Installed Components\{1ef288a1-b63b-25f2-8721-22e45b98eed3}"
      result.value.name = "Locale"
      result.value.string = "*"
      session.Reply(result)

      result = rrg_list_winreg_values_pb2.Result()
      result.root = rrg_winreg_pb2.LOCAL_MACHINE
      result.key = r"SOFTWARE\Microsoft\Active Setup\Installed Components\{1ef288a1-b63b-25f2-8721-22e45b98eed3}"
      result.value.name = "Version"
      result.value.string = "11,5415,22621,0"
      session.Reply(result)

      result = rrg_list_winreg_values_pb2.Result()
      result.root = rrg_winreg_pb2.LOCAL_MACHINE
      result.key = r"SOFTWARE\Microsoft\Active Setup\Installed Components\{1e421321-597b-11e1-332d-22e35e87ccb2}"
      result.value.string = "Microsoft Windows Script 5.6"
      session.Reply(result)

      result = rrg_list_winreg_values_pb2.Result()
      result.root = rrg_winreg_pb2.LOCAL_MACHINE
      result.key = r"SOFTWARE\Microsoft\Active Setup\Installed Components\{1e421321-597b-11e1-332d-22e35e87ccb2}"
      result.value.name = "Locale"
      result.value.string = "EN"
      session.Reply(result)

      result = rrg_list_winreg_values_pb2.Result()
      result.root = rrg_winreg_pb2.LOCAL_MACHINE
      result.key = r"SOFTWARE\Microsoft\Active Setup\Installed Components\{1e421321-597b-11e1-332d-22e35e87ccb2}"
      result.value.name = "Version"
      result.value.string = "5,6,0,8833"
      session.Reply(result)
      # pylint: enable=line-too-long
      # pyformat: enable

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=collectors.ArtifactCollectorFlow,
        flow_args=mig_artifacts.ToRDFArtifactCollectorFlowArgs(args),
        handlers={
            rrg_pb2.Action.LIST_WINREG_VALUES: ListWinregValuesHandler,
        },
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_results = data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0, 128)
    self.assertLen(flow_results, 3)

    results_by_path = {}
    for flow_result in flow_results:
      result = jobs_pb2.StatEntry()
      self.assertTrue(flow_result.payload.Unpack(result))

      results_by_path[result.pathspec.path] = result

    result_mplayer = results_by_path[
        r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Active Setup\Installed Components\{11d63315-c3d1-22d4-94ab-2292a64c7e81}\Version"  # pylint:disable=line-too-long
    ]
    self.assertEqual(result_mplayer.registry_type, jobs_pb2.StatEntry.REG_SZ)
    self.assertEqual(
        result_mplayer.registry_data.string,
        r"12,0,10011,16384",
    )

    result_ie_stools = results_by_path[
        r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Active Setup\Installed Components\{1ef288a1-b63b-25f2-8721-22e45b98eed3}\Version"  # pylint: disable=line-too-long
    ]
    self.assertEqual(result_ie_stools.registry_type, jobs_pb2.StatEntry.REG_SZ)
    self.assertEqual(
        result_ie_stools.registry_data.string,
        r"11,5415,22621,0",
    )

    result_winscript = results_by_path[
        r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Active Setup\Installed Components\{1e421321-597b-11e1-332d-22e35e87ccb2}\Version"  # pylint: disable=line-too-long
    ]
    self.assertEqual(result_winscript.registry_type, jobs_pb2.StatEntry.REG_SZ)
    self.assertEqual(
        result_winscript.registry_data.string,
        "5,6,0,8833",
    )

  def testRRGRegistryValue_Interpolation(self):
    client_id = db_test_utils.InitializeRRGClient(
        data_store.REL_DB,
        os_type=rrg_os_pb2.WINDOWS,
    )

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Windows"

    user_1 = snapshot.knowledge_base.users.add()
    user_1.username = "user1"
    user_1.sid = "S-1-5-80-111-111-111"

    user_2 = snapshot.knowledge_base.users.add()
    user_2.username = "user2"
    user_2.sid = "S-1-5-80-222-222-222"

    data_store.REL_DB.WriteClientSnapshot(snapshot)

    artifact = artifact_pb2.Artifact()
    artifact.name = "InterpolatedRegistryValueExample"
    artifact.doc = "An example artifact with a registry value to collect"

    artifact_source = artifact.sources.add()
    artifact_source.type = artifact_pb2.ArtifactSource.REGISTRY_VALUE

    attr_kv_pairs = artifact_source.attributes.dat.add()
    attr_kv_pairs.k.string = "key_value_pairs"

    attr_kv_pair = attr_kv_pairs.v.list.content.add()

    attr_key = attr_kv_pair.dict.dat.add()
    attr_key.k.string = "key"
    attr_key.v.string = r"HKEY_USERS\%%users.sid%%\Environment"

    attr_value = attr_kv_pair.dict.dat.add()
    attr_value.k.string = "value"
    attr_value.v.string = "Path"

    artifact_registry.REGISTRY.RegisterArtifact(
        mig_artifacts.ToRDFArtifact(artifact)
    )

    args = flows_pb2.ArtifactCollectorFlowArgs()
    args.artifact_list.append("InterpolatedRegistryValueExample")

    def ListWinregValuesHandler(session: rrg_test_lib.Session) -> None:
      args = rrg_list_winreg_values_pb2.Args()
      assert session.args.Unpack(args)

      assert args.root == rrg_winreg_pb2.USERS
      assert args.max_depth == 0

      result = rrg_list_winreg_values_pb2.Result()
      result.root = rrg_winreg_pb2.USERS

      if args.key == r"S-1-5-80-111-111-111\Environment":
        result.key = r"S-1-5-80-111-111-111\Environment"

        result.value.name = "Path"
        result.value.expand_string = r"C:\Users\user1\AppData\Foo\bin"
        session.Reply(result)

        result.value.name = "TEMP"
        result.value.expand_string = r"C:\Users\user1\AppData\Local\Temp"
        session.Reply(result)
      elif args.key == r"S-1-5-80-222-222-222\Environment":
        result.key = r"S-1-5-80-222-222-222\Environment"

        result.value.name = "Path"
        result.value.expand_string = r"C:\Users\user2\AppData\Bar\bin"
        session.Reply(result)

        result.value.name = "TEMP"
        result.value.expand_string = r"C:\Users\user2\AppData\Local\Temp"
        session.Reply(result)
      else:
        raise RuntimeError(f"Unexpected key: {args.key}")

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=collectors.ArtifactCollectorFlow,
        flow_args=mig_artifacts.ToRDFArtifactCollectorFlowArgs(args),
        handlers={
            rrg_pb2.Action.LIST_WINREG_VALUES: ListWinregValuesHandler,
        },
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_results = data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0, 128)
    self.assertLen(flow_results, 2)

    results_by_path = {}
    for flow_result in flow_results:
      result = jobs_pb2.StatEntry()
      self.assertTrue(flow_result.payload.Unpack(result))

      results_by_path[result.pathspec.path] = result

    result_1 = results_by_path[
        r"HKEY_USERS\S-1-5-80-111-111-111\Environment\Path"
    ]
    self.assertEqual(result_1.registry_type, jobs_pb2.StatEntry.REG_EXPAND_SZ)
    self.assertEqual(
        result_1.registry_data.string,
        r"C:\Users\user1\AppData\Foo\bin",
    )

    result_2 = results_by_path[
        r"HKEY_USERS\S-1-5-80-222-222-222\Environment\Path"
    ]
    self.assertEqual(result_2.registry_type, jobs_pb2.StatEntry.REG_EXPAND_SZ)
    self.assertEqual(
        result_2.registry_data.string,
        r"C:\Users\user2\AppData\Bar\bin",
    )

  def testRRGCommand(self):
    rrg_command = rrg_execute_signed_command_pb2.Command()
    rrg_command.path.raw_bytes = "/usr/bin/foo".encode()
    rrg_command.args_signed.append("--bar")
    rrg_command.args_signed.append("--baz")

    signed_command = signed_commands_pb2.SignedCommand()
    signed_command.id = "foo"
    signed_command.operating_system = signed_commands_pb2.SignedCommand.OS.LINUX
    signed_command.command = rrg_command.SerializeToString()
    signed_command.ed25519_signature = os.urandom(64)
    data_store.REL_DB.WriteSignedCommand(signed_command)

    client_id = db_test_utils.InitializeRRGClient(data_store.REL_DB)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    artifact = artifact_pb2.Artifact()
    artifact.name = "CommandExample"
    artifact.doc = "An example artifact with a command to execute"

    artifact_source = artifact.sources.add()
    artifact_source.type = artifact_pb2.ArtifactSource.COMMAND

    attr_cmd = artifact_source.attributes.dat.add()
    attr_cmd.k.string = "cmd"
    attr_cmd.v.string = "/usr/bin/foo"

    attr_args = artifact_source.attributes.dat.add()
    attr_args.k.string = "args"
    attr_args.v.list.content.add().string = "--bar"
    attr_args.v.list.content.add().string = "--baz"

    artifact_registry.REGISTRY.RegisterArtifact(
        mig_artifacts.ToRDFArtifact(artifact)
    )

    args = flows_pb2.ArtifactCollectorFlowArgs()
    args.artifact_list.append("CommandExample")

    def ExecuteSignedCommandHandler(session: rrg_test_lib.Session) -> None:
      args = rrg_execute_signed_command_pb2.Args()
      assert session.args.Unpack(args)

      command = rrg_execute_signed_command_pb2.Command()
      command.ParseFromString(args.command)

      if command.path.raw_bytes != "/usr/bin/foo".encode():
        raise RuntimeError(f"Unexpected command path: {command.path}")
      if command.args_signed != ["--bar", "--baz"]:
        raise RuntimeError(f"Unexpected command args: {command.args_signed}")

      result = rrg_execute_signed_command_pb2.Result()
      result.exit_code = 0
      result.stdout = "lorem ipsum".encode("utf-8")
      result.stderr = "dolor sit amet".encode("utf-8")
      session.Reply(result)

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=collectors.ArtifactCollectorFlow,
        flow_args=mig_artifacts.ToRDFArtifactCollectorFlowArgs(args),
        handlers={
            rrg_pb2.Action.EXECUTE_SIGNED_COMMAND: ExecuteSignedCommandHandler,
        },
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_results = data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0, 128)
    self.assertLen(flow_results, 1)
    self.assertEqual(flow_results[0].tag, "artifact:CommandExample")

    result = jobs_pb2.ExecuteResponse()
    self.assertTrue(flow_results[0].payload.Unpack(result))

    self.assertEqual(result.exit_status, 0)
    self.assertEqual(result.stdout, "lorem ipsum".encode("utf-8"))
    self.assertEqual(result.stderr, "dolor sit amet".encode("utf-8"))

  def testRRGWMIQuery(self):
    client_id = db_test_utils.InitializeRRGClient(data_store.REL_DB)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Windows"
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    artifact = artifact_pb2.Artifact()
    artifact.name = "WmiExample"
    artifact.doc = "An example artifact with WMI query"

    artifact_source = artifact.sources.add()
    artifact_source.supported_os.append("Windows")
    artifact_source.type = artifact_pb2.ArtifactSource.WMI

    attr_query = artifact_source.attributes.dat.add()
    attr_query.k.string = "query"
    attr_query.v.string = "SELECT * FROM Foo"

    artifact_registry.REGISTRY.RegisterArtifact(
        mig_artifacts.ToRDFArtifact(artifact)
    )

    args = flows_pb2.ArtifactCollectorFlowArgs()
    args.artifact_list.append("WmiExample")

    def QueryWmiHandler(session: rrg_test_lib.Session) -> None:
      args = rrg_query_wmi_pb2.Args()
      assert session.args.Unpack(args)

      if not args.query.strip().startswith("SELECT "):
        raise RuntimeError(f"Non-`SELECT` WMI query: {args.query!r}")

      result = rrg_query_wmi_pb2.Result()
      result.row["Bool"].bool = True
      result.row["UnsignedInt"].uint = 1337
      result.row["SignedInt"].int = -42
      result.row["Float"].float = 3.14
      result.row["Double"].double = 2.71
      result.row["String"].string = "Lorem ipsum"
      session.Reply(result)

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=collectors.ArtifactCollectorFlow,
        flow_args=mig_artifacts.ToRDFArtifactCollectorFlowArgs(args),
        handlers={
            rrg_pb2.Action.QUERY_WMI: QueryWmiHandler,
        },
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_results = data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0, 128)
    self.assertLen(flow_results, 1)
    self.assertEqual(flow_results[0].tag, "artifact:WmiExample")

    result = jobs_pb2.Dict()
    self.assertTrue(flow_results[0].payload.Unpack(result))
    self.assertLen(result.dat, 6)

    value_by_key = {_.k.string: _.v for _ in result.dat}
    self.assertEqual(value_by_key["Bool"].boolean, True)
    self.assertEqual(value_by_key["UnsignedInt"].integer, 1337)
    self.assertEqual(value_by_key["SignedInt"].integer, -42)
    self.assertAlmostEqual(value_by_key["Float"].float, 3.14, places=5)
    self.assertAlmostEqual(value_by_key["Double"].float, 2.71, places=5)
    self.assertEqual(value_by_key["String"].string, "Lorem ipsum")

  def testRRGWMIQuery_CustomNamespace(self):
    client_id = db_test_utils.InitializeRRGClient(data_store.REL_DB)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Windows"
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    artifact = artifact_pb2.Artifact()
    artifact.name = "WmiExampleWithBaseObject"
    artifact.doc = "An example artifact with WMI query"

    artifact_source = artifact.sources.add()
    artifact_source.supported_os.append("Windows")
    artifact_source.type = artifact_pb2.ArtifactSource.WMI

    attr_query = artifact_source.attributes.dat.add()
    attr_query.k.string = "query"
    attr_query.v.string = "SELECT * FROM Foo"

    attr_base_object = artifact_source.attributes.dat.add()
    attr_base_object.k.string = "base_object"
    attr_base_object.v.string = "winmgmts:\\root\\SecurityCenter2"

    artifact_registry.REGISTRY.RegisterArtifact(
        mig_artifacts.ToRDFArtifact(artifact)
    )

    args = flows_pb2.ArtifactCollectorFlowArgs()
    args.artifact_list.append("WmiExampleWithBaseObject")

    def QueryWmiHandler(session: rrg_test_lib.Session) -> None:
      args = rrg_query_wmi_pb2.Args()
      assert session.args.Unpack(args)

      if args.namespace != "root\\SecurityCenter2":
        raise RuntimeError(f"Unexpected WMI namespace: {args.namespace}")

      if not args.query.strip().startswith("SELECT "):
        raise RuntimeError(f"Non-`SELECT` WMI query: {args.query!r}")

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=collectors.ArtifactCollectorFlow,
        flow_args=mig_artifacts.ToRDFArtifactCollectorFlowArgs(args),
        handlers={
            rrg_pb2.Action.QUERY_WMI: QueryWmiHandler,
        },
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

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
