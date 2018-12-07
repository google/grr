#!/usr/bin/env python
"""Flows for exporting data out of GRR."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_server import db
from grr_response_server.flows.general import collectors


class Error(Exception):
  pass


class ItemNotExportableError(Error):

  def __init__(self, item):
    super(ItemNotExportableError,
          self).__init__("%r is not exportable" % (item,))


def CollectionItemToAff4Path(item, client_id=None):
  """Converts given RDFValue to an RDFURN of a file to be downloaded."""
  if isinstance(item, rdf_flows.GrrMessage):
    client_id = item.source
    item = item.payload
  if not client_id:
    raise ValueError("Could not determine client_id.")

  if isinstance(item, rdf_client_fs.StatEntry):
    return item.AFF4Path(client_id)
  elif isinstance(item, rdf_file_finder.FileFinderResult):
    return item.stat_entry.AFF4Path(client_id)
  elif isinstance(item, collectors.ArtifactFilesDownloaderResult):
    if item.HasField("downloaded_file"):
      return item.downloaded_file.AFF4Path(client_id)

  raise ItemNotExportableError(item)


def CollectionItemToClientPath(item, client_id=None):
  """Converts given RDFValue to a ClientPath of a file to be downloaded."""
  if isinstance(item, rdf_flows.GrrMessage):
    client_id = item.source
    item = item.payload

  if client_id is None:
    raise ValueError("Could not determine client_id.")
  elif isinstance(client_id, rdf_client.ClientURN):
    client_id = client_id.Basename()

  if isinstance(item, rdf_client_fs.StatEntry):
    return db.ClientPath.FromPathSpec(client_id, item.pathspec)
  elif isinstance(item, rdf_file_finder.FileFinderResult):
    return db.ClientPath.FromPathSpec(client_id, item.stat_entry.pathspec)
  elif isinstance(item, collectors.ArtifactFilesDownloaderResult):
    if item.HasField("downloaded_file"):
      return db.ClientPath.FromPathSpec(client_id,
                                        item.downloaded_file.pathspec)

  raise ItemNotExportableError(item)
