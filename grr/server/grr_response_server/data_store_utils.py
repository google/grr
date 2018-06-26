#!/usr/bin/env python
"""A temporary module with data store utility functions.

This module serves simple functions that delegate calls to appropriate store
(legacy or relational). Once the legacy data store is deprecated functions
provided in this module should be no longer useful.
"""

from grr import config
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import data_store
from grr.server.grr_response_server.rdfvalues import objects as rdf_objects


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


def GetFileHashEntry(fd):
  """Returns an `rdf_crypto.Hash` instance for given AFF4 file descriptor."""
  if data_store.RelationalDBReadEnabled(category="vfs"):
    return GetUrnHashEntry(fd.urn)
  else:
    return fd.Get(fd.Schema.HASH)


def GetUrnHashEntry(urn, token=None):
  """Returns an `rdf_crypto.Hash` instance for given URN of an AFF4 file."""
  if data_store.RelationalDBReadEnabled(category="vfs"):
    client_id, vfs_path = urn.Split(2)
    path_type, components = rdf_objects.ParseCategorizedPath(vfs_path)
    path_id = rdf_objects.PathID(components)

    path_info = data_store.REL_DB.FindPathInfoByPathID(client_id, path_type,
                                                       path_id)
    return path_info.hash_entry
  else:
    with aff4.FACTORY.Open(urn, token=token) as fd:
      return GetFileHashEntry(fd)
