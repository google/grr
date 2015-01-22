#!/usr/bin/env python
"""A server that retrieves Rekall profiles by name."""

import json
import urllib2
import zlib


from rekall import constants

import logging

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib import registry


class ProfileServer(object):

  __metaclass__ = registry.MetaclassRegistry

  def __init__(self):
    self.token = access_control.ACLToken(username="RekallProfileServer",
                                         reason="Implied.")
    self.token.supervisor = True

  def GetProfileByName(self, profile_name,
                       version=constants.PROFILE_REPOSITORY_VERSION):
    """Retrieves a profile by name."""
    pass


class CachingProfileServer(ProfileServer):
  """A ProfileServer that caches profiles in the AFF4 space."""

  def _GetProfileFromCache(self, profile_name,
                           version=constants.PROFILE_REPOSITORY_VERSION):

    cache_urn = rdfvalue.RDFURN(config_lib.CONFIG["Rekall.profile_cache_urn"])

    try:
      aff4_profile = aff4.FACTORY.Open(
          cache_urn.Add(version).Add(profile_name),
          aff4_type="AFF4RekallProfile",
          token=self.token)
      return aff4_profile.Get(aff4_profile.Schema.PROFILE)
    except IOError:
      pass

  def _StoreProfile(self, profile,
                    version=constants.PROFILE_REPOSITORY_VERSION):
    cache_urn = rdfvalue.RDFURN(config_lib.CONFIG["Rekall.profile_cache_urn"])
    aff4_profile = aff4.FACTORY.Create(
        cache_urn.Add(version).Add(profile.name), "AFF4RekallProfile",
        token=self.token)
    aff4_profile.Set(aff4_profile.Schema.PROFILE(profile))
    aff4_profile.Close()

  def GetProfileByName(self, profile_name,
                       version=constants.PROFILE_REPOSITORY_VERSION,
                       ignore_cache=False):
    """Retrieves a profile by name."""
    if not ignore_cache:
      profile = self._GetProfileFromCache(profile_name, version=version)
      if profile:
        return profile

    profile = super(CachingProfileServer, self).GetProfileByName(
        profile_name, version=version)
    if profile:
      self._StoreProfile(profile, version=version)

    return profile


class RekallRepositoryProfileServer(ProfileServer):
  """This server gets the profiles from the official Rekall repository."""

  def GetProfileByName(self, profile_name,
                       version=constants.PROFILE_REPOSITORY_VERSION):
    try:
      url = "%s/%s/%s.gz" % (
          config_lib.CONFIG["Rekall.profile_repository"],
          version, profile_name)
      handle = urllib2.urlopen(url, timeout=10)

    except urllib2.HTTPError as e:
      if e.code == 404:
        logging.info(
            "Got a 404 while downloading Rekall profile %s", url)
        return None
      raise
    except urllib2.URLError as e:
      logging.info(
          "Got an URLError while downloading Rekall profile %s: %s",
          url, e.reason)
      raise

    profile_data = handle.read()
    if profile_data[:3] != "\x1F\x8B\x08":
      raise ValueError("Downloaded file does not look like gzipped data: %s",
                       profile_data[:100])
    return rdfvalue.RekallProfile(name=profile_name,
                                  version=version,
                                  data=profile_data)


class GRRRekallProfileServer(CachingProfileServer,
                             RekallRepositoryProfileServer):
  """A caching Rekall profile server."""

  def GetAllProfiles(self, version=constants.PROFILE_REPOSITORY_VERSION):
    """This function will download all profiles and cache them locally."""

    inv_profile = self.GetProfileByName(
        "inventory", ignore_cache=True, version=version)
    inventory_json = zlib.decompress(inv_profile.data, 16 + zlib.MAX_WBITS)
    inventory = json.loads(inventory_json)

    for profile in inventory["$INVENTORY"].keys():
      logging.info("Getting profile: %s", profile)
      try:
        self.GetProfileByName(profile, ignore_cache=True, version=version)
      except urllib2.URLError as e:
        logging.info("Exception: %s", e)

  def GetMissingProfiles(self, version=constants.PROFILE_REPOSITORY_VERSION):
    """This will download all profiles that are not already cached."""
    inv_profile = self.GetProfileByName(
        "inventory", ignore_cache=True, version=version)
    inventory_json = zlib.decompress(inv_profile.data, 16 + zlib.MAX_WBITS)
    inventory = json.loads(inventory_json)

    cache_urn = rdfvalue.RDFURN(config_lib.CONFIG["Rekall.profile_cache_urn"])
    profile_urns = []
    for profile in inventory["$INVENTORY"]:
      profile_urns.append((profile, cache_urn.Add(version).Add(profile)))

    stats = aff4.FACTORY.Stat(profile_urns)
    profile_infos = {}
    for metadata in stats:
      profile_infos[metadata["urn"]] = metadata["type"][1]

    for profile, profile_urn in sorted(profile_urns):
      if (profile_urn not in profile_infos or
          profile_infos[profile_urn] != u"AFF4RekallProfile"):
        logging.info("Getting missing profile: %s", profile)
        try:
          self.GetProfileByName(
              profile, ignore_cache=True, version=version)
        except urllib2.URLError as e:
          logging.info("Exception: %s", e)
