#!/usr/bin/env python
"""End to end tests for lib.flows.general.memory."""


from grr.endtoend_tests import base
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import rdfvalue


class TestAnalyzeClientMemoryVolatility(base.AutomatedTest):
  """Test AnalyzeClientMemoryVolatility."""
  platforms = ["Windows"]
  flow = "AnalyzeClientMemoryVolatility"
  test_output_path = "analysis/pslist/testing"
  args = {"request": rdfvalue.VolatilityRequest(
      plugins=["pslist"], args={"pslist": {}}),
          "output": test_output_path}

  def CheckFlow(self):
    response = aff4.FACTORY.Open(self.client_id.Add(self.test_output_path),
                                 token=self.token)
    self.assertIsInstance(response, aff4.RDFValueCollection)
    self.assertEqual(len(response), 1)
    result = response[0]
    self.assertEqual(result.error, "")
    self.assertGreater(len(result.sections), 0)

    rows = result.sections[0].table.rows
    self.assertGreater(len(rows), 0)

    expected_name = self.GetGRRBinaryName()
    for values in rows:
      for value in values.values:
        if value.name == "ImageFileName":
          if expected_name == value.svalue:
            return

    self.fail("Process listing does not contain %s." % expected_name)


class TestGrepMemory(base.AutomatedTest):
  """Test ScanMemory."""
  platforms = ["Windows", "Darwin"]
  flow = "ScanMemory"
  test_output_path = "analysis/grep/testing"
  args = {"also_download": False,
          "grep": rdfvalue.BareGrepSpec(
              literal="grr", length=4*1024*1024*1024,
              mode=rdfvalue.GrepSpec.Mode.FIRST_HIT,
              bytes_before=10, bytes_after=10),
          "output": test_output_path,}

  def CheckFlow(self):
    collection = aff4.FACTORY.Open(self.client_id.Add(self.test_output_path),
                                   token=self.token)
    self.assertIsInstance(collection, aff4.RDFValueCollection)
    self.assertEqual(len(list(collection)), 1)
    reference = collection[0]

    self.assertEqual(reference.length, 23)
    self.assertEqual(reference.data[10:10+3], "grr")


class TestAnalyzeClientMemory(base.AutomatedTest):
  """Test AnalyzeClientMemory (Rekall)."""
  platforms = ["Windows"]
  flow = "AnalyzeClientMemory"
  test_output_path = "analysis/memory"
  args = {"request": rdfvalue.RekallRequest(),
          "output": test_output_path}

  def setUp(self):
    # We are running a test but we want to use the real profile server.
    config_lib.CONFIG.Set("Rekall.profile_server", "GRRRekallProfileServer")

    windows_binary_name = config_lib.CONFIG.Get(
        "Client.binary_name", context=["Client context", "Platform:Windows"])

    self.args["request"].plugins = [
        rdfvalue.PluginRequest(plugin="pslist"),
        rdfvalue.PluginRequest(plugin="dlllist",
                               args=dict(
                                   proc_regex=windows_binary_name,
                                   method="PsActiveProcessHead"
                                   )),
        rdfvalue.PluginRequest(plugin="modules"),
        ]

    # RDFValueCollections need to be deleted recursively.
    aff4.FACTORY.Delete(self.client_id.Add(self.test_output_path),
                        token=self.token)
    super(TestAnalyzeClientMemory, self).setUp()

  def tearDown(self):
    # RDFValueCollections need to be deleted recursively.
    aff4.FACTORY.Delete(self.client_id.Add(self.test_output_path),
                        token=self.token)
    super(TestAnalyzeClientMemory, self).tearDown()

  def CheckFlow(self):
    response = aff4.FACTORY.Open(self.client_id.Add(self.test_output_path),
                                 token=self.token)
    self.assertIsInstance(response, aff4.RDFValueCollection)
    self.assertTrue(len(response) >= 1)

    result_str = unicode(response)

    for plugin in ["pslist", "dlllist", "modules"]:
      self.assertTrue("Plugin %s" % plugin in result_str)

    # Make sure the dlllist found our process by regex:
    expected_name = self.GetGRRBinaryName()
    self.assertTrue("%s pid:" % expected_name in result_str)

    # Split into results per plugin, strip the first half line.
    parts = result_str.split("********* Plugin ")[1:]

    self.assertEqual(len(parts), 3)

    for part in parts:
      # There should be some result per plugin.
      self.assertTrue(len(part.split("\n")) > 10)


class TestAnalyzeClientMemoryMac(TestAnalyzeClientMemory):
  platforms = ["Darwin"]
  test_output_path = "analysis/memory"
  args = {"request": rdfvalue.RekallRequest(
      plugins=[rdfvalue.PluginRequest(plugin="pslist")]),
          "output": test_output_path}

  def CheckFlow(self):
    response = aff4.FACTORY.Open(self.client_id.Add(self.test_output_path),
                                 token=self.token)
    binary_name = config_lib.CONFIG.Get(
        "Client.binary_name", context=["Client context", "Platform:Darwin"])

    self.assertTrue(binary_name in str(response))
