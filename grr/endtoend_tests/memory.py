#!/usr/bin/env python
"""End to end tests for lib.flows.general.memory."""

import os

from grr.client.components.rekall_support import rekall_types as rdf_rekall_types
from grr.endtoend_tests import base
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib.aff4_objects import collects
from grr.lib.rdfvalues import client as rdf_client


class TestGrepMemory(base.AutomatedTest):
  """Test ScanMemory."""
  platforms = ["Windows"]
  flow = "ScanMemory"
  test_output_path = "analysis/grep/testing"
  args = {"also_download": False,
          "grep": rdf_client.BareGrepSpec(
              literal="grr",
              length=4 * 1024 * 1024 * 1024,
              mode=rdf_client.GrepSpec.Mode.FIRST_HIT,
              bytes_before=10,
              bytes_after=10),
          "output": test_output_path}

  def CheckFlow(self):
    collection = aff4.FACTORY.Open(
        self.client_id.Add(self.test_output_path),
        token=self.token)
    self.assertIsInstance(collection, collects.RDFValueCollection)
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
    aff4.FACTORY.Delete(
        self.client_id.Add(self.test_output_path),
        token=self.token)
    super(AbstractTestAnalyzeClientMemory, self).setUp()

  def tearDown(self):
    # RDFValueCollections need to be deleted recursively.
    aff4.FACTORY.Delete(
        self.client_id.Add(self.test_output_path),
        token=self.token)
    config_lib.CONFIG.Set("Rekall.profile_server", self.old_config)
    super(AbstractTestAnalyzeClientMemory, self).tearDown()

  def CheckFlow(self):
    self.response = aff4.FACTORY.Open(
        self.client_id.Add(self.test_output_path),
        token=self.token)
    self.assertIsInstance(self.response, collects.RDFValueCollection)
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
    AbstractTestAnalyzeClientMemoryWindows):

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
                                       args=dict(proc_regex=self.binaryname,
                                                 method="PsActiveProcessHead"))
    ]

  def CheckFlow(self):
    super(TestAnalyzeClientMemoryWindowsDLLList, self).CheckFlow()

    # Make sure the dlllist found our process by regex:
    response_str = "".join([x.json_messages for x in self.response])
    self.assertIn(self.binaryname, response_str)


class TestAnalyzeClientMemoryMac(AbstractTestAnalyzeClientMemory,
                                 base.AutomatedTest):
  """Runs Rekall on Macs."""
  platforms = ["Darwin"]

  def setUpRequest(self):
    self.args["request"].plugins = [
        rdf_rekall_types.PluginRequest(plugin="pslist")
    ]

  def CheckFlow(self):
    response = aff4.FACTORY.Open(
        self.client_id.Add(self.test_output_path),
        token=self.token)
    binary_name = config_lib.CONFIG.Get(
        "Client.binary_name",
        context=["Client Context", "Platform:Darwin"])

    responses = list(response)
    self.assertTrue(len(responses))
    self.assertTrue(any([binary_name in response.json_messages
                         for response in list(response)]))


class TestAnalyzeClientMemoryLinux(AbstractTestAnalyzeClientMemory):
  """Runs Rekall on Linux."""
  platforms = ["Linux"]

  def setUpRequest(self):
    self.args["request"].plugins = [
        rdf_rekall_types.PluginRequest(plugin="pslist")
    ]

  def CheckForInit(self):
    responses = aff4.FACTORY.Open(
        self.client_id.Add(self.test_output_path),
        token=self.token)
    self.assertTrue(any(["\"init\"" in r.json_messages for r in responses]))

  def CheckFlow(self):
    self.CheckForInit()


class TestAnalyzeClientMemoryLoggingWorks(AbstractTestAnalyzeClientMemory):
  """Runs pslist with DEBUG logging and checks that we got DEBUG messages."""
  platforms = ["Linux", "Windows", "Darwin"]

  def setUpRequest(self):
    self.args["request"].plugins = [
        rdf_rekall_types.PluginRequest(plugin="pslist")
    ]
    self.args["request"].session["logging_level"] = "DEBUG"

  def CheckFlow(self):
    response = aff4.FACTORY.Open(
        self.client_id.Add(self.test_output_path),
        token=self.token)
    self.assertIn("\"level\":\"DEBUG\"", response[0].json_messages)


