#!/usr/bin/env python
"""Test the collector flows.

To reduce the size of this module, additional collector flow tests are split out
into collectors_*_test.py files.
"""


import os

import mock
import psutil

from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import artifact
from grr.lib import artifact_registry
from grr.lib import artifact_utils
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.aff4_objects import collects
# pylint: disable=unused-import
from grr.lib.flows.general import artifact_fallbacks
from grr.lib.flows.general import collectors
# pylint: enable=unused-import
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths


def ProcessIter():
  return iter([test_lib.MockWindowsProcess()])


class TestArtifactCollectors(test_lib.FlowTestsBaseclass):
  """Test the artifact collection mechanism with fake artifacts."""

  def setUp(self):
    """Make sure things are initialized."""
    super(TestArtifactCollectors, self).setUp()
    test_artifacts_file = os.path.join(config_lib.CONFIG["Test.data_dir"],
                                       "artifacts", "test_artifacts.json")
    artifact_registry.REGISTRY.AddFileSource(test_artifacts_file)

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
    with utils.Stubber(psutil, "process_iter", ProcessIter):
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
      self.assertTrue(len(fd) == 1)

  def testRunGrrClientActionArtifactSplit(self):
    """Test that artifacts get split into separate collections."""
    with utils.Stubber(psutil, "process_iter", ProcessIter):
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
      self.assertEqual(len(fd), 1)

      fd = aff4.FACTORY.Open(
          rdfvalue.RDFURN(self.client_id).Add("test_artifact_FakeArtifact2"),
          token=self.token)
      self.assertEqual(len(fd), 1)
      self.assertTrue(isinstance(list(fd)[0], rdf_client.Process))

  def testConditions(self):
    """Test we can get a GRR client artifact with conditions."""
    with utils.Stubber(psutil, "process_iter", ProcessIter):
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
    with utils.Stubber(psutil, "process_iter", ProcessIter):
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


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
