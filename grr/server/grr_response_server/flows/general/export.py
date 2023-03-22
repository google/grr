#!/usr/bin/env python
"""Flows for exporting data out of GRR."""


from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_server.databases import db
from grr_response_server.flows.general import collectors
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects


class Error(Exception):
  pass


class ItemNotExportableError(Error):

  def __init__(self, item):
    super().__init__("%r is not exportable" % (item,))


def CollectionItemToClientPath(item, client_id=None):
  """Converts given RDFValue to a ClientPath of a file to be downloaded."""
  if isinstance(item, rdf_flows.GrrMessage):
    client_id = item.source
    item = item.payload
  elif isinstance(item, rdf_flow_objects.FlowResult):
    client_id = item.client_id
    item = item.payload

  if not client_id:  # Fail if client_id is '' or None.
    raise ValueError("Could not determine client_id.")

  if isinstance(item, rdf_client_fs.StatEntry):
    return db.ClientPath.FromPathSpec(client_id, item.pathspec)
  elif isinstance(item, rdf_file_finder.FileFinderResult):
    return db.ClientPath.FromPathSpec(client_id, item.stat_entry.pathspec)
  elif isinstance(item, rdf_file_finder.CollectSingleFileResult):
    return db.ClientPath.FromPathSpec(client_id, item.stat.pathspec)
  elif isinstance(item, rdf_file_finder.CollectMultipleFilesResult):
    return db.ClientPath.FromPathSpec(client_id, item.stat.pathspec)
  elif isinstance(item, rdf_file_finder.CollectFilesByKnownPathResult):
    return db.ClientPath.FromPathSpec(client_id, item.stat.pathspec)
  elif isinstance(item, collectors.ArtifactFilesDownloaderResult):
    if item.HasField("downloaded_file"):
      return db.ClientPath.FromPathSpec(client_id,
                                        item.downloaded_file.pathspec)

  raise ItemNotExportableError(item)
