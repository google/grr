#!/usr/bin/env python
"""End to end tests for lib.flows.general.memory."""

import os

from grr import config
from grr.client.components.rekall_support import rekall_types as rdf_rekall_types
from grr.endtoend_tests import base
from grr.server import aff4
from grr.server.flows.general import memory


class AbstractTestAnalyzeClientMemory(base.ClientTestBase):
  """Test AnalyzeClientMemory (Rekall).

  We use the rekall caching profile server for these tests, since we may not
  have direct internet access. It may be necessary to manually populate the
  cache with lib.rekall_profile_server.GRRRekallProfileServer.GetMissingProfiles
  on the console to make these tests pass.
  """
  flow = memory.AnalyzeClientMemory.__name__
  args = {"request": rdf_rekall_types.RekallRequest()}

  def setUpRequest(self):
    raise NotImplementedError("Implemented by subclasses")

  def setUp(self):
    self.setUpRequest()

    self.old_config = config.CONFIG.Get("Rekall.profile_server")
    if "Test Context" in config.CONFIG.context:
      # We're running in a test context, where the rekall repository server is
      # set to TestRekallRepositoryProfileServer, which won't actually work for
      # an end to end test. We change it temporarily to allow the test to pass.
      config.CONFIG.Set("Rekall.profile_server", "GRRRekallProfileServer")

    super(AbstractTestAnalyzeClientMemory, self).setUp()

  def runTest(self):
    if not config.CONFIG["Rekall.enabled"]:
      return self.skipTest(
          "Rekall disabled. Set 'Rekall.enabled=True' in your config to enable")
    else:
      super(AbstractTestAnalyzeClientMemory, self).runTest()

  def tearDown(self):
    if "Test Context" in config.CONFIG.context:
      config.CONFIG.Set("Rekall.profile_server", self.old_config)
    super(AbstractTestAnalyzeClientMemory, self).tearDown()

  def CheckFlow(self):
    self.responses = self.CheckResultCollectionNotEmptyWithRetry(
        self.session_id)

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
        rdf_rekall_types.PluginRequest(
            plugin="dlllist",
            args=dict(proc_regex=self.binaryname, method="PsActiveProcessHead"))
    ]

  def CheckFlow(self):
    super(TestAnalyzeClientMemoryWindowsDLLList, self).CheckFlow()

    # Make sure the dlllist found our process by regex:
    response_str = "".join([x.json_messages for x in self.responses])
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
    super(TestAnalyzeClientMemoryMac, self).CheckFlow()
    binary_name = config.CONFIG.Get(
        "Client.binary_name", context=["Client Context", "Platform:Darwin"])
    self.assertTrue(
        any([
            binary_name in response.json_messages for response in self.responses
        ]))


class TestAnalyzeClientMemoryLinux(AbstractTestAnalyzeClientMemory):
  """Runs Rekall on Linux."""
  platforms = ["Linux"]

  def setUpRequest(self):
    self.args["request"].plugins = [
        rdf_rekall_types.PluginRequest(plugin="pslist")
    ]

  def CheckForInit(self):
    super(TestAnalyzeClientMemoryLinux, self).CheckFlow()
    self.assertTrue(
        any(["\"init\"" in r.json_messages for r in self.responses]))

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
    super(TestAnalyzeClientMemoryLoggingWorks, self).CheckFlow()
    self.assertIn("\"level\":\"DEBUG\"", self.responses[0].json_messages)


class TestAnalyzeClientMemoryNonexistantPlugin(AbstractTestAnalyzeClientMemory):
  """Tests flow failure when a plugin doesn't exist."""
  platforms = ["Linux", "Windows"]

  def setUpRequest(self):
    self.args["request"].plugins = [
        rdf_rekall_types.PluginRequest(plugin="idontexist")
    ]

  def CheckForError(self, flow_obj):
    self.assertEqual(flow_obj.context.state, "ERROR")

  def CheckForInvalidPlugin(self, flow_obj):
    self.assertIn("invalid plugin", str(flow_obj.context.backtrace).lower())

  def CheckFlow(self):
    flow = self.OpenFlow()
    self.CheckForError(flow)
    self.CheckForInvalidPlugin(flow)


class TestAnalyzeClientMemoryPluginBadParamsFails(
    TestAnalyzeClientMemoryNonexistantPlugin):
  """Tests flow failure when a plugin is given wrong parameters."""

  def setUpRequest(self):
    self.args["request"].plugins = [
        rdf_rekall_types.PluginRequest(
            plugin="pslist", args=dict(abcdefg=12345))
    ]

  def CheckForInvalidArgs(self, flow_obj):
    self.assertIn("InvalidArgs", flow_obj.context.backtrace)

  def CheckFlow(self):
    flow = self.OpenFlow()
    # First check that the flow ended up with an error
    self.CheckForError(flow)
    self.CheckForInvalidArgs(flow)


class TestAnalyzeClientMemoryNonexistantPluginWithExisting(
    TestAnalyzeClientMemoryLinux, TestAnalyzeClientMemoryNonexistantPlugin):
  """Tests flow failure when failing and non failing plugins run together."""

  def setUpRequest(self):
    self.args["request"].plugins = [
        rdf_rekall_types.PluginRequest(plugin="pslist"),
        rdf_rekall_types.PluginRequest(plugin="idontexist")
    ]

  def CheckFlow(self):
    super(TestAnalyzeClientMemoryNonexistantPlugin, self).CheckFlow()
    flow = self.OpenFlow()
    # idontexist should throw an error and have invalid plugin in the backtrace.
    self.CheckForError(flow)
    self.CheckForInvalidPlugin(flow)
    # but pslist should still give results.
    self.CheckForInit()


class TestSigScan(AbstractTestAnalyzeClientMemoryWindows):
  """Tests signature scanning on Windows."""

  def setUpRequest(self):
    # This is a signature for the tcpip.sys driver on Windows 7. If you are
    # running a different version, a hit is not guaranteed.
    sig_path = os.path.join(config.CONFIG["Test.end_to_end_data_dir"],
                            "tcpip.sig")

    signature = open(sig_path, "rb").read().strip()
    args = {"scan_kernel": True, "signature": [signature]}
    self.args["request"].plugins = [
        rdf_rekall_types.PluginRequest(plugin="sigscan", args=args)
    ]

  def CheckFlow(self):
    super(TestSigScan, self).CheckFlow()
    self.assertTrue(
        any([
            "Hit in kernel AS:" in response.json_messages
            for response in self.responses
        ]))


class TestYarascanExists(AbstractTestAnalyzeClientMemory):
  """Tests the client has been built with yara."""
  platforms = ["Linux", "Windows", "Darwin"]

  def setUpRequest(self):
    self.args["request"].plugins = [
        rdf_rekall_types.PluginRequest(plugin="yarascan")
    ]

  def CheckForError(self, flow_obj):
    # Invoking yarascan without arguments will report an ERROR.
    self.assertEqual(flow_obj.context.state, "ERROR")

  def CheckForInvalidPlugin(self, flow_obj):
    # When a plugin doesn't exist, Rekall raises with an "Invalid plugin"
    self.assertNotIn("invalid plugin", str(flow_obj.context.backtrace).lower())
    # Yarascan without arguments will generate a PluginError as it requires
    # arguments.
    self.assertIn("PluginError", flow_obj.context.backtrace)

  def CheckFlow(self):
    flow = self.OpenFlow()
    self.CheckForError(flow)
    self.CheckForInvalidPlugin(flow)
