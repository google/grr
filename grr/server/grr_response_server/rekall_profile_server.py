#!/usr/bin/env python
"""A server that retrieves Rekall profiles by name."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import json
import logging
import zlib


from future.moves.urllib import error as urlerror
from future.moves.urllib import request as urlrequest
from future.utils import with_metaclass

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib.rdfvalues import rekall_types as rdf_rekall_types
from grr_response_server import access_control
from grr_response_server import aff4
from grr_response_server import server_stubs
from grr_response_server import threadpool
from grr_response_server.aff4_objects import aff4_grr


class ProfileServer(with_metaclass(registry.MetaclassRegistry, object)):
  """A base class for profile servers."""

  def __init__(self):
    self.token = access_control.ACLToken(
        username="RekallProfileServer", reason="Implied.")
    self.token.supervisor = True

  def GetProfileByName(self,
                       profile_name,
                       version=server_stubs.REKALL_PROFILE_REPOSITORY_VERSION):
    """Retrieves a profile by name."""
    pass


class CachingProfileServer(ProfileServer):
  """A ProfileServer that caches profiles in the AFF4 space."""

  def _GetProfileFromCache(
      self,
      profile_name,
      version=server_stubs.REKALL_PROFILE_REPOSITORY_VERSION):

    cache_urn = rdfvalue.RDFURN(config.CONFIG["Rekall.profile_cache_urn"])

    try:
      aff4_profile = aff4.FACTORY.Open(
          cache_urn.Add(version).Add(profile_name),
          aff4_type=aff4_grr.AFF4RekallProfile,
          token=self.token)
      return aff4_profile.Get(aff4_profile.Schema.PROFILE)
    except IOError:
      pass

  def _StoreProfile(self,
                    profile,
                    version=server_stubs.REKALL_PROFILE_REPOSITORY_VERSION):
    cache_urn = rdfvalue.RDFURN(config.CONFIG["Rekall.profile_cache_urn"])
    aff4_profile = aff4.FACTORY.Create(
        cache_urn.Add(version).Add(profile.name),
        aff4_grr.AFF4RekallProfile,
        token=self.token)
    aff4_profile.Set(aff4_profile.Schema.PROFILE(profile))
    aff4_profile.Close()

  def GetProfileByName(self,
                       profile_name,
                       version=server_stubs.REKALL_PROFILE_REPOSITORY_VERSION,
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

  def GetProfileByName(self,
                       profile_name,
                       version=server_stubs.REKALL_PROFILE_REPOSITORY_VERSION):
    try:
      url = "%s/%s/%s.gz" % (config.CONFIG["Rekall.profile_repository"],
                             version, profile_name)
      handle = urlrequest.urlopen(url, timeout=10)
      profile_data = handle.read()
      if profile_data[:3] != b"\x1F\x8B\x08":
        raise ValueError("Downloaded file does not look like gzipped data: %s" %
                         profile_data[:100])
      compression = "GZIP"
    except urlerror.HTTPError as e:
      if e.code == 404:
        # Try to download without the .gz
        handle = urlrequest.urlopen(url[:-3], timeout=10)
        profile_data = handle.read()
        compression = "NONE"
      else:
        raise
    except urlerror.URLError as e:
      logging.info("Got an URLError while downloading Rekall profile %s: %s",
                   url, e.reason)
      raise

    return rdf_rekall_types.RekallProfile(
        name=profile_name,
        version=version,
        compression=compression,
        data=profile_data)


class GRRRekallProfileServer(CachingProfileServer,
                             RekallRepositoryProfileServer):
  """A caching Rekall profile server."""

  def GetAllProfiles(self,
                     version=server_stubs.REKALL_PROFILE_REPOSITORY_VERSION):
    """This function will download all profiles and cache them locally."""

    inv_profile = self.GetProfileByName(
        "inventory", ignore_cache=True, version=version)
    inventory_json = zlib.decompress(inv_profile.data, 16 + zlib.MAX_WBITS)
    inventory = json.loads(inventory_json)

    for profile in inventory["$INVENTORY"]:
      logging.info("Getting profile: %s", profile)
      try:
        self.GetProfileByName(profile, ignore_cache=True, version=version)
      except urlerror.URLError as e:
        logging.info("Exception: %s", e)

  def GetMissingProfiles(
      self, version=server_stubs.REKALL_PROFILE_REPOSITORY_VERSION):
    """This will download all profiles that are not already cached."""
    inv_profile = self.GetProfileByName(
        "inventory", ignore_cache=True, version=version)
    inventory_json = zlib.decompress(inv_profile.data, 16 + zlib.MAX_WBITS)
    inventory = json.loads(inventory_json)

    # Build a mapping between urns and profile names.
    cache_urn = rdfvalue.RDFURN(config.CONFIG["Rekall.profile_cache_urn"])
    profile_to_urn = {}
    urn_to_profile = {}
    for profile in inventory["$INVENTORY"]:
      profile_urn = cache_urn.Add(version).Add(profile)
      profile_to_urn[profile] = profile_urn
      urn_to_profile[profile_urn] = profile

    # Start off getting everything.
    profiles_to_get = set(urn_to_profile)

    for metadata in aff4.FACTORY.Stat(urn_to_profile):
      timestamp = metadata["type"][-1]
      profile_urn = metadata["urn"]
      profile_name = urn_to_profile[profile_urn]

      inventory_timestamp = inventory["$INVENTORY"][profile_name].get(
          "LastModified")

      # Remove profiles which are newer than upstream.
      if timestamp / 1e6 > inventory_timestamp:
        profiles_to_get.remove(metadata["urn"])

    # Make a threadpool for all the profiles.
    pool = threadpool.ThreadPool.Factory("profiles", 50)
    pool.Start()

    try:
      for urn in profiles_to_get:
        profile = urn_to_profile[urn]
        logging.info("Getting missing profile: %s", profile)
        try:
          pool.AddTask(self.GetProfileByName, (profile, version, True))
        except urlerror.URLError as e:
          logging.info("Exception: %s", e)
    finally:
      pool.Join()
