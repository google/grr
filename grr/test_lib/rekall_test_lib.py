#!/usr/bin/env python
"""Rekall-related testing classes."""

import os

from grr import config
from grr.client.components.rekall_support import rekall_types as rdf_rekall_types
from grr.lib import rekall_profile_server


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
