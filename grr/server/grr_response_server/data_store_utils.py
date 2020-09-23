#!/usr/bin/env python
# Lint as: python3
"""A temporary module with data store utility functions.

This module serves simple functions that delegate calls to appropriate store
(legacy or relational). Once the legacy data store is deprecated functions
provided in this module should be no longer useful.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core import config
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_server import data_store
from grr_response_server.rdfvalues import objects as rdf_objects


def GetClientVersion(client_id):
  """Returns last known GRR version that the client used."""
  sinfo = data_store.REL_DB.ReadClientStartupInfo(client_id=client_id)
  if sinfo is not None:
    return sinfo.client_info.client_version
  else:
    return config.CONFIG["Source.version_numeric"]


def GetClientOs(client_id):
  """Returns last known operating system name that the client used."""
  kb = data_store.REL_DB.ReadClientSnapshot(client_id).knowledge_base
  return kb.os


def GetFileHashEntry(fd):
  """Returns an `rdf_crypto.Hash` instance for given AFF4 file descriptor."""
  # Hash file store is not migrated to RELDB just yet, hence the first check.
  client_id, vfs_path = fd.urn.Split(2)
  path_type, components = rdf_objects.ParseCategorizedPath(vfs_path)

  path_info = data_store.REL_DB.ReadPathInfo(client_id, path_type, components)
  return path_info.hash_entry


def GetClientKnowledgeBase(client_id):
  client = data_store.REL_DB.ReadClientSnapshot(client_id)
  if client is None:
    return None
  return client.knowledge_base


def GetClientInformation(client_id: str) -> rdf_client.ClientInformation:
  startup_info = data_store.REL_DB.ReadClientStartupInfo(client_id)
  if startup_info is None:
    # If we have no startup information, we just return an empty message. This
    # makes the code that handles it easier (as it does not have to consider the
    # null case) and missing fields have to be taken into consideration anyway.
    return rdf_client.ClientInformation()
  else:
    return startup_info.client_info
