#!/usr/bin/env python
"""End to end tests for lib.flows.general.memory."""


from grr.endtoend_tests import base
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import rekall_types as rdf_rekall_types


class TestGrepMemory(base.AutomatedTest):
  """Test ScanMemory."""
  platforms = ["Windows", "Darwin"]
  flow = "ScanMemory"
  test_output_path = "analysis/grep/testing"
  args = {"also_download": False,
          "grep": rdf_client.BareGrepSpec(
              literal="grr", length=4 * 1024 * 1024 * 1024,
              mode=rdf_client.GrepSpec.Mode.FIRST_HIT,
              bytes_before=10, bytes_after=10),
          "output": test_output_path}

  def CheckFlow(self):
    collection = aff4.FACTORY.Open(self.client_id.Add(self.test_output_path),
                                   token=self.token)
    self.assertIsInstance(collection, aff4.RDFValueCollection)
    self.assertEqual(len(list(collection)), 1)
    reference = collection[0]

    self.assertEqual(reference.length, 23)
    self.assertEqual(reference.data[10:10 + 3], "grr")


class AbstractTestAnalyzeClientMemory(base.ClientTestBase):
  """Test AnalyzeClientMemory (Rekall).

  We use the rekall caching profile server for these tests, since we may not
  have direct internet access. It may be necessary to manually populate the
  cache with lib.rekall_profile_server.GRRRekallProfileServer.GetMissingProfiles
  on the console to make these tests pass.
  """
  flow = "AnalyzeClientMemory"
  test_output_path = "analysis/memory"
  args = {"request": rdf_rekall_types.RekallRequest(),
          "output": test_output_path}

  def setUpRequest(self):
    raise NotImplementedError("Implemented by subclasses")

  def setUp(self):
    self.setUpRequest()

    self.old_config = config_lib.CONFIG.Get("Rekall.profile_server")
    if "Test Context" in config_lib.CONFIG.context:
      # We're running in a test context, where the rekall repository server is
      # set to TestRekallRepositoryProfileServer, which won't actually work for
      # an end to end test. We change it temporarily to allow the test to pass.
      config_lib.CONFIG.Set("Rekall.profile_server", "GRRRekallProfileServer")

    # RDFValueCollections need to be deleted recursively.
    aff4.FACTORY.Delete(self.client_id.Add(self.test_output_path),
                        token=self.token)
    super(AbstractTestAnalyzeClientMemory, self).setUp()

  def tearDown(self):
    # RDFValueCollections need to be deleted recursively.
    aff4.FACTORY.Delete(self.client_id.Add(self.test_output_path),
                        token=self.token)
    config_lib.CONFIG.Set("Rekall.profile_server", self.old_config)
    super(AbstractTestAnalyzeClientMemory, self).tearDown()

  def CheckFlow(self):
    self.response = aff4.FACTORY.Open(self.client_id.Add(self.test_output_path),
                                      token=self.token)
    self.assertIsInstance(self.response, aff4.RDFValueCollection)
    self.assertTrue(len(self.response) >= 1)

  def OpenFlow(self):
    """Returns the flow used on this test."""
    return aff4.FACTORY.Open(str(self.session_id), token=self.token)


class AbstractTestAnalyzeClientMemoryWindows(AbstractTestAnalyzeClientMemory,
                                             base.AutomatedTest):
  platforms = ["Windows"]


class TestAnalyzeClientMemoryWindowsPSList(
    AbstractTestAnalyzeClientMemoryWindows):

  def setUpRequest(self):
    self.args["request"].plugins = [
        rdf_rekall_types.PluginRequest(plugin="pslist")
    ]


class TestAnalyzeClientMemoryWindowsModules(
    AbstractTestAnalyzeClientMemoryWindows
):

  def setUpRequest(self):
    self.args["request"].plugins = [
        rdf_rekall_types.PluginRequest(plugin="modules")
    ]


