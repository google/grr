#!/usr/bin/env python
"""Test the collector flows.

To reduce the size of this module, additional collector flow tests are split out
into collectors_*_test.py files.
"""

import itertools
import os
import shutil
from typing import IO
from unittest import mock

from absl import app
import psutil

from grr_response_client import actions
from grr_response_client.client_actions import standard
from grr_response_core import config
from grr_response_core.lib import factory
from grr_response_core.lib import parser
from grr_response_core.lib import parsers
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import mig_artifacts
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.util import temp
from grr_response_proto import knowledge_base_pb2
from grr_response_proto import objects_pb2
from grr_response_server import action_registry
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
from grr.test_lib import filesystem_test_lib
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
    args = rdf_artifacts.ArtifactCollectorFlowArgs()
    collect_flow = collectors.ArtifactCollectorFlow(
        rdf_flow_objects.Flow(args=args)
    )

    kb = rdf_client.KnowledgeBase()
    kb.MergeOrAddUser(rdf_client.User(username="test1"))
    kb.MergeOrAddUser(rdf_client.User(username="test2"))
    collect_flow.state["knowledge_base"] = kb

    collect_flow.current_artifact_name = "blah"

    test_rdf = rdf_client.KnowledgeBase()
    action_args = {
        "usernames": ["%%users.username%%", "%%users.username%%"],
        "nointerp": "asdfsdf",
        "notastring": test_rdf,
    }

    kwargs = collect_flow.InterpolateDict(action_args)
    self.assertCountEqual(
        kwargs["usernames"], ["test1", "test2", "test1", "test2"]
    )
    self.assertEqual(kwargs["nointerp"], "asdfsdf")
    self.assertEqual(kwargs["notastring"], test_rdf)

    # We should be using an array since users.username will expand to multiple
    # values.
    self.assertRaises(
        ValueError, collect_flow.InterpolateDict, {"bad": "%%users.username%%"}
    )

    list_args = collect_flow.InterpolateList(
        ["%%users.username%%", r"%%users.username%%\aa"]
    )
    self.assertCountEqual(
        list_args, ["test1", "test2", r"test1\aa", r"test2\aa"]
    )

    list_args = collect_flow.InterpolateList(["one"])
    self.assertEqual(list_args, ["one"])

    # Ignore the failure in users.desktop, report the others.
    collect_flow.args.ignore_interpolation_errors = True
    list_args = collect_flow.InterpolateList(
        ["%%users.desktop%%", r"%%users.username%%\aa"]
    )
    self.assertCountEqual(list_args, [r"test1\aa", r"test2\aa"])

    # Both fail.
    list_args = collect_flow.InterpolateList(
        [r"%%users.desktop%%\aa", r"%%users.sid%%\aa"]
    )
    self.assertCountEqual(list_args, [])

  def testGrepRegexCombination(self):
    args = rdf_artifacts.ArtifactCollectorFlowArgs()
    collect_flow = collectors.ArtifactCollectorFlow(
        rdf_flow_objects.Flow(args=args)
    )

    self.assertEqual(collect_flow._CombineRegex([b"simple"]), b"simple")
    self.assertEqual(collect_flow._CombineRegex([b"a", b"b"]), b"(a)|(b)")
    self.assertEqual(
        collect_flow._CombineRegex([b"a", b"b", b"c"]), b"(a)|(b)|(c)"
    )
    self.assertEqual(
        collect_flow._CombineRegex([b"a|b", b"[^_]b", b"c|d"]),
        b"(a|b)|([^_]b)|(c|d)",
    )

  def testGrep(self):
    class MockCallFlow(object):

      def CallFlow(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    mock_call_flow = MockCallFlow()
    with mock.patch.object(
        collectors.ArtifactCollectorFlow, "CallFlow", mock_call_flow.CallFlow
    ):
      args = mock.Mock()
      args.ignore_interpolation_errors = False

      collect_flow = collectors.ArtifactCollectorFlow(
          rdf_flow_objects.Flow(args=args)
      )
      kb = rdf_client.KnowledgeBase()
      kb.MergeOrAddUser(rdf_client.User(username="test1"))
      kb.MergeOrAddUser(rdf_client.User(username="test2"))
      collect_flow.state["knowledge_base"] = kb
      collect_flow.current_artifact_name = "blah"

      collector = rdf_artifacts.ArtifactSource(
          type=rdf_artifacts.ArtifactSource.SourceType.GREP,
          attributes={
              "paths": ["/etc/passwd"],
              "content_regex_list": [b"^a%%users.username%%b$"],
          },
      )
      collect_flow.Grep(collector, rdf_paths.PathSpec.PathType.TSK, None)

    conditions = mock_call_flow.kwargs["conditions"]
    self.assertLen(conditions, 1)
    regexes = conditions[0].contents_regex_match.regex.AsBytes()
    self.assertCountEqual(regexes.split(b"|"), [b"(^atest1b$)", b"(^atest2b$)"])
    self.assertEqual(mock_call_flow.kwargs["paths"], ["/etc/passwd"])

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
    flow_test_lib.TestFlowHelper(
        collectors.ArtifactCollectorFlow.__name__,
        client_mock,
        artifact_list=artifact_list,
        use_raw_filesystem_access=False,
        creator=self.test_username,
        client_id=client_id,
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

  def testRunGrrClientActionArtifact(self):
    """Test we can get a GRR client artifact."""
    client_id = self.SetupClient(0, system="Linux")
    with mock.patch.object(psutil, "process_iter", ProcessIter):
      client_mock = action_mocks.ActionMock(standard.ListProcesses)

      coll1 = rdf_artifacts.ArtifactSource(
          type=rdf_artifacts.ArtifactSource.SourceType.GRR_CLIENT_ACTION,
          attributes={"client_action": standard.ListProcesses.__name__},
      )
      self.fakeartifact.sources.append(coll1)
      artifact_list = ["FakeArtifact"]
      flow_id = flow_test_lib.TestFlowHelper(
          collectors.ArtifactCollectorFlow.__name__,
          client_mock,
          artifact_list=artifact_list,
          creator=self.test_username,
          client_id=client_id,
      )

      results = flow_test_lib.GetFlowResults(client_id, flow_id)
      self.assertIsInstance(results[0], rdf_client.Process)
      self.assertLen(results, 1)

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
        flow_id = flow_test_lib.TestFlowHelper(
            collectors.ArtifactCollectorFlow.__name__,
            client_mock,
            artifact_list=artifact_list,
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
        flow_id = flow_test_lib.TestFlowHelper(
            collectors.ArtifactCollectorFlow.__name__,
            client_mock,
            artifact_list=artifact_list,
            creator=self.test_username,
            client_id=client_id,
        )

    results = flow_test_lib.GetFlowResults(client_id, flow_id)
    self.assertIsInstance(results[0], rdf_client_fs.StatEntry)
    self.assertEqual(results[0].registry_data.GetValue(), "DefaultValue")

  def testSupportedOS(self):
    """Test supported_os inside the collector object."""
    client_id = self.SetupClient(0, system="Linux")
    with mock.patch.object(psutil, "process_iter", ProcessIter):
      client_mock = action_mocks.ActionMock(standard.ListProcesses)
      coll1 = rdf_artifacts.ArtifactSource(
          type=rdf_artifacts.ArtifactSource.SourceType.GRR_CLIENT_ACTION,
          attributes={"client_action": standard.ListProcesses.__name__},
          supported_os=["Windows"],
      )
      self.fakeartifact.sources.append(coll1)
      results = self._RunClientActionArtifact(
          client_id, client_mock, ["FakeArtifact"]
      )
      self.assertEmpty(results)

      coll1.supported_os = ["Linux", "Windows"]
      self.fakeartifact.sources = []
      self.fakeartifact.sources.append(coll1)
      results = self._RunClientActionArtifact(
          client_id, client_mock, ["FakeArtifact"]
      )
      self.assertTrue(results)

      coll1.supported_os = ["NotTrue"]
      self.fakeartifact.sources = []
      self.fakeartifact.sources.append(coll1)
      results = self._RunClientActionArtifact(
          client_id, client_mock, ["FakeArtifact"]
      )
      self.assertEmpty(results)

      coll1.supported_os = ["Linux", "Windows"]
      self.fakeartifact.supported_os = ["Linux"]
      results = self._RunClientActionArtifact(
          client_id, client_mock, ["FakeArtifact"]
      )
      self.assertTrue(results)

      self.fakeartifact.supported_os = ["Windows"]
      results = self._RunClientActionArtifact(
          client_id, client_mock, ["FakeArtifact"]
      )
      self.assertEmpty(results)

  def _RunClientActionArtifact(
      self, client_id, client_mock, artifact_list, implementation_type=None
  ):
    self.output_count += 1
    flow_id = flow_test_lib.TestFlowHelper(
        collectors.ArtifactCollectorFlow.__name__,
        client_mock,
        artifact_list=artifact_list,
        creator=self.test_username,
        client_id=client_id,
        implementation_type=implementation_type,
        use_raw_filesystem_access=(implementation_type is not None),
    )

    return flow_test_lib.GetFlowResults(client_id, flow_id)

  @mock.patch.object(
      parsers,
      "SINGLE_RESPONSE_PARSER_FACTORY",
      factory.Factory(parsers.SingleResponseParser),
  )
  def testParsingFailure(self):
    """Test a command artifact where parsing the response fails."""

    filesystem_test_lib.Command("/bin/echo", args=["1"])

    InitGRRWithTestArtifacts(self)

    client_id = self.SetupClient(0, system="Linux")

    parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
        "TestCmd", TestCmdNullParser
    )
    artifact_list = ["TestUntypedEchoArtifact"]

    flow_id = flow_test_lib.StartAndRunFlow(
        collectors.ArtifactCollectorFlow,
        action_mocks.ActionMock(standard.ExecuteCommand),
        artifact_list=artifact_list,
        apply_parsers=True,
        client_id=client_id,
    )
    results = flow_test_lib.GetFlowResults(client_id, flow_id)
    self.assertEmpty(results)

  def testFlowProgressHasEntryForArtifactWithoutResults(self):
    client_id = self.SetupClient(0, system="Linux")
    with mock.patch.object(psutil, "process_iter", lambda: iter([])):
      client_mock = action_mocks.ActionMock(standard.ListProcesses)

      self.fakeartifact.sources.append(
          rdf_artifacts.ArtifactSource(
              type=rdf_artifacts.ArtifactSource.SourceType.GRR_CLIENT_ACTION,
              attributes={"client_action": standard.ListProcesses.__name__},
          )
      )

      flow_id = flow_test_lib.TestFlowHelper(
          collectors.ArtifactCollectorFlow.__name__,
          client_mock,
          artifact_list=["FakeArtifact"],
          client_id=client_id,
      )

      progress = flow_test_lib.GetFlowProgress(client_id, flow_id)
      self.assertLen(progress.artifacts, 1)
      self.assertEqual(progress.artifacts[0].name, "FakeArtifact")
      self.assertEqual(progress.artifacts[0].num_results, 0)

  def testFlowProgressIsCountingResults(self):
    def _Iter():
      return iter([
          client_test_lib.MockWindowsProcess(),
          client_test_lib.MockWindowsProcess(),
      ])

    client_id = self.SetupClient(0, system="Linux")
    with mock.patch.object(psutil, "process_iter", _Iter):
      client_mock = action_mocks.ActionMock(standard.ListProcesses)

      self.fakeartifact.sources.append(
          rdf_artifacts.ArtifactSource(
              type=rdf_artifacts.ArtifactSource.SourceType.GRR_CLIENT_ACTION,
              attributes={"client_action": standard.ListProcesses.__name__},
          )
      )

      flow_id = flow_test_lib.TestFlowHelper(
          collectors.ArtifactCollectorFlow.__name__,
          client_mock,
          artifact_list=["FakeArtifact"],
          client_id=client_id,
      )

      progress = flow_test_lib.GetFlowProgress(client_id, flow_id)
      self.assertLen(progress.artifacts, 1)
      self.assertEqual(progress.artifacts[0].name, "FakeArtifact")
      self.assertEqual(progress.artifacts[0].num_results, 2)

  def testProcessesResultsOfFailedChildArtifactCollector(self):
    client_id = self.SetupClient(0, system="Linux")
    client_mock = action_mocks.ActionMock(standard.ListProcesses)

    self.fakeartifact.sources.append(
        rdf_artifacts.ArtifactSource(
            type=rdf_artifacts.ArtifactSource.SourceType.ARTIFACT_GROUP,
            attributes={"names": ["FakeArtifact2"]},
        )
    )

    self.fakeartifact2.sources.append(
        rdf_artifacts.ArtifactSource(
            type=rdf_artifacts.ArtifactSource.SourceType.GRR_CLIENT_ACTION,
            attributes={"client_action": standard.ListProcesses.__name__},
        )
    )

    def _RunListProcesses(self, args):
      self.SendReply(rdf_client.Process(pid=123))
      raise ValueError()

    with mock.patch.object(standard.ListProcesses, "Run", _RunListProcesses):
      flow_id = flow_test_lib.TestFlowHelper(
          collectors.ArtifactCollectorFlow.__name__,
          client_mock,
          artifact_list=["FakeArtifact"],
          client_id=client_id,
          check_flow_errors=False,
      )

    results = flow_test_lib.GetFlowResults(client_id, flow_id)
    self.assertLen(results, 1)
    self.assertEqual(results[0].pid, 123)

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
                    type=rdf_artifacts.ArtifactSource.SourceType.GRR_CLIENT_ACTION,
                    attributes={"client_action": "DoesNothingActionMock"},
                )
            ],
        )
    )

    class DoesNothingActionMock(actions.ActionPlugin):

      def Run(self, args: any) -> None:
        del args
        pass

    # TODO: Start using the annotation (w/cleanup).
    action_registry.RegisterAdditionalTestClientAction(DoesNothingActionMock)

    flow_id = flow_test_lib.TestFlowHelper(
        collectors.ArtifactCollectorFlow.__name__,
        action_mocks.ActionMock(),
        artifact_list=["Planta"],
        client_id=client_id,
        apply_parsers=False,
        use_raw_filesystem_access=True,
        implementation_type=rdf_paths.PathSpec.ImplementationType.DIRECT,
        max_file_size=1,
        ignore_interpolation_errors=True,
    )

    child_flows = data_store.REL_DB.ReadChildFlowObjects(client_id, flow_id)
    self.assertLen(child_flows, 1)
    args = mig_flow_objects.ToRDFFlow(child_flows[0]).args
    self.assertEqual(args.apply_parsers, False)
    self.assertEqual(args.use_raw_filesystem_access, True)
    self.assertEqual(
        args.implementation_type,
        rdf_paths.PathSpec.ImplementationType.DIRECT,
    )
    self.assertEqual(args.max_file_size, 1)
    self.assertEqual(args.ignore_interpolation_errors, True)

  def testGrep2(self):
    client_id = self.SetupClient(0, system="Linux")
    client_mock = action_mocks.ClientFileFinderClientMock()
    with temp.AutoTempFilePath() as temp_file_path:
      with open(temp_file_path, "w") as f:
        f.write("foo")
      coll1 = rdf_artifacts.ArtifactSource(
          type=rdf_artifacts.ArtifactSource.SourceType.GREP,
          attributes={
              "paths": [temp_file_path],
              "content_regex_list": ["f|o+"],
          },
      )
      self.fakeartifact.sources.append(coll1)
      results = self._RunClientActionArtifact(
          client_id, client_mock, ["FakeArtifact"]
      )
    matches = itertools.chain.from_iterable(
        [m.data for m in r.matches] for r in results
    )
    expected_matches = [b"f", b"oo"]
    self.assertCountEqual(matches, expected_matches)

  def testDirectory(self):
    client_id = self.SetupClient(0, system="Linux")
    client_mock = action_mocks.FileFinderClientMock()
    with temp.AutoTempDirPath() as temp_dir_path:
      coll1 = rdf_artifacts.ArtifactSource(
          type=rdf_artifacts.ArtifactSource.SourceType.PATH,
          attributes={"paths": [temp_dir_path]},
      )
      self.fakeartifact.sources.append(coll1)
      results = self._RunClientActionArtifact(
          client_id, client_mock, ["FakeArtifact"]
      )
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
      results = self._RunClientActionArtifact(
          client_id, client_mock, ["FakeArtifact"]
      )
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

      flow_id = flow_test_lib.TestFlowHelper(
          collectors.ArtifactFilesDownloaderFlow.__name__,
          client_mock,
          artifact_list=["FakeArtifact"],
          creator=self.test_username,
          client_id=client_id,
      )
      results = flow_test_lib.GetFlowResults(client_id, flow_id)
      self.assertLen(results, 1)
      self.assertEqual(results[0].downloaded_file.pathspec.path, temp_file_path)


