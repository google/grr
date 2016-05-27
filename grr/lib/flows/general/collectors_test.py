#!/usr/bin/env python
"""Test the collector flows."""


import os

import mock

from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import artifact
from grr.lib import artifact_registry
from grr.lib import artifact_utils
from grr.lib import client_fixture
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.aff4_objects import collects
# pylint: disable=unused-import
from grr.lib.flows.general import artifact_fallbacks
from grr.lib.flows.general import collectors
# pylint: enable=unused-import
from grr.lib.flows.general import transfer
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import protodict as rdf_protodict

# pylint: mode=test


class CollectorTest(test_lib.FlowTestsBaseclass):

  def setUp(self):
    """Make sure things are initialized."""
    super(CollectorTest, self).setUp()
    test_artifacts_file = os.path.join(config_lib.CONFIG["Test.data_dir"],
                                       "artifacts", "test_artifacts.json")
    artifact_registry.REGISTRY.AddFileSource(test_artifacts_file)


class TestArtifactCollectors(CollectorTest):
  """Test the artifact collection mechanism with fake artifacts."""

  def setUp(self):
    """Make sure things are initialized."""
    super(TestArtifactCollectors, self).setUp()
    self.fakeartifact = artifact_registry.REGISTRY.GetArtifact("FakeArtifact")
    self.fakeartifact2 = artifact_registry.REGISTRY.GetArtifact("FakeArtifact2")

    self.output_count = 0

    with aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw") as fd:
      fd.Set(fd.Schema.SYSTEM("Linux"))
      kb = fd.Schema.KNOWLEDGE_BASE()
      artifact.SetCoreGRRKnowledgeBaseValues(kb, fd)
      fd.Set(kb)

  def tearDown(self):
    super(TestArtifactCollectors, self).tearDown()
    self.fakeartifact.sources = []  # Reset any ArtifactSources
    self.fakeartifact.conditions = []  # Reset any Conditions

    self.fakeartifact2.sources = []  # Reset any ArtifactSources
    self.fakeartifact2.conditions = []  # Reset any Conditions

  def testInterpolateArgs(self):
    collect_flow = collectors.ArtifactCollectorFlow(None, token=self.token)

    collect_flow.state.Register("knowledge_base", rdf_client.KnowledgeBase())
    collect_flow.current_artifact_name = "blah"
    collect_flow.state.knowledge_base.MergeOrAddUser(rdf_client.User(
        username="test1"))
    collect_flow.state.knowledge_base.MergeOrAddUser(rdf_client.User(
        username="test2"))
    collect_flow.args = artifact_utils.ArtifactCollectorFlowArgs()

    test_rdf = rdf_client.KnowledgeBase()
    action_args = {"usernames": ["%%users.username%%", "%%users.username%%"],
                   "nointerp": "asdfsdf",
                   "notastring": test_rdf}
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

    # Ignore the failure in users.desktop, report the others.
    collect_flow.args.ignore_interpolation_errors = True
    list_args = collect_flow.InterpolateList(["%%users.desktop%%",
                                              r"%%users.username%%\aa"])
    self.assertItemsEqual(list_args, [r"test1\aa", r"test2\aa"])

    # Both fail.
    list_args = collect_flow.InterpolateList([r"%%users.desktop%%\aa",
                                              r"%%users.sid%%\aa"])
    self.assertItemsEqual(list_args, [])

  def testGrepRegexCombination(self):
    collect_flow = collectors.ArtifactCollectorFlow(None, token=self.token)
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
    with utils.Stubber(collectors.ArtifactCollectorFlow, "CallFlow",
                       mock_call_flow.CallFlow):

      collect_flow = collectors.ArtifactCollectorFlow(None, token=self.token)
      collect_flow.args = mock.Mock()
      collect_flow.args.ignore_interpolation_errors = False
      collect_flow.state.Register("knowledge_base", rdf_client.KnowledgeBase())
      collect_flow.current_artifact_name = "blah"
      collect_flow.state.knowledge_base.MergeOrAddUser(rdf_client.User(
          username="test1"))
      collect_flow.state.knowledge_base.MergeOrAddUser(rdf_client.User(
          username="test2"))

      collector = artifact_registry.ArtifactSource(
          type=artifact_registry.ArtifactSource.SourceType.GREP,
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
                                          "FingerprintFile", "HashBuffer",
                                          "HashFile")
    client = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    client.Set(client.Schema.SYSTEM("Linux"))
    client.Flush()

    # Dynamically add a ArtifactSource specifying the base path.
    file_path = os.path.join(self.base_path, "test_img.dd")
    coll1 = artifact_registry.ArtifactSource(
        type=artifact_registry.ArtifactSource.SourceType.FILE,
        attributes={"paths": [file_path]})
    self.fakeartifact.sources.append(coll1)

    artifact_list = ["FakeArtifact"]
    for _ in test_lib.TestFlowHelper("ArtifactCollectorFlow",
                                     client_mock,
                                     artifact_list=artifact_list,
                                     use_tsk=False,
                                     token=self.token,
                                     client_id=self.client_id):
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

    coll1 = artifact_registry.ArtifactSource(
        type=artifact_registry.ArtifactSource.SourceType.GRR_CLIENT_ACTION,
        attributes={"client_action": r"ListProcesses"})
    self.fakeartifact.sources.append(coll1)
    artifact_list = ["FakeArtifact"]
    for _ in test_lib.TestFlowHelper("ArtifactCollectorFlow",
                                     client_mock,
                                     artifact_list=artifact_list,
                                     token=self.token,
                                     client_id=self.client_id,
                                     output="test_artifact"):
      pass

    # Test the AFF4 file that was created.
    fd = aff4.FACTORY.Open(
        rdfvalue.RDFURN(self.client_id).Add("test_artifact"),
        token=self.token)
    self.assertTrue(isinstance(list(fd)[0], rdf_client.Process))
    self.assertTrue(len(fd) > 5)

  def testRunGrrClientActionArtifactSplit(self):
    """Test that artifacts get split into separate collections."""
    client_mock = action_mocks.ActionMock("ListProcesses", "StatFile")
    client = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    client.Set(client.Schema.SYSTEM("Linux"))
    client.Flush()

    coll1 = artifact_registry.ArtifactSource(
        type=artifact_registry.ArtifactSource.SourceType.GRR_CLIENT_ACTION,
        attributes={"client_action": r"ListProcesses"})
    self.fakeartifact.sources.append(coll1)
    self.fakeartifact2.sources.append(coll1)
    artifact_list = ["FakeArtifact", "FakeArtifact2"]
    for _ in test_lib.TestFlowHelper("ArtifactCollectorFlow",
                                     client_mock,
                                     artifact_list=artifact_list,
                                     token=self.token,
                                     client_id=self.client_id,
                                     output="test_artifact",
                                     split_output_by_artifact=True):
      pass

    # Check that we got two separate collections based on artifact name
    fd = aff4.FACTORY.Open(
        rdfvalue.RDFURN(self.client_id).Add("test_artifact_FakeArtifact"),
        token=self.token)
    self.assertTrue(isinstance(list(fd)[0], rdf_client.Process))
    self.assertTrue(len(fd) > 5)

    fd = aff4.FACTORY.Open(
        rdfvalue.RDFURN(self.client_id).Add("test_artifact_FakeArtifact2"),
        token=self.token)
    self.assertTrue(len(fd) > 5)
    self.assertTrue(isinstance(list(fd)[0], rdf_client.Process))

  def testConditions(self):
    """Test we can get a GRR client artifact with conditions."""
    # Run with false condition.
    client_mock = action_mocks.ActionMock("ListProcesses")
    coll1 = artifact_registry.ArtifactSource(
        type=artifact_registry.ArtifactSource.SourceType.GRR_CLIENT_ACTION,
        attributes={"client_action": "ListProcesses"},
        conditions=["os == 'Windows'"])
    self.fakeartifact.sources.append(coll1)
    fd = self._RunClientActionArtifact(client_mock, ["FakeArtifact"])
    self.assertEqual(fd.__class__, aff4.AFF4Volume)

    # Now run with matching or condition.
    coll1.conditions = ["os == 'Linux' or os == 'Windows'"]
    self.fakeartifact.sources = []
    self.fakeartifact.sources.append(coll1)
    fd = self._RunClientActionArtifact(client_mock, ["FakeArtifact"])
    self.assertEqual(fd.__class__, collects.RDFValueCollection)

    # Now run with impossible or condition.
    coll1.conditions.append("os == 'NotTrue'")
    self.fakeartifact.sources = []
    self.fakeartifact.sources.append(coll1)
    fd = self._RunClientActionArtifact(client_mock, ["FakeArtifact"])
    self.assertEqual(fd.__class__, aff4.AFF4Volume)

  def testRegistryValueArtifact(self):
    with test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.REGISTRY,
                               test_lib.FakeRegistryVFSHandler):
      with test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                 test_lib.FakeFullVFSHandler):

        client_mock = action_mocks.ActionMock("StatFile")
        coll1 = artifact_registry.ArtifactSource(
            type=artifact_registry.ArtifactSource.SourceType.REGISTRY_VALUE,
            attributes={"key_value_pairs": [{
                "key": (r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet"
                        r"\Control\Session Manager"),
                "value": "BootExecute"
            }]})
        self.fakeartifact.sources.append(coll1)
        artifact_list = ["FakeArtifact"]
        for _ in test_lib.TestFlowHelper("ArtifactCollectorFlow",
                                         client_mock,
                                         artifact_list=artifact_list,
                                         token=self.token,
                                         client_id=self.client_id,
                                         output="test_artifact"):
          pass

    # Test the statentry got stored with the correct aff4path.
    fd = aff4.FACTORY.Open(
        rdfvalue.RDFURN(self.client_id).Add("test_artifact"),
        token=self.token)
    self.assertTrue(isinstance(list(fd)[0], rdf_client.StatEntry))
    self.assertTrue(str(fd[0].aff4path).endswith("BootExecute"))

  def testRegistryDefaultValueArtifact(self):
    with test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.REGISTRY,
                               test_lib.FakeRegistryVFSHandler):
      with test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                 test_lib.FakeFullVFSHandler):

        client_mock = action_mocks.ActionMock("StatFile")
        coll1 = artifact_registry.ArtifactSource(
            type=artifact_registry.ArtifactSource.SourceType.REGISTRY_VALUE,
            attributes={"key_value_pairs": [{
                "key": (r"HKEY_LOCAL_MACHINE/SOFTWARE/ListingTest"),
                "value": ""
            }]})
        self.fakeartifact.sources.append(coll1)
        artifact_list = ["FakeArtifact"]
        for _ in test_lib.TestFlowHelper("ArtifactCollectorFlow",
                                         client_mock,
                                         artifact_list=artifact_list,
                                         token=self.token,
                                         client_id=self.client_id,
                                         output="test_artifact"):
          pass

    fd = aff4.FACTORY.Open(
        rdfvalue.RDFURN(self.client_id).Add("test_artifact"),
        token=self.token)
    self.assertTrue(isinstance(list(fd)[0], rdf_client.StatEntry))
    self.assertEqual(fd[0].registry_data.GetValue(), "DefaultValue")

  def testSupportedOS(self):
    """Test supported_os inside the collector object."""
    # Run with false condition.
    client_mock = action_mocks.ActionMock("ListProcesses")
    coll1 = artifact_registry.ArtifactSource(
        type=artifact_registry.ArtifactSource.SourceType.GRR_CLIENT_ACTION,
        attributes={"client_action": "ListProcesses"},
        supported_os=["Windows"])
    self.fakeartifact.sources.append(coll1)
    fd = self._RunClientActionArtifact(client_mock, ["FakeArtifact"])
    self.assertEqual(fd.__class__, aff4.AFF4Volume)

    # Now run with matching or condition.
    coll1.conditions = []
    coll1.supported_os = ["Linux", "Windows"]
    self.fakeartifact.sources = []
    self.fakeartifact.sources.append(coll1)
    fd = self._RunClientActionArtifact(client_mock, ["FakeArtifact"])
    self.assertEqual(fd.__class__, collects.RDFValueCollection)

    # Now run with impossible or condition.
    coll1.conditions = ["os == 'Linux' or os == 'Windows'"]
    coll1.supported_os = ["NotTrue"]
    self.fakeartifact.sources = []
    self.fakeartifact.sources.append(coll1)
    fd = self._RunClientActionArtifact(client_mock, ["FakeArtifact"])
    self.assertEqual(fd.__class__, aff4.AFF4Volume)

  def _RunClientActionArtifact(self, client_mock, artifact_list):
    client = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    client.Set(client.Schema.SYSTEM("Linux"))
    client.Flush()
    self.output_count += 1
    output = "test_artifact_%d" % self.output_count
    for _ in test_lib.TestFlowHelper("ArtifactCollectorFlow",
                                     client_mock,
                                     artifact_list=artifact_list,
                                     token=self.token,
                                     client_id=self.client_id,
                                     output=output):
      pass

    # Test the AFF4 file was not created, as flow should not have run due to
    # conditions.
    fd = aff4.FACTORY.Open(
        rdfvalue.RDFURN(self.client_id).Add(output),
        token=self.token)
    return fd


