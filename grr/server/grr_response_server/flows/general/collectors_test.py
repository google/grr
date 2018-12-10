#!/usr/bin/env python
"""Test the collector flows.

To reduce the size of this module, additional collector flow tests are split out
into collectors_*_test.py files.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import shutil


from builtins import filter  # pylint: disable=redefined-builtin
import mock
import psutil

from grr_response_client.client_actions import artifact_collector
from grr_response_client.client_actions import standard
from grr_response_core import config
from grr_response_core.lib import factory
from grr_response_core.lib import flags
from grr_response_core.lib import parser
from grr_response_core.lib import parsers
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_server import aff4
from grr_response_server import aff4_flows
from grr_response_server import artifact_registry
from grr_response_server import data_store
from grr_response_server import db
from grr_response_server import file_store
from grr_response_server.flows.general import collectors
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import action_mocks
from grr.test_lib import artifact_test_lib
from grr.test_lib import client_test_lib
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import temp
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib


def ProcessIter():
  return iter([client_test_lib.MockWindowsProcess()])


class ArtifactCollectorsTestMixin(object):
  """A mixin for artifact collectors tests."""

  def setUp(self):
    """Make sure things are initialized."""
    super(ArtifactCollectorsTestMixin, self).setUp()

    self._patcher = artifact_test_lib.PatchDefaultArtifactRegistry()
    self._patcher.start()

    artifact_registry.REGISTRY.ClearSources()
    artifact_registry.REGISTRY.ClearRegistry()

    test_artifacts_file = os.path.join(config.CONFIG["Test.data_dir"],
                                       "artifacts", "test_artifacts.json")
    artifact_registry.REGISTRY.AddFileSource(test_artifacts_file)

    self.fakeartifact = artifact_registry.REGISTRY.GetArtifact("FakeArtifact")
    self.fakeartifact2 = artifact_registry.REGISTRY.GetArtifact("FakeArtifact2")

    self.output_count = 0

  def tearDown(self):
    self._patcher.stop()
    super(ArtifactCollectorsTestMixin, self).tearDown()


@db_test_lib.DualDBTest
class TestArtifactCollectors(ArtifactCollectorsTestMixin,
                             flow_test_lib.FlowTestsBaseclass):
  """Test the artifact collection mechanism with fake artifacts."""

  def testInterpolateArgs(self):
    collect_flow = aff4_flows.ArtifactCollectorFlow(None, token=self.token)

    kb = rdf_client.KnowledgeBase()
    kb.MergeOrAddUser(rdf_client.User(username="test1"))
    kb.MergeOrAddUser(rdf_client.User(username="test2"))
    collect_flow.state["knowledge_base"] = kb

    collect_flow.current_artifact_name = "blah"
    collect_flow.args = rdf_artifacts.ArtifactCollectorFlowArgs()

    test_rdf = rdf_client.KnowledgeBase()
    action_args = {
        "usernames": ["%%users.username%%", "%%users.username%%"],
        "nointerp": "asdfsdf",
        "notastring": test_rdf
    }

    kwargs = collect_flow.InterpolateDict(action_args)
    self.assertCountEqual(kwargs["usernames"],
                          ["test1", "test2", "test1", "test2"])
    self.assertEqual(kwargs["nointerp"], "asdfsdf")
    self.assertEqual(kwargs["notastring"], test_rdf)

    # We should be using an array since users.username will expand to multiple
    # values.
    self.assertRaises(ValueError, collect_flow.InterpolateDict,
                      {"bad": "%%users.username%%"})

    list_args = collect_flow.InterpolateList(
        ["%%users.username%%", r"%%users.username%%\aa"])
    self.assertCountEqual(list_args,
                          ["test1", "test2", r"test1\aa", r"test2\aa"])

    list_args = collect_flow.InterpolateList(["one"])
    self.assertEqual(list_args, ["one"])

    # Ignore the failure in users.desktop, report the others.
    collect_flow.args.ignore_interpolation_errors = True
    list_args = collect_flow.InterpolateList(
        ["%%users.desktop%%", r"%%users.username%%\aa"])
    self.assertCountEqual(list_args, [r"test1\aa", r"test2\aa"])

    # Both fail.
    list_args = collect_flow.InterpolateList(
        [r"%%users.desktop%%\aa", r"%%users.sid%%\aa"])
    self.assertCountEqual(list_args, [])

  def testGrepRegexCombination(self):
    collect_flow = aff4_flows.ArtifactCollectorFlow(None, token=self.token)
    self.assertEqual(collect_flow._CombineRegex([r"simple"]), "simple")
    self.assertEqual(collect_flow._CombineRegex(["a", "b"]), "(a)|(b)")
    self.assertEqual(collect_flow._CombineRegex(["a", "b", "c"]), "(a)|(b)|(c)")
    self.assertEqual(
        collect_flow._CombineRegex(["a|b", "[^_]b", "c|d"]),
        "(a|b)|([^_]b)|(c|d)")

  def testGrep(self):

    class MockCallFlow(object):

      def CallFlow(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    mock_call_flow = MockCallFlow()
    with utils.Stubber(aff4_flows.ArtifactCollectorFlow, "CallFlow",
                       mock_call_flow.CallFlow):

      collect_flow = aff4_flows.ArtifactCollectorFlow(None, token=self.token)
      collect_flow.args = mock.Mock()
      collect_flow.args.ignore_interpolation_errors = False
      kb = rdf_client.KnowledgeBase()
      kb.MergeOrAddUser(rdf_client.User(username="test1"))
      kb.MergeOrAddUser(rdf_client.User(username="test2"))
      collect_flow.state["knowledge_base"] = kb
      collect_flow.current_artifact_name = "blah"

      collector = rdf_artifacts.ArtifactSource(
          type=rdf_artifacts.ArtifactSource.SourceType.GREP,
          attributes={
              "paths": ["/etc/passwd"],
              "content_regex_list": [r"^a%%users.username%%b$"]
          })
      collect_flow.Grep(collector, rdf_paths.PathSpec.PathType.TSK)

    conditions = mock_call_flow.kwargs["conditions"]
    self.assertLen(conditions, 1)
    regexes = conditions[0].contents_regex_match.regex.SerializeToString()
    self.assertCountEqual(regexes.split("|"), ["(^atest1b$)", "(^atest2b$)"])
    self.assertEqual(mock_call_flow.kwargs["paths"], ["/etc/passwd"])

  def testGetArtifact(self):
    """Test we can get a basic artifact."""

    client_mock = action_mocks.FileFinderClientMock()
    client_id = self.SetupClient(0, system="Linux")

    # Dynamically add an ArtifactSource specifying the base path.
    file_path = os.path.join(self.base_path, "hello.exe")
    coll1 = rdf_artifacts.ArtifactSource(
        type=rdf_artifacts.ArtifactSource.SourceType.FILE,
        attributes={"paths": [file_path]})
    self.fakeartifact.sources.append(coll1)

    artifact_list = ["FakeArtifact"]
    flow_test_lib.TestFlowHelper(
        aff4_flows.ArtifactCollectorFlow.__name__,
        client_mock,
        artifact_list=artifact_list,
        use_tsk=False,
        token=self.token,
        client_id=client_id)

    fd2 = open(file_path, "rb")
    fd2.seek(0, 2)
    expected_size = fd2.tell()

    if data_store.AFF4Enabled():
      # Test the AFF4 file that was created.
      fd1 = aff4.FACTORY.Open(
          "%s/fs/os/%s" % (client_id, file_path), token=self.token)
      size = fd1.Get(fd1.Schema.SIZE)
      self.assertEqual(size, expected_size)
    else:
      components = file_path.strip("/").split("/")
      fd = file_store.OpenFile(
          db.ClientPath(
              client_id.Basename(),
              rdf_objects.PathInfo.PathType.OS,
              components=tuple(components)))
      fd.Seek(0, 2)
      size = fd.Tell()
      self.assertEqual(size, expected_size)

  def testArtifactSkipping(self):
    client_mock = action_mocks.ActionMock()
    # This does not match the Artifact so it will not be collected.
    client_id = self.SetupClient(0, system="Windows")

    artifact_list = ["FakeArtifact"]
    session_id = flow_test_lib.TestFlowHelper(
        aff4_flows.ArtifactCollectorFlow.__name__,
        client_mock,
        artifact_list=artifact_list,
        use_tsk=False,
        token=self.token,
        client_id=client_id)

    if data_store.RelationalDBFlowsEnabled():
      flow_obj = data_store.REL_DB.ReadFlowObject(client_id.Basename(),
                                                  session_id)
      state = flow_obj.persistent_data
    else:
      flow_obj = aff4.FACTORY.Open(session_id, token=self.token)
      state = flow_obj.state

    self.assertLen(state.artifacts_skipped_due_to_condition, 1)
    self.assertEqual(state.artifacts_skipped_due_to_condition[0],
                     ["FakeArtifact", "os == 'Linux'"])

  def testRunGrrClientActionArtifact(self):
    """Test we can get a GRR client artifact."""
    client_id = self.SetupClient(0, system="Linux")
    with utils.Stubber(psutil, "process_iter", ProcessIter):
      client_mock = action_mocks.ActionMock(standard.ListProcesses)

      coll1 = rdf_artifacts.ArtifactSource(
          type=rdf_artifacts.ArtifactSource.SourceType.GRR_CLIENT_ACTION,
          attributes={"client_action": standard.ListProcesses.__name__})
      self.fakeartifact.sources.append(coll1)
      artifact_list = ["FakeArtifact"]
      session_id = flow_test_lib.TestFlowHelper(
          aff4_flows.ArtifactCollectorFlow.__name__,
          client_mock,
          artifact_list=artifact_list,
          token=self.token,
          client_id=client_id)

      results = flow_test_lib.GetFlowResults(client_id, session_id)
      self.assertIsInstance(results[0], rdf_client.Process)
      self.assertLen(results, 1)

  def testConditions(self):
    """Test we can get a GRR client artifact with conditions."""
    client_id = self.SetupClient(0, system="Linux")
    with utils.Stubber(psutil, "process_iter", ProcessIter):
      # Run with false condition.
      client_mock = action_mocks.ActionMock(standard.ListProcesses)
      coll1 = rdf_artifacts.ArtifactSource(
          type=rdf_artifacts.ArtifactSource.SourceType.GRR_CLIENT_ACTION,
          attributes={"client_action": standard.ListProcesses.__name__},
          conditions=["os == 'Windows'"])
      self.fakeartifact.sources.append(coll1)
      results = self._RunClientActionArtifact(client_id, client_mock,
                                              ["FakeArtifact"])
      self.assertEmpty(results)

      # Now run with matching or condition.
      coll1.conditions = ["os == 'Linux' or os == 'Windows'"]
      self.fakeartifact.sources = []
      self.fakeartifact.sources.append(coll1)
      results = self._RunClientActionArtifact(client_id, client_mock,
                                              ["FakeArtifact"])
      self.assertTrue(results)

      # Now run with impossible or condition.
      coll1.conditions.append("os == 'NotTrue'")
      self.fakeartifact.sources = []
      self.fakeartifact.sources.append(coll1)
      results = self._RunClientActionArtifact(client_id, client_mock,
                                              ["FakeArtifact"])
      self.assertLen(results, 0)
      self.assertEmpty(results)

  def testRegistryValueArtifact(self):
    client_id = self.SetupClient(0, system="Linux")

    with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.REGISTRY,
                                   vfs_test_lib.FakeRegistryVFSHandler):
      with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                     vfs_test_lib.FakeFullVFSHandler):

        client_mock = action_mocks.ActionMock(standard.GetFileStat)
        coll1 = rdf_artifacts.ArtifactSource(
            type=rdf_artifacts.ArtifactSource.SourceType.REGISTRY_VALUE,
            attributes={
                "key_value_pairs": [{
                    "key": (r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet"
                            r"\Control\Session Manager"),
                    "value": "BootExecute"
                }]
            })
        self.fakeartifact.sources.append(coll1)
        artifact_list = ["FakeArtifact"]
        session_id = flow_test_lib.TestFlowHelper(
            aff4_flows.ArtifactCollectorFlow.__name__,
            client_mock,
            artifact_list=artifact_list,
            token=self.token,
            client_id=client_id)

    # Test the statentry got stored.
    results = flow_test_lib.GetFlowResults(client_id, session_id)
    self.assertIsInstance(results[0], rdf_client_fs.StatEntry)
    self.assertEndsWith(results[0].pathspec.CollapsePath(), "BootExecute")

  def testRegistryDefaultValueArtifact(self):
    client_id = self.SetupClient(0, system="Linux")
    with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.REGISTRY,
                                   vfs_test_lib.FakeRegistryVFSHandler):
      with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                     vfs_test_lib.FakeFullVFSHandler):

        client_mock = action_mocks.ActionMock(standard.GetFileStat)
        coll1 = rdf_artifacts.ArtifactSource(
            type=rdf_artifacts.ArtifactSource.SourceType.REGISTRY_VALUE,
            attributes={
                "key_value_pairs": [{
                    "key": (r"HKEY_LOCAL_MACHINE/SOFTWARE/ListingTest"),
                    "value": ""
                }]
            })
        self.fakeartifact.sources.append(coll1)
        artifact_list = ["FakeArtifact"]
        session_id = flow_test_lib.TestFlowHelper(
            aff4_flows.ArtifactCollectorFlow.__name__,
            client_mock,
            artifact_list=artifact_list,
            token=self.token,
            client_id=client_id)

    results = flow_test_lib.GetFlowResults(client_id, session_id)
    self.assertIsInstance(results[0], rdf_client_fs.StatEntry)
    self.assertEqual(results[0].registry_data.GetValue(), "DefaultValue")

  def testSupportedOS(self):
    """Test supported_os inside the collector object."""
    client_id = self.SetupClient(0, system="Linux")
    with utils.Stubber(psutil, "process_iter", ProcessIter):
      # Run with false condition.
      client_mock = action_mocks.ActionMock(standard.ListProcesses)
      coll1 = rdf_artifacts.ArtifactSource(
          type=rdf_artifacts.ArtifactSource.SourceType.GRR_CLIENT_ACTION,
          attributes={"client_action": standard.ListProcesses.__name__},
          supported_os=["Windows"])
      self.fakeartifact.sources.append(coll1)
      results = self._RunClientActionArtifact(client_id, client_mock,
                                              ["FakeArtifact"])
      self.assertEmpty(results)

      # Now run with matching or condition.
      coll1.conditions = []
      coll1.supported_os = ["Linux", "Windows"]
      self.fakeartifact.sources = []
      self.fakeartifact.sources.append(coll1)
      results = self._RunClientActionArtifact(client_id, client_mock,
                                              ["FakeArtifact"])
      self.assertTrue(results)

      # Now run with impossible or condition.
      coll1.conditions = ["os == 'Linux' or os == 'Windows'"]
      coll1.supported_os = ["NotTrue"]
      self.fakeartifact.sources = []
      self.fakeartifact.sources.append(coll1)
      results = self._RunClientActionArtifact(client_id, client_mock,
                                              ["FakeArtifact"])
      self.assertEmpty(results)

  def _RunClientActionArtifact(self, client_id, client_mock, artifact_list):
    self.output_count += 1
    session_id = flow_test_lib.TestFlowHelper(
        aff4_flows.ArtifactCollectorFlow.__name__,
        client_mock,
        artifact_list=artifact_list,
        token=self.token,
        client_id=client_id)

    return flow_test_lib.GetFlowResults(client_id, session_id)


class RelationalTestArtifactCollectors(ArtifactCollectorsTestMixin,
                                       db_test_lib.RelationalDBEnabledMixin,
                                       test_lib.GRRBaseTest):

  def testRunGrrClientActionArtifactSplit(self):
    """Test that artifacts get split into separate collections."""
    client_id = self.SetupClient(0, system="Linux")
    with utils.Stubber(psutil, "process_iter", ProcessIter):
      client_mock = action_mocks.ActionMock(standard.ListProcesses)

      coll1 = rdf_artifacts.ArtifactSource(
          type=rdf_artifacts.ArtifactSource.SourceType.GRR_CLIENT_ACTION,
          attributes={"client_action": standard.ListProcesses.__name__})
      self.fakeartifact.sources.append(coll1)
      self.fakeartifact2.sources.append(coll1)
      artifact_list = ["FakeArtifact", "FakeArtifact2"]
      session_id = flow_test_lib.TestFlowHelper(
          aff4_flows.ArtifactCollectorFlow.__name__,
          client_mock,
          artifact_list=artifact_list,
          token=self.token,
          client_id=client_id,
          split_output_by_artifact=True)
      results_by_tag = flow_test_lib.GetFlowResultsByTag(
          client_id.Basename(), session_id)
      self.assertCountEqual(results_by_tag.keys(),
                            ["artifact:FakeArtifact", "artifact:FakeArtifact2"])


class MeetsConditionsTest(test_lib.GRRBaseTest):
  """Test the module-level method `MeetsConditions`."""

  def testSourceMeetsConditions(self):
    """Test we can get a GRR client artifact with conditions."""

    knowledge_base = rdf_client.KnowledgeBase()
    knowledge_base.os = "Windows"

    # Run with false condition.
    source = rdf_artifacts.ArtifactSource(
        type=rdf_artifacts.ArtifactSource.SourceType.GRR_CLIENT_ACTION,
        attributes={"client_action": standard.ListProcesses.__name__},
        conditions=["os == 'Linux'"])
    self.assertFalse(collectors.MeetsConditions(knowledge_base, source))

    # Run with matching or condition.
    source = rdf_artifacts.ArtifactSource(
        type=rdf_artifacts.ArtifactSource.SourceType.GRR_CLIENT_ACTION,
        attributes={"client_action": standard.ListProcesses.__name__},
        conditions=["os == 'Linux' or os == 'Windows'"])
    self.assertTrue(collectors.MeetsConditions(knowledge_base, source))


class GetArtifactCollectorArgsTest(test_lib.GRRBaseTest):
  """Test the preparation of the input object for the client action."""

  def SetOS(self, os_name):
    self.knowledge_base.os = os_name

  def ArtifactCollectorArgs(self, artifact_list, collect_knowledge_base=False):
    flow_args = rdf_artifacts.ArtifactCollectorFlowArgs(
        artifact_list=artifact_list,
        recollect_knowledge_base=collect_knowledge_base)
    return collectors.GetArtifactCollectorArgs(flow_args, self.knowledge_base)

  def setUp(self):
    super(GetArtifactCollectorArgsTest, self).setUp()

    test_artifacts_file = os.path.join(config.CONFIG["Test.data_dir"],
                                       "artifacts", "test_artifacts.json")

    artifact_registry.REGISTRY.ClearSources()
    artifact_registry.REGISTRY.ClearRegistry()
    artifact_registry.REGISTRY.AddFileSource(test_artifacts_file)

    self.knowledge_base = rdf_client.KnowledgeBase()

  def tearDown(self):
    super(GetArtifactCollectorArgsTest, self).tearDown()

    artifact_registry.REGISTRY.ClearSources()
    artifact_registry.REGISTRY.ClearRegistry()
    artifact_registry.REGISTRY.AddDefaultSources()

  def testKnowledgeBase(self):
    """Test that the knowledge base can be set."""

    self.SetOS("Windows")

    args = self.ArtifactCollectorArgs(artifact_list=[])
    os_name = args.knowledge_base.os
    self.assertEqual(os_name, "Windows")

  def testPrepareBasicClientArtifactCollectorArgs(self):
    """Test we can prepare a basic artifact."""

    artifact_list = ["TestCmdArtifact"]

    self.SetOS("Linux")

    args = self.ArtifactCollectorArgs(artifact_list)

    art_obj = args.artifacts[0]
    source = art_obj.sources[0]

    self.assertEqual(art_obj.name, "TestCmdArtifact")
    self.assertEqual(source.base_source.attributes["cmd"], "/usr/bin/dpkg")
    self.assertEqual(source.base_source.attributes.get("args", []), ["--list"])

  def testPrepareAggregatedArtifactClientArtifactCollectorArgs(self):
    """Test we can prepare the source artifacts of an aggregation artifact."""

    artifact_list = ["TestAggregationArtifact"]

    self.SetOS("Windows")

    args = self.ArtifactCollectorArgs(artifact_list)
    self.assertLen(args.artifacts, 2)

    art_obj = args.artifacts[0]
    self.assertEqual(art_obj.name, "TestOSAgnostic")
    self.assertLen(art_obj.sources, 1)
    source = art_obj.sources[0]
    self.assertEqual(source.base_source.type, "GRR_CLIENT_ACTION")

    art_obj = args.artifacts[1]
    self.assertEqual(art_obj.name, "TestCmdArtifact")
    self.assertLen(art_obj.sources, 1)
    source = art_obj.sources[0]
    self.assertEqual(source.base_source.type, "COMMAND")

  def testPrepareMultipleArtifacts(self):
    """Test we can prepare multiple artifacts of different types."""

    artifact_list = [
        "TestFilesArtifact", "DepsWindirRegex", "DepsProvidesMultiple",
        "WMIActiveScriptEventConsumer"
    ]

    self.SetOS("Windows")

    args = self.ArtifactCollectorArgs(artifact_list)

    self.assertLen(args.artifacts, 3)
    self.assertEqual(args.artifacts[0].name, "DepsWindirRegex")
    self.assertEqual(args.artifacts[1].name, "DepsProvidesMultiple")
    self.assertEqual(args.artifacts[2].name, "WMIActiveScriptEventConsumer")

    provides = args.artifacts[1].provides
    self.assertEqual(provides, ["environ_path", "environ_temp"])

    source = args.artifacts[2].sources[0]
    query = source.base_source.attributes["query"]
    self.assertEqual(query, "SELECT * FROM ActiveScriptEventConsumer")

  def testDuplicationChecks(self):
    """Test duplicated artifacts are only processed once."""

    artifact_list = [
        "TestAggregationArtifact", "TestFilesArtifact", "TestCmdArtifact",
        "TestFilesArtifact"
    ]

    self.SetOS("Linux")

    args = self.ArtifactCollectorArgs(artifact_list)

    self.assertLen(args.artifacts, 2)

  def testPrepareArtifactFilesClientArtifactCollectorArgs(self):
    """Test the preparation of ArtifactFiles Args."""

    artifact_list = ["TestArtifactFilesArtifact"]

    self.SetOS("Linux")

    file_path = os.path.join(self.base_path, "numbers.txt")
    source = rdf_artifacts.ArtifactSource(
        type=rdf_artifacts.ArtifactSource.SourceType.FILE,
        attributes={"paths": [file_path]})
    artifact_obj = artifact_registry.REGISTRY.GetArtifact("TestFileArtifact")
    artifact_obj.sources.append(source)

    args = self.ArtifactCollectorArgs(artifact_list)
    art_obj = args.artifacts[0]

    self.assertEqual(art_obj.name, "TestArtifactFilesArtifact")

    source = art_obj.sources[0]
    self.assertEqual(source.base_source.type, "ARTIFACT_FILES")

    sub_artifact_source = source.artifact_sources[0]
    self.assertEqual(sub_artifact_source.base_source.type, "FILE")

  def testPrepareArtifactsWithKBInitialization(self):
    """Test the preparation of artifacts for the KB initialization."""

    artifact_list = ["TestFilesArtifact", "DepsWindir"]

    self.SetOS("Windows")

    recollect_knowledge_base = True
    args = self.ArtifactCollectorArgs(artifact_list, recollect_knowledge_base)

    self.assertLen(args.artifacts, 2)
    artifact_names = [str(a.name) for a in args.artifacts]
    self.assertEqual(artifact_names, ["DepsControlSet", "DepsWindir"])

    first_artifact = artifact_registry.REGISTRY.GetArtifact(artifact_list[0])
    dependencies = artifact_registry.GetArtifactPathDependencies(first_artifact)
    self.assertEqual(dependencies, set([]))

  def testFlagRequestedArtifacts(self):
    """Test the artifacts requested by the user are flagged."""

    artifact_list = ["DepsWindir"]

    self.SetOS("Windows")

    recollect_knowledge_base = True
    args = self.ArtifactCollectorArgs(artifact_list, recollect_knowledge_base)

    self.assertLen(args.artifacts, 2)
    artifact_names = [str(a.name) for a in args.artifacts]
    self.assertEqual(artifact_names, ["DepsControlSet", "DepsWindir"])

    self.assertFalse(args.artifacts[0].requested_by_user)
    self.assertTrue(args.artifacts[1].requested_by_user)

  def testFlagArtifactGroup(self):
    """Test the artifacts requested by the user are flagged."""

    # An Artifact group is treated as a list of single artifacts. So, if the
    # collection of the group was requested by the user, every response to the
    # sources will be returned to the server.

    artifact_list = ["TestAggregationArtifact"]

    self.SetOS("Windows")

    args = self.ArtifactCollectorArgs(artifact_list)
    self.assertLen(args.artifacts, 2)

    art_obj = args.artifacts[0]
    self.assertEqual(art_obj.name, "TestOSAgnostic")
    self.assertTrue(art_obj.requested_by_user)

    art_obj = args.artifacts[1]
    self.assertEqual(art_obj.name, "TestCmdArtifact")
    self.assertTrue(art_obj.requested_by_user)

  def testFlagArtifactFiles(self):
    """Test the artifacts requested by the user are flagged."""

    # An ARTIFACT_FILES source is treated as one source that again has different
    # sources to collect. If the collection of the group was requested by the
    # user, every response to the sources will be returned to the server.

    artifact_list = ["TestArtifactFilesArtifact"]

    self.SetOS("Windows")

    args = self.ArtifactCollectorArgs(artifact_list)

    self.assertLen(args.artifacts, 1)
    art_obj = args.artifacts[0]
    self.assertEqual(art_obj.name, "TestArtifactFilesArtifact")
    self.assertTrue(art_obj.requested_by_user)


class TestCmdParser(parser.CommandParser):

  output_types = ["SoftwarePackage"]
  supported_artifacts = ["TestEchoArtifact"]

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


class TestFileParser(parser.FileParser):

  output_types = ["AttributedDict"]
  supported_artifacts = ["TestFileArtifact"]

  def Parse(self, stat, file_obj, knowledge_base):

    del knowledge_base  # Unused.

    lines = set([l.strip() for l in file_obj.read().splitlines()])

    users = list(filter(None, lines))

    filename = stat.pathspec.path
    cfg = {"filename": filename, "users": users}

    yield rdf_protodict.AttributedDict(**cfg)


@db_test_lib.DualDBTest
class ClientArtifactCollectorFlowTest(flow_test_lib.FlowTestsBaseclass):
  """Test the client side artifact collection test artifacts."""

  def setUp(self):
    super(ClientArtifactCollectorFlowTest, self).setUp()
    self.cleanup = None
    InitGRRWithTestArtifacts()

    self.client_id = self.SetupClient(0)

  def tearDown(self):
    super(ClientArtifactCollectorFlowTest, self).tearDown()
    if self.cleanup:
      self.cleanup()

    artifact_registry.REGISTRY.ClearSources()
    artifact_registry.REGISTRY.ClearRegistry()
    artifact_registry.REGISTRY.AddDefaultSources()

  def _RunFlow(self, flow_cls, action, artifact_list, apply_parsers):
    session_id = flow_test_lib.TestFlowHelper(
        flow_cls.__name__,
        action_mocks.ActionMock(action),
        artifact_list=artifact_list,
        token=self.token,
        apply_parsers=apply_parsers,
        client_id=self.client_id)
    return flow_test_lib.GetFlowResults(self.client_id, session_id)

  def InitializeTestFileArtifact(self, with_pathspec_attribute=False):
    file_path = os.path.join(self.base_path, "numbers.txt")
    source = rdf_artifacts.ArtifactSource(
        type=rdf_artifacts.ArtifactSource.SourceType.FILE,
        attributes={"paths": [file_path]})
    if with_pathspec_attribute:
      source.attributes = {
          "paths": [file_path],
          "pathspec_attribute": "pathspec"
      }
    artifact_obj = artifact_registry.REGISTRY.GetArtifact("TestFileArtifact")
    artifact_obj.sources.append(source)
    return file_path

  def testClientArtifactCollector(self):
    """Test artifact collector flow with a single artifact."""

    client_test_lib.Command("/usr/bin/dpkg", args=["--list"], system="Linux")

    artifact_list = ["TestCmdArtifact"]

    results = self._RunFlow(
        aff4_flows.ClientArtifactCollector,
        artifact_collector.ArtifactCollector,
        artifact_list,
        apply_parsers=False)
    self.assertLen(results, 1)

    artifact_response = results[0]
    self.assertIsInstance(artifact_response, rdf_client_action.ExecuteResponse)
    self.assertGreater(artifact_response.time_used, 0)

  def testClientArtifactCollectorWithMultipleArtifacts(self):
    """Test artifact collector flow with a single artifact."""

    client_test_lib.Command("/usr/bin/dpkg", args=["--list"], system="Linux")

    artifact_list = ["TestCmdArtifact", "TestOSAgnostic"]

    results = self._RunFlow(
        aff4_flows.ClientArtifactCollector,
        artifact_collector.ArtifactCollector,
        artifact_list,
        apply_parsers=False)
    self.assertLen(results, 2)

    artifact_response = results[0]
    self.assertIsInstance(artifact_response, rdf_client_action.ExecuteResponse)
    self.assertGreater(artifact_response.time_used, 0)

    artifact_response = results[1]
    self.assertTrue(artifact_response.string)

  def testLinuxMountCmdArtifact(self):
    """Test that LinuxMountCmd artifact can be collected."""

    artifact_list = ["LinuxMountCmd"]

    self.cleanup = InitGRRWithTestSources("""