class RelationalTestArtifactCollectors(
    ArtifactCollectorsTestMixin, test_lib.GRRBaseTest
):

  def testRunGrrClientActionArtifactSplit(self):
    """Test that artifacts get split into separate collections."""
    client_id = self.SetupClient(0, system="Linux")
    with mock.patch.object(psutil, "process_iter", ProcessIter):
      client_mock = action_mocks.ActionMock(standard.ListProcesses)

      coll1 = rdf_artifacts.ArtifactSource(
          type=rdf_artifacts.ArtifactSource.SourceType.GRR_CLIENT_ACTION,
          attributes={"client_action": standard.ListProcesses.__name__},
      )
      self.fakeartifact.sources.append(coll1)
      self.fakeartifact2.sources.append(coll1)
      artifact_list = ["FakeArtifact", "FakeArtifact2"]
      flow_id = flow_test_lib.TestFlowHelper(
          collectors.ArtifactCollectorFlow.__name__,
          client_mock,
          artifact_list=artifact_list,
          creator=self.test_username,
          client_id=client_id,
          split_output_by_artifact=True,
      )
      results_by_tag = flow_test_lib.GetFlowResultsByTag(client_id, flow_id)
      self.assertCountEqual(
          results_by_tag.keys(),
          ["artifact:FakeArtifact", "artifact:FakeArtifact2"],
      )

  def testOldClientSnapshotFallbackIfInterpolationFails(self):
    rel_db = data_store.REL_DB
    client_id = "C.0123456789abcdef"

    rel_db.WriteClientMetadata(client_id, first_seen=rdfvalue.RDFDatetime.Now())

    # Write some fake snapshot history.
    kb_0 = knowledge_base_pb2.KnowledgeBase(os="Linux")
    kb_0.users.add(username="user1")
    kb_0.users.add(username="user2")
    snapshot_0 = objects_pb2.ClientSnapshot(
        client_id=client_id, knowledge_base=kb_0
    )
    rel_db.WriteClientSnapshot(snapshot_0)

    kb_1 = knowledge_base_pb2.KnowledgeBase(os="Linux")
    snapshot_1 = objects_pb2.ClientSnapshot(
        client_id=client_id, knowledge_base=kb_1
    )
    rel_db.WriteClientSnapshot(snapshot_1)

    kb_2 = knowledge_base_pb2.KnowledgeBase(os="Linux")
    snapshot_2 = objects_pb2.ClientSnapshot(
        client_id=client_id, knowledge_base=kb_2
    )
    rel_db.WriteClientSnapshot(snapshot_2)

    with temp.AutoTempDirPath(remove_non_empty=True) as dirpath:
      filesystem_test_lib.CreateFile(
          os.path.join(dirpath, "user1", "quux", "thud")
      )
      filesystem_test_lib.CreateFile(
          os.path.join(dirpath, "user2", "quux", "norf")
      )

      # Write a fake artifact.
      path = os.path.join(dirpath, "%%users.username%%", "quux", "*")
      art = rdf_artifacts.Artifact(
          name="Quux",
          doc="Lorem ipsum.",
          sources=[
              rdf_artifacts.ArtifactSource(
                  type=rdf_artifacts.ArtifactSource.SourceType.PATH,
                  attributes={
                      "paths": [path],
                  },
              ),
          ],
      )
      rel_db.WriteArtifact(mig_artifacts.ToProtoArtifact(art))

      artifact_registry.REGISTRY.ReloadDatastoreArtifacts()
      flow_id = flow_test_lib.TestFlowHelper(
          collectors.ArtifactCollectorFlow.__name__,
          client_mock=action_mocks.FileFinderClientMock(),
          client_id=client_id,
          artifact_list=["Quux"],
          old_client_snapshot_fallback=True,
          creator=self.test_username,
      )

    results = flow_test_lib.GetFlowResults(client_id=client_id, flow_id=flow_id)
    self.assertNotEmpty(results)

    basenames = [os.path.basename(result.pathspec.path) for result in results]
    self.assertCountEqual(basenames, ["thud", "norf"])

  def testOldClientSnapshotFallbackUsesLatestApplicable(self):
    rel_db = data_store.REL_DB
    client_id = "C.0123456789abcdef"

    rel_db.WriteClientMetadata(client_id, first_seen=rdfvalue.RDFDatetime.Now())

    # Write some fake snapshot history.
    kb_0 = knowledge_base_pb2.KnowledgeBase(os="Linux", os_release="rel0")
    snapshot_0 = objects_pb2.ClientSnapshot(
        client_id=client_id, knowledge_base=kb_0
    )
    rel_db.WriteClientSnapshot(snapshot_0)

    kb_1 = knowledge_base_pb2.KnowledgeBase(os="Linux", os_release="rel1")
    snapshot_1 = objects_pb2.ClientSnapshot(
        client_id=client_id, knowledge_base=kb_1
    )
    rel_db.WriteClientSnapshot(snapshot_1)

    kb_2 = knowledge_base_pb2.KnowledgeBase(os="Linux")
    snapshot_2 = objects_pb2.ClientSnapshot(
        client_id=client_id, knowledge_base=kb_2
    )
    rel_db.WriteClientSnapshot(snapshot_2)

    with temp.AutoTempDirPath(remove_non_empty=True) as dirpath:
      filesystem_test_lib.CreateFile(os.path.join(dirpath, "rel0", "quux"))
      filesystem_test_lib.CreateFile(os.path.join(dirpath, "rel1", "norf"))

      # Write a fake artifact.
      art = rdf_artifacts.Artifact(
          name="Quux",
          doc="Lorem ipsum.",
          sources=[
              rdf_artifacts.ArtifactSource(
                  type=rdf_artifacts.ArtifactSource.SourceType.PATH,
                  attributes={
                      "paths": [os.path.join(dirpath, "%%os_release%%", "*")],
                  },
              ),
          ],
      )
      rel_db.WriteArtifact(mig_artifacts.ToProtoArtifact(art))

      artifact_registry.REGISTRY.ReloadDatastoreArtifacts()
      flow_id = flow_test_lib.TestFlowHelper(
          collectors.ArtifactCollectorFlow.__name__,
          client_mock=action_mocks.FileFinderClientMock(),
          client_id=client_id,
          artifact_list=["Quux"],
          old_client_snapshot_fallback=True,
          creator=self.test_username,
      )

    results = flow_test_lib.GetFlowResults(client_id=client_id, flow_id=flow_id)
    self.assertNotEmpty(results)

    basenames = [os.path.basename(result.pathspec.path) for result in results]
    self.assertNotIn("quux", basenames)
    self.assertIn("norf", basenames)