class TestArtifactCollectorsInteractions(CollectorTest):
  """Test the collection of artifacts.

  This class loads both real and test artifacts to test the interaction of badly
  defined artifacts with real artifacts.
  """

  def testNewArtifactLoaded(self):
    """Simulate a new artifact being loaded into the store via the UI."""
    cmd_artifact = """name: "TestCmdArtifact"
doc: "Test command artifact for dpkg."
sources:
- type: "COMMAND"
  attributes:
    cmd: "/usr/bin/dpkg"
    args: ["--list"]
labels: [ "Software" ]
supported_os: [ "Linux" ]
"""
    no_datastore_artifact = """name: "NotInDatastore"
doc: "Test command artifact for dpkg."
sources:
- type: "COMMAND"
  attributes:
    cmd: "/usr/bin/dpkg"
    args: ["--list"]
labels: [ "Software" ]
supported_os: [ "Linux" ]
"""

    collect_flow = collectors.ArtifactCollectorFlow(None, token=self.token)
    artifact_registry.REGISTRY.GetArtifact("TestCmdArtifact")
    artifact_registry.REGISTRY.ClearRegistry()
    artifact_registry.REGISTRY._dirty = False
    with self.assertRaises(artifact_registry.ArtifactNotRegisteredError):
      artifact_registry.REGISTRY.GetArtifact("TestCmdArtifact")

    with self.assertRaises(artifact_registry.ArtifactNotRegisteredError):
      artifact_registry.REGISTRY.GetArtifact("NotInDatastore")

    # Add artifact to datastore but not registry
    for artifact_val in artifact_registry.REGISTRY.ArtifactsFromYaml(
        cmd_artifact):
      with aff4.FACTORY.Open("aff4:/artifact_store",
                             aff4_type=collects.RDFValueCollection,
                             token=self.token,
                             mode="rw") as artifact_coll:
        artifact_coll.Add(artifact_val)

    # Add artifact to registry but not datastore
    for artifact_val in artifact_registry.REGISTRY.ArtifactsFromYaml(
        no_datastore_artifact):
      artifact_registry.REGISTRY.RegisterArtifact(artifact_val,
                                                  source="datastore",
                                                  overwrite_if_exists=False)

    # This should succeeded because the artifacts will be reloaded from the
    # datastore.
    self.assertTrue(collect_flow._GetArtifactFromName("TestCmdArtifact"))

    # We registered this artifact with datastore source but didn't write it into
    # aff4. This simulates an artifact that was uploaded in the UI then later
    # deleted. We expect it to get cleared when the artifacts are reloaded from
    # the datastore.
    with self.assertRaises(artifact_registry.ArtifactNotRegisteredError):
      artifact_registry.REGISTRY.GetArtifact("NotInDatastore")

  def testProcessCollectedArtifacts(self):
    """Test downloading files from artifacts."""
    self.SetupClients(1, system="Windows", os_version="6.2")

    with test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.REGISTRY,
                               test_lib.FakeRegistryVFSHandler):
      with test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                 test_lib.FakeFullVFSHandler):
        self._testProcessCollectedArtifacts()

  def _testProcessCollectedArtifacts(self):
    client_mock = action_mocks.ActionMock("TransferBuffer", "StatFile", "Find",
                                          "HashBuffer", "HashFile",
                                          "FingerprintFile", "ListDirectory")

    # Get KB initialized
    for _ in test_lib.TestFlowHelper("KnowledgeBaseInitializationFlow",
                                     client_mock,
                                     client_id=self.client_id,
                                     token=self.token):
      pass

    artifact_list = ["WindowsPersistenceMechanismFiles"]
    with test_lib.Instrument(transfer.MultiGetFile,
                             "Start") as getfile_instrument:
      for _ in test_lib.TestFlowHelper("ArtifactCollectorFlow",
                                       client_mock,
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
    with test_lib.Instrument(transfer.MultiGetFile,
                             "Start") as getfile_instrument:
      for _ in test_lib.TestFlowHelper("ArtifactCollectorFlow",
                                       client_mock,
                                       artifact_list=artifact_list,
                                       token=self.token,
                                       client_id=self.client_id,
                                       output="analysis/{p}/{u}-{t}",
                                       split_output_by_artifact=True):
        pass

      self.assertFalse(getfile_instrument.args)


class TestArtifactCollectorsRealArtifacts(CollectorTest):
  """Test the collection of real artifacts."""

  def setUp(self):
    """Add test artifacts to existing registry."""
    super(TestArtifactCollectorsRealArtifacts, self).setUp()
    self.SetupClients(1, system="Windows", os_version="6.2")

  def _CheckDriveAndRoot(self):
    client_mock = action_mocks.ActionMock("StatFile", "ListDirectory")

    for _ in test_lib.TestFlowHelper("ArtifactCollectorFlow",
                                     client_mock,
                                     artifact_list=[
                                         "SystemDriveEnvironmentVariable"
                                     ],
                                     token=self.token,
                                     client_id=self.client_id,
                                     output="testsystemdrive"):
      pass

    fd = aff4.FACTORY.Open(
        rdfvalue.RDFURN(self.client_id).Add("testsystemdrive"),
        token=self.token)
    self.assertEqual(len(fd), 1)
    self.assertEqual(str(fd[0]), "C:")

    for _ in test_lib.TestFlowHelper("ArtifactCollectorFlow",
                                     client_mock,
                                     artifact_list=["SystemRoot"],
                                     token=self.token,
                                     client_id=self.client_id,
                                     output="testsystemroot"):
      pass

    fd = aff4.FACTORY.Open(
        rdfvalue.RDFURN(self.client_id).Add("testsystemroot"),
        token=self.token)
    self.assertEqual(len(fd), 1)
    # Filesystem gives WINDOWS, registry gives Windows
    self.assertTrue(str(fd[0]) in [r"C:\Windows", r"C:\WINDOWS"])

  def testSystemDriveArtifact(self):
    self.SetupClients(1, system="Windows", os_version="6.2")

    class BrokenClientMock(action_mocks.ActionMock):

      def StatFile(self, _):
        raise IOError

      def ListDirectory(self, _):
        raise IOError

    # No registry, broken filesystem, this should just raise.
    with self.assertRaises(RuntimeError):
      for _ in test_lib.TestFlowHelper("ArtifactCollectorFlow",
                                       BrokenClientMock(),
                                       artifact_list=[
                                           "SystemDriveEnvironmentVariable"
                                       ],
                                       token=self.token,
                                       client_id=self.client_id,
                                       output="testsystemdrive"):
        pass

    # No registry, so this should use the fallback flow
    with test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                               test_lib.ClientVFSHandlerFixture):
      self._CheckDriveAndRoot()

    # Registry is present, so this should use the regular artifact collection
    with test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.REGISTRY,
                               test_lib.FakeRegistryVFSHandler):
      self._CheckDriveAndRoot()

  def testRunWMIComputerSystemProductArtifact(self):

    class WMIActionMock(action_mocks.ActionMock):

      def WmiQuery(self, _):
        return client_fixture.WMI_CMP_SYS_PRD

    client_mock = WMIActionMock()
    for _ in test_lib.TestFlowHelper(
        "ArtifactCollectorFlow",
        client_mock,
        artifact_list=["WMIComputerSystemProduct"],
        token=self.token,
        client_id=self.client_id,
        dependencies=artifact_utils.ArtifactCollectorFlowArgs.Dependency.
        IGNORE_DEPS,
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

    client_mock = WMIActionMock()
    for _ in test_lib.TestFlowHelper(
        "ArtifactCollectorFlow",
        client_mock,
        artifact_list=["WMILogicalDisks"],
        token=self.token,
        client_id=self.client_id,
        dependencies=artifact_utils.ArtifactCollectorFlowArgs.Dependency.
        IGNORE_DEPS,
        store_results_in_aff4=True):
      pass

    # Test that we set the client VOLUMES attribute
    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    volumes = client.Get(client.Schema.VOLUMES)
    self.assertEqual(len(volumes), 2)
    for result in volumes:
      self.assertTrue(isinstance(result, rdf_client.Volume))
      self.assertTrue(result.windowsvolume.drive_letter in ["Z:", "C:"])
      if result.windowsvolume.drive_letter == "C:":
        self.assertAlmostEqual(result.FreeSpacePercent(), 76.142, delta=0.001)
        self.assertEqual(result.Name(), "C:")
      elif result.windowsvolume.drive_letter == "Z:":
        self.assertEqual(result.Name(), "homefileshare$")
        self.assertAlmostEqual(result.FreeSpacePercent(), 58.823, delta=0.001)

  def testWMIBaseObject(self):

    class WMIActionMock(action_mocks.ActionMock):

      base_objects = []

      def WmiQuery(self, args):
        self.base_objects.append(args.base_object)
        return client_fixture.WMI_SAMPLE

    client_mock = WMIActionMock()
    for _ in test_lib.TestFlowHelper(
        "ArtifactCollectorFlow",
        client_mock,
        artifact_list=["WMIActiveScriptEventConsumer"],
        token=self.token,
        client_id=self.client_id,
        dependencies=artifact_utils.ArtifactCollectorFlowArgs.Dependency.
        IGNORE_DEPS):
      pass

    # Make sure the artifact's base_object made it into the WmiQuery call.
    artifact_obj = artifact_registry.REGISTRY.GetArtifact(
        "WMIActiveScriptEventConsumer")
    self.assertItemsEqual(WMIActionMock.base_objects,
                          [artifact_obj.sources[0].attributes["base_object"]])

  def testRetrieveDependencies(self):
    """Test getting an artifact without a KB using retrieve_depdendencies."""
    with test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.REGISTRY,
                               test_lib.FakeRegistryVFSHandler):
      with test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                 test_lib.FakeFullVFSHandler):

        client_mock = action_mocks.ActionMock("TransferBuffer", "StatFile",
                                              "Find", "HashBuffer", "HashFile",
                                              "FingerprintFile",
                                              "ListDirectory")

        artifact_list = ["WinDirEnvironmentVariable"]
        for _ in test_lib.TestFlowHelper(
            "ArtifactCollectorFlow",
            client_mock,
            artifact_list=artifact_list,
            token=self.token,
            client_id=self.client_id,
            dependencies=artifact_utils.ArtifactCollectorFlowArgs.Dependency.
            FETCH_NOW,
            output="testRetrieveDependencies"):
          pass

        output = aff4.FACTORY.Open(
            self.client_id.Add("testRetrieveDependencies"),
            token=self.token)
        self.assertEqual(len(output), 1)
        self.assertEqual(output[0], r"C:\Windows")


