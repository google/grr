#!/usr/bin/env python
"""A server that retrieves Rekall profiles by name."""

import urllib2

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

  def GetProfileByName(self, profile_name):
    """Retrieves a profile by name."""
    pass


class CachingProfileServer(ProfileServer):
  """A ProfileServer that caches profiles in the AFF4 space."""

  def _GetProfileFromCache(self, profile_name):

    cache_urn = rdfvalue.RDFURN(config_lib.CONFIG["Rekall.profile_cache_urn"])

    try:
      aff4_profile = aff4.FACTORY.Open(
          cache_urn.Add(profile_name), aff4_type="AFF4RekallProfile",
          token=self.token)
      return aff4_profile.Get(aff4_profile.Schema.PROFILE)
    except IOError:
      pass

  def _StoreProfile(self, profile):
    cache_urn = rdfvalue.RDFURN(config_lib.CONFIG["Rekall.profile_cache_urn"])
    aff4_profile = aff4.FACTORY.Create(
        cache_urn.Add(profile.name), "AFF4RekallProfile",
        token=self.token)
    aff4_profile.Set(aff4_profile.Schema.PROFILE(profile))
    aff4_profile.Close()

  def GetProfileByName(self, profile_name, ignore_cache=False):
    """Retrieves a profile by name."""
    if not profile_name.endswith(".gz"):
      profile_name = "%s.gz" % profile_name

    if not ignore_cache:
      profile = self._GetProfileFromCache(profile_name)
      if profile:
        return profile

    profile = super(CachingProfileServer, self).GetProfileByName(profile_name)
    if profile:
      self._StoreProfile(profile)

    return profile


class RekallRepositoryProfileServer(ProfileServer):
  """This server gets the profiles from the official Rekall repository."""

  def GetProfileByName(self, profile_name):
    if not profile_name.endswith(".gz"):
      profile_name = "%s.gz" % profile_name
    try:
      url = "%s/%s" % (config_lib.CONFIG["Rekall.profile_repository"],
                       profile_name)
      handle = urllib2.urlopen(url, timeout=10)

    except urllib2.URLError as e:
      if e.code == 404:
        return None
      raise

    profile_data = handle.read()
    return rdfvalue.RekallProfile(name=profile_name,
                                  data=profile_data)


class GRRRekallProfileServer(CachingProfileServer,
                             RekallRepositoryProfileServer):
  """A caching Rekall profile server."""