name: LinuxMountCmd
doc: Linux output of mount.
sources:
- type: COMMAND
  attributes:
    cmd: '/bin/mount'
    args: []
labels: [System]
supported_os: [Linux]
""")

    self.assertTrue(artifact_registry.REGISTRY.GetArtifact("LinuxMountCmd"))

    # Run the ArtifactCollector to get the expected result.
    expected = self._RunFlow(
        aff4_flows.ArtifactCollectorFlow,
        standard.ExecuteCommand,
        artifact_list,
        apply_parsers=False)
    expected = expected[0]
    self.assertIsInstance(expected, rdf_client_action.ExecuteResponse)

    # Run the ClientArtifactCollector to get the actual result.
    results = self._RunFlow(
        aff4_flows.ClientArtifactCollector,
        artifact_collector.ArtifactCollector,
        artifact_list,
        apply_parsers=False)
    artifact_response = results[0]
    self.assertIsInstance(artifact_response, rdf_client_action.ExecuteResponse)

    self.assertEqual(artifact_response, expected)

  def testBasicRegistryKeyArtifact(self):
    """Test that a registry key artifact can be collected."""

    artifact_list = ["TestRegistryKey"]

    self.cleanup = InitGRRWithTestSources(r"""
name: TestRegistryKey
doc: A sample registry key artifact.
sources:
- type: REGISTRY_KEY
  attributes:
    keys: [
      'HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager'
    ]