class ArtifactFilesDownloaderFlowTest(test_lib.FlowTestsBaseclass):

  def setUp(self):
    super(ArtifactFilesDownloaderFlowTest, self).setUp()

    with aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw") as fd:
      fd.Set(fd.Schema.SYSTEM("Windows"))
      kb = fd.Schema.KNOWLEDGE_BASE()
      artifact.SetCoreGRRKnowledgeBaseValues(kb, fd)
      fd.Set(kb)

    self.output_path = "analysis/artifact_files_downloader"
    self.stubbers = []

    self.collector_replies = []

    def ArtifactCollectorStub(this):
      for r in self.collector_replies:
        this.SendReply(r)

    stubber = utils.Stubber(collectors.ArtifactCollectorFlow, "Start",
                            ArtifactCollectorStub)
    stubber.Start()
    self.stubbers.append(stubber)

    self.start_file_fetch_args = []
    self.received_files = []
    self.failed_files = []

    def StartFileFetch(this, pathspec, request_data=None):
      self.start_file_fetch_args.append(pathspec)

      for r in self.received_files:
        this.ReceiveFetchedFile(r, None, request_data=request_data)

      for r in self.failed_files:
        this.FileFetchFailed(pathspec, "StatFile", request_data=request_data)

    stubber = utils.Stubber(transfer.MultiGetFileMixin, "StartFileFetch",
                            StartFileFetch)
    stubber.Start()
    self.stubbers.append(stubber)

  def tearDown(self):
    super(ArtifactFilesDownloaderFlowTest, self).tearDown()

    for stubber in self.stubbers:
      stubber.Stop()

  def RunFlow(self, artifact_list=None, use_tsk=False):
    if artifact_list is None:
      artifact_list = ["WindowsRunKeys"]

    urn = flow.GRRFlow.StartFlow(flow_name="ArtifactFilesDownloaderFlow",
                                 client_id=self.client_id,
                                 artifact_list=artifact_list,
                                 use_tsk=use_tsk,
                                 output=self.output_path,
                                 token=self.token)
    for _ in test_lib.TestFlowHelper(urn, token=self.token):
      pass

    try:
      results_fd = aff4.FACTORY.Open(
          self.client_id.Add(self.output_path),
          aff4_type=collects.RDFValueCollection,
          token=self.token)
      return list(results_fd)
    except aff4.InstantiationError:
      return []

  def MakeRegistryStatEntry(self, path, value):
    options = rdf_paths.PathSpec.Options.CASE_LITERAL
    pathspec = rdf_paths.PathSpec(path=path,
                                  path_options=options,
                                  pathtype=rdf_paths.PathSpec.PathType.REGISTRY)

    return rdf_client.StatEntry(
        aff4path=self.client_id.Add("registry").Add(path),
        pathspec=pathspec,
        registry_data=rdf_protodict.DataBlob().SetValue(value),
        registry_type=rdf_client.StatEntry.RegistryType.REG_SZ)

  def MakeFileStatEntry(self, path):
    pathspec = rdf_paths.PathSpec(path=path, pathtype="OS")
    return rdf_client.StatEntry(pathspec=pathspec)

  def testDoesNothingIfArtifactCollectorReturnsNothing(self):
    self.RunFlow()
    self.assertFalse(self.start_file_fetch_args)

  def testDoesNotIssueDownloadRequestsIfNoPathIsGuessed(self):
    self.collector_replies = [self.MakeRegistryStatEntry(
        u"HKEY_LOCAL_MACHINE\\SOFTWARE\\foo", u"blah-blah")]
    self.RunFlow()
    self.assertFalse(self.start_file_fetch_args)

  def testJustUsesPathSpecForFileStatEntry(self):
    self.collector_replies = [self.MakeFileStatEntry("C:\\Windows\\bar.exe")]
    self.failed_files = [self.collector_replies[0].pathspec]

    results = self.RunFlow()

    self.assertEquals(len(results), 1)
    self.assertEquals(results[0].found_pathspec,
                      self.collector_replies[0].pathspec)

  def testSendsReplyEvenIfNoPathsAreGuessed(self):
    self.collector_replies = [self.MakeRegistryStatEntry(
        u"HKEY_LOCAL_MACHINE\\SOFTWARE\\foo", u"blah-blah")]

    results = self.RunFlow()

    self.assertEquals(len(results), 1)
    self.assertEquals(results[0].original_result, self.collector_replies[0])
    self.assertFalse(results[0].HasField("found_pathspec"))
    self.assertFalse(results[0].HasField("downloaded_file"))

  def testIncludesGuessedPathspecIfFileFetchFailsIntoReply(self):
    self.collector_replies = [self.MakeRegistryStatEntry(
        u"HKEY_LOCAL_MACHINE\\SOFTWARE\\foo", u"C:\\Windows\\bar.exe")]
    self.failed_files = [rdf_paths.PathSpec(path="C:\\Windows\\bar.exe",
                                            pathtype="OS")]

    results = self.RunFlow()

    self.assertEquals(len(results), 1)
    self.assertEquals(results[0].found_pathspec,
                      rdf_paths.PathSpec(path="C:\\Windows\\bar.exe",
                                         pathtype="OS"))
    self.assertFalse(results[0].HasField("downloaded_file"))

  def testIncludesDownloadedFilesIntoReplyIfFetchSucceeds(self):
    self.collector_replies = [self.MakeRegistryStatEntry(
        u"HKEY_LOCAL_MACHINE\\SOFTWARE\\foo", u"C:\\Windows\\bar.exe")]
    self.received_files = [self.MakeFileStatEntry("C:\\Windows\\bar.exe")]

    results = self.RunFlow()

    self.assertEquals(len(results), 1)
    self.assertEquals(results[0].downloaded_file, self.received_files[0])


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
