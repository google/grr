#!/usr/bin/env python
"""Rekall-related testing classes."""

import gzip
import json
import os

from grr import config
from grr_response_client import comms
from grr_response_client.client_actions import tempfiles
from grr_response_client.components.rekall_support import grr_rekall
from grr.lib import utils
from grr.lib.rdfvalues import rekall_types as rdf_rekall_types
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import rekall_profile_server
from grr.server.grr_response_server.aff4_objects import aff4_grr
from grr.server.grr_response_server.flows.general import memory
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class RekallTestBase(test_lib.GRRBaseTest):
  """Base class for Rekall-based tests."""

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
    super(RekallTestBase, self).setUp()
    self.client_id = self.SetupClient(0)

    self.get_rekall_profile_stubber = utils.Stubber(
        comms.GRRClientWorker, "GetRekallProfile", self.GetRekallProfile)
    self.get_rekall_profile_stubber.Start()

    self.config_overrider = test_lib.ConfigOverrider({
        "Rekall.profile_server": TestRekallRepositoryProfileServer.__name__
    })
    self.config_overrider.Start()

  def tearDown(self):
    super(RekallTestBase, self).tearDown()
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
        "Client.rekall_profile_cache_path": self.temp_dir,
        "Rekall.enabled": True
    }):
      image_path = os.path.join(self.base_path, "win7_trial_64bit.raw")
      request.device.path = image_path

      self.CreateClient()

      # Allow the real RekallAction to run against the image.
      session_id = flow_test_lib.TestFlowHelper(
          memory.AnalyzeClientMemory.__name__,
          action_mocks.MemoryClientMock(grr_rekall.RekallAction,
                                        tempfiles.DeleteGRRTempFiles),
          token=self.token,
          client_id=self.client_id,
          request=request)

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


class TestRekallRepositoryProfileServer(rekall_profile_server.ProfileServer):
  """This server gets the profiles locally from the test data dir."""

  def __init__(self, *args, **kw):
    super(TestRekallRepositoryProfileServer, self).__init__(*args, **kw)
    self.profiles_served = 0

  def GetProfileByName(self, profile_name, version="v1.0"):
    try:
      profile_data = open(
          os.path.join(config.CONFIG["Test.data_dir"], "profiles", version,
                       profile_name + ".gz"), "rb").read()

      self.profiles_served += 1

      return rdf_rekall_types.RekallProfile(
          name=profile_name, version=version, data=profile_data)
    except IOError:
      return None