class TestAnalyzeClientMemoryWindowsDLLList(
    AbstractTestAnalyzeClientMemoryWindows):
  """Run rekall DLL list and look for the GRR process."""

  def setUpRequest(self):
    self.binaryname = "svchost.exe"

    self.args["request"].plugins = [
        rdf_rekall_types.PluginRequest(plugin="dlllist",
                                       args=dict(
                                           proc_regex=self.binaryname,
                                           method="PsActiveProcessHead"
                                       ))
    ]

  def CheckFlow(self):
    super(TestAnalyzeClientMemoryWindowsDLLList, self).CheckFlow()

    # Make sure the dlllist found our process by regex:
    response_str = "".join([unicode(x) for x in self.response])
    self.assertIn(self.binaryname, response_str)


class TestAnalyzeClientMemoryMac(AbstractTestAnalyzeClientMemory):
  """Runs Rekall on Macs.

  This test has been disabled for automated testing since OS X memory analysis
  isn't reliable with Yosemite yet.
  """
  platforms = ["Darwin"]

  def setUpRequest(self):
    self.args["request"].plugins = [
        rdf_rekall_types.PluginRequest(plugin="pslist")]

  def CheckFlow(self):
    response = aff4.FACTORY.Open(self.client_id.Add(self.test_output_path),
                                 token=self.token)
    binary_name = config_lib.CONFIG.Get(
        "Client.binary_name", context=["Client context", "Platform:Darwin"])

    self.assertTrue(binary_name in str(response))


class TestAnalyzeClientMemoryLinux(AbstractTestAnalyzeClientMemory):
  """Runs Rekall on Linux."""
  platforms = ["Linux"]

  def setUpRequest(self):
    self.args["request"].plugins = [
        rdf_rekall_types.PluginRequest(plugin="pslist")]

  def CheckFlow(self):
    response = aff4.FACTORY.Open(self.client_id.Add(self.test_output_path),
                                 token=self.token)
    self.assertTrue('"init"' in str(response[0]))


class TestAnalyzeClientMemoryLoggingWorks(AbstractTestAnalyzeClientMemory):
  """Runs pslist with DEBUG logging and checks that we got DEBUG messages."""
  platforms = ["Linux", "Windows", "Darwin"]

  def setUpRequest(self):
    self.args["request"].plugins = [
        rdf_rekall_types.PluginRequest(plugin="pslist")]
    self.args["request"].session["logging_level"] = "DEBUG"

  def CheckFlow(self):
    response = aff4.FACTORY.Open(self.client_id.Add(self.test_output_path),
                                 token=self.token)
    self.assertTrue('"level":"DEBUG"' in response[0].json_messages)


class TestAnalyzeClientMemoryNonexistantPlugin(AbstractTestAnalyzeClientMemory):
  """Tests flow failure when a plugin doesn't exist."""
  platforms = ["Linux", "Windows"]

  def setUpRequest(self):
    self.args["request"].plugins = [
        rdf_rekall_types.PluginRequest(plugin="idontexist")]

  def CheckFlow(self):
    flow = self.OpenFlow()
    flow_state = flow.Get(flow.SchemaCls.FLOW_STATE)
    self.assertTrue(flow_state.context.state.name == "ERROR")


class TestAnalyzeClientMemoryPluginBadParamsFails(
    TestAnalyzeClientMemoryNonexistantPlugin):
  """Tests flow failure when a plugin is given wrong parameters."""

  def setUpRequest(self):
    self.args["request"].plugins = [
        rdf_rekall_types.PluginRequest(plugin="pslist",
                                       args=dict(abcdefg=12345))]

  def CheckFlow(self):
    # First check that the flow ended up with an error
    super(TestAnalyzeClientMemoryPluginBadParamsFails, self).CheckFlow()
    flow = self.OpenFlow()
    flow_state = flow.Get(flow.SchemaCls.FLOW_STATE)
    self.assertTrue("InvalidArgs" in flow_state.context.backtrace)


class TestAnalyzeClientMemoryNonexistantPluginWithExisting(
    TestAnalyzeClientMemoryNonexistantPlugin):
  """Tests flow failure when failing and non failing plugins run together."""

  def setUpRequest(self):
    self.args["request"].plugins = [
        rdf_rekall_types.PluginRequest(plugin="pslist"),
        rdf_rekall_types.PluginRequest(plugin="idontexist")]