""")

    with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.REGISTRY,
                                   vfs_test_lib.FakeRegistryVFSHandler):
      with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                     vfs_test_lib.FakeFullVFSHandler):

        # Run the ArtifactCollector to get the expected result.
        session_id = flow_test_lib.TestFlowHelper(
            aff4_flows.ArtifactCollectorFlow.__name__,
            action_mocks.FileFinderClientMock(),
            artifact_list=artifact_list,
            token=self.token,
            client_id=self.client_id,
            apply_parsers=False)
        results = flow_test_lib.GetFlowResults(self.client_id, session_id)
        expected = results[0]
        self.assertIsInstance(expected, rdf_client_fs.StatEntry)

        # Run the ClientArtifactCollector to get the actual result.
        cac_results = self._RunFlow(
            aff4_flows.ClientArtifactCollector,
            artifact_collector.ArtifactCollector,
            artifact_list,
            apply_parsers=False)
        artifact_response = cac_results[0]
        self.assertIsInstance(artifact_response, rdf_client_fs.StatEntry)

        self.assertEqual(results, cac_results)

  def testRegistryKeyArtifactWithWildcard(self):
    """Test that a registry key artifact can be collected."""

    artifact_list = ["TestRegistryKey"]

    self.cleanup = InitGRRWithTestSources(r"""