class TestAnalyzeClientMemoryNonexistantPlugin(AbstractTestAnalyzeClientMemory):
  """Tests flow failure when a plugin doesn't exist."""
  platforms = ["Linux", "Windows"]

  def setUpRequest(self):
    self.args["request"].plugins = [
        rdf_rekall_types.PluginRequest(plugin="idontexist")
    ]

  def CheckForError(self, flow_state):
    self.assertEqual(flow_state.context.state.name, "ERROR")

  def CheckForInvalidPlugin(self, flow_state):
    self.assertIn("invalid plugin", str(flow_state.context.backtrace).lower())

  def CheckFlow(self):
    flow = self.OpenFlow()
    flow_state = flow.Get(flow.SchemaCls.FLOW_STATE)
    self.CheckForError(flow_state)
    self.CheckForInvalidPlugin(flow_state)


class TestAnalyzeClientMemoryPluginBadParamsFails(
    TestAnalyzeClientMemoryNonexistantPlugin):
  """Tests flow failure when a plugin is given wrong parameters."""

  def setUpRequest(self):
    self.args["request"].plugins = [
        rdf_rekall_types.PluginRequest(plugin="pslist",
                                       args=dict(abcdefg=12345))
    ]

  def CheckForInvalidArgs(self, flow_state):
    self.assertIn("InvalidArgs", flow_state.context.backtrace)

  def CheckFlow(self):
    flow = self.OpenFlow()
    flow_state = flow.Get(flow.SchemaCls.FLOW_STATE)
    # First check that the flow ended up with an error
    self.CheckForError(flow_state)
    self.CheckForInvalidArgs(flow_state)


class TestAnalyzeClientMemoryNonexistantPluginWithExisting(
    TestAnalyzeClientMemoryLinux, TestAnalyzeClientMemoryNonexistantPlugin):
  """Tests flow failure when failing and non failing plugins run together."""

  def setUpRequest(self):
    self.args["request"].plugins = [
        rdf_rekall_types.PluginRequest(plugin="pslist"),
        rdf_rekall_types.PluginRequest(plugin="idontexist")
    ]

  def CheckFlow(self):
    flow = self.OpenFlow()
    flow_state = flow.Get(flow.SchemaCls.FLOW_STATE)
    # idontexist should throw an error and have invalid plugin in the backtrace.
    self.CheckForError(flow_state)
    self.CheckForInvalidPlugin(flow_state)
    # but pslist should still give results.
    self.CheckForInit()


class TestSigScan(AbstractTestAnalyzeClientMemoryWindows):
  """Tests signature scanning on Windows."""

  def setUpRequest(self):
    # This is a signature for the tcpip.sys driver on Windows 7. If you are
    # running a different version, a hit is not guaranteed.
    sig_path = os.path.join(config_lib.CONFIG["Test.end_to_end_data_dir"],
                            "tcpip.sig")

    signature = open(sig_path, "rb").read().strip()
    args = {"scan_kernel": True, "signature": [signature]}
    self.args["request"].plugins = [
        rdf_rekall_types.PluginRequest(plugin="sigscan",
                                       args=args)
    ]

  def CheckFlow(self):
    collection = aff4.FACTORY.Open(
        self.client_id.Add(self.test_output_path),
        token=self.token)
    self.assertIsInstance(collection, collects.RDFValueCollection)
    self.assertTrue(any(["Hit in kernel AS:" in response.json_messages
                         for response in list(collection)]))


class TestYarascanExists(AbstractTestAnalyzeClientMemory):
  """Tests the client has been built with yara."""
  platforms = ["Linux", "Windows", "Darwin"]

  def setUpRequest(self):
    self.args["request"].plugins = [
        rdf_rekall_types.PluginRequest(plugin="yarascan")
    ]

  def CheckForError(self, flow_state):
    # Invoking yarascan without arguments will report an ERROR.
    self.assertEqual(flow_state.context.state.name, "ERROR")

  def CheckForInvalidPlugin(self, flow_state):
    # When a plugin doesn't exist, Rekall raises with an "Invalid plugin"
    self.assertNotIn("invalid plugin",
                     str(flow_state.context.backtrace).lower())
    # Yarascan without arguments will generate a PluginError as it requires
    # arguments.
    self.assertIn("PluginError", flow_state.context.backtrace)

  def CheckFlow(self):
    flow = self.OpenFlow()
    flow_state = flow.Get(flow.SchemaCls.FLOW_STATE)
    self.CheckForError(flow_state)
    self.CheckForInvalidPlugin(flow_state)
