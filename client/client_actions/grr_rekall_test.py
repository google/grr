#!/usr/bin/env python
"""Tests for grr.client.client_actions.grr_rekall."""


import functools
import os
import re

import logging

from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib import test_lib

from grr.lib.flows.general import transfer


class RekallTestSuite(test_lib.EmptyActionTest):
  """A test suite for testing Rekall plugins.

  Note that since the Rekall plugin is a SuspendableAction it is impossible to
  test it in isolation from the AnalyzeClientMemory Flow. The flow is needed to
  load profiles, and allow the client action to proceed. We therefore have flow
  tests here instead of simply a client action test (Most other client actions
  are very simple so it is possible to test them in isolation).
  """

  def setUp(self):
    super(RekallTestSuite, self).setUp()
    self.client_id = self.SetupClients(1)[0]

  def CreateClient(self):
    client = aff4.FACTORY.Create(self.client_id,
                                 "VFSGRRClient", token=self.token)
    client.Set(client.Schema.ARCH("AMD64"))
    client.Set(client.Schema.OS_RELEASE("7"))
    client.Set(client.Schema.SYSTEM("Windows"))
    client.Close()

  def LaunchRekallPlugin(self, request):
    """Launch AnalyzeClientMemory flow and return its output as a string.

    Args:
      request: A RekallRequest() proto.
    """
    # For this test we force the client to write the profile cache in the temp
    # directory. This forces the profiles to always be downloaded from the
    # server (since each test run gets a new temp directory).
    config_lib.CONFIG.Set("Client.rekall_profile_cache_path", self.temp_dir)
    image_path = os.path.join(self.base_path, "win7_trial_64bit.raw")
    self.CreateClient()
    self.CreateSignedDriver()

    class ClientMock(action_mocks.MemoryClientMock):
      """A mock which returns the image as the driver path."""

      def GetMemoryInformation(self, _):
        """Mock out the driver loading code to pass the memory image."""
        reply = rdfvalue.MemoryInformation(
            device=rdfvalue.PathSpec(
                path=image_path,
                pathtype=rdfvalue.PathSpec.PathType.OS))

        reply.runs.Append(offset=0, length=1000000000)

        return [reply]

    # Allow the real RekallAction to run against the image.
    for _ in test_lib.TestFlowHelper(
        "AnalyzeClientMemory",
        ClientMock(
            "RekallAction", "WriteRekallProfile", "DeleteGRRTempFiles"
            ),
        token=self.token, client_id=self.client_id,
        request=request, output="analysis/memory"):
      pass

    # Check that the profiles are also cached locally.
    test_profile_dir = os.path.join(config_lib.CONFIG["Test.data_dir"],
                                    "profiles")
    self.assertEqual(
        os.stat(os.path.join(self.temp_dir, "v1.0/pe.gz")).st_size,
        os.stat(os.path.join(test_profile_dir, "v1.0/pe.gz")).st_size)

    p_name = "v1.0/nt/GUID/F8E2A8B5C9B74BF4A6E4A48F180099942.gz"
    self.assertEqual(
        os.stat(os.path.join(self.temp_dir, p_name)).st_size,
        os.stat(os.path.join(test_profile_dir, p_name)).st_size)


def RequireTestImage(f):
  """Decorator that skips tests if we don't have the memory image."""

  @functools.wraps(f)
  def Decorator(testinstance):
    image_path = os.path.join(testinstance.base_path, "win7_trial_64bit.raw")
    if os.access(image_path, os.R_OK):
      return f(testinstance)
    else:
      return testinstance.skipTest("No win7_trial_64bit.raw memory image,"
                                   "skipping test. Download it here: "
                                   "goo.gl/19AJGl and put it in test_data.")
  return Decorator