name: TestRegistryKey
doc: A sample registry key artifact.
sources:
- type: REGISTRY_KEY
  attributes:
    keys: [
      'HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager\*'
    ]
""")

    with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.REGISTRY,
                                   vfs_test_lib.FakeRegistryVFSHandler):
      with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                     vfs_test_lib.FakeFullVFSHandler):

        # Run the ArtifactCollector to get the expected result.
        session_id = flow_test_lib.TestFlowHelper(
            aff4_flows.ArtifactCollectorFlow.__name__,
            action_mocks.FileFinderClientMock(),
            artifact_list=artifact_list,
            token=self.token,
            client_id=self.client_id,
            apply_parsers=False)
        results = flow_test_lib.GetFlowResults(self.client_id, session_id)
        self.assertIsInstance(results[0], rdf_client_fs.StatEntry)

        # Run the ClientArtifactCollector to get the actual result.
        cac_results = self._RunFlow(
            aff4_flows.ClientArtifactCollector,
            artifact_collector.ArtifactCollector,
            artifact_list,
            apply_parsers=False)
        artifact_response = cac_results[0]
        self.assertIsInstance(artifact_response, rdf_client_fs.StatEntry)

        self.assertEqual(cac_results, results)

  def testRegistryKeyArtifactWithPathRecursion(self):
    """Test that a registry key artifact can be collected."""

    artifact_list = ["TestRegistryKey"]

    self.cleanup = InitGRRWithTestSources(r"""
