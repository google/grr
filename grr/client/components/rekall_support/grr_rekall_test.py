#!/usr/bin/env python
"""Tests for grr.client.client_actions.grr_rekall."""



import functools
import gzip
import json
import os

from grr import config
from grr.client import comms
from grr.client.client_actions import tempfiles
from grr.client.components.rekall_support import grr_rekall
from grr.client.components.rekall_support import rekall_types as rdf_rekall_types

from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import flags
from grr.lib import flow
from grr.lib import utils
from grr.lib.aff4_objects import aff4_grr
from grr.lib.flows.general import memory
from grr.lib.flows.general import transfer

from grr.test_lib import client_test_lib

from grr.test_lib import flow_test_lib
from grr.test_lib import rekall_test_lib

from grr.test_lib import test_lib


class RekallTestSuite(client_test_lib.EmptyActionTest):
  """A test suite for testing Rekall plugins."""

  def GetRekallProfile(self, name, version=None):
    profile_path = os.path.join(config.CONFIG["Test.data_dir"], "profiles",
                                version, "%s.gz" % name)
    try:
      fd = open(profile_path, "r")
    except IOError:
      return
    return rdf_rekall_types.RekallProfile(
        name=name, version=version, data=fd.read(), compression="GZIP")

  def setUp(self):
    super(RekallTestSuite, self).setUp()
    self.client_id = self.SetupClients(1)[0]

    self.get_rekall_profile_stubber = utils.Stubber(
        comms.GRRClientWorker, "GetRekallProfile", self.GetRekallProfile)
    self.get_rekall_profile_stubber.Start()

    self.config_overrider = test_lib.ConfigOverrider({
        "Rekall.enabled":
            True,
        "Rekall.profile_server":
            rekall_test_lib.TestRekallRepositoryProfileServer.__name__
    })
    self.config_overrider.Start()

  def tearDown(self):
    super(RekallTestSuite, self).tearDown()
    self.get_rekall_profile_stubber.Stop()
    self.config_overrider.Stop()

  def CreateClient(self):
    client = aff4.FACTORY.Create(
        self.client_id, aff4_grr.VFSGRRClient, token=self.token)
    client.Set(client.Schema.ARCH("AMD64"))
    client.Set(client.Schema.OS_RELEASE("7"))
    client.Set(client.Schema.SYSTEM("Windows"))
    client.Close()

  def LaunchRekallPlugin(self, request):
    """Launch AnalyzeClientMemory flow and return its output as a string.

    Args:
      request: A RekallRequest() proto.

    Returns:
      The session_id of the AnalyzeClientMemory flow.
    """
    # For this test we force the client to write the profile cache in the temp
    # directory. This forces the profiles to always be downloaded from the
    # server (since each test run gets a new temp directory).
    with test_lib.ConfigOverrider({
        "Client.rekall_profile_cache_path": self.temp_dir
    }):
      image_path = os.path.join(self.base_path, "win7_trial_64bit.raw")
      request.device.path = image_path

      self.CreateClient()

      # Allow the real RekallAction to run against the image.
      for s in flow_test_lib.TestFlowHelper(
          memory.AnalyzeClientMemory.__name__,
          action_mocks.MemoryClientMock(grr_rekall.RekallAction,
                                        tempfiles.DeleteGRRTempFiles),
          token=self.token,
          client_id=self.client_id,
          request=request):
        session_id = s

      # Check that the profiles are also cached locally.
      test_profile_dir = os.path.join(config.CONFIG["Test.data_dir"],
                                      "profiles")
      self.assertEqual(
          json.load(gzip.open(os.path.join(self.temp_dir, "v1.0/pe.gz"))),
          json.load(gzip.open(os.path.join(test_profile_dir, "v1.0/pe.gz"))))

      p_name = "v1.0/nt/GUID/F8E2A8B5C9B74BF4A6E4A48F180099942.gz"
      self.assertEqual(
          json.load(gzip.open(os.path.join(self.temp_dir, p_name))),
          json.load(gzip.open(os.path.join(test_profile_dir, p_name))))

    return session_id


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
    request = rdf_rekall_types.RekallRequest()
    request.plugins = [
        # Only use these methods for listing processes.
        rdf_rekall_types.PluginRequest(
            plugin="pslist", args=dict(method=["PsActiveProcessHead",
                                               "CSRSS"])),
        rdf_rekall_types.PluginRequest(plugin="modules")
    ]
    session_id = self.LaunchRekallPlugin(request)

    # Get the result collection.
    fd = flow.GRRFlow.ResultCollectionForFID(session_id, token=self.token)

    # Ensure that the client_id is set on each message. This helps us demux
    # messages from different clients, when analyzing the collection from a
    # hunt.
    json_blobs = []
    for x in fd:
      self.assertEqual(x.client_urn, self.client_id)
      json_blobs.append(x.json_messages)

    json_blobs = "".join(json_blobs)

    for knownresult in ["DumpIt.exe", "DumpIt.sys"]:
      self.assertTrue(knownresult in json_blobs)

  @RequireTestImage
  def testFileOutput(self):
    """Tests that a file can be written by a plugin and retrieved."""
    request = rdf_rekall_types.RekallRequest()
    request.plugins = [
        # Run procdump to create one file.
        rdf_rekall_types.PluginRequest(
            plugin="procdump", args=dict(pids=[2860]))
    ]

    with test_lib.Instrument(transfer.MultiGetFile,
                             "StoreStat") as storestat_instrument:
      self.LaunchRekallPlugin(request)
      # Expect one file to be downloaded.
      self.assertEqual(storestat_instrument.call_count, 1)

  @RequireTestImage
  def testParameters(self):
    request = rdf_rekall_types.RekallRequest()
    request.plugins = [
        # Only use these methods for listing processes.
        rdf_rekall_types.PluginRequest(
            plugin="pslist",
            args=dict(pids=[4, 2860], method="PsActiveProcessHead")),
    ]

    session_id = self.LaunchRekallPlugin(request)

    # Get the result collection.
    fd = flow.GRRFlow.ResultCollectionForFID(session_id, token=self.token)

    json_blobs = [x.json_messages for x in fd]
    json_blobs = "".join(json_blobs)

    for knownresult in ["System", "DumpIt.exe"]:
      self.assertTrue(knownresult in json_blobs)

  @RequireTestImage
  def testDLLList(self):
    """Tests that we can run a simple DLLList Action."""
    request = rdf_rekall_types.RekallRequest()
    request.plugins = [
        # Only use these methods for listing processes.
        rdf_rekall_types.PluginRequest(
            plugin="dlllist",
            args=dict(proc_regex="dumpit", method="PsActiveProcessHead")),
    ]

    session_id = self.LaunchRekallPlugin(request)

    # Get the result collection.
    fd = flow.GRRFlow.ResultCollectionForFID(session_id, token=self.token)

    json_blobs = [x.json_messages for x in fd]
    json_blobs = "".join(json_blobs)

    for knownresult in ["DumpIt", "wow64win", "wow64", "wow64cpu", "ntdll"]:
      self.assertTrue(knownresult in json_blobs)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