class MeetsConditionsTest(test_lib.GRRBaseTest):
  """Test the module-level method `MeetsConditions`."""

  def testSourceMeetsOSConditions(self):
    """Test we can get a GRR client artifact with conditions."""

    knowledge_base = rdf_client.KnowledgeBase()
    knowledge_base.os = "Windows"

    # Run with unsupported OS.
    source = rdf_artifacts.ArtifactSource(
        type=rdf_artifacts.ArtifactSource.SourceType.GRR_CLIENT_ACTION,
        attributes={"client_action": standard.ListProcesses.__name__},
        supported_os=["Linux"],
    )
    self.assertFalse(collectors.MeetsOSConditions(knowledge_base, source))

    # Run with supported OS.
    source = rdf_artifacts.ArtifactSource(
        type=rdf_artifacts.ArtifactSource.SourceType.GRR_CLIENT_ACTION,
        attributes={"client_action": standard.ListProcesses.__name__},
        supported_os=["Linux", "Windows"],
    )
    self.assertTrue(collectors.MeetsOSConditions(knowledge_base, source))


class TestCmdParser(parser.CommandParser):
  output_types = [rdf_client.SoftwarePackages]
  supported_artifacts = ["TestEchoArtifact"]

  def Parse(self, cmd, args, stdout, stderr, return_val, knowledge_base):
    del cmd, args, stderr, return_val, knowledge_base  # Unused
    yield rdf_client.SoftwarePackages(
        packages=[
            rdf_client.SoftwarePackage.Installed(
                name="Package",
                description=stdout,
                version="1",
                architecture="amd64",
            ),
        ]
    )


class TestCmdNullParser(parser.CommandParser):
  output_types = [rdf_client.SoftwarePackages]
  supported_artifacts = ["TestUntypedEchoArtifact"]

  def Parse(self, cmd, args, stdout, stderr, return_val, knowledge_base):
    del cmd, args, stderr, return_val, knowledge_base  # Unused
    # This parser tests flow behavior when the input can't be parsed.
    return []


class TestFileParser(parsers.SingleFileParser[rdf_protodict.AttributedDict]):
  output_types = [rdf_protodict.AttributedDict]
  supported_artifacts = ["TestFileArtifact"]

  def ParseFile(
      self,
      knowledge_base: rdf_client.KnowledgeBase,
      pathspec: rdf_paths.PathSpec,
      filedesc: IO[bytes],
  ):
    del knowledge_base  # Unused.

    lines = set([l.strip() for l in filedesc.read().splitlines()])

    users = list(filter(None, lines))

    filename = pathspec.path
    cfg = {"filename": filename, "users": users}

    yield rdf_protodict.AttributedDict(**cfg)


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
