#!/usr/bin/env python
"""Test the collector flows."""


import os

from grr.client import vfs
from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import artifact
from grr.lib import artifact_lib
from grr.lib import artifact_registry
from grr.lib import artifact_test
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
# pylint: disable=unused-import
from grr.lib.flows.general import artifact_fallbacks
from grr.lib.flows.general import collectors
# pylint: enable=unused-import
from grr.lib.flows.general import transfer
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.test_data import client_fixture

# pylint: mode=test


class CollectorTest(artifact_test.ArtifactTest):

  def _PrepareWindowsClient(self):
    client = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    client.Set(client.Schema.SYSTEM("Windows"))
    client.Set(client.Schema.OS_VERSION("6.2"))
    client.Flush()
    return client


class TestArtifactCollectors(CollectorTest):
  """Test the artifact collection mechanism with fake artifacts."""

  def setUp(self):
    """Make sure things are initialized."""
    super(TestArtifactCollectors, self).setUp()
    self.original_artifact_reg = artifact_registry.ArtifactRegistry.artifacts
    artifact_registry.ArtifactRegistry.ClearRegistry()
    self.LoadTestArtifacts()
    artifact_reg = artifact_registry.ArtifactRegistry.artifacts
    self.fakeartifact = artifact_reg["FakeArtifact"]
    self.fakeartifact2 = artifact_reg["FakeArtifact2"]

    self.output_count = 0

    with aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw") as fd:
      fd.Set(fd.Schema.SYSTEM("Linux"))
      kb = fd.Schema.KNOWLEDGE_BASE()
      artifact.SetCoreGRRKnowledgeBaseValues(kb, fd)
      fd.Set(kb)

  def tearDown(self):
    super(TestArtifactCollectors, self).tearDown()
    artifact_registry.ArtifactRegistry.artifacts = self.original_artifact_reg
    self.fakeartifact.sources = []  # Reset any ArtifactSources
    self.fakeartifact.conditions = []  # Reset any Conditions

    self.fakeartifact2.sources = []  # Reset any ArtifactSources
    self.fakeartifact2.conditions = []  # Reset any Conditions

  def testInterpolateArgs(self):
    collect_flow = collectors.ArtifactCollectorFlow(None, token=self.token)

    collect_flow.state.Register("knowledge_base", rdf_client.KnowledgeBase())
    collect_flow.current_artifact_name = "blah"
    collect_flow.state.knowledge_base.MergeOrAddUser(
        rdf_client.KnowledgeBaseUser(username="test1"))
    collect_flow.state.knowledge_base.MergeOrAddUser(
        rdf_client.KnowledgeBaseUser(username="test2"))

    test_rdf = rdf_client.KnowledgeBase()
    action_args = {"usernames": ["%%users.username%%", "%%users.username%%"],
                   "nointerp": "asdfsdf", "notastring": test_rdf}
    kwargs = collect_flow.InterpolateDict(action_args)
    self.assertItemsEqual(kwargs["usernames"],
                          ["test1", "test2", "test1", "test2"])
    self.assertEqual(kwargs["nointerp"], "asdfsdf")
    self.assertEqual(kwargs["notastring"], test_rdf)

    # We should be using an array since users.username will expand to multiple
    # values.
    self.assertRaises(ValueError, collect_flow.InterpolateDict,
                      {"bad": "%%users.username%%"})

    list_args = collect_flow.InterpolateList(["%%users.username%%",
                                              r"%%users.username%%\aa"])
    self.assertItemsEqual(list_args, ["test1", "test2", r"test1\aa",
                                      r"test2\aa"])

    list_args = collect_flow.InterpolateList(["one"])
    self.assertEqual(list_args, ["one"])

  def testGrepRegexCombination(self):
    collect_flow = collectors.ArtifactCollectorFlow(None, token=self.token)
    self.assertEqual(collect_flow._CombineRegex([r"simple"]),
                     "simple")
    self.assertEqual(collect_flow._CombineRegex(["a", "b"]),
                     "(a)|(b)")
    self.assertEqual(collect_flow._CombineRegex(["a", "b", "c"]),
                     "(a)|(b)|(c)")
    self.assertEqual(collect_flow._CombineRegex(["a|b", "[^_]b", "c|d"]),
                     "(a|b)|([^_]b)|(c|d)")

  def testGrep(self):
    class MockCallFlow(object):

      def CallFlow(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    mock_call_flow = MockCallFlow()
    with utils.Stubber(collectors.ArtifactCollectorFlow, "CallFlow",
                       mock_call_flow.CallFlow):

      collect_flow = collectors.ArtifactCollectorFlow(None, token=self.token)
      collect_flow.state.Register("knowledge_base", rdf_client.KnowledgeBase())
      collect_flow.current_artifact_name = "blah"
      collect_flow.state.knowledge_base.MergeOrAddUser(
          rdf_client.KnowledgeBaseUser(username="test1"))
      collect_flow.state.knowledge_base.MergeOrAddUser(
          rdf_client.KnowledgeBaseUser(username="test2"))

      collector = artifact_lib.ArtifactSource(
          type=artifact_lib.ArtifactSource.SourceType.GREP,
          attributes={"paths": ["/etc/passwd"],
                      "content_regex_list": [r"^a%%users.username%%b$"]})
      collect_flow.Grep(collector, rdf_paths.PathSpec.PathType.TSK)

    conditions = mock_call_flow.kwargs["conditions"]
    self.assertEqual(len(conditions), 1)
    regexes = conditions[0].contents_regex_match.regex.SerializeToString()
    self.assertItemsEqual(regexes.split("|"), ["(^atest1b$)", "(^atest2b$)"])
    self.assertEqual(mock_call_flow.kwargs["paths"], ["/etc/passwd"])

  def testGetArtifact1(self):
    """Test we can get a basic artifact."""

    client_mock = action_mocks.ActionMock("TransferBuffer", "StatFile", "Find",
                                          "FingerprintFile", "HashBuffer")
    client = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    client.Set(client.Schema.SYSTEM("Linux"))
    client.Flush()

    # Dynamically add a ArtifactSource specifying the base path.
    file_path = os.path.join(self.base_path, "test_img.dd")
    coll1 = artifact_lib.ArtifactSource(
        type=artifact_lib.ArtifactSource.SourceType.FILE,
        attributes={"paths": [file_path]})
    self.fakeartifact.sources.append(coll1)

    artifact_list = ["FakeArtifact"]
    for _ in test_lib.TestFlowHelper(
        "ArtifactCollectorFlow", client_mock, artifact_list=artifact_list,
        use_tsk=False, token=self.token, client_id=self.client_id):
      pass

    # Test the AFF4 file that was created.
    fd1 = aff4.FACTORY.Open("%s/fs/os/%s" % (self.client_id, file_path),
                            token=self.token)
    fd2 = open(file_path)
    fd2.seek(0, 2)

    self.assertEqual(fd2.tell(), int(fd1.Get(fd1.Schema.SIZE)))

  def testRunGrrClientActionArtifact(self):
    """Test we can get a GRR client artifact."""
    client_mock = action_mocks.ActionMock("ListProcesses")
    client = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    client.Set(client.Schema.SYSTEM("Linux"))
    client.Flush()

    coll1 = artifact_lib.ArtifactSource(
        type=artifact_lib.ArtifactSource.SourceType.GRR_CLIENT_ACTION,
        attributes={"client_action": r"ListProcesses"})
    self.fakeartifact.sources.append(coll1)
    artifact_list = ["FakeArtifact"]
    for _ in test_lib.TestFlowHelper("ArtifactCollectorFlow", client_mock,
                                     artifact_list=artifact_list,
                                     token=self.token, client_id=self.client_id,
                                     output="test_artifact"):
      pass

    # Test the AFF4 file that was created.
    fd = aff4.FACTORY.Open(rdfvalue.RDFURN(self.client_id).Add("test_artifact"),
                           token=self.token)
    self.assertTrue(isinstance(list(fd)[0], rdf_client.Process))
    self.assertTrue(len(fd) > 5)

  def testRunGrrClientActionArtifactSplit(self):
    """Test that artifacts get split into separate collections."""
    client_mock = action_mocks.ActionMock("ListProcesses", "StatFile")
    client = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    client.Set(client.Schema.SYSTEM("Linux"))
    client.Flush()

    coll1 = artifact_lib.ArtifactSource(
        type=artifact_lib.ArtifactSource.SourceType.GRR_CLIENT_ACTION,
        attributes={"client_action": r"ListProcesses"})
    self.fakeartifact.sources.append(coll1)
    self.fakeartifact2.sources.append(coll1)
    artifact_list = ["FakeArtifact", "FakeArtifact2"]
    for _ in test_lib.TestFlowHelper("ArtifactCollectorFlow", client_mock,
                                     artifact_list=artifact_list,
                                     token=self.token, client_id=self.client_id,
                                     output="test_artifact",
                                     split_output_by_artifact=True):
      pass

    # Check that we got two separate collections based on artifact name
    fd = aff4.FACTORY.Open(rdfvalue.RDFURN(
        self.client_id).Add("test_artifact_FakeArtifact"),
                           token=self.token)
    self.assertTrue(isinstance(list(fd)[0], rdf_client.Process))
    self.assertTrue(len(fd) > 5)

    fd = aff4.FACTORY.Open(rdfvalue.RDFURN(
        self.client_id).Add("test_artifact_FakeArtifact2"),
                           token=self.token)
    self.assertTrue(len(fd) > 5)
    self.assertTrue(isinstance(list(fd)[0], rdf_client.Process))

  def testConditions(self):
    """Test we can get a GRR client artifact with conditions."""
    # Run with false condition.
    client_mock = action_mocks.ActionMock("ListProcesses")
    coll1 = artifact_lib.ArtifactSource(
        type=artifact_lib.ArtifactSource.SourceType.GRR_CLIENT_ACTION,
        attributes={"client_action": "ListProcesses"},
        conditions=["os == 'Windows'"])
    self.fakeartifact.sources.append(coll1)
    fd = self._RunClientActionArtifact(client_mock, ["FakeArtifact"])
    self.assertEqual(fd.__class__.__name__, "AFF4Volume")

    # Now run with matching or condition.
    coll1.conditions = ["os == 'Linux' or os == 'Windows'"]
    self.fakeartifact.sources = []
    self.fakeartifact.sources.append(coll1)
    fd = self._RunClientActionArtifact(client_mock, ["FakeArtifact"])
    self.assertEqual(fd.__class__.__name__, "RDFValueCollection")

    # Now run with impossible or condition.
    coll1.conditions.append("os == 'NotTrue'")
    self.fakeartifact.sources = []
    self.fakeartifact.sources.append(coll1)
    fd = self._RunClientActionArtifact(client_mock, ["FakeArtifact"])
    self.assertEqual(fd.__class__.__name__, "AFF4Volume")

  def testSupportedOS(self):
    """Test supported_os inside the collector object."""
    # Run with false condition.
    client_mock = action_mocks.ActionMock("ListProcesses")
    coll1 = artifact_lib.ArtifactSource(
        type=artifact_lib.ArtifactSource.SourceType.GRR_CLIENT_ACTION,
        attributes={"client_action": "ListProcesses"}, supported_os=["Windows"])
    self.fakeartifact.sources.append(coll1)
    fd = self._RunClientActionArtifact(client_mock, ["FakeArtifact"])
    self.assertEqual(fd.__class__.__name__, "AFF4Volume")

    # Now run with matching or condition.
    coll1.conditions = []
    coll1.supported_os = ["Linux", "Windows"]
    self.fakeartifact.sources = []
    self.fakeartifact.sources.append(coll1)
    fd = self._RunClientActionArtifact(client_mock, ["FakeArtifact"])
    self.assertEqual(fd.__class__.__name__, "RDFValueCollection")

    # Now run with impossible or condition.
    coll1.conditions = ["os == 'Linux' or os == 'Windows'"]
    coll1.supported_os = ["NotTrue"]
    self.fakeartifact.sources = []
    self.fakeartifact.sources.append(coll1)
    fd = self._RunClientActionArtifact(client_mock, ["FakeArtifact"])
    self.assertEqual(fd.__class__.__name__, "AFF4Volume")

  def _RunClientActionArtifact(self, client_mock, artifact_list):
    client = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    client.Set(client.Schema.SYSTEM("Linux"))
    client.Flush()
    self.output_count += 1
    output = "test_artifact_%d" % self.output_count
    for _ in test_lib.TestFlowHelper("ArtifactCollectorFlow", client_mock,
                                     artifact_list=artifact_list,
                                     token=self.token, client_id=self.client_id,
                                     output=output):
      pass

    # Test the AFF4 file was not created, as flow should not have run due to
    # conditions.
    fd = aff4.FACTORY.Open(rdfvalue.RDFURN(self.client_id).Add(output),
                           token=self.token)
    return fd


class TestArtifactCollectorsInteractions(CollectorTest):
  """Test the collection of artifacts.

  This class loads both real and test artifacts to test the interaction of badly
  defined artifacts with real artifacts.
  """

  def setUp(self):
    """Add test artifacts to existing registry."""
    super(TestArtifactCollectorsInteractions, self).setUp()
    self.original_artifact_reg = artifact_registry.ArtifactRegistry.artifacts
    self.LoadTestArtifacts()

  def tearDown(self):
    super(TestArtifactCollectorsInteractions, self).tearDown()
    artifact_registry.ArtifactRegistry.artifacts = self.original_artifact_reg

  def testProcessCollectedArtifacts(self):
    """Test downloading files from artifacts."""
    self._PrepareWindowsClient()

    vfs.VFS_HANDLERS[
        rdf_paths.PathSpec.PathType.REGISTRY] = test_lib.FakeRegistryVFSHandler
    vfs.VFS_HANDLERS[
        rdf_paths.PathSpec.PathType.OS] = test_lib.FakeFullVFSHandler

    client_mock = action_mocks.ActionMock("TransferBuffer", "StatFile", "Find",
                                          "HashBuffer", "FingerprintFile",
                                          "ListDirectory")

    # Get KB initialized
    for _ in test_lib.TestFlowHelper(
        "KnowledgeBaseInitializationFlow", client_mock,
        client_id=self.client_id, token=self.token):
      pass

    artifact_list = ["WindowsPersistenceMechanismFiles"]
    with test_lib.Instrument(
        transfer.MultiGetFile, "Start") as getfile_instrument:
      for _ in test_lib.TestFlowHelper("ArtifactCollectorFlow", client_mock,
                                       artifact_list=artifact_list,
                                       token=self.token,
                                       client_id=self.client_id,
                                       output="analysis/{p}/{u}-{t}",
                                       split_output_by_artifact=True):
        pass

      # Check MultiGetFile got called for our runkey files
      # TODO(user): RunKeys for S-1-5-20 are not found because users.sid only
      # expands to users with profiles.
      pathspecs = getfile_instrument.args[0][0].args.pathspecs
      self.assertItemsEqual([x.path for x in pathspecs],
                            [u"C:\\Windows\\TEMP\\A.exe"])

    artifact_list = ["BadPathspecArtifact"]
    with test_lib.Instrument(
        transfer.MultiGetFile, "Start") as getfile_instrument:
      for _ in test_lib.TestFlowHelper("ArtifactCollectorFlow", client_mock,
                                       artifact_list=artifact_list,
                                       token=self.token,
                                       client_id=self.client_id,
                                       output="analysis/{p}/{u}-{t}",
                                       split_output_by_artifact=True):
        pass

      self.assertFalse(getfile_instrument.args)


class TestArtifactCollectorsRealArtifacts(CollectorTest):
  """Test the collection of real artifacts."""

  def _CheckDriveAndRoot(self):
    client_mock = action_mocks.ActionMock("StatFile", "ListDirectory")

    for _ in test_lib.TestFlowHelper("ArtifactCollectorFlow", client_mock,
                                     artifact_list=[
                                         "SystemDriveEnvironmentVariable"],
                                     token=self.token, client_id=self.client_id,
                                     output="testsystemdrive"):
      pass

    fd = aff4.FACTORY.Open(rdfvalue.RDFURN(
        self.client_id).Add("testsystemdrive"), token=self.token)
    self.assertEqual(len(fd), 1)
    self.assertEqual(str(fd[0]), "C:")

    for _ in test_lib.TestFlowHelper("ArtifactCollectorFlow", client_mock,
                                     artifact_list=["SystemRoot"],
                                     token=self.token, client_id=self.client_id,
                                     output="testsystemroot"):
      pass

    fd = aff4.FACTORY.Open(
        rdfvalue.RDFURN(self.client_id).Add("testsystemroot"), token=self.token)
    self.assertEqual(len(fd), 1)
    # Filesystem gives WINDOWS, registry gives Windows
    self.assertTrue(str(fd[0]) in [r"C:\Windows", r"C:\WINDOWS"])

  def testSystemDriveArtifact(self):
    self._PrepareWindowsClient()

    class BrokenClientMock(action_mocks.ActionMock):

      def StatFile(self, _):
        raise IOError

      def ListDirectory(self, _):
        raise IOError

    # No registry, broken filesystem, this should just raise.
    with self.assertRaises(RuntimeError):
      for _ in test_lib.TestFlowHelper("ArtifactCollectorFlow",
                                       BrokenClientMock(), artifact_list=[
                                           "SystemDriveEnvironmentVariable"],
                                       token=self.token,
                                       client_id=self.client_id,
                                       output="testsystemdrive"):
        pass

    # No registry, so this should use the fallback flow
    vfs.VFS_HANDLERS[
        rdf_paths.PathSpec.PathType.OS] = test_lib.ClientVFSHandlerFixture
    self._CheckDriveAndRoot()

    # Registry is present, so this should use the regular artifact collection
    vfs.VFS_HANDLERS[
        rdf_paths.PathSpec.PathType.REGISTRY] = test_lib.FakeRegistryVFSHandler
    self._CheckDriveAndRoot()

  def testRunWMIComputerSystemProductArtifact(self):

    class WMIActionMock(action_mocks.ActionMock):

      def WmiQuery(self, _):
        return client_fixture.WMI_CMP_SYS_PRD

    self._PrepareWindowsClient()
    client_mock = WMIActionMock()
    for _ in test_lib.TestFlowHelper(
        "ArtifactCollectorFlow", client_mock,
        artifact_list=["WMIComputerSystemProduct"], token=self.token,
        client_id=self.client_id,
        dependencies=
        artifact_lib.ArtifactCollectorFlowArgs.Dependency.IGNORE_DEPS,
        store_results_in_aff4=True):
      pass

    client = aff4.FACTORY.Open(self.client_id, token=self.token,)
    hardware = client.Get(client.Schema.HARDWARE_INFO)
    self.assertTrue(isinstance(hardware, rdf_client.HardwareInfo))
    self.assertEqual(str(hardware.serial_number), "2RXYYZ1")
    self.assertEqual(str(hardware.system_manufacturer), "Dell Inc.")

  def testRunWMIArtifact(self):

    class WMIActionMock(action_mocks.ActionMock):

      def WmiQuery(self, _):
        return client_fixture.WMI_SAMPLE

    self._PrepareWindowsClient()

    client_mock = WMIActionMock()
    for _ in test_lib.TestFlowHelper(
        "ArtifactCollectorFlow", client_mock, artifact_list=["WMILogicalDisks"],
        token=self.token, client_id=self.client_id,
        dependencies=
        artifact_lib.ArtifactCollectorFlowArgs.Dependency.IGNORE_DEPS,
        store_results_in_aff4=True):
      pass

    # Test that we set the client VOLUMES attribute
    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    volumes = client.Get(client.Schema.VOLUMES)
    self.assertEqual(len(volumes), 2)
    for result in volumes:
      self.assertTrue(isinstance(result, rdf_client.Volume))
      self.assertTrue(result.windows.drive_letter in ["Z:", "C:"])
      if result.windows.drive_letter == "C:":
        self.assertAlmostEqual(result.FreeSpacePercent(), 76.142, delta=0.001)
        self.assertEqual(result.Name(), "C:")
      elif result.windows.drive_letter == "Z:":
        self.assertEqual(result.Name(), "homefileshare$")
        self.assertAlmostEqual(result.FreeSpacePercent(), 58.823, delta=0.001)

  def testWMIBaseObject(self):
    class WMIActionMock(action_mocks.ActionMock):

      base_objects = []

      def WmiQuery(self, args):
        self.base_objects.append(args.base_object)
        return client_fixture.WMI_SAMPLE

    self._PrepareWindowsClient()

    client_mock = WMIActionMock()
    for _ in test_lib.TestFlowHelper(
        "ArtifactCollectorFlow", client_mock,
        artifact_list=["WMIActiveScriptEventConsumer"],
        token=self.token, client_id=self.client_id,
        dependencies=
        artifact_lib.ArtifactCollectorFlowArgs.Dependency.IGNORE_DEPS):
      pass

    # Make sure the artifact's base_object made it into the WmiQuery call.
    artifact_obj = artifact_registry.ArtifactRegistry.artifacts[
        "WMIActiveScriptEventConsumer"]
    self.assertItemsEqual(WMIActionMock.base_objects,
                          [artifact_obj.sources[0].attributes["base_object"]])

  def testRetrieveDependencies(self):
    """Test getting an artifact without a KB using retrieve_depdendencies."""
    self._PrepareWindowsClient()

    vfs.VFS_HANDLERS[
        rdf_paths.PathSpec.PathType.REGISTRY] = test_lib.FakeRegistryVFSHandler
    vfs.VFS_HANDLERS[
        rdf_paths.PathSpec.PathType.OS] = test_lib.FakeFullVFSHandler

    client_mock = action_mocks.ActionMock("TransferBuffer", "StatFile", "Find",
                                          "HashBuffer", "FingerprintFile",
                                          "ListDirectory")

    artifact_list = ["WinDirEnvironmentVariable"]
    for _ in test_lib.TestFlowHelper(
        "ArtifactCollectorFlow", client_mock, artifact_list=artifact_list,
        token=self.token, client_id=self.client_id,
        dependencies=
        artifact_lib.ArtifactCollectorFlowArgs.Dependency.FETCH_NOW,
        output="testRetrieveDependencies"):
      pass

    output = aff4.FACTORY.Open(self.client_id.Add("testRetrieveDependencies"),
                               token=self.token)
    self.assertEqual(len(output), 1)
    self.assertEqual(output[0], r"C:\Windows")


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