name: TestRegistryKey
doc: A sample registry key artifact.
sources:
- type: REGISTRY_KEY
  attributes:
    keys: [
      'HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\**\Session Manager\*'
    ]
""")

    with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.REGISTRY,
                                   vfs_test_lib.FakeRegistryVFSHandler):
      with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                     vfs_test_lib.FakeFullVFSHandler):

        # Run the ArtifactCollector to get the expected result.
        session_id = flow_test_lib.TestFlowHelper(
            aff4_flows.ArtifactCollectorFlow.__name__,
            action_mocks.FileFinderClientMock(),
            artifact_list=artifact_list,
            token=self.token,
            client_id=self.client_id,
            apply_parsers=False)
        expected = flow_test_lib.GetFlowResults(self.client_id, session_id)[0]
        self.assertIsInstance(expected, rdf_client_fs.StatEntry)

        # Run the ClientArtifactCollector to get the actual result.
        results = self._RunFlow(
            aff4_flows.ClientArtifactCollector,
            artifact_collector.ArtifactCollector,
            artifact_list,
            apply_parsers=False)
        artifact_response = results[0]
        self.assertIsInstance(artifact_response, rdf_client_fs.StatEntry)

        self.assertEqual(artifact_response, expected)

  @mock.patch.object(parsers, "SINGLE_RESPONSE_PARSER_FACTORY",
                     factory.Factory(parser.SingleResponseParser))
  def testCmdArtifactWithParser(self):
    """Test a command artifact and parsing the response."""

    client_test_lib.Command("/bin/echo", args=["1"])

    parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register("TestCmd", TestCmdParser)
    try:
      artifact_list = ["TestEchoArtifact"]

      # Run the ArtifactCollector to get the expected result.
      expected = self._RunFlow(
          aff4_flows.ArtifactCollectorFlow,
          standard.ExecuteCommand,
          artifact_list,
          apply_parsers=True)
      self.assertTrue(expected)
      expected = expected[0]
      self.assertIsInstance(expected, rdf_client.SoftwarePackage)

      # Run the ClientArtifactCollector to get the actual result.
      results = self._RunFlow(
          aff4_flows.ClientArtifactCollector,
          artifact_collector.ArtifactCollector,
          artifact_list,
          apply_parsers=True)
      self.assertLen(results, 1)
      artifact_response = results[0]
      self.assertIsInstance(artifact_response, rdf_client.SoftwarePackage)

      self.assertEqual(artifact_response, expected)
    finally:
      parsers.SINGLE_RESPONSE_PARSER_FACTORY.Unregister("TestCmd")

  @mock.patch.object(parsers, "SINGLE_FILE_PARSER_FACTORY",
                     factory.Factory(parser.SingleFileParser))
  def testFileArtifactWithParser(self):
    """Test collecting a file artifact and parsing the response."""
    parsers.SINGLE_FILE_PARSER_FACTORY.Register("TestFile", TestFileParser)
    try:
      artifact_list = ["TestFileArtifact"]

      file_path = self.InitializeTestFileArtifact()

      # Run the ArtifactCollector to get the expected result.
      session_id = flow_test_lib.TestFlowHelper(
          aff4_flows.ArtifactCollectorFlow.__name__,
          action_mocks.FileFinderClientMock(),
          artifact_list=artifact_list,
          token=self.token,
          apply_parsers=True,
          client_id=self.client_id)
      results = flow_test_lib.GetFlowResults(self.client_id, session_id)
      expected = results[0]
      self.assertIsInstance(expected, rdf_protodict.AttributedDict)
      self.assertEqual(expected.filename, file_path)
      self.assertLen(expected.users, 1000)

      # Run the ClientArtifactCollector to get the actual result.
      cac_results = self._RunFlow(
          aff4_flows.ClientArtifactCollector,
          artifact_collector.ArtifactCollector,
          artifact_list,
          apply_parsers=True)
      self.assertLen(cac_results, 1)

      self.assertEqual(results, cac_results)
    finally:
      parsers.SINGLE_FILE_PARSER_FACTORY.Unregister("TestFile")

  def testAggregatedArtifact(self):
    """Test we can collect an ARTIFACT_GROUP."""

    client_test_lib.Command("/bin/echo", args=["1"])

    artifact_list = ["TestArtifactGroup"]

    self.InitializeTestFileArtifact()

    results = self._RunFlow(
        aff4_flows.ClientArtifactCollector,
        artifact_collector.ArtifactCollector,
        artifact_list,
        apply_parsers=False)
    self.assertLen(results, 2)

    artifact_response = results[0]
    self.assertIsInstance(artifact_response, rdf_client_fs.StatEntry)

    artifact_response = results[1]
    self.assertIsInstance(artifact_response, rdf_client_action.ExecuteResponse)
    self.assertEqual(artifact_response.stdout, "1\n")

  def testArtifactFiles(self):
    """Test collecting an ArtifactFiles artifact."""

    artifact_list = ["TestArtifactFilesArtifact"]

    self.InitializeTestFileArtifact()

    # Run the ArtifactCollector to get the expected result.
    session_id = flow_test_lib.TestFlowHelper(
        aff4_flows.ArtifactCollectorFlow.__name__,
        action_mocks.FileFinderClientMock(),
        artifact_list=artifact_list,
        token=self.token,
        apply_parsers=False,
        client_id=self.client_id)
    results = flow_test_lib.GetFlowResults(self.client_id, session_id)
    expected = results[0]

    self.assertIsInstance(expected, rdf_client_fs.StatEntry)

    # Run the ClientArtifactCollector to get the actual result.
    cac_results = self._RunFlow(
        aff4_flows.ClientArtifactCollector,
        artifact_collector.ArtifactCollector,
        artifact_list,
        apply_parsers=False)
    self.assertLen(cac_results, 1)
    artifact_response = cac_results[0]
    self.assertEqual(artifact_response.pathspec.path, expected.pathspec.path)

  def testArtifactFilesWithPathspecAttribute(self):
    """Test collecting ArtifactFiles with specified pathspec attribute."""

    artifact_list = ["TestArtifactFilesArtifact"]

    self.InitializeTestFileArtifact(with_pathspec_attribute=True)

    # Run the ArtifactCollector to get the expected result.
    session_id = flow_test_lib.TestFlowHelper(
        aff4_flows.ArtifactCollectorFlow.__name__,
        action_mocks.FileFinderClientMock(),
        artifact_list=artifact_list,
        token=self.token,
        apply_parsers=False,
        client_id=self.client_id)
    results = flow_test_lib.GetFlowResults(self.client_id, session_id)
    expected = results[0]

    self.assertIsInstance(expected, rdf_client_fs.StatEntry)

    # Run the ClientArtifactCollector to get the actual result.
    cac_results = self._RunFlow(
        aff4_flows.ClientArtifactCollector,
        artifact_collector.ArtifactCollector,
        artifact_list,
        apply_parsers=False)
    self.assertLen(cac_results, 1)
    artifact_response = cac_results[0]

    self.assertEqual(artifact_response.pathspec.path, expected.pathspec.path)


def InitGRRWithTestArtifacts():
  artifact_registry.REGISTRY.ClearSources()
  artifact_registry.REGISTRY.ClearRegistry()

  test_artifacts_file = os.path.join(config.CONFIG["Test.data_dir"],
                                     "artifacts", "test_artifacts.json")
  artifact_registry.REGISTRY.AddFileSource(test_artifacts_file)


def InitGRRWithTestSources(artifacts_data):
  artifact_registry.REGISTRY.ClearSources()
  artifact_registry.REGISTRY.ClearRegistry()

  artifacts_temp_dir = temp.TempDirPath()
  with open(os.path.join(artifacts_temp_dir, "test_artifacts.yaml"), "w") as fd:
    fd.write(artifacts_data)

  artifact_registry.REGISTRY.AddDirSources([artifacts_temp_dir])

  def CleanUp():
    shutil.rmtree(artifacts_temp_dir)

  return CleanUp


class ArtifactArrangerTest(test_lib.GRRBaseTest):
  """Test the ArtifactArranger gets and sorts all required artifact."""

  def setUp(self):
    super(ArtifactArrangerTest, self).setUp()
    self.cleanup = None

  def tearDown(self):
    super(ArtifactArrangerTest, self).tearDown()
    if self.cleanup:
      self.cleanup()

    artifact_registry.REGISTRY.ClearSources()
    artifact_registry.REGISTRY.ClearRegistry()
    artifact_registry.REGISTRY.AddDefaultSources()

  def testArtifactWithoutDependency(self):
    """Test that artifact list without dependencies does not change."""

    self.cleanup = InitGRRWithTestSources("""
