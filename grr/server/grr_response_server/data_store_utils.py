#!/usr/bin/env python
"""A temporary module with data store utility functions.

This module serves simple functions that delegate calls to appropriate store
(legacy or relational). Once the legacy data store is deprecated functions
provided in this module should be no longer useful.
"""

from grr import config
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import data_store


def GetClientVersion(client_id, token=None):
  """Returns last known GRR version that the client used."""
  if data_store.RelationalDBReadEnabled():
    client_id = client_id.Basename()
    sinfo = data_store.REL_DB.ReadClientStartupInfo(client_id=client_id)
    if sinfo is not None:
      return sinfo.client_info.client_version
    else:
      return config.CONFIG["Source.version_numeric"]
  else:
    with aff4.FACTORY.Open(client_id, token=token) as client:
      cinfo = client.Get(client.Schema.CLIENT_INFO)
      if cinfo is not None:
        return cinfo.client_version
      else:
        return config.CONFIG["Source.version_numeric"]


def GetClientOs(client_id, token=None):
  """Returns last known operating system name that the client used."""
  if data_store.RelationalDBReadEnabled():
    client_id = client_id.Basename()
    kb = data_store.REL_DB.ReadClientSnapshot(client_id).knowledge_base
  else:
    with aff4.FACTORY.Open(client_id, token=token) as client:
      kb = client.Get(client.Schema.KNOWLEDGE_BASE)

  return kb.os