class RekallTests(RekallTestSuite):
  """Test some core Rekall modules."""

  @RequireTestImage
  def testRekallModules(self):
    """Tests the end to end Rekall memory analysis."""
    request = rdfvalue.RekallRequest()
    request.plugins = [
        # Only use these methods for listing processes.
        rdfvalue.PluginRequest(
            plugin="pslist", args=dict(
                method=["PsActiveProcessHead", "CSRSS"]
                )),
        rdfvalue.PluginRequest(plugin="modules")]

    self.LaunchRekallPlugin(request)

    # Get the result collection - it should be a RekallResponseCollection.
    fd = aff4.FACTORY.Open(self.client_id.Add("analysis/memory"),
                           token=self.token)

    # Ensure that the client_id is set on each message. This helps us demux
    # messages from different clients, when analyzing the collection from a
    # hunt.
    for x in fd:
      self.assertEqual(x.client_urn, self.client_id)

    # The output is merged and separated by ***.
    module_output = re.split("^[*]{5}.+$", fd.RenderAsText(), flags=re.M)

    # First output pslist.
    output = module_output[1].strip()

    # 34 processes and headers.
    self.assertEqual(len(output.splitlines()), 34)

    # And should include the DumpIt binary.
    self.assertTrue("DumpIt.exe" in output)

    # Next output modules plugin.
    output = module_output[2].strip()

    # 105 modules and headers.
    self.assertEqual(len(output.splitlines()), 105)

    # And should include the DumpIt kernel driver.
    self.assertTrue("DumpIt.sys" in output)

  @RequireTestImage
  def testFileOutput(self):
    """Tests that a file can be written by a plugin and retrieved."""
    request = rdfvalue.RekallRequest()
    request.plugins = [
        # Run procdump to create one file.
        rdfvalue.PluginRequest(
            plugin="procdump", args=dict(pid=2860))]

    with test_lib.Instrument(transfer.MultiGetFile,
                             "StoreStat") as storestat_instrument:
      self.LaunchRekallPlugin(request)
      # Expect one file to be downloaded.
      self.assertEqual(storestat_instrument.call_count, 1)

  @RequireTestImage
  def testParameters(self):
    request = rdfvalue.RekallRequest()
    request.plugins = [
        # Only use these methods for listing processes.
        rdfvalue.PluginRequest(
            plugin="pslist", args=dict(
                pid=[4, 2860],
                method="PsActiveProcessHead"
                )),
        ]

    self.LaunchRekallPlugin(request)

    # Get the result collection - it should be a RekallResponseCollection.
    fd = aff4.FACTORY.Open(self.client_id.Add("analysis/memory"),
                           token=self.token)

    result = fd.RenderAsText().splitlines()[4:]  # Drop the column headers.

    # There should be 2 results back.
    self.assertEqual(len(result), 2)
    self.assertTrue("System" in result[0])
    self.assertTrue("DumpIt.exe" in result[1])

  @RequireTestImage
  def testDLLList(self):
    """Tests that we can run a simple DLLList Action."""
    request = rdfvalue.RekallRequest()
    request.plugins = [
        # Only use these methods for listing processes.
        rdfvalue.PluginRequest(
            plugin="dlllist", args=dict(
                proc_regex="dumpit",
                method="PsActiveProcessHead"
                )),
        ]

    self.LaunchRekallPlugin(request)

    # Get the result collection - it should be a RekallResponseCollection.
    fd = aff4.FACTORY.Open(self.client_id.Add("analysis/memory"),
                           token=self.token)

    # Get the result but drop the column headers.
    result = [x for x in fd.RenderAsText().splitlines() if x.startswith("0x")]

    # There should be 5 results back.
    self.assertEqual(len(result), 5)
    for item, line in zip(
        ["DumpIt", "wow64win", "wow64", "wow64cpu", "ntdll"],
        sorted(result)):
      self.assertTrue(item in line)

  @RequireTestImage
  def DisabledTestAllPlugins(self):
    """Tests that we can run a wide variety of plugins.

    Some of those plugins are very expensive to run so this test is disabled by
    default.
    """

    plugins = [
        "atoms", "atomscan", "build_index", "callbacks", "cc", "cert_vad_scan",
        "certscan", "cmdscan", "consoles", "convert_profile", "desktops",
        "devicetree", "dis", "dlldump", "dlllist", "driverirp", "driverscan",
        "dt", "dtbscan", "dtbscan2", "dump", "dwarfparser", "eifconfig",
        "enetstat", "eventhooks", "fetch_pdb", "filescan", "find_dtb", "gahti",
        "getservicesids", "grep", "guess_guid", "handles", "hivedump", "hives",
        "imagecopy", "imageinfo", "impscan", "info", "json_render", "kdbgscan",
        "kpcr", "l", "ldrmodules", "load_as", "load_plugin", "malfind",
        "memdump", "memmap", "messagehooks", "moddump", "modscan", "modules",
        "mutantscan", "netscan", "netstat", "notebook", "null", "object_tree",
        "object_types", "p", "parse_pdb", "pas2vas", "pedump", "peinfo", "pfn",
        "phys_map", "pool_tracker", "pools", "printkey", "procdump", "procinfo",
        "pslist", "psscan", "pstree", "psxview", "pte", "ptov", "raw2dmp",
        "regdump", "rekal", "sessions", "ssdt", "svcscan", "symlinkscan",
        "thrdscan", "threads", "timers", "tokens", "unloaded_modules",
        "userassist", "userhandles", "users", "vad", "vaddump", "vadinfo",
        "vadtree", "vadwalk", "version_modules", "version_scan", "vmscan",
        "vtop", "windows_stations"]

    output_urn = self.client_id.Add("analysis/memory")
    failed_plugins = []

    for plugin in plugins:
      logging.info("Running plugin: %s", plugin)
      try:
        aff4.FACTORY.Delete(output_urn, token=self.token)

        request = rdfvalue.RekallRequest()
        request.plugins = [
            rdfvalue.PluginRequest(plugin=plugin)
            ]

        self.LaunchRekallPlugin(request)

        # Get the result collection - it should be a RekallResponseCollection.
        fd = aff4.FACTORY.Open(output_urn, token=self.token)
        # Try to render the result.
        fd.RenderAsText()
      except Exception:  # pylint: disable=broad-except
        failed_plugins.append(plugin)
        logging.error("Plugin %s failed.", plugin)
    if failed_plugins:
      self.fail("Some plugins failed: %s" % failed_plugins)