name: Artifact0
doc: An artifact without dependencies.
sources:
- type: FILE
  attributes:
    paths:
      - '/sample/path'
supported_os: [Linux]
""")

    artifact_arranger = collectors.ArtifactArranger(
        os_name="Linux", artifacts_name_list=["Artifact0"])
    artifact_list = artifact_arranger.GetArtifactsInProperOrder()
    self.assertEqual(artifact_list, ["Artifact0"])

  def testArtifactWithBasicDependency(self):
    """Test that an artifact providing the dependency is added to the list."""

    self.cleanup = InitGRRWithTestSources("""
name: Artifact0
doc: An artifact without dependencies.
supported_os: [Linux]
provides: ["users.desktop"]
---
name: Artifact1
doc: An artifact that depends on Artifact0.
sources:
- type: FILE
  attributes:
    paths:
      - '/sample/path'
      - '/%%users.desktop%%/'
supported_os: [Linux]
""")

    artifact_arranger = collectors.ArtifactArranger(
        os_name="Linux", artifacts_name_list=["Artifact1"])
    artifact_list = artifact_arranger.GetArtifactsInProperOrder()
    self.assertEqual(artifact_list, ["Artifact0", "Artifact1"])

  def testArtifactWithDependencyChain(self):
    """Test an artifact that depends on artifacts with more dependencies."""

    self.cleanup = InitGRRWithTestSources("""
name: Artifact0
doc: An artifact without dependencies.
sources:
supported_os: [Linux]
provides: ["users.desktop"]
---
name: Artifact1
doc: An artifact that depends on Artifact0.
sources:
- type: FILE
  attributes:
    paths:
      - '/%%users.desktop%%/'
provides: ["users.homedir"]
supported_os: [Linux]
---
name: Artifact2
doc: An artifact that depends on Artifact0 and Artifact1.
sources:
- type: FILE
  attributes:
    paths:
      - '/%%users.homedir%%/'
      - '/%%users.desktop%%/'
supported_os: [Linux]
provides: ["os"]
---
name: Artifact3
doc: An artifact that depends on Artifact2.
sources:
- type: FILE
  attributes:
    paths:
      - '/%%os%%/'
supported_os: [Linux]
""")

    artifact_arranger = collectors.ArtifactArranger(
        os_name="Linux", artifacts_name_list=["Artifact3"])
    artifact_list = artifact_arranger.GetArtifactsInProperOrder()
    self.assertEqual(artifact_list,
                     ["Artifact0", "Artifact1", "Artifact2", "Artifact3"])


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
