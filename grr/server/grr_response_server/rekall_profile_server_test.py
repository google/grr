#!/usr/bin/env python
"""Tests for the Rekall profile server."""

import urllib2
import zlib


from grr import config
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import utils
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import rekall_profile_server
from grr.server.grr_response_server import server_stubs
from grr.test_lib import rekall_test_lib
from grr.test_lib import test_lib

# pylint: mode=test


class FakeHandle(object):

  read_count = 0

  def __init__(self, url):
    # Convert the url back into a profile canonical name.
    profile = url.split(server_stubs.REKALL_PROFILE_REPOSITORY_VERSION + "/")[1]
    profile = profile.split(".")[0]
    self.profile = profile

  def read(self):
    FakeHandle.read_count += 1

    profile_name = self.profile
    server = rekall_test_lib.TestRekallRepositoryProfileServer()
    profile = server.GetProfileByName(
        profile_name, version=server_stubs.REKALL_PROFILE_REPOSITORY_VERSION)

    return profile.data


def FakeOpen(url, timeout=None):  # pylint: disable=invalid-name
  _ = timeout
  return FakeHandle(url)


class ProfileServerTest(test_lib.GRRBaseTest):

  def setUp(self):
    self.server = rekall_profile_server.GRRRekallProfileServer()
    super(ProfileServerTest, self).setUp()

  def testProfileFetching(self):

    profile_name = "nt/GUID/F8E2A8B5C9B74BF4A6E4A48F180099942"

    FakeHandle.read_count = 0

    with utils.Stubber(urllib2, "urlopen", FakeOpen):
      profile = self.server.GetProfileByName(
          profile_name, version=server_stubs.REKALL_PROFILE_REPOSITORY_VERSION)
      uncompressed = zlib.decompress(profile.data, 16 + zlib.MAX_WBITS)
      self.assertTrue("BusQueryDeviceID" in uncompressed)

    # We issued one http request.
    self.assertEqual(FakeHandle.read_count, 1)

    with utils.Stubber(urllib2, "urlopen", FakeOpen):
      profile = self.server.GetProfileByName(
          profile_name, version=server_stubs.REKALL_PROFILE_REPOSITORY_VERSION)

    # This time it should have been cached.
    self.assertEqual(FakeHandle.read_count, 1)

  def testGzExtension(self):
    with utils.Stubber(urllib2, "urlopen", FakeOpen):
      profile = self.server.GetProfileByName("pe")
      # We received compressed data.
      zlib.decompress(profile.data, 16 + zlib.MAX_WBITS)

      # We issued one http request.
      self.assertEqual(FakeHandle.read_count, 1)

      self.server.GetProfileByName("pe")

      # This time it should have been cached.
      self.assertEqual(FakeHandle.read_count, 1)

      self.server.GetProfileByName("pe")

      # This is the same profile.
      self.assertEqual(FakeHandle.read_count, 1)

    cache_urn = rdfvalue.RDFURN(config.CONFIG["Rekall.profile_cache_urn"])
    cached_items = list(
        aff4.FACTORY.Open(
            cache_urn.Add(server_stubs.REKALL_PROFILE_REPOSITORY_VERSION),
            token=self.token).ListChildren())

    # We cache the .gz only.
    self.assertEqual(len(cached_items), 1)
    self.assertEqual(cached_items[0].Basename(), "pe")


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  flags.StartMain(main)
