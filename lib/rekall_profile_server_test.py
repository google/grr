#!/usr/bin/env python
"""Tests for the Rekall profile server."""

import urllib2
import zlib

# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import rekall_profile_server
from grr.lib import test_lib
from grr.lib import utils

# pylint: mode=test


class FakeHandle(object):

  read_count = 0

  def __init__(self, url):
    self.url = url

  def read(self):
    FakeHandle.read_count += 1

    if "v1.0" not in self.url:
      return ""

    profile_name = self.url[self.url.find("v1.0"):]

    server = test_lib.TestRekallRepositoryProfileServer()
    profile = server.GetProfileByName(profile_name)

    return profile.data


def FakeOpen(url, timeout=None):  # pylint: disable=invalid-name
  _ = timeout
  return FakeHandle(url)


class ProfileServerTest(test_lib.GRRBaseTest):

  def setUp(self):
    self.server = rekall_profile_server.GRRRekallProfileServer()
    super(ProfileServerTest, self).setUp()

  def testProfileFetching(self):

    profile_name = "v1.0/nt/GUID/F8E2A8B5C9B74BF4A6E4A48F180099942"

    FakeHandle.read_count = 0

    with utils.Stubber(urllib2, "urlopen", FakeOpen):
      profile = self.server.GetProfileByName(profile_name)
      uncompressed = zlib.decompress(profile.data, 16 + zlib.MAX_WBITS)
      self.assertTrue("BusQueryDeviceID" in uncompressed)

    # We issued one http request.
    self.assertEqual(FakeHandle.read_count, 1)

    with utils.Stubber(urllib2, "urlopen", FakeOpen):
      profile = self.server.GetProfileByName(profile_name)

    # This time it should have been cached.
    self.assertEqual(FakeHandle.read_count, 1)

  def testGzExtension(self):
    with utils.Stubber(urllib2, "urlopen", FakeOpen):
      profile = self.server.GetProfileByName("v1.0/pe")
      # We received compressed data.
      zlib.decompress(profile.data, 16 + zlib.MAX_WBITS)

      # We issued one http request.
      self.assertEqual(FakeHandle.read_count, 1)

      self.server.GetProfileByName("v1.0/pe")

      # This time it should have been cached.
      self.assertEqual(FakeHandle.read_count, 1)

      self.server.GetProfileByName("v1.0/pe.gz")

      # This is the same profile.
      self.assertEqual(FakeHandle.read_count, 1)

    cache_urn = rdfvalue.RDFURN(config_lib.CONFIG["Rekall.profile_cache_urn"])
    cache_urn = cache_urn.Add("v1.0")
    cached_items = list(aff4.FACTORY.Open(cache_urn,
                                          token=self.token).ListChildren())

    # We cache the .gz only.
    self.assertEqual(len(cached_items), 1)
    self.assertEqual(cached_items[0].Basename(), "pe.gz")


def main(args):
  test_lib.main(args)

if __name__ == "__main__":
  flags.StartMain(main)
